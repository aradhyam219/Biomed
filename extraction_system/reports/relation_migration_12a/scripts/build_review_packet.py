"""Build the semantic and operational Contract 12A review packet.

Scientific deltas are serialized separately from provider telemetry. This
utility includes every relation/evidence field and every graph node and edge;
it performs deterministic comparisons only and makes no quality judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_ROOT = ROOT / ".cache/relation_migration_12a"
DEFAULT_REPORT_ROOT = ROOT / "reports/relation_migration_12a"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _multiset_delta(baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic multiset differences, preserving exact records."""

    baseline_counts = Counter(_key(item) for item in baseline)
    candidate_counts = Counter(_key(item) for item in candidate)
    baseline_by_key = {_key(item): item for item in baseline}
    candidate_by_key = {_key(item): item for item in candidate}
    baseline_only = [
        baseline_by_key[key]
        for key in sorted(baseline_counts.keys() | candidate_counts.keys())
        for _ in range(max(0, baseline_counts[key] - candidate_counts[key]))
    ]
    candidate_only = [
        candidate_by_key[key]
        for key in sorted(baseline_counts.keys() | candidate_counts.keys())
        for _ in range(max(0, candidate_counts[key] - baseline_counts[key]))
    ]
    return {
        "baseline_only": baseline_only,
        "candidate_only": candidate_only,
        "baseline_duplicate_records": sum(max(count - 1, 0) for count in baseline_counts.values()),
        "candidate_duplicate_records": sum(max(count - 1, 0) for count in candidate_counts.values()),
    }


def _relation_field_differences(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, Any]:
    """Pair same directed endpoint/predicate records to expose rich-field edits."""

    def grouping_key(relation: dict[str, Any]) -> str:
        return _key(
            {
                "source": relation.get("source"),
                "target": relation.get("target"),
                "predicate": relation.get("predicate"),
            }
        )

    left: dict[str, list[dict[str, Any]]] = defaultdict(list)
    right: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in baseline:
        left[grouping_key(relation)].append(relation)
    for relation in candidate:
        right[grouping_key(relation)].append(relation)

    matched_changes: list[dict[str, Any]] = []
    unmatched_left: list[dict[str, Any]] = []
    unmatched_right: list[dict[str, Any]] = []
    for group in sorted(left.keys() | right.keys()):
        left_items = sorted(left[group], key=_key)
        right_items = sorted(right[group], key=_key)
        left_counts = Counter(_key(item) for item in left_items)
        right_counts = Counter(_key(item) for item in right_items)
        exact_counts = left_counts & right_counts
        left_remaining = [
            item
            for item in left_items
            if not _take_one(exact_counts, _key(item))
        ]
        # Rebuild the exact multiplicities because the left subtraction above
        # consumes its counter while preserving duplicate records.
        exact_counts = left_counts & right_counts
        right_remaining = [
            item
            for item in right_items
            if not _take_one(exact_counts, _key(item))
        ]
        pair_count = min(len(left_remaining), len(right_remaining))
        for index in range(pair_count):
            base = left_remaining[index]
            cand = right_remaining[index]
            changed = {
                field: {"baseline": base.get(field), "candidate": cand.get(field)}
                for field in sorted(set(base) | set(cand))
                if base.get(field) != cand.get(field)
            }
            matched_changes.append(
                {
                    "semantic_key": json.loads(group),
                    "changed_fields": changed,
                    "baseline_relation": base,
                    "candidate_relation": cand,
                }
            )
        unmatched_left.extend(left_remaining[pair_count:])
        unmatched_right.extend(right_remaining[pair_count:])

    return {
        "matched_changed_records": matched_changes,
        "unpaired_baseline_records": unmatched_left,
        "unpaired_candidate_records": unmatched_right,
    }


def _take_one(counter: Counter[str], key: str) -> bool:
    if counter[key] <= 0:
        return False
    counter[key] -= 1
    return True


def _edge_identity(edge: dict[str, Any]) -> str:
    return _key(
        {
            "source": edge.get("source"),
            "target": edge.get("target"),
            "predicate": edge.get("predicate"),
            "negated": edge.get("negated"),
        }
    )


