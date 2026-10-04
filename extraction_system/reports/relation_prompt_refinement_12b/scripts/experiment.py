"""One-shot Contract 12B freeze, serial live run, and deterministic comparison.

Reuse saved Sol-medium controls; all graphs traverse the unchanged production
pipeline with frozen entities and no role calls. Durable attempts prevent paid
resubmission. Scientific judgments belong in the separate review packet.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
START_SHA = "c8f37d4c3666d0bdd2a1b46f6a2f34f5569b48e2"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "reports/relation_migration_12a/scripts"))
import run_frozen_regression as previous
import build_review_packet as review
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.llm_relation_extraction import (
    LLMRelationExtractor, OpenAIConfig, RELATION_EXTRACTION_SYSTEM_PROMPT,
    _build_prompt, _structured_payload_schema,
)
from biomedical_extractor.responses_execution import strict_transport_schema, verify_transport_equivalence
from biomedical_extractor.relation_extraction import Relation, validate_relations

read = previous._read_json
write = previous._atomic_json
sha = previous._sha256
canonical = previous._canonical_json


def git(*args):
    return subprocess.check_output([
        "git", "-c", "safe.directory=C:/Projects/Biomed", "-C", str(ROOT.parent), *args
    ], text=True).strip()


def replay(case, relations):
    """Replay saved relations through the same composition seam used live."""
    entities = tuple(Entity(**item) for item in case["entities"])
    validated = validate_relations(case["source_text"], entities, [Relation(**r) for r in relations])
    assert json.loads(json.dumps(validated.to_dict()["relations"])) == relations
    saved = previous._FrozenRelationExtractor(case["source_text"], entities, validated.relations)
    pipeline = LLMExtractionPipeline(previous._FrozenEntityExtractor(case["source_text"], entities), saved)
    return pipeline.extract_graph(case["source_text"], document_id=case["paper_id"], paper_title=case["title"]).to_dict()


def freeze():
    """Establish control equivalence and freeze every scientific input before API use."""
    if (REPORT / "frozen_set_manifest.json").exists():
        raise RuntimeError("Refusing to overwrite the experiment freeze")
    assert git("rev-parse", "HEAD") == git("rev-parse", "origin/extraction_system_v2") == START_SHA
    assert git("branch", "--show-current") == "extraction_system_v2"
    inputs = previous._verify_frozen_inputs()
    previous._runtime_semantic_controls(inputs)
    control = RELATION_EXTRACTION_SYSTEM_PROMPT
    amendment = (REPORT / "prompt_amendment.txt").read_text(encoding="utf-8")
    refined = control + "\n" + amendment
    for name, prompt in [("control", control), ("refined", refined)]:
        (REPORT / f"prompt_{name}.txt").write_text(prompt, encoding="utf-8", newline="\n")
    schema = _structured_payload_schema()
    wire = strict_transport_schema(schema)
    pre11 = read(ROOT / "reports/model_selection_11u/preflight.json")
    assert sha(canonical(schema.model_json_schema())) == pre11["semantic_schema_sha256"]
    assert sha(canonical(wire)) == pre11["transport_schema_sha256"]
    write(REPORT / "semantic_schema.json", schema.model_json_schema())
    write(REPORT / "transport_schema.json", wire)
    cases = []
    dependencies = [previous.FROZEN_INPUTS_PATH, previous.MANIFEST_PATH,
                    ROOT / "reports/relation_migration_12a/telemetry.json",
                    ROOT / "reports/model_selection_11u/preflight.json"]
    telemetry = read(dependencies[2])
    for paper in inputs["papers"]:
        path = ROOT / f"reports/relation_migration_12a/papers/{paper['slug']}.json"
        packet = read(path)
        assert packet["candidate_status"] == "success"
        assert packet["entities"] == paper["entities"] and packet["source"] == paper["source"]
        graph_path = ROOT / packet["graphs"]["candidate_path"]
        row = next(r for r in telemetry["papers"] if r["paper_id"] == paper["paper_id"])
        cases.append(dict(paper_id=paper["paper_id"], slug=paper["slug"], title=paper["title"],
                          source_text=paper["source"]["source_text"], entities=paper["entities"],
                          control_relations=packet["candidate_relations"], control_telemetry=row,
                          control_path=path.relative_to(ROOT).as_posix(), directory="papers"))
        assert replay(cases[-1], cases[-1]["control_relations"]) == read(graph_path)
        dependencies.extend([path, graph_path])
    passage_path = ROOT / "reports/model_selection_11u/frozen_input.json"
    result_path = ROOT / "reports/model_selection_11u/candidate_runs/gpt_61_sol_medium_standard/real.json"
    passage, result = read(passage_path), read(result_path)
    assert result["status"] == "success"
    entities = tuple(Entity(**item) for item in passage["entity_packet"])
    assert sha(passage["source_text"].encode()) == passage["source_sha256"]
    # 11U hashes indented JSON; 12A uses compact canonical JSON.
    assert sha(json.dumps(passage["entity_packet"], ensure_ascii=False, indent=2, sort_keys=True).encode()) == passage["entity_packet_sha256"]
    assert sha(_build_prompt(passage["source_text"], entities, control).encode()) == passage["prompt_sha256"]
    for generation in result["generations"]:
        assert generation["prompt_sha256"] == passage["prompt_sha256"]
        assert generation["schema_sha256"] == pre11["semantic_schema_sha256"]
        assert generation["transport_schema_sha256"] == pre11["transport_schema_sha256"]
        config = generation["configuration"]
        assert (config["model"], config["reasoning"], config["service_tier"], config["background"], config["store"], config["max_output_tokens"]) == ("gpt-6.1-sol", {"effort": "medium"}, "default", True, False, 128000)
    cases.append(dict(paper_id=passage["paper_id"], slug="contract11u_passage_001", title="Contract 11U frozen passage_001",
                      source_text=passage["source_text"], entities=passage["entity_packet"],
                      source_range=passage["source_range"], control_relations=result["validated_relations"],
                      control_telemetry=result, control_path=result_path.relative_to(ROOT).as_posix(), directory="contract11u_passage"))
    dependencies.extend([passage_path, result_path])
    assert telemetry["configuration"] == previous._config_record(OpenAIConfig(
        model="gpt-6.1-sol", reasoning_effort="medium", background=True, service_tier="default"))
    rows = []
    for case in cases:
        for entity in case["entities"]:
            assert case["source_text"][entity["start"]:entity["end"]] == entity["text"]
        graph = replay(case, case["control_relations"])
        base = REPORT / case["directory"] / case["slug"]
        write(base / "input.json", {k:v for k,v in case.items() if not k.startswith("control_")})
        write(base / "control.json", {k:v for k,v in case.items() if k.startswith("control_")})
        write(REPORT / "graphs/control" / f"{case['slug']}.json", graph)
        rows.append(dict(slug=case["slug"], paper_id=case["paper_id"], directory=case["directory"],
                         source_sha256=sha(case["source_text"].encode()), entities_sha256=sha(canonical(case["entities"])),
                         control_output_sha256=sha(canonical(case["control_relations"])),
                         control_request_sha256=sha(_build_prompt(case["source_text"], tuple(Entity(**e) for e in case["entities"]), control).encode()),
                         refined_request_sha256=sha(_build_prompt(case["source_text"], tuple(Entity(**e) for e in case["entities"]), refined).encode())))
    protected = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in (ROOT / "src").rglob("*.py")}
    protected.update({p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in (ROOT / "viewer").rglob("*") if p.is_file()})
    frozen_files = {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in REPORT.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    write(REPORT / "frozen_set_manifest.json", dict(contract="12B", starting_sha=START_SHA,
        frozen_at_utc=previous._utc_now(), configuration=previous._config_record(OpenAIConfig(
            model="gpt-6.1-sol", reasoning_effort="medium", background=True, service_tier="default")),
        production_defaults=previous._config_record(OpenAIConfig()), cases=rows,
        prompt_control_sha256=sha(control.encode()), prompt_refined_sha256=sha(refined.encode()),
        amendment_sha256=sha(amendment.encode()), control_equivalence_established=True,
        control_reruns_required=False, transport_equivalence=verify_transport_equivalence(schema.model_json_schema(), wire),
        protected_files=protected, frozen_files=frozen_files,
        dependencies={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in dependencies}))
    print("Frozen five inputs; controls equivalent; no paid control reruns required.")


def verify_freeze():
    manifest = read(REPORT / "frozen_set_manifest.json")
    for group in ("protected_files", "frozen_files", "dependencies"):
        for name, digest in manifest[group].items():
            assert sha((ROOT / name).read_bytes()) == digest, f"Frozen file changed: {name}"
    assert previous._config_record(OpenAIConfig()) == manifest["production_defaults"]
    assert sha(RELATION_EXTRACTION_SYSTEM_PROMPT.encode()) == manifest["prompt_control_sha256"]
    return manifest


def run():
    """Run each frozen refined request once with the unchanged finite repair budget."""
    manifest = verify_freeze()
    assert git("rev-parse", "HEAD") == START_SHA
    state_path = REPORT / "run_state.json"
    if state_path.exists():
        raise RuntimeError("A live run already exists; refusing duplicate submissions")
    config = previous._candidate_config()
    assert previous._config_record(config) == manifest["configuration"]
    state = dict(status="running", started_at_utc=previous._utc_now(), cases=[])
    write(state_path, state)
    refined = (REPORT / "prompt_refined.txt").read_text(encoding="utf-8")
    for row in manifest["cases"]:
        verify_freeze()
        base = REPORT / row["directory"] / row["slug"]
        case = read(base / "input.json")
        attempt_path = base / "attempt.json"
        if attempt_path.exists():
            raise RuntimeError("Attempt exists; refusing duplicate submission")
        attempt = dict(status="launch_started", started_at_utc=previous._utc_now(), diagnostic_events=[])
        write(attempt_path, attempt)

        def diagnostic(snapshot):
            attempt["diagnostic_events"].append({"recorded_at_utc":previous._utc_now(), **previous._sanitize_diagnostic(snapshot)})
            attempt["status"] = "provider_progress"
            write(attempt_path, attempt)

        started = time.perf_counter()
        extractor = None
        try:
            entities = tuple(Entity(**e) for e in case["entities"])
            assert sha(_build_prompt(case["source_text"], entities, refined).encode()) == row["refined_request_sha256"]
            extractor = LLMRelationExtractor.from_openai(config, prompt=refined, diagnostics_callback=diagnostic)
            recording = previous._RecordingRelationExtractor(extractor)
            pipeline = LLMExtractionPipeline(previous._FrozenEntityExtractor(case["source_text"], entities), recording)
            graph = pipeline.extract_graph(case["source_text"], document_id=case["paper_id"], paper_title=case["title"]).to_dict()
            relations = [r.to_dict() for r in recording.last_result.relations]
            write(REPORT / "graphs/refined" / f"{row['slug']}.json", graph)
            result = dict(status="success", relations=relations, graph=graph)
        except Exception as error:
            result = dict(status="failed", error_class=type(error).__name__)
        diagnostics = [previous._sanitize_diagnostic(d) for d in extractor.last_generation_diagnostics] if extractor else []
        result.update(elapsed_seconds=round(time.perf_counter()-started, 6), generation_diagnostics=diagnostics,
                      repair_attempts=max(0,len(diagnostics)-1), completed_at_utc=previous._utc_now())
        write(base / "refined.json", result)
        attempt.update(status=result["status"], completed_at_utc=result["completed_at_utc"], final_generation_diagnostics=diagnostics)
        write(attempt_path, attempt)
        state["cases"].append({"slug":row["slug"], "status":result["status"]})
        write(state_path, state)
        print(f"{row['slug']}: {result['status']}, {len(result.get('relations',[]))} relations, {result['elapsed_seconds']:.1f}s", flush=True)
    state.update(status="complete", completed_at_utc=previous._utc_now())
    write(state_path, state)


def compare():
    """Write deterministic deltas without equating wording changes to scientific novelty."""
    manifest = verify_freeze()
    rows, telemetry = [], []
    for row in manifest["cases"]:
        base = REPORT / row["directory"] / row["slug"]
        case, control, refined = read(base / "input.json"), read(base / "control.json"), read(base / "refined.json")
        before, after = control["control_relations"], refined.get("relations", [])
        delta = review._relation_delta(before, after)
        graphs = {}
        if refined["status"] == "success":
            left = read(REPORT / "graphs/control" / f"{row['slug']}.json")
            right = refined["graph"]
            assert replay(case, after) == right
            graphs = dict(control=review._graph_overview(left,before), refined=review._graph_overview(right,after),
                          edge_delta=review._multiset_delta(
                              [json.loads(review._edge_identity(e)) for e in left["edges"]],
                              [json.loads(review._edge_identity(e)) for e in right["edges"]]),
                          nodes_identical=left["nodes"] == right["nodes"])
        richness = {mode:{field:sum(bool(r.get(field)) for r in relations) for field in ("intervention","effects","context")}
                    for mode, relations in [("control",before),("refined",after)]}
        packet = dict(case=case, control_relations=before, refined_relations=after, relation_delta=delta, graphs=graphs, richness=richness)
        write(base / "comparison.json", packet)
        rows.append(dict(slug=row["slug"], status=refined["status"], control_relations=len(before), refined_relations=len(after), richness=richness,
                         control_edges=graphs.get("control",{}).get("edge_count"), refined_edges=graphs.get("refined",{}).get("edge_count")))
        telemetry.append(dict(slug=row["slug"], control=control["control_telemetry"], refined={k:v for k,v in refined.items() if k not in ("relations","graph")}))
    write(REPORT / "comparison.json", rows)
    write(REPORT / "telemetry.json", telemetry)
    print(json.dumps(rows,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "run", "compare", "verify"))
    mode = parser.parse_args().mode
    {"freeze":freeze, "run":run, "compare":compare, "verify":verify_freeze}[mode]()
