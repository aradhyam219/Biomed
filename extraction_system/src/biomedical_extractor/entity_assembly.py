"""Conservative document-local assembly of normalized entity mentions.

This module adds a graph-ready document-local layer over the existing
mention-level :class:`~biomedical_extractor.entity_extraction.Entity` values.
It never changes or replaces those values.  Assembly is deliberately limited
to exact surface repetition and explicit ``full form (ABBR)`` evidence in the
supplied source document; biomedical normalization and cross-document identity
remain outside this boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .entity_extraction import Entity


_PARENTHETICAL_PATTERN = re.compile(r"\((?P<content>[^()\r\n]{1,80})\)")
_ABBREVIATION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./+'-]*\Z")
_MAX_ABBREVIATION_LENGTH = 32


@dataclass(frozen=True)
class DocumentEntity:
    """One document-local node backed by one or more original mentions.

    ``entity_id`` is deterministic within one assembly result.  ``mentions``
    contains the original :class:`Entity` objects, in their input order, so
    source text, offsets, confidence, and mention IDs remain available.
    ``type`` preserves the first mention's source spelling when compatible
    mentions differ only in superficial type casing or whitespace.
    """

    entity_id: str
    label: str
    type: str
    mentions: tuple[Entity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mentions", tuple(self.mentions))

    @property
    def id(self) -> str:
        """Return the document-local ID under the usual entity terminology."""

        return self.entity_id

    @property
    def aliases(self) -> tuple[str, ...]:
        """Return distinct source forms in deterministic mention order."""

        values: list[str] = []
        seen: set[str] = set()
        for mention in self.mentions:
            if mention.text not in seen:
                seen.add(mention.text)
                values.append(mention.text)
        return tuple(values)

    @property
    def mention_ids(self) -> tuple[str, ...]:
        """Return the original mention IDs in the assembled node."""

        return tuple(mention.id for mention in self.mentions)

    def to_dict(self) -> dict[str, Any]:
        """Return a machine-consumable node with its complete mentions."""

        return {
            "id": self.entity_id,
            "label": self.label,
            "type": self.type,
            "aliases": list(self.aliases),
            "mentions": [mention.to_dict() for mention in self.mentions],
        }


@dataclass(frozen=True)
class DocumentEntityAssembly:
    """The assembled nodes and endpoint map for one supplied document."""

    document_entities: tuple[DocumentEntity, ...]
    mention_to_document_entity: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_entities", tuple(self.document_entities))
        object.__setattr__(
            self, "mention_to_document_entity", dict(self.mention_to_document_entity)
        )

    @property
    def entities(self) -> tuple[DocumentEntity, ...]:
        """Return assembled entities under the shorter collection spelling."""

        return self.document_entities

    @property
    def mention_to_document_entity_id(self) -> Mapping[str, str]:
        """Return the mention-ID to document-entity-ID endpoint map."""

        return self.mention_to_document_entity

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable assembly result."""

        return {
            "document_entities": [
                entity.to_dict() for entity in self.document_entities
            ],
            "mention_to_document_entity": dict(self.mention_to_document_entity),
        }


