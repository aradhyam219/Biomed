"""Run the V0-B BioRED gold-entity GLiREL development baseline.

This command loads the official development BioC JSON, supplies its gold mentions
directly to the existing relation stage, caches threshold-free scores after each
document, calibrates one threshold without rerunning inference, and writes a compact
machine-readable result. GLiNER is deliberately never loaded.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from biomedical_extractor.biored import (
    BIORED_RELATION_LABELS,
    CANONICAL_TO_PROMPT,
    RELATION_ENTITY_TYPES,
    BioREDDataset,
    BioREDDocument,
    ScoredRelation,
    TypedRelation,
    aggregate_mention_predictions,
    calibrate_threshold,
    deserialize_scored_relations,
    load_biored,
    score_relations,
    serialize_scored_relations,
)
from biomedical_extractor.pipeline import (
    DEFAULT_RELATION_MODEL,
    BiomedicalExtractor,
    ExtractionConfig,
    _tokenize,
)


RAW_TOP_K = 1
FINAL_TOP_K = 1
GLIREL_TRAINING_MAX_LEN = 512


class _ForbiddenEntityModel:
    """Fail loudly if evaluation accidentally invokes production NER."""

    def predict_entities(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("BioRED gold-entity evaluation must not run GLiNER")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate GLiREL on BioRED dev relations using gold entities."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to official Dev.BioC.JSON or its containing directory.",
    )
    parser.add_argument("--split", default="dev", choices=("dev",))
    parser.add_argument(
        "--limit",
        type=int,
        help="Evaluate only the first N dev documents for a smoke/subset run.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(".cache/biored_v0b_raw.json"),
        help="Incremental raw-score cache; matching documents are never inferred twice.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".cache/biored_v0b_summary.json"),
        help="Machine-readable evaluation summary.",
    )
    parser.add_argument("--device", help="Torch device, for example cpu or cuda.")
    parser.add_argument("--model", default=DEFAULT_RELATION_MODEL)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use only already-cached Hugging Face model files.",
    )
    return parser


def _load_model(model_name: str, device: str | None, offline: bool) -> Any:
    """Load only GLiREL so the experiment remains isolated from GLiNER."""

    from glirel import GLiREL
    import torch

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = GLiREL.from_pretrained(
        model_name,
        map_location=selected_device,
        local_files_only=offline,
    )
    model.eval()
    return model


def _extractor(model: Any, device: str | None, model_name: str) -> BiomedicalExtractor:
    """Bind the real relation model to V0-A's supplied-entity adapter."""

    config = ExtractionConfig(
        entity_labels=tuple(sorted(RELATION_ENTITY_TYPES)),
        relation_labels=tuple(CANONICAL_TO_PROMPT.values()),
        relation_threshold=0.0,
        # BioRED permits one relation type per pair. Pair-family constraints are
        # applied after inference because GLiREL's primitive cannot express the
        # symmetric eight-family union exactly.
        relation_top_k=RAW_TOP_K,
        relation_model=model_name,
        device=device,
    )
    return BiomedicalExtractor(_ForbiddenEntityModel(), model, config)


def _cache_identity(dataset: BioREDDataset, model_name: str) -> dict[str, Any]:
    """Return every input that makes cached inference scores reusable."""

    return {
        "format_version": 1,
        "dataset_sha256": dataset.sha256,
        "split": dataset.split,
        "model": model_name,
        "relation_prompts": CANONICAL_TO_PROMPT,
        "raw_top_k": RAW_TOP_K,
        "final_top_k": FINAL_TOP_K,
    }


def _read_cache(path: Path, identity: Mapping[str, Any]) -> dict[str, Any]:
    """Load a compatible incremental score cache or initialize an empty one."""

    if not path.exists():
        return {"identity": dict(identity), "documents": {}}
    cache = json.loads(path.read_text(encoding="utf-8"))
    if cache.get("identity") != dict(identity):
        raise ValueError(
            f"Prediction cache identity does not match this run: {path}. "
            "Choose another --cache path."
        )
    if not isinstance(cache.get("documents"), dict):
        raise ValueError(f"Invalid prediction cache: {path}")
    return cache


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Atomically replace one generated JSON artifact."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _infer_documents(
    documents: Sequence[BioREDDocument],
    extractor: BiomedicalExtractor,
    cache: dict[str, Any],
    cache_path: Path,
) -> tuple[tuple[ScoredRelation, ...], int]:
    """Infer each uncached document once and persist reusable concept-label scores."""

    all_candidates: list[ScoredRelation] = []
    total_mention_predictions = 0
    cached_documents: dict[str, Any] = cache["documents"]
    for index, document in enumerate(documents, start=1):
        cached = cached_documents.get(document.id)
        if cached is None:
            supplied_entities = tuple(
                mention.to_entity() for mention in document.relation_mentions()
            )
            predictions = extractor.extract_relations(document.text, supplied_entities)
            candidates = aggregate_mention_predictions(document, predictions)
            cached = {
                "mention_prediction_count": len(predictions),
                "concept_label_scores": serialize_scored_relations(candidates),
            }
            cached_documents[document.id] = cached
            _write_json(cache_path, cache)
            source = "inferred"
        else:
            candidates = deserialize_scored_relations(cached["concept_label_scores"])
            source = "cached"
        total_mention_predictions += int(cached["mention_prediction_count"])
        all_candidates.extend(candidates)
        print(
            f"[{index}/{len(documents)}] {document.id}: {source}, "
            f"{len(candidates)} concept-label scores",
            file=sys.stderr,
            flush=True,
        )
    return tuple(all_candidates), total_mention_predictions


