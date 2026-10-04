"""Combine explicit source-review judgments with reproducible mechanical checks.

Evidence offsets and literal-field diagnostics are deterministic. Semantic
entailment and scientific equivalence remain recorded reviewer judgments.
"""
import json
import re
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parents[1]
sys.path.insert(0, str(ROOT / "reports/relation_prompt_refinement_12b/scripts"))
import experiment as e
e.REPORT = REPORT
e.START_SHA = "f92ce7e91b62ed069c4479f75a0820ae24d0848f"
FIELDS = ("intervention", "effects", "context")


def rich(relations):
    return {field: sum(bool(r.get(field)) for r in relations) for field in FIELDS}


def main():
    """Validate frozen outputs and publish three-way, matched-finding diagnostics."""
    manifest = e.verify_freeze()
    annotations = e.read(REPORT / "scientific_review.json")
    historic = e.read(ROOT / "reports/relation_prompt_refinement_12b/scientific_review.json")
    summaries, telemetry, checks, locality = [], [], [], []
    for row in manifest["cases"]:
        base = REPORT / row["directory"] / row["slug"]
        case = e.read(base / "input.json")
        packets = {mode:e.read(base / name) for mode,name in
                   [("control", "control.json"), ("12b", "failed_12b.json"), ("12br", "refined.json")]}
        relations = {mode:p.get("relations", p.get("control_relations")) for mode,p in packets.items()}
        final = packets["12br"]
        assert final["status"] == "success"
        annotation = annotations["cases"][row["slug"]]
        assert annotation["reviewed_indices"] == list(range(len(relations["12br"])))
        left = e.read(REPORT / "graphs/control" / f"{row['slug']}.json")
        right = e.read(REPORT / "graphs/refined" / f"{row['slug']}.json")
        assert e.replay(case, relations["12br"]) == right == final["graph"]
        assert left["nodes"] == right["nodes"]
        views = {mode:e.review._graph_overview(graph, relations[key])
                 for mode,graph,key in [("control",left,"control"),("refined",right,"12br")]}
        for v in views.values():
            assert v["rich_evidence_propagation"]["exact_match"]
            assert v["duplicate_edge_identity_count"] == v["duplicate_evidence_record_count"] == 0
        ids = {v["id"] for v in case["entities"]}
        for i,r in enumerate(relations["12br"]):
            assert r["source"] in ids and r["target"] in ids
            start = case["source_text"].find(r["evidence"])
            assert start >= 0
            violations = [v for v in annotation["evidence_locality_violations"] if v["index"] == i]
            values = {field:r.get(field) for field in ("assertion", *FIELDS)}
            literal = {field:[dict(value=value, literal_in_evidence=value.casefold() in r["evidence"].casefold())
                       for value in (items if isinstance(items,list) else [items]) if value]
                       for field,items in values.items()}
            locality.append(dict(slug=row["slug"],index=i,predicate=r["predicate"],
                evidence_start=start,evidence_end=start+len(r["evidence"]),evidence=r["evidence"],
                literal_diagnostics=literal,semantic_review="violation" if violations else "no_known_violation",
                semantic_review_basis=annotation["evidence_review_basis"],violations=violations))
        old_pairs = dict(historic["cases"][row["slug"]]["equivalent_relation_pairs"])
        triples = [[c,old_pairs[c],r] for c,r in annotation["control_to_refined_pairs"] if c in old_pairs]
        invalid_old = {i for flag in annotations["known_12b_failures"]
                       if flag["slug"] == row["slug"] for i in flag["indices"]}
        excluded = [t for t in triples if t[1] in invalid_old]
        triples = [t for t in triples if t[1] not in invalid_old]
        matched = {mode:rich([relations[mode][t[n]] for t in triples])
                   for n,mode in enumerate(("control","12b","12br"))}
        pairs = [dict(control_index=c,refined_index=r,control=relations["control"][c],
                      refined=relations["12br"][r]) for c,r in annotation["control_to_refined_pairs"]]
        e.write(base / "comparison.json", dict(scientific_review=annotation,relations=relations,
            equivalent_pairs=pairs,three_way_matched_indices=triples,matched_finding_richness=matched,
            excluded_three_way_indices=excluded,exclusion_reason="Known 12B grounding/locality violations are not credited as enrichment",
            all_relation_richness={mode:rich(rs) for mode,rs in relations.items()},graph_overviews=views,
            deterministic_delta=e.review._relation_delta(relations["control"],relations["12br"])))
        diagnostics = final["generation_diagnostics"]
        for d in diagnostics:
            assert (d["observed_model"],d["observed_reasoning_effort"],d["observed_service_tier"],d["observed_background"]) == ("gpt-6.1-sol","medium","default",True)
            assert d["terminal_status"] == "completed"
        telemetry.append(dict(slug=row["slug"],control=packets["control"]["control_telemetry"],
            failed_12b={k:v for k,v in packets["12b"].items() if k not in ("relations","graph")},
            refined={k:v for k,v in final.items() if k not in ("relations","graph")}))
        summaries.append(dict(slug=row["slug"],counts={mode:len(rs) for mode,rs in relations.items()},
            richness={mode:rich(rs) for mode,rs in relations.items()},matched_findings=len(triples),
            matched_finding_richness=matched,control_edges=len(left["edges"]),refined_edges=len(right["edges"])))
        checks.append(dict(slug=row["slug"],graph_replay_exact=True,rich_projection_exact=True,
            verbatim_contiguous_evidence=True,valid_endpoint_ids=True,nodes_identical=True,
            exact_duplicate_normalized_relations=e.review._relation_delta(relations["control"],relations["12br"])["candidate_exact_duplicate_record_count"]))
    python_log = REPORT / "validation/python_tests.log"
    viewer_log = REPORT / "validation/viewer_tests.log"
    # PowerShell redirects as UTF-16 on some hosts; inspect the actual encoding.
    def log_text(path):
        data = path.read_bytes()
        return data.decode("utf-16" if data.startswith((b'\xff\xfe',b'\xfe\xff')) else "utf-8-sig").replace("\r\n", "\n")
    py = log_text(python_log if python_log.exists() else ROOT / ".cache/contract12br_full_tests.log")
    js = log_text(viewer_log if viewer_log.exists() else ROOT / ".cache/contract12br_viewer_tests.log")
    assert re.search(r"Ran 170 tests",py) and py.rstrip().endswith("OK")
    assert "tests 13" in js and "pass 13" in js and "fail 0" in js
    python_log.parent.mkdir(exist_ok=True)
    python_log.write_text(py,encoding="utf-8",newline="\n")
    viewer_log.write_text(js,encoding="utf-8",newline="\n")
    viewer = e.read(REPORT / "viewer_smoke.json")
    assert viewer["status"] == "passed" and len(viewer["checks"]) == 10
    violations = [v for case in annotations["cases"].values() for v in case["evidence_locality_violations"]]
    e.write(REPORT / "evidence_locality_review.json", dict(mechanical_entailment_claim=False,
        review_basis=annotations["review_basis"],known_violations=violations,relations=locality))
    e.write(REPORT / "comparison.json",summaries)
    e.write(REPORT / "telemetry.json",telemetry)
    totals = {mode:{f:sum(r["richness"][mode][f] for r in summaries) for f in FIELDS} for mode in ("control","12b","12br")}
    matched = {mode:{f:sum(r["matched_finding_richness"][mode][f] for r in summaries) for f in FIELDS} for mode in totals}
    e.write(REPORT / "verification.json", dict(status="passed",mechanical_only=True,starting_sha=e.START_SHA,
        scientific_gate=annotations["gate"],production_defaults_unchanged=True,control_prompt_unchanged=True,
        replacement_amendment_only=True,five_inputs_unchanged=True,historical_artifacts_unchanged=True,
        prompt_adaptations=0,completed_scientific_reruns=0,paid_control_generations=0,
        successful_generations=sum(len(t["refined"]["generation_diagnostics"]) for t in telemetry),
        repairs=sum(t["refined"]["repair_attempts"] for t in telemetry),
        tests=[dict(command="python -m unittest discover -s tests -v",count=170,status="passed",log=python_log.relative_to(REPORT).as_posix(),sha256=e.sha(python_log.read_bytes()),lifecycle_cases_included=25),
               dict(command="node --test viewer/tests/adapter.test.mjs",count=13,status="passed",log=viewer_log.relative_to(REPORT).as_posix(),sha256=e.sha(viewer_log.read_bytes()))],
        case_checks=checks,viewer_checks=10,known_evidence_locality_violations=len(violations),
        all_relation_richness=totals,three_way_matched_richness=matched,
        three_way_matched_findings=sum(r["matched_findings"] for r in summaries)))
    print(json.dumps(dict(all_richness=totals,matched_richness=matched,cases=summaries),indent=2))


if __name__ == "__main__":
    main()
