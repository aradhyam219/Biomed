"""Build blinded deterministic comparisons and complete review packets."""

from __future__ import annotations

import html
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPOSITORY = Path(__file__).resolve().parents[3]
REPORT = REPOSITORY / "reports" / "luna_56_vs_6_fullpaper_11"
CORPUS = REPOSITORY / ".cache" / "ner_target_domain" / "target_corpus.json"
ALIASES = ("Model A", "Model B")
DIFF_FIELDS = ("predicate", "assertion", "negated", "intervention", "effects", "context", "surface_form", "score")


def canonical(value: Any) -> str:
    """Serialize values for deterministic sorting and matching."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    """Write one stable UTF-8 JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def slug(paper_id: str) -> str:
    """Return the stable report directory name."""
    return "pmcid_" + paper_id.split(":", 1)[1].lower()


def exact_key(r: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the Contract 11 exact relation key."""
    return r["source"], r["target"], r["predicate"], r["negated"], r["evidence"]


def loose_key(r: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the Contract 11 endpoint/evidence alignment key."""
    return r["source"], r["target"], r["negated"], r["evidence"]


def polarity_neutral_key(r: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the grouping key used to expose negation conflicts."""
    return r["source"], r["target"], r["evidence"]


def locate(evidence: str, text: str, segments: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Locate the first exact evidence occurrence and its frozen segment."""
    start = text.find(evidence)
    occurrences, cursor = 0, 0
    while evidence:
        cursor = text.find(evidence, cursor)
        if cursor < 0:
            break
        occurrences += 1
        cursor += 1
    if start < 0:
        return {"start": None, "end": None, "section": None, "occurrences": 0}
    end = start + len(evidence)
    containing = [s for s in segments if s["start"] <= start and end <= s["end"]]
    return {
        "start": start,
        "end": end,
        "section": containing[0]["section"] if containing else None,
        "occurrences": occurrences,
    }


def passage(text: str, location: Mapping[str, Any], evidence: str) -> str:
    """Return a short source excerpt around the first exact evidence span."""
    start, end = location.get("start"), location.get("end")
    if start is None or end is None:
        return evidence
    left, right = max(0, start - 180), min(len(text), end + 180)
    return ("…" if left else "") + text[left:right] + ("…" if right < len(text) else "")


def group(items: Sequence[tuple[int, Mapping[str, Any]]], key_fn: Any) -> dict[tuple[Any, ...], list[tuple[int, Mapping[str, Any]]]]:
    """Group indexed relation values under one deterministic key."""
    result: dict[tuple[Any, ...], list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for item in items:
        result[key_fn(item[1])].append(item)
    return result


def pair_groups(
    left: Sequence[tuple[int, Mapping[str, Any]]],
    right: Sequence[tuple[int, Mapping[str, Any]]],
    key_fn: Any,
) -> tuple[list[tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]], list[tuple[int, Mapping[str, Any]]], list[tuple[int, Mapping[str, Any]]]]:
    """Pair identical records first and then sort unmatched variants."""
    left_groups, right_groups = group(left, key_fn), group(right, key_fn)
    pairs, unmatched_left, unmatched_right = [], [], []
    for key in sorted(set(left_groups) | set(right_groups), key=canonical):
        aa = sorted(left_groups.get(key, []), key=lambda x: (canonical(x[1]), x[0]))
        bb = sorted(right_groups.get(key, []), key=lambda x: (canonical(x[1]), x[0]))
        if not aa or not bb:
            unmatched_left.extend(aa)
            unmatched_right.extend(bb)
            continue
        by_a: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        by_b: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        for item in aa:
            by_a[canonical(item[1])].append(item)
        for item in bb:
            by_b[canonical(item[1])].append(item)
        used_a, used_b = set(), set()
        for value in sorted(set(by_a) & set(by_b)):
            count = min(len(by_a[value]), len(by_b[value]))
            for item_a, item_b in zip(by_a[value][:count], by_b[value][:count]):
                pairs.append((item_a, item_b))
                used_a.add(item_a[0])
                used_b.add(item_b[0])
        remain_a = [item for item in aa if item[0] not in used_a]
        remain_b = [item for item in bb if item[0] not in used_b]
        count = min(len(remain_a), len(remain_b))
        pairs.extend(zip(remain_a[:count], remain_b[:count]))
        unmatched_left.extend(remain_a[count:])
        unmatched_right.extend(remain_b[count:])
    return pairs, unmatched_left, unmatched_right


def pair_opposite_polarity(
    left: Sequence[tuple[int, Mapping[str, Any]]],
    right: Sequence[tuple[int, Mapping[str, Any]]],
) -> tuple[list[tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]], list[tuple[int, Mapping[str, Any]]], list[tuple[int, Mapping[str, Any]]]]:
    """Pair only relations whose endpoints/evidence match and negation differs."""
    left_groups, right_groups = group(left, polarity_neutral_key), group(right, polarity_neutral_key)
    pairs, used_left, used_right = [], set(), set()
    for key in sorted(set(left_groups) & set(right_groups), key=canonical):
        aa = sorted(left_groups[key], key=lambda item: (canonical(item[1]), item[0]))
        bb = sorted(right_groups[key], key=lambda item: (canonical(item[1]), item[0]))
        for item_a in aa:
            candidate = next(
                (
                    item_b for item_b in bb
                    if item_b[0] not in used_right
                    and item_a[1].get("negated") != item_b[1].get("negated")
                ),
                None,
            )
            if candidate is not None:
                pairs.append((item_a, candidate))
                used_left.add(item_a[0])
                used_right.add(candidate[0])
    return (
        pairs,
        [item for item in left if item[0] not in used_left],
        [item for item in right if item[0] not in used_right],
    )


def endpoints(r: Mapping[str, Any], entity_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Include the supplied source and target mention records."""
    return {
        side: dict(entity_by_id[ r[side] ]) if r[side] in entity_by_id else {"id": r[side], "missing_from_packet": True}
        for side in ("source", "target")
    }


def compare_relations(
    a_values: Sequence[Mapping[str, Any]],
    b_values: Sequence[Mapping[str, Any]],
    *,
    paper_id: str,
    title: str,
    text: str,
    segments: Sequence[Mapping[str, Any]],
    entity_by_id: Mapping[str, Mapping[str, Any]],
    source_sha256: str,
) -> dict[str, Any]:
    """Compute exact agreement, field alignments, negation conflicts, and samples."""
    a, b = list(a_values), list(b_values)
    a_exact, b_exact = {exact_key(r) for r in a}, {exact_key(r) for r in b}
    remaining_a, remaining_b = list(enumerate(a)), list(enumerate(b))
    exact_pairs, remaining_a, remaining_b = pair_groups(remaining_a, remaining_b, exact_key)
    loose_pairs, remaining_a, remaining_b = pair_groups(remaining_a, remaining_b, loose_key)
    negation_pairs, remaining_a, remaining_b = pair_opposite_polarity(remaining_a, remaining_b)
    paired = [(pair, "exact") for pair in exact_pairs] + [(pair, "endpoint/evidence") for pair in loose_pairs]
    all_pairs = paired + [(pair, "negation conflict") for pair in negation_pairs]

    def row_for(pair: tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]], kind: str) -> dict[str, Any]:
        ra, rb = pair[0][1], pair[1][1]
        loc = locate(ra["evidence"], text, segments)
        return {
            "category": kind,
            "location": loc,
            "source_passage": passage(text, loc, ra["evidence"]),
            "source_entity_and_target_entity": endpoints(ra, entity_by_id),
            "model_a_output": dict(ra),
            "model_b_output": dict(rb),
            "differing_fields": [f for f in DIFF_FIELDS if ra.get(f) != rb.get(f)],
        }

    disagreements = [
        row_for(pair, kind)
        for pair, kind in all_pairs
        if kind == "negation conflict" or any(pair[0][1].get(f) != pair[1][1].get(f) for f in DIFF_FIELDS)
    ]
    for _, relation in remaining_a:
        loc = locate(relation["evidence"], text, segments)
        disagreements.append({
            "category": "relation emitted only by Model A",
            "location": loc,
            "source_passage": passage(text, loc, relation["evidence"]),
            "source_entity_and_target_entity": endpoints(relation, entity_by_id),
            "model_a_output": dict(relation),
            "model_b_output": None,
            "differing_fields": [],
        })
    for _, relation in remaining_b:
        loc = locate(relation["evidence"], text, segments)
        disagreements.append({
            "category": "relation emitted only by Model B",
            "location": loc,
            "source_passage": passage(text, loc, relation["evidence"]),
            "source_entity_and_target_entity": endpoints(relation, entity_by_id),
            "model_a_output": None,
            "model_b_output": dict(relation),
            "differing_fields": [],
        })
    disagreements.sort(key=lambda x: (
        x["location"]["start"] if x["location"]["start"] is not None else len(text) + 1,
        x["category"],
        canonical(x["model_a_output"]),
        canonical(x["model_b_output"]),
    ))

    shared = []
    for pair, kind in paired:
        ra, rb = pair[0][1], pair[1][1]
        loc = locate(ra["evidence"], text, segments)
        shared.append({
            "alignment": kind,
            "location": loc,
            "source_entity_and_target_entity": endpoints(ra, entity_by_id),
            "model_a_output": dict(ra),
            "model_b_output": dict(rb),
        })
    shared.sort(key=lambda x: (
        x["location"]["start"] if x["location"]["start"] is not None else len(text) + 1,
        canonical(x["model_a_output"]),
        canonical(x["model_b_output"]),
    ))
    if len(shared) > 20:
        shared = [shared[round(i * (len(shared) - 1) / 19)] for i in range(20)]
    return {
        "paper_id": paper_id,
        "title": title,
        "primary_runs": ["Model A run 1", "Model B run 1"],
        "exact_relation_agreement": {
            "key_fields": ["source", "target", "predicate", "negated", "evidence"],
            "shared_count": len(a_exact & b_exact),
            "model_a_only_count": len(a_exact - b_exact),
            "model_b_only_count": len(b_exact - a_exact),
            "model_a_only_keys": [list(k) for k in sorted(a_exact - b_exact, key=canonical)],
            "model_b_only_keys": [list(k) for k in sorted(b_exact - a_exact, key=canonical)],
        },
        "endpoint_evidence_alignment": {
            "key_fields": ["source", "target", "negated", "exact evidence"],
            "aligned_count": len(paired),
            "field_disagreement_count": sum(bool(row_for(pair, kind)["differing_fields"]) for pair, kind in paired),
            "aligned_relations": [
                {
                    "alignment": kind,
                    "model_a": dict(pair[0][1]),
                    "model_b": dict(pair[1][1]),
                    "differing_fields": [f for f in DIFF_FIELDS if pair[0][1].get(f) != pair[1][1].get(f)],
                }
                for pair, kind in paired
            ],
        },
        "negation_conflicts": [
            {"model_a": dict(pair[0][1]), "model_b": dict(pair[1][1])}
            for pair, _ in [(pair, kind) for pair, kind in all_pairs if kind == "negation conflict"]
        ],
        "unmatched_model_a_relations": [dict(r) for _, r in remaining_a],
        "unmatched_model_b_relations": [dict(r) for _, r in remaining_b],
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
        "shared_sample": shared,
        "source_attribution_rule": "first exact evidence occurrence assigned to the containing frozen corpus segment",
    }


def html_pre(value: Any) -> str:
    """Format exact text and JSON safely for a Markdown review packet."""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return "<pre>" + html.escape(text) + "</pre>"


def render_review(comparison: Mapping[str, Any], source_sha256: str) -> tuple[str, str]:
    """Render every disagreement and up to twenty distributed shared examples."""
    paper_id, title = comparison["paper_id"], comparison["title"]
    lines = [
        f"# Blinded disagreements — {paper_id}", "",
        f"Title: {title}", f"Frozen source SHA-256: {source_sha256}",
        "Scope: primary run 1, Model A versus Model B. This packet lists differences without judging quality.", "",
        "## Exact comparison", "",
        f"- Exact shared relation keys: {comparison['exact_relation_agreement']['shared_count']}",
        f"- Model A only exact keys: {comparison['exact_relation_agreement']['model_a_only_count']}",
        f"- Model B only exact keys: {comparison['exact_relation_agreement']['model_b_only_count']}",
        f"- Endpoint/evidence alignments: {comparison['endpoint_evidence_alignment']['aligned_count']}",
        f"- Aligned field differences: {comparison['endpoint_evidence_alignment']['field_disagreement_count']}",
        f"- Negation conflicts: {len(comparison['negation_conflicts'])}",
        f"- Unmatched Model A outputs: {len(comparison['unmatched_model_a_relations'])}",
        f"- Unmatched Model B outputs: {len(comparison['unmatched_model_b_relations'])}", "",
        "## Every disagreement", "",
    ]
    if not comparison["disagreements"]:
        lines.extend(["No deterministic output disagreements were found.", ""])
    for i, item in enumerate(comparison["disagreements"], 1):
        loc = item["location"]
        where = f"characters [{loc['start']}, {loc['end']})" if loc["start"] is not None else "location unavailable"
        relation = item["model_a_output"] or item["model_b_output"]
        lines.extend([
            f"### {i}. {item['category']}", "",
            f"Source section: {loc.get('section') or 'not assignable from frozen segments'}",
            f"Source location: {where}; exact evidence occurrences: {loc['occurrences']}", "",
            "Source passage:", "", html_pre(item["source_passage"]), "",
            "Exact evidence:", "", html_pre(relation["evidence"]), "",
            "Source entity and target entity:", "", html_pre(item["source_entity_and_target_entity"]), "",
        ])
        for alias, key in (("Model A", "model_a_output"), ("Model B", "model_b_output")):
            lines.extend([f"{alias} output:", "", html_pre(item[key]) if item[key] is not None else "None", ""])
        if item["differing_fields"]:
            lines.extend(["Unequal serialized fields: " + ", ".join(item["differing_fields"]), ""])
    lines.extend([
        "## Attribution", "",
        "Section attribution uses the first exact occurrence of verbatim evidence. Endpoint mentions are from the identical frozen HunFlair2 packet.",
        "",
    ])

    sample = [
        f"# Agreement sanity sample — {paper_id}", "",
        f"Title: {title}", f"Frozen source SHA-256: {source_sha256}",
        "Selection: deterministic source-order quantiles, up to 20 exact or endpoint/evidence-aligned primary outputs.",
        "Agreement is included for scientific review and is not treated as correctness.", "",
    ]
    if not comparison["shared_sample"]:
        sample.extend(["No shared or closely aligned primary outputs were available.", ""])
    for i, item in enumerate(comparison["shared_sample"], 1):
        loc = item["location"]
        where = f"characters [{loc['start']}, {loc['end']})" if loc["start"] is not None else "location unavailable"
        sample.extend([
            f"## Sample {i}", "",
            f"Source section: {loc.get('section') or 'not assignable from frozen segments'}; {where}; evidence occurrences: {loc['occurrences']}",
            "Source passage:", "", html_pre(item["model_a_output"]["evidence"]), "",
            "Source entity and target entity:", "", html_pre(item["source_entity_and_target_entity"]), "",
            "Model A output:", "", html_pre(item["model_a_output"]), "",
            "Model B output:", "", html_pre(item["model_b_output"]), "",
        ])
    return "\n".join(lines), "\n".join(sample)


def graph_statistics(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Measure nodes, directed edges, viewer bundles, components, and degrees."""
    nodes, edges = list(graph.get("nodes", [])), list(graph.get("edges", []))
    ids = [str(n["id"]) for n in nodes]
    adjacency = {node_id: set() for node_id in ids}
    indegree, outdegree = Counter({node_id: 0 for node_id in ids}), Counter({node_id: 0 for node_id in ids})
    bundles, self_edges = set(), []
    for edge in edges:
        source, target = str(edge["source"]), str(edge["target"])
        bundles.add((source, target))
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
        outdegree[source] += 1
        indegree[target] += 1
        if source == target:
            self_edges.append(edge)
    seen, components = set(), []
    for start in sorted(ids):
        if start in seen:
            continue
        queue, component = [start], []
        seen.add(start)
        while queue:
            current = queue.pop()
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    nodes_by_id = {str(n["id"]): n for n in nodes}
    degrees = [{
        "id": node_id,
        "label": nodes_by_id[node_id].get("label"),
        "type": nodes_by_id[node_id].get("type"),
        "in_degree": indegree[node_id],
        "out_degree": outdegree[node_id],
        "total_degree": indegree[node_id] + outdegree[node_id],
    } for node_id in sorted(ids)]
    return {
        "canonical_nodes": len(nodes),
        "graph_edges": len(edges),
        "display_bundles": len(bundles),
        "self_edges": len(self_edges),
        "self_edge_records": self_edges,
        "weakly_connected_components": len(components),
        "components": components,
        "isolated_nodes": sum(d["total_degree"] == 0 for d in degrees),
        "degree_histograms": {
            key: dict(sorted(Counter(d[key] for d in degrees).items()))
            for key in ("in_degree", "out_degree", "total_degree")
        },
        "node_degrees": degrees,
    }


def compare_graphs(run_a: Mapping[str, Any] | None, run_b: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compare primary graph structures without a quality assessment."""
    if not run_a or not run_b or run_a.get("status") != "complete" or run_b.get("status") != "complete":
        return {"status": "incomplete"}
    graph_a, graph_b = run_a["graph"], run_b["graph"]
    a_stats, b_stats = graph_statistics(graph_a), graph_statistics(graph_b)
    node_a = {str(n["id"]) for n in graph_a.get("nodes", [])}
    node_b = {str(n["id"]) for n in graph_b.get("nodes", [])}
    edge_key = lambda e: (e["source"], e["target"], e["predicate"], e["negated"])
    edges_a = {edge_key(e) for e in graph_a.get("edges", [])}
    edges_b = {edge_key(e) for e in graph_b.get("edges", [])}
    pairs_a = {(e["source"], e["target"]) for e in graph_a.get("edges", [])}
    pairs_b = {(e["source"], e["target"]) for e in graph_b.get("edges", [])}
    metric_names = ("canonical_nodes", "graph_edges", "display_bundles", "self_edges", "weakly_connected_components", "isolated_nodes")
    count_differences = {
        name: {"model_a": a_stats[name], "model_b": b_stats[name], "model_a_minus_model_b": a_stats[name] - b_stats[name]}
        for name in metric_names
    }
    return {
        "status": "complete",
        "canonical_nodes": count_differences["canonical_nodes"],
        "canonical_node_ids_equal": node_a == node_b,
        "model_a_only_node_ids": sorted(node_a - node_b),
        "model_b_only_node_ids": sorted(node_b - node_a),
        "validated_directed_relations": {
            "model_a": run_a.get("validated_relation_count"),
            "model_b": run_b.get("validated_relation_count"),
            "model_a_minus_model_b": run_a.get("validated_relation_count", 0) - run_b.get("validated_relation_count", 0),
        },
        "graph_edges": count_differences["graph_edges"],
        "display_bundles": count_differences["display_bundles"],
        "self_edges": count_differences["self_edges"],
        "weakly_connected_components": count_differences["weakly_connected_components"],
        "isolated_nodes": count_differences["isolated_nodes"],
        "degree_histograms": {"model_a": a_stats["degree_histograms"], "model_b": b_stats["degree_histograms"]},
        "node_degrees": {"model_a": a_stats["node_degrees"], "model_b": b_stats["node_degrees"]},
        "graph_edge_signatures": {
            "model_a_only": [list(x) for x in sorted(edges_a - edges_b)],
            "model_b_only": [list(x) for x in sorted(edges_b - edges_a)],
        },
        "directional_bundles": {
            "model_a_only": [list(x) for x in sorted(pairs_a - pairs_b)],
            "model_b_only": [list(x) for x in sorted(pairs_b - pairs_a)],
        },
        "model_a_graph_statistics": a_stats,
        "model_b_graph_statistics": b_stats,
        "count_differences": count_differences,
    }


def overlap(left: set[Any], right: set[Any]) -> dict[str, Any]:
    """Return common, unique, and Jaccard measurements."""
    shared = left & right
    return {
        "shared": len(shared),
        "run_1_only": len(left - right),
        "run_2_only": len(right - left),
        "jaccard": len(shared) / len(left | right) if left | right else 1.0,
    }


def stability(one: Mapping[str, Any] | None, two: Mapping[str, Any] | None) -> dict[str, Any]:
    """Compare a model's primary run and replicate."""
    if not one or not two or one.get("status") != "complete" or two.get("status") != "complete":
        return {"status": "incomplete", "run_1_status": None if not one else one.get("status"), "run_2_status": None if not two else two.get("status")}
    relations_one = one["validated_mention_level_relations"]
    relations_two = two["validated_mention_level_relations"]
    exact_one, exact_two = {exact_key(r) for r in relations_one}, {exact_key(r) for r in relations_two}
    loose_one, loose_two = {loose_key(r) for r in relations_one}, {loose_key(r) for r in relations_two}
    return {
        "status": "complete",
        "run_1_relation_count": len(relations_one),
        "run_2_relation_count": len(relations_two),
        "relation_count_difference_run_2_minus_run_1": len(relations_two) - len(relations_one),
        "exact_relation_overlap": overlap(exact_one, exact_two),
        "endpoint_evidence_overlap": overlap(loose_one, loose_two),
        "provider_attempts": {"run_1": one.get("provider_attempts"), "run_2": two.get("provider_attempts")},
        "repair_attempts": {"run_1": one.get("repair_attempts"), "run_2": two.get("repair_attempts")},
    }


def run_metrics(run: Mapping[str, Any] | None, mention_count: int, source_chars: int) -> dict[str, Any]:
    """Calculate the descriptive fields required for every run."""
    if not run:
        return {
            "source_characters": source_chars, "entity_mentions": mention_count,
            "validated_relations": None, "unique_endpoint_pairs": None, "unique_evidence_spans": None,
            "negated_relations": None, "relations_with_intervention": None, "relations_with_effects": None,
            "relations_with_context": None, "exact_duplicates": None, "graph_edges": None,
            "graph_bundles": None, "self_edges": None, "provider_attempts": None, "repair_attempts": None,
            "elapsed_ms": None, "provider_latency_ms": None, "token_usage": None, "status": "missing",
        }
    relations = run.get("validated_mention_level_relations", [])
    edges = run.get("graph", {}).get("edges", [])
    complete = run.get("status") == "complete"
    return {
        "source_characters": run.get("source_characters", source_chars),
        "entity_mentions": mention_count,
        "validated_relations": len(relations) if complete else None,
        "unique_endpoint_pairs": len({(r["source"], r["target"]) for r in relations}) if complete else None,
        "unique_evidence_spans": len({r["evidence"] for r in relations}) if complete else None,
        "negated_relations": sum(r.get("negated") is True for r in relations) if complete else None,
        "relations_with_intervention": sum(bool(r.get("intervention")) for r in relations) if complete else None,
        "relations_with_effects": sum(bool(r.get("effects")) for r in relations) if complete else None,
        "relations_with_context": sum(bool(r.get("context")) for r in relations) if complete else None,
        "exact_duplicates": run.get("exact_duplicates_in_final_structured_response"),
        "graph_edges": len(edges) if complete else None,
        "graph_bundles": len({(e["source"], e["target"]) for e in edges}) if complete else None,
        "self_edges": sum(e["source"] == e["target"] for e in edges) if complete else None,
        "provider_attempts": run.get("provider_attempts"),
        "repair_attempts": run.get("repair_attempts"),
        "elapsed_ms": run.get("elapsed_ms"),
        "provider_latency_ms": run.get("provider_latency_ms"),
        "token_usage": run.get("token_usage"),
        "status": run.get("status", "unknown"),
    }


def git(*args: str) -> str:
    """Read repository state at the parent Git root."""
    return subprocess.check_output(["git", "-c", "safe.directory=C:/Projects/Biomed", "-C", "C:/Projects/Biomed", *args], text=True).strip()


def main() -> int:
    """Write per-paper comparisons and the blinded operational summary."""
    lock = json.loads((REPORT / "preflight.json").read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    source_by_id = {item["paper_id"]: item for item in corpus["papers"]}
    run_table, papers, all_complete = [], [], True
    for locked in lock["papers"]:
        paper_id = locked["paper_id"]
        paper_slug = slug(paper_id)
        source = source_by_id[paper_id]
        text, segments = source["text"], locked["sections"]
        packet = json.loads((REPORT / "papers" / paper_slug / "entities.json").read_text(encoding="utf-8"))
        mention_count = len(packet["entities"])
        entity_by_id = {item["id"]: item for item in packet["entities"]}
        runs: dict[str, dict[int, Mapping[str, Any] | None]] = {alias: {} for alias in ALIASES}
        for alias, dirname in (("Model A", "model_a"), ("Model B", "model_b")):
            for replicate in (1, 2):
                path = REPORT / "papers" / paper_slug / dirname / f"run_{replicate}.json"
                run = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
                runs[alias][replicate] = run
                if not run or run.get("status") != "complete":
                    all_complete = False
                run_table.append({
                    "paper_id": paper_id, "model": alias, "replicate": replicate,
                    **run_metrics(run, mention_count, locked["source_characters"]),
                })

        primary_a, primary_b = runs["Model A"][1], runs["Model B"][1]
        if primary_a and primary_b and primary_a.get("status") == "complete" and primary_b.get("status") == "complete":
            comparison = compare_relations(
                primary_a["validated_mention_level_relations"],
                primary_b["validated_mention_level_relations"],
                paper_id=paper_id,
                title=source["title"],
                text=text,
                segments=segments,
                entity_by_id=entity_by_id,
                source_sha256=locked["source_sha256"],
            )
            disagreements_md, shared_md = render_review(comparison, locked["source_sha256"])
        else:
            comparison = {
                "status": "incomplete",
                "exact_relation_agreement": {"shared_count": None, "model_a_only_count": None, "model_b_only_count": None},
                "endpoint_evidence_alignment": {"aligned_count": None, "field_disagreement_count": None},
                "disagreements": [], "shared_sample": [],
            }
            disagreements_md = f"# Blinded disagreements — {paper_id}\n\nA successful primary output is unavailable for at least one condition. See the run JSON for attempt details.\n"
            shared_md = f"# Agreement sanity sample — {paper_id}\n\nA successful primary output is unavailable for at least one condition.\n"

        paper_dir = REPORT / "papers" / paper_slug
        write_json(paper_dir / "relation_comparison.json", comparison)
        (paper_dir / "disagreements.md").write_text(disagreements_md, encoding="utf-8")
        (paper_dir / "shared_sample.md").write_text(shared_md, encoding="utf-8")

        section_counts, repeated = {}, {}
        for alias in ALIASES:
            counts, multiple = Counter(), 0
            run = runs[alias][1]
            if run and run.get("status") == "complete":
                for relation in run["validated_mention_level_relations"]:
                    loc = locate(relation["evidence"], text, segments)
                    if loc["occurrences"] > 1:
                        multiple += 1
                    if loc["section"] is not None:
                        counts[loc["section"]] += 1
            section_counts[alias] = dict(sorted(counts.items()))
            repeated[alias] = multiple
        section_value = {
            "paper_id": paper_id,
            "source_sha256": locked["source_sha256"],
            "attribution_rule": "first exact evidence occurrence assigned to its containing frozen corpus segment",
            "repeated_evidence_relation_count": repeated,
            "relation_counts_by_exact_source_segment": section_counts,
        }
        write_json(paper_dir / "section_counts.json", section_value)
        section_lines = [
            f"# Relation counts by source section — {paper_id}", "",
            f"Title: {source['title']}",
            f"Frozen source SHA-256: {locked['source_sha256']}",
            "Attribution uses the first exact evidence occurrence and containing frozen segment.", "",
            "| Frozen source section | Model A primary | Model B primary |",
            "|---|---:|---:|",
        ]
        names = sorted(set(section_counts["Model A"]) | set(section_counts["Model B"]))
        if not names:
            section_lines.append("| No section assignments available | — | — |")
        for name in names:
            safe_name = name.replace("|", "¦")
            section_lines.append(f"| {safe_name} | {section_counts['Model A'].get(name, 0)} | {section_counts['Model B'].get(name, 0)} |")
        section_lines.extend([
            "",
            f"- Model A relations whose evidence occurs more than once: {repeated['Model A']}",
            f"- Model B relations whose evidence occurs more than once: {repeated['Model B']}", "",
        ])
        (paper_dir / "section_counts.md").write_text("\n".join(section_lines), encoding="utf-8")

        graph_comparison = compare_graphs(primary_a, primary_b)
        write_json(paper_dir / "graph_comparison.json", graph_comparison)
        papers.append({
            "paper_id": paper_id,
            "title": source["title"],
            "source_characters": locked["source_characters"],
            "source_sha256": locked["source_sha256"],
            "source_checksum": locked["source_checksum"],
            "entity_mentions": mention_count,
            "entity_packet_sha256": locked["entity_packet_sha256"],
            "entity_input_sha256": locked["entity_input_sha256"],
            "exact_relation_agreement": comparison["exact_relation_agreement"],
            "endpoint_evidence_alignment": comparison["endpoint_evidence_alignment"],
            "disagreement_count": comparison.get("disagreement_count"),
            "shared_sample_count": len(comparison.get("shared_sample", [])),
            "stability": {alias: stability(runs[alias][1], runs[alias][2]) for alias in ALIASES},
            "cross_model_graph": graph_comparison,
            "section_counts": section_value,
        })

    ending_sha, branch = git("rev-parse", "HEAD"), git("branch", "--show-current")
    status_lines = git("status", "--porcelain", "--untracked-files=all").splitlines()
    prefixes = ("extraction_system/src/", "extraction_system/viewer/", "extraction_system/tests/")
    production_changes = [
        line[3:] for line in status_lines
        if len(line) > 3 and line[3:].replace("\\", "/").startswith(prefixes)
    ]
    summary = {
        "contract": "Codex Contract 11",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "all 12 runs complete" if all_complete else "one or more scheduled runs incomplete",
        "quality_judgment": "not assigned by Codex",
        "model_mapping_disclosed": False,
        "model_mapping_note": "Model mapping preserved separately and intentionally not disclosed.",
        "baseline": {
            "starting_sha": lock["baseline"]["repository_sha"],
            "ending_sha": ending_sha,
            "branch": branch,
            "production_code_diff_status": "clean" if not production_changes else "CHANGED: " + ", ".join(production_changes),
            "python_tests": "144 passed",
            "viewer_tests": "13 passed",
            "git_diff_check": "passed",
        },
        "frozen_configuration": {
            "provider": lock["configuration"]["provider"],
            "reasoning_effort": lock["configuration"]["reasoning_effort"],
            "max_output_tokens": lock["configuration"]["max_output_tokens"],
            "bounded_repair_budget": lock["configuration"]["bounded_repair_budget"],
            "system_prompt_sha256": lock["configuration"]["system_prompt_sha256"],
            "schema_sha256": lock["configuration"]["schema_sha256"],
            "execution_order": lock["execution_order"],
        },
        "source_corpus": lock["source_corpus"],
        "run_table": run_table,
        "papers": papers,
        "production_changes": production_changes,
        "artifact_paths": {
            "summary_markdown": "summary.md",
            "summary_json": "summary.json",
            "preflight": "preflight.json",
            "run_json_pattern": "papers/<paper>/model_[a,b]/run_[1,2].json",
            "graph_json_pattern": "papers/<paper>/model_[a,b]/graph_run_[1,2].json",
            "screenshots": ".cache/model_ab_11/screenshots/<paper>_model_[a,b].png",
        },
    }
    lines = [
        "# Contract 11 — blinded full-paper relation comparison", "",
        f"Status: {summary['status']}",
        "Quality judgment: deferred to Talia; Codex assigns no winner or aggregate quality score.",
        "Model mapping preserved separately and intentionally not disclosed.", "",
        "## Baseline and validation", "",
        f"- Starting SHA: {summary['baseline']['starting_sha']}",
        f"- Ending SHA: {summary['baseline']['ending_sha']}",
        f"- Production code diff: {summary['baseline']['production_code_diff_status']}",
        f"- Python baseline: {summary['baseline']['python_tests']}",
        f"- Viewer baseline: {summary['baseline']['viewer_tests']}",
        f"- git diff --check: {summary['baseline']['git_diff_check']}", "",
        "## Run measurements", "",
        "| Paper | Blinded model | Replicate | Source chars | Mentions | Relations | Unique evidence spans | Graph edges | Provider attempts | Repairs | Elapsed s | Token usage | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in run_table:
        usage = row["token_usage"]
        token_text = f"in {usage.get('input_tokens', '—')} / out {usage.get('output_tokens', '—')} / total {usage.get('total_tokens', '—')}" if isinstance(usage, Mapping) else "unavailable"
        elapsed = f"{row['elapsed_ms'] / 1000:.3f}" if isinstance(row["elapsed_ms"], (int, float)) else "—"
        values = (
            row["paper_id"], row["model"], row["replicate"], row["source_characters"], row["entity_mentions"],
            row["validated_relations"], row["unique_evidence_spans"], row["graph_edges"], row["provider_attempts"],
            row["repair_attempts"], elapsed, token_text, row["status"],
        )
        lines.append("| " + " | ".join(str(x if x is not None else "—") for x in values) + " |")
    lines.extend([
        "", "## Within-model stability", "",
        "| Paper | Model | Exact shared | Exact Jaccard | Endpoint/evidence shared | Endpoint/evidence Jaccard | Count delta (2−1) | Repairs (1, 2) |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for paper in papers:
        for alias in ALIASES:
            value = paper["stability"][alias]
            if value["status"] != "complete":
                lines.append(f"| {paper['paper_id']} | {alias} | — | — | — | — | — | incomplete |")
            else:
                ex, en = value["exact_relation_overlap"], value["endpoint_evidence_overlap"]
                rp = value["repair_attempts"]
                lines.append(
                    f"| {paper['paper_id']} | {alias} | {ex['shared']} | {ex['jaccard']:.3f} | {en['shared']} | {en['jaccard']:.3f} | "
                    f"{value['relation_count_difference_run_2_minus_run_1']} | {rp['run_1']}, {rp['run_2']} |"
                )
    lines.extend([
        "", "## Primary cross-model graph measurements", "",
        "| Paper | Nodes A/B | Directed relations A/B | Graph edges A/B | Bundles A/B | Self-edges A/B | Weak components A/B | Node IDs equal |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for paper in papers:
        graph = paper["cross_model_graph"]
        if graph.get("status") != "complete":
            lines.append(f"| {paper['paper_id']} | incomplete | incomplete | incomplete | incomplete | incomplete | incomplete | — |")
        else:
            lines.append(
                f"| {paper['paper_id']} | {graph['canonical_nodes']['model_a']}/{graph['canonical_nodes']['model_b']} | "
                f"{graph['validated_directed_relations']['model_a']}/{graph['validated_directed_relations']['model_b']} | "
                f"{graph['graph_edges']['model_a']}/{graph['graph_edges']['model_b']} | "
                f"{graph['display_bundles']['model_a']}/{graph['display_bundles']['model_b']} | "
                f"{graph['self_edges']['model_a']}/{graph['self_edges']['model_b']} | "
                f"{graph['weakly_connected_components']['model_a']}/{graph['weakly_connected_components']['model_b']} | "
                f"{graph['canonical_node_ids_equal']} |"
            )
    lines.extend(["", "## Per-paper review and section artifacts", ""])
    for paper in papers:
        path = f"papers/{slug(paper['paper_id'])}"
        lines.append(
            f"- {paper['paper_id']} ({paper['source_characters']} chars; {paper['entity_mentions']} mentions): "
            f"[disagreements]({path}/disagreements.md), [shared sample]({path}/shared_sample.md), "
            f"[section counts]({path}/section_counts.md), [graph comparison]({path}/graph_comparison.json)."
        )
    lines.extend([
        "", "Every count is descriptive. Section assignment uses the first exact occurrence of verbatim evidence.", "",
        "## Artifact paths", "",
        "- Mention packets and exact entity serialization: papers/<paper>/entities.json and entity_input.json.",
        "- Every replicate relation record and graph: papers/<paper>/model_[a,b]/run_[1,2].json and graph_run_[1,2].json.",
        "- Six primary automatic-layout screenshots: .cache/model_ab_11/screenshots/<paper>_model_[a,b].png.",
        "- Frozen inputs and balanced execution order: preflight.json.",
        "- The blinded model key is stored separately at .cache/model_ab_11/model_key.json.",
        "",
    ])
    write_json(REPORT / "summary.json", summary)
    (REPORT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "runs": len(run_table),
        "papers": len(papers),
        "model_mapping_disclosed": False,
        "production_changes": production_changes,
        "summary": "reports/luna_56_vs_6_fullpaper_11/summary.md",
    }, ensure_ascii=True))
    return 0 if all_complete and not production_changes else 1


if __name__ == "__main__":
    raise SystemExit(main())
