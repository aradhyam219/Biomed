"""Cross-corpus MedMentions NER parsing, scoring, and reporting.

The MedMentions path is intentionally exact-span NER only. UMLS identifiers
remain source metadata; they are not used for normalization or for scoring.
Only semantic types with an explicit, reviewable mapping to the two requested
BioRED-style classes are scored.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import urllib.request

from .entity_extraction import Entity
from .ner_evaluation import canonical_predicted_type


MEDMENTIONS_CORPUS_URL = (
    "https://raw.githubusercontent.com/chanzuckerberg/MedMentions/"
    "master/st21pv/data/corpus_pubtator.txt.gz"
)
MEDMENTIONS_SPLIT_URL = (
    "https://raw.githubusercontent.com/chanzuckerberg/MedMentions/"
    "master/full/data/corpus_pubtator_pmids_{split}.txt"
)
MEDMENTIONS_SOURCE_REPOSITORY = "https://github.com/chanzuckerberg/MedMentions"
MEDMENTIONS_SCORED_TYPES = (
    "ChemicalEntity",
    "DiseaseOrPhenotypicFeature",
)
MEDMENTIONS_MAPPING = {
    "T033": "DiseaseOrPhenotypicFeature",
    "T037": "DiseaseOrPhenotypicFeature",
    "T047": "DiseaseOrPhenotypicFeature",
    "T184": "DiseaseOrPhenotypicFeature",
    "T190": "DiseaseOrPhenotypicFeature",
    "T191": "DiseaseOrPhenotypicFeature",
    "T103": "ChemicalEntity",
}
MEDMENTIONS_MAPPING_DESCRIPTIONS = {
    "T033": "Finding; retained as a phenotypic/disease-style mention",
    "T037": "Injury or Poisoning; retained as a disease/phenotypic mention",
    "T047": "Disease or Syndrome",
    "T184": "Sign or Symptom",
    "T190": "Anatomical Abnormality",
    "T191": "Neoplastic Process",
    "T103": "Chemical",
}
FAILURE_MISSED = "missed_scored_gold"
FAILURE_SPURIOUS = "spurious_scored_prediction"
FAILURE_WRONG_TYPE = "same_span_different_type"
FAILURE_BOUNDARY = "overlapping_same_type_boundary"
FAILURE_CROSS_TYPE = "overlapping_different_type"
FAILURE_UNSUPPORTED_GOLD = "unsupported_gold_semantic_type"
FAILURE_AMBIGUOUS_GOLD = "ambiguous_gold_semantic_type"
FAILURE_UNSUPPORTED_PREDICTED = "unsupported_predicted_type"
FAILURE_CATEGORIES = (
    FAILURE_MISSED,
    FAILURE_SPURIOUS,
    FAILURE_WRONG_TYPE,
    FAILURE_BOUNDARY,
    FAILURE_CROSS_TYPE,
    FAILURE_UNSUPPORTED_GOLD,
    FAILURE_AMBIGUOUS_GOLD,
    FAILURE_UNSUPPORTED_PREDICTED,
)


@dataclass(frozen=True)
class MedMentionsMention:
    """One MedMentions annotation with explicit taxonomy mapping status."""

    id: str
    text: str
    start: int
    end: int
    cui: str
    semantic_types: tuple[str, ...]
    canonical_type: str | None
    mapping_status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable gold mention record."""

        return {
            "id": self.id,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "cui": self.cui,
            "semantic_types": list(self.semantic_types),
            "canonical_type": self.canonical_type,
            "mapping_status": self.mapping_status,
        }


