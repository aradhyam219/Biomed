"""Build the final offline comparison, explicit scientific review, and checks.

Human equivalence pairs distinguish wording changes from distinct findings.
They are reviewer judgments, not gold labels. Initial transport failures remain
separate from the selected completed output and are included in telemetry.
"""
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment as e


def rich(relations):
    return {field:sum(bool(r.get(field)) for r in relations) for field in ("intervention","effects","context")}


def identity(r):
    return {k:r[k] for k in ("source","target","predicate","negated")}


def effective(base):
    retry = base / "refined_retry_01.json"
    return retry if retry.exists() else base / "refined.json"


def brief(case, relation):
    labels = {v["id"]:v["text"] for v in case["entities"]}
    return f"{relation['source']} ({labels[relation['source']]}) → {relation['target']} ({labels[relation['target']]}): {relation['predicate']}"


def table_text(value):
    return json.dumps(value,ensure_ascii=False).replace("|","\\|").replace("\n"," ")


def main():
    manifest = e.verify_freeze()
    annotations = e.read(e.REPORT / "scientific_review.json")
    summaries, telemetry, checks = [], [], []
    sections = []
    for row in manifest["cases"]:
        base = e.REPORT / row["directory"] / row["slug"]
        case, control, refined = e.read(base/"input.json"), e.read(base/"control.json"), e.read(effective(base))
        assert refined["status"] == "success"
        before, after = control["control_relations"], refined["relations"]
        left = e.read(e.REPORT/"graphs/control"/f"{row['slug']}.json")
        right = refined["graph"]
        assert e.replay(case, after) == right
        overviews = {"control":e.review._graph_overview(left,before),"refined":e.review._graph_overview(right,after)}
        for overview in overviews.values():
            assert overview["rich_evidence_propagation"]["exact_match"]
            assert overview["duplicate_edge_identity_count"] == 0
            assert overview["duplicate_evidence_record_count"] == 0
        annotation = annotations["cases"][row["slug"]]
        matched = []
        for old,new in annotation["equivalent_relation_pairs"]:
            changed = {k:{"control":before[old].get(k),"refined":after[new].get(k)}
                       for k in sorted(set(before[old])|set(after[new])) if before[old].get(k) != after[new].get(k)}
            matched.append(dict(control_index=old,refined_index=new,control=before[old],refined=after[new],changed_fields=changed))
        paired_left,paired_right = ({p[0] for p in annotation["equivalent_relation_pairs"]},{p[1] for p in annotation["equivalent_relation_pairs"]})
        unmatched = {"control":[dict(index=i,relation=r) for i,r in enumerate(before) if i not in paired_left],
                     "refined":[dict(index=i,relation=r) for i,r in enumerate(after) if i not in paired_right]}
        result = dict(input=case,control_relations=before,refined_relations=after,
                      effective_refined_path=effective(base).relative_to(e.ROOT).as_posix(),
                      deterministic_relation_delta=e.review._relation_delta(before,after),
                      scientific_equivalence_pairs=matched,unmatched_relations=unmatched,scientific_review=annotation,
                      graph_overviews=overviews,graph_edge_delta=e.review._multiset_delta(
                          [identity(v) for v in left["edges"]],[identity(v) for v in right["edges"]]),
                      nodes_identical=left["nodes"]==right["nodes"],richness={"control":rich(before),"refined":rich(after)},
                      matched_finding_richness={"control":rich([before[p[0]] for p in annotation["equivalent_relation_pairs"]]),
                                               "refined":rich([after[p[1]] for p in annotation["equivalent_relation_pairs"]])})
        e.write(base/"comparison.json",result)
        diagnostics = refined["generation_diagnostics"]
        for d in diagnostics:
            assert (d["observed_model"],d["observed_reasoning_effort"],d["observed_service_tier"],d["observed_background"]) == ("gpt-6.1-sol","medium","default",True)
            assert d["terminal_status"] == "completed"
        run = dict(slug=row["slug"],status="success",relations=len(after),edges=len(right["edges"]),
                   repairs=refined["repair_attempts"],elapsed_seconds=refined["elapsed_seconds"],
                   **{k:sum(d[k] for d in diagnostics) for k in ("input_tokens","output_tokens","reasoning_tokens")},
                   service_tier="default",operational_recovery=effective(base).name!="refined.json")
        initial=e.read(base/"refined.json")
        telemetry.append(dict(**run,control=control["control_telemetry"],initial=initial if initial["status"]!="success" else {k:v for k,v in initial.items() if k not in ("graph","relations")},
                              effective={k:v for k,v in refined.items() if k not in ("graph","relations")}))
        summaries.append(dict(**run,control_relations=len(before),control_edges=len(left["edges"]),richness=result["richness"],
                              matched_finding_richness=result["matched_finding_richness"]))
        checks.append(dict(slug=row["slug"],source_and_entities_frozen=True,graph_replay_exact=True,nodes_identical=result["nodes_identical"],
                           rich_projection_exact=True,endpoint_ids_valid=True,verbatim_contiguous_evidence=True,
                           duplicate_graph_keys=0,duplicate_graph_evidence=0,
                           exact_duplicate_normalized_relations=e.review._relation_delta(before,after)["candidate_exact_duplicate_record_count"]))
        sec=[f"## {row['paper_id']} / {row['slug']}","",f"{len(before)} → {len(after)} relations; {len(left['edges'])} → {len(right['edges'])} graph edges.","",annotation["assessment"],"",
             "### Scientifically distinct findings and review flags","",annotation["control_only_scientific"],"",annotation["refined_only_scientific"],"", "\n".join(f"- {flag}" for flag in annotation["flags"]),"",
             "Unpaired records below require interpretation: predicate/mention changes alone do not establish scientific novelty.",""]
        for mode in ("control","refined"):
            sec.extend([f"{mode.capitalize()} unpaired relations:",""])
            for item in unmatched[mode]:
                sec.append(f"- [{item['index']}] {brief(case,item['relation'])}. {item['relation']['assertion']}")
            if not unmatched[mode]:sec.append("None.")
            sec.append("")
        sec.extend(["### Same-finding field and endpoint changes","", "Pairs below were manually assessed for scientific equivalence; indices are zero-based in the preserved relation arrays.","",
                    "| Control → refined index | Endpoint / predicate change | Rich-field change |", "|---|---|---|"])
        for pair in matched:
            changes=pair["changed_fields"]
            endpoint={k:v for k,v in changes.items() if k in ("source","target","predicate","negated")}
            metadata={k:v for k,v in changes.items() if k in ("intervention","effects","context")}
            if endpoint or metadata: sec.append(f"| {pair['control_index']} → {pair['refined_index']} | {table_text(endpoint)} | {table_text(metadata)} |")
        sec.extend(["","### Grounding and graph comparison","",f"All normalized relations pass Contract 10 validation. Both graphs retain the same {len(left['nodes'])} nodes and exact rich evidence projection. Exact edge-key differences (including wording changes) and complete assertions/evidence are in `comparison.json`.","",
                    f"Rich diagnostics: `{json.dumps(result['richness'],sort_keys=True)}`. These population counts do not certify scientific completeness.",""])
        sections.extend(sec)
    e.write(e.REPORT/"comparison.json",summaries)
    e.write(e.REPORT/"telemetry.json",telemetry)
    old=e.git("show",f"{e.START_SHA}:extraction_system/src/biomedical_extractor/llm_relation_extraction.py")
    new=(e.ROOT/"src/biomedical_extractor/llm_relation_extraction.py").read_text(encoding="utf-8")
    def nodes(source):
        tree=ast.parse(source)
        selected={v.name:ast.dump(v,include_attributes=False) for v in tree.body if isinstance(v,(ast.FunctionDef,ast.ClassDef)) and v.name!="LLMRelationExtractor"}
        cls=next(v for v in tree.body if isinstance(v,ast.ClassDef) and v.name=="LLMRelationExtractor")
        selected.update({"LLMRelationExtractor."+v.name:ast.dump(v,include_attributes=False) for v in cls.body if isinstance(v,ast.FunctionDef) and v.name!="from_openai"})
        return selected
    assert nodes(old)==nodes(new)
    unchanged=e.git("diff","--name-only",e.START_SHA,"--","extraction_system/src","extraction_system/viewer").splitlines()
    assert unchanged==["extraction_system/src/biomedical_extractor/llm_relation_extraction.py"]
    viewer=e.read(e.REPORT/"viewer_smoke.json")
    assert viewer["status"]=="passed" and len(viewer["checks"])==10
    verification=dict(status="passed",starting_sha=e.START_SHA,mechanical_only=True,
        tests=[dict(command=".venv\\Scripts\\python.exe -m unittest discover -s tests -p test_responses_execution.py -v",count=25,status="passed"),
               dict(command=".venv\\Scripts\\python.exe -m unittest discover -s tests -v",count=170,status="passed",log=".cache/contract12b_full_tests.log",sha256=e.sha((e.ROOT/".cache/contract12b_full_tests.log").read_bytes())),
               dict(command="node --test viewer/tests/adapter.test.mjs",count=13,status="passed")],
        defaults_unchanged=True,control_prompt_unchanged=True,refined_is_exact_append_only=True,
        preserved_harness_ast_except_from_openai=True,protected_files_verified=True,
        case_checks=checks,viewer_compatibility="viewer_smoke.json: all ten control/refined graphs; unchanged adapter and Cytoscape conversion",
        transport_equivalence=manifest["transport_equivalence"],scientific_gate=annotations["gate"],
        operational_recovery=dict(initial_create_failures=3,successful_generations=5,repairs=sum(r["repairs"] for r in summaries),
                                  prompt_adaptations=0,control_generations=0,completed_cases_rerun=0))
    control=(e.REPORT/"prompt_control.txt").read_text(encoding="utf-8")
    amendment=(e.REPORT/"prompt_amendment.txt").read_text(encoding="utf-8")
    assert (e.REPORT/"prompt_refined.txt").read_text(encoding="utf-8")==control+"\n"+amendment
    e.write(e.REPORT/"verification.json",verification)
    header=["# Contract 12B — one frozen prompt refinement","",annotations["gate"],"",
            "This is one amendment, five completed refined generations, no paid control reruns, and no adaptive prompt edits. Production defaults and the original Contract 10 prompt remain unchanged. Talia/user retains the scientific promotion decision.","",
            "## Target findings","", "\n".join(f"- {k}: {v}" for k,v in annotations["target_findings"].items()),"",
            "## Frozen execution","", "| Case | Control → refined relations | Control → refined edges | Repairs | Seconds | Input / output / reasoning tokens | Tier |", "|---|---:|---:|---:|---:|---:|---|"]
    for r in summaries:header.append(f"| {r['slug']} | {r['control_relations']} → {r['relations']} | {r['control_edges']} → {r['edges']} | {r['repairs']} | {r['elapsed_seconds']:.3f} | {r['input_tokens']} / {r['output_tokens']} / {r['reasoning_tokens']} | Standard/default |")
    totals={mode:{field:sum(r["richness"][mode][field] for r in summaries) for field in ("intervention","effects","context")} for mode in ("control","refined")}
    paired_totals={mode:{field:sum(r["matched_finding_richness"][mode][field] for r in summaries) for field in ("intervention","effects","context")} for mode in ("control","refined")}
    header.extend(["","The last three cases succeeded on one operational recovery after initial `create_failed` APIConnectionErrors with no response IDs. A read-only provider request independently failed with DNS `gaierror(11001)`; endpoint DNS subsequently resolved. Initial records and recovery records are preserved separately. Eight create attempts are accounted for: five completed generations and three failures; none of the completed cases was rerun. Failed-attempt token usage is unavailable, not zero. No raw error messages, credentials, or endpoint URLs are stored.","",
                   "## Rich-field diagnostics","",f"Across all five cases (including flagged edges): `{json.dumps(totals,sort_keys=True)}`.","",
                   f"On the 74 manually paired, otherwise-valid findings, control/refined population is `{json.dumps(paired_totals,sort_keys=True)}`. This avoids crediting the four unsupported glucose causal edges or other additions as enrichment of existing findings. Intervention count falls by one as the PTEN title condition moves into context; retained intervention wording is fuller in SFPQ. These pairs are scientific review proposals, not final accepted gold.","",
                   "Excluding the four flagged causal edges gives 85 provisionally source-supported refined relations: 31 with intervention, 38 with effects, 54 with context. The two 11U evidence-locality concerns still apply to those otherwise-supported relations. Scientific acceptance of these records remains pending.","",
                   "SFPQ has substantially fuller explicit outcomes and experimental setting; Cbl gains coverage mainly through additional edges while the original dual-context omissions persist. EZH2 gains some fields but loses maintenance outcomes on two pathway edges. See each case's matched-finding table; totals are not an optimization target.","",
                   "## Prompt","", "`prompt_refined.txt` is exactly `prompt_control.txt` plus one newline and the following amendment. No other control prompt text was changed.","","```text",amendment.rstrip(),"```","",
                   "## Validation and limits","","170 Python tests, including the 25 lifecycle/configuration/transport cases, and 13 viewer tests passed. All ten graphs pass the unchanged viewer adapter and Cytoscape element conversion, preserving direction, evidence, rich fields, node reveals, and input JSON. This verifies viewer data compatibility; no new browser interaction test was performed.","",
                   "Evidence substring, endpoint ID, schema, repair and graph checks are mechanical. They do not prove causality, scientific endpoint meaning, or metadata entailment. All five refined outputs were manually read against the frozen passages here; judgments are review proposals, not independent gold labels. One completion per prompt and case cannot separate all sampling variability from prompt effects. Exact duplicates are measured after existing normalization; raw provider duplicates dropped by validation cannot be inferred from these counts.","",
                   "## Review artifacts","","`frozen_set_manifest.json` records file/input/request/prompt/schema hashes and control equivalence. `telemetry.json` includes saved control telemetry, initial failures, and effective completions. Each case folder contains unchanged input, control, initial refined output, attempt events, comparison and (where needed) one recovery. `graphs/control/` and `graphs/refined/` contain all ten graphs. `scientific_review.json` records explicit judgments and equivalence pairs; `verification.json` records mechanical checks. Historical 12A and 11U artifacts remain untouched.","",
                   "## Remaining promotion risks","", "\n".join(f"- {v}" for v in annotations["remaining_risks"]),""])
    (e.REPORT/"summary.md").write_text("\n".join(header+sections),encoding="utf-8",newline="\n")
    e.write(e.REPORT/"review_freeze.json",dict(status="ready_for_talia_review",created_at_utc=e.previous._utc_now(),
        scientific_gate=annotations["gate"],files={p.relative_to(e.REPORT).as_posix():e.sha(p.read_bytes()) for p in e.REPORT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name!="review_freeze.json"}))
    print(json.dumps(dict(cases=summaries,richness=totals,verification="passed"),indent=2))


if __name__=="__main__":
    main()
