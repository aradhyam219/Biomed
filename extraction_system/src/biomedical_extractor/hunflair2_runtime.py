"""Standalone Flair subprocess for the isolated HunFlair2 inference run.

This file is executed by the dedicated ignored HunFlair2 virtual environment,
not imported by the production package.  It accepts source texts as JSON,
performs the official Flair inference with the recommended SciSpaCy sentence
splitter, and returns only plain document-relative prediction records.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


OFFICIAL_MODEL_IDENTIFIER = "hunflair/hunflair2-ner"
OFFICIAL_FLAIR_REPOSITORY = "https://github.com/flairNLP/flair"
SCISPACY_SENTENCE_SPLITTER = "SciSpacySentenceSplitter(en_core_sci_sm)"


def _parser() -> argparse.ArgumentParser:
    """Build the isolated runner command contract."""

    parser = argparse.ArgumentParser(description="Run official HunFlair2 inference.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default=OFFICIAL_MODEL_IDENTIFIER)
    parser.add_argument("--model-identifier", default=OFFICIAL_MODEL_IDENTIFIER)
    parser.add_argument("--model-revision", default=None)
    parser.add_argument("--model-artifact-sha256", default=None)
    parser.add_argument("--device", default="cpu")
    return parser


def _load_json(path: Path) -> Mapping[str, Any]:
    """Load one JSON input object and fail closed on malformed structure."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"Runner input must be a JSON object: {path}")
    return value


