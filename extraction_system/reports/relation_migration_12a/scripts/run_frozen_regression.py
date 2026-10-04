"""Serial Contract 12A graph-regression runner.

``baseline`` replays saved Contract 10 relations through the current production
pipeline with the exact frozen entity packet. ``candidate`` uses the same entity
packet and the real ``LLMRelationExtractor.from_openai`` production boundary.
Candidate calls are single-run only: durable attempt records prevent accidental
duplicate submissions after interruption or a lost response acknowledgement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[3]
GIT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

FROZEN_INPUTS_PATH = ROOT / "reports/relation_migration_12a/frozen_inputs.json"
MANIFEST_PATH = ROOT / "reports/relation_migration_12a/frozen_set_manifest.json"
PROTECTED_START_PATH = ROOT / "reports/relation_migration_12a/protected_start_invariants.json"
OUTPUT_ROOT = ROOT / ".cache/relation_migration_12a"
STOP_AFTER_CONSECUTIVE_PROVIDER_FAILURES = 2
DIAGNOSTIC_FIELDS = frozenset(
    {
        "generation_number",
        "repair",
        "execution_mode",
        "status",
        "response_id",
        "requested_background",
        "observed_background",
        "requested_model",
        "observed_model",
        "requested_reasoning_effort",
        "observed_reasoning_effort",
        "requested_service_tier",
        "observed_service_tier",
        "elapsed_seconds",
        "poll_count",
        "poll_errors",
        "last_poll_error_type",
        "last_poll_http_status",
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "error_type",
        "http_status",
        "provider_error_type",
        "provider_error_code",
        "incomplete_reason",
        "initial_status",
        "initial_create_latency_seconds",
        "terminal_status",
        "cancel_attempted",
        "cancel_status",
        "cancel_response_id",
        "cancel_error_type",
        "diagnostics_callback_error_type",
        "validated_relation_count",
        "output_error_type",
        "response_id_mismatch",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _atomic_json(path: Path, value: Any) -> None:
    """Persist a complete JSON snapshot with one atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sanitize_diagnostic(value: Any) -> dict[str, Any]:
    """Copy only safe scalar telemetry fields from provider diagnostics."""

    if not isinstance(value, dict):
        return {"status": "diagnostic_snapshot_invalid"}
    copied: dict[str, Any] = {}
    for key in DIAGNOSTIC_FIELDS:
        item = value.get(key)
        if item is None or isinstance(item, (str, int, float, bool)):
            if key in value:
                copied[key] = item
    return copied


def _failure_category(error: Exception, diagnostics: tuple[dict[str, Any], ...]) -> tuple[str, bool]:
    """Classify a bounded provider failure without persisting its raw message."""

    from biomedical_extractor.relation_extraction import RelationExtractionError

    if not isinstance(error, RelationExtractionError) or not diagnostics:
        return "runner_or_setup_failure", False
    last_status = diagnostics[-1].get("status")
    if last_status == "output_invalid":
        return "invalid_structured_output_after_bounded_repairs", True
    if last_status in {
        "create_failed",
        "provider_failed",
        "provider_cancelled",
        "provider_incomplete",
        "timeout",
        "interrupted",
        "polling_failed",
        "missing_response_id",
        "response_id_mismatch",
        "missing_output",
    }:
        return f"responses_lifecycle_{last_status}", True
    return "relation_generation_failed", True


def _verify_frozen_inputs() -> dict[str, Any]:
    """Check self-contained inputs against their frozen hashes and spans."""

    inputs = _read_json(FROZEN_INPUTS_PATH)
    manifest = _read_json(MANIFEST_PATH)
    actual_sha = _sha256(FROZEN_INPUTS_PATH.read_bytes())
    if actual_sha != manifest.get("frozen_inputs_file_sha256"):
        raise RuntimeError("Frozen input file checksum does not match its manifest")
    if inputs.get("system_prompt_sha256") != manifest["historical_equivalence"]["system_prompt_sha256"]:
        raise RuntimeError("Frozen system prompt hash differs between input and manifest")
    if inputs.get("semantic_schema_sha256") != manifest["historical_equivalence"]["semantic_schema_sha256"]:
        raise RuntimeError("Frozen semantic schema hash differs between input and manifest")

    paper_rows = {row["paper_id"]: row for row in manifest["papers"]}
    for paper in inputs["papers"]:
        row = paper_rows.get(paper["paper_id"])
        if row is None:
            raise RuntimeError(f"Paper missing from frozen manifest: {paper['paper_id']}")
        source = paper["source"]
        entities = paper["entities"]
        relations = paper["baseline_relations"]
        if _sha256(source["source_text"].encode("utf-8")) != row["source"]["selected_text_sha256"]:
            raise RuntimeError(f"Frozen source changed for {paper['paper_id']}")
        if _sha256(_canonical_json(entities)) != row["ner"]["entities_canonical_sha256"]:
            raise RuntimeError(f"Frozen entities changed for {paper['paper_id']}")
        if _sha256(_canonical_json(relations)) != row["relation_baseline"]["relations_canonical_sha256"]:
            raise RuntimeError(f"Frozen baseline relations changed for {paper['paper_id']}")
        for entity in entities:
            if source["source_text"][entity["start"] : entity["end"]] != entity["text"]:
                raise RuntimeError(f"Frozen entity source span changed for {paper['paper_id']}")
    return inputs


