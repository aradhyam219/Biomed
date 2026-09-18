"""Run the required independent MedMentions ST21pv NER evaluation."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .cross_corpus import (
    acquire_medmentions,
    evaluate_medmentions,
    render_medmentions_markdown,
)
from .ner_runners import normalize_runner_predictions, run_aioner, run_hunflair2


def _parser() -> argparse.ArgumentParser:
    """Build the MedMentions evaluation command contract."""

    parser = argparse.ArgumentParser(
        description="Evaluate AIONER and HunFlair2 on MedMentions ST21pv."
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path(".cache/ner_cross_corpus/medmentions"),
    )
    parser.add_argument("--split", choices=("all", "trng", "dev", "test"), default="test")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--example-limit", type=int, default=5)
    parser.add_argument("--biored-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic JSON report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _metadata(run: Any, adapter: str) -> dict[str, Any]:
    """Build reviewer-facing runner identity metadata."""

    return {
        "adapter": adapter,
        "model": run.metadata.get("model_identifier", run.model),
        "model_artifact_sha256": run.metadata.get("model_artifact_sha256"),
        "runtime": run.metadata.get("runtime", {}),
        "document_count": run.metadata.get("document_count"),
        "predicted_entity_count": run.metadata.get("predicted_entity_count"),
        "inference_duration_seconds": run.metadata.get(
            "inference_duration_seconds"
        ),
        "inference_scope": run.metadata.get("inference_scope"),
        "prediction_file": str(run.prediction_path),
        "prediction_file_sha256": hashlib.sha256(
            run.prediction_path.read_bytes()
        ).hexdigest(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire, run, score, and write the MedMentions report pair."""

    args = _parser().parse_args(argv)
    if args.example_limit < 0:
        raise ValueError("--example-limit must not be negative")
    dataset = acquire_medmentions(
        args.cache_root,
        split=args.split,
        refresh=args.refresh,
    )
    documents = [
        {"id": document.id, "text": document.text}
        for document in dataset.documents
    ]
    input_path = args.cache_root / "model_input.json"
    aioner_run = run_aioner(
        documents,
        input_path=input_path,
        output_path=args.cache_root / "aioner_predictions.json",
    )
    hunflair2_run = run_hunflair2(
        documents,
        input_path=input_path,
        output_path=args.cache_root / "hunflair2_predictions.json",
    )
    predictions = {
        "AIONER": normalize_runner_predictions(aioner_run, documents),
        "HunFlair2": normalize_runner_predictions(hunflair2_run, documents),
    }
    biored_path = args.biored_report or Path(
        "reports/ner_aioner_vs_hunflair2_biored_test_2026-09-18.json"
    )
    biored_report = (
        json.loads(biored_path.read_text(encoding="utf-8"))
        if biored_path.exists()
        else None
    )
    report = evaluate_medmentions(
        dataset,
        predictions,
        predictor_metadata={
            "AIONER": _metadata(aioner_run, "AIONERBioMedExtractor"),
            "HunFlair2": _metadata(hunflair2_run, "HunFlair2BioMedExtractor"),
        },
        example_limit=args.example_limit,
        biored_report=biored_report,
    )
    output = args.output or Path(
        f"reports/ner_aioner_vs_hunflair2_medmentions_{args.report_date}.json"
    )
    markdown = args.markdown_output or output.with_suffix(".md")
    _write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_medmentions_markdown(report), encoding="utf-8")
    print(f"MedMentions JSON report: {output.resolve()}")
    print(f"MedMentions Markdown report: {markdown.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