def _sequence_summary(documents: Sequence[BioREDDocument]) -> dict[str, Any]:
    """Measure exact supplied-entity token lengths against GLiREL's hard limit."""

    lengths = []
    for document in documents:
        boundaries = {
            boundary
            for mention in document.relation_mentions()
            for boundary in (mention.start, mention.end)
        }
        lengths.append((document.id, len(_tokenize(document.text, boundaries))))
    longest_id, longest_length = max(lengths, key=lambda item: item[1])
    over_training_max = [
        {"document_id": document_id, "tokens": length}
        for document_id, length in lengths
        if length > GLIREL_TRAINING_MAX_LEN
    ]
    return {
        "tokenizer": r"\w+(?:[-_]\w+)*|\S with exact gold-boundary splits",
        "checkpoint_max_len": GLIREL_TRAINING_MAX_LEN,
        "longest_document": {"document_id": longest_id, "tokens": longest_length},
        "documents_over_max_len": over_training_max,
        "over_limit_policy": "abort before inference; never truncate or exclude",
    }


def _threshold_summary(
    gold: Sequence[TypedRelation], candidates: Sequence[ScoredRelation], selected: float
) -> list[dict[str, Any]]:
    """Score a compact set of fixed thresholds plus the calibrated boundary."""

    values = sorted({0.0, 0.1, 0.3, 0.5, selected})
    return [
        {
            "threshold": value,
            "predicted": result["predicted_after_threshold"],
            "typed_precision": result["typed_micro"]["precision"],
            "typed_recall": result["typed_micro"]["recall"],
            "typed_f1": result["typed_micro"]["f1"],
        }
        for value in values
        for result in (score_relations(gold, candidates, value),)
    ]


def _diagnostics(
    gold: set[TypedRelation], predictions: Sequence[ScoredRelation], limit: int = 3
) -> dict[str, Any]:
    """Return a few high-score TPs/FPs and informative typed false negatives."""

    predicted_by_typed = {item.typed: item for item in predictions}
    predicted_by_pair = {
        (item.document_id, item.concept_a, item.concept_b): item for item in predictions
    }

    def record(item: ScoredRelation) -> dict[str, Any]:
        return asdict(item)

    true_positives = sorted(
        (item for item in predictions if item.typed in gold),
        key=lambda item: item.score,
        reverse=True,
    )[:limit]
    false_positives = sorted(
        (item for item in predictions if item.typed not in gold),
        key=lambda item: item.score,
        reverse=True,
    )[:limit]
    false_negatives: list[dict[str, Any]] = []
    for item in sorted(gold - set(predicted_by_typed)):
        pair = (item.document_id, item.concept_a, item.concept_b)
        competing = predicted_by_pair.get(pair)
        false_negatives.append(
            {
                **asdict(item),
                "best_predicted_label": competing.relation_type if competing else None,
                "best_score": competing.score if competing else None,
            }
        )
        if len(false_negatives) == limit:
            break
    return {
        "high_confidence_true_positives": [record(item) for item in true_positives],
        "high_confidence_false_positives": [record(item) for item in false_positives],
        "representative_false_negatives": false_negatives,
    }


