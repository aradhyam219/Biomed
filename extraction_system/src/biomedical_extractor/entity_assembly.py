"""Conservative document-local assembly of normalized entity mentions.

This module adds a graph-ready document-local layer over the existing
mention-level :class:`~biomedical_extractor.entity_extraction.Entity` values.
It never changes or replaces those values. Assembly is deliberately limited
to exact surface repetition and explicit ``full form (ABBR)`` source evidence,
including a same-document exact full-form mention when NER fragments the
construction; biomedical normalization and cross-document identity remain
outside this boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .entity_extraction import Entity


_PARENTHETICAL_PATTERN = re.compile(r"\((?P<content>[^()\r\n]{1,80})\)")
_ABBREVIATION_PATTERN = re.compile(r"[\w][\w./+'’–—-]*\Z", re.UNICODE)
_LONG_FORM_TOKEN_PATTERN = re.compile(r"\b[\w][\w’'./+–—-]*", re.UNICODE)
_LONG_FORM_BOUNDARY_PATTERN = re.compile(r"[.!?;:]\s")
_SINGLE_LETTER_ALTERNATIVES_PATTERN = re.compile(
    r"\b[A-Za-z0-9]\s+(?:and|or)\s+[A-Za-z0-9]\b", re.IGNORECASE
)
_MAX_ABBREVIATION_LENGTH = 32
_MAX_LONG_FORM_WORDS = 12


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

    Mentions merge when they have the same deterministic surface/type key, when
    the source contains a reliable ``full form (ABBR)`` alignment, or when the
    literal source long form has an exact compatible mention elsewhere in the
    same document. Surface keys strip and collapse whitespace and use Unicode
    case-folding; no fuzzy matching, biomedical synonym knowledge, embeddings,
    or model calls are used.

    The returned nodes are ordered by the first mention in ``entities`` and
    receive IDs ``doc_e_001``, ``doc_e_002``, and so on.  Every supplied
    mention ID appears exactly once in ``mention_to_document_entity``.
    """

    return _assemble_document_entities(entities, text)


