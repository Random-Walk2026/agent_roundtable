from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Literal

from rag.chunker import RagChunk, chunk_corpus_markdown
from rag.config import (
    CHROMA_COLLECTION_NAME,
    DEFAULT_TOP_K,
    KEYWORD_INDEX_FILE,
    SOURCE_KIND_WEIGHTS,
    KnowledgeScope,
    create_embedding_function,
    resolve_corpus,
    resolve_paths,
)


Backend = Literal["auto", "chroma", "keyword"]


def _load_keyword_chunks(
    corpus_id: str,
    *,
    knowledge_scope: KnowledgeScope,
    root_dir: Path | str,
) -> list[RagChunk]:
    corpus = resolve_corpus(corpus_id, knowledge_scope=knowledge_scope)
    paths = resolve_paths(root_dir)
    index_path = paths.corpus_vector_dir(corpus) / KEYWORD_INDEX_FILE
    if not index_path.exists():
        return chunk_corpus_markdown(
            corpus_id,
            knowledge_scope=knowledge_scope,
            root_dir=paths.root_dir,
        )

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


def _source_kind_weight(chunk: RagChunk) -> float:
    kind = str(chunk.metadata.get("source_kind") or chunk.metadata.get("work_type") or "")
    return SOURCE_KIND_WEIGHTS.get(kind, 1.0)


def _keyword_score(query_terms: Counter[str], chunk: RagChunk) -> float:
    text = " ".join(
        [
            chunk.page_content,
            str(chunk.metadata.get("title", "")),
            str(chunk.metadata.get("chapter", "")),
            str(chunk.metadata.get("source_file", "")),
            str(chunk.metadata.get("source_kind", "")),
            str(chunk.metadata.get("work_type", "")),
        ]
    )
    chunk_terms = Counter(tokenize(text))
    if not chunk_terms:
        return 0.0
    base = float(sum(min(count, chunk_terms.get(term, 0)) for term, count in query_terms.items()))
    return base * _source_kind_weight(chunk)


def tokenize(text: str) -> list[str]:
    from rag.config import tokenize as _tokenize

    return _tokenize(text)


def _keyword_search(
    *,
    corpus_id: str,
    knowledge_scope: KnowledgeScope,
    query: str,
    root_dir: Path | str,
    top_k: int,
) -> list[RagChunk]:
    chunks = _load_keyword_chunks(corpus_id, knowledge_scope=knowledge_scope, root_dir=root_dir)
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
            -_source_kind_weight(chunk),
            str(chunk.metadata.get("source_file", "")),
            int(chunk.metadata.get("chunk_index", 0)),
        )
    )
    return scored[:top_k]


def _chroma_search(
    *,
    corpus_id: str,
    knowledge_scope: KnowledgeScope,
    query: str,
    root_dir: Path | str,
    top_k: int,
) -> list[RagChunk]:
    try:
        import chromadb
    except ImportError:
        return []

    corpus = resolve_corpus(corpus_id, knowledge_scope=knowledge_scope)
    paths = resolve_paths(root_dir)
    persist_dir = paths.corpus_vector_dir(corpus)
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
        result = collection.query(query_texts=[query], n_results=max(top_k * 3, top_k))
    except Exception:
        return []

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0] if result.get("distances") else []
    chunks: list[RagChunk] = []
    for index, document in enumerate(documents):
        distance = float(distances[index]) if index < len(distances) else 0.0
        metadata = dict(metadatas[index] or {})
        chunks.append(
            RagChunk(
                page_content=str(document),
                metadata=metadata,
                score=(1.0 - distance) * _source_kind_weight(
                    RagChunk(page_content=str(document), metadata=metadata)
                ),
            )
        )
    chunks.sort(
        key=lambda chunk: (
            -chunk.score,
            str(chunk.metadata.get("source_file", "")),
            int(chunk.metadata.get("chunk_index", 0)),
        )
    )
    return chunks[:top_k]


class RagRetriever:
    def __init__(
        self,
        corpus_id: str,
        *,
        knowledge_scope: KnowledgeScope = "experts",
        top_k: int = DEFAULT_TOP_K,
        root_dir: Path | str = ".",
        backend: Backend = "auto",
    ) -> None:
        self.corpus_id = corpus_id
        self.knowledge_scope = knowledge_scope
        self.expert_name = corpus_id
        self.top_k = top_k
        self.root_dir = root_dir
        self.backend = backend

    def invoke(self, query: str) -> list[RagChunk]:
        if self.backend in {"auto", "chroma"}:
            chunks = _chroma_search(
                corpus_id=self.corpus_id,
                knowledge_scope=self.knowledge_scope,
                query=query,
                root_dir=self.root_dir,
                top_k=self.top_k,
            )
            if chunks or self.backend == "chroma":
                return chunks

        return _keyword_search(
            corpus_id=self.corpus_id,
            knowledge_scope=self.knowledge_scope,
            query=query,
            root_dir=self.root_dir,
            top_k=self.top_k,
        )

    def get_relevant_documents(self, query: str) -> list[RagChunk]:
        return self.invoke(query)


def get_retriever(
    corpus_id: str,
    top_k: int = DEFAULT_TOP_K,
    *,
    knowledge_scope: KnowledgeScope = "experts",
    root_dir: Path | str = ".",
    backend: Backend = "auto",
) -> RagRetriever:
    return RagRetriever(
        corpus_id,
        knowledge_scope=knowledge_scope,
        top_k=top_k,
        root_dir=root_dir,
        backend=backend,
    )


def format_retrieved_context(chunks: list[RagChunk]) -> str:
    if not chunks:
        return "暂无可用参考资料。"

    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        source_file = metadata.get("source_file", "")
        title = metadata.get("title", "")
        chapter = metadata.get("chapter", "")
        source_kind = metadata.get("source_kind", "")
        work_type = metadata.get("work_type", "")
        kind_label = source_kind or work_type
        text = " ".join(chunk.page_content.split())
        kind_suffix = f"; kind={kind_label}" if kind_label else ""
        lines.append(
            f"[{index}] source_file={source_file}; title={title}; chapter={chapter}{kind_suffix}\n{text[:700]}"
        )
    return "\n\n".join(lines)


def source_files(chunks: list[RagChunk]) -> list[str]:
    files = [str(chunk.metadata.get("source_file", "")) for chunk in chunks]
    return [source for source in dict.fromkeys(files) if source]