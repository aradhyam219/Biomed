"""Deterministic head-to-head reporting for BioRED NER reports."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence

from .ner_evaluation import ALL_CANONICAL_TYPES, COMPARABLE_CANONICAL_TYPES


MODEL_NAMES = ("GLiNER", "AIONER")
DEFAULT_SMALL_F1_DIFFERENCE = 0.01


def validate_report_arithmetic(report: Mapping[str, Any]) -> None:
    """Validate exact P/R/F1 and macro arithmetic in one evaluator report."""

    metrics = report["metrics"]
    views = {
        "shared_class": metrics.get("shared_class", metrics["exact_match"]),
        "full_schema": metrics.get("full_schema", metrics["exact_match"]),
    }
    for view_name, view in views.items():
        _validate_metric(view["micro"], f"{view_name}.micro")
        for canonical_type, metric in view["per_type"].items():
            _validate_metric(metric, f"{view_name}.per_type.{canonical_type}")
        expected_macro_values = [
            metric["f1"]
            for metric in view["per_type"].values()
            if metric["f1"] is not None
        ]
        expected_macro = (
            sum(expected_macro_values) / len(expected_macro_values)
            if expected_macro_values
            else None
        )
        _assert_close(view["macro_f1"], expected_macro, f"{view_name}.macro_f1")


def build_comparison_report(
    gliner_report: Mapping[str, Any],
    aioner_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the preserved GLiNER/AIONER comparison contract."""

    return build_model_comparison_report(
        gliner_report,
        aioner_report,
        first_name="GLiNER",
        second_name="AIONER",
    )


def build_model_comparison_report(
    first_report: Mapping[str, Any],
    second_report: Mapping[str, Any],
    *,
    first_name: str,
    second_name: str,
) -> dict[str, Any]:
    """Build a schema-explicit comparison for any two evaluator reports."""

    if not first_name or not second_name or first_name == second_name:
        raise ValueError("Comparison model names must be distinct and non-empty")
    validate_report_arithmetic(first_report)
    validate_report_arithmetic(second_report)
    first_dataset = first_report["dataset"]
    second_dataset = second_report["dataset"]
    if first_dataset["split"] != "test" or second_dataset["split"] != "test":
        raise ValueError("Head-to-head comparison requires BioRED Test reports")
    if first_dataset["sha256"] != second_dataset["sha256"]:
        raise ValueError("NER reports use different dataset hashes")
    if first_dataset["documents_evaluated"] != second_dataset["documents_evaluated"]:
        raise ValueError("NER reports cover different documents")
    if first_dataset.get("documents_in_source") != second_dataset.get("documents_in_source"):
        raise ValueError("NER reports use different source document counts")

    model_names = (first_name, second_name)
    model_reports = {first_name: first_report, second_name: second_report}
    shared_models = {
        name: _view(report, "shared_class")
        for name, report in model_reports.items()
    }
    full_models = {
        name: _view(report, "full_schema")
        for name, report in model_reports.items()
    }
    return {
        "evaluation_name": (
            f"BioRED Test {first_name} versus {second_name} NER comparison"
        ),
        "comparison": {
            "first_model": first_name,
            "second_model": second_name,
            "active_candidates": [first_name, second_name],
        },
        "dataset": {
            "path": first_dataset["path"],
            "split": "test",
            "sha256": first_dataset["sha256"],
            "source": first_dataset.get("source", ""),
            "date": first_dataset.get("date", ""),
            "key": first_dataset.get("key", ""),
            "documents_evaluated": first_dataset["documents_evaluated"],
            "documents_in_source": first_dataset["documents_in_source"],
            "gold_entities": first_report["counts"]["gold_entities"],
            "gold_entities_by_type": first_report["counts"].get(
                "gold_entities_by_type", {}
            ),
        },
        "shared_class_head_to_head": {
            "supported_types": list(COMPARABLE_CANONICAL_TYPES),
            "models": shared_models,
            "per_type": _per_type_comparison(
                shared_models, COMPARABLE_CANONICAL_TYPES, model_names
            ),
        },
        "full_schema_coverage": {
            "schema": list(ALL_CANONICAL_TYPES),
            "models": full_models,
            "per_type": _per_type_comparison(
                full_models, ALL_CANONICAL_TYPES, model_names
            ),
            "variant": _variant_coverage(model_reports),
        },
        "models": {
            name: {
                "predictor": report.get("predictor", {}),
                "schema_coverage": report["schema_coverage"],
                "graph_critical_entity_recall": report[
                    "graph_critical_entity_recall"
                ],
                "failure_counts": report["failure_analysis"]["counts"],
            }
            for name, report in model_reports.items()
        },
        "graph_critical_recall": {
            "mention_level": {
                name: _graph_view(report, "mention_level")
                for name, report in model_reports.items()
            },
            "concept_level": {
                name: _graph_view(report, "concept_level")
                for name, report in model_reports.items()
            },
        },
        "failure_summary": _failure_summary(model_reports, model_names),
        "decision_evidence": _decision_evidence(
            shared_models,
            model_reports,
            model_names,
            DEFAULT_SMALL_F1_DIFFERENCE,
        ),
        "limitations": [
            "This comparison uses exact half-open source spans and canonical types; no fuzzy matching is applied.",
            "Shared-class metrics use the five classes supported by both adapters.",
            "Full-schema views retain the explicit SequenceVariant capability difference.",
            "Graph-critical recall uses BioRED relation participation only as an NER diagnostic; no relation model is invoked.",
            "Failure overlap is exact only for bounded retained representative examples; aggregate counts are reported separately.",
            "Inference wall-clock is descriptive for each model and is not ranked because the isolated runtimes were not executed under equivalent scopes.",
            "This report provides numerical evidence only and does not declare a production winner.",
        ],
    }


