"""Execute the frozen, blinded Contract 11 relation-model comparison.

This benchmark-only runner reuses the Contract 10 prompt, structured schema,
validator, and graph builder. It records provider accounting without retaining
provider response objects or exposing the blinded model key in run artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


REPOSITORY = Path(__file__).resolve().parents[3]
REPORT = REPOSITORY / "reports" / "luna_56_vs_6_fullpaper_11"
BENCHMARK_CACHE = REPOSITORY / ".cache" / "model_ab_11"
CORPUS_PATH = REPOSITORY / ".cache" / "ner_target_domain" / "target_corpus.json"
KEY_PATH = BENCHMARK_CACHE / "model_key.json"
LOCK_PATH = REPORT / "preflight.json"
EXPECTED_HEAD = "1f12923ce54ab6718a00b8d8e8126536285dc6a8"
PAPER_ORDER = (
    "PMCID:PMC10770459",
    "PMCID:PMC11824863",
    "PMCID:PMC8605525",
)
EXECUTION_ORDER = (
    ("PMCID:PMC10770459", "Model A", 1),
    ("PMCID:PMC10770459", "Model B", 1),
    ("PMCID:PMC10770459", "Model B", 2),
    ("PMCID:PMC10770459", "Model A", 2),
    ("PMCID:PMC11824863", "Model B", 1),
    ("PMCID:PMC11824863", "Model A", 1),
    ("PMCID:PMC11824863", "Model A", 2),
    ("PMCID:PMC11824863", "Model B", 2),
    ("PMCID:PMC8605525", "Model A", 1),
    ("PMCID:PMC8605525", "Model B", 1),
    ("PMCID:PMC8605525", "Model B", 2),
    ("PMCID:PMC8605525", "Model A", 2),
)


def sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of exact serialized bytes."""

    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> str:
    """Serialize a value consistently for exact comparison and hashing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_json(path: Path, value: Any) -> None:
    """Atomically write one UTF-8 JSON artifact with a final newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def slug(paper_id: str) -> str:
    """Return the stable report directory name for one paper ID."""

    return "pmcid_" + paper_id.split(":", 1)[1].lower()


def load_key() -> dict[str, str]:
    """Read the separately stored actual-model mapping without printing it."""

    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    if (
        not isinstance(key, Mapping)
        or set(key) != {"model_a", "model_b"}
        or not all(isinstance(value, str) and value.strip() for value in key.values())
        or key["model_a"] == key["model_b"]
    ):
        raise RuntimeError("The separate blinded model key is invalid")
    return {"Model A": key["model_a"], "Model B": key["model_b"]}


def read_env_value(name: str) -> str | None:
    """Read one requested dotenv value without loading or printing other secrets."""

    process_value = os.environ.get(name)
    if process_value:
        return process_value
    dotenv = REPOSITORY / ".env"
    if not dotenv.is_file():
        return None
    for raw_line in dotenv.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator or key.strip() != name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value or None
    return None


def redact_error(message: str, api_key: str) -> str:
    """Remove credentials and bearer values from failure diagnostics."""

    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = re.sub(r"sk-[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
    message = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)
    return message[:1200]


def response_mapping(response: Any) -> Mapping[str, Any] | None:
    """Read a structured output mapping without changing the returned object."""

    if isinstance(response, Mapping):
        return response
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        value = dump()
        return value if isinstance(value, Mapping) else None
    dump = getattr(response, "dict", None)
    if callable(dump):
        value = dump()
        return value if isinstance(value, Mapping) else None
    return None


def response_duplicate_count(response: Any) -> tuple[int | None, int | None]:
    """Count duplicate structured relations before the domain seam removes them."""

    mapping = response_mapping(response)
    if mapping is None:
        return None, None
    relations = mapping.get("relations")
    if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
        return None, None
    keys = [canonical_json(item) for item in relations]
    return len(relations), len(keys) - len(set(keys))


