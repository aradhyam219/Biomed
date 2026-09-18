"""Evaluate official HunFlair2 predictions on the frozen BioRED Test split."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .biored import BioREDDataset, load_biored
from .hunflair2 import (
    HUNFLAIR2_LABEL_TO_CANONICAL,
    HUNFLAIR2_MODEL_IDENTIFIER,
    HUNFLAIR2_OFFICIAL_REPOSITORY,
    HUNFLAIR2_SUPPORTED_CANONICAL_TYPES,
    HunFlair2BioMedExtractor,
    HunFlair2PredictionRuntime,
)
from .ner_evaluation import evaluate_biored
from .ner_evaluation_cli import (
    _default_markdown_output,
    _print_summary,
    _write_json,
    _write_text,
    render_markdown_report,
)


FROZEN_BIORED_TEST_SHA256 = (
    "35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6"
)
FROZEN_BIORED_TEST_DOCUMENT_COUNT = 100
DEFAULT_RUNTIME_PYTHON = Path(".cache/hunflair2/runtime/Scripts/python.exe")
DEFAULT_RUNTIME_SCRIPT = Path("src/biomedical_extractor/hunflair2_runtime.py")
DEFAULT_RUNTIME_CACHE = Path(".cache/hunflair2")


def _parser() -> argparse.ArgumentParser:
    """Build the isolated HunFlair2 evaluation command contract."""

    parser = argparse.ArgumentParser(
        description="Evaluate official HunFlair2 on the frozen BioRED Test split."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to official Test.BioC.JSON or its containing directory.",
    )
    parser.add_argument("--split", default="test", choices=("test",))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--runtime-python",
        type=Path,
        default=DEFAULT_RUNTIME_PYTHON,
        help="Dedicated Python executable containing Flair and SciSpaCy.",
    )
    parser.add_argument(
        "--runtime-script",
        type=Path,
        default=DEFAULT_RUNTIME_SCRIPT,
        help="Standalone Flair subprocess script.",
    )
    parser.add_argument(
        "--runtime-cache",
        type=Path,
        default=DEFAULT_RUNTIME_CACHE,
        help="Ignored cache root for model/runtime artifacts and predictions.",
    )
    parser.add_argument(
        "--model",
        default=HUNFLAIR2_MODEL_IDENTIFIER,
        help="Official model identifier; do not substitute another tagger.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help="Optional cached model artifact path used instead of downloading.",
    )
    parser.add_argument("--model-revision")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--failure-example-limit",
        type=int,
        default=5,
        help="Representative failure examples retained per category.",
    )
    return parser


def _default_output(today: date | None = None) -> Path:
    """Return the tracked full-run HunFlair2 report path."""

    stamp = (today or date.today()).isoformat()
    return Path(f"reports/ner_hunflair2_biored_test_{stamp}.json")


def _sha256(path: Path) -> str:
    """Hash one generated or external artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_dataset_identity(dataset: BioREDDataset) -> None:
    """Reject any split, document count, or checksum other than frozen Test."""

    if dataset.split != "test":
        raise ValueError(f"HunFlair2 evaluation requires BioRED Test, got {dataset.split!r}")
    if len(dataset.documents) != FROZEN_BIORED_TEST_DOCUMENT_COUNT:
        raise ValueError(
            "HunFlair2 evaluation requires exactly 100 BioRED Test documents; "
            f"found {len(dataset.documents)}"
        )
    if dataset.sha256 != FROZEN_BIORED_TEST_SHA256:
        raise ValueError(
            "BioRED Test dataset SHA-256 differs from the frozen AIONER comparison: "
            f"expected {FROZEN_BIORED_TEST_SHA256}, got {dataset.sha256}"
        )