def _verify_frozen_paper(paper: dict[str, Any]) -> None:
    """Recheck the exact submitted source/entity packet before each paper."""

    manifest = _read_json(MANIFEST_PATH)
    row = next(item for item in manifest["papers"] if item["paper_id"] == paper["paper_id"])
    source = paper["source"]["source_text"]
    if _sha256(source.encode("utf-8")) != row["source"]["selected_text_sha256"]:
        raise RuntimeError(f"Frozen source changed before submission for {paper['paper_id']}")
    if _sha256(_canonical_json(paper["entities"])) != row["ner"]["entities_canonical_sha256"]:
        raise RuntimeError(f"Frozen entity packet changed before submission for {paper['paper_id']}")
    if _sha256(_canonical_json(paper["baseline_relations"])) != row["relation_baseline"]["relations_canonical_sha256"]:
        raise RuntimeError(f"Frozen baseline relations changed before submission for {paper['paper_id']}")


def _runtime_semantic_controls(inputs: dict[str, Any]) -> dict[str, str]:
    """Hash the effective runtime prompt and semantic schema before a request."""

    from biomedical_extractor.llm_relation_extraction import (
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _structured_payload_schema,
    )

    prompt_sha = _sha256(RELATION_EXTRACTION_SYSTEM_PROMPT.encode("utf-8"))
    schema_model = _structured_payload_schema()
    schema_value = (
        schema_model.model_json_schema()
        if callable(getattr(schema_model, "model_json_schema", None))
        else schema_model.schema()
    )
    schema_sha = _sha256(_canonical_json(schema_value))
    if prompt_sha != inputs["system_prompt_sha256"]:
        raise RuntimeError("Runtime system prompt differs from frozen Contract 10 semantics")
    if schema_sha != inputs["semantic_schema_sha256"]:
        raise RuntimeError("Runtime semantic relation schema differs from frozen Contract 10 semantics")
    return {
        "system_prompt_sha256": prompt_sha,
        "semantic_schema_sha256": schema_sha,
    }


