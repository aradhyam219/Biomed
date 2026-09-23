"""Provider-independent contracts for explicit document-local identity checks.

This module discovers only bounded parenthetical constructions that deterministic
assembly could not resolve, then validates a finite verifier response against
the exact mentions and source construction supplied to it. It does not perform
general alias discovery or biomedical normalization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from .entity_assembly import (
    DocumentEntityAssembly,
    _LONG_FORM_TOKEN_PATTERN,
    _SINGLE_LETTER_ALTERNATIVES_PATTERN,
    _explicit_abbreviation_occurrences,
    _looks_like_abbreviation,
    _recover_long_form_span,
    _surface_key,
    _type_key,
)
from .entity_extraction import Entity


_EXPLICIT_SUFFIX_PATTERN = re.compile(r"\((?P<abbreviation>[^()\r\n]+)\)\Z")
_CONSTRUCTION_BOUNDARY_PATTERN = re.compile(r"[.!?;:\n]")
_MENTION_FRAGMENT_GAP_PATTERN = re.compile(r"^[\s–—-]*\Z")
_MAX_CONSTRUCTION_WORDS = 12


class ExplicitIdentityValidationError(ValueError):
    """Raised when a verifier result is incomplete, unsupported, or ungrounded."""


@dataclass(frozen=True)
class ExplicitIdentityCandidate:
    """One locally bounded source construction and its compatible NER mentions."""

    candidate_id: str
    construction: str
    construction_start: int
    construction_end: int
    long_form: str
    abbreviation: str
    long_form_group_id: str
    abbreviation_group_id: str
    long_form_mentions: tuple[Entity, ...]
    abbreviation_mentions: tuple[Entity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "long_form_mentions", tuple(self.long_form_mentions))
        object.__setattr__(
            self, "abbreviation_mentions", tuple(self.abbreviation_mentions)
        )

    @property
    def mention_ids(self) -> tuple[str, ...]:
        """Return all mention IDs that the verifier may consider for this pair."""

        return tuple(
            mention.id
            for mention in (*self.long_form_mentions, *self.abbreviation_mentions)
        )


@dataclass(frozen=True)
class ExplicitIdentityDecision:
    """One finite construction decision tied to a candidate and its mention IDs."""

    candidate_id: str
    mention_ids: tuple[str, ...]
    decision: str
    evidence: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "mention_ids", tuple(self.mention_ids))


@dataclass(frozen=True)
class ExplicitIdentityResult:
    """Provider-independent result containing one decision per candidate."""

    decisions: tuple[ExplicitIdentityDecision, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decisions", tuple(self.decisions))


class ExplicitIdentityVerifier(Protocol):
    """Verify only supplied unresolved source-defined identity candidates."""

    def verify_explicit_identities(
        self, text: str, candidates: Sequence[ExplicitIdentityCandidate]
    ) -> ExplicitIdentityResult:
        """Return a validated finite decision set for one supplied document."""


def find_unresolved_explicit_identity_candidates(
    entities: Sequence[Entity],
    text: str,
    deterministic_assembly: DocumentEntityAssembly,
) -> tuple[ExplicitIdentityCandidate, ...]:
    """Find eligible unresolved ``Long Form (ABBR)`` candidates conservatively.

    Candidates require a normalized abbreviation mention, at least one
    compatible mention in a bounded multiword source construction, one
    unambiguous long-form document group, and two distinct deterministic
    document groups. Ordinary parenthetical prose and competing same-type
    interpretations are left out.
    """

    mentions = tuple(entities)
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not mentions or not deterministic_assembly.document_entities:
        return ()

    candidates: list[ExplicitIdentityCandidate] = []
    for match, abbreviation, abbreviation_groups in _explicit_abbreviation_occurrences(
        text, mentions
    ):
        for abbreviation_type, abbreviation_indices in abbreviation_groups.items():
            recovered = _recover_long_form_span(text, match.start(), abbreviation)
            if recovered is None:
                context_start = _bounded_construction_start(text, match.start())
                context_end = len(text[: match.start()].rstrip())
                context_mentions = [
                    index
                    for index, mention in enumerate(mentions)
                    if context_start <= mention.start
                    and mention.end <= context_end
                    and _type_key(mention.type) == abbreviation_type
                ]
                if not context_mentions:
                    continue
                first_mention = min(
                    (mentions[index] for index in context_mentions),
                    key=lambda mention: (mention.start, mention.end),
                )
                long_form_start = _candidate_construction_start(
                    text, context_start, first_mention
                )
            else:
                long_form_start = recovered[0]
            long_form_end = len(text[: match.start()].rstrip())
            if long_form_start >= long_form_end:
                continue

            long_form = text[long_form_start:long_form_end]
            if len(tuple(_LONG_FORM_TOKEN_PATTERN.finditer(long_form))) < 2:
                continue
            if _SINGLE_LETTER_ALTERNATIVES_PATTERN.search(long_form):
                continue

            long_form_indices = [
                index
                for index, mention in enumerate(mentions)
                if long_form_start <= mention.start
                and mention.end <= long_form_end
                and _type_key(mention.type) == abbreviation_type
            ]
            if not long_form_indices:
                continue

            long_form_group_ids = {
                deterministic_assembly.mention_to_document_entity.get(
                    mentions[index].id
                )
                for index in long_form_indices
            }
            long_form_group_ids.discard(None)
            if not long_form_group_ids or (
                len(long_form_group_ids) > 1
                and not _is_one_contiguous_fragment_run(
                    text,
                    tuple(mentions[index] for index in long_form_indices),
                )
            ):
                continue
            long_form_group_id = "+".join(sorted(long_form_group_ids))

            local_abbreviation_indices = [
                index
                for index in abbreviation_indices
                if _type_key(mentions[index].type) == abbreviation_type
            ]
            if not local_abbreviation_indices:
                continue
            abbreviation_group_ids = {
                deterministic_assembly.mention_to_document_entity.get(
                    mentions[index].id
                )
                for index in local_abbreviation_indices
            }
            abbreviation_group_ids.discard(None)
            if len(abbreviation_group_ids) != 1:
                continue
            abbreviation_group_id = next(iter(abbreviation_group_ids))
            if long_form_group_id == abbreviation_group_id:
                continue

            construction = text[long_form_start : match.end()]
            if not _looks_like_abbreviation(abbreviation):
                continue
            candidates.append(
                ExplicitIdentityCandidate(
                    candidate_id=f"identity_{len(candidates) + 1:03d}",
                    construction=construction,
                    construction_start=long_form_start,
                    construction_end=match.end(),
                    long_form=long_form,
                    abbreviation=abbreviation,
                    long_form_group_id=long_form_group_id,
                    abbreviation_group_id=abbreviation_group_id,
                    long_form_mentions=tuple(
                        mentions[index] for index in long_form_indices
                    ),
                    abbreviation_mentions=tuple(
                        mentions[index] for index in local_abbreviation_indices
                    ),
                )
            )
    return tuple(candidates)


def validate_explicit_identity_result(
    text: str,
    candidates: Sequence[ExplicitIdentityCandidate],
    result: ExplicitIdentityResult,
) -> tuple[tuple[str, str], ...]:
    """Validate the complete result and return only grounded merge pairs.

    Any malformed, unknown, duplicated, missing, incompatible, or ungrounded
    record invalidates the result as a whole. ``not_identity_construction``
    and ``uncertain`` are valid decisions and produce no merge.
    """

    if not isinstance(text, str):
        raise TypeError("Explicit identity source text must be a string")
    candidate_values = tuple(candidates)
    if not isinstance(result, ExplicitIdentityResult):
        raise ExplicitIdentityValidationError(
            "Explicit identity verifier must return ExplicitIdentityResult"
        )
    expected_by_id = {candidate.candidate_id: candidate for candidate in candidate_values}
    if len(expected_by_id) != len(candidate_values):
        raise ExplicitIdentityValidationError("Identity candidates contain duplicate IDs")

    decisions_by_id: dict[str, ExplicitIdentityDecision] = {}
    for decision in result.decisions:
        if not isinstance(decision, ExplicitIdentityDecision):
            raise ExplicitIdentityValidationError(
                "Explicit identity result contains an invalid decision value"
            )
        if decision.candidate_id not in expected_by_id:
            raise ExplicitIdentityValidationError(
                f"Explicit identity result has unknown candidate ID {decision.candidate_id!r}"
            )
        if decision.candidate_id in decisions_by_id:
            raise ExplicitIdentityValidationError(
                f"Explicit identity result duplicates candidate {decision.candidate_id!r}"
            )
        decisions_by_id[decision.candidate_id] = decision
    missing = set(expected_by_id) - set(decisions_by_id)
    if missing:
        raise ExplicitIdentityValidationError(
            f"Explicit identity result is missing candidate(s): {sorted(missing)!r}"
        )

    pairs: list[tuple[str, str]] = []
    for candidate_id, candidate in expected_by_id.items():
        decision = decisions_by_id[candidate_id]
        expected_mentions = candidate.mention_ids
        if len(expected_mentions) != len(set(expected_mentions)):
            raise ExplicitIdentityValidationError(
                f"Identity candidate {candidate_id!r} has duplicate mention IDs"
            )
        if (
            len(decision.mention_ids) != len(set(decision.mention_ids))
            or set(decision.mention_ids) != set(expected_mentions)
        ):
            unknown = set(decision.mention_ids) - set(expected_mentions)
            missing_mentions = set(expected_mentions) - set(decision.mention_ids)
            raise ExplicitIdentityValidationError(
                f"Identity decision for {candidate_id!r} has invalid mention IDs; "
                f"unknown={sorted(unknown)!r}, missing={sorted(missing_mentions)!r}"
            )
        if decision.decision not in {
            "same_identity_construction",
            "not_identity_construction",
            "uncertain",
        }:
            raise ExplicitIdentityValidationError(
                f"Identity decision for {candidate_id!r} has unsupported value"
            )
        _validate_candidate_grounding(text, candidate)
        if decision.decision != "same_identity_construction":
            continue
        if not isinstance(decision.evidence, str) or not decision.evidence:
            raise ExplicitIdentityValidationError(
                f"Affirmative identity decision for {candidate_id!r} needs evidence"
            )
        if (
            decision.evidence != candidate.construction
            or text[candidate.construction_start : candidate.construction_end]
            != decision.evidence
        ):
            raise ExplicitIdentityValidationError(
                f"Affirmative identity evidence for {candidate_id!r} is not the exact source construction"
            )
        long_form_types = {_type_key(mention.type) for mention in candidate.long_form_mentions}
        abbreviation_types = {
            _type_key(mention.type) for mention in candidate.abbreviation_mentions
        }
        if (
            not long_form_types
            or long_form_types != abbreviation_types
            or len(long_form_types) != 1
        ):
            raise ExplicitIdentityValidationError(
                f"Identity candidate {candidate_id!r} contains incompatible types"
            )
        pairs.extend(
            (long_form_mention.id, abbreviation_mention.id)
            for long_form_mention in candidate.long_form_mentions
            for abbreviation_mention in candidate.abbreviation_mentions
        )
    return tuple(pairs)


def _validate_candidate_grounding(
    text: str, candidate: ExplicitIdentityCandidate
) -> None:
    """Ensure candidate offsets, source form, and mention groups are consistent."""

    if not 0 <= candidate.construction_start < candidate.construction_end <= len(text):
        raise ExplicitIdentityValidationError(
            f"Identity candidate {candidate.candidate_id!r} has invalid source offsets"
        )
    if text[candidate.construction_start : candidate.construction_end] != candidate.construction:
        raise ExplicitIdentityValidationError(
            f"Identity candidate {candidate.candidate_id!r} is not verbatim source text"
        )
    suffix = _EXPLICIT_SUFFIX_PATTERN.search(candidate.construction)
    if suffix is None or _surface_key(suffix.group("abbreviation")) != _surface_key(
        candidate.abbreviation
    ):
        raise ExplicitIdentityValidationError(
            f"Identity candidate {candidate.candidate_id!r} is not an explicit parenthetical construction"
        )
    open_offset = suffix.start()
    long_form_start = candidate.construction_start
    long_form_end = candidate.construction_start + open_offset
    if text[long_form_start:long_form_end].rstrip() != candidate.long_form:
        raise ExplicitIdentityValidationError(
            f"Identity candidate {candidate.candidate_id!r} has inconsistent long-form text"
        )
    if (
        candidate.long_form_group_id == candidate.abbreviation_group_id
        or not candidate.long_form_mentions
        or not candidate.abbreviation_mentions
        or _SINGLE_LETTER_ALTERNATIVES_PATTERN.search(candidate.long_form)
    ):
        raise ExplicitIdentityValidationError(
            f"Identity candidate {candidate.candidate_id!r} is empty, resolved, or ambiguous"
        )
    if len(tuple(_LONG_FORM_TOKEN_PATTERN.finditer(candidate.long_form))) < 2:
        raise ExplicitIdentityValidationError(
            f"Identity candidate {candidate.candidate_id!r} is not a bounded long form"
        )
    for mention in candidate.long_form_mentions:
        if (
            text[mention.start : mention.end] != mention.text
            or not long_form_start <= mention.start < mention.end <= long_form_end
        ):
            raise ExplicitIdentityValidationError(
                f"Long-form mention {mention.id!r} is outside its candidate construction"
            )
    for mention in candidate.abbreviation_mentions:
        if (
            text[mention.start : mention.end] != mention.text
            or not long_form_end < mention.start < mention.end < candidate.construction_end
            or _surface_key(mention.text) != _surface_key(candidate.abbreviation)
        ):
            raise ExplicitIdentityValidationError(
                f"Abbreviation mention {mention.id!r} is outside its candidate construction"
            )


def _bounded_construction_start(text: str, parenthetical_start: int) -> int:
    """Return the start of a sentence-bounded, twelve-token source suffix."""

    prior = text[:parenthetical_start]
    boundaries = [match.end() for match in _CONSTRUCTION_BOUNDARY_PATTERN.finditer(prior)]
    sentence_start = boundaries[-1] if boundaries else 0
    region = prior[sentence_start:]
    tokens = tuple(_LONG_FORM_TOKEN_PATTERN.finditer(region))
    if not tokens:
        return parenthetical_start
    token = tokens[-min(len(tokens), _MAX_CONSTRUCTION_WORDS)]
    return sentence_start + token.start()


def _candidate_construction_start(
    text: str, context_start: int, first_mention: Entity
) -> int:
    """Include at most two unannotated prefix words for a fragmented long form.

    A complete one-token mention remains the entire candidate long form. This
    prevents unrelated sentence context from making a single name look like a
    wider alias construction.
    """

    if len(tuple(_LONG_FORM_TOKEN_PATTERN.finditer(first_mention.text))) < 2:
        return first_mention.start
    prefix = text[context_start : first_mention.start]
    tokens = tuple(_LONG_FORM_TOKEN_PATTERN.finditer(prefix))
    if not tokens:
        return first_mention.start
    return context_start + tokens[-min(len(tokens), 2)].start()


def _is_one_contiguous_fragment_run(
    text: str, mentions: Sequence[Entity]
) -> bool:
    """Accept fragmented NER only when its distinct spans form one local phrase."""

    spans = sorted({(mention.start, mention.end) for mention in mentions})
    if len(spans) < 2:
        return False
    for (_, previous_end), (next_start, _) in zip(spans, spans[1:]):
        if previous_end > next_start or not _MENTION_FRAGMENT_GAP_PATTERN.fullmatch(
            text[previous_end:next_start]
        ):
            return False
    return True


__all__ = [
    "ExplicitIdentityCandidate",
    "ExplicitIdentityDecision",
    "ExplicitIdentityResult",
    "ExplicitIdentityValidationError",
    "ExplicitIdentityVerifier",
    "find_unresolved_explicit_identity_candidates",
    "validate_explicit_identity_result",
]
