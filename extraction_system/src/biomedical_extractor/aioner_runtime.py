"""Standalone isolated AIONER runner for arbitrary canonical source texts.

This module is invoked by the evaluation CLI inside the cached legacy AIONER
environment. It imports the official upstream implementation only at runtime,
keeps the model artifact outside the production dependency graph, and emits
plain document-relative predictions for the local AIONER adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Mapping, Sequence


OFFICIAL_AIONER_REPOSITORY = "https://github.com/ncbi/AIONER"
DEFAULT_MODEL_IDENTIFIER = "PubmedBERT-CRF-AIONER.h5"
MAX_BATCH_DOCUMENTS = 128
MAX_BATCH_CHARACTERS = 200_000


def _parser() -> argparse.ArgumentParser:
    """Build the isolated runner command contract."""

    parser = argparse.ArgumentParser(description="Run official AIONER inference.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--upstream-root", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--vocabfile", required=True, type=Path)
    parser.add_argument("--model-identifier", default=DEFAULT_MODEL_IDENTIFIER)
    parser.add_argument("--model-artifact-sha256")
    parser.add_argument("--stanza-resources", type=Path)
    return parser


def _load_json(path: Path) -> Mapping[str, Any]:
    """Load and validate one JSON runner input object."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("AIONER runner input must be a JSON object")
    return value


