"""Run the isolated AIONER/HunFlair2 evaluation on official CRAFT."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .craft import (
    CRAFT_RELEASE_COMMIT_SHA,
    CRAFT_RELEASE_VERSION,
    evaluate_craft,
    load_craft,
    render_craft_markdown,
)
from .ner_runners import (
    RunnerOutput,
    load_cached_runner_output,
    normalize_runner_predictions,
    run_aioner,
    run_hunflair2,
    write_runner_input,
)


def _parser() -> argparse.ArgumentParser:
    """Build the reproducible CRAFT evaluation command contract."""

    parser = argparse.ArgumentParser(
        description="Evaluate AIONER and HunFlair2 on official CRAFT full text."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(f".cache/craft-{CRAFT_RELEASE_VERSION}"),
        help="Official CRAFT release checkout or unpacked release root.",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path(".cache/ner_cross_corpus/craft"),
    )
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--example-limit", type=int, default=5)
    parser.add_argument("--refresh-predictions", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic machine-readable report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    """Hash one model artifact in bounded chunks."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _aioner_artifact() -> Path | None:
    """Locate the exact artifact used by the default isolated AIONER runner."""

    candidates = (
        Path(".cache/aioner-upstream/pretrained_models/AIONER/PubmedBERT-CRF-AIONER.h5"),
        Path(".cache/aioner/models/pretrained_models/AIONER/PubmedBERT-CRF-AIONER.h5"),
    )
    return next((path for path in candidates if path.is_file()), None)


def _hunflair2_artifact() -> Path | None:
    """Locate the exact cached HunFlair2 snapshot artifact."""

    model_root = Path(
        ".cache/hunflair2/flair/models/hunflair2-ner/"
        "models--hunflair--hunflair2-ner"
    )
    ref_path = model_root / "refs" / "main"
    if not ref_path.is_file():
        return None
    revision = ref_path.read_text(encoding="utf-8").strip()
    artifact = model_root / "snapshots" / revision / "pytorch_model.bin"
    return artifact if artifact.is_file() else None


def _load_or_run_aioner(
    documents: Sequence[Mapping[str, str]],
    *,
    input_path: Path,
    output_path: Path,
    refresh: bool,
    artifact: Path | None,
) -> RunnerOutput:
    """Reuse a verified cache entry or run the isolated AIONER runtime."""

    expected_hash = _sha256_file(artifact) if artifact is not None else None
    if not refresh and output_path.is_file():
        try:
            return load_cached_runner_output(
                output_path,
                "AIONER",
                documents,
                expected_model_artifact_sha256=expected_hash,
            )
        except (ValueError, json.JSONDecodeError):
            pass
    return run_aioner(documents, input_path=input_path, output_path=output_path)


def _load_or_run_hunflair2(
    documents: Sequence[Mapping[str, str]],
    *,
    input_path: Path,
    output_path: Path,
    refresh: bool,
    artifact: Path | None,
) -> RunnerOutput:
    """Reuse a verified cache entry or run the isolated HunFlair2 runtime."""

    expected_hash = _sha256_file(artifact) if artifact is not None else None
    if not refresh and output_path.is_file():
        try:
            return load_cached_runner_output(
                output_path,
                "HunFlair2",
                documents,
                expected_model_artifact_sha256=expected_hash,
            )
        except (ValueError, json.JSONDecodeError):
            pass
    return run_hunflair2(documents, input_path=input_path, output_path=output_path)


