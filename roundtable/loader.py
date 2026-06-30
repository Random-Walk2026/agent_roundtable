from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from roundtable.state import Council, Persona


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_structured_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError(f"Config must be a mapping: {path}")
        return data
    raise ValueError(f"Unsupported config format: {path}")


def _find_config(base_dir: Path, name: str) -> Path:
    for suffix in (".yaml", ".yml", ".json"):
        path = base_dir / f"{name}{suffix}"
        if path.exists():
            return path
    raise FileNotFoundError(f"Could not find config '{name}' in {base_dir}")


def _find_persona_config(root: Path, persona_id: str) -> Path:
    search_dirs = [
        root / "config" / "domain_experts",
        root / "config" / "persona_inspired",
    ]
    for base_dir in search_dirs:
        try:
            return _find_config(base_dir, persona_id)
        except FileNotFoundError:
            continue
    searched = ", ".join(str(path) for path in search_dirs)
    raise FileNotFoundError(f"Could not find agent config '{persona_id}' in {searched}")


def _agent_type_for_path(path: Path) -> str:
    parts = set(path.parts)
    if "domain_experts" in parts:
        return "domain_expert"
    if "persona_inspired" in parts:
        return "persona_inspired"
    return "agent"


def load_persona(persona_id: str, root_dir: Path | str | None = None) -> Persona:
    root = Path(root_dir) if root_dir else PROJECT_ROOT
    config_path = _find_persona_config(root, persona_id)
    data = _load_structured_file(config_path)
    return Persona(
        id=persona_id,
        name=str(data["name"]),
        role=str(data["role"]),
        worldview=str(data.get("worldview", "")),
        speaking_style=str(data.get("speaking_style", "")),
        strengths=list(data.get("strengths", [])),
        weaknesses=list(data.get("weaknesses", [])),
        catchphrases=list(data.get("catchphrases", [])),
        llm_config=dict(data.get("llm", {})),
        rag_expert_name=(
            str(data.get("rag_expert_name") or data.get("expert_name"))
            if data.get("rag_expert_name") or data.get("expert_name")
            else None
        ),
        agent_type=str(data.get("agent_type") or _agent_type_for_path(config_path)),
        profile=dict(data.get("profile", {})),
    )


def load_council(council_name: str, root_dir: Path | str | None = None) -> Council:
    root = Path(root_dir) if root_dir else PROJECT_ROOT
    data = _load_structured_file(_find_config(root / "config" / "councils", council_name))
    members = data.get("members", [])
    if not isinstance(members, list) or not members:
        raise ValueError(f"Council '{council_name}' must define at least one member")
    return Council(
        name=str(data.get("name", council_name)),
        description=str(data.get("description", "")),
        members=[str(member) for member in members],
        moderator_llm_config=dict(data.get("moderator_llm", {})),
        moderator=str(data.get("moderator", "moderator")),
    )


def load_council_personas(
    council_name: str,
    root_dir: Path | str | None = None,
) -> tuple[Council, list[Persona]]:
    council = load_council(council_name, root_dir)
    personas = [load_persona(member, root_dir) for member in council.members]
    return council, personas