def _graph_overview(
    graph: dict[str, Any], relations: list[dict[str, Any]]
) -> dict[str, Any]:
    from biomedical_extractor.graph import _is_alias_or_naming_only_relation
    from biomedical_extractor.relation_extraction import Relation

    nodes = graph["nodes"]
    edges = graph["edges"]
    node_ids = {node["id"] for node in nodes}
    connected = {endpoint for edge in edges for endpoint in (edge["source"], edge["target"])}
    edge_key_counts = Counter(_edge_identity(edge) for edge in edges)
    evidence_duplicates = 0
    evidence_count = 0
    for edge in edges:
        evidence_count += len(edge.get("evidence", []))
        evidence_keys = Counter(_key(value) for value in edge.get("evidence", []))
        evidence_duplicates += sum(max(count - 1, 0) for count in evidence_keys.values())

    directed_bundles: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        directed_bundles[(edge["source"], edge["target"])].append(
            {
                "edge_id": edge["id"],
                "source": edge["source"],
                "target": edge["target"],
                "predicate": edge["predicate"],
                "negated": edge["negated"],
                "evidence_count": len(edge.get("evidence", [])),
            }
        )
    directed_bundle_records = []
    for pair in sorted(directed_bundles):
        values = sorted(
            directed_bundles[pair],
            key=lambda item: (item["predicate"], item["negated"], item["edge_id"]),
        )
        directed_bundle_records.append(
            {
                "source_node": pair[0],
                "target_node": pair[1],
                "edge_count": len(values),
                "edges": values,
            }
        )
    directions = set(directed_bundles)
    bidirectional_endpoint_pairs = [
        list(pair)
        for pair in sorted(
            {
                tuple(sorted((source, target)))
                for source, target in directions
                if source != target and (target, source) in directions
            }
        )
    ]

    mention_to_node = {
        mention["id"]: node["id"]
        for node in nodes
        for mention in node.get("mentions", [])
    }
    expected_evidence: list[dict[str, Any]] = []
    suppressed_naming_relations: list[dict[str, Any]] = []
    for relation in relations:
        projected = {
            "source": mention_to_node.get(relation["source"]),
            "target": mention_to_node.get(relation["target"]),
            "predicate": relation["predicate"],
            "negated": relation["negated"],
            "evidence": {
                key: relation.get(key)
                for key in (
                    "evidence",
                    "assertion",
                    "intervention",
                    "effects",
                    "context",
                    "surface_form",
                    "score",
                )
            },
        }
        relation_value = Relation(**relation)
        if projected["source"] == projected["target"] and _is_alias_or_naming_only_relation(
            relation_value
        ):
            suppressed_naming_relations.append(relation)
        else:
            expected_evidence.append(projected)
    actual_evidence = [
        {
            "source": edge["source"],
            "target": edge["target"],
            "predicate": edge["predicate"],
            "negated": edge["negated"],
            "evidence": {
                key: value.get(key)
                for key in (
                    "text",
                    "assertion",
                    "intervention",
                    "effects",
                    "context",
                    "surface_form",
                    "score",
                )
            },
        }
        for edge in edges
        for value in edge.get("evidence", [])
    ]
    # Relation.evidence is the exact source text, while GraphEvidence.text has
    # the graph contract's field name; normalize that single key for comparison.
    expected_evidence = [
        {
            **item,
            "evidence": {
                **{
                    key: value
                    for key, value in item["evidence"].items()
                    if key != "evidence"
                },
                "text": item["evidence"].get("evidence"),
            },
        }
        for item in expected_evidence
    ]
    projected_evidence_counts = Counter(_key(item) for item in expected_evidence)
    actual_evidence_counts = Counter(_key(item) for item in actual_evidence)
    unique_projected_evidence = [
        json.loads(item) for item in sorted(projected_evidence_counts)
    ]
    unique_actual_evidence = [json.loads(item) for item in sorted(actual_evidence_counts)]
    evidence_delta = _multiset_delta(unique_projected_evidence, unique_actual_evidence)
    return {
        "node_count": len(nodes),
        "connected_node_count": len(connected & node_ids),
        "unconnected_node_count": len(node_ids - connected),
        "unconnected_node_ids": [node["id"] for node in nodes if node["id"] not in connected],
        "nodes": nodes,
        "edge_count": len(edges),
        "relation_count": len(relations),
        "evidence_record_count": evidence_count,
        "edges_with_multiple_evidence": [
            {"edge_id": edge["id"], "source": edge["source"], "target": edge["target"], "predicate": edge["predicate"], "evidence_count": len(edge.get("evidence", []))}
            for edge in edges
            if len(edge.get("evidence", [])) > 1
        ],
        "duplicate_edge_identity_count": sum(max(count - 1, 0) for count in edge_key_counts.values()),
        "duplicate_evidence_record_count": evidence_duplicates,
        "self_edges": [edge for edge in edges if edge["source"] == edge["target"]],
        "directed_edge_bundles": directed_bundle_records,
        "bidirectional_endpoint_pairs": bidirectional_endpoint_pairs,
        "rich_evidence_propagation": {
            "projected_relation_evidence_records": len(expected_evidence),
            "unique_projected_relation_evidence_records": len(unique_projected_evidence),
            "collapsed_duplicate_relation_evidence_records": (
                len(expected_evidence) - len(unique_projected_evidence)
            ),
            "actual_graph_evidence_records": len(actual_evidence),
            "unique_actual_graph_evidence_records": len(unique_actual_evidence),
            "duplicate_graph_evidence_records": (
                len(actual_evidence) - len(unique_actual_evidence)
            ),
            "exact_match": not evidence_delta["baseline_only"] and not evidence_delta["candidate_only"],
            "unrepresented_relation_evidence": evidence_delta["baseline_only"],
            "unexpected_graph_evidence": evidence_delta["candidate_only"],
            "alias_or_naming_self_relations_suppressed_by_graph_contract": suppressed_naming_relations,
        },
    }


