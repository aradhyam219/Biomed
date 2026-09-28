"""Run the Contract 11P one-paper chunked relation feasibility probe.

This benchmark-only harness freezes the paper and mention inputs, prepares
deterministic source-complete chunks, runs each chunk in an isolated process,
and assembles successful Contract 10 relations with the unchanged graph code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
PREVIOUS_REPORT = ROOT / "reports/luna_56_vs_6_fullpaper_11"
CORPUS_PATH = ROOT / ".cache/ner_target_domain/target_corpus.json"
PREVIOUS_PREFLIGHT = PREVIOUS_REPORT / "preflight.json"
PAPER_ID = "PMCID:PMC10770459"
REQUIRED_BRANCH = "extraction_system_v2"
REQUIRED_SHA = "1f12923ce54ab6718a00b8d8e8126536285dc6a8"
TARGET_CHARS = 8_000
MIN_TARGET_CHARS = 6_000
MAX_CHARS = 10_000
JOB_TIMEOUT_SECONDS = 600
MODEL = "gpt-6-luna"
REASONING_EFFORT = "max"
MAX_OUTPUT_TOKENS = 128_000
REPAIR_BUDGET = 2


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
        newline="",
    )
    temporary.replace(path)


def json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def git_text(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def read_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], str, list[Any], list[dict[str, Any]]]:
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import _build_prompt
    from biomedical_extractor.llm_relation_extraction import (
        RELATION_EXTRACTION_SYSTEM_PROMPT,
    )

    branch = git_text("branch", "--show-current")
    head = git_text("rev-parse", "HEAD")
    if branch != REQUIRED_BRANCH or head != REQUIRED_SHA:
        raise RuntimeError(
            f"Required baseline mismatch: expected {REQUIRED_BRANCH}@{REQUIRED_SHA}, "
            f"found {branch}@{head}"
        )
    for args in (("diff", "--quiet", "--", "src", "viewer", "tests"),
                 ("diff", "--cached", "--quiet", "--", "src", "viewer", "tests")):
        subprocess.run(["git", *args], cwd=ROOT, check=True)

    previous = json.loads(PREVIOUS_PREFLIGHT.read_text(encoding="utf-8"))
    locked = next(p for p in previous["papers"] if p["paper_id"] == PAPER_ID)
    corpus_raw = CORPUS_PATH.read_bytes()
    if sha256_bytes(corpus_raw) != previous["source_corpus"]["sha256"]:
        raise RuntimeError("Frozen target corpus file checksum differs from Contract 11")
    corpus = json.loads(corpus_raw.decode("utf-8"))
    record = next(p for p in corpus["papers"] if p["paper_id"] == PAPER_ID)
    source_text = record["text"]
    source_sha = sha256_text(source_text)
    if source_sha != locked["source_sha256"] or len(source_text) != locked["source_characters"]:
        raise RuntimeError("Frozen paper source checksum or character count differs")

    packet_path = ROOT / locked["entity_packet_path"]
    packet_raw = packet_path.read_bytes()
    packet_sha = sha256_bytes(packet_raw)
    if packet_sha != locked["entity_packet_sha256"]:
        raise RuntimeError("Frozen entity packet checksum differs from Contract 11")
    packet = json.loads(packet_raw.decode("utf-8"))
    if packet.get("paper_id") != PAPER_ID:
        raise RuntimeError("Frozen entity packet belongs to another paper")
    entities = [Entity(**item) for item in packet["entities"]]
    if len(entities) != locked["entity_mentions"]:
        raise RuntimeError("Frozen entity count differs from the prior preflight")
    input_path = packet_path.with_name("entity_input.json")
    input_raw = input_path.read_bytes()
    input_file = json.loads(input_raw.decode("utf-8"))
    serialized_entities = json.dumps(
        [entity.to_dict() for entity in entities], ensure_ascii=False, indent=2
    )
    input_sha = sha256_text(serialized_entities)
    if input_sha != locked["entity_input_sha256"]:
        raise RuntimeError("Serialized frozen entity input checksum differs")
    if input_file != [entity.to_dict() for entity in entities]:
        raise RuntimeError("entity_input.json does not match the frozen entity packet")

    ids: set[str] = set()
    for entity in entities:
        if entity.id in ids:
            raise RuntimeError(f"Duplicate frozen mention ID: {entity.id}")
        ids.add(entity.id)
        if not (0 <= entity.start < entity.end <= len(source_text)):
            raise RuntimeError(f"Frozen mention has invalid offsets: {entity.id}")
        if source_text[entity.start : entity.end] != entity.text:
            raise RuntimeError(f"Frozen mention text/span mismatch: {entity.id}")

    segments = record["segments"]
    prior_end = 0
    for segment in segments:
        start, end = int(segment["start"]), int(segment["end"])
        if start < prior_end or not (0 <= start <= end <= len(source_text)):
            raise RuntimeError("Frozen corpus segment ranges are invalid")
        if source_text[start:end] != segment["text"]:
            raise RuntimeError("Frozen corpus segment text does not match its range")
        prior_end = end

    chunk_specs = make_chunks(source_text, segments, entities)
    chunks: list[dict[str, Any]] = []
    for index, (start, end, boundary_kind) in enumerate(chunk_specs, start=1):
        chunk_id = f"chunk_{index:03d}"
        local_entities = []
        absolute_entities = []
        for entity in entities:
            if start <= entity.start and entity.end <= end:
                local = entity.to_dict()
                local["start"] -= start
                local["end"] -= start
                local_entities.append(local)
                absolute = entity.to_dict()
                absolute["absolute_start"] = entity.start
                absolute["absolute_end"] = entity.end
                absolute_entities.append(absolute)
        chunk_text = source_text[start:end]
        prompt = _build_prompt(
            chunk_text,
            [Entity(**item) for item in local_entities],
            RELATION_EXTRACTION_SYSTEM_PROMPT,
        )
        source_path = REPORT / "chunks" / f"{chunk_id}_source.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(chunk_text.encode("utf-8"))
        chunks.append(
            {
                "chunk_id": chunk_id,
                "absolute_source_range": {"start": start, "end": end},
                "boundary_kind": boundary_kind,
                "source_characters": end - start,
                "source_text_sha256": sha256_text(chunk_text),
                "source_path": source_path.relative_to(ROOT).as_posix(),
                "entity_count": len(local_entities),
                "entity_packet": absolute_entities,
                "provider_entities": local_entities,
                "prompt_sha256": sha256_text(prompt),
            }
        )
    if not chunks or chunks[0]["absolute_source_range"]["start"] != 0:
        raise RuntimeError("Chunk plan does not begin at source character zero")
    for left, right in zip(chunks, chunks[1:]):
        if left["absolute_source_range"]["end"] != right["absolute_source_range"]["start"]:
            raise RuntimeError("Chunk plan has a gap or overlap")
    if chunks[-1]["absolute_source_range"]["end"] != len(source_text):
        raise RuntimeError("Chunk plan does not cover the complete source")
    if sum(chunk["entity_count"] for chunk in chunks) != len(entities):
        raise RuntimeError("Chunk packets do not contain every frozen mention exactly once")

    prompt_sha = sha256_text(RELATION_EXTRACTION_SYSTEM_PROMPT)
    return (
        {
            "branch": branch,
            "repository_sha": head,
            "production_code_diff": "none in src/, viewer/, or tests/",
        },
        {
            "paper_id": PAPER_ID,
            "source_characters": len(source_text),
            "source_sha256": source_sha,
            "source_corpus_path": CORPUS_PATH.relative_to(ROOT).as_posix(),
            "source_corpus_file_sha256": sha256_bytes(corpus_raw),
            "frozen_entity_count": len(entities),
            "frozen_entity_packet_path": packet_path.relative_to(ROOT).as_posix(),
            "frozen_entity_packet_sha256": packet_sha,
            "frozen_entity_input_path": input_path.relative_to(ROOT).as_posix(),
            "frozen_entity_input_file_sha256": sha256_bytes(input_raw),
            "frozen_entity_input_sha256": input_sha,
            "frozen_entity_input_expected_sha256": locked["entity_input_sha256"],
            "previous_preflight_path": PREVIOUS_PREFLIGHT.relative_to(ROOT).as_posix(),
            "previous_preflight_source_sha256": locked["source_sha256"],
            "previous_preflight_entity_packet_sha256": locked["entity_packet_sha256"],
        },
        source_text,
        entities,
        chunks,
    )


def make_chunks(text: str, segments: list[dict[str, Any]], entities: list[Any]) -> list[tuple[int, int, str]]:
    """Cut at section/paragraph boundaries, then sentence/whitespace fallbacks."""

    boundaries: dict[int, str] = {}
    previous_section: str | None = None
    for segment in segments:
        start = int(segment["start"])
        section = str(segment["section"])
        if start > 0:
            boundaries[start] = "section" if section != previous_section else "paragraph"
        previous_section = section
    boundaries[len(text)] = "end_of_source"

    def safe(position: int) -> bool:
        return not any(entity.start < position < entity.end for entity in entities)

    sentence_boundaries = {
        match.end()
        for match in re.finditer(r"[.!?](?:[\]\)\"’']*)\s+", text)
    }
    whitespace_boundaries = {
        index + 1 for index, char in enumerate(text) if char.isspace()
    }
    result: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        if len(text) - start <= MAX_CHARS:
            result.append((start, len(text), "end_of_source"))
            break
        hard_end = min(len(text), start + MAX_CHARS)
        target = min(len(text), start + TARGET_CHARS)
        lower = min(hard_end, start + MIN_TARGET_CHARS)

        selected: tuple[int, str] | None = None
        for kind in ("section", "paragraph"):
            candidates = [
                position
                for position, boundary_kind in boundaries.items()
                if boundary_kind == kind
                and lower <= position <= hard_end
                and safe(position)
            ]
            if candidates:
                selected = (min(candidates, key=lambda p: (abs(p - target), p)), kind)
                break
        if selected is None:
            for kind, candidates_all in (
                ("sentence", sentence_boundaries),
                ("whitespace", whitespace_boundaries),
            ):
                candidates = [
                    p for p in candidates_all if lower <= p <= hard_end and safe(p)
                ]
                if candidates:
                    selected = (min(candidates, key=lambda p: (abs(p - target), p)), kind)
                    break
        if selected is None:
            eof = len(text)
            if eof <= hard_end and safe(eof):
                selected = (eof, "end_of_source")
        if selected is None:
            raise RuntimeError(f"No safe chunk boundary after source offset {start}")
        end, kind = selected
        if end <= start:
            raise RuntimeError("Chunker did not advance")
        result.append((start, end, kind))
        start = end
    return result


def prepare() -> None:
    from biomedical_extractor.llm_relation_extraction import (
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _structured_payload_schema,
    )

    existing = [
        path
        for path in REPORT.rglob("*")
        if path.is_file()
        and path.resolve() != Path(__file__).resolve()
        and not (path.parent.name == "chunks" and path.name.endswith("_source.txt"))
        and path.name not in {"preflight.json", "chunk_manifest.json"}
    ]
    if existing:
        raise RuntimeError(f"Pilot report directory already contains artifacts: {existing}")
    baseline, paper, source_text, entities, manifest_chunks = read_frozen_inputs()
    schema = _structured_payload_schema().model_json_schema()
    schema_sha = sha256_text(
        json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    previous = json.loads(PREVIOUS_PREFLIGHT.read_text(encoding="utf-8"))
    prompt_sha = sha256_text(RELATION_EXTRACTION_SYSTEM_PROMPT)
    if prompt_sha != previous["configuration"]["system_prompt_sha256"]:
        raise RuntimeError("Current Contract 10 relation prompt differs from prior preflight")
    if schema != previous["configuration"]["structured_schema"]:
        raise RuntimeError("Current Contract 10 structured schema differs from prior preflight")
    api_key_env = os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
    if not os.getenv(api_key_env):
        raise RuntimeError(f"OpenAI credentials are unavailable; set {api_key_env}")
    preflight = {
        "contract": "Codex Contract 11P",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": baseline,
        "paper": paper,
        "chunking": {
            "target_characters": TARGET_CHARS,
            "hard_max_characters": MAX_CHARS,
            "boundary_preference": ["section", "paragraph", "sentence", "safe_whitespace"],
            "non_overlapping": True,
            "complete_source_coverage": True,
            "chunk_count": len(manifest_chunks),
            "chunk_boundaries": [
                {
                    "chunk_id": item["chunk_id"],
                    **item["absolute_source_range"],
                    "characters": item["source_characters"],
                    "boundary_kind": item["boundary_kind"],
                    "source_text_sha256": item["source_text_sha256"],
                    "entity_count": item["entity_count"],
                    "prompt_sha256": item["prompt_sha256"],
                }
                for item in manifest_chunks
            ],
        },
        "model": MODEL,
        "provider": "OpenAI Responses API",
        "reasoning_effort": REASONING_EFFORT,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "repair_budget": REPAIR_BUDGET,
        "provider_retries": 0,
        "temperature": "not set",
        "prompt_sha256": prompt_sha,
        "structured_schema_sha256": schema_sha,
        "contract_10_prompt_matches_previous_preflight": True,
        "contract_10_schema_matches_previous_preflight": True,
        "credentials_available": True,
        "scheduled_gpt6_jobs": len(manifest_chunks),
        "per_job_timeout_seconds": JOB_TIMEOUT_SECONDS,
        "paper_role_enrichment": "disabled",
    }
    write_json(REPORT / "preflight.json", preflight)
    write_json(
        REPORT / "chunk_manifest.json",
        {"paper_id": PAPER_ID, "source_sha256": paper["source_sha256"], "chunks": manifest_chunks},
    )
    print(f"Paper: {PAPER_ID}")
    print(f"Source characters: {len(source_text)}")
    print(f"Frozen mentions: {len(entities)}")
    print(f"Chunks: {len(manifest_chunks)}")
    print(f"Scheduled GPT-6 jobs: {len(manifest_chunks)}")
def run_worker(chunk_id: str) -> None:
    from langchain_openai import ChatOpenAI
    from langchain_core.callbacks import BaseCallbackHandler
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import (
        LLMRelationExtractor,
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _structured_payload_schema,
    )
    from biomedical_extractor.relation_extraction import RelationExtractionError

    manifest = json.loads((REPORT / "chunk_manifest.json").read_text(encoding="utf-8"))
    item = next(chunk for chunk in manifest["chunks"] if chunk["chunk_id"] == chunk_id)
    chunk_text = (ROOT / item["source_path"]).read_bytes().decode("utf-8")
    entities = [Entity(**entity) for entity in item["provider_entities"]]
    if sha256_text(chunk_text) != item["source_text_sha256"]:
        raise RuntimeError("Chunk source checksum changed before worker start")

    api_key_env = os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"OpenAI credentials are unavailable; set {api_key_env}")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    model_kwargs: dict[str, Any] = {
        "model": MODEL,
        "api_key": api_key,
        "use_responses_api": True,
        "reasoning": {"effort": REASONING_EFFORT},
        "max_retries": 0,
        "max_completion_tokens": MAX_OUTPUT_TOKENS,
    }
    if base_url is not None:
        model_kwargs["base_url"] = base_url
    chat_model = ChatOpenAI(**model_kwargs)

    progress_path = REPORT / "chunks" / f"{chunk_id}.progress.json"
    state: dict[str, Any] = {"chunk_id": chunk_id, "attempts": []}

    class UsageHandler(BaseCallbackHandler):
        def __init__(self, attempt: dict[str, Any]) -> None:
            self.attempt = attempt

        def on_llm_end(self, response: Any, **kwargs: Any) -> None:
            in_tokens = out_tokens = total_tokens = None
            for generations in getattr(response, "generations", ()):
                for generation in generations:
                    message = getattr(generation, "message", None)
                    usage = getattr(message, "usage_metadata", None) or {}
                    metadata = getattr(message, "response_metadata", None) or {}
                    token_usage = metadata.get("token_usage", {}) if isinstance(metadata, dict) else {}
                    generation_info = getattr(generation, "generation_info", None) or {}
                    token_usage = token_usage or generation_info.get("token_usage", {})
                    in_tokens = in_tokens if in_tokens is not None else usage.get("input_tokens", token_usage.get("prompt_tokens"))
                    out_tokens = out_tokens if out_tokens is not None else usage.get("output_tokens", token_usage.get("completion_tokens"))
                    total_tokens = total_tokens if total_tokens is not None else usage.get("total_tokens", token_usage.get("total_tokens"))
            self.attempt["input_tokens"] = in_tokens
            self.attempt["output_tokens"] = out_tokens
            self.attempt["total_tokens"] = total_tokens

    class CapturingRunnable:
        def __init__(self, runnable: Any) -> None:
            self.runnable = runnable

        def invoke(self, prompt: str) -> Any:
            number = len(state["attempts"]) + 1
            attempt = {
                "attempt": number,
                "repair": "\n\nREPAIR INSTRUCTION:\n" in prompt,
                "prompt_sha256": sha256_text(prompt),
                "status": "running",
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            }
            state["attempts"].append(attempt)
            write_json(progress_path, state)
            started = time.monotonic()
            try:
                response = self.runnable.invoke(
                    prompt, config={"callbacks": [UsageHandler(attempt)]}
                )
            except BaseException as error:
                attempt["status"] = "provider_or_parser_error"
                attempt["elapsed_seconds"] = round(time.monotonic() - started, 3)
                attempt["error_type"] = type(error).__name__
                attempt["error"] = str(error)
                write_json(progress_path, state)
                raise
            attempt["status"] = "response_received"
            attempt["elapsed_seconds"] = round(time.monotonic() - started, 3)
            attempt["structured_output"] = response
            write_json(progress_path, state)
            return response

    class InstrumentedModel:
        def with_structured_output(self, schema: Any) -> CapturingRunnable:
            if schema.__name__ != _structured_payload_schema().__name__:
                raise RuntimeError("Unexpected structured relation schema")
            return CapturingRunnable(chat_model.with_structured_output(schema))

    extractor = LLMRelationExtractor(
        InstrumentedModel(), max_retries=REPAIR_BUDGET, prompt=RELATION_EXTRACTION_SYSTEM_PROMPT
    )
    started = time.monotonic()
    try:
        result = extractor.extract_relations(chunk_text, entities)
    except BaseException as error:
        status = "validation_failure" if (
            isinstance(error, RelationExtractionError)
            and "remained invalid after" in str(error)
        ) else "provider_failure"
        outcome = {
            "chunk_id": chunk_id,
            "status": status,
            "error_type": type(error).__name__,
            "exact_error": str(error),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "attempts": state["attempts"],
        }
    else:
        outcome = {
            "chunk_id": chunk_id,
            "status": "success",
            "relations": result.to_dict()["relations"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "attempts": state["attempts"],
        }
    write_json(REPORT / "chunks" / f"{chunk_id}.worker.json", outcome)
    write_json(progress_path, state)


def run_pilot() -> None:
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.entity_assembly import assemble_document_entities
    from biomedical_extractor.graph import build_graph_result
    from biomedical_extractor.relation_extraction import Relation

    preflight = json.loads((REPORT / "preflight.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPORT / "chunk_manifest.json").read_text(encoding="utf-8"))
    chunks = manifest["chunks"]
    if any((REPORT / "chunks" / f"{item['chunk_id']}.json").exists() for item in chunks):
        raise RuntimeError("Chunk results already exist; live jobs will not be repeated")
    run_started = time.monotonic()
    outcomes: list[dict[str, Any]] = []
    consecutive_failures = 0
    stop_reason = None
    for item in chunks:
        chunk_id = item["chunk_id"]
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", chunk_id]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=JOB_TIMEOUT_SECONDS,
                check=False,
            )
            elapsed = time.monotonic() - started
            worker_path = REPORT / "chunks" / f"{chunk_id}.worker.json"
            if worker_path.exists():
                worker = json.loads(worker_path.read_text(encoding="utf-8"))
            else:
                progress = REPORT / "chunks" / f"{chunk_id}.progress.json"
                attempts = json.loads(progress.read_text(encoding="utf-8")).get("attempts", []) if progress.exists() else []
                detail = completed.stderr.strip() or completed.stdout.strip() or f"worker exited {completed.returncode} without a result"
                worker = {
                    "chunk_id": chunk_id,
                    "status": "worker_failure",
                    "error_type": "WorkerProcessError",
                    "exact_error": detail,
                    "attempts": attempts,
                }
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - started
            progress = REPORT / "chunks" / f"{chunk_id}.progress.json"
            attempts = json.loads(progress.read_text(encoding="utf-8")).get("attempts", []) if progress.exists() else []
            worker = {
                "chunk_id": chunk_id,
                "status": "timeout",
                "error_type": "JobTimeout",
                "exact_error": f"Worker exceeded the {JOB_TIMEOUT_SECONDS}-second wall-clock ceiling and was terminated; no manual rerun was made.",
                "attempts": attempts,
            }
        attempts = worker.get("attempts", [])
        successful = worker.get("status") == "success"
        artifact = {
            "chunk_id": chunk_id,
            "status": worker.get("status", "worker_failure"),
            "paper_id": PAPER_ID,
            "absolute_source_range": item["absolute_source_range"],
            "source_text_sha256": item["source_text_sha256"],
            "source_characters": item["source_characters"],
            "entity_count": item["entity_count"],
            "entity_packet": item["entity_packet"],
            "provider_entities_with_chunk_local_offsets": item["provider_entities"],
            "validated_relations": worker.get("relations", []),
            "provider_attempts": len(attempts),
            "repair_attempts": sum(bool(attempt.get("repair")) for attempt in attempts),
            "attempts": attempts,
            "elapsed_seconds": round(elapsed, 3),
            "worker_elapsed_seconds": worker.get("elapsed_seconds"),
            "input_tokens": token_sum(attempts, "input_tokens"),
            "output_tokens": token_sum(attempts, "output_tokens"),
        }
        if not successful:
            artifact["error_type"] = worker.get("error_type")
            artifact["exact_error"] = worker.get("exact_error")
        write_json(REPORT / "chunks" / f"{chunk_id}.json", artifact)
        outcomes.append(artifact)
        consecutive_failures = 0 if successful else consecutive_failures + 1
        attempted = len(outcomes)
        failed = sum(outcome["status"] != "success" for outcome in outcomes)
        if consecutive_failures >= 3:
            stop_reason = "three_consecutive_chunks_failed_or_timed_out"
        elif failed / attempted > 0.25:
            stop_reason = "failed_or_timed_out_fraction_exceeded_25_percent"
        if stop_reason:
            break

    if stop_reason:
        for item in chunks[len(outcomes) :]:
            artifact = {
                "chunk_id": item["chunk_id"],
                "status": "not_attempted_due_stop_condition",
                "paper_id": PAPER_ID,
                "absolute_source_range": item["absolute_source_range"],
                "source_text_sha256": item["source_text_sha256"],
                "source_characters": item["source_characters"],
                "entity_count": item["entity_count"],
                "entity_packet": item["entity_packet"],
                "provider_entities_with_chunk_local_offsets": item["provider_entities"],
                "validated_relations": [],
                "provider_attempts": 0,
                "repair_attempts": 0,
                "attempts": [],
                "elapsed_seconds": 0,
                "error_type": "StopCondition",
                "exact_error": stop_reason,
            }
            write_json(REPORT / "chunks" / f"{item['chunk_id']}.json", artifact)

    all_relations = []
    relation_origins = []
    for outcome in outcomes:
        if outcome["status"] != "success":
            continue
        for relation_data in outcome["validated_relations"]:
            all_relations.append(Relation(**relation_data))
            relation_origins.append(
                {
                    "relation_index": len(all_relations) - 1,
                    "chunk_id": outcome["chunk_id"],
                    "absolute_source_range": outcome["absolute_source_range"],
                }
            )

    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    source_text = next(p for p in corpus["papers"] if p["paper_id"] == PAPER_ID)["text"]
    frozen_packet = json.loads(
        (PREVIOUS_REPORT / "papers/pmcid_pmc10770459/entities.json").read_text(encoding="utf-8")
    )
    original_entities = [Entity(**item) for item in frozen_packet["entities"]]
    assembly = assemble_document_entities(original_entities, source_text)
    graph = build_graph_result(PAPER_ID, assembly, tuple(all_relations))
    graph_data = graph.to_dict()
    write_json(
        REPORT / "full_paper_relations.json",
        {
            "paper_id": PAPER_ID,
            "source_sha256": manifest["source_sha256"],
            "relation_count": len(all_relations),
            "successful_chunk_ids": [o["chunk_id"] for o in outcomes if o["status"] == "success"],
            "relation_origins": relation_origins,
            "relations": [relation.to_dict() for relation in all_relations],
        },
    )
    write_json(REPORT / "full_paper_graph.json", graph_data)

    successful_chars = sum(
        outcome["source_characters"]
        for outcome in outcomes
        if outcome["status"] == "success"
    )
    evidence_spans = set()
    ambiguous_evidence_relations = 0
    for outcome in outcomes:
        if outcome["status"] != "success":
            continue
        chunk_start = outcome["absolute_source_range"]["start"]
        chunk_text = (ROOT / next(c["source_path"] for c in chunks if c["chunk_id"] == outcome["chunk_id"])).read_bytes().decode("utf-8")
        for relation_data in outcome["validated_relations"]:
            evidence = relation_data["evidence"]
            matches = find_occurrences(chunk_text, evidence)
            if len(matches) > 1:
                ambiguous_evidence_relations += 1
            evidence_spans.update(
                (chunk_start + start, chunk_start + start + len(evidence))
                for start in matches
            )
    attempts = [attempt for outcome in outcomes for attempt in outcome.get("attempts", [])]
    metrics = {
        "total_chunks": len(chunks),
        "attempted_chunks": len(outcomes),
        "successful_chunks": sum(outcome["status"] == "success" for outcome in outcomes),
        "validation_failures": sum(outcome["status"] == "validation_failure" for outcome in outcomes),
        "timeouts": sum(outcome["status"] == "timeout" for outcome in outcomes),
        "other_chunk_failures": sum(outcome["status"] not in ("success", "validation_failure", "timeout") for outcome in outcomes),
        "provider_attempts": sum(outcome["provider_attempts"] for outcome in outcomes),
        "repair_attempts": sum(outcome["repair_attempts"] for outcome in outcomes),
        "total_relations": len(all_relations),
        "unique_evidence_spans": len(evidence_spans),
        "evidence_span_method": "Count distinct exact occurrences of validated evidence strings within successful source chunks; repeated occurrences in a chunk are included as candidate spans.",
        "relations_with_ambiguous_evidence_occurrence": ambiguous_evidence_relations,
        "total_input_tokens": token_sum(attempts, "input_tokens"),
        "total_output_tokens": token_sum(attempts, "output_tokens"),
        "token_usage_attempts_with_input_count": sum(a.get("input_tokens") is not None for a in attempts),
        "token_usage_attempts_with_output_count": sum(a.get("output_tokens") is not None for a in attempts),
        "total_elapsed_seconds": round(time.monotonic() - run_started, 3),
        "successful_source_characters": successful_chars,
        "source_coverage_percent": round(100 * successful_chars / len(source_text), 4),
        "graph_node_count": len(graph_data["nodes"]),
        "graph_edge_count": len(graph_data["edges"]),
        "stop_reason": stop_reason,
        "viewer_smoke": "pending",
    }
    summary = {
        "contract": "Codex Contract 11P",
        "baseline": preflight["baseline"],
        "paper": {
            "paper_id": PAPER_ID,
            "source_characters": len(source_text),
            "source_sha256": manifest["source_sha256"],
            "frozen_entity_count": len(original_entities),
            "chunk_count": len(chunks),
        },
        "execution": metrics,
        "failures": [
            {
                "chunk_id": outcome["chunk_id"],
                "source_range": outcome["absolute_source_range"],
                "exact_failure": outcome.get("exact_error"),
                "attempt_count": outcome["provider_attempts"],
                "repair_count": outcome["repair_attempts"],
                "elapsed_seconds": outcome["elapsed_seconds"],
            }
            for outcome in outcomes
            if outcome["status"] != "success"
        ],
        "artifacts": {
            "preflight": (REPORT / "preflight.json").relative_to(ROOT).as_posix(),
            "chunk_manifest": (REPORT / "chunk_manifest.json").relative_to(ROOT).as_posix(),
            "chunk_results": (REPORT / "chunks").relative_to(ROOT).as_posix(),
            "full_paper_relations": (REPORT / "full_paper_relations.json").relative_to(ROOT).as_posix(),
            "full_paper_graph": (REPORT / "full_paper_graph.json").relative_to(ROOT).as_posix(),
            "screenshot": (REPORT / "viewer_default.png").relative_to(ROOT).as_posix(),
            "summary_markdown": (REPORT / "summary.md").relative_to(ROOT).as_posix(),
            "summary_json": (REPORT / "summary.json").relative_to(ROOT).as_posix(),
        },
        "production_code_modified": False,
    }
    write_json(REPORT / "summary.json", summary)
    write_summary_markdown(summary)


def token_sum(attempts: list[dict[str, Any]], key: str) -> int | None:
    values = [attempt.get(key) for attempt in attempts if attempt.get(key) is not None]
    return sum(int(value) for value in values) if values else None


def find_occurrences(source: str, value: str) -> list[int]:
    if not value:
        return []
    positions = []
    start = 0
    while True:
        position = source.find(value, start)
        if position < 0:
            break
        positions.append(position)
        start = position + 1
    return positions


def write_summary_markdown(summary: dict[str, Any]) -> None:
    p, e, f = summary["paper"], summary["execution"], summary["failures"]
    baseline = summary["baseline"]
    input_tokens = e["total_input_tokens"] if e["total_input_tokens"] is not None else "unavailable"
    output_tokens = e["total_output_tokens"] if e["total_output_tokens"] is not None else "unavailable"
    lines = [
        "# Contract 11P — Full-Paper Feasibility Probe",
        "",
        f"- Baseline: `{baseline['branch']}@{baseline['repository_sha']}`",
        f"- Paper: `{p['paper_id']}`; {p['source_characters']:,} source characters; {p['frozen_entity_count']} frozen mentions; {p['chunk_count']} chunks.",
        "- Production-code diff: none in `src/`, `viewer/`, or `tests/`.",
        "",
        "## Execution",
        "",
        f"- Successful chunks: {e['successful_chunks']}/{e['total_chunks']} (attempted {e['attempted_chunks']}); validation failures {e['validation_failures']}; timeouts {e['timeouts']}; other failures {e['other_chunk_failures']}.",
        f"- Provider attempts: {e['provider_attempts']}; repairs: {e['repair_attempts']}; elapsed: {e['total_elapsed_seconds']} seconds.",
        f"- Tokens: input {input_tokens}; output {output_tokens} (usage recorded for {e['token_usage_attempts_with_input_count']}/{e['provider_attempts']} input and {e['token_usage_attempts_with_output_count']}/{e['provider_attempts']} output attempts).",
        f"- Validated relations: {e['total_relations']}; unique evidence spans: {e['unique_evidence_spans']}; source coverage by successful chunks: {e['source_coverage_percent']}%.",
        f"- Graph: {e['graph_node_count']} nodes, {e['graph_edge_count']} edges. Viewer smoke: {e['viewer_smoke']}.",
        f"- Stop condition: {e['stop_reason'] or 'none'}.",
        "",
        "## Viewer smoke",
        "",
    ]
    viewer = summary.get("viewer_smoke_details")
    if viewer:
        lines.extend(
            [
                f"- Graph load: {viewer['graph_load']}; console errors/warnings: {viewer['console_errors_and_warnings']}; node inspection: {viewer['node_inspection']}.",
                f"- Edge inspection: {viewer['edge_inspection']}; relation bundles: {viewer['relation_bundles']}.",
                f"- Default-layout screenshot: {viewer['screenshot_status']}.",
                "",
            ]
        )
    lines.extend([
        "## Failed chunks",
        "",
    ])
    if not f:
        lines.append("None.")
    else:
        for failure in f:
            lines.extend(
                [
                    f"- `{failure['chunk_id']}` range `{failure['source_range']['start']}:{failure['source_range']['end']}`; attempts {failure['attempt_count']}; repairs {failure['repair_count']}; elapsed {failure['elapsed_seconds']} seconds.",
                    f"  Error: `{failure['exact_failure']}`",
                ]
            )
    lines.extend(["", "## Artifacts", ""])
    for name, path in summary["artifacts"].items():
        lines.append(f"- {name}: `{path}`" if path is not None else f"- {name}: not persisted")
    lines.extend(["", "No scientific-quality judgment is included in this feasibility probe.", ""])
    (REPORT / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--worker")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        run_pilot()
    elif args.worker:
        run_worker(args.worker)
    else:
        parser.error("choose --prepare, --run, or --worker CHUNK_ID")


if __name__ == "__main__":
    main()
