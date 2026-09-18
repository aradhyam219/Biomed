"""Model-independent exact-match evaluation for biomedical named entities.

The evaluator consumes the normalized :class:`Entity` contract and the existing
BioRED parser.  It deliberately does not inspect GLiNER predictions, model
objects, tokenizers, or relation-model output.  BioRED's relation annotations are
used only for the optional graph-critical entity-recall diagnostic.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .aioner import AIONER_LABEL_TO_CANONICAL
from .biored import BioREDDataset, BioREDDocument, BioREDMention
from .entity_extraction import Entity, EntityExtractor
from .hunflair2 import HUNFLAIR2_LABEL_TO_CANONICAL


# BioRED's loader keeps these short internal names for compatibility with the
# preserved relation path.  NER evaluation maps them back to explicit canonical
# BioRED classes rather than comparing short names to model labels implicitly.
BIORED_INTERNAL_TYPE_TO_CANONICAL: Mapping[str, str] = {
    "Gene": "GeneOrGeneProduct",
    "Disease": "DiseaseOrPhenotypicFeature",
    "Chemical": "ChemicalEntity",
    "Species": "OrganismTaxon",
    "CellLine": "CellLine",
    "Variant": "SequenceVariant",
}

# This is the current production GLiNER schema.  Gene and protein intentionally
# share the BioRED GeneOrGeneProduct evaluation class.  DNA and RNA remain
# outside the comparable taxonomy until a justified BioRED mapping exists.
PREDICTED_TYPE_TO_CANONICAL: Mapping[str, str] = {
    "gene": "GeneOrGeneProduct",
    "protein": "GeneOrGeneProduct",
    "disease": "DiseaseOrPhenotypicFeature",
    "chemical": "ChemicalEntity",
    "species": "OrganismTaxon",
    "cell line": "CellLine",
    # Official AIONER labels are kept explicit at the evaluation boundary.  The
    # adapter preserves these source labels; this table is the only taxonomy
    # normalization applied before exact-match scoring.
    **AIONER_LABEL_TO_CANONICAL,
    # HunFlair2 emits the same five shared BioRED categories with its own
    # official label spelling; the adapter preserves those labels as well.
    **HUNFLAIR2_LABEL_TO_CANONICAL,
}

# The shared-class view is deliberately fixed to the five classes supported by
# the active GLiNER, AIONER, and HunFlair2 comparison adapters.
COMPARABLE_CANONICAL_TYPES = (
    "CellLine",
    "ChemicalEntity",
    "DiseaseOrPhenotypicFeature",
    "GeneOrGeneProduct",
    "OrganismTaxon",
)
ALL_CANONICAL_TYPES = tuple(sorted(set(BIORED_INTERNAL_TYPE_TO_CANONICAL.values())))

FAILURE_MISSED_ENTITY = "missed entity"
FAILURE_SPURIOUS_ENTITY = "spurious entity"
FAILURE_WRONG_TYPE = "wrong type"
FAILURE_SPAN_MISMATCH = "span mismatch"
FAILURE_OVERLAPPING_PREDICTION = "overlapping prediction"
FAILURE_UNSUPPORTED_GOLD = "schema-unscored / unsupported gold category"
FAILURE_UNSUPPORTED_PREDICTED = "schema-unscored / unsupported predicted category"

FAILURE_CATEGORIES = (
    FAILURE_MISSED_ENTITY,
    FAILURE_SPURIOUS_ENTITY,
    FAILURE_WRONG_TYPE,
    FAILURE_SPAN_MISMATCH,
    FAILURE_OVERLAPPING_PREDICTION,
    FAILURE_UNSUPPORTED_GOLD,
    FAILURE_UNSUPPORTED_PREDICTED,
)


@dataclass(frozen=True)
class FailureRecord:
    """One deterministic, inspection-ready NER failure example."""

    document_id: str
    category: str
    context: Mapping[str, Any]
    gold: Mapping[str, Any] | None
    predicted: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable failure record."""

        return {
            "document_id": self.document_id,
            "category": self.category,
            "context": dict(self.context),
            "gold": dict(self.gold) if self.gold is not None else None,
            "predicted": (
                dict(self.predicted) if self.predicted is not None else None
            ),
        }


