from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).resolve().parent
SOURCE = "Protein A inhibits Protein B."
ENTITIES = [
    {"id": "E1", "text": "Protein A", "type": "Protein", "start": 0, "end": 9, "score": 1.0},
    {"id": "E2", "text": "Protein B", "type": "Protein", "start": 19, "end": 28, "score": 1.0},
]
MODEL = "gpt-6-luna"
REASONING_EFFORT = "max"
MAX_OUTPUT_TOKENS = 128000
WATCHDOG_SECONDS = 300


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def text_digest(value: str) -> str:
    return digest(value.encode("utf-8"))


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8", newline="")
    temporary.replace(path)


def json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def prepare_preflight() -> dict[str, Any]:
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import (
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _build_prompt,
        _structured_payload_schema,
    )

    entities = [Entity(**value) for value in ENTITIES]
    for entity in entities:
        if SOURCE[entity.start:entity.end] != entity.text:
            raise RuntimeError(f"Invalid synthetic entity span: {entity.id}")
    schema = _structured_payload_schema().model_json_schema()
    schema_sha = text_digest(json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    key_env = os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "single GPT-6 Luna connectivity and structured-output smoke",
        "baseline": {
            "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "production_scope_status": subprocess.check_output(["git", "status", "--short", "--", "src", "viewer", "tests"], cwd=ROOT, text=True).strip(),
        },
        "provider": "OpenAI Responses API",
        "configuration": {
            "model": MODEL,
            "reasoning": {"effort": REASONING_EFFORT},
            "use_responses_api": True,
            "max_completion_tokens": MAX_OUTPUT_TOKENS,
            "provider_retries": 0,
            "relation_extractor_repair_budget": 0,
            "external_watchdog_seconds": WATCHDOG_SECONDS,
            "base_url_override_configured": bool(os.getenv("OPENAI_BASE_URL")),
            "credential_env_name": key_env,
            "credential_available": bool(os.getenv(key_env)),
        },
        "runtime_versions": {
            "langchain_openai": __import__("langchain_openai").__version__,
            "langchain_core": __import__("langchain_core").__version__,
            "openai": __import__("openai").__version__,
        },
        "synthetic_input": {
            "source": SOURCE,
            "source_sha256": text_digest(SOURCE),
            "entities": [entity.to_dict() for entity in entities],
            "contract10_system_prompt_sha256": text_digest(RELATION_EXTRACTION_SYSTEM_PROMPT),
            "contract10_structured_schema_sha256": schema_sha,
            "rendered_prompt_sha256": text_digest(_build_prompt(SOURCE, entities, RELATION_EXTRACTION_SYSTEM_PROMPT)),
        },
        "provider_calls_scheduled": 1,
        "provider_response_detection": "LangChain on_llm_end callback; successful structured runnable return also sets true",
    }


