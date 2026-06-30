from roundtable.epistemics import (
    EPISTEMIC_LOCAL_CORPUS,
    EPISTEMIC_NO_LOCAL_HIT,
    EPISTEMIC_STYLE_ONLY,
    EPISTEMIC_VERIFY_ONLINE,
    classify_epistemic_tags,
    format_reference_details,
)
from roundtable.state import Persona


def _persona(**overrides) -> Persona:
    base = {
        "id": "macroeconomics",
        "name": "Macroeconomics",
        "role": "宏观经济专家",
        "worldview": "先看总需求",
        "speaking_style": "结构化",
        "strengths": [],
        "weaknesses": [],
        "catchphrases": [],
        "llm_config": {},
        "rag_expert_name": "macroeconomics",
        "knowledge_scope": "experts",
        "agent_type": "domain_expert",
        "profile": {},
    }
    base.update(overrides)
    return Persona(**base)


def test_classify_epistemic_tags_for_local_corpus():
    tags = classify_epistemic_tags(
        _persona(),
        references=["knowledge/experts/macroeconomics/foo.md"],
        rag_configured=True,
    )
    assert EPISTEMIC_LOCAL_CORPUS in tags
    assert EPISTEMIC_VERIFY_ONLINE in tags


def test_classify_epistemic_tags_for_style_only_persona():
    tags = classify_epistemic_tags(
        _persona(id="buffett", agent_type="persona_inspired", rag_expert_name=None),
        references=[],
        rag_configured=False,
    )
    assert tags == [EPISTEMIC_STYLE_ONLY, EPISTEMIC_VERIFY_ONLINE]


def test_classify_epistemic_tags_for_missing_local_hit():
    tags = classify_epistemic_tags(
        _persona(),
        references=[],
        rag_configured=True,
    )
    assert tags == [EPISTEMIC_NO_LOCAL_HIT, EPISTEMIC_VERIFY_ONLINE]


def test_format_reference_details_includes_kind():
    from rag.chunker import RagChunk

    chunks = [
        RagChunk(
            page_content="Debt cycles matter.",
            metadata={
                "source_file": "knowledge/people/desmond_shum/book/red_roulette.md",
                "source_kind": "book",
            },
        )
    ]
    details = format_reference_details(chunks)
    assert details == [
        {
            "source_file": "knowledge/people/desmond_shum/book/red_roulette.md",
            "kind": "book",
        }
    ]