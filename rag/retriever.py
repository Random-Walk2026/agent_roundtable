from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from rag.chunker import RagChunk, chunk_expert_markdown
from rag.config import (
    CHROMA_COLLECTION_NAME,
    DEFAULT_TOP_K,
    KEYWORD_INDEX_FILE,
    create_embedding_function,
    resolve_paths,
    tokenize,
)


Backend = Literal["auto", "chroma", "keyword"]


def _load_keyword_chunks(expert_name: str, root_dir: Path | str) -> list[RagChunk]:
    paths = resolve_paths(root_dir)
    index_path = paths.expert_vector_dir(expert_name) / KEYWORD_INDEX_FILE
    if not index_path.exists():
        return chunk_expert_markdown(expert_name, root_dir=paths.root_dir)

    chunks: list[RagChunk] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        chunks.append(
            RagChunk(
                page_content=str(item.get("page_content", "")),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return chunks


def _keyword_score(query_terms: Counter[str], chunk: RagChunk) -> float:
    text = " ".join(
        [
            chunk.page_content,
            str(chunk.metadata.get("title", "")),
            str(chunk.metadata.get("chapter", "")),
            str(chunk.metadata.get("source_file", "")),
        ]
    )
    chunk_terms = Counter(tokenize(text))
    if not chunk_terms:
        return 0.0
    return float(sum(min(count, chunk_terms.get(term, 0)) for term, count in query_terms.items()))


def _keyword_search(
    *,
    expert_name: str,
    query: str,
    root_dir: Path | str,
    top_k: int,
) -> list[RagChunk]:
    chunks = _load_keyword_chunks(expert_name, root_dir)
    if not chunks:
        return []

    query_terms = Counter(tokenize(query))
    scored: list[RagChunk] = []
    if query_terms:
        for chunk in chunks:
            score = _keyword_score(query_terms, chunk)
            if score > 0:
                scored.append(
                    RagChunk(
                        page_content=chunk.page_content,
                        metadata=dict(chunk.metadata),
                        score=score,
                    )
                )

    if not scored:
        scored = [
            RagChunk(page_content=chunk.page_content, metadata=dict(chunk.metadata), score=0.0)
            for chunk in chunks[:top_k]
        ]

    scored.sort(
        key=lambda chunk: (
            -chunk.score,
            str(chunk.metadata.get("source_file", "")),
            int(chunk.metadata.get("chunk_index", 0)),
        )
    )
    return scored[:top_k]


def _chroma_search(
    *,
    expert_name: str,
    query: str,
    root_dir: Path | str,
    top_k: int,
) -> list[RagChunk]:
    try:
        import chromadb
    except ImportError:
        return []

    paths = resolve_paths(root_dir)
    persist_dir = paths.expert_vector_dir(expert_name)
    if not persist_dir.exists():
        return []

    embedding_function = create_embedding_function()
    if embedding_function is None:
        return []

    try:
        client = chromadb.PersistentClient(path=str(persist_dir))
        collection = client.get_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=embedding_function,
        )
        result = collection.query(query_texts=[query], n_results=top_k)
    except Exception:
        return []

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0] if result.get("distances") else []
    chunks: list[RagChunk] = []
    for index, document in enumerate(documents):
        distance = float(distances[index]) if index < len(distances) else 0.0
        chunks.append(
            RagChunk(
                page_content=str(document),
                metadata=dict(metadatas[index] or {}),
                score=1.0 - distance,
            )
        )
    return chunks


class RagRetriever:
    def __init__(
        self,
        expert_name: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        root_dir: Path | str = ".",
        backend: Backend = "auto",
    ) -> None:
        self.expert_name = expert_name
        self.top_k = top_k
        self.root_dir = root_dir
        self.backend = backend

    def invoke(self, query: str) -> list[RagChunk]:
        if self.backend in {"auto", "chroma"}:
            chunks = _chroma_search(
                expert_name=self.expert_name,
                query=query,
                root_dir=self.root_dir,
                top_k=self.top_k,
            )
            if chunks or self.backend == "chroma":
                return chunks

        return _keyword_search(
            expert_name=self.expert_name,
            query=query,
            root_dir=self.root_dir,
            top_k=self.top_k,
        )

    def get_relevant_documents(self, query: str) -> list[RagChunk]:
        return self.invoke(query)


def get_retriever(
    expert_name: str,
    top_k: int = DEFAULT_TOP_K,
    *,
    root_dir: Path | str = ".",
    backend: Backend = "auto",
) -> RagRetriever:
    return RagRetriever(expert_name, top_k=top_k, root_dir=root_dir, backend=backend)


def format_retrieved_context(chunks: list[RagChunk]) -> str:
    if not chunks:
        return "暂无可用参考资料。"

    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        source_file = metadata.get("source_file", "")
        title = metadata.get("title", "")
        chapter = metadata.get("chapter", "")
        text = " ".join(chunk.page_content.split())
        lines.append(
            f"[{index}] source_file={source_file}; title={title}; chapter={chapter}\n{text[:700]}"
        )
    return "\n\n".join(lines)


def source_files(chunks: list[RagChunk]) -> list[str]:
    files = [str(chunk.metadata.get("source_file", "")) for chunk in chunks]
    return [source for source in dict.fromkeys(files) if source]
