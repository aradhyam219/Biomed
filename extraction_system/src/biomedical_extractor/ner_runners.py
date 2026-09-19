"""Isolated orchestration for the cached AIONER and HunFlair2 runners."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from .aioner import normalize_aioner_predictions
from .entity_extraction import Entity
from .hunflair2 import normalize_hunflair2_predictions


@dataclass(frozen=True)
class RunnerOutput:
    """Plain output emitted by one isolated model runtime."""

    model: str
    prediction_path: Path
    metadata: Mapping[str, Any]
    records: Mapping[str, Sequence[object]]


def _sha256_file(path: Path) -> str:
    """Hash one external artifact in bounded chunks."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_runner_input(
    documents: Sequence[Mapping[str, str]],
    path: Path,
) -> None:
    """Write identical source documents for both isolated model runners."""

    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for document in documents:
        document_id = str(document["id"])
        text = document["text"]
        if document_id in seen:
            raise ValueError(f"Duplicate runner document ID: {document_id}")
        if not isinstance(text, str):
            raise TypeError("Runner document text must be a string")
        seen.add(document_id)
        normalized.append({"id": document_id, "text": text})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"documents": normalized}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_runner_output(path: Path, model: str) -> RunnerOutput:
    """Load and validate one isolated runner output."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{model} runner output must be an object")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, Sequence) or isinstance(
        raw_documents, (str, bytes)
    ):
        raise ValueError(f"{model} runner output requires documents")
    records: dict[str, Sequence[object]] = {}
    for raw in raw_documents:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{model} runner document must be an object")
        document_id = str(raw.get("id", ""))
        predictions = raw.get("predictions", ())
        if not document_id or not isinstance(predictions, Sequence) or isinstance(
            predictions, (str, bytes)
        ):
            raise ValueError(f"Invalid {model} runner document record")
        if document_id in records:
            raise ValueError(f"Duplicate {model} runner document ID: {document_id}")
        records[document_id] = tuple(predictions)
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError(f"{model} runner metadata must be an object")
    return RunnerOutput(model, path, dict(metadata), records)


def load_cached_runner_output(
    path: Path,
    model: str,
    documents: Sequence[Mapping[str, str]],
    *,
    expected_model_artifact_sha256: str | None = None,
) -> RunnerOutput:
    """Load cached predictions only when input and artifact identity still match.

    The isolated runtimes write a checksum for every supplied source document.
    Comparing those checksums, coverage, and the cached model artifact digest is
    sufficient to reuse a prediction file without rerunning inference.
    """

    run = _load_runner_output(path, model)
    expected = {
        str(document["id"]): hashlib.sha256(
            str(document["text"]).encode("utf-8")
        ).hexdigest()
        for document in documents
    }
    if set(run.records) != set(expected):
        raise ValueError(f"{model} cached predictions do not cover the supplied documents")
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    raw_documents = raw_payload.get("documents", ())
    by_id = {str(item.get("id")): item for item in raw_documents}
    for document_id, expected_digest in expected.items():
        actual_digest = by_id[document_id].get("text_sha256")
        if actual_digest != expected_digest:
            raise ValueError(
                f"{model} cached prediction input checksum mismatch for {document_id}"
            )
    if (
        expected_model_artifact_sha256 is not None
        and run.metadata.get("model_artifact_sha256")
        != expected_model_artifact_sha256
    ):
        raise ValueError(f"{model} cached prediction artifact checksum mismatch")
    return run


def _run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    model: str,
) -> None:
    """Run one isolated runtime and surface bounded diagnostics on failure."""

    result = subprocess.run(
        list(command),
        cwd=str(cwd),
        env=dict(environment),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout)[-4000:]
        raise RuntimeError(f"{model} runner failed with exit code {result.returncode}: {detail}")


def run_aioner(
    documents: Sequence[Mapping[str, str]],
    *,
    input_path: Path,
    output_path: Path,
    python_path: Path = Path(".cache/aioner/legacy-venv/Scripts/python.exe"),
    upstream_root: Path = Path(".cache/aioner-upstream"),
    model_path: Path = Path(
        ".cache/aioner-upstream/pretrained_models/AIONER/PubmedBERT-CRF-AIONER.h5"
    ),
    vocab_path: Path = Path(".cache/aioner-upstream/vocab/AIO_label.vocab"),
    stanza_resources: Path = Path(".cache/aioner/stanza_resources"),
) -> RunnerOutput:
    """Run the exact cached official AIONER PubMedBERT-CRF artifact."""

    write_runner_input(documents, input_path)
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    python_path = python_path.resolve()
    upstream_root = upstream_root.resolve()
    model_path = model_path.resolve()
    vocab_path = vocab_path.resolve()
    stanza_resources = stanza_resources.resolve()
    command = [
        str(python_path),
        str((Path(__file__).with_name("aioner_runtime.py")).resolve()),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--upstream-root",
        str(upstream_root),
        "--model",
        str(model_path),
        "--vocabfile",
        str(vocab_path),
        "--model-artifact-sha256",
        _sha256_file(model_path) if model_path.is_file() else "",
        "--stanza-resources",
        str(stanza_resources),
    ]
    environment = os.environ.copy()
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "",
            "TF_CPP_MIN_LOG_LEVEL": "2",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    _run_command(
        command,
        cwd=upstream_root / "src",
        environment=environment,
        model="AIONER",
    )
    return _load_runner_output(output_path, "AIONER")


def _hunflair2_artifact(
    runtime_cache: Path,
    model_identifier: str,
) -> tuple[Path | None, str | None]:
    """Locate the cached Hugging Face HunFlair2 snapshot and revision."""

    if model_identifier != "hunflair/hunflair2-ner":
        return None, None
    model_root = (
        runtime_cache
        / "flair"
        / "models"
        / "hunflair2-ner"
        / "models--hunflair--hunflair2-ner"
    )
    ref_path = model_root / "refs" / "main"
    revision = ref_path.read_text(encoding="utf-8").strip() if ref_path.is_file() else None
    candidates: list[Path] = []
    if revision:
        snapshot = model_root / "snapshots" / revision
        candidates.extend(
            path
            for path in (
                snapshot / "pytorch_model.bin",
                snapshot / "model.safetensors",
                snapshot / "hunflair2-ner.pt",
            )
            if path.is_file()
        )
    if not candidates and runtime_cache.is_dir():
        candidates.extend(
            path
            for path in runtime_cache.rglob("*")
            if path.is_file()
            and path.name in {"pytorch_model.bin", "model.safetensors", "hunflair2-ner.pt"}
        )
    artifact = sorted(candidates, key=lambda path: str(path))[0] if candidates else None
    return artifact, revision


def run_hunflair2(
    documents: Sequence[Mapping[str, str]],
    *,
    input_path: Path,
    output_path: Path,
    python_path: Path | None = None,
    runtime_script: Path = Path("src/biomedical_extractor/hunflair2_runtime.py"),
    runtime_cache: Path = Path(".cache/hunflair2"),
    model_identifier: str = "hunflair/hunflair2-ner",
    device: str = "cpu",
    offline: bool = False,
) -> RunnerOutput:
    """Run the isolated official HunFlair2 artifact and splitter."""

    write_runner_input(documents, input_path)
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    if python_path is None:
        candidates = (
            Path(".cache/hunflair2/runtime/bin/python"),
            Path(".cache/hunflair2/runtime/Scripts/python.exe"),
        )
        python_path = next(
            (candidate for candidate in candidates if candidate.is_file()), candidates[0]
        )
    # Keep the virtualenv launcher symlink intact. Resolving
    # ``runtime/bin/python`` turns it into the underlying uv interpreter and
    # loses the isolated runtime's site-packages.
    python_path = Path(python_path)
    runtime_script = runtime_script.resolve()
    runtime_cache = runtime_cache.resolve()
    if not python_path.is_file():
        raise FileNotFoundError(f"HunFlair2 runtime Python not found: {python_path}")
    if not runtime_script.is_file():
        raise FileNotFoundError(f"HunFlair2 runtime script not found: {runtime_script}")
    runtime_cache.mkdir(parents=True, exist_ok=True)
    artifact, revision = _hunflair2_artifact(runtime_cache, model_identifier)
    model_input = str(artifact) if artifact is not None else model_identifier
    command = [
        str(python_path),
        str(runtime_script),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--model",
        model_input,
        "--model-identifier",
        model_identifier,
        "--device",
        device,
    ]
    if revision:
        command.extend(["--model-revision", revision])
    if artifact is not None:
        command.extend(["--model-artifact-sha256", _sha256_file(artifact)])
    environment = os.environ.copy()
    flair_root = runtime_cache / "flair"
    environment.update(
        {
            "FLAIR_CACHE_ROOT": str(flair_root),
            "HF_HOME": str(runtime_cache / "huggingface"),
            "TRANSFORMERS_CACHE": str(runtime_cache / "huggingface"),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    if offline:
        environment["HF_HUB_OFFLINE"] = "1"
    _run_command(
        command,
        cwd=Path.cwd(),
        environment=environment,
        model="HunFlair2",
    )
    return _load_runner_output(output_path, "HunFlair2")


def normalize_runner_predictions(
    run: RunnerOutput,
    documents: Sequence[Mapping[str, str]],
) -> dict[str, tuple[Entity, ...]]:
    """Convert plain runner records through the existing model adapters."""

    document_map = {str(document["id"]): str(document["text"]) for document in documents}
    if set(run.records) != set(document_map):
        missing = sorted(set(document_map) - set(run.records))
        extra = sorted(set(run.records) - set(document_map))
        raise ValueError(
            f"{run.model} prediction coverage mismatch; missing={missing}, extra={extra}"
        )
    normalized: dict[str, tuple[Entity, ...]] = {}
    for document_id, text in document_map.items():
        raw = run.records[document_id]
        if run.model == "AIONER":
            entities = normalize_aioner_predictions(text, raw)
        elif run.model == "HunFlair2":
            entities = normalize_hunflair2_predictions(text, raw)
        else:
            raise ValueError(f"Unsupported model runner: {run.model}")
        normalized[document_id] = entities
    return normalized


__all__ = [
    "RunnerOutput",
    "load_cached_runner_output",
    "normalize_runner_predictions",
    "run_aioner",
    "run_hunflair2",
    "write_runner_input",
]
