from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from roundtable.state import RoundtableState


FILENAME_SAFE_RE = re.compile(r"[^\w\u4e00-\u9fff-]+", re.UNICODE)


def _topic_filename_prefix(topic: str) -> str:
    prefix = FILENAME_SAFE_RE.sub("_", topic.strip())
    prefix = re.sub(r"_+", "_", prefix).strip("_")
    return prefix or "roundtable"


def _format_reference_line(reference: str, details: list[dict[str, str]]) -> str:
    kind = ""
    for detail in details:
        if detail.get("source_file") == reference and detail.get("kind"):
            kind = str(detail["kind"])
            break
    if kind:
        return f"- {reference} ({kind})"
    return f"- {reference}"


def save_markdown_log(state: RoundtableState, output_dir: Path | str = "logs") -> str:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_prefix = _topic_filename_prefix(str(state.get("topic", "")))
    path = directory / f"{topic_prefix}_{timestamp}.md"

    lines: list[str] = [
        f"# Agent Roundtable: {state.get('topic', '')}",
        "",
        f"- Council: {state.get('council_name', '')}",
        f"- Rounds: {state.get('round', 0)}/{state.get('max_rounds', 0)}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Transcript",
        "",
    ]

    for message in state.get("messages", []):
        round_number = message.get("round", "-")
        speaker = message.get("speaker", "Unknown")
        role = message.get("role", "")
        content = message.get("content", "")
        references = message.get("references", [])
        reference_details = list(message.get("reference_details", []))
        epistemic_tags = message.get("epistemic_tags", [])
        llm_provider = message.get("llm_provider", "unknown")
        llm_model = message.get("llm_model", "unknown")
        lines.extend(
            [
                f"### Round {round_number} - {speaker}",
                "",
                f"*{role}*",
                "",
                f"LLM: {llm_provider} / {llm_model}",
                "",
            ]
        )
        if epistemic_tags:
            lines.append(f"认识论标签：{'，'.join(epistemic_tags)}")
            lines.append("")
        lines.extend([content, ""])
        if references:
            lines.extend(["References:", ""])
            lines.extend(
                _format_reference_line(reference, reference_details) for reference in references
            )
            lines.append("")

    final_summary = state.get("final_summary", "")
    if final_summary:
        lines.extend(["## Final Summary", "", final_summary, ""])

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)