def _relation_delta(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, Any]:
    multiset = _multiset_delta(baseline, candidate)
    fields = _relation_field_differences(baseline, candidate)
    return {
        "baseline_count": len(baseline),
        "candidate_count": len(candidate),
        "exact_multiset_match": not multiset["baseline_only"] and not multiset["candidate_only"],
        "baseline_only": multiset["baseline_only"],
        "candidate_only": multiset["candidate_only"],
        "matched_changed_records": fields["matched_changed_records"],
        "unpaired_baseline_records": fields["unpaired_baseline_records"],
        "unpaired_candidate_records": fields["unpaired_candidate_records"],
        "baseline_exact_duplicate_record_count": multiset["baseline_duplicate_records"],
        "candidate_exact_duplicate_record_count": multiset["candidate_duplicate_records"],
    }


def _safe_telemetry(
    paper_id: str,
    status: str,
    result: dict[str, Any] | None,
    attempt: dict[str, Any] | None,
) -> dict[str, Any]:
    source = result or attempt or {}
    generations = source.get("generation_diagnostics") or source.get("final_generation_diagnostics") or []
    lifecycle_events = (attempt or {}).get("diagnostic_events", [])
    response_ids = sorted(
        {
            item["response_id"]
            for item in [*lifecycle_events, *generations]
            if isinstance(item, dict) and item.get("response_id")
        }
    )
    unique_generations: dict[int, dict[str, Any]] = {}
    for item in generations:
        if isinstance(item, dict):
            number = item.get("generation_number")
            if isinstance(number, int):
                unique_generations[number] = item
    observed_tiers = sorted(
        {
            item["observed_service_tier"]
            for item in unique_generations.values()
            if item.get("observed_service_tier") is not None
        }
    )

    def sum_if_reported(field: str) -> int | None:
        values = [item.get(field) for item in unique_generations.values()]
        if not values or any(not isinstance(value, int) for value in values):
            return None
        return sum(values)

    return {
        "paper_id": paper_id,
        "status": status,
        "elapsed_seconds": source.get("elapsed_seconds"),
        "generation_attempts": source.get("generation_attempts", len(unique_generations)),
        "repair_attempts": source.get("repair_attempts", max(0, len(unique_generations) - 1)),
        "response_ids": response_ids,
        "diagnostic_events": lifecycle_events,
        "terminal_statuses": [
            item.get("terminal_status") or item.get("status")
            for item in unique_generations.values()
        ],
        "observed_models": sorted(
            {
                item["observed_model"]
                for item in unique_generations.values()
                if item.get("observed_model") is not None
            }
        ),
        "observed_reasoning_efforts": sorted(
            {
                item["observed_reasoning_effort"]
                for item in unique_generations.values()
                if item.get("observed_reasoning_effort") is not None
            }
        ),
        "observed_service_tiers": observed_tiers,
        "poll_count": sum_if_reported("poll_count"),
        "poll_errors": sum_if_reported("poll_errors"),
        "input_tokens": sum_if_reported("input_tokens"),
        "output_tokens": sum_if_reported("output_tokens"),
        "reasoning_tokens": sum_if_reported("reasoning_tokens"),
        "failure_category": source.get("failure_category"),
        "error_class": source.get("error_class"),
        "generation_diagnostics": list(generations),
    }