def worker() -> None:
    from langchain_openai import ChatOpenAI
    from langchain_core.callbacks import BaseCallbackHandler
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import (
        LLMRelationExtractor,
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _structured_payload_schema,
    )
    from biomedical_extractor.relation_extraction import RelationExtractionError

    entities = [Entity(**value) for value in ENTITIES]
    key_env = os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
    api_key = os.getenv(key_env)
    if not api_key:
        write_json(REPORT / "result.json", {"status": "setup_failure", "provider_response_received": False, "error_type": "MissingCredentials", "exact_error": f"OpenAI credentials are unavailable; set {key_env}", "attempts": []})
        return
    kwargs: dict[str, Any] = {
        "model": MODEL,
        "api_key": api_key,
        "use_responses_api": True,
        "reasoning": {"effort": REASONING_EFFORT},
        "max_retries": 0,
        "max_completion_tokens": MAX_OUTPUT_TOKENS,
    }
    if os.getenv("OPENAI_BASE_URL"):
        kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
    chat_model = ChatOpenAI(**kwargs)
    attempt: dict[str, Any] = {
        "attempt": 1,
        "repair": False,
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "prompt_sha256": None,
        "provider_response_received": False,
        "structured_output_received": False,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }
    state = {"attempts": [attempt]}
    progress_path = REPORT / "progress.json"

    class UsageHandler(BaseCallbackHandler):
        def on_llm_end(self, response: Any, **kwargs: Any) -> None:
            attempt["provider_response_received"] = True
            input_tokens = output_tokens = total_tokens = None
            for generations in getattr(response, "generations", ()):
                for generation in generations:
                    message = getattr(generation, "message", None)
                    usage = getattr(message, "usage_metadata", None) or {}
                    metadata = getattr(message, "response_metadata", None) or {}
                    token_usage = metadata.get("token_usage", {}) if isinstance(metadata, dict) else {}
                    generation_info = getattr(generation, "generation_info", None) or {}
                    token_usage = token_usage or generation_info.get("token_usage", {})
                    input_tokens = input_tokens if input_tokens is not None else usage.get("input_tokens", token_usage.get("prompt_tokens"))
                    output_tokens = output_tokens if output_tokens is not None else usage.get("output_tokens", token_usage.get("completion_tokens"))
                    total_tokens = total_tokens if total_tokens is not None else usage.get("total_tokens", token_usage.get("total_tokens"))
            attempt["input_tokens"] = input_tokens
            attempt["output_tokens"] = output_tokens
            attempt["total_tokens"] = total_tokens
            write_json(progress_path, state)

    class CapturingRunnable:
        def __init__(self, runnable: Any) -> None:
            self.runnable = runnable

        def invoke(self, prompt: str) -> Any:
            attempt["prompt_sha256"] = text_digest(prompt)
            attempt["provider_invocation_started_utc"] = datetime.now(timezone.utc).isoformat()
            write_json(progress_path, state)
            started = time.monotonic()
            try:
                response = self.runnable.invoke(prompt, config={"callbacks": [UsageHandler()]})
            except BaseException as error:
                attempt["status"] = "provider_or_parser_error"
                attempt["elapsed_seconds"] = round(time.monotonic() - started, 3)
                attempt["error_type"] = type(error).__name__
                attempt["error"] = str(error)
                write_json(progress_path, state)
                raise
            attempt["provider_response_received"] = True
            attempt["structured_output_received"] = True
            attempt["status"] = "response_received"
            attempt["elapsed_seconds"] = round(time.monotonic() - started, 3)
            attempt["structured_output"] = json_default(response)
            write_json(progress_path, state)
            return response

    class InstrumentedModel:
        def with_structured_output(self, schema: Any) -> CapturingRunnable:
            if schema.__name__ != _structured_payload_schema().__name__:
                raise RuntimeError("Unexpected structured relation schema")
            return CapturingRunnable(chat_model.with_structured_output(schema))

    extractor = LLMRelationExtractor(
        InstrumentedModel(), max_retries=0, prompt=RELATION_EXTRACTION_SYSTEM_PROMPT
    )
    write_json(progress_path, state)
    started = time.monotonic()
    try:
        result = extractor.extract_relations(SOURCE, entities)
    except BaseException as error:
        causes = []
        cursor: BaseException | None = error
        while cursor is not None:
            causes.append({"type": type(cursor).__name__, "message": str(cursor)})
            cursor = cursor.__cause__
        received = bool(attempt.get("provider_response_received"))
        is_connection = any("connection" in f"{item['type']} {item['message']}".lower() for item in causes)
        status = "validation_failure" if received else ("connection_failure" if is_connection else "provider_failure")
        outcome = {
            "status": status,
            "provider_response_received": received,
            "structured_output_received": bool(attempt.get("structured_output_received")),
            "validated_relation_count": 0,
            "validated_relations": [],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "error_type": type(error).__name__,
            "exact_error": str(error),
            "causes": causes,
            "attempts": [attempt],
        }
    else:
        outcome = {
            "status": "success",
            "provider_response_received": bool(attempt.get("provider_response_received")),
            "structured_output_received": bool(attempt.get("structured_output_received")),
            "validated_relation_count": len(result.relations),
            "validated_relations": result.to_dict()["relations"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "exact_error": None,
            "attempts": [attempt],
        }
    write_json(REPORT / "result.json", outcome)
    write_json(progress_path, state)


def driver() -> None:
    preflight = prepare_preflight()
    write_json(REPORT / "preflight.json", preflight)
    start = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=WATCHDOG_SECONDS,
            check=False,
        )
        elapsed = time.monotonic() - start
        if (REPORT / "result.json").exists():
            outcome = json.loads((REPORT / "result.json").read_text(encoding="utf-8"))
        else:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"Worker exited {completed.returncode} without a result"
            outcome = {"status": "worker_failure", "provider_response_received": False, "validated_relation_count": 0, "validated_relations": [], "elapsed_seconds": round(elapsed, 3), "exact_error": detail, "attempts": []}
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        progress_path = REPORT / "progress.json"
        progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {"attempts": []}
        attempts = progress.get("attempts", [])
        received = any(bool(attempt.get("provider_response_received")) for attempt in attempts)
        outcome = {
            "status": "timeout",
            "provider_response_received": received,
            "structured_output_received": any(bool(attempt.get("structured_output_received")) for attempt in attempts),
            "validated_relation_count": 0,
            "validated_relations": [],
            "elapsed_seconds": round(elapsed, 3),
            "error_type": "JobTimeout",
            "exact_error": f"Worker exceeded the {WATCHDOG_SECONDS}-second wall-clock ceiling and was terminated; no retry was made.",
            "attempts": attempts,
        }
        if attempts and attempts[-1].get("provider_invocation_started_utc"):
            call_started = datetime.fromisoformat(attempts[-1]["provider_invocation_started_utc"])
            attempts[-1]["observed_latency_until_watchdog_seconds"] = round((datetime.now(timezone.utc) - call_started).total_seconds(), 3)
        if attempts and attempts[-1].get("status") == "running":
            attempts[-1]["status"] = "terminated_by_external_watchdog"
            attempts[-1]["terminated_by_external_watchdog"] = True
            attempts[-1]["watchdog_elapsed_seconds"] = round(elapsed, 3)
        write_json(REPORT / "progress.json", progress)
    write_json(REPORT / "result.json", outcome)
    attempts = outcome.get("attempts", [])
    attempt = attempts[0] if attempts else {}
    summary = {
        "status": outcome["status"],
        "provider_response_received": bool(outcome.get("provider_response_received")),
        "structured_output_received": bool(outcome.get("structured_output_received")),
        "provider_attempts": len(attempts),
        "repair_attempts": sum(bool(item.get("repair")) for item in attempts),
        "elapsed_seconds": outcome.get("elapsed_seconds", round(elapsed, 3)),
        "provider_attempt_latency_seconds": attempt.get("elapsed_seconds") if attempt.get("elapsed_seconds") is not None else attempt.get("observed_latency_until_watchdog_seconds"),
        "provider_attempt_latency_kind": "measured" if attempt.get("elapsed_seconds") is not None else ("observed until watchdog" if attempt.get("observed_latency_until_watchdog_seconds") is not None else None),
        "input_tokens": attempt.get("input_tokens"),
        "output_tokens": attempt.get("output_tokens"),
        "total_tokens": attempt.get("total_tokens"),
        "validated_relation_count": outcome.get("validated_relation_count", 0),
        "validated_relations": outcome.get("validated_relations", []),
        "exact_error": outcome.get("exact_error"),
        "external_watchdog_seconds": WATCHDOG_SECONDS,
        "stopped_after_single_call": True,
    }
    write_json(REPORT / "summary.json", summary)
    lines = [
        "# GPT-6 Luna Connectivity and Structured Output Smoke",
        "",
        f"- Status: `{summary['status']}`",
        f"- Provider response received: `{str(summary['provider_response_received']).lower()}`",
        f"- Structured output received: `{str(summary['structured_output_received']).lower()}`",
        f"- Provider attempts: {summary['provider_attempts']}; repair attempts: {summary['repair_attempts']}",
        f"- Elapsed time: {summary['elapsed_seconds']} seconds; provider-attempt latency: {summary['provider_attempt_latency_seconds']}",
        f"- Tokens: input {summary['input_tokens']}; output {summary['output_tokens']}; total {summary['total_tokens']}",
        f"- Validated relations: {summary['validated_relation_count']}",
        f"- Exact error: {summary['exact_error']}",
        "- The test used only the synthetic source in `preflight.json`; no paper data, NER run, or repair call was used.",
        "",
    ]
    (REPORT / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="")
    print(json.dumps(summary, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker()
    else:
        driver()


if __name__ == "__main__":
    main()
