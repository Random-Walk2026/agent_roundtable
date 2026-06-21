from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from rag.chunker import RagChunk, chunk_expert_markdown
from rag.config import (
    CHROMA_COLLECTION_NAME,
    DEFAULT_EMBEDDING_PROVIDER,
    KEYWORD_INDEX_FILE,
    create_embedding_function,
    resolve_paths,
)


def _chunk_id(chunk: RagChunk) -> str:
    raw = "|".join(
        [
            str(chunk.metadata.get("expert_name", "")),
            str(chunk.metadata.get("source_file", "")),
            str(chunk.metadata.get("chunk_index", "")),
            chunk.page_content,
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _serialize_chunk(chunk: RagChunk) -> dict[str, Any]:
    return {
        "id": _chunk_id(chunk),
        "page_content": chunk.page_content,
        "metadata": dict(chunk.metadata),
    }


def _write_keyword_index(chunks: list[RagChunk], persist_dir: Path) -> None:
    persist_dir.mkdir(parents=True, exist_ok=True)
    index_path = persist_dir / KEYWORD_INDEX_FILE
    lines = [json.dumps(_serialize_chunk(chunk), ensure_ascii=False) for chunk in chunks]
    index_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_chroma(
    *,
    chunks: list[RagChunk],
    persist_dir: Path,
    embedding_provider: str,
    reset: bool,
) -> bool:
    if not chunks:
        return False

    try:
        import chromadb
    except ImportError:
        return False

    embedding_function = create_embedding_function(embedding_provider)
    if embedding_function is None:
        return False

    client = chromadb.PersistentClient(path=str(persist_dir))
    if reset:
        try:
            client.delete_collection(CHROMA_COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[_chunk_id(chunk) for chunk in chunks],
        documents=[chunk.page_content for chunk in chunks],
        metadatas=[dict(chunk.metadata) for chunk in chunks],
    )
    return True


def ingest_expert(
    expert_name: str,
    *,
    root_dir: Path | str = ".",
    embedding_provider: str | None = None,
    reset: bool = True,
) -> dict[str, Any]:
    paths = resolve_paths(root_dir)
    persist_dir = paths.expert_vector_dir(expert_name)
    if reset and persist_dir.exists():
        shutil.rmtree(persist_dir)

    chunks = chunk_expert_markdown(expert_name, root_dir=paths.root_dir)
    _write_keyword_index(chunks, persist_dir)

    provider = (embedding_provider or DEFAULT_EMBEDDING_PROVIDER).lower()
    chroma_written = False
    if provider != "keyword":
        chroma_written = _write_chroma(
            chunks=chunks,
            persist_dir=persist_dir,
            embedding_provider=provider,
            reset=False,
        )

    return {
        "expert_name": expert_name,
        "files_indexed": len({chunk.metadata.get("source_file") for chunk in chunks}),
        "chunks_indexed": len(chunks),
        "persist_dir": str(persist_dir),
        "backend": "chroma" if chroma_written else "keyword",
        "embedding_provider": provider,
    }


def _discover_experts(root_dir: Path | str = ".") -> list[str]:
    paths = resolve_paths(root_dir)
    if not paths.knowledge_dir.exists():
        return []
    return sorted(path.name for path in paths.knowledge_dir.iterdir() if path.is_dir())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest expert Markdown knowledge into local RAG storage.")
    parser.add_argument("--expert-name", action="append", help="Expert folder under knowledge/.")
    parser.add_argument("--root-dir", default=".", help="Project root directory.")
    parser.add_argument(
        "--embedding-provider",
        default=None,
        choices=["keyword", "mock", "openai", "gemini", "openrouter"],
        help="Embedding backend. keyword skips embeddings; mock uses deterministic local vectors.",
    )
    parser.add_argument("--no-reset", action="store_true", help="Keep existing vector DB contents.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    experts = args.expert_name or _discover_experts(args.root_dir)
    if not experts:
        raise SystemExit("No expert folders found under knowledge/.")

    for expert_name in experts:
        stats = ingest_expert(
            expert_name,
            root_dir=args.root_dir,
            embedding_provider=args.embedding_provider,
            reset=not args.no_reset,
        )
        print(
            f"{stats['expert_name']}: indexed {stats['files_indexed']} files, "
            f"{stats['chunks_indexed']} chunks -> {stats['persist_dir']} "
            f"({stats['backend']}, provider={stats['embedding_provider']})"
        )


if __name__ == "__main__":
    main()
