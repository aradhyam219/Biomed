"""Standalone Flair subprocess for the evaluation-only HunFlair2 run.

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

    relative_start = int(span.start_position)
    relative_end = int(span.end_position)
    span_text = str(span.text)
    if not 0 <= relative_start < relative_end <= len(sentence.text):
        raise ValueError(
            f"Flair returned invalid sentence span: [{relative_start}, {relative_end})"
        )
    if sentence.text[relative_start:relative_end] != span_text:
        raise ValueError(
            "Flair sentence span does not resolve to its reported text"
        )
    document_start = int(sentence.start_position) + relative_start
    document_end = int(sentence.start_position) + relative_end
    if not 0 <= document_start < document_end <= len(source_text):
        raise ValueError(
            f"Invalid lifted HunFlair2 span: [{document_start}, {document_end})"
        )
    if source_text[document_start:document_end] != span_text:
        raise ValueError(
            "Lifted HunFlair2 span does not resolve to the untouched source text"
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
        "tagger_class": type(tagger).__name__,
        "label_type": str(getattr(tagger, "label_type", "ner")),
        "transformer_model": getattr(embeddings, "base_model_name", None),
        "model_max_length": getattr(tokenizer, "model_max_length", None),
        "allow_long_sentences": getattr(embeddings, "allow_long_sentences", None),
        "stride": getattr(embeddings, "stride", None),
        "truncate": getattr(embeddings, "truncate", None),
        "sentence_splitter": SCISPACY_SENTENCE_SPLITTER,
        "offset_mechanics": (
            "SciSpaCy sentence boundaries retain each sentence.start_position; "
            "Flair span offsets are lifted to the untouched document text and "
            "validated before serialization."
        ),
    }


def run(payload: Mapping[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Run official HunFlair2 NER over every input document."""

    documents = _documents(payload)
    if args.device:
        os.environ["FLAIR_DEVICE"] = args.device

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
