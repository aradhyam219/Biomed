"""Build the target-domain gold pilot and freeze the pretrained baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ner_reconnaissance import (
    acquire_target_corpus,
    load_target_corpus,
    write_target_corpus,
)
from .ner_runners import (
    _hunflair2_artifact,
    load_cached_runner_output,
    normalize_runner_predictions,
    run_hunflair2,
)
from .ner_evaluation import canonical_predicted_type
from .target_domain_pilot import (
    build_pilot_package,
    build_split_manifest,
    load_review_packet,
    render_pilot_markdown,
    sha256_file,
    sha256_json,
    validate_annotation_package,
    write_json,
    write_pilot_package,
    write_split_manifest,
)


DEFAULT_REPORT_DATE = "2026-09-19"
DEFAULT_RECON_REPORT_DATE = "2026-09-18"


def _parser() -> argparse.ArgumentParser:
    """Build the pilot command contract."""

    parser = argparse.ArgumentParser(
        description=(
            "Select a human target-domain NER pilot and freeze official "
            "HunFlair2 predictions without creating gold labels."
        )
    )
    parser.add_argument(
        "--cache-root", type=Path, default=Path(".cache/ner_target_domain")
    )
    parser.add_argument("--canonical-corpus", type=Path)
    parser.add_argument("--refresh-corpus", action="store_true")
    parser.add_argument("--target-per-paper", type=int, default=20)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--aioner-predictions", type=Path)
    parser.add_argument(
        "--review-packet",
        type=Path,
        default=Path(
            f"reports/ner_target_domain_review_packet_{DEFAULT_RECON_REPORT_DATE}.json"
        ),
    )
    parser.add_argument("--report-date", default=DEFAULT_REPORT_DATE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--split-output", type=Path)
    parser.add_argument("--baseline-output", type=Path)
    parser.add_argument("--force-baseline", action="store_true")
    return parser


def _write_text(path: Path, text: str) -> None:
    """Write one UTF-8 text artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_or_acquire_corpus(args: argparse.Namespace) -> tuple[tuple[Any, ...], Path]:
    """Reuse the canonical cache or restore it through official acquisition."""

    corpus_path = args.canonical_corpus or (args.cache_root / "target_corpus.json")
    if args.refresh_corpus or not corpus_path.is_file():
        papers = acquire_target_corpus(args.cache_root, refresh=args.refresh_corpus)
        write_target_corpus(papers, corpus_path)
    else:
        papers = load_target_corpus(corpus_path)
    return papers, corpus_path


def _cached_artifact_sha(cache_root: Path) -> str | None:
    """Return the current cached HunFlair2 model digest when discoverable."""

    artifact, _ = _hunflair2_artifact(cache_root, "hunflair/hunflair2-ner")
    return sha256_file(artifact) if artifact is not None else None


def _load_hunflair2_predictions(
    papers: Sequence[Any],
    *,
    cache_root: Path,
    device: str,
) -> tuple[dict[str, tuple[Any, ...]], Any]:
    """Load or run full-paper HunFlair2 predictions for sampling context."""

    documents = [{"id": paper.paper_id, "text": paper.text} for paper in papers]
    input_path = cache_root / "pilot_model_input.json"
    output_path = cache_root / "hunflair2_predictions.json"
    artifact_sha = _cached_artifact_sha(cache_root.parent / "hunflair2")
    run = None
    if output_path.is_file():
        try:
            run = load_cached_runner_output(
                output_path,
                "HunFlair2",
                documents,
                expected_model_artifact_sha256=artifact_sha,
            )
        except (ValueError, json.JSONDecodeError):
            run = None
    if run is None:
        run = run_hunflair2(
            documents,
            input_path=input_path,
            output_path=output_path,
            runtime_cache=cache_root.parent / "hunflair2",
            device=device,
        )
    return normalize_runner_predictions(run, documents), run


def _load_aioner_predictions(
    path: Path | None,
    papers: Sequence[Any],
) -> dict[str, tuple[Any, ...]] | None:
    """Load prior AIONER predictions only when a verified cache is supplied."""

    if path is None:
        return None
    documents = [{"id": paper.paper_id, "text": paper.text} for paper in papers]
    run = load_cached_runner_output(path, "AIONER", documents)
    return normalize_runner_predictions(run, documents)