@dataclass(frozen=True)
class MedMentionsDocument:
    """One MedMentions title/abstract document."""

    id: str
    text: str
    mentions: tuple[MedMentionsMention, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable document record."""

        return {
            "id": self.id,
            "text": self.text,
            "text_sha256": hashlib.sha256(self.text.encode("utf-8")).hexdigest(),
            "mentions": [mention.to_dict() for mention in self.mentions],
        }


@dataclass(frozen=True)
class MedMentionsDataset:
    """Selected MedMentions documents plus source identity/checksums."""

    split: str
    corpus_url: str
    corpus_sha256: str
    split_url: str | None
    split_sha256: str | None
    source_repository: str
    documents: tuple[MedMentionsDocument, ...]

    def to_dict(self, *, include_documents: bool = False) -> dict[str, Any]:
        """Serialize dataset identity and optional cached documents."""

        result: dict[str, Any] = {
            "name": "MedMentions ST21pv",
            "split": self.split,
            "source_repository": self.source_repository,
            "corpus_url": self.corpus_url,
            "corpus_sha256": self.corpus_sha256,
            "split_url": self.split_url,
            "split_sha256": self.split_sha256,
            "document_count": len(self.documents),
        }
        if include_documents:
            result["documents"] = [document.to_dict() for document in self.documents]
        return result


def _fetch(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
    timeout: float = 120.0,
) -> bytes:
    """Fetch one public corpus file with a descriptive user agent."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "biomedical-extractor/medmentions-evaluation"},
    )
    fetch = opener or urllib.request.urlopen
    with fetch(request, timeout=timeout) as response:
        return response.read()


def _map_semantic_types(
    semantic_types: Sequence[str],
) -> tuple[str | None, str]:
    """Map only explicit, unambiguous semantic-type sets."""

    values = tuple(sorted(set(value for value in semantic_types if value)))
    mapped = {MEDMENTIONS_MAPPING[value] for value in values if value in MEDMENTIONS_MAPPING}
    unsupported = set(values) - set(MEDMENTIONS_MAPPING)
    if len(mapped) == 1 and not unsupported:
        return next(iter(mapped)), "scored"
    if len(mapped) > 1:
        return None, "ambiguous"
    return None, "unsupported"


def medmentions_semantic_type_mapping(semantic_types: Sequence[str]) -> dict[str, Any]:
    """Expose the inspectable MedMentions mapping decision."""

    canonical_type, status = _map_semantic_types(semantic_types)
    return {
        "semantic_types": list(sorted(set(semantic_types))),
        "canonical_type": canonical_type,
        "status": status,
        "mapped_semantic_types": {
            value: MEDMENTIONS_MAPPING_DESCRIPTIONS[value]
            for value in sorted(set(semantic_types))
            if value in MEDMENTIONS_MAPPING_DESCRIPTIONS
        },
    }


def _parse_block(
    block: str,
    *,
    selected_ids: set[str] | None,
) -> MedMentionsDocument | None:
    """Parse one PubTator title/abstract block."""

    title = ""
    abstract = ""
    annotation_lines: list[list[str]] = []
    document_id = ""
    for line in block.splitlines():
        line = line.rstrip("\r")
        if not line:
            continue
        if "|t|" in line:
            document_id, title = line.split("|t|", 1)
        elif "|a|" in line:
            current_id, abstract = line.split("|a|", 1)
            if document_id and current_id != document_id:
                raise ValueError(f"MedMentions title/abstract ID mismatch: {document_id}")
            document_id = current_id
        else:
            annotation_lines.append(line.split("\t"))
    if not document_id:
        return None
    if selected_ids is not None and document_id not in selected_ids:
        return None
    join_candidates = [title + " " + abstract, title + abstract]
    parsed_rows: list[tuple[int, int, str, str, tuple[str, ...]]] = []
    for fields in annotation_lines:
        if len(fields) < 6:
            raise ValueError(
                f"MedMentions annotation has fewer than six fields: {fields!r}"
            )
        row_id, start, end, mention_text, semantic_field, cui = fields[:6]
        if row_id != document_id:
            raise ValueError(f"MedMentions annotation ID mismatch: {row_id}")
        semantic_types = tuple(
            sorted(value for value in semantic_field.split("|") if value)
        )
        parsed_rows.append(
            (int(start), int(end), mention_text, cui, semantic_types)
        )
    source_text = next(
        (
            candidate
            for candidate in join_candidates
            if all(candidate[start:end] == mention_text for start, end, mention_text, _, _ in parsed_rows)
        ),
        None,
    )
    if source_text is None:
        raise ValueError(
            f"MedMentions annotations do not resolve against title/abstract text: {document_id}"
        )
    mentions: list[MedMentionsMention] = []
    for index, (start, end, mention_text, cui, semantic_types) in enumerate(
        parsed_rows, start=1
    ):
        canonical_type, status = _map_semantic_types(semantic_types)
        mentions.append(
            MedMentionsMention(
                id=f"{document_id}:M{index}",
                text=mention_text,
                start=start,
                end=end,
                cui=cui,
                semantic_types=semantic_types,
                canonical_type=canonical_type,
                mapping_status=status,
            )
        )
    return MedMentionsDocument(document_id, source_text, tuple(mentions))