def main(argv: Sequence[str] | None = None) -> int:
    """Load CRAFT, run or reuse both challengers, and write JSON/Markdown reports."""

    args = _parser().parse_args(argv)
    if args.example_limit < 0:
        raise ValueError("--example-limit must not be negative")
    dataset = load_craft(args.source)
    if dataset.release_version != CRAFT_RELEASE_VERSION:
        raise ValueError(
            f"Unsupported CRAFT release {dataset.release_version!r}; "
            f"expected {CRAFT_RELEASE_VERSION!r}"
        )
    if dataset.source_revision != CRAFT_RELEASE_COMMIT_SHA:
        raise ValueError(
            "CRAFT source is not the verified official v5.0.2 release commit: "
            f"{dataset.source_revision!r}"
        )
    if len(dataset.documents) != 97:
        raise ValueError(
            f"CRAFT v5.0.2 should contain 97 articles, found {len(dataset.documents)}"
        )
    documents = [document.to_runner_document() for document in dataset.documents]
    args.cache_root.mkdir(parents=True, exist_ok=True)
    input_path = args.cache_root / "model_input.json"
    write_runner_input(documents, input_path)
    aioner_artifact = _aioner_artifact()
    hunflair2_artifact = _hunflair2_artifact()
    aioner_run = _load_or_run_aioner(
        documents,
        input_path=input_path,
        output_path=args.cache_root / "aioner_predictions.json",
        refresh=args.refresh_predictions,
        artifact=aioner_artifact,
    )
    hunflair2_run = _load_or_run_hunflair2(
        documents,
        input_path=input_path,
        output_path=args.cache_root / "hunflair2_predictions.json",
        refresh=args.refresh_predictions,
        artifact=hunflair2_artifact,
    )
    predictions = {
        "AIONER": normalize_runner_predictions(aioner_run, documents),
        "HunFlair2": normalize_runner_predictions(hunflair2_run, documents),
    }
    report = evaluate_craft(
        dataset,
        predictions,
        predictor_metadata={
            "AIONER": {
                "adapter": "AIONERBioMedExtractor",
                "model": aioner_run.metadata.get("model_identifier", aioner_run.model),
                "model_artifact_sha256": aioner_run.metadata.get("model_artifact_sha256"),
                "runtime": aioner_run.metadata.get("runtime", {}),
                "document_count": aioner_run.metadata.get("document_count"),
                "predicted_entity_count": aioner_run.metadata.get("predicted_entity_count"),
                "inference_duration_seconds": aioner_run.metadata.get("inference_duration_seconds"),
                "inference_scope": aioner_run.metadata.get("inference_scope"),
                "prediction_file": str(aioner_run.prediction_path),
                "prediction_file_sha256": _sha256_file(aioner_run.prediction_path),
            },
            "HunFlair2": {
                "adapter": "HunFlair2BioMedExtractor",
                "model": hunflair2_run.metadata.get("model_identifier", hunflair2_run.model),
                "model_artifact_sha256": hunflair2_run.metadata.get("model_artifact_sha256"),
                "runtime": hunflair2_run.metadata.get("runtime", {}),
                "document_count": hunflair2_run.metadata.get("document_count"),
                "predicted_entity_count": hunflair2_run.metadata.get("predicted_entity_count"),
                "inference_duration_seconds": hunflair2_run.metadata.get("inference_duration_seconds"),
                "inference_scope": hunflair2_run.metadata.get("inference_scope"),
                "prediction_file": str(hunflair2_run.prediction_path),
                "prediction_file_sha256": _sha256_file(hunflair2_run.prediction_path),
            },
        },
        report_date=args.report_date,
        example_limit=args.example_limit,
    )
    report["model_input"] = {
        "path": str(input_path),
        "sha256": _sha256_file(input_path),
        "document_count": len(documents),
        "identical_canonical_source_for": ["AIONER", "HunFlair2"],
        "source_text_manifest_sha256": dataset.text_manifest_sha256,
    }
    output = args.output or Path(
        f"reports/ner_aioner_vs_hunflair2_craft_{args.report_date}.json"
    )
    markdown = args.markdown_output or output.with_suffix(".md")
    _write_json(output, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_craft_markdown(report), encoding="utf-8")
    print(f"CRAFT JSON report: {output.resolve()}")
    print(f"CRAFT Markdown report: {markdown.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