def _build_summary(
    dataset: BioREDDataset,
    documents: Sequence[BioREDDocument],
    model_name: str,
    candidates: Sequence[ScoredRelation],
    mention_prediction_count: int,
) -> dict[str, Any]:
    """Assemble the reproducible machine-readable result and diagnostics."""

    gold = tuple(relation for document in documents for relation in document.relations)
    threshold, result = calibrate_threshold(gold, candidates)
    predictions: tuple[ScoredRelation, ...] = result.pop("predictions")
    return {
        "dataset": {
            "path": str(dataset.path),
            "split": dataset.split,
            "sha256": dataset.sha256,
            "source": dataset.source,
            "date": dataset.date,
            "key": dataset.key,
        },
        "model_checkpoint": model_name,
        "gold_entities": True,
        "gliner_used": False,
        "relation_schema": list(BIORED_RELATION_LABELS),
        "relation_prompts": CANONICAL_TO_PROMPT,
        "candidate_pair_policy": (
            "BioRED eight concept-pair families; no stricter label/type matrix"
        ),
        "raw_top_k": RAW_TOP_K,
        "final_top_k": FINAL_TOP_K,
        "selected_dev_threshold": threshold,
        "counts": {
            "documents": len(documents),
            "gold_mentions": sum(len(document.mentions) for document in documents),
            "supplied_relation_mentions": sum(
                len(document.relation_mentions()) for document in documents
            ),
            "raw_mention_predictions": mention_prediction_count,
            "concept_label_scores": len(candidates),
            "gold_relations": result["gold_relations"],
            "predicted_before_threshold": result["predicted_before_threshold"],
            "predicted_after_threshold": result["predicted_after_threshold"],
        },
        "pair_only": result["pair_only"],
        "typed_micro": result["typed_micro"],
        "per_label": result["per_label"],
        "threshold_summary": _threshold_summary(gold, candidates, threshold),
        "sequence_integrity": _sequence_summary(documents),
        "diagnostics": _diagnostics(set(gold), predictions),
        "limitations": [
            "Threshold and reported quality are calibrated on the same development split.",
            (
                "GLiREL top_k=1 is applied per directed mention pair; concept "
                "aggregation keeps one final label per pair."
            ),
            (
                "The evaluator aborts before inference if any selected document "
                "exceeds GLiREL's 512-token limit."
            ),
        ],
    }


def _format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def _print_summary(summary: Mapping[str, Any]) -> None:
    """Render the contract's concise human-readable baseline report."""

    print("BioRED V0-B gold-entity relation baseline")
    print(f"Source/split: {summary['dataset']['path']} ({summary['dataset']['split']})")
    print(f"Documents: {summary['counts']['documents']}")
    print(f"GLiREL checkpoint: {summary['model_checkpoint']}")
    print("Gold entities: yes; GLiNER used: no")
    print(f"Candidate pairs: {summary['candidate_pair_policy']}")
    print(f"top_k: raw={summary['raw_top_k']}, final={summary['final_top_k']}")
    print(f"Selected dev threshold: {summary['selected_dev_threshold']:.8f}")
    pair = summary["pair_only"]
    typed = summary["typed_micro"]
    print(
        "Pair-only: "
        f"P={_format_metric(pair['precision'])} "
        f"R={_format_metric(pair['recall'])} F1={_format_metric(pair['f1'])} "
        f"(TP={pair['tp']} FP={pair['fp']} FN={pair['fn']})"
    )
    print(
        "Typed micro: "
        f"P={_format_metric(typed['precision'])} "
        f"R={_format_metric(typed['recall'])} F1={_format_metric(typed['f1'])} "
        f"(TP={typed['tp']} FP={typed['fp']} FN={typed['fn']})"
    )
    print("Per-label:")
    for label in BIORED_RELATION_LABELS:
        metric = summary["per_label"][label]
        print(
            f"  {label}: support={metric['support']} "
            f"P={_format_metric(metric['precision'])} "
            f"R={_format_metric(metric['recall'])} F1={_format_metric(metric['f1'])}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run cached inference, dev calibration, reporting, and JSON serialization."""

    args = _parser().parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be a positive integer")
    dataset = load_biored(args.dataset, args.split)
    documents = dataset.documents[: args.limit]
    sequence_summary = _sequence_summary(documents)
    over_limit = sequence_summary["documents_over_max_len"]
    if over_limit:
        print(
            "Cannot run a methodologically valid full-document evaluation: "
            f"{len(over_limit)} selected document(s) exceed GLiREL's "
            f"{GLIREL_TRAINING_MAX_LEN}-token limit: {over_limit}. "
            "No over-limit document was inferred, truncated, or excluded.",
            file=sys.stderr,
        )
        return 2

    identity = _cache_identity(dataset, args.model)
    cache = _read_cache(args.cache, identity)
    missing_ids = [document.id for document in documents if document.id not in cache["documents"]]
    model = _load_model(args.model, args.device, args.offline) if missing_ids else None
    extractor = _extractor(model, args.device, args.model) if model is not None else None
    if extractor is None:
        # No inference occurs on a fully cached run; this placeholder is never used.
        extractor = BiomedicalExtractor(_ForbiddenEntityModel(), object())
    candidates, mention_prediction_count = _infer_documents(
        documents, extractor, cache, args.cache
    )
    summary = _build_summary(
        dataset, documents, args.model, candidates, mention_prediction_count
    )
    _write_json(args.output, summary)
    _print_summary(summary)
    print(f"Machine-readable summary: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