def _load_run_artifact(root: Path, mode: str, slug: str) -> dict[str, Any] | None:
    path = root / mode / slug / "result.json"
    if not path.exists():
        return None
    return _read_json(path)


def build(
    candidate_root: Path,
    output_root: Path,
    baseline_root: Path = DEFAULT_CACHE_ROOT,
) -> dict[str, Any]:
    """Build deterministic comparisons and safe operational metrics."""

    frozen = _read_json(output_root / "frozen_inputs.json")
    manifest = _read_json(output_root / "frozen_set_manifest.json")
    baseline_run_path = baseline_root / "baseline_run.json"
    candidate_run_path = candidate_root / "candidate_run.json"
    if not baseline_run_path.exists():
        raise RuntimeError("Current-pipeline baseline replay is missing")
    baseline_run = _read_json(baseline_run_path)
    if baseline_run.get("status") != "complete":
        raise RuntimeError("Current-pipeline baseline replay is incomplete")
    candidate_run = _read_json(candidate_run_path) if candidate_run_path.exists() else None
    if candidate_run is None:
        raise RuntimeError("Candidate run record is missing")

    summary_papers: list[dict[str, Any]] = []
    telemetry_papers: list[dict[str, Any]] = []
    for paper in frozen["papers"]:
        slug = paper["slug"]
        paper_id = paper["paper_id"]
        baseline = _load_run_artifact(baseline_root, "baseline", slug)
        candidate = _load_run_artifact(candidate_root, "candidate", slug)
        attempt_path = candidate_root / "candidate" / slug / "attempt.json"
        attempt = _read_json(attempt_path) if attempt_path.exists() else None
        if baseline is None or baseline.get("status") != "success":
            raise RuntimeError(f"Current-pipeline baseline output is missing for {paper_id}")

        if candidate is not None and candidate.get("status") == "success":
            baseline_graph = baseline["graph"]
            candidate_graph = candidate["graph"]
            baseline_relations = baseline["relations"]
            candidate_relations = candidate["relations"]
            baseline_node_ids = [node["id"] for node in baseline_graph["nodes"]]
            candidate_node_ids = [node["id"] for node in candidate_graph["nodes"]]
            node_id_delta = _multiset_delta(
                [{"id": value} for value in baseline_node_ids],
                [{"id": value} for value in candidate_node_ids],
            )
            graph_delta = {
                "node_multiset": _multiset_delta(baseline_graph["nodes"], candidate_graph["nodes"]),
                "node_ids": {
                    "baseline_only": [item["id"] for item in node_id_delta["baseline_only"]],
                    "candidate_only": [item["id"] for item in node_id_delta["candidate_only"]],
                    "identities_preserved": not node_id_delta["baseline_only"]
                    and not node_id_delta["candidate_only"],
                },
                "edge_multiset": _multiset_delta(baseline_graph["edges"], candidate_graph["edges"]),
                "edge_identity_multiset": _multiset_delta(
                    [
                        {
                            "source": edge["source"],
                            "target": edge["target"],
                            "predicate": edge["predicate"],
                            "negated": edge["negated"],
                        }
                        for edge in baseline_graph["edges"]
                    ],
                    [
                        {
                            "source": edge["source"],
                            "target": edge["target"],
                            "predicate": edge["predicate"],
                            "negated": edge["negated"],
                        }
                        for edge in candidate_graph["edges"]
                    ],
                ),
                "archived_contract_10_graph": _compare_archived_graph(
                    output_root, paper, baseline_graph
                ),
            }
            baseline_overview = _graph_overview(baseline_graph, baseline_relations)
            candidate_overview = _graph_overview(candidate_graph, candidate_relations)
            graph_delta["counts"] = {
                "baseline": {
                    "nodes": baseline_overview["node_count"],
                    "connected_nodes": baseline_overview["connected_node_count"],
                    "unconnected_nodes": baseline_overview["unconnected_node_count"],
                    "edges": baseline_overview["edge_count"],
                    "evidence_records": baseline_overview["evidence_record_count"],
                },
                "candidate": {
                    "nodes": candidate_overview["node_count"],
                    "connected_nodes": candidate_overview["connected_node_count"],
                    "unconnected_nodes": candidate_overview["unconnected_node_count"],
                    "edges": candidate_overview["edge_count"],
                    "evidence_records": candidate_overview["evidence_record_count"],
                },
            }
            relation_delta = _relation_delta(baseline_relations, candidate_relations)
            _write_json(output_root / "graphs/baseline" / f"{slug}.json", baseline_graph)
            _write_json(output_root / "graphs/candidate" / f"{slug}.json", candidate_graph)
            semantic = {
                "paper_id": paper_id,
                "title": paper["title"],
                "source": paper["source"],
                "entities": paper["entities"],
                "baseline_relations": baseline_relations,
                "candidate_relations": candidate_relations,
                "relation_delta": relation_delta,
                "graphs": {
                    "baseline_path": f"reports/relation_migration_12a/graphs/baseline/{slug}.json",
                    "candidate_path": f"reports/relation_migration_12a/graphs/candidate/{slug}.json",
                    "baseline_overview": baseline_overview,
                    "candidate_overview": candidate_overview,
                    "delta": graph_delta,
                },
                "candidate_status": "success",
            }
            _write_json(output_root / "papers" / f"{slug}.json", semantic)
            summary_papers.append(
                {
                    "paper_id": paper_id,
                    "status": "compared",
                    "baseline_relations": len(baseline_relations),
                    "candidate_relations": len(candidate_relations),
                    "baseline_nodes": baseline_overview["node_count"],
                    "candidate_nodes": candidate_overview["node_count"],
                    "baseline_edges": baseline_overview["edge_count"],
                    "candidate_edges": candidate_overview["edge_count"],
                    "baseline_only_count": len(relation_delta["baseline_only"]),
                    "candidate_only_count": len(relation_delta["candidate_only"]),
                    "paired_rich_field_change_count": len(
                        relation_delta["matched_changed_records"]
                    ),
                    "exact_relations_match": relation_delta["exact_multiset_match"],
                    "node_ids_preserved": graph_delta["node_ids"]["identities_preserved"],
                    "edge_identities_match": not graph_delta["edge_identity_multiset"]["baseline_only"]
                    and not graph_delta["edge_identity_multiset"]["candidate_only"],
                    "exact_graph_edges_match": not graph_delta["edge_multiset"]["baseline_only"]
                    and not graph_delta["edge_multiset"]["candidate_only"],
                }
            )
        else:
            status = (
                candidate.get("status")
                if candidate is not None
                else (attempt or {}).get("status", "not_run")
            )
            semantic = {
                "paper_id": paper_id,
                "title": paper["title"],
                "source": paper["source"],
                "entities": paper["entities"],
                "baseline_relations": baseline["relations"],
                "candidate_relations": None,
                "candidate_status": status,
                "candidate_attempt": {
                    key: value
                    for key, value in (attempt or {}).items()
                    if key
                    in {
                        "attempt_id",
                        "status",
                        "started_at_utc",
                        "completed_at_utc",
                        "elapsed_seconds",
                        "last_response_id",
                        "diagnostic_events",
                        "final_generation_diagnostics",
                        "failure_category",
                        "last_diagnostic_status",
                        "error_class",
                    }
                },
                "relation_delta": {"status": "not_comparable_candidate_has_no_validated_result"},
                "graphs": {
                    "baseline_path": f"reports/relation_migration_12a/graphs/baseline/{slug}.json",
                    "candidate_path": None,
                    "baseline_overview": _graph_overview(baseline["graph"], baseline["relations"]),
                    "candidate_overview": None,
                },
            }
            _write_json(output_root / "graphs/baseline" / f"{slug}.json", baseline["graph"])
            _write_json(output_root / "papers" / f"{slug}.json", semantic)
            summary_papers.append(
                {
                    "paper_id": paper_id,
                    "status": status,
                    "baseline_only_count": None,
                    "candidate_only_count": None,
                    "paired_rich_field_change_count": None,
                    "node_ids_preserved": None,
                    "edge_identities_match": None,
                }
            )

        telemetry_papers.append(_safe_telemetry(paper_id, semantic["candidate_status"], candidate, attempt))

    telemetry = {
        "contract": "12A",
        "candidate_run_status": candidate_run.get("status"),
        "configuration": candidate_run.get("configuration", {}),
        "papers": telemetry_papers,
    }
    _write_json(output_root / "telemetry.json", telemetry)
    summary = {
        "contract": "12A",
        "status": candidate_run.get("status"),
        "frozen_set_manifest": "reports/relation_migration_12a/frozen_set_manifest.json",
        "frozen_input_path": "reports/relation_migration_12a/frozen_inputs.json",
        "frozen_provenance": {
            "baseline_commit": manifest["baseline_commit"],
            "contract_10_selection_commit": manifest["contract_10_selection_commit"],
            "frozen_inputs_sha256": manifest["frozen_inputs_file_sha256"],
            "system_prompt_sha256": manifest["historical_equivalence"]["system_prompt_sha256"],
            "semantic_schema_sha256": manifest["historical_equivalence"]["semantic_schema_sha256"],
        },
        "candidate_configuration": candidate_run.get("configuration", {}),
        "papers": summary_papers,
        "scientific_interpretation": "Deterministic output differences only; scientific quality assessment is reserved for human review.",
        "telemetry_path": "reports/relation_migration_12a/telemetry.json",
    }
    _write_json(output_root / "summary.json", summary)
    _write_summary_markdown(output_root, summary, telemetry)
    return summary


