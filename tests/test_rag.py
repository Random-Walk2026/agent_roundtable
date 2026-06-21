from pathlib import Path

from rag.chunker import chunk_expert_markdown
from rag.ingest import ingest_expert
from rag.retriever import get_retriever


def test_chunk_expert_markdown_keeps_required_metadata(tmp_path: Path):
    source = tmp_path / "knowledge" / "macro_economist" / "keynes" / "demand.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Keynesian Demand\n\n"
        "Intro paragraph about aggregate demand.\n\n"
        "## Fiscal Policy\n\n"
        + ("Multiplier policy can stabilize employment and demand. " * 40),
        encoding="utf-8",
    )

    chunks = chunk_expert_markdown("macro_economist", root_dir=tmp_path)

    assert chunks
    assert chunks[0].metadata["expert_name"] == "macro_economist"
    assert chunks[0].metadata["source_file"] == "knowledge/macro_economist/keynes/demand.md"
    assert chunks[0].metadata["title"] == "Keynesian Demand"
    assert any(chunk.metadata["chapter"] == "Fiscal Policy" for chunk in chunks)
    assert all(len(chunk.page_content) <= 900 for chunk in chunks)


def test_keyword_mock_retriever_works_without_embedding_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    source = tmp_path / "knowledge" / "investing_master" / "buffett" / "moat.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Durable Moats\n\n"
        "## Pricing Power\n\n"
        "A strong business has durable pricing power, high return on capital, "
        "and managers who avoid leverage.",
        encoding="utf-8",
    )

    stats = ingest_expert(
        "investing_master",
        root_dir=tmp_path,
        embedding_provider="keyword",
    )
    retriever = get_retriever("investing_master", top_k=2, root_dir=tmp_path, backend="keyword")
    results = retriever.invoke("pricing power leverage capital")

    assert stats["chunks_indexed"] >= 1
    assert stats["backend"] == "keyword"
    assert (tmp_path / "vector_db" / "chroma" / "investing_master" / "chunks.jsonl").exists()
    assert results
    assert results[0].metadata["source_file"] == "knowledge/investing_master/buffett/moat.md"
    assert "pricing power" in results[0].page_content


def test_chunk_expert_markdown_ignores_external_sources_yaml(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    external_dir = tmp_path / "doc2md" / "宏观经济专家"
    external_dir.mkdir(parents=True)
    external_file = external_dir / "general_theory.md"
    external_file.write_text(
        "# General Theory\n\n"
        "## Employment\n\n"
        "Effective demand is central to employment analysis.",
        encoding="utf-8",
    )
    (project_root / "rag").mkdir()
    (project_root / "rag" / "sources.yaml").write_text(
        "macro_economist:\n"
        f"  - {external_dir}\n",
        encoding="utf-8",
    )

    chunks = chunk_expert_markdown("macro_economist", root_dir=project_root)

    assert chunks == []


def test_chunker_strips_doc2md_image_and_html_noise(tmp_path: Path):
    source = tmp_path / "knowledge" / "ai_researcher" / "turing.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "![](/tmp/cover.jpg)\n\n"
        "<div><svg><image href=\"cover.jpg\"></image></svg></div>\n\n"
        "# Computing Machinery\n\n"
        "<span id=\"p1\"></span> The imitation game asks whether machines can think.",
        encoding="utf-8",
    )

    chunks = chunk_expert_markdown("ai_researcher", root_dir=tmp_path)
    text = "\n".join(chunk.page_content for chunk in chunks)

    assert "cover.jpg" not in text
    assert "<svg" not in text
    assert "imitation game" in text
