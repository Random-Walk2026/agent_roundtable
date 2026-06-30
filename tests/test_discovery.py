from pathlib import Path

import pytest

from roundtable.discovery import (
    discover_configured_agent_ids,
    discover_knowledge_people_ids,
    validate_council_members,
)


def test_discover_configured_agent_ids_includes_experts_and_personas():
    ids = set(discover_configured_agent_ids(Path(__file__).resolve().parents[1]))
    assert "macroeconomics" in ids
    assert "desmond_shum" in ids


def test_validate_council_members_rejects_unknown_ids(tmp_path: Path):
    (tmp_path / "config" / "domain_experts").mkdir(parents=True)
    (tmp_path / "config" / "persona_inspired").mkdir(parents=True)
    (tmp_path / "config" / "domain_experts" / "macroeconomics.yaml").write_text(
        "name: Macro\nrole: r\nrag_expert_name: macroeconomics\nagent_type: domain_expert\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unknown council members"):
        validate_council_members(["macroeconomics", "missing_agent"], tmp_path)


def test_discover_knowledge_people_ids(tmp_path: Path):
    (tmp_path / "knowledge" / "people" / "desmond_shum" / "book").mkdir(parents=True)
    assert discover_knowledge_people_ids(tmp_path) == ["desmond_shum"]