def _documents(payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Validate source documents without changing their text."""

    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, Sequence) or isinstance(
        raw_documents, (str, bytes)
    ):
        raise ValueError("AIONER runner input requires a documents array")
    documents: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_documents:
        if not isinstance(raw, Mapping):
            raise ValueError("AIONER runner documents must be objects")
        document_id = str(raw.get("id", ""))
        text = raw.get("text")
        if not document_id or not isinstance(text, str):
            raise ValueError("AIONER runner documents require id and string text")
        if document_id in seen:
            raise ValueError(f"Duplicate AIONER runner document ID: {document_id}")
        seen.add(document_id)
        documents.append({"id": document_id, "text": text})
    return tuple(documents)


def _sha256_file(path: Path) -> str:
    """Hash a model artifact in bounded chunks."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(distribution: str) -> str | None:
    """Return one installed distribution version when available."""

    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _load_official_model(
    upstream_root: Path,
    model_path: Path,
    vocab_path: Path,
) -> tuple[Any, Any, Any]:
    """Import and construct the exact upstream PubMedBERT-CRF model."""

    source_root = (upstream_root / "src").resolve()
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    from model_ner import HUGFACE_NER

    pretrained_root = (upstream_root / "pretrained_models").resolve()
    checkpoint = pretrained_root / (
        "BiomedNLP-PubMedBERT-base-uncased-abstract"
    )
    model_files = {
        "labelfile": str(vocab_path.resolve()),
        "checkpoint_path": str(checkpoint),
        "lowercase": True,
    }
    model = HUGFACE_NER(model_files)
    model.build_encoder()
    model.build_crf_decoder()
    model.load_model(str(model_path.resolve()))
    import AIONER_Run
    from restore_index import NN_BIO_tag_entity

    return model, AIONER_Run, NN_BIO_tag_entity


def _lift_official_predictions(
    source_text: str,
    tagged_blocks: Sequence[tuple[Sequence[str], Sequence[Any]]],
) -> list[dict[str, Any]]:
    """Lift official BIO token spans onto the untouched source text.

    AIONER's bundled ``NN_restore_index_fn`` searches each sentence in a
    mutable remainder of the source. One missing token therefore shifts every
    later offset, and the failure is especially visible on multi-sentence
    biomedical text. The model output itself is retained unchanged; this
    repository-owned lifter consumes the same token blocks and matches them in
    monotonically increasing order against the original source.
    """

    source_lower = source_text.lower()
    cursor = 0
    predictions: list[dict[str, Any]] = []
    for block_index, (tokens, entities) in enumerate(tagged_blocks):
        offsets: list[tuple[int, int]] = []
        for token in tokens:
            token_lower = token.lower()
            found = source_lower.find(token_lower, cursor)
            if found < 0:
                raise ValueError(
                    "AIONER token cannot be lifted to source text: "
                    f"block={block_index} token={token!r} cursor={cursor}"
                )
            end = found + len(token)
            offsets.append((found, end))
            cursor = end

        for entity in entities:
            if len(entity) != 3:
                raise ValueError("AIONER BIO entity must have three fields")
            token_start, token_end, label = int(entity[0]), int(entity[1]), str(entity[2])
            if not 0 <= token_start <= token_end < len(offsets):
                raise ValueError(
                    "AIONER BIO entity token span is outside its block: "
                    f"[{token_start}, {token_end}] / {len(offsets)}"
                )
            start = offsets[token_start][0]
            end = offsets[token_end][1]
            predictions.append(
                {
                    "start": start,
                    "end": end,
                    "text": source_text[start:end],
                    "label": label,
                    "score": None,
                }
            )
    return predictions


def _official_tagged_blocks(
    conll_input: str,
    model: Any,
    official: Any,
    parse_bio: Any,
) -> tuple[tuple[tuple[str, ...], tuple[Sequence[Any], ...]], ...]:
    """Decode AIONER exactly while preserving empty/truncated input blocks.

    The upstream ``out_BIO_BERT_crf_fn`` serializes empty blocks as a single
    newline, so its later ``split('\\n\\n')`` parser can merge those blocks.
    Repeating that small official decode loop in memory preserves the model
    output and the one-to-one input ordering without changing model behavior.
    """

    test_list = official.ml_intext_fn(conll_input)
    test_x, _test_y, test_bert_text_label = model.rep.load_data_hugface(
        test_list,
        word_max_len=model.maxlen,
        label_type="crf",
    )
    test_pre = model.model.predict(test_x, batch_size=64)
    tagged_blocks: list[tuple[tuple[str, ...], tuple[Sequence[Any], ...]]] = []
    for block_index, raw_input in enumerate(test_bert_text_label):
        lines: list[str] = []
        for item in raw_input:
            token = str(item[0])
            original_label = str(item[1])
            token_index = int(item[-1])
            if token_index < len(test_pre[block_index]):
                label_id = test_pre[block_index][token_index]
                label = model.rep.index_2_label[str(int(label_id))]
            else:
                label = "O"
            lines.append(f"{token}\t{original_label}\t{label}")
        parsed = parse_bio("\n".join(lines))
        if len(parsed) != 1:
            raise ValueError(
                f"AIONER BIO parser returned {len(parsed)} blocks for block "
                f"{block_index}"
            )
        tokens = tuple(line.split("\t", 1)[0] for line in lines[1:-1])
        entities = tuple(parsed[0][1])
        tagged_blocks.append((tokens, entities))
    return tuple(tagged_blocks)


def _document_batches(
    documents: Sequence[Mapping[str, str]],
) -> tuple[tuple[Mapping[str, str], ...], ...]:
    """Group documents into bounded inference batches without reordering them."""

    batches: list[tuple[Mapping[str, str], ...]] = []
    current: list[Mapping[str, str]] = []
    current_characters = 0
    for document in documents:
        document_length = len(document["text"])
        if current and (
            len(current) >= MAX_BATCH_DOCUMENTS
            or current_characters + document_length > MAX_BATCH_CHARACTERS
        ):
            batches.append(tuple(current))
            current = []
            current_characters = 0
        current.append(document)
        current_characters += document_length
    if current:
        batches.append(tuple(current))
    return tuple(batches)


def run(payload: Mapping[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Run official AIONER NER over every supplied canonical document."""

    documents = _documents(payload)
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    if args.stanza_resources is not None:
        os.environ["STANZA_RESOURCES_DIR"] = str(args.stanza_resources.resolve())
    model, official, parse_bio = _load_official_model(
        args.upstream_root, args.model, args.vocabfile
    )
    started = time.perf_counter()
    output_by_id: dict[str, dict[str, Any]] = {}
    prediction_count = 0
    sentence_count = 0
    for batch in _document_batches(documents):
        nonempty_documents = tuple(
            document for document in batch if document["text"].strip()
        )
        for document in batch:
            if document["text"].strip():
                continue
            output_by_id[document["id"]] = {
                "id": document["id"],
                "text_sha256": hashlib.sha256(
                    document["text"].encode("utf-8")
                ).hexdigest(),
                "predictions": [],
            }
        if not nonempty_documents:
            continue
        conll_parts = tuple(
            official.ssplit_token(
                document["text"],
                "ALL",
                max_len=model.maxlen,
            )
            for document in nonempty_documents
        )
        block_counts = tuple(
            len(official.ml_intext_fn(conll_part)) for conll_part in conll_parts
        )
        tagged_blocks = _official_tagged_blocks(
            "".join(conll_parts),
            model,
            official,
            parse_bio,
        )
        expected_block_count = sum(block_counts)
        if len(tagged_blocks) != expected_block_count:
            raise ValueError(
                "AIONER batch token/BIO block count mismatch: "
                f"{len(tagged_blocks)} != {expected_block_count}"
            )
        block_start = 0
        for document, block_count in zip(nonempty_documents, block_counts):
            document_blocks = tagged_blocks[block_start : block_start + block_count]
            block_start += block_count
            predictions = _lift_official_predictions(
                document["text"],
                document_blocks,
            )
            sentence_count += len(document_blocks)
            predictions.sort(
                key=lambda item: (item["start"], item["end"], item["label"])
            )
            prediction_count += len(predictions)
            output_by_id[document["id"]] = {
                "id": document["id"],
                "text_sha256": hashlib.sha256(
                    document["text"].encode("utf-8")
                ).hexdigest(),
                "predictions": predictions,
            }
    output_documents = [output_by_id[document["id"]] for document in documents]
    duration = time.perf_counter() - started
    artifact_sha256 = (
        _sha256_file(args.model)
        if args.model.is_file()
        else args.model_artifact_sha256
    )
    return {
        "documents": output_documents,
        "metadata": {
            "model_identifier": args.model_identifier,
            "model_input": str(args.model.resolve()),
            "model_artifact_sha256": artifact_sha256,
            "upstream_repository": OFFICIAL_AIONER_REPOSITORY,
            "runtime": {
                "python": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "tensorflow": _package_version("tensorflow"),
                "transformers": _package_version("transformers"),
                "stanza": _package_version("stanza"),
                "decoder": "crf",
                "entity_scope": "ALL",
                "max_sentence_tokens": 256,
                "offset_mechanics": (
                    "Official AIONER token/BIO output is lifted sequentially "
                    "onto the untouched document text and validated; the "
                    "upstream mutable-remainder offset restorer is not used."
                ),
                "max_batch_documents": MAX_BATCH_DOCUMENTS,
                "max_batch_characters": MAX_BATCH_CHARACTERS,
            },
            "document_count": len(documents),
            "sentence_count": sentence_count,
            "predicted_entity_count": prediction_count,
            "inference_duration_seconds": duration,
            "inference_scope": (
                "All supplied canonical document text through the official "
                "AIONER preprocessing/model path; repository-owned offset "
                "lifting only, with no manual correction or threshold change."
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


__all__ = ["main", "run"]
