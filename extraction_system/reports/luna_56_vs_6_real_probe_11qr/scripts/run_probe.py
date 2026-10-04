"""Run the blinded Contract 11Q-R real-passage relation probe.

The harness freezes passage selection and passage-local mention packets before
starting a provider process.  Provider calls run in one child process per
passage/model job so the parent can enforce the external watchdog without
changing the Contract 10 production harness or its validation behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


REPOSITORY = Path(__file__).resolve().parents[3]
GIT_ROOT = REPOSITORY.parent
REPORT = REPOSITORY / "reports" / "luna_56_vs_6_real_probe_11qr"
SCRIPT_PATH = REPORT / "scripts" / "run_probe.py"
CORPUS_PATH = REPOSITORY / ".cache" / "ner_target_domain" / "target_corpus.json"
REFERENCE_REPORT = REPOSITORY / "reports" / "luna_56_vs_6_fullpaper_11"
REFERENCE_PREFLIGHT = REFERENCE_REPORT / "preflight.json"
MODEL_CACHE = REPOSITORY / ".cache" / "model_ab_11qr"
MODEL_KEY_PATH = MODEL_CACHE / "model_key.json"
PREFLIGHT_PATH = REPORT / "preflight.json"
STATE_PATH = REPORT / "probe_state.json"
EXPECTED_HEAD = "7f388368a8bd06f35f60eda37eb2ccdce711eed8"
EXPECTED_BRANCH = "extraction_system_v2"
PAPER_IDS = (
    "PMCID:PMC10770459",
    "PMCID:PMC11824863",
    "PMCID:PMC8605525",
)
MODEL_ALIASES = ("Model A", "Model B")
MODEL_IDS = ("gpt-5.6-luna", "gpt-6-luna")
PASSAGE_TARGET = 1500
PASSAGE_MIN = 1200
PASSAGE_MAX = 2000
WATCHDOG_SECONDS = 240
REPAIR_BUDGET = 2
PROVIDER_RETRIES = 0
REASONING_EFFORT = "max"
MAX_OUTPUT_TOKENS = 128000

EXECUTION_ORDER = (
    (1, "passage_001", "Model A"),
    (2, "passage_001", "Model B"),
    (3, "passage_002", "Model B"),
    (4, "passage_002", "Model A"),
    (5, "passage_003", "Model A"),
    (6, "passage_003", "Model B"),
    (7, "passage_004", "Model B"),
    (8, "passage_004", "Model A"),
    (9, "passage_005", "Model A"),
    (10, "passage_005", "Model B"),
)


def sha256_bytes(value: bytes) -> str:
    """Return the hexadecimal SHA-256 digest for exact bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    """Hash a stable compact JSON representation."""

    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def json_bytes(value: Any) -> bytes:
    """Serialize a value using the provider-input packet formatting."""

    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    """Atomically write one UTF-8 JSON artifact with a final newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def now_utc() -> str:
    """Return an explicit UTC timestamp for operational artifacts."""

    return datetime.now(timezone.utc).isoformat()


def git(*args: str) -> str:
    """Read repository state from the parent Git root."""

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


def production_state() -> dict[str, Any]:
    """Return the exact production/test path state relevant to the probe."""

    pathspec = (
        "extraction_system/src",
        "extraction_system/viewer",
        "extraction_system/tests",
    )
    unstaged = git("diff", "--", *pathspec)
    staged = git("diff", "--cached", "--", *pathspec)
    status = git("status", "--short", "--", *pathspec)
    return {
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "unstaged_diff": unstaged,
        "staged_diff": staged,
        "status": status,
        "clean": not any((unstaged, staged, status)),
    }


def require_clean_baseline() -> dict[str, Any]:
    """Fail closed if the requested repository baseline is not present."""

    state = production_state()
    if state["head"] != EXPECTED_HEAD:
        raise RuntimeError(
            f"Unexpected repository HEAD: {state['head']} != {EXPECTED_HEAD}"
        )
    if state["branch"] != EXPECTED_BRANCH:
        raise RuntimeError(
            f"Unexpected repository branch: {state['branch']} != {EXPECTED_BRANCH}"
        )
    if not state["clean"]:
        raise RuntimeError("Production, viewer, or test paths are modified")
    return state


def read_env_value(name: str) -> str | None:
    """Read one dotenv value without printing or serializing credentials."""

    value = os.environ.get(name)
    if value:
        return value
    dotenv = REPOSITORY / ".env"
    if not dotenv.is_file():
        return None
    for raw_line in dotenv.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, candidate = line.partition("=")
        if separator and key.strip() == name:
            candidate = candidate.strip()
            if len(candidate) >= 2 and candidate[0] == candidate[-1]:
                if candidate[0] in {"'", '"'}:
                    candidate = candidate[1:-1]
            return candidate or None
    return None


def redact_error(message: str, api_key: str) -> str:
    """Remove credentials from an operational error while retaining detail."""

    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = re.sub(r"sk-[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
    message = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)
    return message[:2000]


def load_model_key() -> dict[str, str]:
    """Load and validate the separately stored blinded model mapping."""

    if not MODEL_KEY_PATH.is_file():
        raise RuntimeError(f"Missing separate model key: {MODEL_KEY_PATH}")
    value = json.loads(MODEL_KEY_PATH.read_text(encoding="utf-8"))
    if (
        not isinstance(value, Mapping)
        or set(value) != {"model_a", "model_b"}
        or set(value.values()) != set(MODEL_IDS)
    ):
        raise RuntimeError("The separate blinded model key is invalid")
    return {"Model A": str(value["model_a"]), "Model B": str(value["model_b"])}


def create_model_key() -> None:
    """Create the one-time random alias mapping before inference."""

    if MODEL_KEY_PATH.exists():
        load_model_key()
        return
    values = list(MODEL_IDS)
    secrets.SystemRandom().shuffle(values)
    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    write_json(
        MODEL_KEY_PATH,
        {
            "model_a": values[0],
            "model_b": values[1],
        },
    )


def slug(paper_id: str) -> str:
    """Return a stable local name for one PMCID."""

    return "pmcid_" + paper_id.split(":", 1)[1].lower()


def load_contract_modules() -> tuple[Any, Any, Any, Any, Any, Any]:
    """Import only the existing Contract 10 prompt, schema, parser, and values."""

    sys.path.insert(0, str(REPOSITORY / "src"))
    from biomedical_extractor.entity_extraction import Entity
    from biomedical_extractor.llm_relation_extraction import (
        LLMRelationExtractor,
        OpenAIConfig,
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _build_prompt,
        _structured_payload_schema,
    )

    return (
        Entity,
        LLMRelationExtractor,
        OpenAIConfig,
        RELATION_EXTRACTION_SYSTEM_PROMPT,
        _build_prompt,
        _structured_payload_schema,
    )


def frozen_reference() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify current corpus and frozen entity packets against Contract 11."""

    if not REFERENCE_PREFLIGHT.is_file():
        raise RuntimeError(f"Missing Contract 11 reference preflight: {REFERENCE_PREFLIGHT}")
    reference = json.loads(REFERENCE_PREFLIGHT.read_text(encoding="utf-8"))
    corpus_bytes = CORPUS_PATH.read_bytes()
    if sha256_bytes(corpus_bytes) != reference["source_corpus"]["sha256"]:
        raise RuntimeError("The frozen target corpus changed after Contract 11")
    corpus = json.loads(corpus_bytes.decode("utf-8"))
    corpus_by_id = {item["paper_id"]: item for item in corpus["papers"]}
    locked_by_id = {item["paper_id"]: item for item in reference["papers"]}
    if set(PAPER_IDS) - set(corpus_by_id) or set(PAPER_IDS) - set(locked_by_id):
        raise RuntimeError("The required Contract 11 papers are missing")

    (
        Entity,
        _llm_extractor,
        _openai_config,
        system_prompt,
        _build_prompt,
        structured_schema,
    ) = load_contract_modules()
    schema_sha = sha256_json(structured_schema().model_json_schema())
    if schema_sha != reference["configuration"]["schema_sha256"]:
        raise RuntimeError("The Contract 10 structured schema changed")
    prompt_sha = sha256_bytes(system_prompt.encode("utf-8"))
    if prompt_sha != reference["configuration"]["system_prompt_sha256"]:
        raise RuntimeError("The Contract 10 relation prompt changed")

    verified: dict[str, Any] = {}
    for paper_id in PAPER_IDS:
        record = corpus_by_id[paper_id]
        locked = locked_by_id[paper_id]
        text = record["text"]
        source_sha = sha256_bytes(text.encode("utf-8"))
        if source_sha != locked["source_sha256"]:
            raise RuntimeError(f"Frozen source text changed: {paper_id}")
        if len(text) != locked["source_characters"]:
            raise RuntimeError(f"Frozen source length changed: {paper_id}")
        packet_path = REFERENCE_REPORT / "papers" / slug(paper_id) / "entities.json"
        packet_bytes = packet_path.read_bytes()
        if sha256_bytes(packet_bytes) != locked["entity_packet_sha256"]:
            raise RuntimeError(f"Frozen entity packet changed: {paper_id}")
        packet = json.loads(packet_bytes.decode("utf-8"))
        entities = [Entity(**item) for item in packet["entities"]]
        entity_input_sha = sha256_bytes(
            json.dumps(
                [entity.to_dict() for entity in entities],
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
        )
        if entity_input_sha != locked["entity_input_sha256"]:
            raise RuntimeError(f"Frozen serialized entity input changed: {paper_id}")
        verified[paper_id] = {
            "record": record,
            "locked": locked,
            "packet": packet,
            "entities": entities,
            "packet_path": packet_path,
        }
    return reference, corpus, verified


def candidate_windows(text: str, entities: Sequence[Any]) -> list[dict[str, Any]]:
    """Return all valid sentence windows in deterministic rank order."""

    from biomedical_extractor.ner_reconnaissance import sentence_spans

    spans = sentence_spans(text)
    candidates: list[dict[str, Any]] = []
    for first in range(len(spans)):
        for last_exclusive in range(first + 1, len(spans) + 1):
            start = spans[first][0]
            end = spans[last_exclusive - 1][1]
            characters = end - start
            if not PASSAGE_MIN <= characters <= PASSAGE_MAX:
                continue
            count = sum(start <= item.start and item.end <= end for item in entities)
            split_entity = any(
                (item.start < end and item.end > start)
                and not (start <= item.start and item.end <= end)
                for item in entities
            )
            if split_entity:
                continue
            candidates.append(
                {
                    "start": start,
                    "end": end,
                    "characters": characters,
                    "entity_count": count,
                    "density_per_1000_chars": round(count * 1000 / characters, 6),
                    "first_sentence_index": first,
                    "last_sentence_index_exclusive": last_exclusive,
                    "distance_from_target": abs(characters - PASSAGE_TARGET),
                }
            )
    candidates.sort(
        key=lambda value: (
            -value["entity_count"],
            value["distance_from_target"],
            value["start"],
            value["end"],
        )
    )
    return candidates


def choose_window(
    text: str,
    entities: Sequence[Any],
    *,
    excluded: Sequence[Mapping[str, int]] = (),
) -> dict[str, Any]:
    """Choose the highest-count valid window outside prior windows."""

    candidates = candidate_windows(text, entities)
    for candidate in candidates:
        if all(
            candidate["end"] <= item["start"] or candidate["start"] >= item["end"]
            for item in excluded
        ):
            return candidate
    raise RuntimeError("No valid non-overlapping passage window exists")


def make_passage(
    passage_id: str,
    paper_id: str,
    verified: Mapping[str, Any],
    window: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize one frozen passage and its local and absolute mention views."""

    Entity = load_contract_modules()[0]
    text = verified["record"]["text"]
    start, end = int(window["start"]), int(window["end"])
    source_text = text[start:end]
    local_entities: list[dict[str, Any]] = []
    absolute_entities: list[dict[str, Any]] = []
    for entity in verified["entities"]:
        if not (start <= entity.start and entity.end <= end):
            continue
        local = Entity(
            id=entity.id,
            text=entity.text,
            type=entity.type,
            start=entity.start - start,
            end=entity.end - start,
            score=entity.score,
        ).to_dict()
        local_entities.append(local)
        absolute_entities.append(
            {
                "id": entity.id,
                "text": entity.text,
                "type": entity.type,
                "score": entity.score,
                "absolute_start": entity.start,
                "absolute_end": entity.end,
                "passage_start": entity.start - start,
                "passage_end": entity.end - start,
            }
        )
    return {
        "passage_id": passage_id,
        "paper_id": paper_id,
        "source_range": {"start": start, "end": end},
        "source_characters": len(source_text),
        "source_text": source_text,
        "source_sha256": sha256_bytes(source_text.encode("utf-8")),
        "selection": dict(window),
        "entity_packet": local_entities,
        "entity_packet_absolute": absolute_entities,
        "entity_count": len(local_entities),
        "entity_packet_sha256": sha256_bytes(json_bytes(local_entities)),
        "full_entity_packet_sha256": verified["locked"]["entity_packet_sha256"],
        "full_source_sha256": verified["locked"]["source_sha256"],
    }


def passage_prompt_sha(passage: Mapping[str, Any]) -> str:
    """Hash the exact Contract 10 prompt constructed for one local packet."""

    (
        Entity,
        _llm_extractor,
        _openai_config,
        system_prompt,
        build_prompt,
        _schema,
    ) = load_contract_modules()
    entities = [Entity(**item) for item in passage["entity_packet"]]
    prompt = build_prompt(passage["source_text"], entities, system_prompt)
    return sha256_bytes(prompt.encode("utf-8"))


def prepare() -> int:
    """Freeze the five passages, local packets, schedule, and separate key."""

    if STATE_PATH.exists():
        raise RuntimeError("This probe has started; do not overwrite its freeze")
    if any(
        result_path(passage_id, alias).exists()
        for _sequence, passage_id, alias in EXECUTION_ORDER
    ):
        raise RuntimeError("A provider job artifact exists; do not overwrite its freeze")
    baseline = require_clean_baseline()
    reference, corpus, verified = frozen_reference()
    create_model_key()
    passages: list[dict[str, Any]] = []
    top_windows: dict[str, dict[str, Any]] = {}
    for paper_id in PAPER_IDS:
        top_windows[paper_id] = choose_window(
            verified[paper_id]["record"]["text"], verified[paper_id]["entities"]
        )
    assignments = (
        ("passage_001", PAPER_IDS[0], top_windows[PAPER_IDS[0]]),
        ("passage_002", PAPER_IDS[1], top_windows[PAPER_IDS[1]]),
        ("passage_003", PAPER_IDS[2], top_windows[PAPER_IDS[2]]),
        (
            "passage_004",
            PAPER_IDS[0],
            choose_window(
                verified[PAPER_IDS[0]]["record"]["text"],
                verified[PAPER_IDS[0]]["entities"],
                excluded=(top_windows[PAPER_IDS[0]],),
            ),
        ),
        (
            "passage_005",
            PAPER_IDS[1],
            choose_window(
                verified[PAPER_IDS[1]]["record"]["text"],
                verified[PAPER_IDS[1]]["entities"],
                excluded=(top_windows[PAPER_IDS[1]],),
            ),
        ),
    )
    for passage_id, paper_id, window in assignments:
        passage = make_passage(passage_id, paper_id, verified[paper_id], window)
        passage["prompt_sha256"] = passage_prompt_sha(passage)
        passages.append(passage)

    passage_by_id = {item["passage_id"]: item for item in passages}
    execution = [
        {
            "sequence": sequence,
            "passage_id": passage_id,
            "paper_id": passage_by_id[passage_id]["paper_id"],
            "model": alias,
        }
        for sequence, passage_id, alias in EXECUTION_ORDER
    ]
    preflight = {
        "contract": "Codex Contract 11Q-R",
        "created_utc": now_utc(),
        "baseline": {
            "branch": baseline["branch"],
            "repository_sha": baseline["head"],
            "expected_repository_sha": EXPECTED_HEAD,
            "production_code_diff": "clean",
            "production_paths_checked": ["src", "viewer", "tests"],
        },
        "reference_contract_11_preflight": {
            "path": "reports/luna_56_vs_6_fullpaper_11/preflight.json",
            "repository_sha": reference["baseline"]["repository_sha"],
            "source_corpus_sha256_verified": True,
            "source_and_entity_packet_checksums_verified": True,
        },
        "source_corpus": {
            "path": ".cache/ner_target_domain/target_corpus.json",
            "sha256": sha256_bytes(CORPUS_PATH.read_bytes()),
            "paper_ids": list(PAPER_IDS),
            "source_text_mode": "complete frozen PMC full text",
        },
        "configuration": {
            "provider": "OpenAI Responses API",
            "reasoning_effort": REASONING_EFFORT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "bounded_repair_budget": REPAIR_BUDGET,
            "provider_retries": PROVIDER_RETRIES,
            "system_prompt_sha256": reference["configuration"]["system_prompt_sha256"],
            "schema_sha256": reference["configuration"]["schema_sha256"],
            "prompt_source": "unchanged Contract 10 RELATION_EXTRACTION_SYSTEM_PROMPT",
            "structured_schema_source": "unchanged Contract 10 _structured_payload_schema",
            "parser_validator_source": "unchanged Contract 10 LLMRelationExtractor",
            "model_id_is_explicit_in_benchmark_harness": True,
        },
        "selection": {
            "sentence_splitter": "biomedical_extractor.ner_reconnaissance.sentence_spans",
            "sentence_boundary_rule": "(?<=[.!?])\\s+",
            "target_characters": PASSAGE_TARGET,
            "acceptable_characters": [PASSAGE_MIN, PASSAGE_MAX],
            "candidate_rule": "contiguous sentence windows in range; reject any window that cuts a frozen entity",
            "rank_rule": "descending contained entity count, then closest length to target, then earliest source position",
            "second_window_rule": "rank again after excluding any source-character overlap with that paper's first window",
            "tie_break": "earliest source position",
            "completed_before_first_provider_request": True,
        },
        "blinding": {
            "aliases": list(MODEL_ALIASES),
            "model_key_path": ".cache/model_ab_11qr/model_key.json",
            "mapping_disclosed": False,
        },
        "watchdog": {
            "per_job_external_wall_clock_seconds": WATCHDOG_SECONDS,
            "consecutive_provider_or_timeout_abort_threshold": 3,
            "timeouts_are_not_retried_manually": True,
        },
        "execution_order": execution,
        "passages": [
            {
                key: value
                for key, value in passage.items()
                if key not in {"source_text", "entity_packet", "entity_packet_absolute"}
            }
            for passage in passages
        ],
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    for passage in passages:
        passage_dir = REPORT / passage["passage_id"]
        write_json(passage_dir / "manifest.json", passage)
    write_json(PREFLIGHT_PATH, preflight)
    print(
        json.dumps(
            {
                "preflight_written": True,
                "passages": len(passages),
                "scheduled_jobs": len(EXECUTION_ORDER),
                "production_code_modified": False,
                "model_mapping_disclosed": False,
            },
            sort_keys=True,
        )
    )
    return 0


def load_preflight() -> dict[str, Any]:
    """Load the frozen preflight without changing it."""

    if not PREFLIGHT_PATH.is_file():
        raise RuntimeError("Run --prepare before using the frozen probe")
    return json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))


def validate_preflight(*, require_repo: bool = True) -> dict[str, Any]:
    """Revalidate immutable source, packet, prompt, schema, and passage inputs."""

    if require_repo:
        require_clean_baseline()
    preflight = load_preflight()
    if preflight["baseline"]["repository_sha"] != EXPECTED_HEAD:
        raise RuntimeError("Preflight repository SHA is not the required baseline")
    if sha256_bytes(CORPUS_PATH.read_bytes()) != preflight["source_corpus"]["sha256"]:
        raise RuntimeError("Frozen source corpus changed after preflight")
    reference, _corpus, verified = frozen_reference()
    if reference["configuration"]["system_prompt_sha256"] != preflight["configuration"]["system_prompt_sha256"]:
        raise RuntimeError("Preflight prompt SHA differs from Contract 11")
    if reference["configuration"]["schema_sha256"] != preflight["configuration"]["schema_sha256"]:
        raise RuntimeError("Preflight schema SHA differs from Contract 11")
    expected_passages = {item["passage_id"]: item for item in preflight["passages"]}
    for passage_id, locked in expected_passages.items():
        manifest_path = REPORT / passage_id / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest != _read_manifest(passage_id):
            raise RuntimeError(f"Passage manifest read inconsistency: {passage_id}")
        paper_id = manifest["paper_id"]
        if paper_id not in verified:
            raise RuntimeError(f"Unknown frozen passage paper: {paper_id}")
        text = verified[paper_id]["record"]["text"]
        start, end = manifest["source_range"]["start"], manifest["source_range"]["end"]
        if text[start:end] != manifest["source_text"]:
            raise RuntimeError(f"Passage source changed: {passage_id}")
        if sha256_bytes(manifest["source_text"].encode("utf-8")) != manifest["source_sha256"]:
            raise RuntimeError(f"Passage source checksum is invalid: {passage_id}")
        if sha256_bytes(json_bytes(manifest["entity_packet"])) != manifest["entity_packet_sha256"]:
            raise RuntimeError(f"Passage entity packet checksum is invalid: {passage_id}")
        if locked != {
            key: value
            for key, value in manifest.items()
            if key not in {"source_text", "entity_packet", "entity_packet_absolute"}
        }:
            raise RuntimeError(f"Preflight passage freeze differs from manifest: {passage_id}")
        if passage_prompt_sha(manifest) != manifest["prompt_sha256"]:
            raise RuntimeError(f"Passage prompt changed: {passage_id}")
    load_model_key()
    return preflight


def _read_manifest(passage_id: str) -> dict[str, Any]:
    """Read one frozen passage manifest."""

    path = REPORT / passage_id / "manifest.json"
    if not path.is_file():
        raise RuntimeError(f"Missing passage manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def response_mapping(response: Any) -> Mapping[str, Any] | None:
    """Convert a structured response to a JSON-ready mapping when available."""

    if isinstance(response, Mapping):
        return response
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        try:
            value = dump(mode="json")
        except TypeError:
            value = dump()
        return value if isinstance(value, Mapping) else None
    dump = getattr(response, "dict", None)
    if callable(dump):
        value = dump()
        return value if isinstance(value, Mapping) else None
    return None


def response_duplicate_count(response: Any) -> tuple[int | None, int | None]:
    """Count raw structured relation duplicates before domain validation."""

    mapping = response_mapping(response)
    if mapping is None:
        return None, None
    relations = mapping.get("relations")
    if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
        return None, None
    keys = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in relations]
    return len(relations), len(keys) - len(set(keys))


def extract_token_usage(response: Any) -> dict[str, int] | None:
    """Normalize callback usage values without retaining provider objects."""

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

    value = {
        "input_tokens": first_integer(("input_tokens", "prompt_tokens")),
        "output_tokens": first_integer(("output_tokens", "completion_tokens")),
        "total_tokens": first_integer(("total_tokens",)),
    }
    if all(item is None for item in value.values()):
        return None
    return {key: item for key, item in value.items() if item is not None}


def total_usage(calls: Sequence[Mapping[str, Any]]) -> dict[str, int] | None:
    """Sum callback token usage across provider and bounded repair attempts."""

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


try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover - only reached before project sync
    BaseCallbackHandler = object  # type: ignore[misc,assignment]


class UsageRecorder(BaseCallbackHandler):
    """Record provider callback timing and normalized token usage."""

    def __init__(self) -> None:
        super().__init__()
        self.started: dict[str, float] = {}
        self.events: list[dict[str, Any]] = []

    def on_chat_model_start(self, serialized: Mapping[str, Any], messages: Sequence[Sequence[Any]], *, run_id: Any, **kwargs: Any) -> None:
        del serialized, messages, kwargs
        self.started[str(run_id)] = time.perf_counter()

    def on_llm_start(self, serialized: Mapping[str, Any], prompts: Sequence[str], *, run_id: Any, **kwargs: Any) -> None:
        del serialized, prompts, kwargs
        self.started.setdefault(str(run_id), time.perf_counter())

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        del kwargs
        self._finish(str(run_id), response, None)

    def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        del kwargs
        self._finish(str(run_id), None, error)

    def _finish(self, run_id: str, response: Any, error: BaseException | None) -> None:
        started = self.started.pop(run_id, None)
        self.events.append(
            {
                "status": "error" if error is not None else "response_received",
                "provider_latency_ms": round((time.perf_counter() - started) * 1000, 3) if started is not None else None,
                "token_usage": extract_token_usage(response) if response is not None else None,
                "error_type": type(error).__name__ if error is not None else None,
            }
        )


class RecordingRunnable:
    """Capture structured payloads at the unchanged Contract 10 model seam."""

    def __init__(self, inner: Any, recorder: UsageRecorder, calls: list[dict[str, Any]]) -> None:
        self.inner = inner
        self.recorder = recorder
        self.calls = calls

    def invoke(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        callbacks_before = len(self.recorder.events)
        entry: dict[str, Any] = {
            "attempt": len(self.calls) + 1,
            "repair": isinstance(value, str) and "REPAIR INSTRUCTION:\n" in value,
            "status": "started",
            "prompt_sha256": sha256_bytes(value.encode("utf-8")) if isinstance(value, str) else None,
        }
        try:
            response = self.inner.invoke(value, *args, **kwargs)
            raw_payload = response_mapping(response)
            raw_count, duplicate_count = response_duplicate_count(response)
            entry.update(
                {
                    "status": "response_received",
                    "raw_structured_payload": raw_payload,
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
                    "error": str(error)[:2000],
                }
            )
            raise
        finally:
            entry["invocation_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            entry["provider_callback_events"] = [
                dict(event) for event in self.recorder.events[callbacks_before:]
            ]
            entry["provider_callback_event_count"] = len(entry["provider_callback_events"])
            self.calls.append(entry)


class RecordingModel:
    """Wrap only structured-output binding, leaving the production harness intact."""

    def __init__(self, inner: Any, recorder: UsageRecorder, calls: list[dict[str, Any]]) -> None:
        self.inner = inner
        self.recorder = recorder
        self.calls = calls

    def with_structured_output(self, schema: Any) -> RecordingRunnable:
        return RecordingRunnable(self.inner.with_structured_output(schema), self.recorder, self.calls)


def initial_job_record(passage: Mapping[str, Any], alias: str, sequence: int) -> dict[str, Any]:
    """Return the frozen input portion of one blinded job artifact."""

    return {
        "sequence": sequence,
        "passage_id": passage["passage_id"],
        "paper_id": passage["paper_id"],
        "source_range": passage["source_range"],
        "source_text": passage["source_text"],
        "source_sha256": passage["source_sha256"],
        "entity_packet": passage["entity_packet"],
        "entity_packet_absolute": passage["entity_packet_absolute"],
        "entity_packet_sha256": passage["entity_packet_sha256"],
        "full_entity_packet_sha256": passage["full_entity_packet_sha256"],
        "blinded_model": alias,
        "configuration": {
            "provider": "OpenAI Responses API",
            "reasoning_effort": REASONING_EFFORT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "bounded_repair_budget": REPAIR_BUDGET,
            "provider_retries": PROVIDER_RETRIES,
            "prompt_sha256": passage["prompt_sha256"],
        },
        "status": "in_progress",
        "provider_attempts": 0,
        "repair_attempts": 0,
        "latency_ms": None,
        "provider_latency_ms": None,
        "token_usage": None,
        "validated_relations": None,
        "provider_attempt_details": [],
    }


def result_path(passage_id: str, alias: str) -> Path:
    """Return the blinded result path for one passage/model alias."""

    return REPORT / passage_id / ("model_a.json" if alias == "Model A" else "model_b.json")


def classify_failure(error: BaseException, calls: Sequence[Mapping[str, Any]]) -> str:
    """Separate generated-output failures from provider failures for stop logic."""

    generated_types = {
        "RelationValidationError",
        "JSONDecodeError",
        "OutputParserException",
        "ValidationError",
    }
    if any(call.get("error_type") in generated_types for call in calls):
        return "validation_failure"
    if calls and any(call.get("status") == "response_received" for call in calls):
        return "validation_failure"
    del error
    return "provider_failure"


def run_child(passage_id: str, alias: str, sequence: int) -> int:
    """Execute exactly one provider-backed model/passage job."""

    preflight = validate_preflight()
    passage = _read_manifest(passage_id)
    if alias not in MODEL_ALIASES:
        raise RuntimeError(f"Invalid blinded alias: {alias}")
    key = load_model_key()
    api_key = read_env_value("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is unavailable")
    path = result_path(passage_id, alias)
    record = initial_job_record(passage, alias, sequence)
    record["started_utc"] = now_utc()
    write_json(path, record)

    sys.path.insert(0, str(REPOSITORY / "src"))
    from langchain_openai import ChatOpenAI
    from biomedical_extractor.llm_relation_extraction import LLMRelationExtractor, OpenAIConfig

    calls: list[dict[str, Any]] = []
    recorder = UsageRecorder()
    config = OpenAIConfig(
        model=key[alias],
        api_key=api_key,
        reasoning_effort=REASONING_EFFORT,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
        max_retries=REPAIR_BUDGET,
        base_url=None,
    )
    client_kwargs: dict[str, Any] = {
        "model": config.model,
        "api_key": config.resolved_api_key(),
        "use_responses_api": True,
        "reasoning": {"effort": config.reasoning_effort},
        "max_retries": PROVIDER_RETRIES,
        "callbacks": [recorder],
        "max_completion_tokens": config.max_completion_tokens,
    }
    client = ChatOpenAI(**client_kwargs)
    extractor = LLMRelationExtractor(
        RecordingModel(client, recorder, calls),
        max_retries=REPAIR_BUDGET,
    )
    entities = [load_contract_modules()[0](**item) for item in passage["entity_packet"]]
    started = time.perf_counter()
    error: Exception | None = None
    result: Any = None
    try:
        result = extractor.extract_relations(passage["source_text"], entities)
    except Exception as caught:
        error = caught
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    provider_latencies = [
        event["provider_latency_ms"]
        for call in calls
        for event in call.get("provider_callback_events", [])
        if isinstance(event.get("provider_latency_ms"), (int, float))
    ]
    usage = total_usage(calls)
    record.update(
        {
            "finished_utc": now_utc(),
            "status": "success" if error is None else classify_failure(error, calls),
            "latency_ms": elapsed_ms,
            "provider_latency_ms": round(sum(provider_latencies), 3) if provider_latencies else None,
            "provider_attempts": len(calls),
            "repair_attempts": sum(bool(call.get("repair")) for call in calls),
            "token_usage": usage,
            "provider_attempt_details": calls,
        }
    )
    if error is None:
        record["validated_relations"] = [item.to_dict() for item in result.relations]
    else:
        record["error"] = {
            "type": type(error).__name__,
            "message": redact_error(str(error), api_key),
        }
    write_json(path, record)
    print(
        json.dumps(
            {
                "sequence": sequence,
                "passage_id": passage_id,
                "model": alias,
                "status": record["status"],
                "provider_attempts": record["provider_attempts"],
                "repair_attempts": record["repair_attempts"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    del preflight
    return 0


def timeout_record(passage: Mapping[str, Any], alias: str, sequence: int, started: float) -> dict[str, Any]:
    """Create the parent-owned record after an external watchdog timeout."""

    record = initial_job_record(passage, alias, sequence)
    record.update(
        {
            "started_utc": now_utc(),
            "finished_utc": now_utc(),
            "status": "timeout",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": {
                "type": "ExternalWatchdogTimeout",
                "message": f"job exceeded external wall-clock ceiling of {WATCHDOG_SECONDS} seconds and was terminated",
            },
        }
    )
    return record


def not_run_record(passage: Mapping[str, Any], alias: str, sequence: int, reason: str) -> dict[str, Any]:
    """Preserve scheduled-but-not-started pairs after the mandatory abort."""

    record = initial_job_record(passage, alias, sequence)
    record.update(
        {
            "started_utc": None,
            "finished_utc": None,
            "status": "not_run_aborted",
            "error": {"type": "ProbeAborted", "message": reason},
        }
    )
    return record


def run_probe() -> int:
    """Run the ten scheduled jobs with the external per-job watchdog."""

    preflight = validate_preflight()
    if STATE_PATH.exists():
        raise RuntimeError("Probe state already exists; refusing to rerun jobs")
    passage_by_id = {item["passage_id"]: _read_manifest(item["passage_id"]) for item in preflight["passages"]}
    started_utc = now_utc()
    started = time.perf_counter()
    state: dict[str, Any] = {
        "contract": "Codex Contract 11Q-R",
        "status": "running",
        "started_utc": started_utc,
        "scheduled_jobs": len(EXECUTION_ORDER),
        "completed_sequences": [],
        "stop_condition": None,
        "model_mapping_disclosed": False,
    }
    write_json(STATE_PATH, state)
    consecutive_failures = 0
    for sequence, passage_id, alias in EXECUTION_ORDER:
        validate_preflight()
        passage = passage_by_id[passage_id]
        path = result_path(passage_id, alias)
        job_record = initial_job_record(passage, alias, sequence)
        job_record["started_utc"] = now_utc()
        write_json(path, job_record)
        command = [sys.executable, str(SCRIPT_PATH), "--job", passage_id, alias, str(sequence)]
        child_started = time.perf_counter()
        process = subprocess.Popen(
            command,
            cwd=str(REPOSITORY),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=WATCHDOG_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            write_json(path, timeout_record(passage, alias, sequence, child_started))
            status = "timeout"
        else:
            if path.is_file():
                result = json.loads(path.read_text(encoding="utf-8"))
            else:
                result = initial_job_record(passage, alias, sequence)
                result.update(
                    {
                        "status": "provider_failure",
                        "finished_utc": now_utc(),
                        "latency_ms": round((time.perf_counter() - child_started) * 1000, 3),
                        "error": {
                            "type": "ChildProcessFailure",
                            "message": (
                                f"child exited with code {process.returncode} without a result; "
                                f"stderr={redact_error(stderr[-1800:], read_env_value('OPENAI_API_KEY') or '')}"
                            ),
                        },
                    }
                )
                write_json(path, result)
            status = result.get("status", "provider_failure")
            if process.returncode != 0 and status == "success":
                result["status"] = "provider_failure"
                result["error"] = {
                    "type": "ChildProcessFailure",
                    "message": f"child exited with code {process.returncode}; stderr={redact_error(stderr[-1800:], read_env_value('OPENAI_API_KEY') or '')}",
                }
                write_json(path, result)
                status = result["status"]
            del stdout
        if status in {"provider_failure", "timeout"}:
            consecutive_failures += 1
        else:
            consecutive_failures = 0
        state["completed_sequences"].append(sequence)
        state["last_status"] = status
        state["consecutive_provider_or_timeout_failures"] = consecutive_failures
        write_json(STATE_PATH, state)
        print(
            json.dumps(
                {
                    "sequence": sequence,
                    "passage_id": passage_id,
                    "model": alias,
                    "status": status,
                    "consecutive_provider_or_timeout_failures": consecutive_failures,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if consecutive_failures >= 3:
            reason = "three consecutive provider-error or timeout jobs before structured output"
            state["status"] = "aborted_stop_condition"
            state["stop_condition"] = reason
            for remaining_sequence, remaining_passage, remaining_alias in EXECUTION_ORDER:
                if remaining_sequence in state["completed_sequences"]:
                    continue
                write_json(
                    result_path(remaining_passage, remaining_alias),
                    not_run_record(
                        passage_by_id[remaining_passage],
                        remaining_alias,
                        remaining_sequence,
                        reason,
                    ),
                )
            break
    else:
        state["status"] = "completed_schedule"
    state["finished_utc"] = now_utc()
    state["elapsed_wall_seconds"] = round(time.perf_counter() - started, 3)
    write_json(STATE_PATH, state)
    build_analysis()
    return 0 if state["status"] == "completed_schedule" else 1


def exact_key(relation: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the exact Contract 11Q-R relation identity."""

    return (
        relation.get("source"),
        relation.get("target"),
        relation.get("predicate"),
        relation.get("negated"),
        relation.get("evidence"),
    )


def loose_key(relation: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the endpoint/negation/exact-evidence alignment identity."""

    return (
        relation.get("source"),
        relation.get("target"),
        relation.get("negated"),
        relation.get("evidence"),
    )


def endpoint_evidence_key(relation: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return a key that allows evidence-span disagreement alignment."""

    return (
        relation.get("source"),
        relation.get("target"),
        relation.get("negated"),
    )


def endpoint_evidence_polarity_key(relation: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return a key that allows explicit negation disagreement alignment."""

    return (
        relation.get("source"),
        relation.get("target"),
        relation.get("evidence"),
    )


def canonical(value: Any) -> str:
    """Serialize values for deterministic comparison and output ordering."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pair_grouped(
    left: list[tuple[int, Mapping[str, Any]]],
    right: list[tuple[int, Mapping[str, Any]]],
    key_fn: Any,
    ) -> tuple[
        list[tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]],
        list[tuple[int, Mapping[str, Any]]],
        list[tuple[int, Mapping[str, Any]]],
    ]:
    """Pair deterministic relation variants by one alignment key."""

    left_groups: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    right_groups: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    for item in left:
        left_groups.setdefault(key_fn(item[1]), []).append(item)
    for item in right:
        right_groups.setdefault(key_fn(item[1]), []).append(item)
    pairs: list[tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]] = []
    used_left: set[int] = set()
    used_right: set[int] = set()
    for key in sorted(set(left_groups) & set(right_groups), key=canonical):
        aa = sorted(left_groups[key], key=lambda item: (canonical(item[1]), item[0]))
        bb = sorted(right_groups[key], key=lambda item: (canonical(item[1]), item[0]))
        for item_a, item_b in zip(aa, bb):
            pairs.append((item_a, item_b))
            used_left.add(item_a[0])
            used_right.add(item_b[0])
    return (
        pairs,
        [item for item in left if item[0] not in used_left],
        [item for item in right if item[0] not in used_right],
    )


def pair_negation(
    left: list[tuple[int, Mapping[str, Any]]],
    right: list[tuple[int, Mapping[str, Any]]],
) -> tuple[list[tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]], list[tuple[int, Mapping[str, Any]]], list[tuple[int, Mapping[str, Any]]]]:
    """Pair relations with the same endpoints/evidence but opposite negation."""

    left_groups: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    right_groups: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    for item in left:
        left_groups.setdefault(endpoint_evidence_polarity_key(item[1]), []).append(item)
    for item in right:
        right_groups.setdefault(endpoint_evidence_polarity_key(item[1]), []).append(item)
    pairs = []
    used_left: set[int] = set()
    used_right: set[int] = set()
    for key in sorted(set(left_groups) & set(right_groups), key=canonical):
        for item_a in sorted(left_groups[key], key=lambda item: (canonical(item[1]), item[0])):
            candidate = next(
                (
                    item_b
                    for item_b in sorted(right_groups[key], key=lambda item: (canonical(item[1]), item[0]))
                    if item_b[0] not in used_right
                    and item_a[0] not in used_left
                    and item_a[1].get("negated") != item_b[1].get("negated")
                ),
                None,
            )
            if candidate is not None:
                pairs.append((item_a, candidate))
                used_left.add(item_a[0])
                used_right.add(candidate[0])
    return pairs, [item for item in left if item[0] not in used_left], [item for item in right if item[0] not in used_right]