def parse_medmentions_pubtator(
    raw: bytes,
    *,
    selected_ids: Sequence[str] | None = None,
) -> tuple[MedMentionsDocument, ...]:
    """Parse MedMentions ST21pv PubTator bytes with exact source offsets."""

    selected = None if selected_ids is None else set(str(value) for value in selected_ids)
    decoded = raw.decode("utf-8")
    documents = [
        document
        for block in decoded.strip().split("\n\n")
        if (document := _parse_block(block, selected_ids=selected)) is not None
    ]
    return tuple(documents)


def acquire_medmentions(
    cache_dir: Path,
    *,
    split: str = "test",
    refresh: bool = False,
    opener: Callable[..., Any] | None = None,
) -> MedMentionsDataset:
    """Download and parse MedMentions ST21pv, defaulting to its official test IDs."""

    if split not in {"all", "trng", "dev", "test"}:
        raise ValueError("MedMentions split must be all, trng, dev, or test")
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = cache_dir / "corpus_pubtator.txt.gz"
    if refresh or not corpus_path.exists():
        corpus_raw = _fetch(MEDMENTIONS_CORPUS_URL, opener=opener)
        corpus_path.write_bytes(corpus_raw)
    else:
        corpus_raw = corpus_path.read_bytes()
    corpus_sha256 = hashlib.sha256(corpus_raw).hexdigest()
    split_url = None
    split_sha256 = None
    selected_ids: tuple[str, ...] | None = None
    if split != "all":
        split_url = MEDMENTIONS_SPLIT_URL.format(split=split)
        split_path = cache_dir / f"corpus_pubtator_pmids_{split}.txt"
        if refresh or not split_path.exists():
            split_raw = _fetch(split_url, opener=opener)
            split_path.write_bytes(split_raw)
        else:
            split_raw = split_path.read_bytes()
        split_sha256 = hashlib.sha256(split_raw).hexdigest()
        selected_ids = tuple(
            line.strip() for line in split_raw.decode("utf-8").splitlines() if line.strip()
        )
    documents = parse_medmentions_pubtator(
        gzip.decompress(corpus_raw),
        selected_ids=selected_ids,
    )
    if not documents:
        raise ValueError("MedMentions acquisition produced no selected documents")
    if selected_ids is not None and {document.id for document in documents} != set(
        selected_ids
    ):
        missing = sorted(set(selected_ids) - {document.id for document in documents})
        raise ValueError(f"MedMentions split IDs missing from corpus: {missing[:10]}")
    return MedMentionsDataset(
        split=split,
        corpus_url=MEDMENTIONS_CORPUS_URL,
        corpus_sha256=corpus_sha256,
        split_url=split_url,
        split_sha256=split_sha256,
        source_repository=MEDMENTIONS_SOURCE_REPOSITORY,
        documents=documents,
    )


def _predicted_type(entity: Entity) -> str | None:
    """Map a normalized model label to the two scored classes."""

    canonical = canonical_predicted_type(entity.type)
    return canonical if canonical in MEDMENTIONS_SCORED_TYPES else None


def _metric_counts(
    tp: int,
    fp: int,
    fn: int,
    *,
    gold: int,
    predicted: int,
) -> dict[str, Any]:
    """Compute exact count-derived precision, recall, and F1."""

    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "gold": gold,
        "predicted": predicted,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _span_overlap(
    left_start: int,
    left_end: int,
    right_start: int,
    right_end: int,
) -> bool:
    """Return whether two non-empty half-open spans overlap."""

    return max(left_start, right_start) < min(left_end, right_end)


def _gold_payload(mention: MedMentionsMention) -> dict[str, Any]:
    """Serialize one gold mention for bounded failure diagnostics."""

    return mention.to_dict()


