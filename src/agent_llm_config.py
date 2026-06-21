from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_AGENT_LLM_CONFIG_PATH = Path("configs") / "agent_llms.json"
ALLOWED_LLM_CONFIG_KEYS = {"provider", "model", "api_key_env", "base_url", "timeout"}
DEFAULT_DESCRIPTION = (
    "Committed per-agent LLM routing. Store real API keys in .env; "
    "this file only names provider, model, and api_key_env."
)


def _resolve_config_path(
    root_dir: Path | str,
    config_path: Path | str | None = None,
) -> Path:
    root = Path(root_dir)
    path = Path(config_path) if config_path else root / DEFAULT_AGENT_LLM_CONFIG_PATH
    if not path.is_absolute():
        path = root / path
    return path


def _sanitize_agent_configs(agents: dict[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for agent_id, config in agents.items():
        if not isinstance(agent_id, str) or not isinstance(config, dict):
            raise ValueError(f"Agent LLM config entries must map agent ids to objects: {path}")
        unknown_keys = set(config) - ALLOWED_LLM_CONFIG_KEYS
        if unknown_keys:
            keys = ", ".join(sorted(unknown_keys))
            raise ValueError(f"Unsupported LLM config keys for '{agent_id}': {keys}")
        configs[agent_id] = {
            key: value
            for key, value in config.items()
            if value is not None and value != ""
        }
    return configs


def load_agent_llm_config_document(
    root_dir: Path | str,
    config_path: Path | str | None = None,
) -> dict[str, Any]:
    path = _resolve_config_path(root_dir, config_path)
    if not path.exists():
        return {"description": DEFAULT_DESCRIPTION, "agents": {}}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Agent LLM config must be a JSON object: {path}")
    agents = data.get("agents")
    if not isinstance(agents, dict):
        raise ValueError(f"Agent LLM config must contain an 'agents' object: {path}")
    return {
        "description": str(data.get("description") or DEFAULT_DESCRIPTION),
        "agents": _sanitize_agent_configs(agents, path),
    }


def load_agent_llm_configs(
    root_dir: Path | str,
    config_path: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    return load_agent_llm_config_document(root_dir, config_path)["agents"]


def save_agent_llm_config_document(
    root_dir: Path | str,
    agents: dict[str, Any],
    config_path: Path | str | None = None,
    *,
    description: str = DEFAULT_DESCRIPTION,
) -> Path:
    path = _resolve_config_path(root_dir, config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "description": description,
        "agents": _sanitize_agent_configs(agents, path),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
