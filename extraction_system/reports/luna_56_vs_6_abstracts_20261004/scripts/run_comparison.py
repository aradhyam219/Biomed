"""Freeze and run a paired, blinded eight-abstract Luna relation comparison.

The production prompt, schema, validator, and bounded repair harness are reused
unchanged. Saved HunFlair2 mention packets hold NER constant; every provider
request is fresh. Raw provider metadata and the random model key stay in the
ignored cache until the semantic review is frozen. Child processes bound each
job without changing production extraction or retrying transport failures.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / REPORT.name
SCRIPT = Path(__file__).resolve()
KEY = CACHE / "model_key.json"
MODELS = ("gpt-5.6-luna", "gpt-6-luna")
PAPERS = (
    "PMCID:PMC10770459", "PMCID:PMC11824863", "PMCID:PMC8605525",
    "PMID:27172794", "PMID:27370646", "PMID:31324362",
    "PMID:33652126", "PMID:38569671",
)
REPAIRS = 2
REQUEST_TIMEOUT = 300
WATCHDOG = 920
MAX_OUTPUT = 128000
STOP_ERRORS = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return value.replace(":", "_").lower()


def serialize(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(serialize(value))
    temporary.replace(path)


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def env() -> None:
    """Load the existing ignored runner environment without exposing secrets."""
    path = ROOT / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(name.strip(), value)


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "safe.directory=C:/Projects/Biomed", "-C", str(ROOT.parent), *args],
        text=True,
    ).strip()


def contract() -> tuple[Any, Any, Any, Any]:
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import (
        LLMRelationExtractor, RELATION_EXTRACTION_SYSTEM_PROMPT,
        _build_prompt, _structured_payload_schema,
    )
    return Entity, LLMRelationExtractor, _build_prompt, (
        RELATION_EXTRACTION_SYSTEM_PROMPT, _structured_payload_schema,
    )


def prepare() -> None:
    """Validate and freeze all inputs and execution rules before paid requests."""
    if (REPORT / "preflight.json").exists():
        raise RuntimeError("Preflight already exists; do not overwrite a frozen run")
    env()
    key_env = os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
    if not os.getenv(key_env):
        raise RuntimeError(f"Credentials unavailable in {key_env}")
    dirty = git("status", "--short", "--", "extraction_system/src", "extraction_system/tests", "extraction_system/viewer")
    if dirty:
        raise RuntimeError("Production, test, or viewer changes must be resolved before freezing")
    Entity, _, build_prompt, (system_prompt, schema_factory) = contract()
    corpus_path = ROOT / ".cache/ner_target_domain/target_corpus.json"
    corpus = {p["paper_id"]: p for p in read(corpus_path)["papers"]}
    manifests = []
    for paper_id in PAPERS:
        reference_path = ROOT / "reports/relation_generalization_09b/papers" / f"{slug(paper_id)}.json"
        old = read(reference_path)
        segments = [s for s in corpus[paper_id]["segments"] if s["section"] == "title" or s["section"].startswith("abstract")]
        text = "\n\n".join(s["text"] for s in segments)
        if digest(text) != old["source"]["selected_source_sha256"]:
            raise RuntimeError(f"Canonical source differs from saved mention packet: {paper_id}")
        entities = tuple(Entity(**e) for e in old["entities"])
        if len({e.id for e in entities}) != len(entities):
            raise RuntimeError(f"Duplicate entity IDs: {paper_id}")
        for e in entities:
            if text[e.start:e.end] != e.text:
                raise RuntimeError(f"Invalid exact-source span: {paper_id}/{e.id}")
        prompt = build_prompt(text, entities, system_prompt)
        manifest = {
            "paper_id": paper_id, "title": corpus[paper_id]["title"],
            "source_text": text, "source_sha256": digest(text),
            "entities": [e.to_dict() for e in entities],
            "entity_packet_sha256": digest(serialize([e.to_dict() for e in entities])),
            "prompt_sha256": digest(prompt), "source_scope": "title plus complete abstract",
            "canonical_segments": segments,
            "entity_packet_origin": str(reference_path.relative_to(ROOT)),
            "entity_packet_origin_sha256": digest(reference_path.read_bytes()),
            "prior_relation_outputs_reused": False,
        }
        destination = REPORT / "inputs" / f"{slug(paper_id)}.json"
        write(destination, manifest)
        manifests.append({"paper_id": paper_id, "manifest_sha256": digest(destination.read_bytes()),
                          "source_sha256": digest(text), "entity_count": len(entities),
                          "prompt_sha256": digest(prompt)})
    shuffled = list(MODELS)
    secrets.SystemRandom().shuffle(shuffled)
    write(KEY, {"Model A": shuffled[0], "Model B": shuffled[1]})
    order = []
    for i, paper_id in enumerate(PAPERS):
        aliases = ("Model A", "Model B") if i % 2 == 0 else ("Model B", "Model A")
        for alias in aliases:
            order.append({"sequence": len(order) + 1, "paper_id": paper_id, "alias": alias})
    modules = ("llm_relation_extraction.py", "relation_extraction.py", "entity_extraction.py")
    write(REPORT / "preflight.json", {
        "created_utc": now(), "baseline_head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"), "production_scope_status": dirty,
        "authorization": "User requested the eight-abstract GPT-6 Luna max versus GPT-5.6 Luna max comparison and a thorough Codex review",
        "models": list(MODELS), "mapping_disclosed_before_review": False,
        "configuration": {"api": "Responses", "reasoning": {"effort": "max"},
            "reasoning_mode": "standard/default", "max_output_tokens": MAX_OUTPUT,
            "sampling_parameters": "omitted", "provider_retries": 0,
            "repair_budget": REPAIRS, "request_timeout_seconds": REQUEST_TIMEOUT,
            "job_watchdog_seconds": WATCHDOG, "consecutive_operational_error_stop": STOP_ERRORS,
            "manual_transport_retries": 0, "replicates_per_paper_model": 1,
            "base_url_override_configured": bool(os.getenv("OPENAI_BASE_URL")),
            "credential_env_name": key_env, "credential_available": True,
            "context": "one independent fresh request per attempt; no previous response or saved extraction supplied"},
        "review_policy": {"reviewer": "Codex", "human_gold": False,
            "source_only_reference_before_model_output_review": True,
            "all_final_relations_reviewed": True,
            "dimensions": ["endpoint identity", "direction", "negation", "assertion support",
                "intervention", "effects", "context", "verbatim grounding", "alias-only relations", "omitted explicit claims"],
            "no_formal_precision_recall_f1_or_population_accuracy": True,
            "no_quality_winner_from_operational_failures": True},
        "source_corpus_sha256": digest(corpus_path.read_bytes()),
        "system_prompt_sha256": digest(system_prompt),
        "schema_sha256": digest(json.dumps(schema_factory().model_json_schema(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))),
        "production_files_sha256": {name: digest((ROOT / "src/biomedical_extractor" / name).read_bytes()) for name in modules},
        "runner_sha256": digest(SCRIPT.read_bytes()),
        "versions": {p: importlib.metadata.version(p) for p in ("openai", "langchain-openai", "langchain-core")},
        "papers": manifests, "execution_order": order,
        "cost_rates_usd_per_million": {
            "gpt-5.6-luna": {"input": .2, "cached_input": .02, "cache_write": .25, "output": 1.2},
            "gpt-6-luna": {"input": .1, "cached_input": .01, "cache_write": .125, "output": .5}},
        "cost_source": "https://developers.openai.com/api/docs/models/", "pricing_checked_date": "2026-10-04",
    })
    print(json.dumps({"prepared_papers": len(manifests), "planned_jobs": len(order), "head": git("rev-parse", "HEAD")}))


def verify() -> dict[str, Any]:
    preflight = read(REPORT / "preflight.json")
    if git("rev-parse", "HEAD") != preflight["baseline_head"]:
        raise RuntimeError("Repository HEAD changed after freeze")
    for name, expected in preflight["production_files_sha256"].items():
        if digest((ROOT / "src/biomedical_extractor" / name).read_bytes()) != expected:
            raise RuntimeError(f"Frozen production file changed: {name}")
    if digest(SCRIPT.read_bytes()) != preflight["runner_sha256"]:
        raise RuntimeError("Frozen runner changed")
    for item in preflight["papers"]:
        if digest((REPORT / "inputs" / f"{slug(item['paper_id'])}.json").read_bytes()) != item["manifest_sha256"]:
            raise RuntimeError("Frozen input changed")
    return preflight


def result_path(job: dict[str, Any]) -> Path:
    return REPORT / "outputs" / slug(job["paper_id"]) / (job["alias"].lower().replace(" ", "_") + ".json")


def worker(sequence: int) -> None:
    """Instrument the unchanged production repair harness for one condition."""
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_openai import ChatOpenAI
    from biomedical_extractor.llm_relation_extraction import _parse_structured_response
    from biomedical_extractor.relation_extraction import validate_relations
    env()
    preflight = verify()
    job = preflight["execution_order"][sequence - 1]
    packet = read(REPORT / "inputs" / f"{slug(job['paper_id'])}.json")
    model_id = read(KEY)[job["alias"]]
    api_key = os.environ[os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")]
    Entity, Extractor, _, _ = contract()
    entities = tuple(Entity(**e) for e in packet["entities"])
    kwargs = {"model": model_id, "api_key": api_key, "use_responses_api": True,
        "reasoning": {"effort": "max"}, "max_completion_tokens": MAX_OUTPUT,
        "max_retries": 0, "timeout": REQUEST_TIMEOUT}
    if os.getenv("OPENAI_BASE_URL"):
        kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
    chat = ChatOpenAI(**kwargs)
    attempts: list[dict[str, Any]] = []
    target = result_path(job)
    started = time.monotonic()

    def safe_error(error: BaseException) -> str:
        message = str(error).replace(api_key, "[REDACTED]")
        for name in MODELS:
            message = message.replace(name, "[MODEL]")
        return message

    def persist(status: str, **extra: Any) -> None:
        write(target, {**job, "status": status, "source_sha256": packet["source_sha256"],
            "entity_packet_sha256": packet["entity_packet_sha256"],
            "elapsed_seconds": round(time.monotonic() - started, 3), "attempts": attempts, **extra})

    class Recorder(BaseCallbackHandler):
        def on_llm_end(self, response: Any, **unused: Any) -> None:
            for generations in response.generations:
                for generation in generations:
                    message = generation.message
                    attempts[-1]["provider_response_received"] = True
                    attempts[-1]["usage"] = message.usage_metadata
                    raw_path = CACHE / "raw" / slug(job["paper_id"]) / job["alias"].replace(" ", "_") / f"attempt_{len(attempts)}.json"
                    write(raw_path, message.model_dump(mode="json"))
                    attempts[-1]["raw_response_sha256"] = digest(raw_path.read_bytes())
                    attempts[-1]["raw_response_cache_path"] = str(raw_path.relative_to(ROOT))
                    persist("running")

    class Runnable:
        def __init__(self, bound: Any) -> None:
            self.bound = bound

        def invoke(self, prompt: str) -> Any:
            attempt = {"attempt": len(attempts) + 1, "repair": bool(attempts),
                "started_utc": now(), "prompt_sha256": digest(prompt),
                "provider_response_received": False, "usage": None, "status": "running"}
            attempts.append(attempt)
            write(CACHE / "prompts" / slug(job["paper_id"]) / job["alias"].replace(" ", "_") / f"attempt_{len(attempts)}.json", {"prompt": prompt})
            persist("running")
            start = time.monotonic()
            try:
                response = self.bound.invoke(prompt, config={"callbacks": [Recorder()]})
            except Exception as error:
                attempt.update(status="provider_or_parser_error", error_type=type(error).__name__, exact_error=safe_error(error))
                raise
            else:
                attempt["status"] = "structured_output_received"
                attempt["structured_output"] = response.model_dump(mode="json") if hasattr(response, "model_dump") else response
                try:
                    validate_relations(packet["source_text"], entities, _parse_structured_response(response))
                except Exception as validation_error:
                    attempt["validation_status"] = "invalid"
                    attempt["validation_error"] = safe_error(validation_error)
                else:
                    attempt["validation_status"] = "valid"
                return response
            finally:
                attempt["latency_seconds"] = round(time.monotonic() - start, 3)
                persist("running")

    class Model:
        def with_structured_output(self, schema: Any) -> Runnable:
            return Runnable(chat.with_structured_output(schema))

    persist("running")
    extractor = Extractor(Model(), max_retries=REPAIRS)
    try:
        result = extractor.extract_relations(packet["source_text"], entities)
    except Exception as error:
        received = bool(attempts and attempts[-1]["provider_response_received"])
        causes = []
        cursor: BaseException | None = error
        while cursor:
            causes.append({"error_type": type(cursor).__name__, "exact_error": safe_error(cursor)})
            cursor = cursor.__cause__
        persist("validation_failure" if received else "provider_failure", exact_error=safe_error(error), causes=causes,
                validated_relations=None, repair_attempts=max(0, len(attempts) - 1))
    else:
        persist("success", validated_relations=result.to_dict()["relations"], exact_error=None,
                repair_attempts=max(0, len(attempts) - 1))


def run() -> None:
    preflight = verify()
    state_path = REPORT / "run_state.json"
    if state_path.exists():
        raise RuntimeError("Run already started; automatic reruns are prohibited")
    state = {"started_utc": now(), "status": "running", "completed": [], "consecutive_operational_errors": 0}
    write(state_path, state)
    for job in preflight["execution_order"]:
        path = result_path(job)
        if path.exists():
            raise RuntimeError("Existing job output would be overwritten")
        print(f"Starting {job['sequence']}/16 {job['paper_id']} {job['alias']}", flush=True)
        start = time.monotonic()
        try:
            child = subprocess.run([sys.executable, str(SCRIPT), "--worker", str(job["sequence"])],
                cwd=ROOT, capture_output=True, text=True, timeout=WATCHDOG)
            if child.returncode or not path.exists():
                existing = read(path) if path.exists() else {**job, "attempts": []}
                write(path, {**existing, "status": "worker_failure", "exact_error": "Worker exited without a terminal result", "worker_exit_code": child.returncode})
                write(CACHE / "worker_logs" / f"job_{job['sequence']}.json", {"stdout": child.stdout, "stderr": child.stderr})
        except subprocess.TimeoutExpired:
            existing = read(path) if path.exists() else {**job, "attempts": []}
            write(path, {**existing, "status": "timeout", "exact_error": f"Worker exceeded the {WATCHDOG}-second wall-clock ceiling", "elapsed_seconds": round(time.monotonic() - start, 3), "validated_relations": None})
        outcome = read(path)
        state["completed"].append({**job, "status": outcome["status"], "elapsed_seconds": outcome.get("elapsed_seconds"),
                                   "relations": len(outcome.get("validated_relations") or []), "attempts": len(outcome["attempts"])})
        operational = outcome["status"] in {"provider_failure", "timeout", "worker_failure"}
        state["consecutive_operational_errors"] = state["consecutive_operational_errors"] + 1 if operational else 0
        write(state_path, state)
        print(json.dumps(state["completed"][-1]), flush=True)
        if state["consecutive_operational_errors"] >= STOP_ERRORS:
            state["status"] = "aborted_stop_condition"
            break
    else:
        state["status"] = "complete"
    for job in preflight["execution_order"][len(state["completed"]):]:
        write(result_path(job), {**job, "status": "not_run_aborted", "attempts": [], "validated_relations": None})
    state["completed_utc"] = now()
    write(state_path, state)
    print(json.dumps({"status": state["status"], "completed_jobs": len(state["completed"])}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--worker", type=int)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        run()
    elif args.worker:
        worker(args.worker)
    else:
        parser.error("Choose --prepare, --run, or --worker")
