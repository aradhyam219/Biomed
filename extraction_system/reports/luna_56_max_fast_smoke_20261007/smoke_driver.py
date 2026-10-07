"""Single authorized SFPQ smoke; preparation is offline and paid execution is one-shot.

Replay frozen entities through the existing NER seam. Real provider factories,
prompts, validation, graph construction, and automatic role orchestration are
used unchanged. No scientific output is repaired by this driver.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
CACHE = Path(__file__).resolve().parent
REPORT = ROOT / "reports/luna_56_max_fast_smoke_20261007"
PACKET = ROOT / "reports/relation_migration_12a/papers/pmcid_pmc11824863.json"
LEDGER = ROOT / "reports/graph_damage_audit_13c/comparisons/pmcid_pmc11824863.json"

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor import llm_relation_extraction as relation
from biomedical_extractor import llm_paper_roles as role
from biomedical_extractor.responses_execution import strict_transport_schema, verify_transport_equivalence


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def env_value(name):
    # Same environment-first credential lookup as the preserved provider harness.
    if os.getenv(name):
        return os.environ[name]
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.strip().removeprefix("export ").partition("=")
        if separator and key.strip() == name:
            return value.strip().strip("\"'") or None
    return None


def tier_passes(requested, observed, *, deliberate_standard=False):
    return (requested == "fast" and observed == "priority") or (
        deliberate_standard and requested == observed == "default"
    )


class FrozenEntities:
    def __init__(self, packet):
        self.source = packet["source"]["source_text"]
        self.entities = tuple(Entity(**value) for value in packet["entities"])

    def extract_entities(self, text):
        assert text == self.source
        return self.entities


def prepare():
    assert not REPORT.exists(), "Report must be fresh"
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    frozen = FrozenEntities(packet)
    assert len(frozen.entities) == 41
    assert digest(frozen.source.encode("utf-8")) == packet["source"]["selected_source_sha256"]
    assert digest(relation.RELATION_EXTRACTION_SYSTEM_PROMPT.encode("utf-8")) == "13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f"
    for entity in frozen.entities:
        assert frozen.source[entity.start:entity.end] == entity.text
    config = relation.OpenAIConfig()
    assert (config.model, config.reasoning_effort, config.background, config.service_tier) == ("gpt-5.6-luna", "max", True, "fast")
    assert role.DEFAULT_PAPER_ROLE_MODEL == config.model and role.DEFAULT_PAPER_ROLE_REASONING_EFFORT == config.reasoning_effort
    offline = json.loads((CACHE / "offline_verification.json").read_text())
    assert offline["passed"]
    assert tier_passes("fast", "priority")
    assert tier_passes("default", "default", deliberate_standard=True)
    assert not tier_passes("default", "default")
    assert not tier_passes("fast", "default") and not tier_passes("fast", None)
    baseline = relation._parse_structured_response(json.dumps({"relations": packet["baseline_relations"]}))
    baseline = relation.validate_relations(frozen.source, frozen.entities, baseline)
    graph = build_graph_result(packet["paper_id"], assemble_document_entities(frozen.entities, frozen.source), baseline)
    protected = {name: digest((ROOT / "src/biomedical_extractor" / name).read_bytes()) for name in (
        "entity_assembly.py", "graph.py", "llm_pipeline.py", "relation_extraction.py", "paper_roles.py", "responses_execution.py"
    )}
    schemas = {}
    for name, module in (("relation", relation), ("role", role)):
        semantic = module._structured_payload_schema().model_json_schema()
        transport = strict_transport_schema(module._structured_payload_schema())
        verify_transport_equivalence(semantic, transport)
        schemas[name] = {"semantic_sha256": digest(canonical(semantic)), "transport_sha256": digest(canonical(transport)),
                         "prompt_sha256": digest((relation.RELATION_EXTRACTION_SYSTEM_PROMPT if name == "relation" else role.PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT).encode("utf-8"))}
        write(REPORT / f"{name}_semantic_schema.json", semantic)
        write(REPORT / f"{name}_transport_schema.json", transport)
    write(REPORT / "inputs.json", {key: packet[key] for key in ("paper_id", "title", "source", "entities", "baseline_relations")})
    write(REPORT / "baseline_graph.json", graph.to_dict())
    ledger = json.loads(LEDGER.read_text())["views"]["baseline_contract10"]["findings"]
    write(REPORT / "frozen_findings.json", [{key: finding[key] for key in ("finding_id", "material", "baseline_relation_indices", "baseline_assertions", "source_evidence")} for finding in ledger])
    diff = subprocess.check_output(["git", "-c", "safe.directory=C:/Projects/Biomed", "-C", "C:/Projects/Biomed", "diff", "--", "extraction_system"])
    (REPORT / "candidate.patch").write_bytes(diff)
    tracked = json.loads((CACHE / "original_hashes.json").read_text())
    write(CACHE / "candidate_hashes.json", {name: digest((ROOT/name).read_bytes()) for name in tracked})
    write(REPORT / "preflight.json", {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_head": subprocess.check_output(["git", "-c", "safe.directory=C:/Projects/Biomed", "-C", "C:/Projects/Biomed", "rev-parse", "HEAD"], text=True).strip(),
        "paper_id": packet["paper_id"], "source_sha256": digest(frozen.source.encode("utf-8")),
        "entities_sha256": digest(canonical(packet["entities"])), "input_packet_file_sha256": digest(PACKET.read_bytes()),
        "baseline_relations_sha256": digest(canonical(packet["baseline_relations"])), "finding_ledger_file_sha256": digest(LEDGER.read_bytes()),
        "schemas": schemas, "protected_modules": protected,
        "candidate": {k: v for k, v in asdict(config).items() if k not in {"api_key", "base_url", "api_key_env"}},
        "budget": {"papers": 1, "initial_relation_generations": 1, "initial_role_batches": 1, "maximum_output_repairs_per_provider": 2, "scientific_repairs": 0, "operational_resubmissions": 0},
        "scientific_gate": "Preserve every material Contract 10 finding and grounded role; any material regression blocks migration without tuning.",
        "tier_gate": "Each default generation must independently record requested fast and observed priority; default/missing observation blocks migration.",
        "offline_verification": offline, "provider_calls": 0, "migration_promoted": False,
        "driver_sha256": digest(Path(__file__).read_bytes()),
    })
    (REPORT / ".gitattributes").write_text("* -text\n", encoding="utf-8")
    (REPORT / "smoke_driver.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"prepared": True, "provider_calls": 0, "offline_tests_passed": offline["tests_run"]}), flush=True)


def run():
    preflight = json.loads((REPORT / "preflight.json").read_text())
    assert not (REPORT / "run_started.json").exists(), "One-shot run has already started; do not resubmit"
    assert digest(PACKET.read_bytes()) == preflight["input_packet_file_sha256"]
    assert digest(LEDGER.read_bytes()) == preflight["finding_ledger_file_sha256"]
    assert digest(Path(__file__).read_bytes()) == preflight["driver_sha256"]
    for name, expected in json.loads((CACHE/"candidate_hashes.json").read_text()).items():
        assert digest((ROOT/name).read_bytes()) == expected, name
    packet = json.loads(PACKET.read_text())
    frozen = FrozenEntities(packet)
    key = env_value(env_value("OPENAI_API_KEY_ENV") or "OPENAI_API_KEY")
    assert key, "Credentials unavailable"
    config = relation.OpenAIConfig(api_key=key, base_url=env_value("OPENAI_BASE_URL"))
    calls = []
    captures = {}
    holders = {}
    import openai
    sdk_factory = openai.OpenAI

    class CapturedResponses:
        def __init__(self, responses):
            self.responses = responses

        def create(self, **kwargs):
            task = "role" if kwargs["text"]["format"]["name"] == "StructuredPaperRolePayload" else "relation"
            number = 1 + sum(call["task"] == task for call in calls)
            assert number <= 3
            assert kwargs["model"] == "gpt-5.6-luna" and kwargs["reasoning"] == {"effort": "max"}
            assert kwargs["background"] is True and kwargs["service_tier"] == "fast"
            call = {"task": task, "generation_number": number, "requested_service_tier": kwargs["service_tier"],
                    "model": kwargs["model"], "reasoning": kwargs["reasoning"], "background": kwargs["background"],
                    "prompt_sha256": digest(kwargs["input"].encode("utf-8")), "status": "create_requested"}
            calls.append(call)
            write(REPORT / "requests.json", calls)
            (CACHE/f"{task}_request_{number:02d}.txt").write_text(kwargs["input"], encoding="utf-8")
            print(json.dumps({"task": task, "generation": number, "status": "create_requested"}), flush=True)
            response = self.responses.create(**kwargs)
            captures[response.id] = call
            self.capture(response)
            return response

        def capture(self, response):
            call = captures[response.id]
            call.update(response_id=response.id, status=response.status, observed_service_tier=response.service_tier)
            write(REPORT / "requests.json", calls)
            if response.output_text:
                (CACHE/f"{call['task']}_raw_{call['generation_number']:02d}.txt").write_text(response.output_text, encoding="utf-8")
            if response.status not in {"queued", "in_progress"}:
                print(json.dumps({"task": call["task"], "status": response.status, "requested": call["requested_service_tier"], "observed": call["observed_service_tier"]}), flush=True)

        def retrieve(self, response_id, **kwargs):
            response = self.responses.retrieve(response_id, **kwargs)
            self.capture(response)
            return response

        def cancel(self, response_id, **kwargs):
            response = self.responses.cancel(response_id, **kwargs)
            self.capture(response)
            return response

    def client_factory(**kwargs):
        client = sdk_factory(**kwargs)
        client.responses = CapturedResponses(client.responses)
        return client

    role_factory = role.LLMPaperRoleExtractor.from_openai

    def capture_role_factory(role_config=None):
        holders["role"] = role_factory(role_config)
        return holders["role"]

    write(REPORT / "run_started.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(), "authorized_papers": 1})
    try:
        with patch("openai.OpenAI", side_effect=client_factory), patch(
            "biomedical_extractor.llm_pipeline.HunFlair2BioMedExtractor.from_pretrained", return_value=frozen
        ), patch.object(role.LLMPaperRoleExtractor, "from_openai", side_effect=capture_role_factory):
            pipeline = LLMExtractionPipeline.from_pretrained(llm_config=config)
            holders["relation"] = pipeline.relation_extractor
            extract = pipeline.extract_relations

            def capture_relations(text, entities):
                result = extract(text, entities)
                holders["relations"] = result
                write(REPORT / "relations.json", result.to_dict())
                diagnostics = pipeline.relation_extractor.last_generation_diagnostics
                write(REPORT / "relation_diagnostics.json", diagnostics)
                if not all(tier_passes(d["requested_service_tier"], d.get("observed_service_tier")) for d in diagnostics):
                    raise RuntimeError("Fast-tier gate failed; no role request permitted")
                return result

            pipeline.extract_relations = capture_relations
            graph = pipeline.extract_graph(frozen.source, document_id=packet["paper_id"], paper_title=packet["title"])
            write(REPORT / "graph.json", graph.to_dict())
            if not all(tier_passes(c["requested_service_tier"], c.get("observed_service_tier")) for c in calls):
                raise RuntimeError("Fast-tier gate failed")
            write(REPORT / "execution.json", {"operational_pass": True, "fast_tier_pass": True, "scientific_review": "pending", "provider_generations": len(calls), "migration_promoted": False})
    except BaseException as error:
        write(REPORT / "execution.json", {"operational_pass": False, "fast_tier_pass": bool(calls) and all(tier_passes(c["requested_service_tier"], c.get("observed_service_tier")) for c in calls), "error_type": type(error).__name__, "provider_generations": len(calls), "migration_promoted": False, "stop_rule": "No resubmission or tuning"})
        print(json.dumps({"execution_complete": False, "error_type": type(error).__name__, "provider_generations": len(calls)}), flush=True)
        raise SystemExit(1) from None
    finally:
        for task in ("relation", "role"):
            if task in holders:
                write(REPORT / f"{task}_diagnostics.json", holders[task].last_generation_diagnostics)
        if "relations" in holders:
            unaugmented = build_graph_result(packet["paper_id"], assemble_document_entities(frozen.entities, frozen.source), holders["relations"])
            write(REPORT / "graph_before_roles.json", unaugmented.to_dict())
        print(json.dumps({"provider_generations": len(calls), "report": str(REPORT)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    prepare() if args.prepare else run()