@dataclass(frozen=True)
class EntityScore:
    """Exact-match score and diagnostics for one BioRED document."""

    metrics: Mapping[str, Any]
    failures: tuple[FailureRecord, ...]
    failure_counts: Mapping[str, int]
    failure_examples: Mapping[str, tuple[FailureRecord, ...]]
    matched_gold_ids: frozenset[str]
    gold_scored_count: int
    predicted_scored_count: int
    gold_unscored_counts: Mapping[str, int]
    predicted_unscored_counts: Mapping[str, int]


class _FailureCollector:
    """Keep complete category counts and a bounded deterministic sample."""

    def __init__(self, limit: int) -> None:
        if limit < 0:
            raise ValueError("failure example limit must not be negative")
        self._limit = limit
        self.counts: Counter[str] = Counter()
        self.examples: dict[str, list[FailureRecord]] = defaultdict(list)

    def add(self, record: FailureRecord) -> None:
        self.counts[record.category] += 1
        if len(self.examples[record.category]) < self._limit:
            self.examples[record.category].append(record)


def canonical_gold_type(entity_type: str) -> str | None:
    """Map a BioRED loader type to the explicit evaluation taxonomy."""

    return BIORED_INTERNAL_TYPE_TO_CANONICAL.get(entity_type)


def canonical_predicted_type(entity_type: str) -> str | None:
    """Map one normalized predictor label to the explicit evaluation taxonomy."""

    return PREDICTED_TYPE_TO_CANONICAL.get(entity_type)


def _normalize_scored_types(
    scored_types: Sequence[str] | None,
) -> tuple[str, ...]:
    """Validate and deterministically order one model's supported taxonomy."""

    selected = tuple(
        COMPARABLE_CANONICAL_TYPES if scored_types is None else scored_types
    )
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("scored types must contain unique non-empty classes")
    unknown = set(selected) - set(ALL_CANONICAL_TYPES)
    if unknown:
        raise ValueError(f"Unsupported canonical scored type(s): {sorted(unknown)}")
    return tuple(sorted(selected))


def _metric_counts(
    true_positive: int,
    false_positive: int,
    false_negative: int,
    *,
    gold: int | None = None,
    predicted: int | None = None,
) -> dict[str, Any]:
    """Return counts and exact precision/recall/F1 with undefined values as None."""

    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else None
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else None
    )
    observed = (gold or 0) + (predicted or 0)
    if observed:
        f1 = 2 * true_positive / (2 * true_positive + false_positive + false_negative)
    elif precision is None or recall is None:
        f1 = None
    elif precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    result: dict[str, Any] = {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }
    if gold is not None:
        result["support"] = gold
    if predicted is not None:
        result["predicted"] = predicted
    return result


def _span_overlaps(
    left_start: int, left_end: int, right_start: int, right_end: int
) -> bool:
    """Return whether two non-empty half-open character spans overlap."""

    return max(left_start, right_start) < min(left_end, right_end)


def _validate_prediction(document_id: str, text: str, entity: Entity) -> None:
    """Fail closed when an adapter violates the normalized entity contract."""

    if not isinstance(entity, Entity):
        raise TypeError(
            f"{document_id}: EntityExtractor returned {type(entity).__name__}, "
            "expected Entity"
        )
    if not 0 <= entity.start < entity.end <= len(text):
        raise ValueError(
            f"{document_id}: invalid predicted entity span "
            f"[{entity.start}, {entity.end})"
        )
    if text[entity.start : entity.end] != entity.text:
        raise ValueError(
            f"{document_id}: predicted span [{entity.start}, {entity.end}) "
            f"does not resolve to {entity.text!r}"
        )


def _gold_payload(mention: BioREDMention) -> dict[str, Any]:
    """Serialize a gold mention with both source and evaluation labels."""

    return {
        "id": mention.id,
        "text": mention.text,
        "type": mention.type,
        "canonical_type": canonical_gold_type(mention.type),
        "start": mention.start,
        "end": mention.end,
        "concept_ids": list(mention.concept_ids),
    }


