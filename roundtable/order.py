from __future__ import annotations

from roundtable.state import Persona


def rotate_personas(personas: list[Persona], round_number: int) -> list[Persona]:
    if not personas:
        return []
    offset = (max(round_number, 1) - 1) % len(personas)
    if offset == 0:
        return list(personas)
    return personas[offset:] + personas[:offset]