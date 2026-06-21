import json
from pathlib import Path

from src.agent_llm_config import (
    load_agent_llm_config_document,
    load_agent_llm_configs,
    save_agent_llm_config_document,
)


def test_save_agent_llm_config_document_writes_sanitized_agent_configs(tmp_path: Path):
    save_agent_llm_config_document(
        tmp_path,
        {
            "macro_economist": {
                "provider": "openrouter",
                "model": "model-a",
                "api_key_env": "OPENROUTER_API_KEY_1",
                "base_url": "",
            }
        },
    )

    path = tmp_path / "configs" / "agent_llms.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["agents"]["macro_economist"] == {
        "provider": "openrouter",
        "model": "model-a",
        "api_key_env": "OPENROUTER_API_KEY_1",
    }
    assert load_agent_llm_configs(tmp_path)["macro_economist"]["model"] == "model-a"


def test_load_agent_llm_config_document_returns_default_when_missing(tmp_path: Path):
    payload = load_agent_llm_config_document(tmp_path)

    assert payload["agents"] == {}
    assert "description" in payload
