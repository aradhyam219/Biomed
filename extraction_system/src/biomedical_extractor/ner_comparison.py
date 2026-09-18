"""Deterministic head-to-head reporting for BioRED NER evaluation reports."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping

from .ner_evaluation import ALL_CANONICAL_TYPES, COMPARABLE_CANONICAL_TYPES


MODEL_NAMES = ("GLiNER", "AIONER")


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
    """Build a schema-explicit GLiNER/AIONER comparison from two reports."""

    validate_report_arithmetic(gliner_report)
    validate_report_arithmetic(aioner_report)
    gliner_dataset = gliner_report["dataset"]
    aioner_dataset = aioner_report["dataset"]
    if gliner_dataset["split"] != "test" or aioner_dataset["split"] != "test":
        raise ValueError("Head-to-head comparison requires BioRED Test reports")
    if gliner_dataset["sha256"] != aioner_dataset["sha256"]:
        raise ValueError("GLiNER and AIONER reports use different dataset hashes")
    if gliner_dataset["documents_evaluated"] != aioner_dataset["documents_evaluated"]:
        raise ValueError("GLiNER and AIONER reports cover different documents")

    model_reports = {"GLiNER": gliner_report, "AIONER": aioner_report}
    shared_models = {
        name: _view(report, "shared_class") for name, report in model_reports.items()
    }
    full_models = {
        name: _view(report, "full_schema") for name, report in model_reports.items()
    }
    failure_summary = _failure_summary(model_reports)
    return {
        "evaluation_name": "BioRED Test GLiNER versus AIONER NER comparison",
        "dataset": {
            "path": gliner_dataset["path"],
            "split": "test",
            "sha256": gliner_dataset["sha256"],
            "source": gliner_dataset.get("source", ""),
            "date": gliner_dataset.get("date", ""),
            "key": gliner_dataset.get("key", ""),
            "documents_evaluated": gliner_dataset["documents_evaluated"],
            "documents_in_source": gliner_dataset["documents_in_source"],
            "gold_entities": gliner_report["counts"]["gold_entities"],
            "gold_entities_by_type": gliner_report["counts"].get(
                "gold_entities_by_type", {}
            ),
        },
        "shared_class_head_to_head": {
            "supported_types": list(COMPARABLE_CANONICAL_TYPES),
            "models": shared_models,
            "per_type": _per_type_comparison(shared_models, COMPARABLE_CANONICAL_TYPES),
        },
        "full_schema_coverage": {
            "schema": list(ALL_CANONICAL_TYPES),
            "models": full_models,
            "per_type": _per_type_comparison(full_models, ALL_CANONICAL_TYPES),
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
        "failure_summary": failure_summary,
        "limitations": [
            "This comparison uses exact half-open source spans and canonical types; no fuzzy matching is applied.",
            "Shared-class metrics use the five classes supported by both adapters.",
            "Full-schema views retain the explicit SequenceVariant capability gap for GLiNER.",
            "Graph-critical recall uses BioRED relation participation only as an NER diagnostic; no relation model is invoked.",
            "Published AIONER scores are context only; this report does not declare a production winner or rank HunFlair2.",
            "Failure overlap is exact only for retained representative examples; aggregate both fields are upper bounds and only fields are count differences.",
            "Inference wall-clock is not compared because the isolated official AIONER run and GLiNER evaluation were not timed with identical scopes; AIONER was run on CPU.",
        ],
    }


def render_comparison_markdown(report: Mapping[str, Any]) -> str:
    """Render the compact reviewer-facing comparison report."""

    dataset = report["dataset"]
    shared = report["shared_class_head_to_head"]
    full = report["full_schema_coverage"]
    models = shared["models"]
    lines = [
        "# GLiNER vs AIONER on BioRED Test",
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
    for name in MODEL_NAMES:
        predictor = models[name]["predictor"]
        runtime = predictor.get("runtime", {})
        lines.append(
            f"- **{name}**: `{predictor.get('model', 'unspecified')}`; "
            f"adapter `{predictor.get('adapter', 'unspecified')}`; "
            f"device `{predictor.get('device', predictor.get('execution_device', 'unspecified'))}`; "
            f"runtime `{runtime}`"
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
    for name in MODEL_NAMES:
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
            "| Type | GLiNER P/R/F1 | AIONER P/R/F1 | AIONER - GLiNER F1 |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for canonical_type in shared["supported_types"]:
        gliner = shared["per_type"][canonical_type]["GLiNER"]
        aioner = shared["per_type"][canonical_type]["AIONER"]
        lines.append(
            f"| `{canonical_type}` | {_triple(gliner)} | {_triple(aioner)} | "
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
    for name in MODEL_NAMES:
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
            f"- GLiNER supported: `{variant['gliner_supported']}`; metric: `{variant['gliner_metric']}`",
            f"- AIONER supported: `{variant['aioner_supported']}`; metric: `{variant['aioner_metric']}`",
            "",
            "## Graph-critical recall",
            "",
            "| View | GLiNER mention | AIONER mention | GLiNER concept | AIONER concept |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for view_name, label in (("overall", "Overall"), ("comparable_class", "Comparable-class")):
        mention = report["graph_critical_recall"]["mention_level"]
        concept = report["graph_critical_recall"]["concept_level"]
        lines.append(
            f"| {label} | {_format(mention['GLiNER'][view_name]['recall'])} "
            f"({mention['GLiNER'][view_name]['recognized']}/{mention['GLiNER'][view_name]['gold']}) | "
            f"{_format(mention['AIONER'][view_name]['recall'])} "
            f"({mention['AIONER'][view_name]['recognized']}/{mention['AIONER'][view_name]['gold']}) | "
            f"{_format(concept['GLiNER'][view_name]['recall'])} "
            f"({concept['GLiNER'][view_name]['recognized']}/{concept['GLiNER'][view_name]['gold']}) | "
            f"{_format(concept['AIONER'][view_name]['recall'])} "
            f"({concept['AIONER'][view_name]['recognized']}/{concept['AIONER'][view_name]['gold']}) |"
        )
    lines.extend(
        [
            "",
            "## Failure-count differences",
            "",
            "| Category | GLiNER | AIONER | Both count upper bound | GLiNER-only difference | AIONER-only difference |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for category, values in report["failure_summary"]["categories"].items():
        lines.append(
            f"| {category} | {values['GLiNER']} | {values['AIONER']} | "
            f"{values['both_count_upper_bound']} | {values['GLiNER_only_count_difference']} | "
            f"{values['AIONER_only_count_difference']} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.append("")
    return "\n".join(lines)


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
    canonical_types: tuple[str, ...],
) -> dict[str, Any]:
    """Align per-type metrics and compute AIONER-minus-GLiNER F1."""

    result: dict[str, Any] = {}
    for canonical_type in canonical_types:
        gliner = models["GLiNER"]["per_type"].get(canonical_type)
        aioner = models["AIONER"]["per_type"].get(canonical_type)
        result[canonical_type] = {
            "GLiNER": gliner,
            "AIONER": aioner,
            "f1_delta": _difference(
                None if gliner is None else gliner["f1"],
                None if aioner is None else aioner["f1"],
            ),
        }
    return result


def _difference(gliner: float | None, aioner: float | None) -> float | None:
    """Return a numeric F1 difference only when both values are defined."""

    return None if gliner is None or aioner is None else aioner - gliner


def _variant_coverage(reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Describe the explicit SequenceVariant schema difference."""

    result: dict[str, Any] = {}
    for name, report in reports.items():
        view = _view(report, "full_schema")
        coverage = report["schema_coverage"]["gold"]
        result[name.lower() + "_supported"] = "SequenceVariant" in view[
            "supported_canonical_types"
        ]
        result[name.lower() + "_metric"] = view["per_type"].get("SequenceVariant")
        result[name.lower() + "_gold_mentions"] = sum(
            count
            for raw_type, count in coverage.get("unscored_by_type", {}).items()
            if raw_type == "Variant"
        )
        if result[name.lower() + "_metric"] is not None:
            metric_key = name.lower() + "_metric"
            result[name.lower() + "_gold_mentions"] = result[metric_key]["support"]
    return {
        "gold_mentions": max(
            result.get("gliner_gold_mentions", 0),
            result.get("aioner_gold_mentions", 0),
        ),
        "gliner_supported": result["gliner_supported"],
        "aioner_supported": result["aioner_supported"],
        "gliner_metric": result["gliner_metric"],
        "aioner_metric": result["aioner_metric"],
    }