def _compare_archived_graph(
    output_root: Path, paper: dict[str, Any], current_graph: dict[str, Any]
) -> dict[str, Any]:
    path = ROOT / "reports/relation_contract_10/graphs" / f"{paper['slug']}.json"
    archived = _read_json(path)
    archived_without_roles = json.loads(json.dumps(archived))
    current_without_roles = json.loads(json.dumps(current_graph))
    archived_roles = {
        node["id"]: node.pop("paper_role")
        for node in archived_without_roles["nodes"]
        if "paper_role" in node
    }
    current_roles = {
        node["id"]: node.pop("paper_role")
        for node in current_without_roles["nodes"]
        if "paper_role" in node
    }
    same = archived == current_graph
    same_ignoring_roles = archived_without_roles == current_without_roles
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(path.read_bytes()),
        "same_as_current_pipeline_control": same,
        "same_entities_and_edges_ignoring_paper_roles": same_ignoring_roles,
        "archived_role_annotations_withheld_from_both_migration_paths": archived_roles,
        "current_control_role_annotations": current_roles,
        "archived_node_count": len(archived["nodes"]),
        "archived_edge_count": len(archived["edges"]),
        "archived_graph_delta": None
        if same_ignoring_roles
        else {
            "nodes": _multiset_delta(
                archived_without_roles["nodes"], current_without_roles["nodes"]
            ),
            "edges": _multiset_delta(
                archived_without_roles["edges"], current_without_roles["edges"]
            ),
        },
    }