def _cached_model_path(runtime_cache: Path, model_identifier: str) -> tuple[Path | None, str | None]:
    """Find the cached official artifact and its Hugging Face revision."""

    if model_identifier != HUNFLAIR2_MODEL_IDENTIFIER:
        return None, None
    model_root = runtime_cache / "flair" / "models" / "hunflair2-ner" / (
        "models--hunflair--hunflair2-ner"
    )
    ref_path = model_root / "refs" / "main"
    if not ref_path.is_file():
        return None, None
    revision = ref_path.read_text(encoding="utf-8").strip()
    artifact = model_root / "snapshots" / revision / "pytorch_model.bin"
    return (artifact if artifact.is_file() else None), revision


def _write_runner_input(dataset: BioREDDataset, path: Path) -> None:
    """Write exact source strings for the isolated process."""

    payload = {
        "documents": [
            {"id": document.id, "text": document.text}
            for document in dataset.documents
        ]
    }
    _write_json(path, payload)


def _run_isolated_runner(
    dataset: BioREDDataset,
    *,
    runtime_python: Path,
    runtime_script: Path,
    runtime_cache: Path,
    model_identifier: str,
    model_path: Path | None,
    model_revision: str | None,
    device: str,
    offline: bool,
) -> tuple[dict[str, Any], Path]:
    """Run the official Flair subprocess and return its JSON plus cache path."""

    runtime_python = runtime_python.resolve()
    runtime_script = runtime_script.resolve()
    runtime_cache = runtime_cache.resolve()
    if not runtime_python.is_file():
        raise FileNotFoundError(f"HunFlair2 runtime Python not found: {runtime_python}")
    if not runtime_script.is_file():
        raise FileNotFoundError(f"HunFlair2 runtime script not found: {runtime_script}")

    runtime_cache.mkdir(parents=True, exist_ok=True)
    input_path = runtime_cache / f"input_biored_test_{dataset.sha256}.json"
    output_path = runtime_cache / f"predictions_biored_test_{dataset.sha256}.json"
    _write_runner_input(dataset, input_path)
    selected_model_path = model_path.resolve() if model_path is not None else None
    cached_model, cached_revision = _cached_model_path(runtime_cache, model_identifier)
    if selected_model_path is None and cached_model is not None:
        selected_model_path = cached_model
    selected_revision = model_revision or cached_revision
    model_input = str(selected_model_path) if selected_model_path is not None else model_identifier

    command = [
        str(runtime_python),
        str(runtime_script),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--model",
        model_input,
        "--model-identifier",
        model_identifier,
        "--device",
        device,
    ]
    if selected_revision:
        command.extend(("--model-revision", selected_revision))
    environment = os.environ.copy()
    environment.update(
        {
            "FLAIR_CACHE_ROOT": str(runtime_cache / "flair"),
            "HF_HOME": str(runtime_cache / "huggingface"),
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "FLAIR_DEVICE": device,
            "PYTHONUNBUFFERED": "1",
        }
    )
    if offline:
        environment["HF_HUB_OFFLINE"] = "1"
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(
            "Official HunFlair2 isolated runner failed with exit code "
            f"{completed.returncode}: {details[-4000:]}"
        )
    if not output_path.is_file():
        raise RuntimeError("HunFlair2 runner completed without writing predictions")
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("HunFlair2 runner output must be a JSON object")
    payload["metadata"] = {
        **dict(payload.get("metadata", {})),
        "runner_stdout": completed.stdout.strip(),
    }
    return payload, output_path


