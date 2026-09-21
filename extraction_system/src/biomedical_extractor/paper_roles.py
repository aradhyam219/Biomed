"""Provider-independent grounded role metadata for unconnected graph nodes.

Paper roles explain why a genuinely unconnected document-local entity appears
in one supplied paper.  They are optional node metadata, never graph edges or
ontology assertions.  This module owns the small domain contract and source
grounding checks; provider-specific structured-output code lives separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence, TYPE_CHECKING

from .entity_extraction import Entity


PAPER_ROLE_CATEGORIES = ("substantive", "contextual")


class PaperRoleValidationError(ValueError):
    """Raised when role metadata violates the local grounded-output contract."""


@dataclass(frozen=True)
class PaperRole:
    """A concise, evidence-backed explanation of one entity's paper role."""

    category: str
    paragraphs: tuple[str, ...]
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.category not in PAPER_ROLE_CATEGORIES:
            raise PaperRoleValidationError(
                "Paper-role category must be one of: "
                f"{', '.join(PAPER_ROLE_CATEGORIES)}"
            )
        paragraphs = tuple(self.paragraphs)
        evidence = tuple(self.evidence)
        if not 1 <= len(paragraphs) <= 2:
            raise PaperRoleValidationError(
                "Paper-role paragraphs must contain one or two values"
            )
        if any(not isinstance(value, str) or not value.strip() for value in paragraphs):
            raise PaperRoleValidationError(
                "Paper-role paragraphs must contain non-empty strings"
            )
        if not evidence or any(
            not isinstance(value, str) or not value.strip() for value in evidence
        ):
            raise PaperRoleValidationError(
                "Paper-role evidence must contain non-empty strings"
            )
        object.__setattr__(self, "paragraphs", paragraphs)
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON representation used under a graph node."""

        return {
            "category": self.category,
            "paragraphs": list(self.paragraphs),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class PaperRoleTarget:
    """The complete local input context for one requested unconnected node."""

    node_id: str
    label: str
    type: str
    mentions: tuple[Entity, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id.strip():
            raise PaperRoleValidationError("Paper-role target ID must be non-empty")
        if not isinstance(self.label, str) or not self.label.strip():
            raise PaperRoleValidationError("Paper-role target label must be non-empty")
        if not isinstance(self.type, str) or not self.type.strip():
            raise PaperRoleValidationError("Paper-role target type must be non-empty")
        mentions = tuple(self.mentions)
        if any(not isinstance(mention, Entity) for mention in mentions):
            raise PaperRoleValidationError(
                "Paper-role targets must contain normalized Entity mentions"
            )
        object.__setattr__(self, "mentions", mentions)

    def to_dict(self) -> dict[str, Any]:
        """Return the target with every original source mention."""

        return {
            "node_id": self.node_id,
            "label": self.label,
            "type": self.type,
            "mentions": [mention.to_dict() for mention in self.mentions],
        }


@dataclass(frozen=True)
class PaperRoleRecord:
    """One independently addressable node ID and its role metadata."""

    node_id: str
    role: PaperRole

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id.strip():
            raise PaperRoleValidationError("Paper-role record ID must be non-empty")
        if not isinstance(self.role, PaperRole):
            raise PaperRoleValidationError(
                "Paper-role record must contain a PaperRole value"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return one role record without provider-specific objects."""

        return {"node_id": self.node_id, "paper_role": self.role.to_dict()}


