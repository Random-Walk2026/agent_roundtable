from __future__ import annotations

from rag.chunker import RagChunk
from roundtable.state import Persona


EPISTEMIC_LOCAL_CORPUS = "本地语料"
EPISTEMIC_STYLE_ONLY = "纯风格推演"
EPISTEMIC_NO_LOCAL_HIT = "无本地命中"
EPISTEMIC_VERIFY_ONLINE = "需联网核实"


def classify_epistemic_tags(
    persona: Persona,
    *,
    references: list[str],
    rag_configured: bool,
) -> list[str]:
    tags: list[str] = []
    if references:
        tags.append(EPISTEMIC_LOCAL_CORPUS)
    elif rag_configured:
        tags.append(EPISTEMIC_NO_LOCAL_HIT)
    else:
        tags.append(EPISTEMIC_STYLE_ONLY)

    if persona.agent_type in {"domain_expert", "persona_inspired"}:
        tags.append(EPISTEMIC_VERIFY_ONLINE)
    return tags


def format_reference_details(chunks: list[RagChunk]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk in chunks:
        source_file = str(chunk.metadata.get("source_file", ""))
        if not source_file or source_file in seen:
            continue
        seen.add(source_file)
        kind = str(chunk.metadata.get("source_kind") or chunk.metadata.get("work_type") or "")
        detail = {"source_file": source_file}
        if kind:
            detail["kind"] = kind
        details.append(detail)
    return details