def assemble_document_entities(
    entities: Sequence[Entity], text: str
) -> DocumentEntityAssembly:
    """Assemble safe same-document mention identities without normalization.

    Mentions merge when they have the same deterministic surface/type key, or
    when the source contains a reliable ``full form (ABBR)`` pattern and the
    two corresponding mentions have compatible types.  Surface keys strip and
    collapse whitespace and use Unicode case-folding; no fuzzy matching,
    biomedical synonym knowledge, embeddings, or model calls are used.

    The returned nodes are ordered by the first mention in ``entities`` and
    receive IDs ``doc_e_001``, ``doc_e_002``, and so on.  Every supplied
    mention ID appears exactly once in ``mention_to_document_entity``.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    mentions = tuple(entities)
    _validate_mentions(mentions, text)
    if not mentions:
        return DocumentEntityAssembly((), {})

    parent = list(range(len(mentions)))
    first_index = list(range(len(mentions)))
    display_override: list[tuple[int, str] | None] = [None] * len(mentions)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def merge(
        left: int,
        right: int,
        *,
        abbreviation_index: int | None = None,
        abbreviation_text: str | None = None,
    ) -> int:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            if first_index[left_root] > first_index[right_root]:
                left_root, right_root = right_root, left_root
            parent[right_root] = left_root
            first_index[left_root] = min(
                first_index[left_root], first_index[right_root]
            )
            candidates = [
                candidate
                for candidate in (
                    display_override[left_root],
                    display_override[right_root],
                )
                if candidate is not None
            ]
            display_override[left_root] = min(candidates) if candidates else None
        root = left_root
        if abbreviation_index is not None and abbreviation_text is not None:
            candidate = (abbreviation_index, abbreviation_text)
            current = display_override[root]
            if current is None or candidate < current:
                display_override[root] = candidate
        return root

    exact_groups: dict[tuple[str, str], int] = {}
    for index, mention in enumerate(mentions):
        key = (_type_key(mention.type), _surface_key(mention.text))
        previous = exact_groups.get(key)
        if previous is None:
            exact_groups[key] = index
        else:
            merge(previous, index)

    for full_index, abbreviation_index in _explicit_alias_pairs(text, mentions):
        merge(
            full_index,
            abbreviation_index,
            abbreviation_index=abbreviation_index,
            abbreviation_text=mentions[abbreviation_index].text,
        )

    grouped: dict[int, list[Entity]] = {}
    group_first_index: dict[int, int] = {}
    for index, mention in enumerate(mentions):
        root = find(index)
        grouped.setdefault(root, []).append(mention)
        group_first_index.setdefault(root, index)

    ordered_roots = sorted(grouped, key=group_first_index.__getitem__)
    document_entities: list[DocumentEntity] = []
    mention_to_document_entity: dict[str, str] = {}
    for number, group_root in enumerate(ordered_roots, start=1):
        group = grouped[group_root]
        document_id = f"doc_e_{number:03d}"
        label = display_override[group_root]
        document_entity = DocumentEntity(
            entity_id=document_id,
            label=label[1] if label is not None else group[0].text,
            type=group[0].type,
            mentions=tuple(group),
        )
        document_entities.append(document_entity)
        for mention in group:
            mention_to_document_entity[mention.id] = document_id

    return DocumentEntityAssembly(
        tuple(document_entities), mention_to_document_entity
    )


def _validate_mentions(mentions: Sequence[Entity], text: str) -> None:
    """Validate mention identity and source-span invariants before grouping."""

    seen_ids: set[str] = set()
    for index, mention in enumerate(mentions):
        if not isinstance(mention, Entity):
            raise TypeError(
                f"Entity at index {index} must be a normalized Entity value"
            )
        if not isinstance(mention.id, str) or not mention.id.strip():
            raise ValueError(f"Entity at index {index} has an empty or invalid ID")
        if mention.id in seen_ids:
            raise ValueError(f"Duplicate mention entity ID: {mention.id!r}")
        seen_ids.add(mention.id)
        if not isinstance(mention.type, str) or not mention.type.strip():
            raise ValueError(f"Entity {mention.id!r} has an empty or invalid type")
        if not isinstance(mention.text, str):
            raise ValueError(f"Entity {mention.id!r} has non-string mention text")
        if not 0 <= mention.start < mention.end <= len(text):
            raise ValueError(
                f"Entity {mention.id!r} has an invalid span: "
                f"[{mention.start}, {mention.end})"
            )
        if text[mention.start : mention.end] != mention.text:
            raise ValueError(
                f"Entity {mention.id!r} does not resolve to its source text"
            )


def _explicit_alias_pairs(
    text: str, mentions: Sequence[Entity]
) -> tuple[tuple[int, int], ...]:
    """Find unambiguous source-defined full-form/abbreviation mention pairs."""

    pairs: list[tuple[int, int]] = []
    for match in _PARENTHETICAL_PATTERN.finditer(text):
        content = match.group("content").strip()
        if not _looks_like_abbreviation(content):
            continue

        open_index = match.start()
        close_index = match.end() - 1
        abbreviation_candidates = [
            index
            for index, mention in enumerate(mentions)
            if open_index < mention.start
            and mention.end <= close_index
            and _surface_key(mention.text) == _surface_key(content)
        ]
        abbreviation_types = {
            _type_key(mentions[index].type) for index in abbreviation_candidates
        }
        if len(abbreviation_types) != 1:
            continue
        abbreviation_index = min(
            abbreviation_candidates,
            key=lambda index: (mentions[index].start, index),
            default=None,
        )
        if abbreviation_index is None:
            continue

        full_form_candidates = [
            index
            for index, mention in enumerate(mentions)
            if mention.end <= open_index
            and not text[mention.end : open_index].strip()
        ]
        if not full_form_candidates:
            continue
        nearest_end = max(mentions[index].end for index in full_form_candidates)
        full_form_candidates = [
            index
            for index in full_form_candidates
            if mentions[index].end == nearest_end
        ]
        full_form_types = {
            _type_key(mentions[index].type) for index in full_form_candidates
        }
        if full_form_types != abbreviation_types or len(full_form_types) != 1:
            continue
        unique_full_spans = {
            (mentions[index].start, mentions[index].end)
            for index in full_form_candidates
        }
        if len(unique_full_spans) != 1:
            continue
        full_form_index = min(full_form_candidates)
        pairs.append((full_form_index, abbreviation_index))
    return tuple(pairs)


def _looks_like_abbreviation(value: str) -> bool:
    """Accept only a compact, conventional-looking parenthetical token."""

    if not 2 <= len(value) <= _MAX_ABBREVIATION_LENGTH:
        return False
    if _ABBREVIATION_PATTERN.fullmatch(value) is None:
        return False
    return (
        any(character.isalpha() for character in value)
        and any(character.isupper() or character.isdigit() for character in value)
    )


def _surface_key(value: str) -> str:
    """Normalize only superficial whitespace and casing for identity checks."""

    return " ".join(value.split()).casefold()


def _type_key(value: str) -> str:
    """Normalize type casing/spacing without mapping distinct biomedical types."""

    return " ".join(value.split()).casefold()


__all__ = [
    "DocumentEntity",
    "DocumentEntityAssembly",
    "assemble_document_entities",
]
