"""Single authorized role proof with frozen NER/RE replay through the ordinary factory.

Only upstream loaders are replaced with recorded adapters; role construction,
graph generation, shared background execution, and grounding stay production code.
A durable marker prevents accidental repetition of this paid proof.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.llm_relation_extraction import OpenAIConfig, RELATION_EXTRACTION_SYSTEM_PROMPT
from biomedical_extractor.relation_extraction import Relation, RelationExtractionResult

OUT = ROOT / "reports/paper_role_auto_13b"
SOURCE = ROOT / "reports/relation_migration_12a/papers/pmcid_pmc11824863.json"
BASE = ROOT / "reports/relation_migration_12a/graphs/candidate/pmcid_pmc11824863.json"
PROMPT_SHA = "13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f"

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def projection(data):
    data = json.loads(json.dumps(data))
    for node in data["nodes"]:
        node.pop("paper_role", None)
    return data

packet = json.loads(SOURCE.read_text(encoding="utf-8"))
text = packet["source"]["source_text"]
entities = tuple(Entity(**value) for value in packet["entities"])
relations = RelationExtractionResult(tuple(Relation(**value) for value in packet["candidate_relations"]))
baseline = json.loads(BASE.read_text(encoding="utf-8"))
preflight = build_graph_result(baseline["document"]["id"], assemble_document_entities(entities, text), relations)
assert projection(preflight.to_dict()) == projection(baseline), "Frozen graph replay diverged"
assert hashlib.sha256(RELATION_EXTRACTION_SYSTEM_PROMPT.encode()).hexdigest() == PROMPT_SHA
if "--preflight" in sys.argv:
    print(json.dumps({"degree_zero": len(preflight.unconnected_nodes), "topology_identical": True,
                      "labels": [node.label for node in preflight.unconnected_nodes]}))
    sys.exit(0)

# Match repository environment-first credential loading without printing secrets.
dotenv = ROOT / ".env"
for line in dotenv.read_text(encoding="utf-8-sig").splitlines() if dotenv.is_file() else ():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
config = OpenAIConfig.from_environment()
config.resolved_api_key()
marker = OUT / "attempt.json"
with marker.open("x", encoding="utf-8") as stream:
    json.dump({"status": "started", "initial_generation_limit": 1,
               "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               "baseline_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest()}, stream, indent=2)

class FrozenNER:
    def extract_entities(self, supplied):
        assert supplied == text
        return entities

class FrozenRE:
    def extract_relations(self, supplied, supplied_entities):
        assert supplied == text and tuple(supplied_entities) == entities
        return relations

started = time.monotonic()
with (
    patch("biomedical_extractor.llm_pipeline.HunFlair2BioMedExtractor.from_pretrained", return_value=FrozenNER()),
    patch("biomedical_extractor.llm_pipeline.LLMRelationExtractor.from_openai", return_value=FrozenRE()),
):
    pipeline = LLMExtractionPipeline.from_pretrained(llm_config=config)
try:
    enriched = pipeline.extract_graph(text, document_id=baseline["document"]["id"], paper_title=packet["title"])
    assert projection(enriched.to_dict()) == projection(baseline)
    orphans = enriched.unconnected_nodes
    assert all(node.paper_role and all(e in text for e in node.paper_role.evidence) for node in orphans)
    assert all(node.paper_role is None for node in enriched.nodes if node not in orphans)
    diagnostics = pipeline.paper_role_extractor.last_generation_diagnostics
    assert sum(not d["repair"] for d in diagnostics) == 1
    write(OUT / "pmcid_pmc11824863.json", enriched.to_dict())
    proof = {"status": "passed", "mechanism": "ordinary from_pretrained/extract_graph with frozen upstream replay",
             "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
             "baseline_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
             "model": "gpt-6.1-sol", "reasoning_effort": "medium", "service_tier": "default",
             "background": True, "degree_zero_nodes": len(orphans),
             "roles_returned": diagnostics[-1]["validated_role_count"],
             "roles_attached": sum(node.paper_role is not None for node in enriched.nodes),
             "evidence_grounding_passed": True, "graph_projection_identical": True,
             "re_prompt_sha256": PROMPT_SHA, "initial_generations": 1,
             "repairs": sum(d["repair"] for d in diagnostics),
             "elapsed_seconds": round(time.monotonic() - started, 3), "diagnostics": diagnostics}
    write(OUT / "live_proof.json", proof)
    write(marker, {"status": "completed"})
    print(json.dumps(proof))
except Exception as error:
    diagnostics = getattr(pipeline.paper_role_extractor, "last_generation_diagnostics", [])
    write(OUT / "live_proof.json", {"status": "failed", "error_type": type(error).__name__, "diagnostics": diagnostics})
    write(marker, {"status": "failed", "error_type": type(error).__name__})
    raise