def _pred_payload(entity: Entity) -> dict[str, Any]:
    """Serialize one normalized prediction for bounded failure diagnostics."""

    return {
        "id": entity.id,
        "text": entity.text,
        "type": entity.type,
        "canonical_type": _predicted_type(entity),
        "start": entity.start,
        "end": entity.end,
        "score": entity.score,
    }


def _score_document(
    document: MedMentionsDocument,
    predictions: Sequence[Entity],
    *,
    example_limit: int,
) -> dict[str, Any]:
    """Score one document and classify bounded exact-span failure diagnostics."""

    scored_gold = [
        mention
        for mention in document.mentions
        if mention.mapping_status == "scored" and mention.canonical_type
    ]
    unsupported_gold = [
        mention for mention in document.mentions if mention.mapping_status == "unsupported"
    ]
    ambiguous_gold = [
        mention for mention in document.mentions if mention.mapping_status == "ambiguous"
    ]
    scored_predictions = [
        entity for entity in predictions if _predicted_type(entity) is not None
    ]
    unsupported_predictions = [
        entity for entity in predictions if _predicted_type(entity) is None
    ]
    gold_by_key: defaultdict[tuple[int, int, str], list[MedMentionsMention]] = defaultdict(
        list
    )
    pred_by_key: defaultdict[tuple[int, int, str], list[Entity]] = defaultdict(list)
    for mention in scored_gold:
        gold_by_key[(mention.start, mention.end, mention.canonical_type)].append(mention)
    for entity in scored_predictions:
        pred_by_key[(entity.start, entity.end, _predicted_type(entity))].append(entity)
    matched_gold: set[str] = set()
    matched_pred: set[str] = set()
    per_type: dict[str, Counter[str]] = {
        entity_type: Counter() for entity_type in MEDMENTIONS_SCORED_TYPES
    }
    for entity_type in MEDMENTIONS_SCORED_TYPES:
        per_type[entity_type]["gold"] = sum(
            len(items)
            for (start, end, canonical), items in gold_by_key.items()
            if canonical == entity_type
        )
        per_type[entity_type]["predicted"] = sum(
            len(items)
            for (start, end, canonical), items in pred_by_key.items()
            if canonical == entity_type
        )
    for key in sorted(set(gold_by_key) | set(pred_by_key)):
        gold_items = gold_by_key.get(key, [])
        pred_items = pred_by_key.get(key, [])
        count = min(len(gold_items), len(pred_items))
        for mention, entity in zip(gold_items[:count], pred_items[:count]):
            matched_gold.add(mention.id)
            matched_pred.add(entity.id)
            per_type[key[2]]["tp"] += 1

    remaining_gold = [mention for mention in scored_gold if mention.id not in matched_gold]
    remaining_pred = [entity for entity in scored_predictions if entity.id not in matched_pred]
    failure_counts: Counter[str] = Counter()
    examples: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    def add_failure(
        category: str,
        *,
        gold: MedMentionsMention | None = None,
        predicted: Entity | None = None,
    ) -> None:
        failure_counts[category] += 1
        if len(examples[category]) < example_limit:
            starts = [
                item.start
                for item in (gold, predicted)
                if item is not None
            ]
            ends = [
                item.end
                for item in (gold, predicted)
                if item is not None
            ]
            start = min(starts) if starts else 0
            end = max(ends) if ends else start
            examples[category].append(
                {
                    "document_id": document.id,
                    "context": document.text[max(0, start - 80) : min(len(document.text), end + 80)],
                    "gold": None if gold is None else _gold_payload(gold),
                    "predicted": None if predicted is None else _pred_payload(predicted),
                }
            )

    paired_gold: set[str] = set()
    paired_pred: set[str] = set()
    candidates: list[tuple[int, int, int, int, int, str]] = []
    for gold_index, gold in enumerate(remaining_gold):
        for pred_index, predicted in enumerate(remaining_pred):
            predicted_type = _predicted_type(predicted)
            if not _span_overlap(gold.start, gold.end, predicted.start, predicted.end):
                continue
            if gold.start == predicted.start and gold.end == predicted.end:
                category = FAILURE_WRONG_TYPE
                priority = 0
            elif gold.canonical_type == predicted_type:
                category = FAILURE_BOUNDARY
                priority = 1
            else:
                category = FAILURE_CROSS_TYPE
                priority = 2
            candidates.append(
                (
                    priority,
                    min(gold.start, predicted.start),
                    min(gold.end, predicted.end),
                    gold_index,
                    pred_index,
                    category,
                )
            )
    candidates.sort()
    for _, _, _, gold_index, pred_index, category in candidates:
        if gold_index in paired_gold or pred_index in paired_pred:
            continue
        paired_gold.add(gold_index)
        paired_pred.add(pred_index)
        gold = remaining_gold[gold_index]
        predicted = remaining_pred[pred_index]
        add_failure(category, gold=gold, predicted=predicted)

    for index, gold in enumerate(remaining_gold):
        if index not in paired_gold:
            add_failure(FAILURE_MISSED, gold=gold)
            per_type[gold.canonical_type]["fn"] += 1
    for index, predicted in enumerate(remaining_pred):
        if index not in paired_pred:
            add_failure(FAILURE_SPURIOUS, predicted=predicted)
            per_type[_predicted_type(predicted)]["fp"] += 1
    for mention in unsupported_gold:
        add_failure(FAILURE_UNSUPPORTED_GOLD, gold=mention)
    for mention in ambiguous_gold:
        add_failure(FAILURE_AMBIGUOUS_GOLD, gold=mention)
    for predicted in unsupported_predictions:
        add_failure(FAILURE_UNSUPPORTED_PREDICTED, predicted=predicted)

    for entity_type, counts in per_type.items():
        counts.setdefault("tp", 0)
        counts.setdefault("fp", 0)
        counts.setdefault("fn", 0)
    return {
        "metrics": {
            "per_type": {
                entity_type: _metric_counts(
                    counts["tp"],
                    counts["fp"],
                    counts["fn"],
                    gold=counts["gold"],
                    predicted=counts["predicted"],
                )
                for entity_type, counts in per_type.items()
            }
        },
        "counts": {
            "gold_mentions": len(document.mentions),
            "gold_scored_mentions": len(scored_gold),
            "gold_unsupported_mentions": len(unsupported_gold),
            "gold_ambiguous_mentions": len(ambiguous_gold),
            "predicted_mentions": len(predictions),
            "predicted_scored_mentions": len(scored_predictions),
            "predicted_unsupported_mentions": len(unsupported_predictions),
        },
        "failure_counts": {
            category: failure_counts.get(category, 0) for category in FAILURE_CATEGORIES
        },
        "failure_examples": {
            category: list(examples.get(category, ()))
            for category in FAILURE_CATEGORIES
            if examples.get(category)
        },
    }


