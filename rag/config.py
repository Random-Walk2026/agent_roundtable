from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path


CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
KNOWLEDGE_DIR = Path("knowledge")
VECTOR_DB_DIR = Path("vector_db") / "chroma"
KEYWORD_INDEX_FILE = "chunks.jsonl"
CHROMA_COLLECTION_NAME = "rag_chunks"
DEFAULT_TOP_K = 5
DEFAULT_EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "mock").lower()
MOCK_EMBEDDING_DIMENSIONS = 384

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class RagPaths:
    root_dir: Path
    knowledge_dir: Path
    vector_db_dir: Path

    def expert_knowledge_dir(self, expert_name: str) -> Path:
        return self.knowledge_dir / expert_name

    def expert_vector_dir(self, expert_name: str) -> Path:
        return self.vector_db_dir / expert_name


def resolve_paths(root_dir: Path | str = ".") -> RagPaths:
    root = Path(root_dir).expanduser().resolve()
    return RagPaths(
        root_dir=root,
        knowledge_dir=root / KNOWLEDGE_DIR,
        vector_db_dir=root / VECTOR_DB_DIR,
    )


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class MockEmbeddingFunction:
    """Small deterministic embedding function accepted by Chroma."""

    def __init__(self, dimensions: int = MOCK_EMBEDDING_DIMENSIONS) -> None:
        self.dimensions = dimensions

    def __call__(self, input: list[str]) -> list[list[float]]:  # Chroma expects this signature.
        return [self._embed(text) for text in input]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text) or [text.lower()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAICompatibleEmbeddingFunction:
    """Placeholder for OpenAI/OpenRouter-compatible embeddings."""

    def __init__(
        self,
        *,
        model: str,
        api_key_env: str,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.api_key_env = api_key_env
        self.base_url = base_url

    def __call__(self, input: list[str]) -> list[list[float]]:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"{self.api_key_env} is required for {self.model} embeddings.")

        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=self.base_url)
        response = client.embeddings.create(model=self.model, input=input)
        return [list(item.embedding) for item in response.data]


class GeminiEmbeddingFunction:
    """Gemini embedding placeholder.

    The project can run without this path by using the mock embedding function or
    the keyword retriever. Fill this adapter in when a production Gemini embedding
    model is chosen.
    """

    def __init__(self, *, model: str, api_key_env: str = "GEMINI_API_KEY") -> None:
        self.model = model
        self.api_key_env = api_key_env

    def __call__(self, input: list[str]) -> list[list[float]]:
        if not os.getenv(self.api_key_env):
            raise RuntimeError(f"{self.api_key_env} is required for Gemini embeddings.")
        raise NotImplementedError(
            "Gemini embedding adapter is a placeholder. Use RAG_EMBEDDING_PROVIDER=mock "
            "or keyword until a production Gemini embedding endpoint is configured."
        )


def create_embedding_function(provider: str | None = None):
    selected = (provider or DEFAULT_EMBEDDING_PROVIDER).lower()
    if selected == "keyword":
        return None
    if selected == "mock":
        return MockEmbeddingFunction()
    if selected == "openai":
        return OpenAICompatibleEmbeddingFunction(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            api_key_env=os.getenv("OPENAI_EMBEDDING_API_KEY_ENV", "OPENAI_API_KEY"),
        )
    if selected == "openrouter":
        return OpenAICompatibleEmbeddingFunction(
            model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
            api_key_env=os.getenv("OPENROUTER_EMBEDDING_API_KEY_ENV", "OPENROUTER_API_KEY_1"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
    if selected == "gemini":
        return GeminiEmbeddingFunction(
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            api_key_env=os.getenv("GEMINI_EMBEDDING_API_KEY_ENV", "GEMINI_API_KEY"),
        )
    raise ValueError(f"Unsupported RAG embedding provider: {provider}")
