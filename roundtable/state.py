from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TypedDict


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    role: str
    worldview: str
    speaking_style: str
    strengths: list[str]
    weaknesses: list[str]
    catchphrases: list[str]
    llm_config: dict[str, Any]
    rag_expert_name: str | None = None
    knowledge_scope: str | None = None
    agent_type: str = "persona"
    profile: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Council:
    name: str
    description: str
    members: list[str]
    moderator_llm_config: dict[str, Any]
    moderator: str = "moderator"


class RoundtableMessage(TypedDict, total=False):
    round: int
    speaker: str
    speaker_id: str
    role: str
    type: str
    content: str
    references: list[str]
    reference_details: list[dict[str, str]]
    epistemic_tags: list[str]
    llm_provider: str
    llm_model: str


class RoundtableState(TypedDict, total=False):
    topic: str
    round: int
    max_rounds: int
    council_name: str
    council_description: str
    current_speaker: str
    personas: list[dict[str, Any]]
    messages: list[RoundtableMessage]
    round_summaries: list[str]
    final_summary: str
    log_path: str
