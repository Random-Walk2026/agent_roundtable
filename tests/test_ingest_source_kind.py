from pathlib import Path

from rag.ingest import ingest_person


def test_ingest_person_source_kind_merges_without_dropping_other_kinds(tmp_path: Path):
    book = tmp_path / "knowledge" / "people" / "desmond_shum" / "book" / "book.md"
    x_post = tmp_path / "knowledge" / "people" / "desmond_shum" / "x" / "post.md"
    book.parent.mkdir(parents=True)
    x_post.parent.mkdir(parents=True)
    book.write_text(
        "# Red Roulette\n\n" + ("Book content about political access. " * 40),
        encoding="utf-8",
    )
    x_post.write_text(
        "# Balance Sheet\n\n" + ("Household debt is rising quickly. " * 40),
        encoding="utf-8",
    )

    ingest_person("desmond_shum", root_dir=tmp_path, embedding_provider="keyword", reset=True)
    updated = tmp_path / "knowledge" / "people" / "desmond_shum" / "x" / "post.md"
    updated.write_text(
        "# Balance Sheet\n\n" + ("Household debt keeps compressing consumption. " * 40),
        encoding="utf-8",
    )
    stats = ingest_person(
        "desmond_shum",
        root_dir=tmp_path,
        embedding_provider="keyword",
        source_kinds={"x"},
    )

    assert stats["merge_mode"] is True
    assert stats["chunks_indexed"] >= 2
    index_path = (
        tmp_path / "vector_db" / "chroma" / "people__desmond_shum" / "chunks.jsonl"
    )
    text = index_path.read_text(encoding="utf-8")
    assert "book/book.md" in text
    assert "x/post.md" in text
    assert "compressing consumption" in text