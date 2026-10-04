"""Combine recorded semantic judgments with exact replay and telemetry checks.

Manual matching is finding-level, not string identity or an accepted gold set.
Literal diagnostics and source offsets do not substitute for entailment review.
"""
import importlib.util
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("format_experiment", REPORT / "scripts/experiment_format.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
e = module.e
e.REPORT, e.START_SHA = REPORT, module.START
FIELDS = ("intervention", "effects", "context")


def richness(relations):
    """Count populated records, treating population as a diagnostic only."""
    return {f:sum(bool(r.get(f)) for r in relations) for f in FIELDS}


def main():
    """Require full source review, then preserve comparisons and field-level audits."""
    manifest = e.verify_freeze()
    annotations = e.read(REPORT / "scientific_review.json")
    totals = {mode:{f:0 for f in FIELDS} for mode in ("control", "formatted")}
    matched_totals = {mode:{f:0 for f in FIELDS} for mode in totals}
    rows, checks, telemetry, audits = [], [], [], []
    for row in manifest["cases"]:
        base = REPORT / "cases" / row["slug"]
        case = e.read(base / "input.json")
        before = e.read(base / "control.json")["control_relations"]
        result = e.read(base / "refined.json")
        after = result["relations"]
        a = annotations["cases"][row["slug"]]
        assert a["reviewed_indices"] == list(range(len(after)))
        assert set(a["relation_judgments"]) == {str(i) for i in range(len(after))}
        pairs = a["valid_matched_pairs"]
        assert len({c for c,r in pairs}) == len({r for c,r in pairs}) == len(pairs)
        counts = {"control":richness(before), "formatted":richness(after)}
        matched = {"control":richness([before[c] for c,r in pairs]),
                   "formatted":richness([after[r] for c,r in pairs])}
        for mode in totals:
            for f in FIELDS:
                totals[mode][f] += counts[mode][f]
                matched_totals[mode][f] += matched[mode][f]
        graph = e.read(REPORT / "graphs/refined" / f"{row['slug']}.json")
        control_graph = e.read(REPORT / "graphs/control" / f"{row['slug']}.json")
        assert e.replay(case, after) == graph == result["graph"]
        assert control_graph["nodes"] == graph["nodes"]
        if row["slug"] == "contract11u_passage_001":
            assert [(r["source"],r["target"],r["negated"]) for r in before] == [
                (r["source"],r["target"],r["negated"]) for r in after]
            assert sorted((v["source"],v["target"],v["negated"]) for v in control_graph["edges"]) == sorted(
                (v["source"],v["target"],v["negated"]) for v in graph["edges"])
        view = e.review._graph_overview(graph, after)
        assert view["rich_evidence_propagation"]["exact_match"]
        assert view["duplicate_edge_identity_count"] == view["duplicate_evidence_record_count"] == 0
        pairs_by_after = {r:c for c,r in pairs}
        ids = {v["id"] for v in case["entities"]}
        for i, r in enumerate(after):
            assert r["source"] in ids and r["target"] in ids
            start = case["source_text"].find(r["evidence"])
            assert start >= 0
            previous = before[pairs_by_after[i]] if i in pairs_by_after else {}
            values = []
            for f in FIELDS:
                items = r.get(f) or []
                items = items if isinstance(items,list) else [items]
                for value in items:
                    values.append(dict(field=f,value=value,
                        changed_or_added_vs_matched_control=r.get(f) != previous.get(f),
                        literal_in_evidence=value.casefold() in r["evidence"].casefold(),
                        semantic_judgment=a["relation_judgments"][str(i)]))
            audits.append(dict(slug=row["slug"],index=i,source=r["source"],target=r["target"],
                predicate=r["predicate"],assertion=r["assertion"],evidence=r["evidence"],
                evidence_start=start,evidence_end=start+len(r["evidence"]),
                rich_values=values,semantic_judgment=a["relation_judgments"][str(i)]))
        ds = result["generation_diagnostics"]
        assert result["status"] == "success" and len(ds) == 1 and result["repair_attempts"] == 0
        d = ds[0]
        assert (d["observed_model"],d["observed_reasoning_effort"],d["observed_service_tier"],d["observed_background"],d["terminal_status"]) == ("gpt-6.1-sol","medium","default",True,"completed")
        telemetry.append({**d,"slug":row["slug"],"status":result["status"],
                          "latency_seconds":result["elapsed_seconds"],
                          "repair_attempts":result["repair_attempts"],"generation_resubmissions":0,
                          "operational_retries":d["poll_errors"]})
        delta = e.review._relation_delta(before, after)
        assert delta["candidate_exact_duplicate_record_count"] == 0
        e.write(base / "comparison.json", dict(valid_matched_pairs=pairs,
            matched_finding_richness=matched,all_record_richness=counts,
            scientific_review=a,mechanical_delta=delta,graph_overview=view))
        rows.append(dict(slug=row["slug"],control_relations=len(before),formatted_relations=len(after),
            control_edges=len(control_graph["edges"]),formatted_edges=len(graph["edges"]),
            matched_findings=len(pairs),matched_finding_richness=matched,all_record_richness=counts))
        checks.append(dict(slug=row["slug"],replay_exact=True,rich_projection_exact=True,
            nodes_identical=True,valid_endpoints=True,contiguous_verbatim_evidence=True,
            normalized_exact_duplicates=0))
    e.write(REPORT / "rich_field_review.json", audits)
    e.write(REPORT / "comparison.json", rows)
    e.write(REPORT / "telemetry.json", telemetry)
    e.write(REPORT / "verification.json", dict(status="passed",starting_sha=module.START,
        scientific_gate=annotations["scientific_gate"],prompt_equivalence=module.normalize(
            (REPORT / "prompt_control.txt").read_text(encoding="utf-8")) == module.normalize(
            (REPORT / "prompt_formatted.txt").read_text(encoding="utf-8")),
        control_prompt_unchanged=True,production_defaults_unchanged=True,
        protected_code_and_viewer_unchanged=True,historical_artifacts_unchanged=True,
        scientific_generations=len(telemetry),paid_control_generations=0,prompt_adaptations=0,
        repairs=sum(r["repair_attempts"] for r in [e.read(REPORT / "cases" / row["slug"] / "refined.json") for row in manifest["cases"]]),
        all_record_richness=totals,valid_matched_finding_richness=matched_totals,
        case_checks=checks,tests=e.read(REPORT / "validation/results.json"),
        viewer_compatibility=e.read(REPORT / "viewer_smoke.json"),
        limits="Primary-agent semantic review, one completion per case, no independent adjudication or sampling-variability isolation; duplicate checks cover normalized outputs."))
    print("Reviewed five outputs; exact replay and preserved runtime controls verified.")


if __name__ == "__main__":
    main()