def _predicted_payload(entity: Entity) -> dict[str, Any]:
    """Serialize a normalized prediction with its evaluation label."""

    return {
        "id": entity.id,
        "text": entity.text,
        "type": entity.type,
        "canonical_type": canonical_predicted_type(entity.type),
        "start": entity.start,
        "end": entity.end,
        "score": entity.score,
    }


def _context(
    text: str,
    gold: BioREDMention | None,
    predicted: Entity | None,
    window: int,
) -> dict[str, Any]:
    """Return a bounded source-text context around the involved spans."""

    starts = [item.start for item in (gold, predicted) if item is not None]
    ends = [item.end for item in (gold, predicted) if item is not None]
    start = min(starts) if starts else 0
    end = max(ends) if ends else start
    left = max(0, start - window)
    right = min(len(text), end + window)
    return {
        "text": text[left:right],
        "start": left,
        "end": right,
    }


def _failure_record(
    document_id: str,
    text: str,
    category: str,
    gold: BioREDMention | None,
    predicted: Entity | None,
    context_window: int,
) -> FailureRecord:
    """Construct one failure record without changing primary matching."""

    return FailureRecord(
        document_id=document_id,
        category=category,
        context=_context(text, gold, predicted, context_window),
        gold=_gold_payload(gold) if gold is not None else None,
        predicted=_predicted_payload(predicted) if predicted is not None else None,
    )


def _exact_key(start: int, end: int, canonical_type: str) -> tuple[int, int, str]:
    """Return the deterministic exact-match key."""

    return start, end, canonical_type


