from pathlib import Path

import yaml

from rag.config import PERSON_SOURCE_KINDS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_EXPERT_IDS = {
    "computing",
    "history",
    "investing",
    "macroeconomics",
    "philosophy",
}
EXPECTED_PERSONA_IDS = {
    "buffett",
    "dalio",
    "desmond_shum",
    "hayek",
    "munger",
}
STYLE_ONLY_PERSONA_IDS = EXPECTED_PERSONA_IDS - {"desmond_shum"}
PERSON_CORPUS_PERSONA_IDS = {"desmond_shum"}
EXPECTED_PERSON_IDS = {"desmond_shum"}
BOOK_LEVEL_MIN_LINES = 1000


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must be a YAML mapping"
    return data


def test_knowledge_layout_separates_experts_and_people():
    knowledge_dir = PROJECT_ROOT / "knowledge"
    experts_dir = knowledge_dir / "experts"
    people_dir = knowledge_dir / "people"

    assert experts_dir.is_dir()
    assert people_dir.is_dir()

    actual_expert_dirs = {path.name for path in experts_dir.iterdir() if path.is_dir()}
    actual_people_dirs = {path.name for path in people_dir.iterdir() if path.is_dir()}

    assert actual_expert_dirs <= EXPECTED_EXPERT_IDS
    assert actual_people_dirs <= EXPECTED_PERSON_IDS

    markdown_files = [
        path
        for path in sorted(experts_dir.rglob("*.md"))
        if path.relative_to(experts_dir).parts[0] in EXPECTED_EXPERT_IDS
    ]
    for path in markdown_files:
        line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        assert line_count >= BOOK_LEVEL_MIN_LINES, f"{path} has only {line_count} lines"


def test_person_folders_use_standard_source_kinds():
    people_dir = PROJECT_ROOT / "knowledge" / "people"
    for person_id in EXPECTED_PERSON_IDS:
        person_dir = people_dir / person_id
        assert person_dir.is_dir()
        actual_kinds = {path.name for path in person_dir.iterdir() if path.is_dir()}
        assert actual_kinds <= set(PERSON_SOURCE_KINDS)


def test_councils_include_core_and_mixed_modes():
    councils_dir = PROJECT_ROOT / "config" / "councils"
    council_files = {path.stem for path in councils_dir.glob("*.yaml")}

    assert council_files >= {"experts", "persona_inspired", "china_debt"}
    assert _load_yaml(councils_dir / "experts.yaml")["members"] == [
        "macroeconomics",
        "investing",
        "computing",
        "philosophy",
        "history",
    ]
    assert _load_yaml(councils_dir / "persona_inspired.yaml")["members"] == [
        "buffett",
        "munger",
        "dalio",
        "hayek",
        "desmond_shum",
    ]
    assert _load_yaml(councils_dir / "china_debt.yaml")["members"] == [
        "macroeconomics",
        "desmond_shum",
        "history",
    ]


def test_domain_experts_use_matching_book_corpora():
    agents_dir = PROJECT_ROOT / "config" / "domain_experts"
    agent_files = {path.stem for path in agents_dir.glob("*.yaml")}

    assert agent_files == EXPECTED_EXPERT_IDS
    for expert_id in EXPECTED_EXPERT_IDS:
        data = _load_yaml(agents_dir / f"{expert_id}.yaml")
        assert data["agent_type"] == "domain_expert"
        assert data["rag_expert_name"] == expert_id
        assert (PROJECT_ROOT / "knowledge" / "experts" / expert_id).is_dir()
        assert "knowledge_sources" not in data


def test_persona_inspired_agents_use_style_or_person_corpus_profiles():
    agents_dir = PROJECT_ROOT / "config" / "persona_inspired"
    agent_files = {path.stem for path in agents_dir.glob("*.yaml")}

    assert agent_files == EXPECTED_PERSONA_IDS
    for persona_id in STYLE_ONLY_PERSONA_IDS:
        data = _load_yaml(agents_dir / f"{persona_id}.yaml")
        assert data["agent_type"] == "persona_inspired"
        assert "rag_expert_name" not in data
        assert "knowledge_sources" not in data.get("profile", {})
        assert data["profile"]["knowledge_status"] == "pending_person_specific_corpus"

    for persona_id in PERSON_CORPUS_PERSONA_IDS:
        data = _load_yaml(agents_dir / f"{persona_id}.yaml")
        assert data["agent_type"] == "persona_inspired"
        assert data["knowledge_scope"] == "people"
        assert data["rag_expert_name"] == persona_id
        assert data["profile"]["knowledge_status"] == "multi_source_corpus"
        assert data["profile"]["knowledge_sources"]
        assert (PROJECT_ROOT / "knowledge" / "people" / persona_id).is_dir()


def test_legacy_personas_directory_has_been_removed():
    assert not (PROJECT_ROOT / "personas").exists()