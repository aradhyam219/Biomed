"""Contract 11S shadow transport probe; production owns all biomedical semantics.

Run --prepare locally, then --run only through network-capable escalation.
An existing generation record prevents a second launch, including after a lost ACK.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.llm_relation_extraction import (
    DEFAULT_LLM_RELATION_MODEL, RELATION_EXTRACTION_SYSTEM_PROMPT,
    _build_prompt, _structured_payload_schema, _parse_structured_response,
)
from biomedical_extractor.relation_extraction import validate_relations, RelationValidationError
from openai import OpenAI, APIConnectionError, APIStatusError

EXPECTED_HEAD = "7f388368a8bd06f35f60eda37eb2ccdce711eed8"
EXPECTED_SCHEMA = "023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945"
EXPECTED_PROMPT = "ee73415e65f88d52e17c473eb2d5143940b19b9adfa7d4a6d117e5db450b0405"
CONFIG = dict(model="gpt-6-luna", reasoning={"effort": "max"},
              max_output_tokens=128000, background=True, store=False)
SYNTHETIC = "Protein A inhibits Protein B."
SYNTHETIC_ENTITIES = [Entity(id="E1", text="Protein A", type="Protein", start=0, end=9, score=1.0),
                      Entity(id="E2", text="Protein B", type="Protein", start=19, end=28, score=1.0)]
SCHEMA = _structured_payload_schema().model_json_schema()
HISTORY = []
SECRET = ""


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write(name, value):
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=C:/Projects/Biomed", *args],
                                   cwd=ROOT, text=True).strip()


def baseline():
    paths = ["src", "viewer", "tests", "pyproject.toml", "uv.lock", ".env", "requirements*"]
    state = dict(head=git("rev-parse", "HEAD"), branch=git("branch", "--show-current"),
                 production_status=git("status", "--short", "--", *paths),
                 production_diff=git("diff", "HEAD", "--", *paths),
                 production_model_default=DEFAULT_LLM_RELATION_MODEL)
    if state["head"] != EXPECTED_HEAD or state["branch"] != "extraction_system_v2":
        raise RuntimeError("Required repository baseline is absent")
    if state["production_status"] or state["production_diff"]:
        raise RuntimeError("Production freeze violated")
    return state


def frozen():
    manifest = json.loads((ROOT / "reports/luna_56_vs_6_real_probe_11qr/passage_001/manifest.json").read_text())
    text = manifest["source_text"]
    entities = [Entity(**item) for item in manifest["entity_packet"]]
    packet_sha = sha(json.dumps(manifest["entity_packet"], ensure_ascii=False, indent=2, sort_keys=True))
    assert sha(text) == "ecd73abad943377d0d94e5937c61c1eab0799c4e70c0044202ac3910d412b087"
    assert packet_sha == "b35d86c489fb52755adb5dd7750dc86b045fefd405167a42cefeedc403377e56"
    assert len(text) == 1981 and len(entities) == 68
    assert manifest["source_range"] == {"start": 25843, "end": 27824}
    assert manifest["paper_id"] == "PMCID:PMC10770459" and manifest["passage_id"] == "passage_001"
    assert all(text[e.start:e.end] == e.text for e in entities)
    assert sha(_build_prompt(text, entities, RELATION_EXTRACTION_SYSTEM_PROMPT)) == EXPECTED_PROMPT
    assert sha(canonical(SCHEMA)) == EXPECTED_SCHEMA
    return manifest, text, entities


def prepare():
    state = baseline()
    manifest, _, _ = frozen()
    preflight = dict(created_timestamp=now(), baseline=state,
        runtime_versions={name: importlib.metadata.version(name) for name in
                          ("openai", "langchain-openai", "langchain-core")},
        network_execution_mode="require_escalated / network-capable; all provider operations",
        configuration={**CONFIG, "provider_sdk_retries": 0, "temperature": "unset", "service_tier": "unset"},
        contract10_system_prompt_sha256=sha(RELATION_EXTRACTION_SYSTEM_PROMPT),
        contract10_schema_sha256=sha(canonical(SCHEMA)),
        real_passage={key: manifest[key] for key in ("paper_id", "passage_id", "source_range",
                     "source_sha256", "entity_packet_sha256", "entity_count", "source_characters", "prompt_sha256")},
        poll_interval_seconds=3, consecutive_poll_error_limit=5,
        synthetic_deadline_seconds=120, real_passage_deadline_seconds=480, repair_budget=2,
        schema_transport="unchanged model_json_schema; strict=true; no requiredness/default rewrites",
        official_background_documentation="https://developers.openai.com/api/docs/guides/background")
    write("preflight.json", preflight)
    return preflight


def env_value(name):
    value = os.getenv(name)
    if value:
        return value
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, sep, candidate = line.strip().removeprefix("export ").partition("=")
            if sep and key.strip() == name:
                return candidate.strip().strip("\"'") or None
    return None


def redact(message):
    if SECRET:
        message = message.replace(SECRET, "[REDACTED]")
    message = re.sub(r"sk-[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
    return re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)


def error_chain(error):
    result, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        item = dict(type=type(error).__name__, message=redact(str(error)))
        if isinstance(error, APIStatusError):
            item.update(status_code=error.status_code, request_id=error.request_id)
        result.append(item)
        error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    return result


def generation(client, prompt, deadline, record, persist):
    """Persist the ID before polling; never retry create, even after lost ACK."""
    baseline()
    record.update(configuration=CONFIG, prompt_sha256=sha(prompt), schema_sha256=EXPECTED_SCHEMA,
                  create_requested_timestamp=now(), response_id=None, initial_status=None,
                  status="create_requested", poll_count=0, poll_errors=0, structured_output_received=False,
                  validated_relation_count=0, validation_error=None, provider_sdk_retries=0)
    persist()
    started = time.monotonic()
    try:
        response = client.responses.create(**CONFIG, input=prompt, timeout=60,
            text={"format": {"type": "json_schema", "name": "StructuredRelationPayload",
                             "schema": SCHEMA, "strict": True}})
    except Exception as error:
        record.update(status="background_create_failure", error_chain=error_chain(error),
                      initial_create_latency_seconds=round(time.monotonic()-started, 3),
                      terminal_timestamp=now(), elapsed_wall_seconds=round(time.monotonic()-started, 3))
        persist()
        return None
    received = time.monotonic()
    record.update(response_id=response.id, created_timestamp=now(), provider_created_at=response.created_at,
                  initial_status=response.status, status=response.status,
                  initial_create_latency_seconds=round(received-started, 3))
    persist()
    consecutive = 0
    while response.status in ("queued", "in_progress"):
        remaining = deadline - (time.monotonic()-received)
        if remaining <= 0:
            record.update(status="background_timeout_cancelled", cancel_requested=True,
                          cancel_requested_timestamp=now(), last_known_status=response.status)
            persist()
            try:
                cancelled = client.responses.cancel(response.id, timeout=30)
                record["cancel_result"] = {"id": cancelled.id, "status": cancelled.status}
            except Exception as error:
                record["cancel_error"] = error_chain(error)
            break
        time.sleep(min(3, remaining))
        remaining = deadline - (time.monotonic()-received)
        if remaining <= 0:
            continue
        baseline()
        polled = time.monotonic()
        entry = dict(timestamp=now(), response_id=response.id)
        record["poll_count"] += 1
        try:
            response = client.responses.retrieve(response.id, timeout=min(20, remaining))
            entry["status"] = response.status
            record["status"] = response.status
            consecutive = 0
        except Exception as error:
            entry.update(status=response.status, poll_error=error_chain(error))
            record["poll_errors"] += 1
            consecutive += 1
            # Only transient retrieve failures are retryable; generation is never retried.
            transient = isinstance(error, APIConnectionError) or (
                isinstance(error, APIStatusError) and (error.status_code >= 500 or error.status_code in (408, 429)))
            if consecutive >= 5 or not transient:
                record.update(status="background_polling_failure", error_chain=error_chain(error))
        entry["poll_latency_seconds"] = round(time.monotonic()-polled, 3)
        HISTORY.append(entry)
        write("poll_history.json", HISTORY)
        persist()
        if record["status"] == "background_polling_failure":
            break
    record.update(terminal_timestamp=now(), terminal_status=response.status,
                  background_elapsed_seconds=round(time.monotonic()-received, 3),
                  elapsed_wall_seconds=round(time.monotonic()-started, 3),
                  usage=response.usage.model_dump(mode="json") if response.usage else None,
                  provider_error=response.error.model_dump(mode="json") if response.error else None,
                  incomplete_details=response.incomplete_details.model_dump(mode="json") if response.incomplete_details else None)
    record["structured_output_received"] = bool(response.output_text)
    record["transport_success"] = response.status == "completed" and bool(response.output_text)
    # Capture output text only; never serialize reasoning items or hidden reasoning.
    if response.output_text:
        record["structured_output"] = response.output_text
    if record["status"] in ("background_timeout_cancelled", "background_polling_failure"):
        persist()
        return None
    record["status"] = {"failed": "provider_failed", "incomplete": "provider_incomplete",
                        "cancelled": "background_timeout_cancelled"}.get(response.status, response.status)
    if response.status == "completed" and not response.output_text:
        record.update(status="structured_parse_failure", validation_error="Completed response has no structured output text")
    persist()
    return response.output_text if record["transport_success"] else None


def phase(client, name, text, entities, deadline):
    outcome = dict(status="pending", generations=[], provider_generation_count=0, repair_count=0,
                   validated_relation_count=0, unique_evidence_span_count=0, transport_success=False,
                   contract10_success=False)
    persist = lambda: write(name, outcome)
    prompt = _build_prompt(text, entities, RELATION_EXTRACTION_SYSTEM_PROMPT)
    phase_started = time.monotonic()
    for attempt in range(3):
        record = dict(generation_number=attempt+1, repair=bool(attempt))
        outcome["generations"].append(record)
        outcome.update(provider_generation_count=attempt+1, repair_count=attempt)
        generation_deadline = deadline
        if name == "synthetic_background.json" and attempt:
            # Phase A's 120-second budget covers its whole lifecycle after the first ID.
            first = outcome["generations"][0]
            generation_deadline -= time.monotonic()-phase_started-first["initial_create_latency_seconds"]
            if generation_deadline <= 0:
                outcome["generations"].pop()
                outcome.update(status="background_timeout_cancelled", provider_generation_count=attempt,
                               repair_count=max(0, attempt-1))
                break
        output = generation(client, prompt, generation_deadline, record, persist)
        outcome["transport_success"] |= record.get("transport_success", False)
        outcome["status"] = record["status"]
        if output is None:
            break
        stage = "structured_parse_failure"
        try:
            raw = _parse_structured_response(output)
            stage = "contract10_validation_failure"
            validated = validate_relations(text, entities, raw)
        except RelationValidationError as error:
            record.update(status=stage, validation_error=redact(str(error)))
            outcome["status"] = stage
            persist()
            if attempt == 2:
                break
            prompt = _build_prompt(text, entities, RELATION_EXTRACTION_SYSTEM_PROMPT,
                repair=f"The previous response failed validation: {error}. Return a corrected structured response only.")
        else:
            # Validation already verified exact occurrence; count distinct half-open source spans.
            spans = {(text.find(r.evidence), text.find(r.evidence)+len(r.evidence)) for r in validated.relations}
            record.update(status="success", validated_relation_count=len(validated.relations))
            outcome.update(status="success", contract10_success=True,
                validated_relation_count=len(validated.relations), unique_evidence_span_count=len(spans),
                validated_relations=validated.to_dict()["relations"])
            break
    outcome["total_elapsed_seconds"] = round(time.monotonic()-phase_started, 3)
    persist()
    return outcome


def run():
    global SECRET
    if (REPORT / "synthetic_background.json").exists():
        raise RuntimeError("Generation record exists; refusing a duplicate experiment")
    preflight = prepare()
    SECRET = env_value(env_value("OPENAI_API_KEY_ENV") or "OPENAI_API_KEY") or ""
    if not SECRET:
        raise RuntimeError("OpenAI API credential unavailable")
    client = OpenAI(api_key=SECRET, base_url=env_value("OPENAI_BASE_URL") or None, max_retries=0, timeout=20)
    write("poll_history.json", HISTORY)
    real = dict(status="not_run", reason="Phase A must succeed")
    write("real_passage_background.json", real)
    control = phase(client, "synthetic_background.json", SYNTHETIC, SYNTHETIC_ENTITIES, 120)
    if control["contract10_success"]:
        _, text, entities = frozen()
        real = phase(client, "real_passage_background.json", text, entities, 480)
    else:
        real["reason"] = "Contract stopped after background synthetic control failed"
        write("real_passage_background.json", real)
    final = baseline()
    summary = dict(status=real["status"] if control["contract10_success"] else control["status"],
                   baseline=preflight["baseline"], background_control=control, real_passage=real,
                   final_baseline=final, production_code_unchanged=True,
                   production_model_default_unchanged=final["production_model_default"] == preflight["baseline"]["production_model_default"],
                   nothing_committed_or_pushed=True)
    write("summary.json", summary)
    def compact(outcome):
        result = {key: value for key, value in outcome.items() if key not in ("generations", "validated_relations")}
        result["generations"] = [{key: value for key, value in record.items()
                                  if key != "structured_output"} for record in outcome.get("generations", [])]
        return json.dumps(result, ensure_ascii=False, indent=2)
    lines = ["# Contract 11S", "", "## BASELINE", f"HEAD: {final['head']}",
             "Production diff: empty", "", "## BACKGROUND CONTROL", "```json", compact(control), "```",
             "", "## REAL PASSAGE", "```json", compact(real), "```", "",
             "Production code unchanged: yes", "Production model default unchanged: yes", "Nothing committed or pushed: yes"]
    (REPORT / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "control_status": control["status"], "real_status": real["status"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.prepare == args.run:
        parser.error("Choose exactly one of --prepare or --run")
    if args.prepare:
        print(json.dumps(prepare()))
    else:
        run()
