"""Run the target-domain AIONER/HunFlair2 reconnaissance workflow."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ner_reconnaissance import (
    TARGET_DOMAIN_DATE,
    acquire_target_corpus,
    build_target_domain_report,
    load_target_corpus,
    render_target_domain_markdown,
    write_target_corpus,
)
from .ner_runners import normalize_runner_predictions, run_aioner, run_hunflair2


def _parser() -> argparse.ArgumentParser:
    """Build the deterministic target-domain command contract."""

    parser = argparse.ArgumentParser(
        description="Acquire science-team papers and compare AIONER with HunFlair2."
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path(".cache/ner_target_domain"),
        help="Ignored cache root for source XML, canonical text, and predictions.",
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--report-date", default=TARGET_DOMAIN_DATE)
    parser.add_argument("--review-target", type=int, default=75)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--review-output", type=Path)
    parser.add_argument("--review-markdown-output", type=Path)
    return parser


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic JSON report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    """Write one UTF-8 Markdown report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


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
    """Acquire, run, compare, and write the two target-domain report pairs."""

    args = _parser().parse_args(argv)
    if not 0 <= args.review_target <= 100:
        raise ValueError("--review-target must be between 0 and 100")
    cache_root = args.cache_root
    corpus_path = cache_root / "target_corpus.json"
    if args.refresh or not corpus_path.exists():
        papers = acquire_target_corpus(cache_root, refresh=args.refresh)
        write_target_corpus(papers, corpus_path)
    else:
        papers = load_target_corpus(corpus_path)
    documents = [{"id": paper.paper_id, "text": paper.text} for paper in papers]
    input_path = cache_root / "model_input.json"
    aioner_run = run_aioner(
        documents,
        input_path=input_path,
        output_path=cache_root / "aioner_predictions.json",
    )
    hunflair2_run = run_hunflair2(
        documents,
        input_path=input_path,
        output_path=cache_root / "hunflair2_predictions.json",
    )
    aioner_predictions = normalize_runner_predictions(aioner_run, documents)
    hunflair2_predictions = normalize_runner_predictions(hunflair2_run, documents)
    report, review_packet = build_target_domain_report(
        papers,
        aioner_predictions,
        hunflair2_predictions,
        predictor_metadata={
            "AIONER": _metadata(aioner_run, "AIONERBioMedExtractor"),
            "HunFlair2": _metadata(hunflair2_run, "HunFlair2BioMedExtractor"),
        },
        review_target_count=args.review_target,
        report_date=args.report_date,
    )
    output = args.output or Path(
        f"reports/ner_target_domain_aioner_hunflair2_{args.report_date}.json"
    )
    markdown = args.markdown_output or output.with_suffix(".md")
    review_output = args.review_output or Path(
        f"reports/ner_target_domain_review_packet_{args.report_date}.json"
    )
    review_markdown = args.review_markdown_output or review_output.with_suffix(".md")
    _write_json(output, report)
    _write_text(markdown, render_target_domain_markdown(report))
    _write_json(review_output, review_packet)
    _write_text(
        review_markdown,
        "# Target-domain human-review packet\n\n"
        "Deterministic examples selected from model agreement and disagreement "
        "categories. These are not gold labels.\n\n"
        f"- Selected examples: {review_packet['selection']['selected_count']}\n"
        f"- Candidate examples: {review_packet['selection']['candidate_count']}\n"
        f"- Selection method: {review_packet['selection']['method']}\n",
    )
    print(f"Target JSON report: {output.resolve()}")
    print(f"Target Markdown report: {markdown.resolve()}")
    print(f"Review JSON packet: {review_output.resolve()}")
    print(f"Review Markdown packet: {review_markdown.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