def _runtime_for_dataset(
    dataset: BioREDDataset,
    payload: Mapping[str, Any],
) -> HunFlair2PredictionRuntime:
    """Validate runner coverage/source hashes and build the text-keyed runtime."""

    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, Sequence) or isinstance(
        raw_documents, (str, bytes)
    ):
        raise ValueError("HunFlair2 runner output requires a documents array")
    records: dict[str, Mapping[str, Any]] = {}
    for raw in raw_documents:
        if not isinstance(raw, Mapping):
            raise ValueError("HunFlair2 runner document records must be objects")
        document_id = str(raw.get("id", ""))
        if not document_id or document_id in records:
            raise ValueError(f"Invalid or duplicate HunFlair2 runner document ID: {document_id!r}")
        records[document_id] = raw
    dataset_ids = {document.id for document in dataset.documents}
    record_ids = set(records)
    missing = sorted(dataset_ids - record_ids)
    extra = sorted(record_ids - dataset_ids)
    if missing or extra:
        raise ValueError(
            f"HunFlair2 prediction coverage mismatch; missing={missing}, extra={extra}"
        )

    by_digest: dict[str, Sequence[object]] = {}
    for document in dataset.documents:
        record = records[document.id]
        expected_digest = hashlib.sha256(document.text.encode("utf-8")).hexdigest()
        if record.get("text_sha256") != expected_digest:
            raise ValueError(
                f"HunFlair2 runner source text hash mismatch for document {document.id}"
            )
        predictions = record.get("predictions", ())
        if not isinstance(predictions, Sequence) or isinstance(predictions, (str, bytes)):
            raise ValueError(f"HunFlair2 predictions are not an array for {document.id}")
        if expected_digest in by_digest:
            raise ValueError("Duplicate BioRED source text prevents text-keyed HunFlair2 cache")
        by_digest[expected_digest] = tuple(predictions)
    return HunFlair2PredictionRuntime(by_digest)


def main(argv: Sequence[str] | None = None) -> int:
    """Run isolated HunFlair2 inference and shared BioRED scoring."""

    args = _parser().parse_args(argv)
    if args.failure_example_limit < 0:
        raise ValueError("--failure-example-limit must not be negative")
    dataset = load_biored(args.dataset, args.split)
    _validate_dataset_identity(dataset)
    payload, prediction_path = _run_isolated_runner(
        dataset,
        runtime_python=args.runtime_python,
        runtime_script=args.runtime_script,
        runtime_cache=args.runtime_cache,
        model_identifier=args.model,
        model_path=args.model_path,
        model_revision=args.model_revision,
        device=args.device,
        offline=args.offline,
    )
    runtime = _runtime_for_dataset(dataset, payload)
    report = evaluate_biored(
        dataset,
        HunFlair2BioMedExtractor(runtime),
        supported_types=HUNFLAIR2_SUPPORTED_CANONICAL_TYPES,
        failure_example_limit=args.failure_example_limit,
    )
    metadata = dict(payload.get("metadata", {}))
    flair_version = metadata.get("runtime", {}).get("flair")
    report["predictor"] = {
        "adapter": "HunFlair2BioMedExtractor",
        "name": "HunFlair2",
        "model": args.model,
        "model_identifier": args.model,
        "supported_labels": dict(HUNFLAIR2_LABEL_TO_CANONICAL),
        "supported_canonical_types": list(HUNFLAIR2_SUPPORTED_CANONICAL_TYPES),
        "upstream_repository": HUNFLAIR2_OFFICIAL_REPOSITORY,
        "upstream_revision": None if flair_version is None else f"flair=={flair_version}",
        "model_revision": metadata.get("model_revision"),
        "model_artifact_sha256": metadata.get("model_artifact_sha256"),
        "prediction_file": str(prediction_path.resolve()),
        "prediction_file_sha256": _sha256(prediction_path),
        "device": args.device,
        "runtime": metadata.get("runtime", {}),
        "inference_duration_seconds": metadata.get("inference_duration_seconds"),
        "document_count": metadata.get("document_count"),
        "sentence_count": metadata.get("sentence_count"),
        "inference_scope": metadata.get("inference_scope"),
        "inference_mechanics": metadata.get("runtime", {}).get("offset_mechanics"),
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
    "FROZEN_BIORED_TEST_DOCUMENT_COUNT",
    "FROZEN_BIORED_TEST_SHA256",
    "main",
    "_runtime_for_dataset",
    "_validate_dataset_identity",
]
