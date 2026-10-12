"""Shared normalized entity values and the model-independent NER boundary."""

from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Protocol


class EntityExtractor(Protocol):
    """Small contract for extracting normalized entities from source text."""

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Return entities whose offsets refer to the supplied text."""


@dataclass(frozen=True)
class Entity:
    """Normalized entity with a stable ID and half-open character offsets."""

    id: str
    text: str
    type: str
    start: int
    end: int
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the machine-consumable entity representation."""

        return asdict(self)