class UsageRecorder(BaseCallbackHandler):
    """Record provider timing and token counts from LangChain callbacks."""

    def __init__(self) -> None:
        super().__init__()
        self.started: dict[str, float] = {}
        self.events: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []

    def on_chat_model_start(
        self,
        serialized: Mapping[str, Any],
        messages: Sequence[Sequence[Any]],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        del serialized, messages, kwargs
        self.started[str(run_id)] = time.perf_counter()

    def on_llm_start(
        self,
        serialized: Mapping[str, Any],
        prompts: Sequence[str],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        del serialized, prompts, kwargs
        self.started.setdefault(str(run_id), time.perf_counter())

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        del kwargs
        self._finish(str(run_id), response=response, error=None)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        del kwargs
        self._finish(str(run_id), response=None, error=error)

    def _finish(
        self,
        run_id: str,
        *,
        response: Any,
        error: BaseException | None,
    ) -> None:
        started = self.started.pop(run_id, None)
        usage = extract_token_usage(response) if response is not None else None
        self.events.append(
            {
                "callback_run_id": run_id,
                "status": "error" if error is not None else "response_received",
                "provider_latency_ms": (
                    round((time.perf_counter() - started) * 1000, 3)
                    if started is not None
                    else None
                ),
                "token_usage": usage,
                "error_type": type(error).__name__ if error is not None else None,
            }
        )


def extract_token_usage(response: Any) -> dict[str, int] | None:
    """Return normalized token totals without retaining provider metadata."""

    mappings: list[Mapping[str, Any]] = []
    llm_output = getattr(response, "llm_output", None)
    if isinstance(llm_output, Mapping):
        token_usage = llm_output.get("token_usage")
        if isinstance(token_usage, Mapping):
            mappings.append(token_usage)
    for generations in getattr(response, "generations", ()) or ():
        for generation in generations or ():
            message = getattr(generation, "message", None)
            metadata = getattr(message, "usage_metadata", None)
            if isinstance(metadata, Mapping):
                mappings.append(metadata)
    if not mappings:
        return None

    def first_integer(keys: Sequence[str]) -> int | None:
        for mapping in mappings:
            for key in keys:
                value = mapping.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    return value
        return None

    result = {
        "input_tokens": first_integer(("input_tokens", "prompt_tokens")),
        "output_tokens": first_integer(("output_tokens", "completion_tokens")),
        "total_tokens": first_integer(("total_tokens",)),
    }
    if all(value is None for value in result.values()):
        return None
    return {key: value for key, value in result.items() if value is not None}


class RecordingRunnable:
    """Measure one unchanged structured-model invocation and its response shape."""

    def __init__(self, inner: Any, recorder: UsageRecorder) -> None:
        self.inner = inner
        self.recorder = recorder

    def invoke(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        callbacks_before = len(self.recorder.events)
        attempt_index = len(self.recorder.calls) + 1
        repair = isinstance(value, str) and "REPAIR INSTRUCTION:\n" in value
        entry: dict[str, Any] = {
            "attempt": attempt_index,
            "repair": repair,
            "status": "started",
            "prompt_sha256": (
                sha256_bytes(value.encode("utf-8")) if isinstance(value, str) else None
            ),
        }
        try:
            response = self.inner.invoke(value, *args, **kwargs)
            raw_count, duplicate_count = response_duplicate_count(response)
            entry.update(
                {
                    "status": "response_received",
                    "raw_relation_count": raw_count,
                    "raw_exact_duplicates": duplicate_count,
                }
            )
            return response
        except Exception as error:
            entry.update(
                {
                    "status": "invocation_error",
                    "error_type": type(error).__name__,
                }
            )
            raise
        finally:
            entry["invocation_latency_ms"] = round(
                (time.perf_counter() - started) * 1000,
                3,
            )
            new_events = self.recorder.events[callbacks_before:]
            entry["provider_callback_events"] = [
                dict(event) for event in new_events
            ]
            entry["provider_callback_event_count"] = len(new_events)
            self.recorder.calls.append(entry)


class RecordingModel:
    """Wrap only the structured runnable boundary used by Contract 10."""

    def __init__(self, inner: Any, recorder: UsageRecorder) -> None:
        self.inner = inner
        self.recorder = recorder

    def with_structured_output(self, schema: Any) -> RecordingRunnable:
        return RecordingRunnable(
            self.inner.with_structured_output(schema),
            self.recorder,
        )


def validate_frozen_inputs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Verify all locked source, entity, prompt, schema, and alias inputs."""

    sys.path.insert(0, str(REPOSITORY / "src"))
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import (
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _build_prompt,
        _structured_payload_schema,
    )

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock["baseline"]["repository_sha"] != EXPECTED_HEAD:
        raise RuntimeError("The frozen Contract 10 SHA does not match")
    actual_head = subprocess.check_output(
        [
            "git",
            "-c",
            "safe.directory=C:/Projects/Biomed",
            "-C",
            "C:/Projects/Biomed",
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()
    actual_branch = subprocess.check_output(
        [
            "git",
            "-c",
            "safe.directory=C:/Projects/Biomed",
            "-C",
            "C:/Projects/Biomed",
            "branch",
            "--show-current",
        ],
        text=True,
    ).strip()
    if actual_head != EXPECTED_HEAD or actual_branch != "extraction_system_v2":
        raise RuntimeError("The live repository no longer matches the locked baseline")
    source_bytes = CORPUS_PATH.read_bytes()
    expected_corpus_sha = lock["source_corpus"]["sha256"]
    if sha256_bytes(source_bytes) != expected_corpus_sha:
        raise RuntimeError("The frozen source corpus changed after the lock")
    schema = _structured_payload_schema().model_json_schema()
    schema_text = canonical_json(schema)
    if sha256_bytes(schema_text.encode("utf-8")) != lock["configuration"]["schema_sha256"]:
        raise RuntimeError("The Contract 10 structured schema changed after the lock")
    if (
        RELATION_EXTRACTION_SYSTEM_PROMPT
        != lock["configuration"]["system_prompt"]
    ):
        raise RuntimeError("The Contract 10 relation prompt changed after the lock")

    corpus = json.loads(source_bytes.decode("utf-8"))
    records = {item["paper_id"]: item for item in corpus["papers"]}
    by_paper: dict[str, dict[str, Any]] = {}
    for locked in lock["papers"]:
        paper_id = locked["paper_id"]
        record = records[paper_id]
        text = record["text"]
        source_sha = sha256_bytes(text.encode("utf-8"))
        if (
            source_sha != locked["source_sha256"]
            or len(text) != locked["source_characters"]
        ):
            raise RuntimeError(f"Frozen paper text changed: {paper_id}")
        packet_path = REPORT / locked["entity_packet_path"].split(
            "luna_56_vs_6_fullpaper_11/", 1
        )[1]
        if sha256_bytes(packet_path.read_bytes()) != locked["entity_packet_sha256"]:
            raise RuntimeError(f"Frozen entity packet changed: {paper_id}")
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        entities = [Entity(**item) for item in packet["entities"]]
        entity_json = json.dumps(
            [entity.to_dict() for entity in entities],
            ensure_ascii=False,
            indent=2,
        )
        if sha256_bytes(entity_json.encode("utf-8")) != locked["entity_input_sha256"]:
            raise RuntimeError(f"Serialized entity input changed: {paper_id}")
        prompt = _build_prompt(
            text,
            entities,
            RELATION_EXTRACTION_SYSTEM_PROMPT,
        )
        prompt_sha = sha256_bytes(prompt.encode("utf-8"))
        if prompt_sha != locked["prompt_sha256"]:
            raise RuntimeError(f"Complete prompt input changed: {paper_id}")
        if (
            locked["condition_entity_input_sha256"]["Model A"]
            != locked["condition_entity_input_sha256"]["Model B"]
            or locked["condition_prompt_sha256"]["Model A"]
            != locked["condition_prompt_sha256"]["Model B"]
        ):
            raise RuntimeError(f"Blinded condition inputs differ: {paper_id}")
        by_paper[paper_id] = {
            "record": record,
            "text": text,
            "entities": entities,
            "packet": packet,
            "lock": locked,
        }
    return lock, by_paper


def load_api_key() -> str:
    """Read the configured credential into memory without writing it to artifacts."""

    value = read_env_value("OPENAI_API_KEY")
    if not value:
        raise RuntimeError("OPENAI_API_KEY is unavailable in the process or project dotenv")
    return value


def total_usage(calls: Sequence[Mapping[str, Any]]) -> dict[str, int] | None:
    """Sum normalized token usage when callbacks reported it for any attempt."""

    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    found = False
    for call in calls:
        for event in call.get("provider_callback_events", []):
            usage = event.get("token_usage")
            if not isinstance(usage, Mapping):
                continue
            for key in totals:
                value = usage.get(key)
                if isinstance(value, int):
                    totals[key] += value
                    found = True
    return totals if found else None


def run_one(
    paper_id: str,
    model_alias: str,
    replicate: int,
    model_id: str,
    paper: Mapping[str, Any],
    api_key: str,
    lock: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one frozen relation condition and save output before continuing."""

    from langchain_openai import ChatOpenAI

    from biomedical_extractor.entity_assembly import assemble_document_entities
    from biomedical_extractor.llm_relation_extraction import (
        LLMRelationExtractor,
        OpenAIConfig,
    )
    from biomedical_extractor.graph import build_graph_result

    paper_slug = slug(paper_id)
    alias_slug = "model_a" if model_alias == "Model A" else "model_b"
    run_path = REPORT / "papers" / paper_slug / alias_slug / f"run_{replicate}.json"
    graph_path = (
        REPORT / "papers" / paper_slug / alias_slug / f"graph_run_{replicate}.json"
    )
    if run_path.exists():
        existing = json.loads(run_path.read_text(encoding="utf-8"))
        if existing.get("status") in {"complete", "failed"}:
            print(
                json.dumps(
                    {
                        "paper_id": paper_id,
                        "model": model_alias,
                        "replicate": replicate,
                        "status": "already_preserved",
                    },
                    ensure_ascii=True,
                ),
                flush=True,
            )
            return existing
        raise RuntimeError(
            f"Existing in-progress record needs manual reconciliation: {run_path}"
        )

    locked = paper["lock"]
    config = lock["configuration"]
    shared_record: dict[str, Any] = {
        "paper_id": paper_id,
        "model": model_alias,
        "replicate": replicate,
        "source_sha256": locked["source_sha256"],
        "source_characters": locked["source_characters"],
        "entity_packet_sha256": locked["entity_packet_sha256"],
        "entity_input_sha256": locked["entity_input_sha256"],
        "prompt_sha256": locked["prompt_sha256"],
        "schema_sha256": config["schema_sha256"],
        "prompt_schema_configuration": {
            "provider": config["provider"],
            "reasoning_effort": config["reasoning_effort"],
            "max_output_tokens": config["max_output_tokens"],
            "bounded_repair_budget": config["bounded_repair_budget"],
            "provider_retries": config["provider_retries"],
        },
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
    }
    write_json(run_path, shared_record)

    recorder = UsageRecorder()
    config_obj = OpenAIConfig(
        model=model_id,
        api_key=api_key,
        reasoning_effort=config["reasoning_effort"],
        max_completion_tokens=config["max_output_tokens"],
        max_retries=config["bounded_repair_budget"],
        base_url=None,
    )
    client_kwargs: dict[str, Any] = {
        "model": config_obj.model,
        "api_key": config_obj.resolved_api_key(),
        "use_responses_api": True,
        "reasoning": {"effort": config_obj.reasoning_effort},
        "max_retries": 0,
        "callbacks": [recorder],
    }
    if config_obj.max_completion_tokens is not None:
        client_kwargs["max_completion_tokens"] = config_obj.max_completion_tokens
    client = ChatOpenAI(**client_kwargs)
    extractor = LLMRelationExtractor(
        RecordingModel(client, recorder),
        max_retries=config_obj.max_retries,
    )

    started = time.perf_counter()
    error: Exception | None = None
    result: Any = None
    try:
        result = extractor.extract_relations(paper["text"], paper["entities"])
    except Exception as caught:
        error = caught
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    calls = [dict(item) for item in recorder.calls]
    token_usage = total_usage(calls)
    repair_count = sum(1 for item in calls if item.get("repair") is True)
    provider_attempt_count = len(calls)
    provider_latency_values = [
        event["provider_latency_ms"]
        for item in calls
        for event in item.get("provider_callback_events", [])
        if isinstance(event.get("provider_latency_ms"), (int, float))
    ]
    shared_record.update(
        {
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "status": "failed" if error is not None else "complete",
            "elapsed_ms": elapsed_ms,
            "provider_attempts": provider_attempt_count,
            "repair_attempts": repair_count,
            "provider_latency_ms": (
                round(sum(provider_latency_values), 3)
                if provider_latency_values
                else None
            ),
            "token_usage": token_usage,
            "provider_attempt_details": calls,
        }
    )
    if error is not None:
        shared_record["error"] = {
            "type": type(error).__name__,
            "message": redact_error(str(error), api_key),
        }
        write_json(run_path, shared_record)
        print(
            json.dumps(
                {
                    "paper_id": paper_id,
                    "model": model_alias,
                    "replicate": replicate,
                    "status": "failed",
                    "provider_attempts": provider_attempt_count,
                    "repair_attempts": repair_count,
                    "elapsed_ms": elapsed_ms,
                },
                ensure_ascii=True,
            ),
            flush=True,
        )
        return shared_record

    relations = [relation.to_dict() for relation in result.relations]
    graph = build_graph_result(
        paper_id,
        assemble_document_entities(paper["entities"], paper["text"]),
        result,
    )
    graph_value = graph.to_dict()
    write_json(graph_path, graph_value)
    raw_duplicate_counts = [
        item.get("raw_exact_duplicates")
        for item in calls
        if isinstance(item.get("raw_exact_duplicates"), int)
    ]
    final_raw_duplicates = raw_duplicate_counts[-1] if raw_duplicate_counts else None
    shared_record.update(
        {
            "validated_mention_level_relations": relations,
            "validated_relation_count": len(relations),
            "exact_duplicates_in_final_structured_response": final_raw_duplicates,
            "graph_path": graph_path.relative_to(REPORT).as_posix(),
            "graph_sha256": sha256_bytes(graph_path.read_bytes()),
            "graph": graph_value,
        }
    )
    write_json(run_path, shared_record)
    print(
        json.dumps(
            {
                "paper_id": paper_id,
                "model": model_alias,
                "replicate": replicate,
                "status": "complete",
                "relations": len(relations),
                "provider_attempts": provider_attempt_count,
                "repair_attempts": repair_count,
                "elapsed_ms": elapsed_ms,
                "token_usage": token_usage,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    return shared_record


def main() -> int:
    """Validate the immutable preflight and execute the frozen 12-run order."""

    if len(sys.argv) > 1 and sys.argv[1] not in {"--verify-only", "--run"}:
        raise SystemExit("Usage: run_benchmark.py [--verify-only|--run]")
    lock, papers = validate_frozen_inputs()
    model_ids = load_key()
    if set(model_ids) != {"Model A", "Model B"}:
        raise RuntimeError("Both blinded model aliases are required")
    if "--verify-only" in sys.argv:
        print(
            json.dumps(
                {
                    "preflight_valid": True,
                    "papers": len(papers),
                    "scheduled_relation_invocations": len(EXECUTION_ORDER),
                    "blinded_model_aliases": ["Model A", "Model B"],
                    "relation_requests_started": False,
                },
                ensure_ascii=True,
            )
        )
        return 0

    api_key = load_api_key()
    completed: list[dict[str, Any]] = []
    for paper_id, model_alias, replicate in EXECUTION_ORDER:
        completed.append(
            run_one(
                paper_id,
                model_alias,
                replicate,
                model_ids[model_alias],
                papers[paper_id],
                api_key,
                lock,
            )
        )
    print(
        json.dumps(
            {
                "scheduled_runs": len(EXECUTION_ORDER),
                "completed_or_preserved": sum(
                    1 for item in completed if item.get("status") == "complete"
                ),
                "failed": sum(
                    1 for item in completed if item.get("status") == "failed"
                ),
                "model_mapping_stored_separately": True,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(REPOSITORY / "src"))
    raise SystemExit(main())
