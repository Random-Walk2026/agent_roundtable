from pathlib import Path

from src.logger import save_markdown_log
from src.state import RoundtableState


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