def pair_evidence(
    left: list[tuple[int, Mapping[str, Any]]],
    right: list[tuple[int, Mapping[str, Any]]],
) -> tuple[list[tuple[tuple[int, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]], list[tuple[int, Mapping[str, Any]]], list[tuple[int, Mapping[str, Any]]]]:
    """Pair relations with same endpoints/negation but different evidence."""

    left_groups: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    right_groups: dict[Any, list[tuple[int, Mapping[str, Any]]]] = {}
    for item in left:
        left_groups.setdefault(endpoint_evidence_key(item[1]), []).append(item)
    for item in right:
        right_groups.setdefault(endpoint_evidence_key(item[1]), []).append(item)
    pairs = []
    used_left: set[int] = set()
    used_right: set[int] = set()
    for key in sorted(set(left_groups) & set(right_groups), key=canonical):
        aa = sorted(left_groups[key], key=lambda item: (canonical(item[1]), item[0]))
        bb = sorted(right_groups[key], key=lambda item: (canonical(item[1]), item[0]))
        for item_a in aa:
            candidate = next(
                (
                    item_b
                    for item_b in bb
                    if item_b[0] not in used_right
                    and item_a[0] not in used_left
                    and item_a[1].get("evidence") != item_b[1].get("evidence")
                ),
                None,
            )
            if candidate is not None:
                pairs.append((item_a, candidate))
                used_left.add(item_a[0])
                used_right.add(candidate[0])
    return pairs, [item for item in left if item[0] not in used_left], [item for item in right if item[0] not in used_right]


SEMANTIC_FIELDS = (
    "predicate",
    "assertion",
    "negated",
    "intervention",
    "effects",
    "context",
    "surface_form",
)


def locate_source(passage: Mapping[str, Any], evidence: str | None) -> dict[str, Any]:
    """Locate one exact evidence string in a frozen passage."""

    text = passage["source_text"]
    if not isinstance(evidence, str):
        return {"local_start": None, "local_end": None, "absolute_start": None, "absolute_end": None, "exact_evidence": None, "exact_context": None}
    start = text.find(evidence)
    if start < 0:
        return {"local_start": None, "local_end": None, "absolute_start": None, "absolute_end": None, "exact_evidence": evidence, "exact_context": None}
    end = start + len(evidence)
    context_start = max(0, start - 180)
    context_end = min(len(text), end + 180)
    base = passage["source_range"]["start"]
    return {
        "local_start": start,
        "local_end": end,
        "absolute_start": base + start,
        "absolute_end": base + end,
        "exact_evidence": text[start:end],
        "exact_context": text[context_start:context_end],
        "context_local_start": context_start,
        "context_local_end": context_end,
    }


def relation_row(
    passage: Mapping[str, Any],
    entity_by_id: Mapping[str, Mapping[str, Any]],
    category: str,
    relation_a: Mapping[str, Any] | None,
    relation_b: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build one deterministic, non-judgmental review row."""

    source_relation = relation_a or relation_b or {}
    source_id, target_id = source_relation.get("source"), source_relation.get("target")
    return {
        "passage_id": passage["passage_id"],
        "paper_id": passage["paper_id"],
        "category": category,
        "source": {
            "range": passage["source_range"],
            "context": locate_source(passage, source_relation.get("evidence")),
        },
        "source_entity": entity_by_id.get(source_id, {"id": source_id, "missing_from_packet": True}),
        "target_entity": entity_by_id.get(target_id, {"id": target_id, "missing_from_packet": True}),
        "model_a_relation": dict(relation_a) if relation_a is not None else None,
        "model_b_relation": dict(relation_b) if relation_b is not None else None,
        "differing_fields": [
            field
            for field in SEMANTIC_FIELDS
            if (relation_a or {}).get(field) != (relation_b or {}).get(field)
        ] if relation_a is not None and relation_b is not None else [],
    }


def compare_passage(passage: Mapping[str, Any], result_a: Mapping[str, Any], result_b: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two successful outputs without assigning quality."""

    relations_a = result_a.get("validated_relations") if result_a.get("status") == "success" else None
    relations_b = result_b.get("validated_relations") if result_b.get("status") == "success" else None
    if not isinstance(relations_a, list) or not isinstance(relations_b, list):
        return {
            "passage_id": passage["passage_id"],
            "paper_id": passage["paper_id"],
            "status": "comparison_unavailable",
            "reason": "both blinded jobs did not return validated relations",
            "exact_relation_identity": {
                "fields": ["source", "target", "predicate", "negated", "evidence"],
                "shared": None,
                "model_a_only": None,
                "model_b_only": None,
            },
            "loose_alignment": [],
            "disagreements": [],
            "shared_exact": [],
        }
    entity_by_id = {item["id"]: item for item in passage["entity_packet_absolute"]}
    a_index = list(enumerate(relations_a))
    b_index = list(enumerate(relations_b))
    exact_a = {exact_key(item) for item in relations_a}
    exact_b = {exact_key(item) for item in relations_b}
    exact_pairs, rem_a, rem_b = pair_grouped(a_index, b_index, exact_key)
    loose_pairs, rem_a, rem_b = pair_grouped(rem_a, rem_b, loose_key)
    negation_pairs, rem_a, rem_b = pair_negation(rem_a, rem_b)
    evidence_pairs, rem_a, rem_b = pair_evidence(rem_a, rem_b)
    aligned = []
    for pair, kind in (
        *[(pair, "exact") for pair in exact_pairs],
        *[(pair, "endpoint_negation_exact_evidence") for pair in loose_pairs],
        *[(pair, "negation_difference") for pair in negation_pairs],
        *[(pair, "evidence_span_difference") for pair in evidence_pairs],
    ):
        relation_a, relation_b = pair[0][1], pair[1][1]
        aligned.append(
            {
                "alignment": kind,
                "model_a": dict(relation_a),
                "model_b": dict(relation_b),
                "differing_fields": [field for field in SEMANTIC_FIELDS if relation_a.get(field) != relation_b.get(field)],
            }
        )
    disagreements: list[dict[str, Any]] = []
    for item in aligned:
        if item["differing_fields"]:
            disagreements.append(
                relation_row(
                    passage,
                    entity_by_id,
                    item["alignment"],
                    item["model_a"],
                    item["model_b"],
                )
            )
    for _, relation in rem_a:
        disagreements.append(relation_row(passage, entity_by_id, "model_a_only_exact_relation", relation, None))
    for _, relation in rem_b:
        disagreements.append(relation_row(passage, entity_by_id, "model_b_only_exact_relation", None, relation))
    disagreements.sort(
        key=lambda item: (
            item["source"]["context"]["local_start"]
            if item["source"]["context"]["local_start"] is not None
            else len(passage["source_text"]) + 1,
            item["category"],
            canonical(item["model_a_relation"]),
            canonical(item["model_b_relation"]),
        )
    )
    shared_exact = []
    for pair in exact_pairs:
        relation_a, relation_b = pair[0][1], pair[1][1]
        if exact_key(relation_a) in exact_a & exact_b:
            shared_exact.append(
                relation_row(passage, entity_by_id, "exact_shared_relation", relation_a, relation_b)
            )
    shared_exact.sort(
        key=lambda item: (
            item["source"]["context"]["local_start"]
            if item["source"]["context"]["local_start"] is not None
            else len(passage["source_text"]) + 1,
            canonical(item["model_a_relation"]),
        )
    )
    return {
        "passage_id": passage["passage_id"],
        "paper_id": passage["paper_id"],
        "status": "compared",
        "exact_relation_identity": {
            "fields": ["source", "target", "predicate", "negated", "evidence"],
            "shared": [list(item) for item in sorted(exact_a & exact_b, key=canonical)],
            "model_a_only": [list(item) for item in sorted(exact_a - exact_b, key=canonical)],
            "model_b_only": [list(item) for item in sorted(exact_b - exact_a, key=canonical)],
            "shared_count": len(exact_a & exact_b),
            "model_a_only_count": len(exact_a - exact_b),
            "model_b_only_count": len(exact_b - exact_a),
        },
        "loose_alignment": {
            "fields": ["source", "target", "negated", "exact evidence"],
            "aligned_relations": aligned,
            "aligned_count": len(aligned),
        },
        "disagreements": disagreements,
        "shared_exact": shared_exact,
    }


def relation_count(result: Mapping[str, Any]) -> int | None:
    """Return validated relation count for successful jobs only."""

    values = result.get("validated_relations") if result.get("status") == "success" else None
    return len(values) if isinstance(values, list) else None


def token_value(result: Mapping[str, Any], key: str) -> int | None:
    """Read one token metric without treating unavailable usage as zero."""

    usage = result.get("token_usage")
    value = usage.get(key) if isinstance(usage, Mapping) else None
    return value if isinstance(value, int) else None


def build_analysis() -> None:
    """Write blinded deterministic comparison, shared sample, and summaries."""

    preflight = validate_preflight()
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.is_file() else {}
    rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    all_disagreements: list[dict[str, Any]] = []
    all_shared: list[dict[str, Any]] = []
    for passage_locked in preflight["passages"]:
        passage_id = passage_locked["passage_id"]
        passage = _read_manifest(passage_id)
        result_values: dict[str, dict[str, Any]] = {}
        for alias in MODEL_ALIASES:
            path = result_path(passage_id, alias)
            result = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else not_run_record(passage, alias, 0, "result file unavailable")
            result_values[alias] = result
            rows.append(
                {
                    "passage": passage_id,
                    "model": alias,
                    "chars": passage["source_characters"],
                    "entities": passage["entity_count"],
                    "status": result.get("status"),
                    "relations": relation_count(result),
                    "attempts": result.get("provider_attempts"),
                    "repairs": result.get("repair_attempts"),
                    "latency_ms": result.get("latency_ms"),
                    "input_tokens": token_value(result, "input_tokens"),
                    "output_tokens": token_value(result, "output_tokens"),
                }
            )
        comparison = compare_passage(passage, result_values["Model A"], result_values["Model B"])
        comparisons.append(comparison)
        all_disagreements.extend(comparison.get("disagreements", []))
        shared = comparison.get("shared_exact", [])
        if len(shared) > 20:
            shared = shared[:20]
        all_shared.extend(shared)

    exact_fields = ["source", "target", "predicate", "negated", "evidence"]
    shared_lines = [
        "# Contract 11Q-R exact shared relations",
        "",
        "All identities use source ID, target ID, predicate, negated, and exact evidence. This packet is descriptive and blinded; it does not judge correctness.",
        "",
    ]
    for comparison in comparisons:
        shared_lines.extend(
            [
                f"## {comparison['passage_id']} — {comparison['paper_id']}",
                "",
                f"Exact identity fields: {', '.join(exact_fields)}",
                f"Exact shared count: {comparison['exact_relation_identity'].get('shared_count', 'unavailable')}",
                "",
            ]
        )
        sample = comparison.get("shared_exact", [])
        if not sample:
            shared_lines.extend(["No exact shared relation sample is available.", ""])
        for index, item in enumerate(sample, 1):
            shared_lines.extend(
                [
                    f"### Shared relation {index}",
                    "",
                    f"Source context local/absolute: {item['source']['context'].get('local_start')}–{item['source']['context'].get('local_end')} / {item['source']['context'].get('absolute_start')}–{item['source']['context'].get('absolute_end')}",
                    "",
                    "Exact source evidence:",
                    "",
                    "```text",
                    str(item["source"]["context"].get("exact_evidence")),
                    "```",
                    "",
                    "Source entity:",
                    "",
                    "```json",
                    json.dumps(item["source_entity"], ensure_ascii=False, indent=2, sort_keys=True),
                    "```",
                    "",
                    "Target entity:",
                    "",
                    "```json",
                    json.dumps(item["target_entity"], ensure_ascii=False, indent=2, sort_keys=True),
                    "```",
                    "",
                    "Model A relation:",
                    "",
                    "```json",
                    json.dumps(item["model_a_relation"], ensure_ascii=False, indent=2, sort_keys=True),
                    "```",
                    "",
                    "Model B relation:",
                    "",
                    "```json",
                    json.dumps(item["model_b_relation"], ensure_ascii=False, indent=2, sort_keys=True),
                    "```",
                    "",
                ]
            )
    (REPORT / "shared.md").write_text("\n".join(shared_lines), encoding="utf-8")

    disagreement_lines = [
        "# Contract 11Q-R blinded disagreements",
        "",
        "Every entry is a deterministic output difference. Codex does not decide which relation is correct.",
        "",
    ]
    if not all_disagreements:
        disagreement_lines.extend(["No substantive disagreements were available from the returned outputs.", ""])
    for index, item in enumerate(all_disagreements, 1):
        context = item["source"]["context"]
        disagreement_lines.extend(
            [
                f"## {index}. {item['category']}",
                "",
                f"Passage: {item['passage_id']}",
                f"Paper: {item['paper_id']}",
                f"Source range: [{item['source']['range']['start']}, {item['source']['range']['end']})",
                f"Evidence range local/absolute: [{context.get('local_start')}, {context.get('local_end')}) / [{context.get('absolute_start')}, {context.get('absolute_end')})",
                f"Differing fields: {', '.join(item['differing_fields']) if item['differing_fields'] else 'relation presence/evidence'}",
                "",
                "Exact source evidence:",
                "",
                "```text",
                str(context.get("exact_evidence")),
                "```",
                "",
                "Exact source context:",
                "",
                "```text",
                str(context.get("exact_context")),
                "```",
                "",
                "Source entity:",
                "",
                "```json",
                json.dumps(item["source_entity"], ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
                "Target entity:",
                "",
                "```json",
                json.dumps(item["target_entity"], ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
                "Model A relation:",
                "",
                "```json",
                json.dumps(item["model_a_relation"], ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
                "Model B relation:",
                "",
                "```json",
                json.dumps(item["model_b_relation"], ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    (REPORT / "disagreements.md").write_text("\n".join(disagreement_lines), encoding="utf-8")

    totals: dict[str, dict[str, Any]] = {}
    for alias in MODEL_ALIASES:
        model_rows = [row for row in rows if row["model"] == alias]
        statuses = [row["status"] for row in model_rows]
        latencies = [row["latency_ms"] for row in model_rows if isinstance(row["latency_ms"], (int, float))]
        total_relations = [row["relations"] for row in model_rows if isinstance(row["relations"], int)]
        input_values = [row["input_tokens"] for row in model_rows if isinstance(row["input_tokens"], int)]
        output_values = [row["output_tokens"] for row in model_rows if isinstance(row["output_tokens"], int)]
        totals[alias] = {
            "successes": statuses.count("success"),
            "validation_failures": statuses.count("validation_failure"),
            "timeouts_provider_failures": statuses.count("timeout") + statuses.count("provider_failure"),
            "timeouts": statuses.count("timeout"),
            "provider_failures": statuses.count("provider_failure"),
            "not_run_aborted": statuses.count("not_run_aborted"),
            "total_relations": sum(total_relations),
            "input_tokens": sum(input_values) if input_values else None,
            "output_tokens": sum(output_values) if output_values else None,
            "total_tokens": (
                sum(input_values) + sum(output_values)
                if input_values and output_values
                else None
            ),
            "latency_aggregation": "executed jobs with numeric latency, including failures and watchdog timeouts; not-run jobs excluded",
            "mean_latency_ms": round(mean(latencies), 3) if latencies else None,
            "median_latency_ms": round(median(latencies), 3) if latencies else None,
        }
    summary = {
        "contract": "Codex Contract 11Q-R",
        "status": state.get("status", "unknown"),
        "quality_judgment": "not assigned by Codex",
        "model_mapping_disclosed": False,
        "baseline": {
            "head": preflight["baseline"]["repository_sha"],
            "branch": preflight["baseline"]["branch"],
            "production_code_diff": "clean",
        },
        "probe": {
            "passages": 5,
            "scheduled_jobs": 10,
            "completed_jobs": len(state.get("completed_sequences", [])),
            "failures_or_timeouts": sum(row["status"] in {"provider_failure", "timeout"} for row in rows),
            "validation_failures": sum(row["status"] == "validation_failure" for row in rows),
            "repairs": sum(row["repairs"] or 0 for row in rows if isinstance(row["repairs"], int)),
            "total_elapsed_wall_seconds": state.get("elapsed_wall_seconds"),
            "stop_condition": state.get("stop_condition"),
        },
        "configuration": {
            "provider": "OpenAI Responses API",
            "reasoning_effort": REASONING_EFFORT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "bounded_repair_budget": REPAIR_BUDGET,
            "provider_retries": PROVIDER_RETRIES,
            "system_prompt_sha256": preflight["configuration"]["system_prompt_sha256"],
            "schema_sha256": preflight["configuration"]["schema_sha256"],
        },
        "execution_order": preflight["execution_order"],
        "rows": rows,
        "totals": totals,
        "comparisons": comparisons,
        "artifact_paths": {
            "preflight": "reports/luna_56_vs_6_real_probe_11qr/preflight.json",
            "per_passage": "reports/luna_56_vs_6_real_probe_11qr/passage_<001-005>/model_<a,b>.json",
            "disagreements": "reports/luna_56_vs_6_real_probe_11qr/disagreements.md",
            "shared": "reports/luna_56_vs_6_real_probe_11qr/shared.md",
            "summary": "reports/luna_56_vs_6_real_probe_11qr/summary.md",
            "summary_json": "reports/luna_56_vs_6_real_probe_11qr/summary.json",
        },
    }
    write_json(REPORT / "summary.json", summary)
    lines = [
        "# Contract 11Q-R blinded real biomedical RE probe",
        "",
        f"Status: {summary['status']}",
        "Quality judgment: deferred to Talia; Codex assigns no winner or quality score.",
        "Model mapping remains separately preserved and undisclosed.",
        "",
        "## Baseline",
        "",
        f"- HEAD: {summary['baseline']['head']}",
        f"- Branch: {summary['baseline']['branch']}",
        f"- Production-code diff under src/viewer/tests: {summary['baseline']['production_code_diff']}",
        "",
        "## Descriptive run table",
        "",
        "| Passage | Model | Chars | Entities | Status | Relations | Attempts | Repairs | Latency ms | Input tokens | Output tokens |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        values = (
            row["passage"],
            row["model"],
            row["chars"],
            row["entities"],
            row["status"],
            row["relations"],
            row["attempts"],
            row["repairs"],
            row["latency_ms"],
            row["input_tokens"],
            row["output_tokens"],
        )
        lines.append("| " + " | ".join("—" if value is None else str(value) for value in values) + " |")
    lines.extend(["", "## Totals", ""])
    lines.extend(
        [
            "| Model | Successes | Validation failures | Timeouts/provider failures | Not run after abort | Total relations | Total tokens | Mean latency ms | Median latency ms |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for alias in MODEL_ALIASES:
        value = totals[alias]
        lines.append(
            "| "
            + alias
            + " | "
            + " | ".join(
                str(value.get(key)) if value.get(key) is not None else "—"
                for key in (
                    "successes",
                    "validation_failures",
                    "timeouts_provider_failures",
                    "not_run_aborted",
                    "total_relations",
                    "total_tokens",
                    "mean_latency_ms",
                    "median_latency_ms",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            f"- Passages: {summary['probe']['passages']}",
            f"- Scheduled jobs: {summary['probe']['scheduled_jobs']}",
            f"- Completed jobs: {summary['probe']['completed_jobs']}",
            f"- Failures/timeouts: {summary['probe']['failures_or_timeouts']}",
            f"- Validation failures: {summary['probe']['validation_failures']}",
            f"- Repair attempts: {summary['probe']['repairs']}",
            f"- Total elapsed wall time (seconds): {summary['probe']['total_elapsed_wall_seconds']}",
            "- No quality interpretation is included.",
            "",
            "## Frozen configuration",
            "",
            f"- Provider: {summary['configuration']['provider']}",
            f"- Reasoning effort: {summary['configuration']['reasoning_effort']}",
            f"- Max output tokens: {summary['configuration']['max_output_tokens']}",
            f"- Contract 10 repair budget: {summary['configuration']['bounded_repair_budget']}",
            f"- Provider retries: {summary['configuration']['provider_retries']}",
            f"- Contract 10 prompt SHA-256: {summary['configuration']['system_prompt_sha256']}",
            f"- Contract 10 schema SHA-256: {summary['configuration']['schema_sha256']}",
            "",
            "## Review packets",
            "",
            "- [disagreements.md](disagreements.md)",
            "- [shared.md](shared.md)",
            "- [preflight.json](preflight.json)",
            "- Per-passage manifests and blinded results are under `passage_001/` through `passage_005/`.",
            "",
        ]
    )
    (REPORT / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """Dispatch preparation, verification, execution, analysis, or one child job."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--job", nargs=3, metavar=("PASSAGE_ID", "MODEL_ALIAS", "SEQUENCE"))
    args = parser.parse_args()
    selected = sum(bool(value) for value in (args.prepare, args.verify_only, args.run, args.analyze, args.job))
    if selected != 1:
        parser.error("choose exactly one of --prepare, --verify-only, --run, --analyze, or --job")
    if args.prepare:
        return prepare()
    if args.verify_only:
        preflight = validate_preflight()
        print(json.dumps({"preflight_valid": True, "passages": len(preflight["passages"]), "scheduled_jobs": len(preflight["execution_order"]), "provider_requests_started": False}, sort_keys=True))
        return 0
    if args.run:
        return run_probe()
    if args.analyze:
        validate_preflight()
        build_analysis()
        return 0
    passage_id, alias, sequence = args.job
    return run_child(passage_id, alias, int(sequence))


if __name__ == "__main__":
    raise SystemExit(main())
