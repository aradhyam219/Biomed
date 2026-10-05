"""Freeze, run once, and project Contract 13C without modifying production code.

Historical relations and candidate relations use the same current deterministic
assembly. Scientific judgments are supplied separately after reading the source;
this utility makes no semantic quality decisions.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports/graph_damage_audit_13c"
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("runner12a", ROOT / "reports/relation_migration_12a/scripts/run_frozen_regression.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.llm_relation_extraction import LLMRelationExtractor, RELATION_EXTRACTION_SYSTEM_PROMPT, _structured_payload_schema, _build_prompt
from biomedical_extractor.relation_extraction import Relation, validate_relations
from openai.lib._pydantic import to_strict_json_schema

START = "abcdb79a3d6215e5dc82bbb2ad1e4cf280410851"
OLD = "0330923166a6b85584c1206c7bb21ae4721b99f3"
SLUGS = ("pmcid_pmc10770459", "pmcid_pmc11824863", "pmcid_pmc8605525", "pmid_27172794", "pmid_27370646", "pmid_31324362", "pmid_33652126", "pmid_38569671")
read = runner._read_json
write = runner._atomic_json
sha = runner._sha256
canonical = runner._canonical_json


def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=C:/Projects/Biomed", "-C", str(ROOT.parent), *args], text=True, encoding="utf-8").strip()


def protected():
    """Hash every tracked file outside the new report and attributes."""
    paths = git("ls-files", "extraction_system").splitlines()
    return {p: sha((ROOT.parent / p).read_bytes()) for p in paths if not p.startswith("extraction_system/reports/graph_damage_audit_13c/") and p != "extraction_system/.gitattributes"}


def freeze():
    assert git("rev-parse", "HEAD") == START
    assert not (OUT / "manifest.json").exists(), "Do not overwrite the freeze"
    historical = git("show", f"{OLD}:extraction_system/src/biomedical_extractor/llm_relation_extraction.py")
    tree = ast.parse(historical)
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "RELATION_EXTRACTION_SYSTEM_PROMPT" for t in n.targets))
    old_prompt = ast.literal_eval(assignment.value)
    schema_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_structured_payload_schema")
    namespace = {"Any": Any}
    exec("from __future__ import annotations\n" + ast.get_source_segment(historical, schema_fn), namespace)
    old_schema = namespace["_structured_payload_schema"]().model_json_schema()
    schema = _structured_payload_schema().model_json_schema()
    prompt_sha = sha(RELATION_EXTRACTION_SYSTEM_PROMPT.encode())
    assert prompt_sha == "13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f"
    config = runner._config_record(runner._candidate_config())
    twelve = runner._verify_frozen_inputs()
    assert schema == old_schema, "Record schema confound before proceeding"
    assert sha(canonical(schema)) == twelve["semantic_schema_sha256"]
    manifest = {"contract": "13C", "starting_sha": START, "configuration": config, "protected_files": protected(), "prompt_sha256": prompt_sha, "semantic_schema_sha256": sha(canonical(schema)), "09b_equivalence": {"implementation_commit": OLD, "prompt_equal": old_prompt == RELATION_EXTRACTION_SYSTEM_PROMPT, "historical_prompt_sha256": sha(old_prompt.encode()), "semantic_schema_equal": True, "confound": "Contract 10 adds exclusion of naming/alias-only relations. All other prompt text is identical."}, "papers": [], "policy": "One fresh production RE extraction per necessary paper; no role calls, second pass, auditor, or tuning. Production bounded structured-output validation remains unchanged."}
    for slug in SLUGS:
        old_path = ROOT / f"reports/relation_generalization_09b/papers/{slug}.json"
        old = read(old_path)
        assert old["status"] == "success"
        source, entities = old["source"]["text"], old["entities"]
        p = {"slug": slug, "paper_id": old["paper_id"], "title": old["title"], "source_text": source, "entities": entities, "baseline_09b": old["mention_level_rich_relations"], "historical_09b_graph": old["graph"]}
        found = next((v for v in twelve["papers"] if v["slug"] == slug), None)
        row = {"slug": slug, "paper_id": old["paper_id"], "09b_artifact_sha256": sha(old_path.read_bytes()), "reuse": found is not None}
        if found:
            assert source == found["source"]["source_text"]
            assert {v["id"]: v for v in entities} == {v["id"]: v for v in found["entities"]}
            row["09b_packet_order_differs"] = entities != found["entities"]
            p["entities"] = found["entities"]
            p["baseline_contract10"] = found["baseline_relations"]
            p["historical_contract10_graph"] = read(ROOT / f"reports/relation_contract_10/graphs/{slug}.json")
            result_path = ROOT / f".cache/relation_migration_12a/candidate/{slug}/result.json"
            result = read(result_path)
            assert result["status"] == "success" and result["repair_attempts"] == 0
            assert result["configuration"] == config
            assert result["source_sha256"] == sha(source.encode())
            assert result["entity_packet_sha256"] == sha(canonical(p["entities"]))
            assert result["semantic_controls"] == {"system_prompt_sha256": prompt_sha, "semantic_schema_sha256": manifest["semantic_schema_sha256"]}
            assert all(d["execution_mode"] == "background" and d["observed_model"] == "gpt-6.1-sol" and d["observed_reasoning_effort"] == "medium" and d["observed_service_tier"] == "default" for d in result["generation_diagnostics"])
            dest = OUT / "candidate" / slug
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(result_path, dest / "result.json")
            shutil.copyfile(result_path.with_name("attempt.json"), dest / "attempt.json")
            row["reused_from"] = result_path.relative_to(ROOT).as_posix()
            row["reused_output_sha256"] = sha(result_path.read_bytes())
        for e in p["entities"]:
            assert source[e["start"]:e["end"]] == e["text"]
        row.update(source_sha256=sha(source.encode()), entity_packet_sha256=sha(canonical(p["entities"])))
        write(OUT / "inputs" / f"{slug}.json", p)
        row["input_sha256"] = sha((OUT / "inputs" / f"{slug}.json").read_bytes())
        manifest["papers"].append(row)
    write(OUT / "semantic_schema.json", schema)
    (OUT / "prompt_09b.txt").write_text(old_prompt, encoding="utf-8")
    (OUT / "prompt_confounds.diff").write_text("".join(difflib.unified_diff(old_prompt.splitlines(True), RELATION_EXTRACTION_SYSTEM_PROMPT.splitlines(True), fromfile="09B", tofile="Contract10-current")), encoding="utf-8")
    write(OUT / "transport_schema.json", to_strict_json_schema(_structured_payload_schema()))
    (OUT / "prompt.txt").write_text(RELATION_EXTRACTION_SYSTEM_PROMPT, encoding="utf-8")
    write(OUT / "manifest.json", manifest)
    print("Frozen eight inputs; verified four exact 12A reuses; recorded 09B prompt confound, equivalent schema")


def verify():
    m = read(OUT / "manifest.json")
    actual = protected()
    assert all(actual.get(p) == h for p, h in m["protected_files"].items()), "Protected artifact changed"
    assert sha(RELATION_EXTRACTION_SYSTEM_PROMPT.encode()) == m["prompt_sha256"]
    for row in m["papers"]:
        assert sha((OUT / "inputs" / f"{row['slug']}.json").read_bytes()) == row["input_sha256"]
    return m


def run():
    m = verify()
    for row in m["papers"]:
        if row["reuse"]:
            continue
        slug = row["slug"]
        dest = OUT / "candidate" / slug
        if (dest / "attempt.json").exists():
            assert (dest / "result.json").exists(), "Existing failed/interrupted attempt requires investigation; no resubmission"
            continue
        verify()
        p = read(OUT / "inputs" / f"{slug}.json")
        config = runner._candidate_config()
        assert runner._config_record(config) == m["configuration"]
        state = {"contract": "13C", "paper_id": p["paper_id"], "configuration": m["configuration"], "source_sha256": row["source_sha256"], "entity_packet_sha256": row["entity_packet_sha256"], "status": "launch_started", "diagnostic_events": []}
        write(dest / "attempt.json", state)
        def callback(d):
            state["diagnostic_events"].append(runner._sanitize_diagnostic(d))
            write(dest / "attempt.json", state)
        extractor = LLMRelationExtractor.from_openai(config, diagnostics_callback=callback)
        executor = extractor._background_executor
        original = executor.execute
        def capture(prompt, diagnostics):
            value = original(prompt, diagnostics)
            (dest / f"raw_{diagnostics['generation_number']:02d}.txt").write_text(value, encoding="utf-8")
            return value
        executor.execute = capture
        entities = tuple(Entity(**v) for v in p["entities"])
        (dest / "request.txt").write_text(_build_prompt(p["source_text"], entities, RELATION_EXTRACTION_SYSTEM_PROMPT), encoding="utf-8")
        started = time.monotonic()
        try:
            result = extractor.extract_relations(p["source_text"], entities)
            write(dest / "result.json", {"contract": "13C", "paper_id": p["paper_id"], "status": "success", "configuration": m["configuration"], "relations": [v.to_dict() for v in result.relations], "generation_diagnostics": list(extractor.last_generation_diagnostics), "elapsed_seconds": time.monotonic()-started})
            state["status"] = "success"
        except Exception as error:
            state.update(status="failed", error_class=type(error).__name__, generation_diagnostics=list(extractor.last_generation_diagnostics))
            write(dest / "attempt.json", state)
            raise
        write(dest / "attempt.json", state)
        print(slug, len(result.relations), "relations", flush=True)


def project():
    m = verify()
    for row in m["papers"]:
        slug = row["slug"]
        p = read(OUT / "inputs" / f"{slug}.json")
        entities = tuple(Entity(**e) for e in p["entities"])
        assembly = assemble_document_entities(entities, p["source_text"])
        write(OUT / "projections" / slug / "assembly.json", assembly.to_dict())
        sets = {"baseline_09b": p["baseline_09b"], "candidate": read(OUT / "candidate" / slug / "result.json")["relations"]}
        if "baseline_contract10" in p:
            sets["baseline_contract10"] = p["baseline_contract10"]
        for name, values in sets.items():
            relations = tuple(Relation(**r) for r in values)
            valid = validate_relations(p["source_text"], entities, relations)
            assert len(valid.relations) == len(relations)
            graph = build_graph_result(p["paper_id"], assembly, valid)
            write(OUT / "projections" / slug / f"{name}.json", graph.to_dict())
        print(slug, {n: len(v) for n,v in sets.items()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "run", "project", "verify"])
    args = parser.parse_args()
    globals()[args.mode]()