@dataclass(frozen=True)
class PaperRoleExtractionResult:
    """The provider-independent result for one bounded paper-level call."""

    records: tuple[PaperRoleRecord, ...]

    def __post_init__(self) -> None:
        records = tuple(self.records)
        if any(not isinstance(record, PaperRoleRecord) for record in records):
            raise PaperRoleValidationError(
                "Paper-role results must contain PaperRoleRecord values"
            )
        if len({record.node_id for record in records}) != len(records):
            raise PaperRoleValidationError("Paper-role result contains duplicate node IDs")
        object.__setattr__(self, "records", records)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible role result."""

        return {"roles": [record.to_dict() for record in self.records]}


class PaperRoleExtractor(Protocol):
    """Provider-independent seam for one bounded paper-level role call."""

    def extract_roles(
        self,
        title: str,
        text: str,
        targets: Sequence[PaperRoleTarget],
    ) -> PaperRoleExtractionResult:
        """Return one grounded role record for every requested target."""


def validate_paper_role_result(
    text: str,
    targets: Sequence[PaperRoleTarget],
    result: PaperRoleExtractionResult,
) -> PaperRoleExtractionResult:
    """Validate IDs, categories, paragraph bounds, and verbatim evidence."""

    if not isinstance(text, str):
        raise TypeError("paper-role source text must be a string")
    if not isinstance(result, PaperRoleExtractionResult):
        raise PaperRoleValidationError(
            "Paper-role provider must return PaperRoleExtractionResult"
        )

    target_values = tuple(targets)
    if any(not isinstance(target, PaperRoleTarget) for target in target_values):
        raise PaperRoleValidationError(
            "Paper-role targets must contain PaperRoleTarget values"
        )
    target_by_id = {target.node_id: target for target in target_values}
    if len(target_by_id) != len(target_values):
        raise PaperRoleValidationError("Paper-role targets contain duplicate node IDs")

    records_by_id = {record.node_id: record for record in result.records}
    unknown = sorted(set(records_by_id) - set(target_by_id))
    if unknown:
        raise PaperRoleValidationError(
            f"Paper-role result contains unknown node ID(s): {unknown!r}"
        )
    missing = sorted(set(target_by_id) - set(records_by_id))
    if missing:
        raise PaperRoleValidationError(
            f"Paper-role result is missing node ID(s): {missing!r}"
        )

    for record in result.records:
        target = target_by_id[record.node_id]
        if _is_species_type(target.type) and record.role.category != "contextual":
            raise PaperRoleValidationError(
                f"Species target {record.node_id!r} must use contextual paper role"
            )
        for evidence in record.role.evidence:
            if evidence not in text:
                raise PaperRoleValidationError(
                    f"Paper-role evidence for {record.node_id!r} is not a verbatim "
                    "source substring"
                )

    # Reorder provider output into the deterministic target order.
    return PaperRoleExtractionResult(
        tuple(records_by_id[target.node_id] for target in target_values)
    )


def apply_paper_roles(
    graph: Any,
    text: str,
    result: PaperRoleExtractionResult,
) -> Any:
    """Attach roles only to genuinely unconnected graph nodes.

    The local import avoids a module cycle while keeping graph construction
    independent from any provider implementation.
    """

    from dataclasses import replace

    from .graph import GraphResult

    if not isinstance(graph, GraphResult):
        raise TypeError("graph must be a GraphResult")
    unconnected = graph.unconnected_nodes
    targets = tuple(
        PaperRoleTarget(
            node_id=node.id,
            label=node.label,
            type=node.type,
            mentions=node.mentions,
        )
        for node in unconnected
    )
    validated = validate_paper_role_result(text, targets, result)
    role_by_id = {record.node_id: record.role for record in validated.records}
    nodes = tuple(
        replace(node, paper_role=role_by_id[node.id])
        if node.id in role_by_id
        else node
        for node in graph.nodes
    )
    return GraphResult(document=graph.document, nodes=nodes, edges=graph.edges)


def _is_species_type(value: str) -> bool:
    """Recognize only presentation/domain spellings of the current Species type."""

    normalized = "".join(character for character in value.casefold() if character.isalnum())
    return normalized in {"species", "organism"}


if TYPE_CHECKING:
    from .graph import GraphResult


__all__ = [
    "PAPER_ROLE_CATEGORIES",
    "PaperRole",
    "PaperRoleExtractor",
    "PaperRoleExtractionResult",
    "PaperRoleRecord",
    "PaperRoleTarget",
    "PaperRoleValidationError",
    "apply_paper_roles",
    "validate_paper_role_result",
]