def score_entity_mentions(
    document_id: str,
    text: str,
    gold_mentions: Sequence[BioREDMention],
    predicted_entities: Sequence[Entity],
    *,
    scored_types: Sequence[str] | None = None,
    context_window: int = 80,
    failure_example_limit: int = 5,
) -> EntityScore:
    """Score normalized predictions against one document's BioRED mentions.

    Primary matching is a deterministic multiset match on exact half-open span
    and canonical type.  Unsupported gold or prediction labels are excluded from
    the primary counts and recorded as schema-coverage failures.  Boundary/type
    diagnostics are paired only after exact scoring and therefore cannot alter the
    exact-match metrics.
    """

    if context_window < 0:
        raise ValueError("context window must not be negative")
    scored_type_set = set(_normalize_scored_types(scored_types))
    collector = _FailureCollector(failure_example_limit)
    gold_scored: list[tuple[BioREDMention, str]] = []
    gold_unscored_counts: Counter[str] = Counter()
    for mention in gold_mentions:
        canonical_type = canonical_gold_type(mention.type)
        if canonical_type is None or canonical_type not in scored_type_set:
            gold_unscored_counts[mention.type] += 1
            collector.add(
                _failure_record(
                    document_id,
                    text,
                    FAILURE_UNSUPPORTED_GOLD,
                    mention,
                    None,
                    context_window,
                )
            )
        else:
            gold_scored.append((mention, canonical_type))

    predicted_scored: list[tuple[Entity, str]] = []
    predicted_unscored_counts: Counter[str] = Counter()
    for entity in predicted_entities:
        _validate_prediction(document_id, text, entity)
        canonical_type = canonical_predicted_type(entity.type)
        if canonical_type is None or canonical_type not in scored_type_set:
            predicted_unscored_counts[entity.type] += 1
            collector.add(
                _failure_record(
                    document_id,
                    text,
                    FAILURE_UNSUPPORTED_PREDICTED,
                    None,
                    entity,
                    context_window,
                )
            )
        else:
            predicted_scored.append((entity, canonical_type))

    gold_by_key: dict[tuple[int, int, str], list[BioREDMention]] = defaultdict(list)
    predicted_by_key: dict[tuple[int, int, str], list[Entity]] = defaultdict(list)
    for mention, canonical_type in gold_scored:
        gold_by_key[_exact_key(mention.start, mention.end, canonical_type)].append(
            mention
        )
    for entity, canonical_type in predicted_scored:
        predicted_by_key[_exact_key(entity.start, entity.end, canonical_type)].append(
            entity
        )

    matched_gold_ids: set[str] = set()
    unmatched_gold: list[tuple[BioREDMention, str]] = []
    unmatched_predicted: list[tuple[Entity, str]] = []
    per_type_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0, "gold": 0, "predicted": 0}
    )
    for mention, canonical_type in gold_scored:
        per_type_counts[canonical_type]["gold"] += 1
    for entity, canonical_type in predicted_scored:
        per_type_counts[canonical_type]["predicted"] += 1

    all_keys = sorted(set(gold_by_key) | set(predicted_by_key))
    for key in all_keys:
        gold_items = gold_by_key.get(key, [])
        predicted_items = predicted_by_key.get(key, [])
        matched_count = min(len(gold_items), len(predicted_items))
        canonical_type = key[2]
        per_type_counts[canonical_type]["tp"] += matched_count
        for mention in gold_items[:matched_count]:
            matched_gold_ids.add(mention.id)
        unmatched_gold.extend(
            (mention, canonical_type) for mention in gold_items[matched_count:]
        )
        unmatched_predicted.extend(
            (entity, canonical_type) for entity in predicted_items[matched_count:]
        )

    # Exact matching is complete above.  The following deterministic pairings are
    # diagnostics only and never affect TP/FP/FN counts.
    remaining_gold = list(unmatched_gold)
    remaining_predicted = list(unmatched_predicted)

    def pair_first(
        predicate: Any,
        category: str,
    ) -> None:
        nonlocal remaining_gold, remaining_predicted
        paired_gold: set[int] = set()
        paired_predicted: set[int] = set()
        for gold_index, (gold, gold_type) in enumerate(remaining_gold):
            for predicted_index, (predicted, predicted_type) in enumerate(
                remaining_predicted
            ):
                if gold_index in paired_gold or predicted_index in paired_predicted:
                    continue
                if predicate(gold, gold_type, predicted, predicted_type):
                    collector.add(
                        _failure_record(
                            document_id,
                            text,
                            category,
                            gold,
                            predicted,
                            context_window,
                        )
                    )
                    paired_gold.add(gold_index)
                    paired_predicted.add(predicted_index)
                    break
        remaining_gold = [
            item for index, item in enumerate(remaining_gold) if index not in paired_gold
        ]
        remaining_predicted = [
            item
            for index, item in enumerate(remaining_predicted)
            if index not in paired_predicted
        ]

    pair_first(
        lambda gold, gold_type, predicted, predicted_type: (
            gold.start == predicted.start
            and gold.end == predicted.end
            and gold_type != predicted_type
        ),
        FAILURE_WRONG_TYPE,
    )
    pair_first(
        lambda gold, gold_type, predicted, predicted_type: (
            gold_type == predicted_type
            and _span_overlaps(
                gold.start, gold.end, predicted.start, predicted.end
            )
        ),
        FAILURE_SPAN_MISMATCH,
    )
    pair_first(
        lambda gold, gold_type, predicted, predicted_type: (
            gold_type != predicted_type
            and _span_overlaps(
                gold.start, gold.end, predicted.start, predicted.end
            )
        ),
        FAILURE_OVERLAPPING_PREDICTION,
    )
    for gold, _ in remaining_gold:
        collector.add(
            _failure_record(
                document_id,
                text,
                FAILURE_MISSED_ENTITY,
                gold,
                None,
                context_window,
            )
        )
    for predicted, _ in remaining_predicted:
        collector.add(
            _failure_record(
                document_id,
                text,
                FAILURE_SPURIOUS_ENTITY,
                None,
                predicted,
                context_window,
            )
        )

    true_positive = sum(item["tp"] for item in per_type_counts.values())
    false_positive = sum(
        item["predicted"] - item["tp"] for item in per_type_counts.values()
    )
    false_negative = sum(
        item["gold"] - item["tp"] for item in per_type_counts.values()
    )
    per_type = {
        canonical_type: _metric_counts(
            per_type_counts[canonical_type]["tp"],
            per_type_counts[canonical_type]["predicted"]
            - per_type_counts[canonical_type]["tp"],
            per_type_counts[canonical_type]["gold"]
            - per_type_counts[canonical_type]["tp"],
            gold=per_type_counts[canonical_type]["gold"],
            predicted=per_type_counts[canonical_type]["predicted"],
        )
        for canonical_type in _normalize_scored_types(scored_types)
    }
    macro_values = [
        metric["f1"] for metric in per_type.values() if metric["f1"] is not None
    ]
    metrics = {
        "matching": "exact half-open character span and canonical evaluation type",
        "micro": _metric_counts(true_positive, false_positive, false_negative),
        "per_type": per_type,
        "macro_f1": sum(macro_values) / len(macro_values)
        if macro_values
        else None,
        "macro_scored_types": [
            canonical_type
            for canonical_type, metric in per_type.items()
            if metric["f1"] is not None
        ],
    }
    failure_examples = {
        category: tuple(collector.examples.get(category, ()))
        for category in FAILURE_CATEGORIES
    }
    failure_records = tuple(
        record
        for category in FAILURE_CATEGORIES
        for record in failure_examples[category]
    )
    failure_counts = {
        category: collector.counts.get(category, 0)
        for category in FAILURE_CATEGORIES
    }
    return EntityScore(
        metrics=metrics,
        failures=failure_records,
        failure_counts=failure_counts,
        failure_examples=failure_examples,
        matched_gold_ids=frozenset(matched_gold_ids),
        gold_scored_count=len(gold_scored),
        predicted_scored_count=len(predicted_scored),
        gold_unscored_counts=dict(sorted(gold_unscored_counts.items())),
        predicted_unscored_counts=dict(sorted(predicted_unscored_counts.items())),
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    """Return a bounded diagnostic ratio, or None when no denominator exists."""

    return numerator / denominator if denominator else None


def _graph_critical_recall(
    documents: Sequence[BioREDDocument],
    matched_gold_ids_by_document: Mapping[str, frozenset[str]],
) -> dict[str, Any]:
    """Measure graph-critical recognition with overall and shared-class views.

    The overall denominator intentionally includes relation-participating variant
    mentions even when a model does not support that class.  The comparable view
    removes those unsupported classes so it measures recognition quality on the
    shared taxonomy rather than schema coverage.
    """

    overall_mentions = {"gold": 0, "recognized": 0, "unsupported": 0}
    comparable_mentions = {"gold": 0, "recognized": 0, "unsupported": 0}
    overall_concepts = {"gold": 0, "recognized": 0}
    comparable_concepts = {"gold": 0, "recognized": 0}
    documents_with_relations = 0
    for document in documents:
        participating_concepts = {
            concept_id
            for relation in document.relations
            for concept_id in (relation.concept_a, relation.concept_b)
        }
        if not participating_concepts:
            continue
        documents_with_relations += 1
        critical_mentions = [
            mention
            for mention in document.mentions
            if participating_concepts.intersection(mention.concept_ids)
        ]
        matched_ids = matched_gold_ids_by_document.get(document.id, frozenset())
        overall_mentions["gold"] += len(critical_mentions)
        overall_mentions["recognized"] += sum(
            mention.id in matched_ids for mention in critical_mentions
        )
        overall_mentions["unsupported"] += sum(
            canonical_gold_type(mention.type) not in COMPARABLE_CANONICAL_TYPES
            for mention in critical_mentions
        )

        comparable_critical_mentions = [
            mention
            for mention in critical_mentions
            if canonical_gold_type(mention.type) in COMPARABLE_CANONICAL_TYPES
        ]
        comparable_mentions["gold"] += len(comparable_critical_mentions)
        comparable_mentions["recognized"] += sum(
            mention.id in matched_ids for mention in comparable_critical_mentions
        )

        critical_concepts = {
            concept_id
            for mention in critical_mentions
            for concept_id in mention.concept_ids
            if concept_id in participating_concepts
        }
        recognized_concept_ids = {
            concept_id
            for mention in critical_mentions
            if mention.id in matched_ids
            for concept_id in mention.concept_ids
            if concept_id in participating_concepts
        }
        overall_concepts["gold"] += len(critical_concepts)
        overall_concepts["recognized"] += len(recognized_concept_ids)

        comparable_concepts_for_document = {
            concept_id
            for mention in comparable_critical_mentions
            for concept_id in mention.concept_ids
            if concept_id in participating_concepts
        }
        recognized_comparable_concepts = {
            concept_id
            for mention in comparable_critical_mentions
            if mention.id in matched_ids
            for concept_id in mention.concept_ids
            if concept_id in participating_concepts
        }
        comparable_concepts["gold"] += len(comparable_concepts_for_document)
        comparable_concepts["recognized"] += len(recognized_comparable_concepts)

    overall_mention_view = {
        "recognized": overall_mentions["recognized"],
        "gold": overall_mentions["gold"],
        "recall": _ratio(overall_mentions["recognized"], overall_mentions["gold"]),
        "unscored_gold_type": overall_mentions["unsupported"],
        "denominator": "all relation-participating gold mentions",
    }
    comparable_mention_view = {
        "recognized": comparable_mentions["recognized"],
        "gold": comparable_mentions["gold"],
        "recall": _ratio(
            comparable_mentions["recognized"], comparable_mentions["gold"]
        ),
        "unscored_gold_type": comparable_mentions["unsupported"],
        "denominator": "relation-participating gold mentions in shared taxonomy",
    }
    overall_concept_view = {
        "recognized": overall_concepts["recognized"],
        "gold": overall_concepts["gold"],
        "recall": _ratio(overall_concepts["recognized"], overall_concepts["gold"]),
        "denominator": "all relation-participating gold concepts",
    }
    comparable_concept_view = {
        "recognized": comparable_concepts["recognized"],
        "gold": comparable_concepts["gold"],
        "recall": _ratio(
            comparable_concepts["recognized"], comparable_concepts["gold"]
        ),
        "denominator": "relation-participating gold concepts with shared-class mentions",
    }

    return {
        "definition": (
            "Gold BioRED entity mentions/concepts participating in at least one "
            "annotated relation, recognized by exact span and canonical type; "
            "this is an NER diagnostic, not relation evaluation."
        ),
        "documents_with_relations": documents_with_relations,
        "mention_level": {
            # These aliases preserve the original report contract as overall
            # recall while the nested views make the denominator explicit.
            **overall_mention_view,
            "overall": overall_mention_view,
            "comparable_class": comparable_mention_view,
        },
        "concept_level": {
            **overall_concept_view,
            "overall": overall_concept_view,
            "comparable_class": comparable_concept_view,
        },
    }


def _taxonomy_report() -> dict[str, Any]:
    """Return the inspectable evaluation-side taxonomy contract."""

    return {
        "gold_internal_type_to_canonical": dict(
            sorted(BIORED_INTERNAL_TYPE_TO_CANONICAL.items())
        ),
        "predicted_type_to_canonical": dict(
            sorted(PREDICTED_TYPE_TO_CANONICAL.items())
        ),
        "comparable_canonical_types": list(COMPARABLE_CANONICAL_TYPES),
        "all_canonical_types": list(ALL_CANONICAL_TYPES),
        "unscored_gold_canonical_types": [
            canonical_type
            for canonical_type in sorted(set(BIORED_INTERNAL_TYPE_TO_CANONICAL.values()))
            if canonical_type not in COMPARABLE_CANONICAL_TYPES
        ],
        "unscored_predicted_types": [
            "DNA",
            "RNA",
        ],
        "policy": (
            "Shared-class metrics compare only exact span plus canonical type for "
            "classes represented by both systems. Full-schema metrics use the "
            "explicit supported taxonomy supplied by the predictor. Unsupported "
            "gold/prediction labels are reported as schema coverage gaps and are "
            "not silently remapped."
        ),
    }


def _aggregate_entity_scores(
    scores: Sequence[EntityScore],
    scored_types: Sequence[str],
) -> dict[str, Any]:
    """Aggregate per-document exact-match scores for one taxonomy view."""

    selected_types = _normalize_scored_types(scored_types)
    aggregate: dict[str, dict[str, int]] = {
        canonical_type: {
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "gold": 0,
            "predicted": 0,
        }
        for canonical_type in selected_types
    }
    for score in scores:
        for canonical_type in selected_types:
            metric = score.metrics["per_type"][canonical_type]
            counts = aggregate[canonical_type]
            counts["tp"] += metric["tp"]
            counts["fp"] += metric["fp"]
            counts["fn"] += metric["fn"]
            counts["gold"] += metric["support"]
            counts["predicted"] += metric["predicted"]

    per_type = {
        canonical_type: _metric_counts(
            counts["tp"],
            counts["fp"],
            counts["fn"],
            gold=counts["gold"],
            predicted=counts["predicted"],
        )
        for canonical_type, counts in aggregate.items()
    }
    true_positive = sum(counts["tp"] for counts in aggregate.values())
    false_positive = sum(counts["fp"] for counts in aggregate.values())
    false_negative = sum(counts["fn"] for counts in aggregate.values())
    macro_values = [
        metric["f1"] for metric in per_type.values() if metric["f1"] is not None
    ]
    return {
        "matching": "exact half-open character span and canonical evaluation type",
        "micro": _metric_counts(true_positive, false_positive, false_negative),
        "per_type": per_type,
        "macro_f1": sum(macro_values) / len(macro_values)
        if macro_values
        else None,
        "macro_scored_types": [
            canonical_type
            for canonical_type, metric in per_type.items()
            if metric["f1"] is not None
        ],
    }


def evaluate_biored(
    dataset: BioREDDataset,
    extractor: EntityExtractor,
    *,
    documents: Sequence[BioREDDocument] | None = None,
    supported_types: Sequence[str] | None = None,
    context_window: int = 80,
    failure_example_limit: int = 5,
) -> dict[str, Any]:
    """Evaluate any normalized entity extractor on BioRED documents.

    The returned mapping is deliberately model-independent.  A caller may add
    predictor metadata such as model identifier and threshold before serializing
    it, as the CLIs do for the current GLiNER baseline and AIONER challenger.

    ``supported_types`` describes the predictor's full canonical capability.  The
    evaluator always computes a separate five-class shared view and a full-schema
    view over those supported classes.
    """

    selected_documents = tuple(dataset.documents if documents is None else documents)
    if failure_example_limit < 0:
        raise ValueError("failure example limit must not be negative")
    full_supported_types = _normalize_scored_types(supported_types)

    shared_scores: list[EntityScore] = []
    full_scores: list[EntityScore] = []
    matched_gold_ids_by_document: dict[str, frozenset[str]] = {}
    failure_counts: Counter[str] = Counter()
    failure_examples: dict[str, list[FailureRecord]] = defaultdict(list)
    gold_total = 0
    predicted_total = 0
    gold_scored_total = 0
    predicted_scored_total = 0
    gold_entity_type_counts: Counter[str] = Counter(
        mention.type
        for document in selected_documents
        for mention in document.mentions
    )
    gold_unscored_counts: Counter[str] = Counter()
    predicted_unscored_counts: Counter[str] = Counter()

    for document in selected_documents:
        predictions = tuple(extractor.extract_entities(document.text))
        shared_score = score_entity_mentions(
            document.id,
            document.text,
            document.mentions,
            predictions,
            scored_types=COMPARABLE_CANONICAL_TYPES,
            context_window=context_window,
            failure_example_limit=0,
        )
        full_score = score_entity_mentions(
            document.id,
            document.text,
            document.mentions,
            predictions,
            scored_types=full_supported_types,
            context_window=context_window,
            failure_example_limit=failure_example_limit,
        )
        shared_scores.append(shared_score)
        full_scores.append(full_score)
        gold_total += len(document.mentions)
        predicted_total += len(predictions)
        gold_scored_total += full_score.gold_scored_count
        predicted_scored_total += full_score.predicted_scored_count
        gold_unscored_counts.update(full_score.gold_unscored_counts)
        predicted_unscored_counts.update(full_score.predicted_unscored_counts)
        matched_gold_ids_by_document[document.id] = full_score.matched_gold_ids
        for category, count in full_score.failure_counts.items():
            failure_counts[category] += count
        for category, records in full_score.failure_examples.items():
            room = failure_example_limit - len(failure_examples[category])
            if room > 0:
                failure_examples[category].extend(records[:room])

    shared_exact_match = _aggregate_entity_scores(
        shared_scores, COMPARABLE_CANONICAL_TYPES
    )
    full_exact_match = _aggregate_entity_scores(full_scores, full_supported_types)
    shared_view = {
        "supported_canonical_types": list(COMPARABLE_CANONICAL_TYPES),
        **shared_exact_match,
    }
    full_view = {
        "supported_canonical_types": list(full_supported_types),
        "unsupported_canonical_types": [
            canonical_type
            for canonical_type in ALL_CANONICAL_TYPES
            if canonical_type not in full_supported_types
        ],
        **full_exact_match,
    }
    failure_report = {
        "counts": {
            category: failure_counts.get(category, 0)
            for category in FAILURE_CATEGORIES
        },
        "examples": {
            category: [
                record.to_dict() for record in failure_examples.get(category, ())
            ]
            for category in FAILURE_CATEGORIES
        },
        "example_limit_per_category": failure_example_limit,
    }
    return {
        "evaluation_name": "BioRED exact-match biomedical NER evaluation",
        "dataset": {
            "path": str(dataset.path),
            "split": dataset.split,
            "sha256": dataset.sha256,
            "source": dataset.source,
            "date": dataset.date,
            "key": dataset.key,
            "documents_in_source": len(dataset.documents),
            "documents_evaluated": len(selected_documents),
        },
        "taxonomy": _taxonomy_report(),
        "counts": {
            "documents_evaluated": len(selected_documents),
            "gold_entities": gold_total,
            "gold_entities_by_type": dict(sorted(gold_entity_type_counts.items())),
            "gold_entities_scored": gold_scored_total,
            "predicted_entities": predicted_total,
            "predicted_entities_scored": predicted_scored_total,
        },
        "schema_coverage": {
            "gold": {
                "total": gold_total,
                "scored": gold_scored_total,
                "unscored": gold_total - gold_scored_total,
                "unscored_by_type": dict(sorted(gold_unscored_counts.items())),
                "scored_fraction": _ratio(gold_scored_total, gold_total),
            },
            "predicted": {
                "total": predicted_total,
                "scored": predicted_scored_total,
                "unscored": predicted_total - predicted_scored_total,
                "unscored_by_type": dict(sorted(predicted_unscored_counts.items())),
                "scored_fraction": _ratio(predicted_scored_total, predicted_total),
            },
        },
        "metrics": {
            "primary": "shared_class",
            # ``exact_match`` remains an alias for callers of the original
            # five-class report contract.
            "exact_match": shared_view,
            "shared_class": shared_view,
            "full_schema": full_view,
        },
        "graph_critical_entity_recall": _graph_critical_recall(
            selected_documents, matched_gold_ids_by_document
        ),
        "failure_analysis": failure_report,
        "limitations": [
            "Primary metrics use exact half-open character spans and canonical type only; no fuzzy matching is applied.",
            "Unsupported schema labels are reported separately and excluded from primary comparable-class metrics.",
            "Failure categories are deterministic diagnostics and do not change the primary counts.",
            "Graph-critical recall uses BioRED relation concept participation only as an NER diagnostic; no relation model is invoked.",
            "This report is baseline evidence and does not establish production readiness or rank a candidate model.",
        ],
    }


__all__ = [
    "ALL_CANONICAL_TYPES",
    "BIORED_INTERNAL_TYPE_TO_CANONICAL",
    "COMPARABLE_CANONICAL_TYPES",
    "FAILURE_CATEGORIES",
    "FAILURE_MISSED_ENTITY",
    "FAILURE_OVERLAPPING_PREDICTION",
    "FAILURE_SPAN_MISMATCH",
    "FAILURE_SPURIOUS_ENTITY",
    "FAILURE_UNSUPPORTED_GOLD",
    "FAILURE_UNSUPPORTED_PREDICTED",
    "FAILURE_WRONG_TYPE",
    "PREDICTED_TYPE_TO_CANONICAL",
    "EntityScore",
    "FailureRecord",
    "canonical_gold_type",
    "canonical_predicted_type",
    "evaluate_biored",
    "score_entity_mentions",
]