def evaluate_medmentions(
    dataset: MedMentionsDataset,
    predictions_by_model: Mapping[str, Mapping[str, Sequence[Entity]]],
    *,
    predictor_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    example_limit: int = 5,
    biored_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute exact MedMentions NER metrics for each active model."""

    if example_limit < 0:
        raise ValueError("example_limit must not be negative")
    expected_ids = {document.id for document in dataset.documents}
    metadata = predictor_metadata or {}
    model_reports: dict[str, Any] = {}
    for model_name, predictions in predictions_by_model.items():
        if set(predictions) != expected_ids:
            raise ValueError(f"{model_name} predictions do not cover MedMentions exactly")
        document_scores = {
            document.id: _score_document(
                document,
                predictions[document.id],
                example_limit=example_limit,
            )
            for document in dataset.documents
        }
        per_type_counts: dict[str, Counter[str]] = {
            entity_type: Counter() for entity_type in MEDMENTIONS_SCORED_TYPES
        }
        counts = Counter()
        failures = Counter()
        failure_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for score in document_scores.values():
            counts.update(score["counts"])
            failures.update(score["failure_counts"])
            for category, values in score["failure_examples"].items():
                remaining = example_limit - len(failure_examples[category])
                if remaining > 0:
                    failure_examples[category].extend(values[:remaining])
            for entity_type, metric in score["metrics"]["per_type"].items():
                per_type_counts[entity_type]["tp"] += metric["tp"]
                per_type_counts[entity_type]["fp"] += metric["fp"]
                per_type_counts[entity_type]["fn"] += metric["fn"]
                per_type_counts[entity_type]["gold"] += metric["gold"]
                per_type_counts[entity_type]["predicted"] += metric["predicted"]
        per_type = {
            entity_type: _metric_counts(
                values["tp"],
                values["fp"],
                values["fn"],
                gold=values["gold"],
                predicted=values["predicted"],
            )
            for entity_type, values in per_type_counts.items()
        }
        micro = _metric_counts(
            sum(metric["tp"] for metric in per_type.values()),
            sum(metric["fp"] for metric in per_type.values()),
            sum(metric["fn"] for metric in per_type.values()),
            gold=sum(metric["gold"] for metric in per_type.values()),
            predicted=sum(metric["predicted"] for metric in per_type.values()),
        )
        macro_values = [metric["f1"] for metric in per_type.values() if metric["f1"] is not None]
        model_reports[model_name] = {
            "predictor": dict(metadata.get(model_name, {})),
            "counts": dict(sorted(counts.items())),
            "metrics": {
                "per_type": per_type,
                "micro": micro,
                "macro_f1": sum(macro_values) / len(macro_values)
                if macro_values
                else None,
            },
            "failure_counts": {
                category: failures.get(category, 0) for category in FAILURE_CATEGORIES
            },
            "failure_examples": dict(failure_examples),
        }
    report = {
        "evaluation_name": (
            "Exploratory AIONER versus HunFlair2 MedMentions ST21pv "
            "cross-schema stress test"
        ),
        "evidence_role": (
            "exploratory cross-schema stress test using explicit UMLS "
            "semantic-type mappings"
        ),
        "clean_model_selection_evidence": False,
        "report_date": "2026-09-18",
        "dataset": dataset.to_dict(include_documents=False),
        "mapping": {
            "scored_types": list(MEDMENTIONS_SCORED_TYPES),
            "semantic_type_to_canonical": dict(sorted(MEDMENTIONS_MAPPING.items())),
            "descriptions": dict(sorted(MEDMENTIONS_MAPPING_DESCRIPTIONS.items())),
            "unsupported_and_ambiguous_are_excluded_from_primary_metrics": True,
            "umls_normalization_scored": False,
        },
        "models": model_reports,
        "independence_verification": {
            "AIONER": {
                "documented_training_corpora_checked": [
                    "BioRED",
                    "NLM-Gene",
                    "GNormPlus",
                    "NCBI Disease",
                    "NLM-Chem",
                    "BC5CDR",
                    "Linnaeus",
                    "Species-800",
                    "tmVar3",
                    "BioID",
                ],
                "medmentions_listed_in_training_recipe": False,
                "evidence": "Official AIONER paper Table 1 and released upstream data manifest",
                "evidence_urls": [
                    "https://doi.org/10.1093/bioinformatics/btad310",
                    "https://github.com/ncbi/AIONER",
                ],
            },
            "HunFlair2": {
                "documented_training_corpora_checked": [
                    "BioRED",
                    "NLM Gene",
                    "GNormPlus",
                    "Linnaeus",
                    "S800",
                    "NLM Chem",
                    "SCAI Chemical",
                    "NCBI Disease",
                    "SCAI disease",
                ],
                "medmentions_listed_in_training_recipe": False,
                "evidence": "HunFlair2 paper Section 3 and cross-corpus protocol",
                "evidence_urls": [
                    "https://arxiv.org/html/2402.12372",
                    "https://github.com/flairNLP/flair",
                ],
            },
            "independent_under_documented_recipes": True,
            "qualification": (
                "This verifies absence from the documented supervised training "
                "recipes checked for the cached artifacts; it is not a claim "
                "about every possible pretraining source."
            ),
        },
        "biored_reference": _biored_reference(biored_report),
        "limitations": [
            "MedMentions UMLS identifiers are not normalized or used for scoring.",
            "Only explicit, unambiguous semantic-type mappings are scored; unsupported and ambiguous gold mentions are reported separately.",
            "Exact character span and canonical type are required for a true positive.",
            "The default run uses the official MedMentions test PMID split; the split identity and checksums are recorded.",
            "This exploratory cross-schema stress test is not clean model-selection evidence comparable to BioRED or CRAFT.",
            "Annotation conventions differ from BioRED and CRAFT, so cross-corpus scores are not directly interchangeable.",
        ],
    }
    report["comparison"] = _comparison_to_biored(report)
    validate_medmentions_report_arithmetic(report)
    return report


def _biored_reference(report: Mapping[str, Any] | None) -> dict[str, Any]:
    """Extract comparable BioRED reference values when a frozen report exists."""

    if not report:
        return {"available": False}
    result: dict[str, Any] = {"available": True}
    for model in ("AIONER", "HunFlair2"):
        model_report = report.get("models", {}).get(model, {})
        metrics = model_report.get("metrics", {}).get("shared_class", {})
        if not metrics:
            # The repository's frozen BioRED report predates the generic
            # ``metrics.shared_class`` shape and stores the same values under
            # ``shared_class_head_to_head.models``. Accept both report shapes
            # without changing the BioRED artifact.
            metrics = (
                report.get("shared_class_head_to_head", {})
                .get("models", {})
                .get(model, {})
            )
        result[model] = {
            "micro_f1": metrics.get("micro", {}).get("f1"),
            "per_type_f1": {
                key: value.get("f1")
                for key, value in metrics.get("per_type", {}).items()
            },
        }
    return result


def _comparison_to_biored(report: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize ordering and descriptive drops against frozen BioRED values."""

    models = list(report["models"])
    f1_values = {
        model: report["models"][model]["metrics"]["micro"]["f1"] for model in models
    }
    ordered = sorted(
        models,
        key=lambda model: (
            -(f1_values[model] if f1_values[model] is not None else -1),
            model,
        ),
    )
    reference = report["biored_reference"]
    result: dict[str, Any] = {
        "medmentions_micro_f1_order": ordered,
        "biored_micro_f1_order": None,
        "ordering_differs": None,
        "substantial_drop_threshold": 0.10,
        "models": {},
    }
    if reference.get("available"):
        reference_values = {
            model: reference.get(model, {}).get("micro_f1") for model in models
        }
        reference_ordered = sorted(
            models,
            key=lambda model: (
                -(reference_values[model] if reference_values[model] is not None else -1),
                model,
            ),
        )
        result["biored_micro_f1_order"] = reference_ordered
        result["ordering_differs"] = ordered != reference_ordered
        for model in models:
            cross_f1 = f1_values[model]
            biored_f1 = reference_values[model]
            result["models"][model] = {
                "medmentions_micro_f1": cross_f1,
                "biored_shared_micro_f1": biored_f1,
                "micro_f1_drop": (
                    None
                    if cross_f1 is None or biored_f1 is None
                    else biored_f1 - cross_f1
                ),
                "substantial_micro_drop": (
                    None
                    if cross_f1 is None or biored_f1 is None
                    else biored_f1 - cross_f1 >= 0.10
                ),
            }
    return result


def validate_medmentions_report_arithmetic(report: Mapping[str, Any]) -> None:
    """Validate exact P/R/F1 and macro arithmetic in a MedMentions report."""

    for model, model_report in report["models"].items():
        metrics = model_report["metrics"]
        micro = metrics["micro"]
        expected_micro = _metric_counts(
            sum(metric["tp"] for metric in metrics["per_type"].values()),
            sum(metric["fp"] for metric in metrics["per_type"].values()),
            sum(metric["fn"] for metric in metrics["per_type"].values()),
            gold=sum(metric["gold"] for metric in metrics["per_type"].values()),
            predicted=sum(
                metric["predicted"] for metric in metrics["per_type"].values()
            ),
        )
        for key in ("tp", "fp", "fn", "gold", "predicted", "precision", "recall", "f1"):
            if micro[key] != expected_micro[key]:
                raise ValueError(f"{model} micro metric arithmetic mismatch: {key}")
        values = [
            metric["f1"]
            for metric in metrics["per_type"].values()
            if metric["f1"] is not None
        ]
        expected_macro = sum(values) / len(values) if values else None
        actual_macro = metrics["macro_f1"]
        if actual_macro is None or expected_macro is None:
            if actual_macro != expected_macro:
                raise ValueError(f"{model} macro metric arithmetic mismatch")
        elif abs(actual_macro - expected_macro) > 1e-12:
            raise ValueError(f"{model} macro metric arithmetic mismatch")


def render_medmentions_markdown(report: Mapping[str, Any]) -> str:
    """Render the reviewer-facing MedMentions exact-NER report."""

    dataset = report["dataset"]
    lines = [
        "# Exploratory MedMentions cross-schema stress test",
        "",
        "This is an exploratory cross-schema stress test using explicit UMLS "
        "semantic-type mappings. It is not clean model-selection evidence "
        "comparable to BioRED or CRAFT. UMLS normalization is intentionally out "
        "of scope.",
        "",
        "## Dataset identity",
        "",
        f"- Split: {dataset['split']}",
        f"- Documents: {dataset['document_count']}",
        f"- Corpus URL: {dataset['corpus_url']}",
        f"- Corpus SHA-256: {dataset['corpus_sha256']}",
        f"- Split URL: {dataset.get('split_url') or 'all documents'}",
        f"- Split SHA-256: {dataset.get('split_sha256') or 'N/A'}",
        "",
        "## Explicit semantic-type mapping",
        "",
        "| Semantic type | Canonical class |",
        "|---|---|",
    ]
    for semantic_type, canonical in sorted(
        report["mapping"]["semantic_type_to_canonical"].items()
    ):
        lines.append(f"| {semantic_type} | {canonical} |")
    lines.extend(
        [
            "",
            "Unsupported and ambiguous gold annotations are retained in counts "
            "but excluded from primary precision, recall, and F1.",
            "",
            "## Exact NER results",
            "",
            "| Model | Gold scored | Predicted scored | Precision | Recall | Micro F1 | Macro F1 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model, model_report in report["models"].items():
        metric = model_report["metrics"]
        lines.append(
            f"| {model} | {metric['micro']['gold']} | "
            f"{metric['micro']['predicted']} | {metric['micro']['precision']} | "
            f"{metric['micro']['recall']} | {metric['micro']['f1']} | "
            f"{metric['macro_f1']} |"
        )
    lines.extend(
        [
            "",
            "### Per type",
            "",
            "| Type | AIONER P | AIONER R | AIONER F1 | HunFlair2 P | HunFlair2 R | HunFlair2 F1 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for entity_type in MEDMENTIONS_SCORED_TYPES:
        aioner = report["models"]["AIONER"]["metrics"]["per_type"][entity_type]
        hunflair2 = report["models"]["HunFlair2"]["metrics"]["per_type"][entity_type]
        lines.append(
            f"| {entity_type} | {aioner['precision']} | {aioner['recall']} | "
            f"{aioner['f1']} | {hunflair2['precision']} | "
            f"{hunflair2['recall']} | {hunflair2['f1']} |"
        )
    lines.extend(
        [
            "",
            "## Failure categories",
            "",
            "| Category | AIONER | HunFlair2 |",
            "|---|---:|---:|",
        ]
    )
    for category in FAILURE_CATEGORIES:
        lines.append(
            f"| {category} | "
            f"{report['models']['AIONER']['failure_counts'][category]} | "
            f"{report['models']['HunFlair2']['failure_counts'][category]} |"
        )
    lines.extend(
        [
            "",
            "## BioRED comparison",
            "",
            f"- MedMentions ordering: {report['comparison']['medmentions_micro_f1_order']}",
            f"- BioRED ordering: {report['comparison']['biored_micro_f1_order']}",
            f"- Ordering differs: {report['comparison']['ordering_differs']}",
            "",
            "## Independence and caveats",
            "",
            "- MedMentions is absent from the documented AIONER and HunFlair2 supervised training recipes checked for these artifacts.",
            "- Exact source spans and explicit canonical types are required; no fuzzy or ontology-linking credit is given.",
            "- BioRED and MedMentions use different annotation conventions, so scores should not be treated as directly interchangeable.",
        ]
    )
    return "\n".join(lines) + "\n"


__all__ = [
    "FAILURE_CATEGORIES",
    "MEDMENTIONS_MAPPING",
    "MEDMENTIONS_SCORED_TYPES",
    "MedMentionsDataset",
    "MedMentionsDocument",
    "MedMentionsMention",
    "acquire_medmentions",
    "evaluate_medmentions",
    "medmentions_semantic_type_mapping",
    "parse_medmentions_pubtator",
    "render_medmentions_markdown",
    "validate_medmentions_report_arithmetic",
]
