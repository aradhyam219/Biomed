"""Stable, provider-independent contract for grounded relation extraction.

This module contains only normalized values, a small extractor protocol, and
deterministic validation.  Model/provider integrations may use these types, but
no LangChain or provider-specific object crosses this boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping, Protocol, Sequence

from .entity_extraction import Entity


class RelationExtractor(Protocol):
    """Extract directed relations from text and supplied normalized entities."""

    def extract_relations(
        self, text: str, entities: Sequence[Entity]
    ) -> RelationExtractionResult:
        """Return only relations whose endpoints and evidence refer to the input."""


@dataclass(frozen=True)
class Relation:
    """A directed, evidence-grounded relation between supplied entity IDs.

    ``evidence`` is a verbatim substring of the source text.  ``surface_form``
    optionally preserves the exact relation wording separately from the concise
    normalized ``predicate``.  ``score`` is optional because not every provider
    supplies a calibrated confidence value.
    """

    source: str
    target: str
    predicate: str
    evidence: str
    negated: bool
    surface_form: str | None = None
    score: float | None = None

    @property
    def source_entity_id(self) -> str:
        """Return the source endpoint using its explicit contract terminology."""

        return self.source

    @property
    def target_entity_id(self) -> str:
        """Return the target endpoint using its explicit contract terminology."""

        return self.target

    @property
    def type(self) -> str:
        """Return the predicate under the legacy relation-type spelling."""

        return self.predicate

    def to_dict(self) -> dict[str, Any]:
        """Return the machine-consumable relation representation."""

        return asdict(self)


# This name makes the grounded nature of the value explicit for callers that
# already use ``Relation`` for the legacy GLiREL result contract.
GroundedRelation = Relation


@dataclass(frozen=True)
class RelationExtractionResult:
    """Immutable normalized output from one relation-extraction pass."""

    relations: tuple[Relation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "relations", tuple(self.relations))

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Return a JSON-serializable relation collection."""

        return {"relations": [relation.to_dict() for relation in self.relations]}


class RelationValidationError(ValueError):
    """Raised when a generated relation violates the local output contract."""


class RelationExtractionError(ValueError):
    """Raised when the bounded relation-extraction harness cannot return output."""


def validate_relations(
    text: str,
    entities: Sequence[Entity],
    relations: Sequence[Relation | Mapping[str, Any]],
    *,
    allowed_predicates: Sequence[str] | None = None,
) -> RelationExtractionResult:
    """Validate and deduplicate generated relations without judging truth.

    Validation checks only structural and traceability invariants: endpoint IDs,
    required fields, evidence occurrence, optional surface-form occurrence, an
    optional finite predicate schema, and optional score shape.  It deliberately
    does not decide whether a biologically plausible claim is true.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    entity_ids = _entity_ids(entities)
    predicate_set = _predicate_set(allowed_predicates)
    validated: list[Relation] = []
    seen: set[Relation] = set()

    for index, raw_relation in enumerate(relations):
        relation = _coerce_relation(raw_relation, index)
        _validate_relation(
            relation,
            entity_ids=entity_ids,
            source_text=text,
            allowed_predicates=predicate_set,
        )
        if relation not in seen:
            seen.add(relation)
            validated.append(relation)

    return RelationExtractionResult(tuple(validated))


def _entity_ids(entities: Sequence[Entity]) -> set[str]:
    """Return supplied entity IDs after checking they are usable and unique."""

    entity_ids: set[str] = set()
    for index, entity in enumerate(entities):
        if not isinstance(entity, Entity):
            raise RelationValidationError(
                f"Entity at index {index} is not a normalized Entity value"
            )
        if not isinstance(entity.id, str) or not entity.id.strip():
            raise RelationValidationError(
                f"Entity at index {index} has an empty or invalid ID"
            )
        if entity.id in entity_ids:
            raise RelationValidationError(f"Duplicate supplied entity ID: {entity.id!r}")
        entity_ids.add(entity.id)
    return entity_ids


def _predicate_set(
    allowed_predicates: Sequence[str] | None,
) -> set[str] | None:
    """Normalize an optional finite predicate schema for membership checks."""

    if allowed_predicates is None:
        return None
    predicates = tuple(allowed_predicates)
    if not predicates or any(
        not isinstance(predicate, str) or not predicate.strip()
        for predicate in predicates
    ):
        raise ValueError("Allowed predicates must contain non-empty strings")
    if len(set(predicates)) != len(predicates):
        raise ValueError("Allowed predicates must be unique")
    return set(predicates)


def _coerce_relation(
    raw_relation: Relation | Mapping[str, Any], index: int
) -> Relation:
    """Convert a structured mapping into the stable relation value."""

    if isinstance(raw_relation, Relation):
        return raw_relation
    if not isinstance(raw_relation, Mapping):
        raise RelationValidationError(
            f"Relation at index {index} must be a mapping or Relation value"
        )

    required = ("source", "target", "predicate", "evidence", "negated")
    missing = [field for field in required if field not in raw_relation]
    if missing:
        raise RelationValidationError(
            f"Relation at index {index} is missing required field(s): {', '.join(missing)}"
        )
    allowed = set(required) | {"surface_form", "score"}
    unknown = set(raw_relation) - allowed
    if unknown:
        raise RelationValidationError(
            f"Relation at index {index} has unsupported field(s): {sorted(unknown)}"
        )

    return Relation(
        source=raw_relation["source"],
        target=raw_relation["target"],
        predicate=raw_relation["predicate"],
        evidence=raw_relation["evidence"],
        negated=raw_relation["negated"],
        surface_form=raw_relation.get("surface_form"),
        score=raw_relation.get("score"),
    )


def _validate_relation(
    relation: Relation,
    *,
    entity_ids: set[str],
    source_text: str,
    allowed_predicates: set[str] | None,
) -> None:
    """Validate one relation's structural and source-traceability invariants."""

    for field_name in ("source", "target", "predicate", "evidence"):
        value = getattr(relation, field_name)
        if not isinstance(value, str) or not value.strip():
            raise RelationValidationError(
                f"Relation field {field_name!r} must be a non-empty string"
            )

    if relation.source not in entity_ids:
        raise RelationValidationError(
            f"Relation source entity ID {relation.source!r} is not supplied"
        )
    if relation.target not in entity_ids:
        raise RelationValidationError(
            f"Relation target entity ID {relation.target!r} is not supplied"
        )
    if allowed_predicates is not None and relation.predicate not in allowed_predicates:
        raise RelationValidationError(
            f"Relation predicate {relation.predicate!r} is outside the configured schema"
        )
    if relation.evidence not in source_text:
        raise RelationValidationError(
            "Relation evidence must occur verbatim in the supplied source text"
        )
    if not isinstance(relation.negated, bool):
        raise RelationValidationError("Relation negated field must be a boolean")
    if relation.surface_form is not None:
        if not isinstance(relation.surface_form, str) or not relation.surface_form.strip():
            raise RelationValidationError(
                "Relation surface_form must be a non-empty string when supplied"
            )
        if relation.surface_form not in source_text:
            raise RelationValidationError(
                "Relation surface_form must occur verbatim in the supplied source text"
            )
    if relation.score is not None:
        if isinstance(relation.score, bool) or not isinstance(
            relation.score, (int, float)
        ):
            raise RelationValidationError("Relation score must be numeric when supplied")
        if not isfinite(float(relation.score)) or not 0.0 <= float(relation.score) <= 1.0:
            raise RelationValidationError("Relation score must be between 0 and 1")
