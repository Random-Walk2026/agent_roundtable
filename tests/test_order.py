from roundtable.order import rotate_personas
from roundtable.state import Persona


def _persona(agent_id: str) -> Persona:
    return Persona(
        id=agent_id,
        name=agent_id,
        role=agent_id,
        worldview="",
        speaking_style="",
        strengths=[],
        weaknesses=[],
        catchphrases=[],
        llm_config={},
    )


def test_rotate_personas_offsets_by_round():
    personas = [_persona("a"), _persona("b"), _persona("c")]
    assert [persona.id for persona in rotate_personas(personas, 1)] == ["a", "b", "c"]
    assert [persona.id for persona in rotate_personas(personas, 2)] == ["b", "c", "a"]
    assert [persona.id for persona in rotate_personas(personas, 3)] == ["c", "a", "b"]