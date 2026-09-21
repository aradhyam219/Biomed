"""Typed graph-ready application values and deterministic serialization.

The graph boundary consumes normalized document-local entities and grounded
relations.  It does not know about model output, perform entity normalization,
or infer relation semantics; its only transformation is remapping mention
endpoints to assembled document-local node IDs and preserving source evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from math import isfinite
from typing import Any, Sequence

from .entity_assembly import DocumentEntity, DocumentEntityAssembly
from .entity_extraction import Entity
from .paper_roles import PaperRole
from .relation_extraction import Relation, RelationExtractionResult


_NAMING_ONLY_PATTERN = re.compile(
    r"(?:abbreviat(?:e|ed|ion)|acronym|alias|synonym|"
    r"alternative\s+(?:name|label|term)|(?:also\s+)?known\s+as|"
    r"same\s+(?:entity|name|thing)|full\s+form|short\s+form|"
    r"refers?\s+to|denot(?:e|es)|called|named)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GraphDocument:
    """Stable identity for the source document represented by a graph."""

    id: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Graph document ID must be a non-empty string")

    def to_dict(self) -> dict[str, str]:
        """Return the document metadata in the graph contract."""

        return {"id": self.id}


@dataclass(frozen=True)
class GraphNode:
    """One graph node backed by one assembled document-local entity."""

    id: str
    label: str
    type: str
    mentions: tuple[Entity, ...]
    aliases: tuple[str, ...] = ()
    paper_role: PaperRole | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mentions", tuple(self.mentions))
        object.__setattr__(self, "aliases", tuple(self.aliases))

    def to_dict(self) -> dict[str, Any]:
        """Return the node and every constituent source mention."""

        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "aliases": list(self.aliases),
            "mentions": [mention.to_dict() for mention in self.mentions],
            **(
                {"paper_role": self.paper_role.to_dict()}
                if self.paper_role is not None
                else {}
            ),
        }


@dataclass(frozen=True)
class GraphEvidence:
    """One source-evidence record with the grounded relation semantics it carries."""

    text: str
    assertion: str
    intervention: str | None = None
    effects: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    surface_form: str | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        for field_name in ("text", "assertion"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Graph evidence {field_name} must be a non-empty string"
                )
        if self.intervention is not None and (
            not isinstance(self.intervention, str) or not self.intervention.strip()
        ):
            raise ValueError(
                "Graph evidence intervention must be non-empty when supplied"
            )
        for field_name in ("effects", "context"):
            values = getattr(self, field_name)
            if not isinstance(values, (list, tuple)):
                raise ValueError(
                    f"Graph evidence {field_name} must be a sequence of strings"
                )
            normalized = tuple(values)
            if any(
                not isinstance(value, str) or not value.strip()
                for value in normalized
            ):
                raise ValueError(
                    f"Graph evidence {field_name} must contain non-empty strings"
                )
            object.__setattr__(self, field_name, normalized)
        if self.surface_form is not None and (
            not isinstance(self.surface_form, str) or not self.surface_form.strip()
        ):
            raise ValueError(
                "Graph evidence surface_form must be non-empty when supplied"
            )
        if self.score is not None:
            if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
                raise ValueError("Graph evidence score must be numeric when supplied")
            if not isfinite(float(self.score)) or not 0.0 <= float(self.score) <= 1.0:
                raise ValueError("Graph evidence score must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        """Return evidence without discarding optional grounded relation fields."""

        return {
            "text": self.text,
            "assertion": self.assertion,
            "intervention": self.intervention,
            "effects": list(self.effects),
            "context": list(self.context),
            "surface_form": self.surface_form,
            "score": self.score,
        }


@dataclass(frozen=True)
class GraphEdge:
    """One conceptual directed relation with one or more evidence records."""

    id: str
    source: str
    target: str
    predicate: str
    negated: bool
    evidence: tuple[GraphEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if not self.evidence:
            raise ValueError("Graph edges require at least one evidence record")
        if any(not isinstance(item, GraphEvidence) for item in self.evidence):
            raise TypeError("Graph edge evidence must contain GraphEvidence values")

    def to_dict(self) -> dict[str, Any]:
        """Return the directed edge and all contributing evidence."""

        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "predicate": self.predicate,
            "negated": self.negated,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class GraphResult:
    """Deterministic application-level graph data for one source document."""

    document: GraphDocument
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))

    def to_dict(self) -> dict[str, Any]:
        """Return the frontend-neutral graph JSON-compatible structure."""

        return {
            "document": self.document.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the graph with stable key ordering and no model objects."""

        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    @property
    def unconnected_nodes(self) -> tuple[GraphNode, ...]:
        """Return nodes with degree zero after final edge cleanup."""

        connected_ids = {
            endpoint
            for edge in self.edges
            for endpoint in (edge.source, edge.target)
        }
        return tuple(node for node in self.nodes if node.id not in connected_ids)


