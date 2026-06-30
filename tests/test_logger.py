from pathlib import Path

from roundtable.logger import save_markdown_log
from roundtable.state import RoundtableState


def test_markdown_log_uses_topic_filename_in_flat_output_dir(tmp_path: Path):
    state: RoundtableState = {
        "topic": "AI如何影响经济？",
        "round": 1,
        "max_rounds": 1,
        "council_name": "experts",
        "messages": [],
        "final_summary": "summary",
    }

    log_path = Path(save_markdown_log(state, output_dir=tmp_path))

    assert log_path.parent == tmp_path
    assert log_path.name.startswith("AI如何影响经济_")
    assert log_path.suffix == ".md"
    assert "?" not in log_path.name
    assert "？" not in log_path.name
    assert not any(path.is_dir() for path in tmp_path.iterdir())


def test_markdown_log_filename_falls_back_when_topic_has_no_filename_text(tmp_path: Path):
    state: RoundtableState = {
        "topic": "///",
        "round": 1,
        "max_rounds": 1,
        "council_name": "experts",
        "messages": [],
        "final_summary": "summary",
    }

    log_path = Path(save_markdown_log(state, output_dir=tmp_path))

    assert log_path.name.startswith("roundtable_")
    assert log_path.suffix == ".md"


def test_save_markdown_log_includes_epistemic_tags_and_reference_kinds(tmp_path: Path):
    state: RoundtableState = {
        "topic": "测试话题",
        "round": 1,
        "max_rounds": 1,
        "council_name": "experts",
        "messages": [
            {
                "round": 1,
                "speaker": "Macroeconomics",
                "speaker_id": "macroeconomics",
                "role": "宏观经济专家",
                "type": "agent",
                "content": "先看总需求。",
                "references": ["knowledge/experts/macroeconomics/foo.md"],
                "reference_details": [
                    {"source_file": "knowledge/experts/macroeconomics/foo.md", "kind": "book"}
                ],
                "epistemic_tags": ["本地语料", "需联网核实"],
                "llm_provider": "mock",
                "llm_model": "mock",
            }
        ],
        "final_summary": "",
    }

    log_path = save_markdown_log(state, output_dir=tmp_path)
    text = Path(log_path).read_text(encoding="utf-8")
    assert "认识论标签：本地语料，需联网核实" in text
    assert "knowledge/experts/macroeconomics/foo.md (book)" in text