def _assemble_document_entities(
    entities: Sequence[Entity],
    text: str,
    *,
    verified_identity_pairs: Sequence[tuple[str, str]] = (),
) -> DocumentEntityAssembly:
    """Assemble mentions, optionally applying validated verifier decisions.

    ``verified_identity_pairs`` is an internal pipeline input produced only
    after :func:`validate_explicit_identity_result` accepts grounded decisions.
    The public assembly function remains deterministic and provider-independent.
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

    for full_index, abbreviation_index in _explicit_same_document_recovery_pairs(
        text, mentions
    ):
        merge(
            full_index,
            abbreviation_index,
            abbreviation_index=abbreviation_index,
            abbreviation_text=mentions[abbreviation_index].text,
        )

    mention_index_by_id = {mention.id: index for index, mention in enumerate(mentions)}
    for pair in verified_identity_pairs:
        if len(pair) != 2 or pair[0] not in mention_index_by_id or pair[1] not in mention_index_by_id:
            raise ValueError("Verified identity pairs must reference supplied mention IDs")
        left = mention_index_by_id[pair[0]]
        right = mention_index_by_id[pair[1]]
        if _type_key(mentions[left].type) != _type_key(mentions[right].type):
            raise ValueError("Verified identity pairs cannot combine incompatible types")
        merge(
            left,
            right,
            abbreviation_index=right,
            abbreviation_text=mentions[right].text,
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
    """Find source-defined pairs with deterministic long-form recovery.

    The parenthetical abbreviation is matched against a bounded suffix of the
    source text immediately before the opening parenthesis.  That suffix may
    contain several same-type NER mentions, which lets a fragmented long form
    participate in one identity group without manufacturing a new mention.
    """

    pairs: list[tuple[int, int]] = []
    for match, content, abbreviation_groups in _explicit_abbreviation_occurrences(
        text, mentions
    ):
        if len(abbreviation_groups) != 1:
            continue
        abbreviation_type, abbreviation_candidates = next(
            iter(abbreviation_groups.items())
        )
        abbreviation_index = min(
            abbreviation_candidates, key=lambda index: (mentions[index].start, index)
        )

        long_form_span = _recover_long_form_span(text, match.start(), content)
        if long_form_span is None:
            continue
        long_form_start, long_form_end = _expand_long_form_start(
            text,
            long_form_span[0],
            long_form_span[1],
            mentions,
            {abbreviation_type},
        )
        full_form_candidates = [
            index
            for index, mention in enumerate(mentions)
            if long_form_start <= mention.start
            and mention.end <= long_form_end
            and _type_key(mention.type) == abbreviation_type
        ]
        for full_form_index in full_form_candidates:
            pairs.append((full_form_index, abbreviation_index))
    return tuple(pairs)


def _explicit_same_document_recovery_pairs(
    text: str, mentions: Sequence[Entity]
) -> tuple[tuple[int, int], ...]:
    """Attach a parenthetical abbreviation to an exact full form mentioned elsewhere.

    The source abbreviation must lexically align to one unambiguous literal
    long form, and the complete same-type surface form must already exist as a
    normalized mention. This never manufactures or edits a mention.
    """

    pairs: list[tuple[int, int]] = []
    for match, content, abbreviation_groups in _explicit_abbreviation_occurrences(
        text, mentions
    ):
        if len(abbreviation_groups) != 1:
            continue
        abbreviation_type, abbreviation_indices = next(
            iter(abbreviation_groups.items())
        )
        source_end = len(text[: match.start()].rstrip())
        if _SINGLE_LETTER_ALTERNATIVES_PATTERN.search(
            text[max(0, source_end - 16) : source_end]
        ):
            continue
        exact_mentions = [
            index
            for index, mention in enumerate(mentions)
            if _type_key(mention.type) == abbreviation_type
            and source_end >= len(mention.text)
            and _surface_key(
                text[source_end - len(mention.text) : source_end]
            )
            == _surface_key(mention.text)
            and _abbreviation_aligns(
                content,
                text[source_end - len(mention.text) : source_end],
            )
            and not _is_superficial_single_word_match(
                content,
                text[source_end - len(mention.text) : source_end],
            )
        ]
        if not exact_mentions:
            continue
        abbreviation_index = min(
            abbreviation_indices,
            key=lambda index: (mentions[index].start, index),
        )
        pairs.extend((index, abbreviation_index) for index in exact_mentions)
    return tuple(pairs)


def _explicit_abbreviation_occurrences(
    text: str, mentions: Sequence[Entity]
) -> tuple[tuple[re.Match[str], str, dict[str, tuple[int, ...]]], ...]:
    """Return type-specific normalized mentions of explicit parenthetical tokens."""

    occurrences: list[tuple[re.Match[str], str, dict[str, tuple[int, ...]]]] = []
    for match in _PARENTHETICAL_PATTERN.finditer(text):
        content = match.group("content").strip()
        if not _looks_like_abbreviation(content):
            continue
        open_index = match.start()
        close_index = match.end() - 1
        candidates = [
            index
            for index, mention in enumerate(mentions)
            if open_index < mention.start
            and mention.end <= close_index
            and _surface_key(mention.text) == _surface_key(content)
        ]
        by_type: dict[str, list[int]] = {}
        for index in candidates:
            by_type.setdefault(_type_key(mentions[index].type), []).append(index)
        groups: dict[str, tuple[int, ...]] = {}
        for entity_type, indices in by_type.items():
            spans = {(mentions[index].start, mentions[index].end) for index in indices}
            if len(spans) == 1:
                groups[entity_type] = tuple(indices)
        if groups:
            occurrences.append((match, content, groups))
    return tuple(occurrences)


def _expand_long_form_start(
    text: str,
    long_form_start: int,
    long_form_end: int,
    mentions: Sequence[Entity],
    compatible_types: set[str],
) -> tuple[int, int]:
    """Include only adjacent same-type NER fragments before an aligned suffix."""

    current_start = long_form_start
    while True:
        candidates = [
            mention
            for mention in mentions
            if _type_key(mention.type) in compatible_types
            and mention.end <= current_start
            and not text[mention.end:current_start].strip()
        ]
        if not candidates:
            return current_start, long_form_end
        preceding = max(candidates, key=lambda mention: (mention.end, mention.start))
        current_start = preceding.start


def _looks_like_abbreviation(value: str) -> bool:
    """Accept only a compact, conventional-looking parenthetical token.

    Requiring either a digit or multiple uppercase letters prevents ordinary
    parenthetical prose such as ``(control)`` or ``(Mice)`` from becoming an
    alias candidate.  The source alignment below supplies the stronger guard.
    """

    if not 2 <= len(value) <= _MAX_ABBREVIATION_LENGTH:
        return False
    if _ABBREVIATION_PATTERN.fullmatch(value) is None:
        return False
    if not any(character.isalpha() for character in value):
        return False
    if any(character.isdigit() for character in value) or sum(
        character.isupper() for character in value
    ) >= 2:
        return True
    # Compact CamelCase forms such as Cbl are conventional abbreviations even
    # when only their initial is uppercase.  Alignment still has to validate
    # the source construction, so ordinary capitalized prose is not enough.
    return (
        len(value) <= 6
        and value[0].isupper()
        and any(character.islower() for character in value[1:])
    )


def _recover_long_form_span(
    text: str, abbreviation_start: int, abbreviation: str
) -> tuple[int, int] | None:
    """Recover one high-confidence long-form source span before ``(ABBR)``."""

    source_before_parenthesis = text[:abbreviation_start]
    long_form_end = len(source_before_parenthesis.rstrip())
    tokens = list(_LONG_FORM_TOKEN_PATTERN.finditer(source_before_parenthesis))
    if not tokens or tokens[-1].end() != long_form_end:
        return None

    max_words = min(
        _MAX_LONG_FORM_WORDS,
        max(3, len([character for character in abbreviation if character.isalnum()]) + 5),
    )
    candidates: list[tuple[int, int, int]] = []
    first_token_index = max(0, len(tokens) - max_words)
    for token_index in range(first_token_index, len(tokens)):
        start = tokens[token_index].start()
        candidate = text[start:long_form_end]
        if _LONG_FORM_BOUNDARY_PATTERN.search(candidate):
            continue
        if _SINGLE_LETTER_ALTERNATIVES_PATTERN.search(candidate):
            continue
        if _is_superficial_single_word_match(abbreviation, candidate):
            continue
        if _abbreviation_aligns(abbreviation, candidate):
            candidates.append((start, long_form_end, len(tokens) - token_index))

    if not candidates:
        return None

    # Prefer the longest aligned phrase, but refuse a tie that would make the
    # source construction ambiguous.  This keeps false-negative merging safer
    # than choosing one of several plausible preceding phrases.
    longest_word_count = max(candidate[2] for candidate in candidates)
    longest = [candidate for candidate in candidates if candidate[2] == longest_word_count]
    if len(longest) != 1:
        return None
    if _SINGLE_LETTER_ALTERNATIVES_PATTERN.search(
        text[max(0, longest[0][0] - 16) : long_form_end]
    ):
        return None
    return longest[0][0], longest[0][1]


def _abbreviation_aligns(abbreviation: str, long_form: str) -> bool:
    """Return whether abbreviation characters align in order with the phrase."""

    short = [character.casefold() for character in abbreviation if character.isalnum()]
    long = [character.casefold() for character in long_form]
    if len(short) < 2 or len(short) > len(long):
        return False

    matched_positions: list[int] = []
    long_index = len(long) - 1
    for short_character in reversed(short):
        while long_index >= 0 and long[long_index] != short_character:
            long_index -= 1
        if long_index < 0:
            return False
        matched_positions.append(long_index)
        long_index -= 1
    matched_positions.reverse()

    # The first aligned character must occur in the first recovered word.
    # Subsequent characters may occur inside hyphenated or ordinary words (for
    # example, KNTC1 aligns with kinetochore-associated protein 1), which is
    # part of the compact Schwartz-Hearst-style signal rather than synonym
    # knowledge.
    if _surface_key(abbreviation) == _surface_key(long_form):
        return True
    first_word_end = next(
        (index for index, character in enumerate(long_form) if character.isspace()),
        len(long_form),
    )
    return matched_positions[0] < first_word_end


def _is_superficial_single_word_match(abbreviation: str, long_form: str) -> bool:
    """Reject a capitalized parenthetical copy of one ordinary source word."""

    words = long_form.split()
    short = "".join(character for character in abbreviation.casefold() if character.isalnum())
    if len(words) != 1 or not short:
        return False
    word = "".join(character for character in words[0].casefold() if character.isalnum())
    return word.startswith(short) and len(word) - len(short) <= 2


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