class GraphConstructionError(ValueError):
    """Raised when graph conversion would violate endpoint or evidence integrity."""


def build_graph_result(
    document_id: str,
    assembly: DocumentEntityAssembly,
    relations: Sequence[Relation] | RelationExtractionResult,
) -> GraphResult:
    """Build a graph from assembled entities and grounded mention relations.

    Document-local node IDs come directly from ``assembly``.  Relations are
    grouped only by their exact remapped endpoints, predicate, and negation
    state.  Grounded relations are retained after endpoint remapping, including
    relations whose distinct mention endpoints assemble to the same node.
    """

    document = GraphDocument(document_id)
    nodes, mention_map = _build_nodes_and_validate_assembly(assembly)
    relation_values = _relation_values(relations)

    aggregated: dict[tuple[str, str, str, bool], list[GraphEvidence]] = {}
    for index, relation in enumerate(relation_values):
        _validate_relation_shape(relation, index)
        if relation.source not in mention_map:
            raise GraphConstructionError(
                f"Relation at index {index} source mention ID {relation.source!r} "
                "has no assembled document-entity mapping"
            )
        if relation.target not in mention_map:
            raise GraphConstructionError(
                f"Relation at index {index} target mention ID {relation.target!r} "
                "has no assembled document-entity mapping"
            )

        source_node = mention_map[relation.source]
        target_node = mention_map[relation.target]
        if (
            source_node == target_node
            and _is_alias_or_naming_only_relation(relation)
        ):
            continue
        key = (source_node, target_node, relation.predicate, relation.negated)
        aggregated.setdefault(key, []).append(
            GraphEvidence(
                text=relation.evidence,
                assertion=relation.assertion,
                intervention=relation.intervention,
                effects=relation.effects,
                context=relation.context,
                surface_form=relation.surface_form,
                score=relation.score,
            )
        )

    edges: list[GraphEdge] = []
    for index, (source, target, predicate, negated) in enumerate(
        sorted(aggregated), start=1
    ):
        edges.append(
            GraphEdge(
                id=f"doc_r_{index:03d}",
                source=source,
                target=target,
                predicate=predicate,
                negated=negated,
                evidence=tuple(
                    sorted(
                        aggregated[(source, target, predicate, negated)],
                        key=_evidence_sort_key,
                    )
                ),
            )
        )
    return GraphResult(document=document, nodes=nodes, edges=tuple(edges))


def _relation_values(
    relations: Sequence[Relation] | RelationExtractionResult,
) -> tuple[Relation, ...]:
    """Normalize the two existing grounded-relation collection shapes."""

    if isinstance(relations, RelationExtractionResult):
        return tuple(relations.relations)
    return tuple(relations)


