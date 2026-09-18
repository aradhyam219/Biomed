"""Evaluate cached official AIONER PubTator output on BioRED Test."""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .aioner import (
    AIONERBioMedExtractor,
    AIONERPredictionRuntime,
    AIONER_SUPPORTED_CANONICAL_TYPES,
)
from .biored import load_biored
from .ner_evaluation import evaluate_biored
from .ner_evaluation_cli import (
    _default_markdown_output,
    _print_summary,
    _write_json,
    _write_text,
    render_markdown_report,
)


OFFICIAL_AIONER_REPOSITORY = "https://github.com/ncbi/AIONER"
DEFAULT_AIONER_MODEL = "PubmedBERT-CRF-AIONER.h5"


def _parser() -> argparse.ArgumentParser:
    """Build the Test-only AIONER report command contract."""

    parser = argparse.ArgumentParser(
        description="Evaluate official AIONER PubTator output on BioRED Test."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to official Test.BioC.JSON or its containing directory.",
    )
    parser.add_argument(
        "--predictions",
        required=True,
        type=Path,
        help="PubTator output produced by the official AIONER runner.",
    )
    parser.add_argument("--split", default="test", choices=("test",))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--upstream-repository",
        default=OFFICIAL_AIONER_REPOSITORY,
    )
    parser.add_argument("--upstream-revision", required=True)
    parser.add_argument("--model-artifact", default=DEFAULT_AIONER_MODEL)
    parser.add_argument("--model-artifact-sha256")
    parser.add_argument("--runtime-python", default="3.8.20")
    parser.add_argument("--runtime-tensorflow", default="2.3.0")
    parser.add_argument("--runtime-transformers", default="4.18.0")
    parser.add_argument("--runtime-stanza", default="1.4.0")
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--failure-example-limit",
        type=int,
        default=5,
        help="Representative failure examples retained per category.",
    )
    return parser


def _default_output(today: date | None = None) -> Path:
    """Return the tracked full-run AIONER report path."""

    stamp = (today or date.today()).isoformat()
    return Path(f"reports/ner_aioner_biored_test_{stamp}.json")


def _sha256(path: Path) -> str:
    """Hash one external prediction artifact for report identity."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_pubtator_predictions(path: Path) -> dict[str, dict[str, Any]]:
    """Parse official AIONER PubTator output without changing its offsets."""

    raw = path.read_text(encoding="utf-8")
    records: dict[str, dict[str, Any]] = {}
    for block in raw.strip().split("\n\n"):
        lines = [line.rstrip("\r") for line in block.splitlines() if line.strip()]
        if len(lines) < 2 or "|t|" not in lines[0] or "|a|" not in lines[1]:
            raise ValueError(f"Invalid AIONER PubTator document block in {path}")
        document_id, title = lines[0].split("|t|", 1)
        abstract_id, abstract = lines[1].split("|a|", 1)
        if document_id != abstract_id or not document_id:
            raise ValueError(f"Mismatched AIONER PubTator document IDs in {path}")
        if document_id in records:
            raise ValueError(f"Duplicate AIONER PubTator document ID {document_id!r}")
        predictions: list[dict[str, Any]] = []
        for line in lines[2:]:
            fields = line.split("\t")
            if len(fields) != 5:
                raise ValueError(
                    "AIONER PubTator entity lines must contain document, start, "
                    "end, text, and type fields"
                )
            prediction_id, start, end, text, label = fields
            if prediction_id != document_id:
                raise ValueError(
                    f"AIONER prediction document ID {prediction_id!r} does not "
                    f"match block {document_id!r}"
                )
            predictions.append(
                {
                    "start": int(start),
                    "end": int(end),
                    "text": text,
                    "label": label,
                }
            )
        records[document_id] = {
            "text": title + " " + abstract,
            "predictions": tuple(predictions),
        }
    if not records:
        raise ValueError(f"AIONER PubTator output is empty: {path}")
    return records


def _runtime_for_dataset(
    dataset: Any,
    records: Mapping[str, Mapping[str, Any]],
) -> AIONERPredictionRuntime:
    """Validate document identity/text and build the text-keyed adapter runtime."""

    dataset_ids = {document.id for document in dataset.documents}
    record_ids = set(records)
    missing = sorted(dataset_ids - record_ids)
    extra = sorted(record_ids - dataset_ids)
    if missing or extra:
        raise ValueError(
            f"AIONER prediction coverage mismatch; missing={missing}, extra={extra}"
        )
    by_digest: dict[str, Sequence[object]] = {}
    for document in dataset.documents:
        record = records[document.id]
        if document.text != record["text"]:
            raise ValueError(
                f"AIONER PubTator source text does not match BioRED document "
                f"{document.id}"
            )
        digest = hashlib.sha256(document.text.encode("utf-8")).hexdigest()
        if digest in by_digest:
            raise ValueError("Duplicate BioRED source text prevents text-keyed AIONER cache")
        by_digest[digest] = record["predictions"]
    return AIONERPredictionRuntime(by_digest)


def main(argv: Sequence[str] | None = None) -> int:
    """Evaluate official AIONER output through the shared NER evaluator."""

    args = _parser().parse_args(argv)
    if args.failure_example_limit < 0:
        raise ValueError("--failure-example-limit must not be negative")
    predictions_path = args.predictions.resolve()
    dataset = load_biored(args.dataset, args.split)
    records = _parse_pubtator_predictions(predictions_path)
    runtime = _runtime_for_dataset(dataset, records)
    extractor = AIONERBioMedExtractor(runtime)
    report = evaluate_biored(
        dataset,
        extractor,
        supported_types=AIONER_SUPPORTED_CANONICAL_TYPES,
        failure_example_limit=args.failure_example_limit,
    )
    report["predictor"] = {
        "adapter": "AIONERBioMedExtractor",
        "name": "AIONER PubMedBERT-CRF",
        "model": args.model_artifact,
        "supported_canonical_types": list(AIONER_SUPPORTED_CANONICAL_TYPES),
        "upstream_repository": args.upstream_repository,
        "upstream_revision": args.upstream_revision,
        "model_artifact_sha256": args.model_artifact_sha256,
        "prediction_file": str(predictions_path),
        "prediction_file_sha256": _sha256(predictions_path),
        "device": args.device,
        "runtime": {
            "python": args.runtime_python,
            "tensorflow": args.runtime_tensorflow,
            "transformers": args.runtime_transformers,
            "stanza": args.runtime_stanza,
        },
    }
    output_path = args.output or _default_output()
    markdown_path = args.markdown_output or _default_markdown_output(output_path)
    _write_json(output_path, report)
    _write_text(markdown_path, render_markdown_report(report))
    _print_summary(report, output_path, markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "main",
    "_parse_pubtator_predictions",
    "_runtime_for_dataset",
]