def _baseline_input(package: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build the exact selected-sentence input manifest for frozen inference."""

    return [
        {
            "id": str(item["example_id"]),
            "text": str(item["text"]),
        }
        for item in package["examples"]
    ]


def _baseline_artifact(
    package: Mapping[str, Any],
    package_path: Path,
    run: Any,
    documents: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Create the tracked, prediction-only frozen-base artifact."""

    normalized = normalize_runner_predictions(run, documents)
    item_by_id = {str(item["example_id"]): item for item in package["examples"]}
    prediction_documents: list[dict[str, Any]] = []
    for document in documents:
        example_id = str(document["id"])
        item = item_by_id[example_id]
        predictions = []
        for entity in normalized[example_id]:
            predictions.append(
                {
                    "start": entity.start,
                    "end": entity.end,
                    "text": entity.text,
                    "type": entity.type,
                    "canonical_type": (
                        entity.type
                        if entity.type in package["approved_entity_types"]
                        else canonical_predicted_type(entity.type)
                    ),
                    "score": entity.score,
                }
            )
        prediction_documents.append(
            {
                "example_id": example_id,
                "paper_id": item["paper_id"],
                "split": item["split"],
                "sentence_start": item["sentence_start"],
                "sentence_end": item["sentence_end"],
                "text_sha256": hashlib.sha256(
                    str(document["text"]).encode("utf-8")
                ).hexdigest(),
                "predictions": predictions,
            }
        )
    metadata = dict(run.metadata)
    return {
        "schema_version": 1,
        "artifact_kind": "frozen_pretrained_hunflair2_target_pilot_baseline",
        "gold_status": "empty_template_not_used_for_inference",
        "model_selection_candidate": False,
        "model": {
            "identifier": metadata.get("model_identifier", run.model),
            "input": metadata.get("model_input"),
            "revision": metadata.get("model_revision"),
            "artifact_sha256": metadata.get("model_artifact_sha256"),
        },
        "runtime": metadata.get("runtime", {}),
        "inference": {
            "document_count": metadata.get("document_count"),
            "sentence_count": metadata.get("sentence_count"),
            "predicted_entity_count": metadata.get("predicted_entity_count"),
            "duration_seconds": metadata.get("inference_duration_seconds"),
            "scope": metadata.get("inference_scope"),
        },
        "inference_configuration": {
            "device": metadata.get("runtime", {}).get("device"),
            "sentence_input": True,
            "threshold": None,
            "sentence_splitter": metadata.get("runtime", {}).get("sentence_splitter"),
        },
        "input": {
            "pilot_package": str(package_path),
            "pilot_package_sha256": sha256_file(package_path),
            "manifest_sha256": sha256_json(documents),
            "example_count": len(documents),
            "text_identity": "Each input is the exact selected sentence text.",
        },
        "prediction_payload_sha256": sha256_json(prediction_documents),
        "prediction_count": sum(
            len(document["predictions"]) for document in prediction_documents
        ),
        "documents": prediction_documents,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Build the pilot package, reviewer packet, and frozen base predictions."""

    args = _parser().parse_args(argv)
    if args.target_per_paper <= 0:
        raise ValueError("--target-per-paper must be positive")
    papers, corpus_path = _load_or_acquire_corpus(args)
    split_manifest = build_split_manifest(papers)
    split_path = args.split_output or Path(
        f"reports/target_domain_pilot_split_{args.report_date}.json"
    )
    write_split_manifest(split_path, split_manifest)

    hunflair2_predictions, full_run = _load_hunflair2_predictions(
        papers,
        cache_root=args.cache_root,
        device=args.device,
    )
    del full_run
    aioner_predictions = _load_aioner_predictions(args.aioner_predictions, papers)
    review_candidates = load_review_packet(args.review_packet) if args.review_packet.is_file() else ()
    package = build_pilot_package(
        papers,
        hunflair2_predictions,
        aioner_predictions=aioner_predictions,
        review_candidates=review_candidates,
        paper_split=split_manifest["paper_splits"],
        target_per_paper=args.target_per_paper,
        source_manifest_sha256=sha256_file(corpus_path),
        source_manifest_path=str(corpus_path),
    )
    validate_annotation_package(package, canonical_papers=papers)
    output = args.output or Path(
        f"reports/target_domain_pilot_{args.report_date}.json"
    )
    markdown = args.markdown_output or output.with_suffix(".md")
    write_pilot_package(output, package)
    _write_text(markdown, render_pilot_markdown(package))

    documents = _baseline_input(package)
    baseline_cache_input = args.cache_root / "pilot_baseline_model_input.json"
    baseline_cache_output = args.cache_root / "pilot_baseline_hunflair2.json"
    baseline_run = None
    if not args.force_baseline and baseline_cache_output.is_file():
        try:
            baseline_run = load_cached_runner_output(
                baseline_cache_output,
                "HunFlair2",
                documents,
                expected_model_artifact_sha256=_cached_artifact_sha(
                    args.cache_root.parent / "hunflair2"
                ),
            )
        except (ValueError, json.JSONDecodeError):
            baseline_run = None
    if baseline_run is None:
        baseline_run = run_hunflair2(
            documents,
            input_path=baseline_cache_input,
            output_path=baseline_cache_output,
            runtime_cache=args.cache_root.parent / "hunflair2",
            device=args.device,
        )
    baseline = _baseline_artifact(package, output, baseline_run, documents)
    baseline_output = args.baseline_output or Path(
        f"reports/target_domain_hunflair2_baseline_{args.report_date}.json"
    )
    write_json(baseline_output, baseline)

    print(f"Pilot package: {output.resolve()}")
    print(f"Reviewer packet: {markdown.resolve()}")
    print(f"Split manifest: {split_path.resolve()}")
    print(f"Frozen baseline: {baseline_output.resolve()}")
    print(f"Pilot package SHA-256: {sha256_file(output)}")
    print(f"Baseline SHA-256: {sha256_file(baseline_output)}")
    print(f"Baseline predictions: {baseline['prediction_count']}")
    print(f"Pilot sentences: {package['selection']['selected_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
