"""Exercise candidate persistence and packet assembly without provider access.

The production provider factory is replaced in-process with a deterministic
fake that returns the frozen relations for one paper and emits safe lifecycle
diagnostics. No API client is constructed and no network request is possible.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import build_review_packet
import run_frozen_regression as runner


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _assert_no_sensitive_field(value: Any) -> None:
    forbidden = {"api_key", "authorization", "prompt", "output_text", "raw_error", "raw_response"}
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in forbidden:
                raise AssertionError(f"Sensitive or unbounded field persisted: {key}")
            _assert_no_sensitive_field(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_sensitive_field(child)


def _exercise_environment_loader(temporary_root: Path) -> None:
    """Check environment priority and safe parsing without exposing values."""

    fixture_root = temporary_root / "environment-loader"
    fixture_root.mkdir()
    dotenv_path = fixture_root / ".env"
    dotenv_path.write_text(
        "export OPENAI_API_KEY_ENV='FILE_KEY'\n"
        "export FILE_KEY='file-secret-never-persisted'\n"
        'OPENAI_BASE_URL="https://dotenv.invalid/v1"\n',
        encoding="utf-8-sig",
    )
    original_root = runner.ROOT
    runner.ROOT = fixture_root
    try:
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY_ENV": "CUSTOM_KEY",
                "CUSTOM_KEY": "environment-secret-never-persisted",
                "OPENAI_BASE_URL": "https://environment.invalid/v1",
            },
            clear=False,
        ):
            if runner._environment_value("OPENAI_API_KEY_ENV") != "CUSTOM_KEY":
                raise AssertionError("environment did not override the .env key-variable name")
            if runner._environment_value("OPENAI_BASE_URL") != "https://environment.invalid/v1":
                raise AssertionError("environment did not override the .env base URL")
            config = runner._candidate_config()
            if config.api_key != "environment-secret-never-persisted" or config.api_key_env != "CUSTOM_KEY":
                raise AssertionError("candidate loader did not use its configured environment key")
            if config.base_url != "https://environment.invalid/v1":
                raise AssertionError("candidate loader did not honor the environment base URL")
            if "api_key" in runner._config_record(config):
                raise AssertionError("candidate config report contains an API key field")

        with patch.dict(os.environ, {}, clear=True):
            if runner._environment_value("OPENAI_API_KEY_ENV") != "FILE_KEY":
                raise AssertionError("UTF-8 BOM/export/quoted .env key-name parsing failed")
            if runner._environment_value("FILE_KEY") != "file-secret-never-persisted":
                raise AssertionError("quoted .env API key parsing failed")
            if runner._environment_value("OPENAI_BASE_URL") != "https://dotenv.invalid/v1":
                raise AssertionError("quoted .env base URL parsing failed")
            config = runner._candidate_config()
            if config.api_key != "file-secret-never-persisted" or config.api_key_env != "FILE_KEY":
                raise AssertionError("candidate loader did not resolve the .env custom key")
            if config.base_url != "https://dotenv.invalid/v1":
                raise AssertionError("candidate loader did not honor the .env base URL")

            dotenv_path.write_text("OPENAI_API_KEY_ENV=MISSING_KEY\n", encoding="utf-8")
            if runner._environment_value("MISSING_KEY") is not None:
                raise AssertionError("missing credential was not reported as unavailable")
            try:
                runner._candidate_config()
            except RuntimeError:
                pass
            else:
                raise AssertionError("candidate loader accepted a missing credential")
    finally:
        runner.ROOT = original_root


def main() -> None:
    from biomedical_extractor.llm_relation_extraction import LLMRelationExtractor, OpenAIConfig
    from biomedical_extractor.relation_extraction import Relation, RelationExtractionResult

    frozen = runner._verify_frozen_inputs()
    paper = frozen["papers"][0]
    original_output_root = runner.OUTPUT_ROOT
    original_config_factory = runner._candidate_config
    original_from_openai = LLMRelationExtractor.__dict__["from_openai"]

    with tempfile.TemporaryDirectory(
        prefix="contract12a-fake-", dir=original_output_root
    ) as temporary:
        temporary_root = Path(temporary)
        _exercise_environment_loader(temporary_root)
        cache_root = temporary_root / "cache"
        report_root = temporary_root / "report"
        cache_root.mkdir()
        report_root.mkdir()
        for name in ("frozen_inputs.json", "frozen_set_manifest.json"):
            shutil.copyfile(runner.ROOT / "reports/relation_migration_12a" / name, report_root / name)

        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key="fake-key-never-used",
            reasoning_effort="medium",
            max_completion_tokens=128000,
            max_retries=2,
            background=True,
            service_tier="default",
            poll_interval_seconds=3.0,
            generation_timeout_seconds=900.0,
        )
        runner.OUTPUT_ROOT = cache_root
        runner._candidate_config = lambda: config

        class FakeRelationExtractor:
            def __init__(self, diagnostics_callback: Any) -> None:
                self.diagnostics_callback = diagnostics_callback
                self.last_generation_diagnostics: tuple[dict[str, Any], ...] = ()

            def extract_relations(self, text: str, entities: Any) -> Any:
                if text != paper["source"]["source_text"]:
                    raise AssertionError("fake received non-frozen text")
                if [entity.to_dict() for entity in entities] != paper["entities"]:
                    raise AssertionError("fake received non-frozen entity packet")
                snapshots = (
                    {
                        "generation_number": 1,
                        "repair": False,
                        "execution_mode": "background",
                        "status": "processing",
                        "response_id": "resp_fake_contract12a_001",
                        "requested_background": True,
                        "observed_background": True,
                        "requested_model": "gpt-6.1-sol",
                        "observed_model": "gpt-6.1-sol",
                        "requested_reasoning_effort": "medium",
                        "observed_reasoning_effort": "medium",
                        "requested_service_tier": "default",
                        "observed_service_tier": "default",
                        "poll_count": 1,
                        "poll_errors": 0,
                    },
                    {
                        "generation_number": 1,
                        "repair": False,
                        "execution_mode": "background",
                        "status": "validated",
                        "terminal_status": "completed",
                        "response_id": "resp_fake_contract12a_001",
                        "requested_background": True,
                        "observed_background": True,
                        "requested_model": "gpt-6.1-sol",
                        "observed_model": "gpt-6.1-sol",
                        "requested_reasoning_effort": "medium",
                        "observed_reasoning_effort": "medium",
                        "requested_service_tier": "default",
                        "observed_service_tier": "default",
                        "elapsed_seconds": 0.25,
                        "poll_count": 1,
                        "poll_errors": 0,
                        "input_tokens": 2500,
                        "output_tokens": 400,
                        "reasoning_tokens": 175,
                        "validated_relation_count": len(paper["baseline_relations"]),
                    },
                )
                for snapshot in snapshots:
                    self.diagnostics_callback(snapshot)
                self.last_generation_diagnostics = (snapshots[-1],)
                return RelationExtractionResult(
                    Relation(**value) for value in paper["baseline_relations"]
                )

        def fake_factory(cls: Any, received_config: Any, diagnostics_callback: Any = None) -> Any:
            if received_config is not config:
                raise AssertionError("runner did not pass the frozen candidate config")
            return FakeRelationExtractor(diagnostics_callback)

        LLMRelationExtractor.from_openai = classmethod(fake_factory)
        try:
            runner._run_candidate({**frozen, "papers": [paper]})
        finally:
            LLMRelationExtractor.from_openai = original_from_openai
            runner._candidate_config = original_config_factory
            runner.OUTPUT_ROOT = original_output_root

        candidate_root = cache_root
        candidate_result_path = candidate_root / "candidate" / paper["slug"] / "result.json"
        attempt_path = candidate_root / "candidate" / paper["slug"] / "attempt.json"
        candidate = json.loads(candidate_result_path.read_text(encoding="utf-8"))
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        baseline = json.loads(
            (original_output_root / "baseline" / paper["slug"] / "result.json").read_text(encoding="utf-8")
        )
        if _canonical(candidate["relations"]) != _canonical(baseline["relations"]):
            raise AssertionError("fake candidate relation output does not equal frozen replay")
        if _canonical(candidate["graph"]) != _canonical(baseline["graph"]):
            raise AssertionError("fake candidate graph does not equal current-pipeline control")
        if attempt.get("last_response_id") != "resp_fake_contract12a_001":
            raise AssertionError("response ID was not durably persisted in the attempt record")
        if len(attempt.get("diagnostic_events", [])) != 2:
            raise AssertionError("safe callback snapshots were not durably persisted")
        _assert_no_sensitive_field(attempt)
        _assert_no_sensitive_field(candidate)

        packet = build_review_packet.build(
            candidate_root,
            report_root,
            baseline_root=original_output_root,
        )
        if packet["papers"][0]["status"] != "compared":
            raise AssertionError("review packet did not compare the fake candidate paper")
        telemetry = json.loads((report_root / "telemetry.json").read_text(encoding="utf-8"))
        paper_telemetry = telemetry["papers"][0]
        if paper_telemetry["response_ids"] != ["resp_fake_contract12a_001"]:
            raise AssertionError("review packet lost the safe response ID telemetry")
        if len(paper_telemetry["diagnostic_events"]) != 2:
            raise AssertionError("review packet lost safe provider lifecycle events")
        if paper_telemetry["input_tokens"] != 2500 or paper_telemetry["output_tokens"] != 400:
            raise AssertionError("review packet lost token telemetry")
        semantic_output = json.loads(
            (report_root / "papers" / f"{paper['slug']}.json").read_text(encoding="utf-8")
        )
        graph_delta = semantic_output["graphs"]["delta"]
        if graph_delta["edge_identity_multiset"]["baseline_only"] or graph_delta["edge_identity_multiset"]["candidate_only"]:
            raise AssertionError("identical fake outputs produced an edge identity delta")
        if not graph_delta["node_ids"]["identities_preserved"]:
            raise AssertionError("identical fake outputs did not preserve node IDs")
        if not semantic_output["graphs"]["candidate_overview"]["rich_evidence_propagation"]["exact_match"]:
            raise AssertionError("review packet did not preserve exact unique graph evidence")
        if not semantic_output["graphs"]["delta"]["archived_contract_10_graph"]["same_entities_and_edges_ignoring_paper_roles"]:
            raise AssertionError("archive provenance comparison did not isolate stored role annotations")
        _assert_no_sensitive_field(telemetry)
        _assert_no_sensitive_field(semantic_output)

        # Duplicate matching and changed rich fields must stay distinct.
        relation = {"source": "a", "target": "b", "predicate": "activates", "evidence": "x", "score": 0.8}
        changed = {**relation, "evidence": "y", "score": 0.7}
        field_delta = build_review_packet._relation_field_differences(
            [relation, relation], [relation, changed]
        )
        if len(field_delta["matched_changed_records"]) != 1 or field_delta["unpaired_baseline_records"] or field_delta["unpaired_candidate_records"]:
            raise AssertionError("relation rich-field delta pairing mishandled duplicate records")

        shared_evidence = {
            "assertion": "A regulates B",
            "evidence": "A regulates B",
            "intervention": None,
            "effects": [],
            "context": [],
            "surface_form": None,
            "score": 0.8,
        }
        mention_relations = [
            {
                "source": "mention_a1",
                "target": "mention_b",
                "predicate": "regulates",
                "negated": False,
                **shared_evidence,
            },
            {
                "source": "mention_a2",
                "target": "mention_b",
                "predicate": "regulates",
                "negated": False,
                **shared_evidence,
            },
        ]
        collapsed_graph = {
            "nodes": [
                {"id": "node_a", "mentions": [{"id": "mention_a1"}, {"id": "mention_a2"}]},
                {"id": "node_b", "mentions": [{"id": "mention_b"}]},
            ],
            "edges": [
                {
                    "id": "edge_1",
                    "source": "node_a",
                    "target": "node_b",
                    "predicate": "regulates",
                    "negated": False,
                    "evidence": [
                        {
                            key: value
                            for key, value in shared_evidence.items()
                            if key != "evidence"
                        }
                        | {"text": shared_evidence["evidence"]}
                    ],
                }
            ],
        }
        collapsed_overview = build_review_packet._graph_overview(
            collapsed_graph, mention_relations
        )
        propagation = collapsed_overview["rich_evidence_propagation"]
        if (
            propagation["collapsed_duplicate_relation_evidence_records"] != 1
            or propagation["unique_projected_relation_evidence_records"] != 1
            or not propagation["exact_match"]
        ):
            raise AssertionError("projected mention duplicates were counted as lost unique graph evidence")

        print(
            json.dumps(
                {
                    "status": "fake_candidate_smoke_passed",
                    "paper_id": paper["paper_id"],
                    "relation_count": len(candidate["relations"]),
                    "node_count": len(candidate["graph"]["nodes"]),
                    "edge_count": len(candidate["graph"]["edges"]),
                    "persisted_response_id": attempt["last_response_id"],
                    "packet_status": packet["papers"][0]["status"],
                    "network_calls": 0,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