def _documents(payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Validate and return source documents without changing their text."""

    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, Sequence) or isinstance(
        raw_documents, (str, bytes)
    ):
        raise ValueError("Runner input requires a documents array")
    documents: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for raw in raw_documents:
        if not isinstance(raw, Mapping):
            raise ValueError("Runner documents must be objects")
        document_id = str(raw.get("id", ""))
        text = raw.get("text")
        if not document_id or not isinstance(text, str):
            raise ValueError("Runner documents require non-empty id and string text")
        if document_id in seen_ids:
            raise ValueError(f"Duplicate runner document ID: {document_id!r}")
        seen_ids.add(document_id)
        documents.append({"id": document_id, "text": text})
    return tuple(documents)


def _package_version(distribution: str) -> str | None:
    """Return one installed distribution version when available."""

    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _module_version(module_name: str) -> str | None:
    """Return the runtime module's exact version string when available."""

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    value = getattr(module, "__version__", None)
    return None if value is None else str(value)


def _sha256_file(path: Path) -> str:
    """Hash a model artifact in bounded chunks."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prediction_for_span(sentence: Any, span: Any, label_type: str, source_text: str) -> dict[str, Any]:
    """Convert and validate one Flair span into a plain document record."""

    reported_start = int(span.start_position)
    reported_end = int(span.end_position)
    span_text = str(span.text)
    if not 0 <= reported_start < reported_end:
        raise ValueError(
            "Flair returned invalid sentence span: "
            f"[{reported_start}, {reported_end}) sentence_len={len(sentence.text)}"
        )
    relative_start = reported_start
    relative_end = reported_end
    if sentence.text[relative_start:relative_end] != span_text:
        # Older Flair/SciSpaCy combinations can report a character position
        # shifted by tokenizer metadata while retaining the exact span text.
        # Resolve that discrepancy against the sentence text, preferring the
        # occurrence nearest the model-reported position, and still fail
        # closed if the text cannot be resolved unambiguously.
        candidates: list[int] = []
        search_from = 0
        while True:
            candidate = sentence.text.find(span_text, search_from)
            if candidate < 0:
                break
            candidates.append(candidate)
            search_from = candidate + 1
        if not candidates:
            raise ValueError(
                "Flair sentence span does not resolve to its reported text: "
                f"positions=[{reported_start}, {reported_end}) span={span_text!r} "
                f"sentence={sentence.text!r}"
            )
        relative_start = min(candidates, key=lambda value: abs(value - reported_start))
        relative_end = relative_start + len(span_text)
    if not 0 <= relative_start < relative_end <= len(sentence.text):
        raise ValueError(
            "Resolved Flair sentence span is outside sentence bounds: "
            f"[{relative_start}, {relative_end}) sentence_len={len(sentence.text)}"
        )
    reported_sentence_start = int(sentence.start_position)
    source_sentence_start = source_text.find(sentence.text, reported_sentence_start)
    if source_sentence_start < 0:
        raise ValueError(
            "Flair sentence text does not resolve to the untouched source text: "
            f"reported_start={reported_sentence_start} sentence={sentence.text!r}"
        )
    document_start = source_sentence_start + relative_start
    document_end = source_sentence_start + relative_end
    if not 0 <= document_start < document_end <= len(source_text):
        raise ValueError(
            f"Invalid lifted HunFlair2 span: [{document_start}, {document_end})"
        )
    if source_text[document_start:document_end] != span_text:
        raise ValueError(
            "Lifted HunFlair2 span does not resolve to the untouched source text: "
            f"sentence_start={source_sentence_start} relative=[{relative_start}, "
            f"{relative_end}) document=[{document_start}, {document_end}) "
            f"span={span_text!r} slice={source_text[document_start:document_end]!r}"
        )
    label = span.get_label(label_type)
    score = getattr(label, "score", None)
    return {
        "start": document_start,
        "end": document_end,
        "text": span_text,
        "label": str(label.value),
        "score": None if score is None else float(score),
    }


def _tagger_runtime_details(tagger: Any, flair: Any) -> dict[str, Any]:
    """Record the model and long-sentence inference settings used by Flair."""

    embeddings = getattr(tagger, "embeddings", None)
    tokenizer = getattr(embeddings, "tokenizer", None)
    torch = importlib.import_module("torch")
    cuda_available = bool(torch.cuda.is_available())
    return {
        "flair": getattr(flair, "__version__", None),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "pytorch": _module_version("torch") or _package_version("torch"),
        "transformers": _module_version("transformers")
        or _package_version("transformers"),
        "scispacy": _package_version("scispacy"),
        "spacy": _package_version("spacy"),
        "en_core_sci_sm": _package_version("en-core-sci-sm"),
        "device": str(getattr(flair, "device", "cpu")),
        "cuda_available": cuda_available,
        "cuda_device": torch.cuda.get_device_name(0) if cuda_available else None,
        "cuda_version": getattr(torch.version, "cuda", None),
        "tagger_class": type(tagger).__name__,
        "label_type": str(getattr(tagger, "label_type", "ner")),
        "transformer_model": getattr(embeddings, "base_model_name", None),
        "model_max_length": getattr(tokenizer, "model_max_length", None),
        "allow_long_sentences": getattr(embeddings, "allow_long_sentences", None),
        "stride": getattr(embeddings, "stride", None),
        "truncate": getattr(embeddings, "truncate", None),
        "sentence_splitter": SCISPACY_SENTENCE_SPLITTER,
        "offset_mechanics": (
            "Flair span text is resolved against the model sentence; that "
            "sentence is located in the untouched source and the lifted span "
            "is validated before serialization."
        ),
    }


def run(payload: Mapping[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Run official HunFlair2 NER over every input document."""

    documents = _documents(payload)
    if args.device:
        # Flair 0.15 interprets FLAIR_DEVICE as a CUDA index, not the string
        # ``cuda``.  Passing ``cuda`` would construct the invalid device
        # string ``cuda:cuda`` inside Flair.
        os.environ["FLAIR_DEVICE"] = "0" if args.device == "cuda" else args.device

    import flair
    from flair.nn import Classifier
    from flair.splitter import SciSpacySentenceSplitter

    tagger = Classifier.load(args.model)
    splitter = SciSpacySentenceSplitter()
    label_type = str(getattr(tagger, "label_type", "ner"))
    started = time.perf_counter()
    output_documents: list[dict[str, Any]] = []
    sentence_count = 0
    prediction_count = 0
    for document in documents:
        text = document["text"]
        sentences = splitter.split(text)
        sentence_count += len(sentences)
        if sentences:
            tagger.predict(sentences)
        predictions = [
            _prediction_for_span(sentence, span, label_type, text)
            for sentence in sentences
            for span in sentence.get_spans(label_type)
        ]
        predictions.sort(key=lambda item: (item["start"], item["end"], item["label"]))
        prediction_count += len(predictions)
        output_documents.append(
            {
                "id": document["id"],
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "predictions": predictions,
            }
        )

    duration = time.perf_counter() - started
    artifact_path = Path(args.model)
    artifact_sha256 = (
        _sha256_file(artifact_path) if artifact_path.is_file() else args.model_artifact_sha256
    )
    return {
        "documents": output_documents,
        "metadata": {
            "model_identifier": args.model_identifier,
            "model_input": args.model,
            "model_revision": args.model_revision,
            "model_artifact_sha256": artifact_sha256,
            "upstream_repository": OFFICIAL_FLAIR_REPOSITORY,
            "runtime": _tagger_runtime_details(tagger, flair),
            "document_count": len(documents),
            "sentence_count": sentence_count,
            "predicted_entity_count": prediction_count,
            "inference_duration_seconds": duration,
            "inference_scope": (
                "All supplied document text; SciSpacy sentence segmentation; "
                "Flair long-sentence striding when required; no truncation."
            ),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the isolated model and write plain JSON predictions."""

    args = _parser().parse_args(argv)
    result = run(_load_json(args.input), args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["metadata"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