def _write_summary_markdown(output_root: Path, summary: dict[str, Any], telemetry: dict[str, Any]) -> None:
    lines = [
        "# Contract 12A production-path regression",
        "",
        f"Run status: **{summary['status']}**",
        "",
        "The paper set, title-plus-abstract source, mention packets, baseline relations, prompt, and semantic schema were frozen before the candidate run. Both current-pipeline comparison paths omit paper roles. The archived Contract 10 graph references contain stored role annotations on some unconnected nodes; archive equivalence therefore reports entity/edge equality with roles ignored and lists those annotations separately. This packet reports deterministic differences only; it does not declare a scientific winner.",
        "",
        "## Semantic comparison",
        "",
        "| Paper | Status | Baseline relations | Candidate relations | Baseline nodes/edges | Candidate nodes/edges | Node IDs preserved | Edge identities match | Baseline-only records | Candidate-only records | Paired rich-field changes | Exact relation match |",
        "|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---|",
    ]
    paper_telemetry = {item["paper_id"]: item for item in telemetry["papers"]}
    for paper in summary["papers"]:
        if paper["status"] == "compared":
            lines.append(
                f"| {paper['paper_id']} | compared | {paper['baseline_relations']} | {paper['candidate_relations']} | "
                f"{paper['baseline_nodes']}/{paper['baseline_edges']} | {paper['candidate_nodes']}/{paper['candidate_edges']} | "
                f"{paper['node_ids_preserved']} | {paper['edge_identities_match']} | "
                f"{paper['baseline_only_count']} | {paper['candidate_only_count']} | "
                f"{paper['paired_rich_field_change_count']} | {paper['exact_relations_match']} |"
            )
        else:
            lines.append(f"| {paper['paper_id']} | {paper['status']} | — | — | — | — | — | — | — | — | — | — |")
    lines.extend(["", "Full source text, supplied entities, every baseline/candidate relation field, and graph deltas are in `papers/*.json`. Baseline and candidate graph JSON files are under `graphs/baseline/` and `graphs/candidate/`. Edge identity compares directed source, target, predicate, and negation independently of edge IDs and rich evidence. Baseline-only and candidate-only relation counts are exact-record multiset differences; paired rich-field changes identify changed records sharing the same directed endpoints and predicate, so that count can overlap the two exact-record counts.", "", "## Operational telemetry", "", "| Paper | Status | Seconds | Generations | Repairs | Polls | Input tokens | Output tokens | Reasoning tokens | Observed service tier | Response IDs |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"])
    for item in telemetry["papers"]:
        lines.append(
            f"| {item['paper_id']} | {item['status']} | {item['elapsed_seconds'] if item['elapsed_seconds'] is not None else '—'} | "
            f"{item['generation_attempts']} | {item['repair_attempts']} | {item['poll_count'] if item['poll_count'] is not None else '—'} | "
            f"{item['input_tokens'] if item['input_tokens'] is not None else '—'} | {item['output_tokens'] if item['output_tokens'] is not None else '—'} | "
            f"{item['reasoning_tokens'] if item['reasoning_tokens'] is not None else '—'} | "
            f"{', '.join(item['observed_service_tiers']) or '—'} | {', '.join(item['response_ids']) or '—'} |"
        )
    lines.extend(
        [
            "",
            "## Reviewer paths",
            "",
            "- `frozen_set_manifest.json` records selection, provenance hashes, and historical equivalence.",
            "- `frozen_inputs.json` contains the self-contained source text, entity packets, and saved baseline relations.",
            "- `papers/*.json` contains the complete per-paper semantic comparison.",
            "- `telemetry.json` contains operational data separately from scientific output.",
            "- `graphs/candidate/*.json` contains graph JSON for the existing viewer compatibility smoke.",
            "- `verification.json`, `compatibility_verification.json`, and `viewer_smoke.json` record the mechanical, preservation, and viewer checks.",
            "",
        ]
    )
    (output_root / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--baseline-root", type=Path, default=DEFAULT_CACHE_ROOT)
    args = parser.parse_args()
    summary = build(args.candidate_root, args.output_root, args.baseline_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
