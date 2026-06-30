from __future__ import annotations

from pathlib import Path

from rag.config import PERSON_SOURCE_KINDS


def discover_domain_expert_ids(root_dir: Path | str) -> list[str]:
    root = Path(root_dir).expanduser().resolve()
    agents_dir = root / "config" / "domain_experts"
    if not agents_dir.exists():
        return []
    return sorted(
        path.stem
        for path in agents_dir.glob("*.yaml")
        if path.stem not in {"README"}
    )


def discover_persona_inspired_ids(root_dir: Path | str) -> list[str]:
    root = Path(root_dir).expanduser().resolve()
    agents_dir = root / "config" / "persona_inspired"
    if not agents_dir.exists():
        return []
    return sorted(path.stem for path in agents_dir.glob("*.yaml"))


def discover_configured_agent_ids(root_dir: Path | str) -> list[str]:
    return sorted(
        set(discover_domain_expert_ids(root_dir)) | set(discover_persona_inspired_ids(root_dir))
    )


def discover_knowledge_people_ids(root_dir: Path | str) -> list[str]:
    root = Path(root_dir).expanduser().resolve()
    people_dir = root / "knowledge" / "people"
    if not people_dir.exists():
        return []
    return sorted(path.name for path in people_dir.iterdir() if path.is_dir())


def discover_knowledge_expert_ids(root_dir: Path | str) -> list[str]:
    root = Path(root_dir).expanduser().resolve()
    experts_dir = root / "knowledge" / "experts"
    if not experts_dir.exists():
        return []
    return sorted(path.name for path in experts_dir.iterdir() if path.is_dir())


def people_without_config(root_dir: Path | str) -> list[str]:
    configured = set(discover_persona_inspired_ids(root_dir))
    present = set(discover_knowledge_people_ids(root_dir))
    return sorted(present - configured)


def validate_council_members(members: list[str], root_dir: Path | str) -> None:
    configured = set(discover_configured_agent_ids(root_dir))
    missing = [member for member in members if member not in configured]
    if missing:
        available = ", ".join(discover_configured_agent_ids(root_dir))
        raise ValueError(
            f"Unknown council members: {', '.join(missing)}. "
            f"Configured agents: {available or '(none)'}"
        )


def standard_person_source_kinds() -> frozenset[str]:
    return PERSON_SOURCE_KINDS