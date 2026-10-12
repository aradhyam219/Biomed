"""Isolated orchestration for the current HunFlair2 runtime."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence



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
    """Write source documents for the isolated HunFlair2 runner."""

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




__all__ = ["RunnerOutput", "run_hunflair2", "write_runner_input"]