def _build_nodes_and_validate_assembly(
    assembly: DocumentEntityAssembly,
) -> tuple[tuple[GraphNode, ...], dict[str, str]]:
    """Create nodes while checking that assembly identity is complete."""

    if not isinstance(assembly, DocumentEntityAssembly):
        raise TypeError("assembly must be a DocumentEntityAssembly")

    node_ids: set[str] = set()
    mention_ids: set[str] = set()
    nodes: list[GraphNode] = []
    for index, document_entity in enumerate(assembly.document_entities):
        if not isinstance(document_entity, DocumentEntity):
            raise GraphConstructionError(
                f"Assembled entity at index {index} is not a DocumentEntity"
            )
        if document_entity.entity_id in node_ids:
            raise GraphConstructionError(
                f"Duplicate assembled document-entity ID: {document_entity.entity_id!r}"
            )
        node_ids.add(document_entity.entity_id)
        for mention in document_entity.mentions:
            if not isinstance(mention, Entity):
                raise GraphConstructionError(
                    f"Node {document_entity.entity_id!r} contains a non-Entity mention"
                )
            if mention.id in mention_ids:
                raise GraphConstructionError(
                    f"Mention ID {mention.id!r} occurs in multiple graph nodes"
                )
            mention_ids.add(mention.id)

        nodes.append(
            GraphNode(
                id=document_entity.entity_id,
                label=document_entity.label,
                type=document_entity.type,
                aliases=document_entity.aliases,
                mentions=document_entity.mentions,
            )
        )

    mention_map = dict(assembly.mention_to_document_entity)
    extra_mentions = set(mention_map) - mention_ids
    if extra_mentions:
        raise GraphConstructionError(
            "Assembly mapping contains unknown mention ID(s): "
            f"{sorted(extra_mentions)!r}"
        )
    missing_mentions = mention_ids - set(mention_map)
    if missing_mentions:
        raise GraphConstructionError(
            "Assembly mapping is missing mention ID(s): "
            f"{sorted(missing_mentions)!r}"
        )
    invalid_nodes = set(mention_map.values()) - node_ids
    if invalid_nodes:
        raise GraphConstructionError(
            "Assembly mapping references unknown document-entity ID(s): "
            f"{sorted(invalid_nodes)!r}"
        )
    for document_entity in assembly.document_entities:
        for mention in document_entity.mentions:
            if mention_map[mention.id] != document_entity.entity_id:
                raise GraphConstructionError(
                    f"Assembly mapping places mention {mention.id!r} outside "
                    f"its node {document_entity.entity_id!r}"
                )
    return tuple(nodes), mention_map


def _validate_relation_shape(relation: Relation, index: int) -> None:
    """Check fields needed to produce a valid evidence-bearing graph edge."""

    if not isinstance(relation, Relation):
        raise GraphConstructionError(
            f"Relation at index {index} must be a grounded Relation value"
        )
    for field_name in ("source", "target", "predicate", "assertion", "evidence"):
        value = getattr(relation, field_name)
        if not isinstance(value, str) or not value.strip():
            raise GraphConstructionError(
                f"Relation at index {index} field {field_name!r} must be non-empty"
            )
    if not isinstance(relation.negated, bool):
        raise GraphConstructionError(
            f"Relation at index {index} negated field must be boolean"
        )


def _is_alias_or_naming_only_relation(relation: Relation) -> bool:
    """Identify naming-only predicates without suppressing biological self-edges."""

    # The predicate is the safest semantic signal: evidence or assertion prose
    # can mention an alias while carrying a separate biological claim.  Only a
    # naming predicate is suppressed, and only after endpoint identity collapse.
    return bool(_NAMING_ONLY_PATTERN.search(relation.predicate))


def _evidence_sort_key(
    evidence: GraphEvidence,
) -> tuple[str, str, str, tuple[str, ...], tuple[str, ...], str, bool, float]:
    """Order evidence independently of provider/list arrival order."""

    return (
        evidence.text,
        evidence.assertion,
        evidence.intervention or "",
        evidence.effects,
        evidence.context,
        evidence.surface_form or "",
        evidence.score is None,
        float(evidence.score) if evidence.score is not None else 0.0,
    )


__all__ = [
    "GraphConstructionError",
    "GraphDocument",
    "GraphEdge",
    "GraphEvidence",
    "GraphNode",
    "GraphResult",
    "build_graph_result",
]
