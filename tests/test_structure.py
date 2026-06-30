from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_EXPERT_IDS = {
    "ai_researcher",
    "history_strategist",
    "investing_master",
    "macro_economist",
    "philosophy_expert",
}
EXPECTED_PERSONA_IDS = {
    "buffett_inspired",
    "dalio_inspired",
    "hayek_inspired",
    "munger_inspired",
}
BOOK_LEVEL_MIN_LINES = 1000


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must be a YAML mapping"
    return data


def test_knowledge_contains_only_book_level_expert_corpora():
    knowledge_dir = PROJECT_ROOT / "knowledge"
    actual_dirs = {path.name for path in knowledge_dir.iterdir() if path.is_dir()}

    assert actual_dirs <= EXPECTED_EXPERT_IDS

    markdown_files = [
        path for path in sorted(knowledge_dir.rglob("*.md"))
        if path.relative_to(knowledge_dir).parts[0] in EXPECTED_EXPERT_IDS
    ]
    for path in markdown_files:
        line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        assert line_count >= BOOK_LEVEL_MIN_LINES, f"{path} has only {line_count} lines"


def test_councils_are_limited_to_experts_and_persona_inspired_modes():
    councils_dir = PROJECT_ROOT / "config" / "councils"
    council_files = {path.stem for path in councils_dir.glob("*.yaml")}

    assert council_files == {"experts", "persona_inspired"}
    assert _load_yaml(councils_dir / "experts.yaml")["members"] == [
        "macro_economist",
        "investing_master",
        "ai_researcher",
        "philosophy_expert",
        "history_strategist",
    ]
    assert _load_yaml(councils_dir / "persona_inspired.yaml")["members"] == [
        "buffett_inspired",
        "munger_inspired",
        "dalio_inspired",
        "hayek_inspired",
    ]


def test_domain_experts_use_matching_book_corpora():
    agents_dir = PROJECT_ROOT / "config" / "domain_experts"
    agent_files = {path.stem for path in agents_dir.glob("*.yaml")}

    assert agent_files == EXPECTED_EXPERT_IDS
    for expert_id in EXPECTED_EXPERT_IDS:
        data = _load_yaml(agents_dir / f"{expert_id}.yaml")
        assert data["agent_type"] == "domain_expert"
        assert data["rag_expert_name"] == expert_id
        assert (PROJECT_ROOT / "knowledge" / expert_id).is_dir()
        assert "knowledge_sources" not in data


def test_persona_inspired_agents_are_style_only_until_their_books_exist():
    agents_dir = PROJECT_ROOT / "config" / "persona_inspired"
    agent_files = {path.stem for path in agents_dir.glob("*.yaml")}

    assert agent_files == EXPECTED_PERSONA_IDS
    for persona_id in EXPECTED_PERSONA_IDS:
        data = _load_yaml(agents_dir / f"{persona_id}.yaml")
        assert data["agent_type"] == "persona_inspired"
        assert "rag_expert_name" not in data
        assert "knowledge_sources" not in data
        assert data["profile"]["knowledge_status"] == "pending_person_specific_corpus"


def test_legacy_personas_directory_has_been_removed():
    assert not (PROJECT_ROOT / "personas").exists()
