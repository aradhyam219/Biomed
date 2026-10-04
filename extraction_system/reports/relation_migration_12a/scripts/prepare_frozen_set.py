"""Freeze the established Contract 10 inputs for the Contract 12A shadow run.

This report utility reads the ignored Contract 10 raw outputs, validates their
source/entity/relation provenance, and writes self-contained review inputs plus
a compact hash manifest. It does not contact a provider or alter frozen files.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
GIT_ROOT = ROOT.parent
BASELINE_SHA = "96b8312879b337c57aba51342676890602b5c30d"
CONTRACT_10_COMMIT = "16b00b4e7ebe99ec257adf93917d3487629be257"
PAPERS = (
    ("PMCID:PMC11824863", "pmcid_pmc11824863"),
    ("PMCID:PMC8605525", "pmcid_pmc8605525"),
    ("PMID:27172794", "pmid_27172794"),
    ("PMID:33652126", "pmid_33652126"),
)
PROMPT_PATH = "src/biomedical_extractor/llm_relation_extraction.py"
SCHEMA_PATH = "src/biomedical_extractor/relation_extraction.py"
PROTECTED_PATHS = (
    PROMPT_PATH,
    SCHEMA_PATH,
    "src/biomedical_extractor/entity_assembly.py",
    "src/biomedical_extractor/graph.py",
    "src/biomedical_extractor/pipeline.py",
    "src/biomedical_extractor/llm_pipeline.py",
)
INVARIANTS_PATH = ROOT / ".cache/relation_migration_12a/starting_invariants.json"
RAW_DIR = ROOT / ".cache/relation_contract_10/papers"
CORPUS_PATH = ROOT / ".cache/ner_target_domain/target_corpus.json"
CONTRACT_10_GRAPH_DIR = ROOT / "reports/relation_contract_10/graphs"
CONTRACT_10_SUMMARY_PATH = ROOT / "reports/relation_contract_10/summary.json"
TEN_RC_DIR = ROOT / ".cache/contract_10r/final_10rc/graphs"
TEN_RD_ROLE_DIR = ROOT / ".cache/contract_10r/role_runs_10rd"
OUTPUT_DIR = ROOT / "reports/relation_migration_12a"
INPUTS_PATH = OUTPUT_DIR / "frozen_inputs.json"
MANIFEST_PATH = OUTPUT_DIR / "frozen_set_manifest.json"
PROTECTED_START_PATH = OUTPUT_DIR / "protected_start_invariants.json"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(encoded)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(
        [
            "git",
            "-c",
            "safe.directory=C:/Projects/Biomed",
            "-C",
            str(GIT_ROOT),
            *args,
        ],
        text=True,
    ).strip()


def _prompt_sha_at(revision: str) -> str:
    source = subprocess.check_output(
        [
            "git",
            "-c",
            "safe.directory=C:/Projects/Biomed",
            "-C",
            str(GIT_ROOT),
            "show",
            f"{revision}:extraction_system/{PROMPT_PATH}",
        ],
        text=True,
        encoding="utf-8",
    )
    module = ast.parse(source)
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "RELATION_EXTRACTION_SYSTEM_PROMPT"
            for target in node.targets
        )
    )
    prompt = ast.literal_eval(assignment.value)
    return _sha256(prompt.encode("utf-8"))


def _git_blob(revision: str, path: str) -> str:
    return _git("rev-parse", f"{revision}:extraction_system/{path}")


def _validate_relation_payload(source_text: str, entities: list[dict[str, Any]], relations: list[dict[str, Any]]) -> None:
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.relation_extraction import Relation, validate_relations

    entity_values = tuple(Entity(**entity) for entity in entities)
    relation_values = tuple(Relation(**relation) for relation in relations)
    validated = validate_relations(source_text, entity_values, relation_values)
    normalized = json.loads(
        json.dumps(
            [item.to_dict() for item in validated.relations],
            ensure_ascii=False,
        )
    )
    if normalized != relations:
        raise RuntimeError("Frozen Contract 10 relations changed under current validation")


def main() -> None:
    """Validate frozen provenance and write the self-contained report inputs."""

    import sys

    sys.path.insert(0, str(ROOT / "src"))

    if _git("rev-parse", "HEAD") != BASELINE_SHA:
        raise RuntimeError("Frozen input preparation requires the verified baseline HEAD")
    if any(path.exists() for path in (INPUTS_PATH, MANIFEST_PATH, PROTECTED_START_PATH)):
        raise RuntimeError("Refusing to overwrite an existing Contract 12A freeze")
    for path in (RAW_DIR, CORPUS_PATH, CONTRACT_10_GRAPH_DIR, INVARIANTS_PATH):
        if not path.exists():
            raise RuntimeError(f"Required frozen source is missing: {path.relative_to(ROOT)}")

    invariants = _read_json(INVARIANTS_PATH)
    if invariants.get("baseline_sha") != BASELINE_SHA:
        raise RuntimeError("Protected starting invariants do not match the required baseline")
    if _prompt_sha_at(CONTRACT_10_COMMIT) != invariants["system_prompt_sha256"]:
        raise RuntimeError("Contract 10 historical system prompt hash does not match the runtime freeze")
    if _prompt_sha_at(BASELINE_SHA) != invariants["system_prompt_sha256"]:
        raise RuntimeError("Current baseline system prompt differs from Contract 10")
    _write_json(PROTECTED_START_PATH, invariants)

    protected_blobs = {}
    for path in PROTECTED_PATHS:
        contract_10_blob = _git_blob(CONTRACT_10_COMMIT, path)
        current_blob = _git_blob(BASELINE_SHA, path)
        if contract_10_blob != current_blob:
            raise RuntimeError(f"Protected code changed since Contract 10: {path}")
        protected_blobs[path] = {
            "contract_10_blob": contract_10_blob,
            "baseline_blob": current_blob,
        }

    corpus = _read_json(CORPUS_PATH)
    corpus_by_id = {paper["paper_id"]: paper for paper in corpus["papers"]}
    contract_10_summary = _read_json(CONTRACT_10_SUMMARY_PATH)
    summary_by_id = {
        paper["paper_id"]: paper for paper in contract_10_summary["papers"]
    }
    if contract_10_summary["source"]["selected_papers"] != [item[0] for item in PAPERS]:
        raise RuntimeError("The existing Contract 10 paper set differs from the frozen selection")

    frozen_papers: list[dict[str, Any]] = []
    paper_manifest: list[dict[str, Any]] = []
    for paper_id, slug in PAPERS:
        raw_path = RAW_DIR / f"{slug}.json"
        graph_path = CONTRACT_10_GRAPH_DIR / f"{slug}.json"
        raw = _read_json(raw_path)
        paper = corpus_by_id.get(paper_id)
        if paper is None or raw.get("paper_id") != paper_id:
            raise RuntimeError(f"Frozen paper identity mismatch for {paper_id}")
        if raw.get("status") != "success":
            raise RuntimeError(f"Contract 10 raw output is not successful for {paper_id}")
        if raw.get("configuration", {}).get("relation_model") != "gpt-5.6-luna":
            raise RuntimeError(f"Unexpected Contract 10 relation model for {paper_id}")
        if raw.get("configuration", {}).get("reasoning_effort") != "max":
            raise RuntimeError(f"Unexpected Contract 10 reasoning setting for {paper_id}")
        if raw.get("configuration", {}).get("prompt_frozen_before_first_paper") is not True:
            raise RuntimeError(f"Contract 10 prompt was not recorded frozen for {paper_id}")
        if raw.get("configuration", {}).get("selection_frozen_before_first_inference") is not True:
            raise RuntimeError(f"Contract 10 selection was not recorded frozen for {paper_id}")
        if raw.get("relation_provider_attempts") != 1 or raw.get("relation_provider_failures") != 0:
            raise RuntimeError(f"Contract 10 relation run had repairs or provider failures for {paper_id}")

        source = raw["source"]
        source_text = source["text"]
        source_sha = _sha256(source_text.encode("utf-8"))
        if source_sha != source["selected_source_sha256"]:
            raise RuntimeError(f"Selected Contract 10 source checksum failed for {paper_id}")
        if source.get("scope") != "title plus complete abstract":
            raise RuntimeError(f"Unexpected source scope for {paper_id}")
        if source.get("canonical_full_text_sha256") != paper.get("text_sha256"):
            raise RuntimeError(f"Canonical full-source provenance mismatch for {paper_id}")

        entities = raw["mention_level_entities"]
        relations = raw["mention_level_relations"]
        for entity in entities:
            if source_text[entity["start"] : entity["end"]] != entity["text"]:
                raise RuntimeError(f"Frozen entity span mismatch for {paper_id}: {entity['id']}")
        _validate_relation_payload(source_text, entities, relations)

        stored_graph = _read_json(graph_path)
        if stored_graph != raw["graph"]:
            raise RuntimeError(f"Tracked Contract 10 graph differs from its raw frozen input for {paper_id}")
        graph_stats = {
            "nodes": len(stored_graph["nodes"]),
            "edges": len(stored_graph["edges"]),
            "evidence_records": sum(len(edge["evidence"]) for edge in stored_graph["edges"]),
            "unconnected_nodes": summary_by_id[paper_id]["unconnected"],
            "genuine_self_edges": [
                {"id": edge["id"], "source": edge["source"], "target": edge["target"], "predicate": edge["predicate"]}
                for edge in stored_graph["edges"]
                if edge["source"] == edge["target"]
            ],
        }
        if graph_stats["evidence_records"] != len(relations):
            raise RuntimeError(f"Tracked Contract 10 graph lost relation evidence for {paper_id}")

        frozen_papers.append(
            {
                "paper_id": paper_id,
                "slug": slug,
                "title": raw["title"],
                "source": {
                    "scope": source["scope"],
                    "source_text": source_text,
                    "selected_source_sha256": source_sha,
                    "canonical_full_text_sha256": source["canonical_full_text_sha256"],
                    "canonical_source_checksum": source.get("canonical_source_checksum"),
                    "segments": source.get("segments", []),
                    "source_url": paper.get("source_url"),
                    "acquisition_mode": paper.get("acquisition_mode"),
                },
                "entities": entities,
                "baseline_relations": relations,
            }
        )
        paper_manifest.append(
            {
                "paper_id": paper_id,
                "slug": slug,
                "source": {
                    "scope": source["scope"],
                    "characters": len(source_text),
                    "selected_text_sha256": source_sha,
                    "canonical_full_text_sha256": source["canonical_full_text_sha256"],
                    "canonical_source_checksum": source.get("canonical_source_checksum"),
                },
                "ner": {
                    "entity_count": len(entities),
                    "entities_canonical_sha256": _canonical_sha256(entities),
                    "all_spans_match_source": True,
                },
                "relation_baseline": {
                    "model": "gpt-5.6-luna",
                    "reasoning_effort": "max",
                    "provider_attempts": raw["relation_provider_attempts"],
                    "repair_attempts": max(raw["relation_provider_attempts"] - 1, 0),
                    "relation_count": len(relations),
                    "relations_canonical_sha256": _canonical_sha256(relations),
                },
                "historical_contract_10_graph": {
                    "path": graph_path.relative_to(ROOT).as_posix(),
                    "sha256": _sha256(graph_path.read_bytes()),
                    **graph_stats,
                },
                "later_10rc_graph_reference": (
                    {
                        "path": (TEN_RC_DIR / f"{slug}.json").relative_to(ROOT).as_posix(),
                        "sha256": _sha256((TEN_RC_DIR / f"{slug}.json").read_bytes()),
                        "role_cache_path": (TEN_RD_ROLE_DIR / f"{slug}.json").relative_to(ROOT).as_posix(),
                        "role_cache_sha256": _sha256((TEN_RD_ROLE_DIR / f"{slug}.json").read_bytes()),
                    }
                    if (TEN_RC_DIR / f"{slug}.json").exists()
                    and (TEN_RD_ROLE_DIR / f"{slug}.json").exists()
                    else None
                ),
            }
        )

    inputs = {
        "contract": "12A",
        "selection_basis": "The complete frozen Contract 10 four-paper regression set, selected before its first inference; no candidate outputs were available at selection time.",
        "baseline_commit": BASELINE_SHA,
        "contract_10_selection_commit": CONTRACT_10_COMMIT,
        "system_prompt_sha256": invariants["system_prompt_sha256"],
        "semantic_schema_sha256": invariants["semantic_schema_sha256"],
        "papers": frozen_papers,
    }
    _write_json(INPUTS_PATH, inputs)
    manifest = {
        "contract": "12A",
        "status": "frozen_inputs_prepared_candidate_not_run",
        "baseline_commit": BASELINE_SHA,
        "contract_10_selection_commit": CONTRACT_10_COMMIT,
        "contract_10_run_window": "2026-09-21; frozen four-paper run, completed before the Contract 10 report commit",
        "selection_basis": inputs["selection_basis"],
        "candidate": {
            "model": "gpt-6.1-sol",
            "reasoning_effort": "medium",
            "service_tier": "default",
            "service_label": "Standard",
            "background": True,
        },
        "historical_equivalence": {
            "system_prompt_sha256": invariants["system_prompt_sha256"],
            "semantic_schema_sha256": invariants["semantic_schema_sha256"],
            "protected_git_blobs_identical_to_contract_10_commit": protected_blobs,
            "control_baseline": "Reuse saved Contract 10 relation outputs after source/entity/prompt/schema equivalence checks; rebuild both control and candidate graphs through current LLMExtractionPipeline.extract_graph.",
            "paid_baseline_required": False,
        },
        "compatibility_notes": {
            "re_relation_source": "Exact saved title plus complete abstract text, even where the current corpus also stores full paper text.",
            "entity_input": "The saved Contract 10 mention-level entity packet is embedded in frozen_inputs.json and must be returned unchanged by the injected extractor.",
            "role_policy": "Paper roles are omitted from both migration comparison paths. Existing Contract 10 and 10R-D role artifacts are provenance references only; no frozen roles are replayed onto candidate graphs.",
            "10rc_10rd_policy": "Later identity-verifier/role graphs are recorded as history references, not used as the graph baseline. The selected control is the saved Contract 10 relations replayed through the current deterministic pipeline.",
            "credentials": "No credentials or provider error bodies are stored in the frozen inputs.",
        },
        "frozen_inputs_path": INPUTS_PATH.relative_to(ROOT).as_posix(),
        "frozen_inputs_file_sha256": _sha256(INPUTS_PATH.read_bytes()),
        "protected_start_invariants_path": PROTECTED_START_PATH.relative_to(ROOT).as_posix(),
        "protected_start_invariants_sha256": _sha256(PROTECTED_START_PATH.read_bytes()),
        "papers": paper_manifest,
        "runtime_environment_at_freeze": invariants.get("runtime", {}),
    }
    _write_json(MANIFEST_PATH, manifest)
    print(
        json.dumps(
            {
                "frozen_inputs": INPUTS_PATH.relative_to(ROOT).as_posix(),
                "frozen_inputs_sha256": manifest["frozen_inputs_file_sha256"],
                "manifest": MANIFEST_PATH.relative_to(ROOT).as_posix(),
                "papers": [
                    {
                        "paper_id": paper["paper_id"],
                        "entities": paper["ner"]["entity_count"],
                        "relations": paper["relation_baseline"]["relation_count"],
                        "text_sha256": paper["source"]["selected_text_sha256"],
                    }
                    for paper in paper_manifest
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