def _failure_summary(
    reports: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare deterministic failure counts and retained examples."""

    categories = set()
    for report in reports.values():
        categories.update(report["failure_analysis"]["counts"])
    result: dict[str, Any] = {}
    for category in sorted(categories):
        gliner_count = reports["GLiNER"]["failure_analysis"]["counts"].get(category, 0)
        aioner_count = reports["AIONER"]["failure_analysis"]["counts"].get(category, 0)
        result[category] = {
            "GLiNER": gliner_count,
            "AIONER": aioner_count,
            "both_count_upper_bound": min(gliner_count, aioner_count),
            "GLiNER_only_count_difference": max(gliner_count - aioner_count, 0),
            "AIONER_only_count_difference": max(aioner_count - gliner_count, 0),
            "shared_representative_examples": _shared_examples(
                reports["GLiNER"], reports["AIONER"], category
            ),
        }
    return {
        "categories": result,
        "note": "Both aggregate fields are upper bounds and only fields are count differences; representative overlap uses bounded retained examples.",
    }


def _shared_examples(
    left: Mapping[str, Any], right: Mapping[str, Any], category: str
) -> list[dict[str, Any]]:
    """Return exact intersections of bounded deterministic example records."""

    left_records = left["failure_analysis"]["examples"].get(category, [])
    right_records = right["failure_analysis"]["examples"].get(category, [])
    right_by_key = {_failure_key(record): record for record in right_records}
    return [right_by_key[key] for key in (_failure_key(record) for record in left_records) if key in right_by_key]


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
    "render_comparison_markdown",
    "validate_report_arithmetic",
]
