"""Target-domain gold-pilot selection, validation, and evaluation contracts.

This module owns the small human-annotation packet for the nine science-team
papers.  It consumes the canonical text and optional model predictions produced
by reconnaissance, but never copies a prediction into ``entities``.  Gold
entities use sentence-relative, half-open character offsets so a reviewer can
annotate one item without editing the canonical source text.  The validator can
resolve those offsets back to the canonical paper whenever that cache is
available.

The same validated package is the input contract for the isolated HunFlair2
training runtime.  Incomplete examples are useful review material, but they are
not training data; overlapping gold spans are reported and are rejected only
when converting to Flair's non-nested sequence-tagging representation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .entity_extraction import Entity
from .ner_evaluation import canonical_predicted_type
from .ner_reconnaissance import (
    AGREEMENT_AIONER_ONLY,
    AGREEMENT_BOUNDARY,
    AGREEMENT_CROSS_TYPE,
    AGREEMENT_HUNFLAIR2_ONLY,
    AGREEMENT_TYPE,
    TargetPaper,
    align_entity_predictions,
    sentence_spans,
)


PILOT_SCHEMA_VERSION = 1
PILOT_PACKAGE_KIND = "target_domain_gold_pilot"
PILOT_SELECTION_VERSION = "target-domain-pilot-v1"
PILOT_ANNOTATION_CONVENTION = (
    "Python/Unicode character offsets relative to the selected sentence, "
    "half-open [start, end); sentence text is unchanged from canonical source."
)

APPROVED_ENTITY_TYPES = (
    "GeneOrGeneProduct",
    "DiseaseOrPhenotypicFeature",
    "ChemicalEntity",
    "OrganismTaxon",
    "CellLine",
    "SequenceVariant",
)
APPROVED_ENTITY_TYPE_SET = frozenset(APPROVED_ENTITY_TYPES)

# HunFlair2's released tagger has five output labels.  SequenceVariant remains
# valid target gold, but a future training run must stop explicitly if a human
# annotates one because a flat five-label HunFlair2 head cannot represent it.
HUNFLAIR2_TRAINING_LABEL_BY_TYPE = {
    "GeneOrGeneProduct": "Gene",
    "DiseaseOrPhenotypicFeature": "Disease",
    "ChemicalEntity": "Chemical",
    "OrganismTaxon": "Species",
    "CellLine": "CellLine",
}

HARD_CASE_CATEGORIES = frozenset(
    {
        AGREEMENT_AIONER_ONLY,
        AGREEMENT_BOUNDARY,
        AGREEMENT_CROSS_TYPE,
        AGREEMENT_HUNFLAIR2_ONLY,
        AGREEMENT_TYPE,
    }
)
HARD_CASE_PRIORITY = {
    AGREEMENT_TYPE: 0,
    AGREEMENT_BOUNDARY: 1,
    AGREEMENT_CROSS_TYPE: 2,
    AGREEMENT_HUNFLAIR2_ONLY: 3,
    AGREEMENT_AIONER_ONLY: 4,
}

# This assignment was chosen before annotation: one full-text and one
# abstract-only paper are held out, while the train group retains both coverage
# modes and the longer target-domain articles.  It is intentionally explicit so
# a later code change cannot silently move the held-out papers.
DEFAULT_PAPER_SPLIT = {
    "PMID:27370646": "train",
    "PMID:27172794": "train",
    "PMID:33652126": "train",
    "PMID:31324362": "train",
    "PMCID:PMC8605525": "test",
    "PMCID:PMC11824863": "train",
    "PMID:38569671": "test",
    "PMCID:PMC10444909": "dev",
    "PMCID:PMC10770459": "train",
}
SPLITS = ("train", "dev", "test")


class AnnotationValidationError(ValueError):
    """Raised when a target annotation package violates its data contract."""


class TrainingCompatibilityError(ValueError):
    """Raised when valid target gold cannot be represented by flat HunFlair2."""


@dataclass(frozen=True)
class AnnotationValidation:
    """Validation summary including explicit overlap diagnostics."""

    item_count: int
    complete_count: int
    incomplete_count: int
    entity_count: int
    entity_counts_by_type: Mapping[str, int]
    overlaps: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable validation summary."""

        return {
            "item_count": self.item_count,
            "complete_count": self.complete_count,
            "incomplete_count": self.incomplete_count,
            "entity_count": self.entity_count,
            "entity_counts_by_type": dict(sorted(self.entity_counts_by_type.items())),
            "overlap_count": len(self.overlaps),
            "overlaps": [dict(value) for value in self.overlaps],
        }


def _canonical_json(value: Any) -> str:
    """Serialize one value deterministically for identity and ranking hashes."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    """Return the SHA-256 of deterministic UTF-8 JSON."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash one file without loading it all into memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_prediction_type(entity_type: str) -> str | None:
    """Resolve a local or official model label to the pilot taxonomy."""

    if entity_type in APPROVED_ENTITY_TYPE_SET:
        return entity_type
    return canonical_predicted_type(entity_type)


def _entity_sort_key(entity: Entity) -> tuple[int, int, str, str]:
    """Return stable ordering for model suggestions."""

    return entity.start, entity.end, entity.type, entity.text