def render_comparison_markdown(report: Mapping[str, Any]) -> str:
    """Render the preserved GLiNER/AIONER comparison report."""

    return render_model_comparison_markdown(report)


def render_model_comparison_markdown(report: Mapping[str, Any]) -> str:
    """Render a compact reviewer-facing comparison for any model pair."""

    dataset = report["dataset"]
    comparison = report.get("comparison", {})
    first_name = comparison.get("first_model", MODEL_NAMES[0])
    second_name = comparison.get("second_model", MODEL_NAMES[1])
    model_names = (first_name, second_name)
    shared = report["shared_class_head_to_head"]
    full = report["full_schema_coverage"]
    models = shared["models"]
    decision = report.get("decision_evidence", {})
    lines = [
        f"# {first_name} vs {second_name} on BioRED Test",
        "",
        "This is comparative NER evidence, not a production model-selection decision.",
        "",
        "## Dataset identity",
        "",
        f"- Path: `{dataset['path']}`",
        f"- Split: `{dataset['split']}`",
        f"- SHA-256: `{dataset['sha256']}`",
        f"- Documents: {dataset['documents_evaluated']} / {dataset['documents_in_source']}",
        f"- Gold entities: {dataset['gold_entities']}",
        f"- Gold entities by BioRED type: `{dataset['gold_entities_by_type']}`",
        "",
        "## Model/runtime identities",
        "",
    ]
    for name in model_names:
        predictor = models[name]["predictor"]
        runtime = predictor.get("runtime", {})
        duration = predictor.get("inference_duration_seconds")
        duration_text = "N/A" if duration is None else f"{duration:.3f}s"
        lines.append(
            f"- **{name}**: `{predictor.get('model', 'unspecified')}`; "
            f"adapter `{predictor.get('adapter', 'unspecified')}`; "
            f"device `{predictor.get('device', predictor.get('execution_device', 'unspecified'))}`; "
            f"runtime `{runtime}`; inference duration `{duration_text}`"
        )
    lines.extend(
        [
            "",
            "## Shared-class head-to-head",
            "",
            "Classes: `" + "`, `".join(shared["supported_types"]) + "`",
            "",
            "| Model | TP | FP | FN | Precision | Recall | F1 | Macro F1 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in model_names:
        view = models[name]
        micro = view["micro"]
        lines.append(
            f"| {name} | {micro['tp']} | {micro['fp']} | {micro['fn']} | "
            f"{_format(micro['precision'])} | {_format(micro['recall'])} | "
            f"{_format(micro['f1'])} | {_format(view['macro_f1'])} |"
        )
    lines.extend(
        [
            "",
            "### Shared-class per-type metrics",
            "",
            f"| Type | {first_name} P/R/F1 | {second_name} P/R/F1 | "
            f"{second_name} - {first_name} F1 |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for canonical_type in shared["supported_types"]:
        first = shared["per_type"][canonical_type][first_name]
        second = shared["per_type"][canonical_type][second_name]
        lines.append(
            f"| `{canonical_type}` | {_triple(first)} | {_triple(second)} | "
            f"{_format(shared['per_type'][canonical_type]['f1_delta'])} |"
        )
    lines.extend(
        [
            "",
            "## Full-schema coverage",
            "",
            "| Model | Supported canonical classes | Unsupported canonical classes | Micro F1 | Macro F1 |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for name in model_names:
        view = full["models"][name]
        lines.append(
            f"| {name} | `{view['supported_canonical_types']}` | "
            f"`{view.get('unsupported_canonical_types', [])}` | "
            f"{_format(view['micro']['f1'])} | {_format(view['macro_f1'])} |"
        )
    variant = full["variant"]
    lines.extend(
        [
            "",
            "### SequenceVariant coverage",
            "",
            f"- Gold mentions: {variant['gold_mentions']}",
        ]
    )
    for name in model_names:
        model_variant = variant["models"][name]
        lines.append(
            f"- {name} supported: `{model_variant['supported']}`; "
            f"metric: `{model_variant['metric']}`"
        )
    lines.extend(
        [
            "",
            "## Graph-critical recall",
            "",
            f"| View | {first_name} mention | {second_name} mention | "
            f"{first_name} concept | {second_name} concept |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for view_name, label in (("overall", "Overall"), ("comparable_class", "Comparable-class")):
        mention = report["graph_critical_recall"]["mention_level"]
        concept = report["graph_critical_recall"]["concept_level"]
        lines.append(
            f"| {label} | {_format(mention[first_name][view_name]['recall'])} "
            f"({mention[first_name][view_name]['recognized']}/{mention[first_name][view_name]['gold']}) | "
            f"{_format(mention[second_name][view_name]['recall'])} "
            f"({mention[second_name][view_name]['recognized']}/{mention[second_name][view_name]['gold']}) | "
            f"{_format(concept[first_name][view_name]['recall'])} "
            f"({concept[first_name][view_name]['recognized']}/{concept[first_name][view_name]['gold']}) | "
            f"{_format(concept[second_name][view_name]['recall'])} "
            f"({concept[second_name][view_name]['recognized']}/{concept[second_name][view_name]['gold']}) |"
        )
    lines.extend(["", "## Decision-evidence summary", ""])
    lines.extend(_decision_markdown_lines(decision, first_name, second_name))
    lines.extend(
        [
            "",
            "## Failure-count differences",
            "",
            f"| Category | {first_name} | {second_name} | Both count upper bound | "
            f"{first_name}-only count difference | {second_name}-only count difference |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    first_only_key = f"{_safe_name(first_name)}_only_count_difference"
    second_only_key = f"{_safe_name(second_name)}_only_count_difference"
    for category, values in report["failure_summary"]["categories"].items():
        lines.append(
            f"| {category} | {values[first_name]} | {values[second_name]} | "
            f"{values['both_count_upper_bound']} | {values[first_only_key]} | "
            f"{values[second_only_key]} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def _decision_evidence(
    shared_models: Mapping[str, Mapping[str, Any]],
    model_reports: Mapping[str, Mapping[str, Any]],
    model_names: tuple[str, str],
    small_difference_threshold: float,
) -> dict[str, Any]:
    """Compute factual comparison answers without selecting a production model."""

    first_name, second_name = model_names

    def metric_comparison(first: float | None, second: float | None) -> dict[str, Any]:
        delta = None if first is None or second is None else second - first
        absolute = None if delta is None else abs(delta)
        if first is None or second is None:
            higher = None
        elif second > first:
            higher = second_name
        elif first > second:
            higher = first_name
        else:
            higher = "tie"
        return {
            first_name: first,
            second_name: second,
            "delta_second_minus_first": delta,
            "absolute_delta": absolute,
            "higher": higher,
            "within_small_difference": (
                absolute is not None and absolute <= small_difference_threshold
            ),
        }

    shared_micro = metric_comparison(
        shared_models[first_name]["micro"]["f1"],
        shared_models[second_name]["micro"]["f1"],
    )
    shared_macro = metric_comparison(
        shared_models[first_name]["macro_f1"],
        shared_models[second_name]["macro_f1"],
    )
    per_type: dict[str, Any] = {}
    first_higher: list[str] = []
    second_higher: list[str] = []
    ties: list[str] = []
    for canonical_type in COMPARABLE_CANONICAL_TYPES:
        first_metric = shared_models[first_name]["per_type"].get(canonical_type)
        second_metric = shared_models[second_name]["per_type"].get(canonical_type)
        comparison = metric_comparison(
            None if first_metric is None else first_metric["f1"],
            None if second_metric is None else second_metric["f1"],
        )
        per_type[canonical_type] = comparison
        if comparison["higher"] == first_name:
            first_higher.append(canonical_type)
        elif comparison["higher"] == second_name:
            second_higher.append(canonical_type)
        elif comparison["higher"] == "tie":
            ties.append(canonical_type)

    graph: dict[str, Any] = {}
    for level in ("mention_level", "concept_level"):
        for view in ("overall", "comparable_class"):
            graph[f"{level}.{view}"] = metric_comparison(
                model_reports[first_name]["graph_critical_entity_recall"][level][view][
                    "recall"
                ],
                model_reports[second_name]["graph_critical_entity_recall"][level][view][
                    "recall"
                ],
            )

    variant_models = {
        name: {
            "supported": "SequenceVariant"
            in model_reports[name]["metrics"]["full_schema"][
                "supported_canonical_types"
            ],
            "gold_mentions": _variant_gold_mentions(model_reports[name]),
        }
        for name in model_names
    }
    return {
        "shared_class_micro_f1": shared_micro,
        "shared_class_macro_f1": shared_macro,
        "shared_class_per_type_f1": per_type,
        "classes_with_higher_f1": {
            first_name: first_higher,
            second_name: second_higher,
            "ties": ties,
        },
        "graph_critical_recall": graph,
        "sequence_variant": variant_models,
        "small_difference_threshold": small_difference_threshold,
        "target_domain_reconnaissance_relevant": (
            shared_micro["within_small_difference"]
            or shared_macro["within_small_difference"]
        ),
    }


def _decision_markdown_lines(
    decision: Mapping[str, Any], first_name: str, second_name: str
) -> list[str]:
    """Render the seven requested factual decision questions."""

    micro = decision["shared_class_micro_f1"]
    macro = decision["shared_class_macro_f1"]
    mention = decision["graph_critical_recall"]["mention_level.comparable_class"]
    concept = decision["graph_critical_recall"]["concept_level.comparable_class"]
    variant = decision["sequence_variant"]
    first_variant = variant[first_name]["supported"]
    second_variant = variant[second_name]["supported"]
    return [
        f"1. Shared-class micro F1 higher: **{micro['higher']}**; delta "
        f"({second_name} - {first_name}) = `{_format(micro['delta_second_minus_first'])}`.",
        f"2. Shared-class macro F1 higher: **{macro['higher']}**; delta "
        f"({second_name} - {first_name}) = `{_format(macro['delta_second_minus_first'])}`.",
        f"3. Per-type F1 higher: `{decision['classes_with_higher_f1']}`.",
        f"4. Comparable graph-critical mention recall higher: **{mention['higher']}**; "
        f"delta = `{_format(mention['delta_second_minus_first'])}`.",
        f"5. Comparable graph-critical concept recall higher: **{concept['higher']}**; "
        f"delta = `{_format(concept['delta_second_minus_first'])}`.",
        f"6. SequenceVariant capability: `{first_name}={first_variant}`, "
        f"`{second_name}={second_variant}`; gold mentions = `{max(variant[first_name]['gold_mentions'], variant[second_name]['gold_mentions'])}`.",
        f"7. At least one primary shared-score difference is within "
        f"`{decision['small_difference_threshold']:.4f}`: "
        f"`{decision['target_domain_reconnaissance_relevant']}`; no production winner is declared.",
    ]


def _validate_metric(metric: Mapping[str, Any], label: str) -> None:
    """Validate one metric's count-derived values."""

    tp = int(metric["tp"])
    fp = int(metric["fp"])
    fn = int(metric["fn"])
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    observed = tp + fp + fn
    f1 = 2 * tp / (2 * tp + fp + fn) if observed else None
    _assert_close(metric["precision"], precision, f"{label}.precision")
    _assert_close(metric["recall"], recall, f"{label}.recall")
    _assert_close(metric["f1"], f1, f"{label}.f1")


def _assert_close(actual: Any, expected: Any, label: str) -> None:
    """Raise a useful error when serialized arithmetic is inconsistent."""

    if actual is None or expected is None:
        if actual is not None or expected is not None:
            raise ValueError(f"Invalid {label}: expected {expected}, got {actual}")
        return
    if not math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError(f"Invalid {label}: expected {expected}, got {actual}")


def _view(report: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Copy one metric view with predictor metadata for comparison output."""

    metrics = report["metrics"].get(name, report["metrics"]["exact_match"])
    return {
        **metrics,
        "predictor": report.get("predictor", {}),
    }


def _per_type_comparison(
    models: Mapping[str, Mapping[str, Any]],
    canonical_types: Sequence[str],
    model_names: tuple[str, str],
) -> dict[str, Any]:
    """Align per-type metrics and compute second-minus-first F1."""

    first_name, second_name = model_names
    result: dict[str, Any] = {}
    for canonical_type in canonical_types:
        first = models[first_name]["per_type"].get(canonical_type)
        second = models[second_name]["per_type"].get(canonical_type)
        result[canonical_type] = {
            first_name: first,
            second_name: second,
            "f1_delta": _difference(
                None if first is None else first["f1"],
                None if second is None else second["f1"],
            ),
        }
    return result


def _difference(first: float | None, second: float | None) -> float | None:
    """Return a numeric F1 difference only when both values are defined."""

    return None if first is None or second is None else second - first


def _variant_gold_mentions(report: Mapping[str, Any]) -> int:
    """Return the explicit BioRED Variant support count for one report."""

    full = report["metrics"].get("full_schema", report["metrics"]["exact_match"])
    metric = full["per_type"].get("SequenceVariant")
    if metric is not None:
        return int(metric["support"])
    return int(
        report["schema_coverage"]["gold"].get("unscored_by_type", {}).get("Variant", 0)
    )


def _variant_coverage(reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Describe the explicit SequenceVariant schema difference."""

    models: dict[str, Any] = {}
    for name, report in reports.items():
        view = _view(report, "full_schema")
        models[name] = {
            "supported": "SequenceVariant" in view["supported_canonical_types"],
            "metric": view["per_type"].get("SequenceVariant"),
            "gold_mentions": _variant_gold_mentions(report),
        }
    result: dict[str, Any] = {
        "gold_mentions": max(item["gold_mentions"] for item in models.values()),
        "models": models,
    }
    for name, item in models.items():
        key = _safe_name(name)
        result[f"{key}_supported"] = item["supported"]
        result[f"{key}_metric"] = item["metric"]
        result[f"{key}_gold_mentions"] = item["gold_mentions"]
    return result


def _failure_summary(
    reports: Mapping[str, Mapping[str, Any]],
    model_names: tuple[str, str],
) -> dict[str, Any]:
    """Compare deterministic counts and bounded exact example intersections."""

    first_name, second_name = model_names
    categories = set()
    for report in reports.values():
        categories.update(report["failure_analysis"]["counts"])
    result: dict[str, Any] = {}
    first_only_key = f"{_safe_name(first_name)}_only_count_difference"
    second_only_key = f"{_safe_name(second_name)}_only_count_difference"
    for category in sorted(categories):
        first_count = reports[first_name]["failure_analysis"]["counts"].get(category, 0)
        second_count = reports[second_name]["failure_analysis"]["counts"].get(category, 0)
        result[category] = {
            first_name: first_count,
            second_name: second_count,
            "both_count_upper_bound": min(first_count, second_count),
            first_only_key: max(first_count - second_count, 0),
            second_only_key: max(second_count - first_count, 0),
            "shared_representative_examples": _shared_examples(
                reports[first_name], reports[second_name], category
            ),
        }
    return {
        "models": list(model_names),
        "categories": result,
        "note": (
            "Both aggregate fields are upper bounds and only fields are count "
            "differences; representative overlap uses bounded retained examples."
        ),
    }


def _shared_examples(
    left: Mapping[str, Any], right: Mapping[str, Any], category: str
) -> list[dict[str, Any]]:
    """Return exact intersections of bounded deterministic example records."""

    left_records = left["failure_analysis"]["examples"].get(category, [])
    right_records = right["failure_analysis"]["examples"].get(category, [])
    right_by_key = {_failure_key(record): record for record in right_records}
    return [
        right_by_key[key]
        for key in (_failure_key(record) for record in left_records)
        if key in right_by_key
    ]


def _failure_key(record: Mapping[str, Any]) -> str:
    """Create a stable comparable key for one retained failure example."""

    return json.dumps(
        {
            "document_id": record.get("document_id"),
            "category": record.get("category"),
            "gold": record.get("gold"),
            "predicted": record.get("predicted"),
        },
        sort_keys=True,
    )


def _graph_view(report: Mapping[str, Any], level: str) -> dict[str, Any]:
    """Return the explicit graph recall views from one evaluator report."""

    return report["graph_critical_entity_recall"][level]


def _safe_name(name: str) -> str:
    """Create stable JSON field names for model-specific difference fields."""

    return "".join(
        character.lower() if character.isalnum() else "_" for character in name
    ).strip("_")


def _format(value: float | None) -> str:
    """Format nullable metrics for Markdown."""

    return "N/A" if value is None else f"{value:.4f}"


def _triple(metric: Mapping[str, Any] | None) -> str:
    """Format one per-type P/R/F1 triple."""

    return "N/A" if metric is None else "/".join(
        _format(metric[key]) for key in ("precision", "recall", "f1")
    )


__all__ = [
    "build_comparison_report",
    "build_model_comparison_report",
    "render_comparison_markdown",
    "render_model_comparison_markdown",
    "validate_report_arithmetic",
]
