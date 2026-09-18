"""Run the model-independent BioRED biomedical NER evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .biored import load_biored
from .entity_extraction import (
    DEFAULT_CORE_ENTITY_LABELS,
    DEFAULT_ENTITY_MODEL,
    GLiNERBioMedExtractor,
)
from .ner_evaluation import evaluate_biored
from .ner_evaluation import COMPARABLE_CANONICAL_TYPES


def _parser() -> argparse.ArgumentParser:
    """Build the baseline evaluation command-line parser."""

    parser = argparse.ArgumentParser(
        description="Evaluate the current GLiNER-BioMed NER path on BioRED."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to official BioRED Dev/Test.BioC.JSON or its containing directory.",
    )
    parser.add_argument("--split", default="dev", choices=("dev", "test"))
    parser.add_argument(
        "--limit",
        type=int,
        help="Evaluate only the first N documents for a diagnostic subset run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Machine-readable JSON report path.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Markdown companion report path; defaults beside --output.",
    )
    parser.add_argument(
        "--entity-threshold",
        type=float,
        default=0.5,
        help="Existing GLiNER entity threshold; default is the production default.",
    )
    parser.add_argument("--device", help="Torch device, for example cpu or cuda.")
    parser.add_argument(
        "--failure-example-limit",
        type=int,
        default=5,
        help="Representative failure examples retained per category.",
    )
    return parser


def _default_output(
    limit: int | None,
    today: date | None = None,
    split: str = "dev",
) -> Path:
    """Keep the full baseline tracked and subset diagnostics disposable."""

    stamp = (today or date.today()).isoformat()
    if limit is None:
        suffix = "baseline" if split == "dev" else split
        return Path(f"reports/ner_gliner_biored_{suffix}_{stamp}.json")
    return Path(f".cache/ner_gliner_biored_subset_{stamp}.json")


def _default_markdown_output(output: Path) -> Path:
    """Place the Markdown companion beside a JSON report."""

    return output.with_suffix(".md") if output.suffix else Path(f"{output}.md")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one generated report atomically."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_text(path: Path, value: str) -> None:
    """Write a generated Markdown report atomically."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _format_metric(value: float | None) -> str:
    """Format a possibly undefined metric for the companion report."""

    return "N/A" if value is None else f"{value:.4f}"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    """Render the concise human-readable companion for a JSON report."""

    dataset = report["dataset"]
    predictor = report.get("predictor", {})
    counts = report["counts"]
    exact = report["metrics"]["exact_match"]
    shared = report["metrics"].get("shared_class", exact)
    full_schema = report["metrics"].get("full_schema", exact)
    taxonomy = report["taxonomy"]
    coverage = report["schema_coverage"]
    graph = report["graph_critical_entity_recall"]
    failures = report["failure_analysis"]["counts"]

    lines = [
        f"# {predictor.get('name', 'Biomedical NER')} BioRED NER Evaluation",
        "",
        "This is evidence from the model-independent NER evaluator. It is",
        "not a production-readiness claim and does not rank future candidate models.",
        "",
        "## Method",
        "",
        f"- Dataset: `{dataset['path']}` ({dataset['split']})",
        f"- Dataset SHA-256: `{dataset['sha256']}`",
        f"- Documents: {counts['documents_evaluated']} / {dataset['documents_in_source']}",
        f"- Gold entities by BioRED type: `{counts['gold_entities_by_type']}`",
        f"- Predictor: `{predictor.get('model', 'unspecified')}`",
        f"- Threshold: `{predictor.get('threshold', 'unspecified')}`",
        "- Primary matching: exact half-open character span plus canonical type",
        "- No fuzzy matching, relation model, LLM, or model fine-tuning was used",
        "",
    ]
    runtime = predictor.get("runtime")
    if runtime:
        lines.extend(
            [
                "## Runtime and inference",
                "",
                f"- Runtime versions: `{runtime}`",
                f"- Model revision: `{predictor.get('model_revision', 'unspecified')}`",
                f"- Model artifact SHA-256: `{predictor.get('model_artifact_sha256', 'unspecified')}`",
                f"- Inference duration: `{predictor.get('inference_duration_seconds', 'unspecified')}` seconds",
                f"- Inference scope: `{predictor.get('inference_scope', 'unspecified')}`",
                f"- Offset mechanics: `{predictor.get('inference_mechanics', 'unspecified')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Taxonomy mapping",
            "",
            "| BioRED loader type | Canonical evaluation type |",
            "| --- | --- |",
        ]
    )
    for source_type, canonical_type in taxonomy[
        "gold_internal_type_to_canonical"
    ].items():
        lines.append(f"| `{source_type}` | `{canonical_type}` |")
    lines.extend(
        [
            "",
            "| Predictor label | Canonical evaluation type |",
            "| --- | --- |",
        ]
    )
    for source_type, canonical_type in taxonomy[
        "predicted_type_to_canonical"
    ].items():
        lines.append(f"| `{source_type}` | `{canonical_type}` |")
    lines.extend(
        [
            "",
            f"- Shared-class taxonomy: `{shared['supported_canonical_types']}`",
            f"- Full-schema supported taxonomy: `{full_schema['supported_canonical_types']}`",
            f"- Full-schema unsupported taxonomy: `{full_schema.get('unsupported_canonical_types', [])}`",
            "DNA/RNA are not force-mapped to unrelated BioRED classes.",
            "",
            "## Shared-class exact-match metrics",
            "",
            "| Scope | TP | FP | FN | Precision | Recall | F1 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| Micro | {shared['micro']['tp']} | {shared['micro']['fp']} | {shared['micro']['fn']} | "
            f"{_format_metric(shared['micro']['precision'])} | {_format_metric(shared['micro']['recall'])} | "
            f"{_format_metric(shared['micro']['f1'])} |",
        ]
    )
    for canonical_type, metric in shared["per_type"].items():
        lines.append(
            f"| `{canonical_type}` | {metric['tp']} | {metric['fp']} | "
            f"{metric['fn']} | {_format_metric(metric['precision'])} | "
            f"{_format_metric(metric['recall'])} | {_format_metric(metric['f1'])} |"
        )
    lines.extend(
        [
            "",
            f"Macro F1: **{_format_metric(shared['macro_f1'])}**",
            "",
            "## Full-schema exact-match metrics",
            "",
            "| Scope | TP | FP | FN | Precision | Recall | F1 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| Micro | {full_schema['micro']['tp']} | {full_schema['micro']['fp']} | {full_schema['micro']['fn']} | "
            f"{_format_metric(full_schema['micro']['precision'])} | {_format_metric(full_schema['micro']['recall'])} | "
            f"{_format_metric(full_schema['micro']['f1'])} |",
        ]
    )
    for canonical_type, metric in full_schema["per_type"].items():
        lines.append(
            f"| `{canonical_type}` | {metric['tp']} | {metric['fp']} | "
            f"{metric['fn']} | {_format_metric(metric['precision'])} | "
            f"{_format_metric(metric['recall'])} | {_format_metric(metric['f1'])} |"
        )
    lines.extend(
        [
            "",
            f"Macro F1: **{_format_metric(full_schema['macro_f1'])}**",
            "",
            "## Schema coverage",
            "",
            f"- Gold entities: {coverage['gold']['scored']} scored / "
            f"{coverage['gold']['total']} total; unscored by type: "
            f"`{coverage['gold']['unscored_by_type']}`",
            f"- Predicted entities: {coverage['predicted']['scored']} scored / "
            f"{coverage['predicted']['total']} total; unscored by type: "
            f"`{coverage['predicted']['unscored_by_type']}`",
            "",
            "## Failure analysis",
            "",
            "| Category | Count |",
            "| --- | ---: |",
        ]
    )
    for category, count in failures.items():
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "Representative records are retained in the machine-readable report.",
            "",
            "## Graph-critical NER diagnostic",
            "",
            f"- Overall mention recall: `{_format_metric(graph['mention_level']['overall']['recall'])}` "
            f"({graph['mention_level']['overall']['recognized']} / {graph['mention_level']['overall']['gold']})",
            f"- Comparable-class mention recall: `{_format_metric(graph['mention_level']['comparable_class']['recall'])}` "
            f"({graph['mention_level']['comparable_class']['recognized']} / {graph['mention_level']['comparable_class']['gold']})",
            f"- Overall concept recall: `{_format_metric(graph['concept_level']['overall']['recall'])}` "
            f"({graph['concept_level']['overall']['recognized']} / {graph['concept_level']['overall']['gold']})",
            f"- Comparable-class concept recall: `{_format_metric(graph['concept_level']['comparable_class']['recall'])}` "
            f"({graph['concept_level']['comparable_class']['recognized']} / {graph['concept_level']['comparable_class']['gold']})",
            "- This uses relation participation annotations only; it is not relation evaluation.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def _print_summary(report: Mapping[str, Any], json_path: Path, markdown_path: Path) -> None:
    """Print the key baseline result without hiding coverage limitations."""

    dataset = report["dataset"]
    counts = report["counts"]
    micro = report["metrics"]["exact_match"]["micro"]
    graph = report["graph_critical_entity_recall"]
    print("BioRED exact-match biomedical NER evaluation")
    print(
        f"Documents: {counts['documents_evaluated']} / "
        f"{dataset['documents_in_source']}"
    )
    print(
        f"Gold entities: {counts['gold_entities_scored']} scored / "
        f"{counts['gold_entities']} total"
    )
    print(
        f"Micro exact match: P={_format_metric(micro['precision'])} "
        f"R={_format_metric(micro['recall'])} F1={_format_metric(micro['f1'])} "
        f"(TP={micro['tp']} FP={micro['fp']} FN={micro['fn']})"
    )
    print(
        "Graph-critical mention recall: "
        f"{_format_metric(graph['mention_level']['recall'])}"
    )
    print(f"JSON report: {json_path.resolve()}")
    print(f"Markdown report: {markdown_path.resolve()}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the current default GLiNER path through the NER evaluator."""

    args = _parser().parse_args(argv)
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be a positive integer")
    if args.failure_example_limit < 0:
        raise ValueError("--failure-example-limit must not be negative")

    dataset = load_biored(args.dataset, args.split)
    documents = dataset.documents[: args.limit]
    output_path = args.output or _default_output(args.limit, split=args.split)
    markdown_path = args.markdown_output or _default_markdown_output(output_path)

    print(
        f"Evaluating {len(documents)} BioRED document(s) with "
        f"{DEFAULT_ENTITY_MODEL} at threshold {args.entity_threshold}...",
        file=sys.stderr,
        flush=True,
    )
    extractor = GLiNERBioMedExtractor.from_pretrained(
        labels=DEFAULT_CORE_ENTITY_LABELS,
        threshold=args.entity_threshold,
        device=args.device,
    )
    report = evaluate_biored(
        dataset,
        extractor,
        documents=documents,
        supported_types=COMPARABLE_CANONICAL_TYPES,
        failure_example_limit=args.failure_example_limit,
    )
    report["predictor"] = {
        "adapter": "GLiNERBioMedExtractor",
        "name": "GLiNER BioRED",
        "model": DEFAULT_ENTITY_MODEL,
        "threshold": args.entity_threshold,
        "labels": list(DEFAULT_CORE_ENTITY_LABELS),
        "device": args.device or "auto",
    }
    _write_json(output_path, report)
    _write_text(markdown_path, render_markdown_report(report))
    _print_summary(report, output_path, markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "main",
    "render_markdown_report",
]