def _prediction_payload(entity: Entity, sentence_start: int) -> dict[str, Any]:
    """Serialize one model suggestion with both source and local offsets."""

    return {
        "start": entity.start,
        "end": entity.end,
        "relative_start": entity.start - sentence_start,
        "relative_end": entity.end - sentence_start,
        "text": entity.text,
        "type": entity.type,
        "canonical_type": _canonical_prediction_type(entity.type),
        "score": entity.score,
    }


def _entities_for_sentence(
    entities: Sequence[Entity],
    start: int,
    end: int,
) -> tuple[Entity, ...]:
    """Return predictions that touch one complete source sentence."""

    return tuple(
        sorted(
            (
                entity
                for entity in entities
                if max(start, entity.start) < min(end, entity.end)
            ),
            key=_entity_sort_key,
        )
    )


def _is_low_information_section(section: str) -> bool:
    """Identify obvious non-prose regions that should not consume the sample."""

    normalized = section.casefold()
    return any(
        marker in normalized
        for marker in (
            "reference",
            "bibliograph",
            "acknowledg",
            "author affiliation",
            "copyright",
            "license",
        )
    )


def _sentence_key(paper_id: str, start: int, end: int, text: str) -> str:
    """Return a stable identity for one canonical sentence."""

    return sha256_json(
        {
            "paper_id": paper_id,
            "sentence_start": start,
            "sentence_end": end,
            "text": text,
        }
    )


def _example_id(sentence_key: str) -> str:
    """Return the compact reviewer-facing example identifier."""

    return f"targetpilot-{sentence_key[:16]}"


def _candidate_rank(candidate: Mapping[str, Any]) -> str:
    """Rank one candidate without using model confidence or annotation outcome."""

    return sha256_json(
        {
            "selection_version": PILOT_SELECTION_VERSION,
            "paper_id": candidate["paper_id"],
            "sentence_start": candidate["sentence_start"],
            "sentence_end": candidate["sentence_end"],
            "text": candidate["sentence_text"],
        }
    )