def _verify_protected_checkout() -> None:
    """Ensure graph inputs and assembly still match the pre-integration freeze."""

    import subprocess

    if not PROTECTED_START_PATH.exists():
        raise RuntimeError("The protected starting invariant record is missing")
    manifest = _read_json(MANIFEST_PATH)
    if _sha256(PROTECTED_START_PATH.read_bytes()) != manifest.get(
        "protected_start_invariants_sha256"
    ):
        raise RuntimeError("Tracked protected starting invariants failed their manifest hash")
    invariants = _read_json(PROTECTED_START_PATH)
    if invariants.get("baseline_sha") != "96b8312879b337c57aba51342676890602b5c30d":
        raise RuntimeError("The protected starting invariant record has a different baseline SHA")
    for relative, expected in invariants.get("protected_sha256", {}).items():
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"Protected file is missing: {relative}")
        if _sha256(path.read_bytes()) != expected:
            raise RuntimeError(f"Protected file changed during provider integration: {relative}")
    head = subprocess.check_output(
        [
            "git",
            "-c",
            "safe.directory=C:/Projects/Biomed",
            "-C",
            str(GIT_ROOT),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()
    if head != invariants["baseline_sha"]:
        raise RuntimeError("Candidate graph replay must start from the frozen baseline HEAD")


class _FrozenEntityExtractor:
    """Supply the frozen Contract 10 mentions without rerunning NER."""

    def __init__(self, expected_text: str, entities: list[Any]) -> None:
        self._expected_text = expected_text
        self._entities = tuple(entities)

    def extract_entities(self, text: str) -> tuple[Any, ...]:
        if text != self._expected_text:
            raise RuntimeError("The pipeline requested entities for a different source text")
        return self._entities


class _FrozenRelationExtractor:
    """Return the previously validated Contract 10 relation output."""

    def __init__(self, expected_text: str, expected_entities: tuple[Any, ...], relations: list[Any]) -> None:
        self._expected_text = expected_text
        self._expected_entities = tuple(entity.to_dict() for entity in expected_entities)
        self._result = relations
        self.last_result: Any = None

    def extract_relations(self, text: str, entities: Any) -> Any:
        from biomedical_extractor.relation_extraction import RelationExtractionResult

        if text != self._expected_text:
            raise RuntimeError("Baseline relation replay received different source text")
        if [entity.to_dict() for entity in entities] != list(self._expected_entities):
            raise RuntimeError("Baseline relation replay received a different entity packet")
        self.last_result = RelationExtractionResult(self._result)
        return self.last_result


class _RecordingRelationExtractor:
    """Record normalized relation values returned through the provider seam."""

    def __init__(self, extractor: Any) -> None:
        self.extractor = extractor
        self.last_result: Any = None

    def extract_relations(self, text: str, entities: Any) -> Any:
        self.last_result = self.extractor.extract_relations(text, entities)
        return self.last_result


def _environment_value(name: str) -> str | None:
    """Read environment first, then the established simple repository .env format."""

    value = os.getenv(name)
    if value:
        return value
    dotenv_path = ROOT / ".env"
    if dotenv_path.is_file():
        for line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
            key, separator, candidate = line.strip().removeprefix("export ").partition("=")
            if separator and key.strip() == name:
                return candidate.strip().strip("\"'") or None
    return None


def _candidate_config() -> Any:
    """Build the explicit candidate config without logging credential values."""

    from biomedical_extractor.llm_relation_extraction import OpenAIConfig

    api_key_env = _environment_value("OPENAI_API_KEY_ENV") or "OPENAI_API_KEY"
    api_key = _environment_value(api_key_env)
    if not api_key:
        raise RuntimeError("OpenAI credentials are unavailable in the configured environment or repository .env")

    config = OpenAIConfig.from_environment()
    base_url = config.base_url or _environment_value("OPENAI_BASE_URL")
    return replace(
        config,
        model="gpt-6.1-sol",
        api_key_env=api_key_env,
        api_key=api_key,
        base_url=base_url,
        reasoning_effort="medium",
        max_completion_tokens=128000,
        max_retries=2,
        background=True,
        service_tier="default",
        poll_interval_seconds=3.0,
        generation_timeout_seconds=900.0,
    )


def _config_record(config: Any) -> dict[str, Any]:
    return {
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "service_tier": config.service_tier,
        "service_label": "Standard" if config.service_tier == "default" else None,
        "background": config.background,
        "max_completion_tokens": config.max_completion_tokens,
        "max_retries": config.max_retries,
        "poll_interval_seconds": config.poll_interval_seconds,
        "generation_timeout_seconds": config.generation_timeout_seconds,
    }


def _load_models(paper: dict[str, Any], mode: str, config: Any = None, callback: Callable[[dict[str, Any]], None] | None = None) -> tuple[Any, Any]:
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
    from biomedical_extractor.llm_relation_extraction import LLMRelationExtractor
    from biomedical_extractor.relation_extraction import Relation

    source_text = paper["source"]["source_text"]
    entities = tuple(Entity(**value) for value in paper["entities"])
    entity_extractor = _FrozenEntityExtractor(source_text, entities)
    if mode == "baseline":
        relations = [Relation(**value) for value in paper["baseline_relations"]]
        relation_extractor = _FrozenRelationExtractor(source_text, entities, relations)
    else:
        relation_extractor = LLMRelationExtractor.from_openai(
            config,
            diagnostics_callback=callback,
        )
    recording = _RecordingRelationExtractor(relation_extractor)
    return LLMExtractionPipeline(entity_extractor, recording), recording


def _paper_record(paper: dict[str, Any], attempt_id: str | None = None) -> dict[str, Any]:
    return {
        "contract": "12A",
        "paper_id": paper["paper_id"],
        "slug": paper["slug"],
        "source_sha256": paper["source"]["selected_source_sha256"],
        "entity_count": len(paper["entities"]),
        "entity_packet_sha256": _sha256(_canonical_json(paper["entities"])),
        "attempt_id": attempt_id,
    }


def _run_baseline(inputs: dict[str, Any]) -> None:
    run_path = OUTPUT_ROOT / "baseline_run.json"
    if run_path.exists():
        raise RuntimeError("Baseline replay already exists; refusing to overwrite it")
    _verify_protected_checkout()
    state = {
        "contract": "12A",
        "mode": "baseline",
        "status": "in_progress",
        "started_at_utc": _utc_now(),
        "papers": [],
    }
    _atomic_json(run_path, state)
    for paper in inputs["papers"]:
        _verify_frozen_paper(paper)
        controls = _runtime_semantic_controls(inputs)
        output_dir = OUTPUT_ROOT / "baseline" / paper["slug"]
        output_path = output_dir / "result.json"
        if output_path.exists():
            raise RuntimeError(f"Baseline output already exists for {paper['paper_id']}")
        pipeline, recording = _load_models(paper, "baseline")
        started = time.perf_counter()
        graph = pipeline.extract_graph(
            paper["source"]["source_text"],
            document_id=paper["paper_id"],
            paper_title=paper["title"],
        )
        relation_result = recording.last_result
        if relation_result is None:
            raise RuntimeError(f"Baseline pipeline returned no relations for {paper['paper_id']}")
        record = {
            **_paper_record(paper),
            "status": "success",
            "execution": "saved_contract_10_relations_replayed_through_current_extract_graph",
            "semantic_controls": controls,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "relations": [item.to_dict() for item in relation_result.relations],
            "graph": graph.to_dict(),
        }
        _atomic_json(output_path, record)
        state["papers"].append({"paper_id": paper["paper_id"], "status": record["status"]})
        _atomic_json(run_path, state)
        print(f"[baseline] {paper['paper_id']}: {len(record['relations'])} relations, {len(record['graph']['nodes'])} nodes, {len(record['graph']['edges'])} edges")
    state.update({"status": "complete", "completed_at_utc": _utc_now()})
    _atomic_json(run_path, state)


def _run_candidate(inputs: dict[str, Any]) -> None:
    run_path = OUTPUT_ROOT / "candidate_run.json"
    if run_path.exists():
        raise RuntimeError("Candidate run record already exists; refusing a duplicate provider submission")
    for paper in inputs["papers"]:
        if (OUTPUT_ROOT / "candidate" / paper["slug"] / "attempt.json").exists():
            raise RuntimeError(f"Candidate attempt already exists for {paper['paper_id']}; audit it before any new run")

    _verify_protected_checkout()
    config = _candidate_config()
    if (
        config.model != "gpt-6.1-sol"
        or config.reasoning_effort != "medium"
        or config.service_tier != "default"
        or config.background is not True
        or config.max_retries != 2
    ):
        raise RuntimeError("Candidate configuration does not match the frozen Contract 12A selection")

    state = {
        "contract": "12A",
        "mode": "candidate",
        "status": "in_progress",
        "started_at_utc": _utc_now(),
        "configuration": _config_record(config),
        "papers": [],
        "stop_after_consecutive_provider_failures": STOP_AFTER_CONSECUTIVE_PROVIDER_FAILURES,
    }
    _atomic_json(run_path, state)
    consecutive_provider_failures = 0
    any_provider_failure = False

    for index, paper in enumerate(inputs["papers"]):
        try:
            _verify_protected_checkout()
            _verify_frozen_paper(paper)
            semantic_controls = _runtime_semantic_controls(inputs)
        except Exception as error:
            state["papers"].append(
                {
                    "paper_id": paper["paper_id"],
                    "status": "not_run_contract_preflight_failed",
                    "error_class": type(error).__name__,
                }
            )
            for remaining in inputs["papers"][index + 1 :]:
                state["papers"].append(
                    {"paper_id": remaining["paper_id"], "status": "not_run_after_contract_preflight_failure"}
                )
            state.update({"status": "stopped_contract_preflight_failure", "completed_at_utc": _utc_now()})
            _atomic_json(run_path, state)
            break

        output_dir = OUTPUT_ROOT / "candidate" / paper["slug"]
        output_dir.mkdir(parents=True, exist_ok=True)
        attempt_path = output_dir / "attempt.json"
        if attempt_path.exists():
            raise RuntimeError(f"Candidate attempt already exists for {paper['paper_id']}; refusing to launch it again")

        callback_events: list[dict[str, Any]] = []
        attempt_id = f"contract12a-candidate-{index + 1:02d}"
        attempt = {
            **_paper_record(paper, attempt_id),
            "status": "launch_started",
            "started_at_utc": _utc_now(),
            "configuration": _config_record(config),
            "semantic_controls": semantic_controls,
            "diagnostic_events": callback_events,
        }
        # This durable record precedes client construction and the first request.
        _atomic_json(attempt_path, attempt)

        def save_diagnostic(snapshot: dict[str, Any]) -> None:
            safe = _sanitize_diagnostic(snapshot)
            callback_events.append({"recorded_at_utc": _utc_now(), **safe})
            attempt["status"] = "provider_progress"
            attempt["diagnostic_events"] = callback_events
            if safe.get("response_id"):
                attempt["last_response_id"] = safe["response_id"]
            _atomic_json(attempt_path, attempt)

        pipeline = None
        recording = None
        started = time.perf_counter()
        try:
            pipeline, recording = _load_models(paper, "candidate", config, save_diagnostic)
            graph = pipeline.extract_graph(
                paper["source"]["source_text"],
                document_id=paper["paper_id"],
                paper_title=paper["title"],
            )
            relation_result = recording.last_result
            if relation_result is None:
                raise RuntimeError("Candidate pipeline returned no relation result")
            relation_model = recording.extractor
            diagnostics = tuple(
                _sanitize_diagnostic(value)
                for value in getattr(relation_model, "last_generation_diagnostics", ())
            )
            if diagnostics:
                attempt["final_generation_diagnostics"] = list(diagnostics)
            record = {
                **_paper_record(paper, attempt_id),
                "status": "success",
                "started_at_utc": attempt["started_at_utc"],
                "completed_at_utc": _utc_now(),
                "elapsed_seconds": round(time.perf_counter() - started, 6),
                "configuration": _config_record(config),
                "semantic_controls": semantic_controls,
                "generation_diagnostics": list(diagnostics),
                "generation_attempts": len(diagnostics),
                "repair_attempts": max(0, len(diagnostics) - 1),
                "relations": [item.to_dict() for item in relation_result.relations],
                "graph": graph.to_dict(),
            }
            _atomic_json(output_dir / "result.json", record)
            attempt.update(
                {
                    "status": "success",
                    "completed_at_utc": record["completed_at_utc"],
                    "elapsed_seconds": record["elapsed_seconds"],
                    "final_generation_diagnostics": list(diagnostics),
                }
            )
            _atomic_json(attempt_path, attempt)
            consecutive_provider_failures = 0
        except Exception as error:
            relation_model = recording.extractor if recording is not None else None
            diagnostics = tuple(
                _sanitize_diagnostic(value)
                for value in getattr(relation_model, "last_generation_diagnostics", ())
            )
            if diagnostics:
                attempt["final_generation_diagnostics"] = list(diagnostics)
            failure_category, provider_failure = _failure_category(error, diagnostics)
            any_provider_failure = any_provider_failure or provider_failure
            attempt.update(
                {
                    "status": "provider_failed" if provider_failure else "run_failed",
                    "completed_at_utc": _utc_now(),
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                    "error_class": type(error).__name__,
                    "failure_category": failure_category,
                    "last_diagnostic_status": diagnostics[-1].get("status") if diagnostics else None,
                }
            )
            _atomic_json(attempt_path, attempt)
            state["papers"].append(
                {
                    "paper_id": paper["paper_id"],
                    "status": attempt["status"],
                    "attempt_id": attempt_id,
                }
            )
            _atomic_json(run_path, state)
            if not provider_failure:
                for remaining in inputs["papers"][index + 1 :]:
                    state["papers"].append(
                        {"paper_id": remaining["paper_id"], "status": "not_run_after_non_provider_failure"}
                    )
                state.update({"status": "stopped_on_non_provider_failure", "completed_at_utc": _utc_now()})
                _atomic_json(run_path, state)
                break
            consecutive_provider_failures += 1
            if consecutive_provider_failures >= STOP_AFTER_CONSECUTIVE_PROVIDER_FAILURES:
                for remaining in inputs["papers"][index + 1 :]:
                    state["papers"].append(
                        {"paper_id": remaining["paper_id"], "status": "not_run_after_provider_stop_condition"}
                    )
                state.update({"status": "stopped_after_consecutive_provider_failures", "completed_at_utc": _utc_now()})
                _atomic_json(run_path, state)
                break
            continue

        state["papers"].append(
            {"paper_id": paper["paper_id"], "status": "success", "attempt_id": attempt_id}
        )
        _atomic_json(run_path, state)
        print(f"[candidate] {paper['paper_id']}: completed in {attempt['elapsed_seconds']:.1f}s")

    if state["status"] == "in_progress":
        state.update(
            {
                "status": "complete_with_provider_failures" if any_provider_failure else "complete",
                "completed_at_utc": _utc_now(),
            }
        )
    _atomic_json(run_path, state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "candidate"), required=True)
    args = parser.parse_args()

    inputs = _verify_frozen_inputs()
    if args.mode == "baseline":
        _run_baseline(inputs)
    else:
        _run_candidate(inputs)


if __name__ == "__main__":
    main()