def _coverage_order(candidates: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Round-robin deterministic candidates across source sections."""

    by_section: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_section[str(candidate["section"])].append(candidate)
    for values in by_section.values():
        values.sort(key=_candidate_rank)
    ordered: list[Mapping[str, Any]] = []
    index = 0
    sections = sorted(by_section)
    while True:
        progressed = False
        for section in sections:
            values = by_section[section]
            if index < len(values):
                ordered.append(values[index])
                progressed = True
        if not progressed:
            break
        index += 1
    return ordered


def _review_category_index(
    review_candidates: Iterable[Mapping[str, Any]] | None,
) -> dict[tuple[str, int, int], set[str]]:
    """Index tracked reconnaissance review examples by canonical sentence."""

    result: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    for candidate in review_candidates or ():
        sentence = candidate.get("sentence")
        if not isinstance(sentence, Mapping):
            continue
        paper_id = str(candidate.get("paper_id", ""))
        try:
            start = int(sentence["start"])
            end = int(sentence["end"])
        except (KeyError, TypeError, ValueError):
            continue
        category = str(candidate.get("category", ""))
        if category in HARD_CASE_CATEGORIES:
            result[(paper_id, start, end)].add(category)
    return result


def _coerce_review_entities(value: Any) -> tuple[Entity, ...]:
    """Convert one review-packet prediction field to local entities."""

    values = value if isinstance(value, list) else ([] if value is None else [value])
    entities: list[Entity] = []
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping):
            continue
        try:
            start = int(raw["start"])
            end = int(raw["end"])
            text = str(raw["text"])
            entity_type = str(raw["type"])
        except (KeyError, TypeError, ValueError):
            continue
        score = raw.get("score")
        entities.append(
            Entity(
                id=str(raw.get("id", f"review-{index}")),
                text=text,
                type=entity_type,
                start=start,
                end=end,
                score=None if score is None else float(score),
            )
        )
    return tuple(sorted(entities, key=_entity_sort_key))


def review_packet_prediction_index(
    review_candidates: Iterable[Mapping[str, Any]] | None,
) -> dict[tuple[str, int, int], dict[str, tuple[Entity, ...]]]:
    """Index partial AIONER/HunFlair2 suggestions from a tracked review packet."""

    result: dict[tuple[str, int, int], dict[str, tuple[Entity, ...]]] = {}
    for candidate in review_candidates or ():
        sentence = candidate.get("sentence")
        if not isinstance(sentence, Mapping):
            continue
        try:
            key = (
                str(candidate["paper_id"]),
                int(sentence["start"]),
                int(sentence["end"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        result[key] = {
            "AIONER": _coerce_review_entities(candidate.get("aioner_prediction")),
            "HunFlair2": _coerce_review_entities(
                candidate.get("hunflair2_prediction")
            ),
        }
    return result


def _paper_feature_payload(
    paper: TargetPaper,
    *,
    prediction_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Serialize only pre-annotation paper facts for the split manifest."""

    payload = {
        "paper_id": paper.paper_id,
        "pmid": paper.pmid,
        "pmcid": paper.pmcid,
        "acquisition_mode": paper.acquisition_mode,
        "character_count": len(paper.text),
        "sentence_count": paper.sentence_count,
        "section_availability": list(paper.section_availability),
        "source_checksum": paper.source_checksum,
        "source_text_sha256": paper.text_checksum,
    }
    if prediction_counts is not None:
        payload["reconnaissance_prediction_counts"] = dict(
            sorted(prediction_counts.items())
        )
    return payload


def build_split_manifest(
    papers: Sequence[TargetPaper],
    *,
    paper_split: Mapping[str, str] | None = None,
    prediction_counts: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, Any]:
    """Build the frozen paper-level split manifest before human annotation."""

    assignment = dict(DEFAULT_PAPER_SPLIT if paper_split is None else paper_split)
    paper_ids = {paper.paper_id for paper in papers}
    if set(assignment) != paper_ids:
        missing = sorted(paper_ids - set(assignment))
        extra = sorted(set(assignment) - paper_ids)
        raise ValueError(f"Paper split coverage mismatch: missing={missing}, extra={extra}")
    if set(assignment.values()) != set(SPLITS):
        raise ValueError("Paper split manifest must contain train, dev, and test")
    counts = Counter(assignment.values())
    if counts != Counter({"train": 6, "dev": 1, "test": 2}):
        raise ValueError(f"Expected 6/1/2 paper split, got {dict(counts)}")
    return {
        "schema_version": PILOT_SCHEMA_VERSION,
        "manifest_kind": "target_domain_pilot_paper_split",
        "assignment_version": PILOT_SELECTION_VERSION,
        "assignment_basis": (
            "Frozen before annotation using canonical article length, full-text versus "
            "abstract-only coverage, section variety, and pre-annotation reconnaissance "
            "coverage; no human gold or eventual test outcome was used."
        ),
        "paper_splits": dict(sorted(assignment.items())),
        "papers": [
            {
                **_paper_feature_payload(
                    paper,
                    prediction_counts=(prediction_counts or {}).get(paper.paper_id),
                ),
                "split": assignment[paper.paper_id],
            }
            for paper in sorted(papers, key=lambda value: value.paper_id)
        ],
    }


def load_review_packet(path: Path) -> tuple[Mapping[str, Any], ...]:
    """Load tracked review examples without treating them as gold."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        raise ValueError("Review packet examples must be an array")
    return tuple(value for value in examples if isinstance(value, Mapping))


def build_pilot_package(
    papers: Sequence[TargetPaper],
    hunflair2_predictions: Mapping[str, Sequence[Entity]],
    *,
    aioner_predictions: Mapping[str, Sequence[Entity]] | None = None,
    review_candidates: Iterable[Mapping[str, Any]] | None = None,
    paper_split: Mapping[str, str] | None = None,
    target_per_paper: int = 20,
    source_manifest_sha256: str | None = None,
    source_manifest_path: str | None = None,
) -> dict[str, Any]:
    """Select a representative, sentence-complete annotation package.

    Every paper is sampled independently.  Approximately 30% of each paper's
    capacity is allocated to disagreement/hard cases, approximately 35% to
    entity-rich stable prose, and the remainder to deterministic section-
    coverage sampling.  Short papers simply contribute all suitable sentences.
    """

    if target_per_paper <= 0:
        raise ValueError("target_per_paper must be positive")
    split_manifest = build_split_manifest(papers, paper_split=paper_split)
    assignment = split_manifest["paper_splits"]
    review_index = _review_category_index(review_candidates)
    review_predictions = review_packet_prediction_index(review_candidates)
    aioner_map = aioner_predictions or {}
    aioner_is_available = aioner_predictions is not None

    selected_items: list[dict[str, Any]] = []
    composition_by_paper: dict[str, Counter[str]] = {}
    candidate_counts_by_paper: dict[str, int] = {}
    for paper in papers:
        paper_aioner = tuple(aioner_map.get(paper.paper_id, ()))
        paper_hunflair2 = tuple(hunflair2_predictions.get(paper.paper_id, ()))
        paper_aioner_known = aioner_is_available and paper.paper_id in aioner_map
        candidates: list[dict[str, Any]] = []
        for sentence_index, (start, end) in enumerate(sentence_spans(paper.text)):
            section = paper.section_for_offset(start)
            sentence_text = paper.text[start:end]
            if _is_low_information_section(section):
                continue
            key = (paper.paper_id, start, end)
            h_entities = _entities_for_sentence(paper_hunflair2, start, end)
            a_entities = (
                _entities_for_sentence(paper_aioner, start, end)
                if paper_aioner_known
                else review_predictions.get(key, {}).get("AIONER", ())
            )
            review_categories = review_index.get(key, set())
            model_categories: set[str] = set(review_categories)
            if paper_aioner_known:
                model_categories.update(
                    alignment.category
                    for alignment in align_entity_predictions(a_entities, h_entities)
                    if alignment.category in HARD_CASE_CATEGORIES
                )
            hard_categories = sorted(
                model_categories & HARD_CASE_CATEGORIES,
                key=lambda value: (HARD_CASE_PRIORITY.get(value, 99), value),
            )
            hard = bool(hard_categories)
            stable_rich = len(h_entities) >= 2 and not hard
            if hard:
                group = "A"
                reason = f"model_disagreement:{hard_categories[0]}"
            elif stable_rich:
                group = "B"
                reason = "entity_rich_stable_predictions"
            else:
                group = "C"
                reason = "deterministic_general_coverage"
            candidates.append(
                {
                    "paper_id": paper.paper_id,
                    "pmid": paper.pmid,
                    "pmcid": paper.pmcid,
                    "section": section,
                    "sentence_index": sentence_index,
                    "sentence_start": start,
                    "sentence_end": end,
                    "sentence_text": sentence_text,
                    "group": group,
                    "sampling_reason": reason,
                    "hard_case_categories": hard_categories,
                    "aioner_predictions": [
                        _prediction_payload(entity, start) for entity in a_entities
                    ],
                    "hunflair2_predictions": [
                        _prediction_payload(entity, start) for entity in h_entities
                    ],
                }
            )
        candidate_counts_by_paper[paper.paper_id] = len(candidates)
        quotas = {
            "A": max(1, round(target_per_paper * 0.30)),
            "B": max(1, round(target_per_paper * 0.35)),
        }
        selected: list[Mapping[str, Any]] = []
        selected_keys: set[str] = set()
        for group in ("A", "B"):
            group_candidates = sorted(
                (item for item in candidates if item["group"] == group),
                key=_candidate_rank,
            )
            for item in group_candidates[: quotas[group]]:
                selected.append(item)
                selected_keys.add(
                    _sentence_key(
                        paper.paper_id,
                        int(item["sentence_start"]),
                        int(item["sentence_end"]),
                        str(item["sentence_text"]),
                    )
                )
        remaining = [
            item
            for item in candidates
            if _sentence_key(
                paper.paper_id,
                int(item["sentence_start"]),
                int(item["sentence_end"]),
                str(item["sentence_text"]),
            )
            not in selected_keys
        ]
        for item in _coverage_order(remaining):
            if len(selected) >= min(target_per_paper, len(candidates)):
                break
            selected.append(item)
            selected_keys.add(
                _sentence_key(
                    paper.paper_id,
                    int(item["sentence_start"]),
                    int(item["sentence_end"]),
                    str(item["sentence_text"]),
                )
            )
        selected.sort(key=lambda item: int(item["sentence_index"]))
        composition = Counter(str(item["group"]) for item in selected)
        composition_by_paper[paper.paper_id] = composition
        for item in selected:
            start = int(item["sentence_start"])
            end = int(item["sentence_end"])
            sentence_text = str(item["sentence_text"])
            sentence_key = _sentence_key(paper.paper_id, start, end, sentence_text)
            selected_items.append(
                {
                    "example_id": _example_id(sentence_key),
                    "paper_id": paper.paper_id,
                    "pmid": paper.pmid,
                    "pmcid": paper.pmcid,
                    "split": assignment[paper.paper_id],
                    "section": item["section"],
                    "sentence_id": f"s{int(item['sentence_index']) + 1:04d}",
                    "sentence_key": sentence_key,
                    "sentence_start": start,
                    "sentence_end": end,
                    "sentence_text": sentence_text,
                    "text": sentence_text,
                    "source_checksum": paper.source_checksum,
                    "source_text_sha256": paper.text_checksum,
                    "sampling_group": item["group"],
                    "sampling_reason": item["sampling_reason"],
                    "hard_case_categories": list(item["hard_case_categories"]),
                    "prediction_context": {
                        "hunflair2": list(item["hunflair2_predictions"]),
                        "aioner": list(item["aioner_predictions"]),
                    },
                    # This is the only gold field.  It is deliberately empty
                    # even when prediction context is present.
                    "entities": [],
                    "annotation_status": "unreviewed",
                    "annotation_complete": False,
                }
            )

    selected_items.sort(key=lambda item: (str(item["paper_id"]), int(item["sentence_start"])))
    selection_counts = Counter(str(item["sampling_group"]) for item in selected_items)
    reason_counts = Counter(str(item["sampling_reason"]) for item in selected_items)
    return {
        "schema_version": PILOT_SCHEMA_VERSION,
        "package_kind": PILOT_PACKAGE_KIND,
        "selection_version": PILOT_SELECTION_VERSION,
        "status": "awaiting_human_gold_annotations",
        "gold_policy": (
            "Predictions are reviewer context only. Human annotation is exhaustive "
            "for each selected sentence; an item enters training only when "
            "annotation_complete is true."
        ),
        "annotation_convention": PILOT_ANNOTATION_CONVENTION,
        "approved_entity_types": list(APPROVED_ENTITY_TYPES),
        "canonical_source": {
            "manifest_path": source_manifest_path,
            "manifest_sha256": source_manifest_sha256,
            "paper_count": len(papers),
            "papers": [
                _paper_feature_payload(paper)
                | {"split": assignment[paper.paper_id]}
                for paper in sorted(papers, key=lambda value: value.paper_id)
            ],
        },
        "paper_split": split_manifest,
        "selection": {
            "target_per_paper": target_per_paper,
            "selected_count": len(selected_items),
            "candidate_count_by_paper": dict(sorted(candidate_counts_by_paper.items())),
            "selected_count_by_paper": dict(
                sorted(
                    Counter(str(item["paper_id"]) for item in selected_items).items()
                )
            ),
            "composition_counts": dict(sorted(selection_counts.items())),
            "sampling_reason_counts": dict(sorted(reason_counts.items())),
            "composition_by_paper": {
                paper_id: dict(sorted(counter.items()))
                for paper_id, counter in sorted(composition_by_paper.items())
            },
            "method": (
                "Per-paper quota: 30% disagreement/hard cases, 35% stable entity-rich "
                "sentences, remainder deterministic section round-robin; low-information "
                "reference/boilerplate sections are excluded."
            ),
        },
        "examples": selected_items,
    }


def _require_int(value: Any, field: str) -> int:
    """Read a real integer field, rejecting booleans."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise AnnotationValidationError(f"{field} must be an integer")
    return value


def _paper_map(
    canonical_papers: Sequence[TargetPaper] | Mapping[str, TargetPaper] | None,
) -> dict[str, TargetPaper]:
    """Normalize optional canonical source records for provenance checks."""

    if canonical_papers is None:
        return {}
    if isinstance(canonical_papers, Mapping):
        return {str(key): value for key, value in canonical_papers.items()}
    return {paper.paper_id: paper for paper in canonical_papers}


def _overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Return whether two annotation spans overlap."""

    return max(int(left["start"]), int(right["start"])) < min(
        int(left["end"]), int(right["end"])
    )


def validate_annotation_package(
    package: Mapping[str, Any],
    *,
    canonical_papers: Sequence[TargetPaper] | Mapping[str, TargetPaper] | None = None,
    require_complete: bool = False,
) -> AnnotationValidation:
    """Validate gold structure and report overlaps without modifying annotations.

    ``require_complete=False`` is appropriate for the empty review template.
    Training and scoring must pass ``require_complete=True``; that gate rejects
    every item without explicit human completion, including a partially filled
    entity list.
    """

    errors: list[str] = []
    if package.get("schema_version") != PILOT_SCHEMA_VERSION:
        errors.append("unsupported or missing schema_version")
    if package.get("package_kind") != PILOT_PACKAGE_KIND:
        errors.append("unsupported or missing package_kind")
    if tuple(package.get("approved_entity_types", ())) != APPROVED_ENTITY_TYPES:
        errors.append("approved_entity_types does not match the six-type pilot schema")
    examples = package.get("examples")
    if not isinstance(examples, list):
        raise AnnotationValidationError("examples must be an array")
    papers = _paper_map(canonical_papers)
    split_payload = package.get("paper_split", {})
    paper_split = (
        split_payload.get("paper_splits", {})
        if isinstance(split_payload, Mapping)
        else {}
    )
    if paper_split and set(paper_split.values()) - set(SPLITS):
        errors.append("paper_split contains an unsupported split")

    seen_examples: set[str] = set()
    seen_sentences: set[tuple[str, int, int]] = set()
    complete_count = 0
    entity_count = 0
    entity_counts: Counter[str] = Counter()
    overlaps: list[Mapping[str, Any]] = []
    for index, item in enumerate(examples):
        prefix = f"examples[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        required = (
            "example_id",
            "paper_id",
            "pmid",
            "pmcid",
            "split",
            "section",
            "sentence_id",
            "sentence_key",
            "sentence_start",
            "sentence_end",
            "sentence_text",
            "text",
            "source_checksum",
            "source_text_sha256",
            "sampling_reason",
            "entities",
            "annotation_status",
            "annotation_complete",
        )
        for field in required:
            if field not in item:
                errors.append(f"{prefix} missing {field}")
        if any(field not in item for field in required):
            continue
        example_id = str(item["example_id"])
        if example_id in seen_examples:
            errors.append(f"{prefix} duplicates example_id {example_id}")
        seen_examples.add(example_id)
        paper_id = str(item["paper_id"])
        split = str(item["split"])
        if split not in SPLITS:
            errors.append(f"{prefix} has unsupported split {split!r}")
        if paper_split and paper_split.get(paper_id) != split:
            errors.append(f"{prefix} split disagrees with paper_split for {paper_id}")
        try:
            start = _require_int(item["sentence_start"], f"{prefix}.sentence_start")
            end = _require_int(item["sentence_end"], f"{prefix}.sentence_end")
        except AnnotationValidationError as error:
            errors.append(str(error))
            continue
        text = item["sentence_text"]
        if not isinstance(text, str) or item["text"] != text:
            errors.append(f"{prefix} text and sentence_text must be identical strings")
            continue
        if not start < end:
            errors.append(f"{prefix} sentence span must satisfy start < end")
        sentence_identity = (paper_id, start, end)
        if sentence_identity in seen_sentences:
            errors.append(f"{prefix} duplicates canonical sentence {sentence_identity}")
        seen_sentences.add(sentence_identity)
        expected_key = _sentence_key(paper_id, start, end, text)
        if item["sentence_key"] != expected_key:
            errors.append(f"{prefix} sentence_key does not match source identity")
        if item["example_id"] != _example_id(expected_key):
            errors.append(f"{prefix} example_id does not match sentence_key")

        paper = papers.get(paper_id)
        if paper is not None:
            if not 0 <= start < end <= len(paper.text):
                errors.append(f"{prefix} sentence span is outside canonical paper")
            elif paper.text[start:end] != text:
                errors.append(f"{prefix} sentence text does not resolve to canonical text")
            elif (start, end) not in sentence_spans(paper.text):
                errors.append(f"{prefix} is not a complete deterministic sentence")
            if item["source_checksum"] != paper.source_checksum:
                errors.append(f"{prefix} source_checksum mismatch")
            if item["source_text_sha256"] != paper.text_checksum:
                errors.append(f"{prefix} source_text_sha256 mismatch")
            expected_section = paper.section_for_offset(start)
            if item["section"] != expected_section:
                errors.append(f"{prefix} section provenance mismatch")
            if item["pmid"] != paper.pmid or item["pmcid"] != paper.pmcid:
                errors.append(f"{prefix} PMID/PMCID provenance mismatch")

        annotation_complete = item["annotation_complete"]
        if not isinstance(annotation_complete, bool):
            errors.append(f"{prefix}.annotation_complete must be a boolean")
        complete = annotation_complete is True
        if complete:
            complete_count += 1
        elif require_complete:
            errors.append(f"{prefix} is not explicitly human-complete")
        annotation_status = item["annotation_status"]
        if not isinstance(annotation_status, str) or annotation_status not in {
            "unreviewed",
            "in_progress",
            "complete",
        }:
            errors.append(f"{prefix} has unsupported annotation_status")
        if complete and annotation_status != "complete":
            errors.append(f"{prefix} complete item must have annotation_status='complete'")
        if not complete and annotation_status == "complete":
            errors.append(
                f"{prefix} annotation_status='complete' requires annotation_complete=true"
            )
        entities = item["entities"]
        if not isinstance(entities, list):
            errors.append(f"{prefix}.entities must be an array")
            continue
        seen_entities: set[tuple[int, int, str, str]] = set()
        parsed_entities: list[Mapping[str, Any]] = []
        for entity_index, entity in enumerate(entities):
            entity_prefix = f"{prefix}.entities[{entity_index}]"
            if not isinstance(entity, Mapping):
                errors.append(f"{entity_prefix} must be an object")
                continue
            for field in ("start", "end", "text", "type"):
                if field not in entity:
                    errors.append(f"{entity_prefix} missing {field}")
            if any(field not in entity for field in ("start", "end", "text", "type")):
                continue
            try:
                entity_start = _require_int(entity["start"], f"{entity_prefix}.start")
                entity_end = _require_int(entity["end"], f"{entity_prefix}.end")
            except AnnotationValidationError as error:
                errors.append(str(error))
                continue
            entity_text = entity["text"]
            entity_type = entity["type"]
            if not isinstance(entity_text, str):
                errors.append(f"{entity_prefix}.text must be a string")
                continue
            if not isinstance(entity_type, str):
                errors.append(f"{entity_prefix}.type must be a string")
                continue
            if entity_type not in APPROVED_ENTITY_TYPE_SET:
                errors.append(f"{entity_prefix} has unsupported entity type {entity_type!r}")
            if not 0 <= entity_start < entity_end <= len(text):
                errors.append(f"{entity_prefix} has an invalid sentence-relative span")
            elif text[entity_start:entity_end] != entity_text:
                errors.append(f"{entity_prefix} text does not match its span")
            identity = (entity_start, entity_end, entity_text, str(entity_type))
            if identity in seen_entities:
                errors.append(f"{entity_prefix} is an exact duplicate")
            seen_entities.add(identity)
            parsed_entities.append(
                {
                    "start": entity_start,
                    "end": entity_end,
                    "text": entity_text,
                    "type": entity_type,
                }
            )
            entity_count += 1
            entity_counts[str(entity_type)] += 1
        for left_index, left in enumerate(parsed_entities):
            for right in parsed_entities[left_index + 1 :]:
                if _overlap(left, right):
                    overlaps.append(
                        {
                            "example_id": example_id,
                            "left": dict(left),
                            "right": dict(right),
                            "nested": (
                                int(left["start"]) <= int(right["start"])
                                and int(left["end"]) >= int(right["end"])
                            )
                            or (
                                int(right["start"]) <= int(left["start"])
                                and int(right["end"]) >= int(left["end"])
                            ),
                        }
                    )

    if errors:
        if len(errors) > 20:
            errors = errors[:20] + [f"... and {len(errors) - 20} more validation error(s)"]
        raise AnnotationValidationError("; ".join(errors))
    incomplete_count = len(examples) - complete_count
    return AnnotationValidation(
        item_count=len(examples),
        complete_count=complete_count,
        incomplete_count=incomplete_count,
        entity_count=entity_count,
        entity_counts_by_type=dict(sorted(entity_counts.items())),
        overlaps=tuple(overlaps),
    )


def load_annotation_package(path: Path) -> dict[str, Any]:
    """Load a JSON annotation package without weakening validation."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise AnnotationValidationError("Annotation package must be a JSON object")
    return dict(payload)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic UTF-8 JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_split_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    """Create or verify the frozen paper-level split manifest."""

    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("paper_splits") != manifest.get("paper_splits"):
            raise ValueError(
                f"Frozen split manifest {path} disagrees with requested paper assignment"
            )
        return
    write_json(path, manifest)


def write_pilot_package(path: Path, package: Mapping[str, Any]) -> None:
    """Write and validate the empty-or-human-edited pilot package."""

    validate_annotation_package(package)
    write_json(path, package)


def _render_prediction_lines(
    predictions: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Render model suggestions in a compact reviewer-friendly form."""

    if not predictions:
        return ["- none recorded"]
    return [
        "- "
        f"`[{value.get('relative_start')}, {value.get('relative_end')})` "
        f"{value.get('text')!r} — {value.get('type')}"
        + (
            f" (score={value['score']:.4f})"
            if isinstance(value.get("score"), (int, float))
            else ""
        )
        for value in predictions
    ]


def render_pilot_markdown(package: Mapping[str, Any]) -> str:
    """Render a reviewer packet while keeping gold fields visibly empty."""

    selection = package.get("selection", {})
    lines = [
        "# Target-domain gold pilot annotation packet",
        "",
        "This packet is a human annotation template. Existing HunFlair2 and "
        "AIONER outputs are suggestions only; they are not gold labels.",
        "",
        f"- Status: `{package.get('status')}`",
        f"- Selected sentences: {selection.get('selected_count', 0)}",
        f"- Annotation convention: `{package.get('annotation_convention')}`",
        "- Gold policy: annotate every target-schema entity in each sentence, "
        "including sentences with no entities.",
        "",
        "## Paper split",
        "",
        "| Paper | Split | Mode | Characters | Sentences |",
        "|---|---|---|---:|---:|",
    ]
    split = package.get("paper_split", {})
    for paper in split.get("papers", []):
        lines.append(
            f"| {paper.get('paper_id')} | {paper.get('split')} | "
            f"{paper.get('acquisition_mode')} | {paper.get('character_count')} | "
            f"{paper.get('sentence_count')} |"
        )
    lines.extend(["", "## Annotation items", ""])
    for index, item in enumerate(package.get("examples", []), start=1):
        lines.extend(
            [
                f"### {index}. `{item['example_id']}`",
                "",
                f"- Paper: `{item['paper_id']}` (PMID `{item.get('pmid')}`, "
                f"PMCID `{item.get('pmcid')}`)",
                f"- Split: `{item['split']}`; section: `{item['section']}`",
                f"- Sentence: `{item['sentence_id']}`; canonical offsets: "
                f"`[{item['sentence_start']}, {item['sentence_end']})`",
                f"- Sampling: `{item['sampling_group']}` — {item['sampling_reason']}",
                f"- Source text SHA-256: `{item['source_text_sha256']}`",
                "",
                "> " + item["sentence_text"].replace("\n", "\n> "),
                "",
                "HunFlair2 suggestions:",
                *_render_prediction_lines(item["prediction_context"]["hunflair2"]),
                "",
                "AIONER suggestions (when available):",
                *_render_prediction_lines(item["prediction_context"]["aioner"]),
                "",
                "Gold annotation to complete by a human reviewer:",
                "```json",
                json.dumps(
                    {
                        "entities": item["entities"],
                        "annotation_status": item["annotation_status"],
                        "annotation_complete": item["annotation_complete"],
                    },
                    indent=2,
                ),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def _entity_from_prediction(value: Mapping[str, Any], index: int) -> Entity:
    """Convert a plain prediction payload to an evaluation entity."""

    entity_type = str(value.get("type", value.get("label", "")))
    return Entity(
        id=str(value.get("id", f"prediction-{index}")),
        text=str(value["text"]),
        type=entity_type,
        start=int(value["start"]),
        end=int(value["end"]),
        score=None if value.get("score") is None else float(value["score"]),
    )


def _gold_entity_from_item(value: Mapping[str, Any], index: int) -> Entity:
    """Convert one validated sentence-relative gold entry to an Entity."""

    return Entity(
        id=f"gold-{index}",
        text=str(value["text"]),
        type=str(value["type"]),
        start=int(value["start"]),
        end=int(value["end"]),
        score=None,
    )


def evaluate_pilot_predictions(
    package: Mapping[str, Any],
    predictions_by_example: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    split: str = "test",
) -> dict[str, Any]:
    """Compute future exact-span target metrics and bounded failure diagnostics."""

    if split not in SPLITS:
        raise ValueError(f"Unsupported evaluation split: {split}")
    validation = validate_annotation_package(package, require_complete=True)
    del validation
    items = [item for item in package["examples"] if item["split"] == split]
    if not items:
        raise ValueError(f"No complete pilot items in split {split}")

    counts: dict[str, Counter[str]] = {
        entity_type: Counter() for entity_type in APPROVED_ENTITY_TYPES
    }
    failure_counts: Counter[str] = Counter()
    overlap_count = 0
    total_gold = 0
    total_predicted = 0
    exact_matches = 0
    for item in items:
        gold = [_gold_entity_from_item(value, index) for index, value in enumerate(item["entities"])]
        predicted = [
            _entity_from_prediction(value, index)
            for index, value in enumerate(predictions_by_example.get(item["example_id"], ()))
        ]
        gold_keys = {(e.start, e.end, e.type): e for e in gold}
        pred_keys = {
            (e.start, e.end, _canonical_prediction_type(e.type) or e.type): e
            for e in predicted
        }
        matched_keys = set(gold_keys) & set(pred_keys)
        exact_matches += len(matched_keys)
        total_gold += len(gold)
        total_predicted += len(predicted)
        for entity_type in APPROVED_ENTITY_TYPES:
            gold_count = sum(1 for entity in gold if entity.type == entity_type)
            pred_count = sum(
                1
                for entity in predicted
                if (_canonical_prediction_type(entity.type) or entity.type) == entity_type
            )
            tp = sum(1 for key in matched_keys if key[2] == entity_type)
            counts[entity_type].update(
                {"gold": gold_count, "predicted": pred_count, "tp": tp}
            )
        remaining_gold = [entity for key, entity in gold_keys.items() if key not in matched_keys]
        remaining_pred = [
            entity for key, entity in pred_keys.items() if key not in matched_keys
        ]
        paired_gold: set[int] = set()
        paired_pred: set[int] = set()
        for gold_index, gold_entity in enumerate(remaining_gold):
            for pred_index, pred_entity in enumerate(remaining_pred):
                if gold_index in paired_gold or pred_index in paired_pred:
                    continue
                pred_type = _canonical_prediction_type(pred_entity.type) or pred_entity.type
                if gold_entity.start == pred_entity.start and gold_entity.end == pred_entity.end:
                    if gold_entity.type != pred_type:
                        failure_counts["wrong type"] += 1
                        paired_gold.add(gold_index)
                        paired_pred.add(pred_index)
                elif gold_entity.type == pred_type and _entity_overlap(gold_entity, pred_entity):
                    failure_counts["span mismatch"] += 1
                    paired_gold.add(gold_index)
                    paired_pred.add(pred_index)
                elif gold_entity.type != pred_type and _entity_overlap(gold_entity, pred_entity):
                    failure_counts["wrong type"] += 1
                    paired_gold.add(gold_index)
                    paired_pred.add(pred_index)
        failure_counts["missed entity"] += len(remaining_gold) - len(paired_gold)
        failure_counts["spurious entity"] += len(remaining_pred) - len(paired_pred)
        for gold_index, left in enumerate(gold):
            for right in gold[gold_index + 1 :]:
                if _entity_overlap(left, right):
                    overlap_count += 1
        for left_index, left in enumerate(predicted):
            for right in predicted[left_index + 1 :]:
                if _entity_overlap(left, right):
                    overlap_count += 1

    per_type: dict[str, Any] = {}
    observed_f1: list[float] = []
    for entity_type in APPROVED_ENTITY_TYPES:
        values = counts[entity_type]
        tp = values["tp"]
        fp = values["predicted"] - tp
        fn = values["gold"] - tp
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
        if f1 is not None:
            observed_f1.append(f1)
        per_type[entity_type] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "gold": values["gold"],
            "predicted": values["predicted"],
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    micro_fp = total_predicted - exact_matches
    micro_fn = total_gold - exact_matches
    micro_precision = (
        exact_matches / total_predicted if total_predicted else None
    )
    micro_recall = exact_matches / total_gold if total_gold else None
    micro_f1 = (
        2 * exact_matches / (2 * exact_matches + micro_fp + micro_fn)
        if total_gold + total_predicted
        else None
    )
    return {
        "split": split,
        "item_count": len(items),
        "micro": {
            "tp": exact_matches,
            "fp": micro_fp,
            "fn": micro_fn,
            "precision": micro_precision,
            "recall": micro_recall,
            "f1": micro_f1,
        },
        "macro_f1": sum(observed_f1) / len(observed_f1) if observed_f1 else None,
        "per_type": per_type,
        "failure_counts": dict(sorted(failure_counts.items())),
        "overlap_diagnostics": {"overlapping_span_pairs": overlap_count},
        "method": (
            "Exact half-open sentence-relative span and canonical type; no fuzzy "
            "matching or threshold tuning."
        ),
    }


def _entity_overlap(left: Entity, right: Entity) -> bool:
    """Return whether two entity spans overlap."""

    return max(left.start, right.start) < min(left.end, right.end)


def assert_flat_hunflair2_gold_supported(
    package: Mapping[str, Any],
) -> None:
    """Reject valid-but-nested or unsupported gold before Flair conversion."""

    validation = validate_annotation_package(package, require_complete=True)
    if validation.overlaps:
        examples = sorted({str(item["example_id"]) for item in validation.overlaps})
        raise TrainingCompatibilityError(
            "HunFlair2's flat BIOES representation cannot represent overlapping "
            f"or nested gold spans; review examples: {examples}"
        )
    unsupported_variants = [
        item["example_id"]
        for item in package["examples"]
        for entity in item["entities"]
        if entity["type"] == "SequenceVariant"
    ]
    if unsupported_variants:
        raise TrainingCompatibilityError(
            "The released HunFlair2 base head has no SequenceVariant label; "
            "do not drop or remap human gold. Resolve these examples before "
            f"training: {sorted(unsupported_variants)}"
        )


__all__ = [
    "APPROVED_ENTITY_TYPES",
    "APPROVED_ENTITY_TYPE_SET",
    "AnnotationValidation",
    "AnnotationValidationError",
    "DEFAULT_PAPER_SPLIT",
    "HUNFLAIR2_TRAINING_LABEL_BY_TYPE",
    "PILOT_ANNOTATION_CONVENTION",
    "PILOT_PACKAGE_KIND",
    "PILOT_SCHEMA_VERSION",
    "PILOT_SELECTION_VERSION",
    "TrainingCompatibilityError",
    "assert_flat_hunflair2_gold_supported",
    "build_pilot_package",
    "build_split_manifest",
    "evaluate_pilot_predictions",
    "load_annotation_package",
    "load_review_packet",
    "render_pilot_markdown",
    "review_packet_prediction_index",
    "sha256_file",
    "sha256_json",
    "validate_annotation_package",
    "write_json",
    "write_pilot_package",
    "write_split_manifest",
]
