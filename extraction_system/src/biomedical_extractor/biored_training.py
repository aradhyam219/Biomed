"""Prepare and run the V1 supervised GLiREL BioRED experiment.

BioRED stores document-level relations between normalized concepts, while GLiREL
trains on ordered mention-span pairs. This module performs the deliberately narrow
V1-A projection: eligible mentions are expanded by concept relation, both ordered
directions are emitted, and duplicate span-pair/label records are removed. The
training runner delegates batching, negative-label construction, and model
serialization to GLiREL 1.2.1's native mechanisms. Its optimizer construction
follows the named-parameter AdamW grouping used by the upstream training script.

The module is evaluation/training infrastructure only. It is not imported by the
production text-to-entities-and-relations path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import Counter
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from biomedical_extractor.biored import (
    BIORED_RELATION_LABELS,
    CANONICAL_TO_PROMPT,
    RELATION_ENTITY_TYPES,
    BioREDDocument,
    BioREDDataset,
    TypedRelation,
    load_biored,
    resolve_biored_path,
)
from biomedical_extractor.pipeline import DEFAULT_RELATION_MODEL, _tokenize


GLIREL_TRAINING_MAX_LEN = 512
SMOKE_MAX_AMP_ATTEMPTS = 8
GLIREL_RELATION_LABELS = tuple(
    CANONICAL_TO_PROMPT[label] for label in BIORED_RELATION_LABELS
)
_GLIREL_PROMPT_ORDER = {
    prompt: index for index, prompt in enumerate(GLIREL_RELATION_LABELS)
}
EXPECTED_BIORED_DEV_SHA256 = (
    "d5ab4d05673ac46fb5e3b2904d2820462dec2c4c50dfcdd8678635ff1b8ce1f5"
)


class _OrderedRelationPrompt(str):
    """Keep GLiREL's native ``sorted(label)`` on the inference prompt order."""

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            self_order = _GLIREL_PROMPT_ORDER.get(str(self))
            other_order = _GLIREL_PROMPT_ORDER.get(str(other))
            if self_order is not None and other_order is not None:
                return self_order < other_order
        return super().__lt__(other)


@dataclass(frozen=True)
class V1TrainingConfig:
    """The fixed first-pass supervised configuration for the AWS T4 run."""

    checkpoint: str = DEFAULT_RELATION_MODEL
    lr_encoder: float = 1e-5
    lr_others: float = 1e-4
    weight_decay_encoder: float = 0.01
    weight_decay_other: float = 0.01
    warmup_ratio: float = 0.1
    scheduler: str = "cosine_with_warmup"
    loss_func: str = "binary_cross_entropy_loss"
    fine_tune: bool = True
    refine_prompt: bool = False
    refine_relation: bool = False
    max_len: int = GLIREL_TRAINING_MAX_LEN
    top_k: int = 1
    fixed_relation_types: bool = True
    random_drop: bool = False
    num_unseen_rel_types: int = 0
    num_train_rel_types: int = len(BIORED_RELATION_LABELS)
    train_batch_size: int = 1
    gradient_accumulation: int = 8
    mixed_precision: str = "fp16"
    num_steps: int = 4_000
    save_every: int = 1_000
    seed: int = 0
    device: str | None = None
    add_entity_markers: bool = False

    def __post_init__(self) -> None:
        """Reject settings that would violate the first experiment contract."""

        if self.max_len != GLIREL_TRAINING_MAX_LEN:
            raise ValueError("V1 GLiREL preparation requires max_len=512")
        if self.num_train_rel_types != len(BIORED_RELATION_LABELS):
            raise ValueError("V1 training must expose exactly the eight BioRED labels")
        if self.top_k != 1:
            raise ValueError("V1 training/evaluation preparation requires top_k=1")
        if self.num_unseen_rel_types != 0:
            raise ValueError("V1 supervised training does not use unseen relation types")
        if not self.fixed_relation_types or self.random_drop:
            raise ValueError("V1 requires fixed relation types and random_drop=false")
        if self.loss_func != "binary_cross_entropy_loss":
            raise ValueError("V1 requires binary_cross_entropy_loss")
        if self.scheduler != "cosine_with_warmup":
            raise ValueError("V1 requires cosine_with_warmup")
        if self.lr_encoder <= 0 or self.lr_others <= 0:
            raise ValueError("Learning rates must be positive")
        if self.weight_decay_encoder < 0 or self.weight_decay_other < 0:
            raise ValueError("Weight decay values must be non-negative")
        if not 0 < self.warmup_ratio < 1:
            raise ValueError("warmup_ratio must be between zero and one")
        if self.train_batch_size != 1:
            raise ValueError("V1's T4 starting point requires train_batch_size=1")
        if self.gradient_accumulation <= 0:
            raise ValueError("gradient_accumulation must be positive")
        if self.mixed_precision not in {"fp16", "none"}:
            raise ValueError("mixed_precision must be fp16 or none")
        if self.num_steps <= 0 or self.save_every <= 0:
            raise ValueError("num_steps and save_every must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON representation of the selected experiment config."""

        return {
            **asdict(self),
            "relation_labels": list(BIORED_RELATION_LABELS),
            "glirel_relation_labels": list(GLIREL_RELATION_LABELS),
            "negative_supervision": (
                "GLiREL native collate_fn assigns label 0 to every generated "
                "entity pair absent from the supplied gold relations."
            ),
        }


@dataclass(frozen=True)
class ConvertedDocument:
    """One deterministic GLiREL JSONL example plus representability diagnostics."""

    document_id: str
    token_count: int
    example: dict[str, Any]
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class PreparedTrainingCorpus:
    """Prepared fitting examples and all statistics needed by the V1 report."""

    dataset: BioREDDataset
    examples: tuple[dict[str, Any], ...]
    stats: dict[str, Any]


@dataclass(frozen=True)
class TrainingPlan:
    """Validated local inputs for a later native GLiREL training run."""

    training_jsonl: Path
    output_dir: Path
    config: V1TrainingConfig


def _sha256(path: Path) -> str:
    """Hash one corpus file without loading the entire file into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_biored_dev_hash(
    dataset_path: str | Path,
    expected_sha256: str = EXPECTED_BIORED_DEV_SHA256,
) -> dict[str, str]:
    """Verify that the sibling official Dev file matches the accepted release.

    The training command requires this guard before preparing Train. Passing a
    directory or any split file is supported; the Dev file is resolved from the
    containing directory and is never used as training input.
    """

    candidate = Path(dataset_path).expanduser().resolve()
    container = candidate if candidate.is_dir() else candidate.parent
    dev_path = resolve_biored_path(container, "dev")
    actual = _sha256(dev_path)
    if actual.casefold() != expected_sha256.casefold():
        raise ValueError(
            "BioRED Dev.BioC.JSON SHA-256 mismatch: "
            f"expected {expected_sha256}, observed {actual} at {dev_path}"
        )
    return {"filename": dev_path.name, "sha256": actual}


def _dataset_identity(dataset: BioREDDataset) -> dict[str, Any]:
    """Return the source identity recorded beside generated examples."""

    return {
        "filename": dataset.path.name,
        "split": dataset.split,
        "sha256": dataset.sha256,
        "source": dataset.source,
        "date": dataset.date,
        "key": dataset.key,
    }


def _document_tokens_and_spans(
    document: BioREDDocument,
) -> tuple[tuple[str, ...], dict[str, tuple[int, int]]]:
    """Reuse V0-B's exact token pattern and supplied-boundary splitting."""

    mentions = document.relation_mentions()
    boundaries = {
        boundary for mention in mentions for boundary in (mention.start, mention.end)
    }
    tokens = _tokenize(document.text, boundaries)
    starts = {token.start: index for index, token in enumerate(tokens)}
    ends = {token.end: index for index, token in enumerate(tokens)}
    spans: dict[str, tuple[int, int]] = {}
    for mention in mentions:
        if mention.start not in starts or mention.end not in ends:
            raise ValueError(
                f"BioRED mention {document.id}:{mention.id} does not align with "
                "the exact GLiREL token boundaries"
            )
        start = starts[mention.start]
        end = ends[mention.end]
        if start > end:
            raise ValueError(f"Invalid token span for {document.id}:{mention.id}")
        spans[mention.id] = (start, end)
    return tuple(token.text for token in tokens), spans


def _relation_source(document_id: str, relation: TypedRelation) -> dict[str, str]:
    """Serialize the gold concept relation that authorized one positive pair."""

    return {
        "document_id": document_id,
        "concept_a": relation.concept_a,
        "concept_b": relation.concept_b,
        "relation_type": relation.relation_type,
    }


def _relation_record(
    head: Any,
    tail: Any,
    head_span: tuple[int, int],
    tail_span: tuple[int, int],
    relation: TypedRelation,
) -> dict[str, Any]:
    """Build one upstream-compatible GLiREL relation with traceable provenance."""

    canonical_label = relation.relation_type
    return {
        "head": {
            "mention": head.text,
            "position": list(head_span),
            "type": head.type,
        },
        "tail": {
            "mention": tail.text,
            "position": list(tail_span),
            "type": tail.type,
        },
        "relation_text": CANONICAL_TO_PROMPT[canonical_label],
        "canonical_relation_type": canonical_label,
        # GLiREL ignores this diagnostic field; it makes every positive auditable.
        "source_gold_relation": _relation_source(relation.document_id, relation),
    }


def convert_document_to_glirel(
    document: BioREDDocument,
    *,
    split: str = "train",
    max_len: int = GLIREL_TRAINING_MAX_LEN,
) -> ConvertedDocument:
    """Convert one fitting BioRED document to native GLiREL training JSON.

    For each normalized concept relation, all eligible mention cross-products are
    expanded in both ordered directions. Same-span pairs are reported and omitted
    because GLiREL 1.2.1's native relation-pair generator excludes self-pairs and
    cannot distinguish duplicate entity spans.
    """

    tokens, spans = _document_tokens_and_spans(document)
    if len(tokens) > max_len:
        raise ValueError(
            f"BioRED document {document.id} has {len(tokens)} tokens; "
            f"refusing to truncate above max_len={max_len}"
        )

    mentions = tuple(
        mention
        for mention in document.relation_mentions()
        if mention.type in RELATION_ENTITY_TYPES
    )
    mentions_by_concept: dict[str, list[Any]] = {}
    for mention in mentions:
        for concept_id in mention.concept_ids:
            mentions_by_concept.setdefault(concept_id, []).append(mention)
    for concept_mentions in mentions_by_concept.values():
        concept_mentions.sort(key=lambda item: (item.start, item.end, item.id))

    positive_by_key: dict[tuple[tuple[int, int], tuple[int, int], str], dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    unrepresentable: list[dict[str, Any]] = []
    for relation in document.relations:
        head_mentions = mentions_by_concept.get(relation.concept_a, [])
        tail_mentions = mentions_by_concept.get(relation.concept_b, [])
        if not head_mentions or not tail_mentions:
            unresolved.append(
                {
                    **_relation_source(document.id, relation),
                    "reason": "concept endpoint has no eligible relation-bearing mention",
                }
            )
            continue
        for head in head_mentions:
            for tail in tail_mentions:
                head_span = spans[head.id]
                tail_span = spans[tail.id]
                if head.id == tail.id or head_span == tail_span:
                    unrepresentable.append(
                        {
                            **_relation_source(document.id, relation),
                            "head_mention_id": head.id,
                            "tail_mention_id": tail.id,
                            "reason": "same mention/span is not a representable GLiREL pair",
                        }
                    )
                    continue
                for ordered_head, ordered_tail, ordered_head_span, ordered_tail_span in (
                    (head, tail, head_span, tail_span),
                    (tail, head, tail_span, head_span),
                ):
                    key = (ordered_head_span, ordered_tail_span, relation.relation_type)
                    positive_by_key.setdefault(
                        key,
                        _relation_record(
                            ordered_head,
                            ordered_tail,
                            ordered_head_span,
                            ordered_tail_span,
                            relation,
                        ),
                    )

    ner = [
        [spans[mention.id][0], spans[mention.id][1], mention.type, mention.text]
        for mention in mentions
    ]
    relations = [
        positive_by_key[key]
        for key in sorted(
            positive_by_key,
            key=lambda item: (item[0], item[1], item[2]),
        )
    ]
    example = {
        "tokenized_text": list(tokens),
        "ner": ner,
        "relations": relations,
        # The native collator uses this key to expose all eight labels per sample.
        "label": list(GLIREL_RELATION_LABELS),
        "metadata": {
            "document_id": document.id,
            "source_split": split,
            "token_count": len(tokens),
            "gold_relation_count": len(document.relations),
            "generated_positive_count": len(relations),
        },
    }
    diagnostics = {
        "unresolved_gold_relations": unresolved,
        "unrepresentable_mention_pairs": unrepresentable,
        "generated_positive_count": len(relations),
        "generated_positive_by_label": dict(
            Counter(relation["canonical_relation_type"] for relation in relations)
        ),
    }
    return ConvertedDocument(document.id, len(tokens), example, diagnostics)


def verify_generated_positive_origins(
    examples: Sequence[Mapping[str, Any]],
    dataset: BioREDDataset,
) -> dict[str, Any]:
    """Prove every serialized positive cites an actual gold concept relation."""

    gold_by_document = {
        document.id: {
            (relation.concept_a, relation.concept_b, relation.relation_type)
            for relation in document.relations
        }
        for document in dataset.documents
    }
    invalid: list[dict[str, Any]] = []
    checked = 0
    for example in examples:
        for relation in example["relations"]:
            checked += 1
            source = relation.get("source_gold_relation")
            key = (
                source.get("concept_a"),
                source.get("concept_b"),
                source.get("relation_type"),
            ) if isinstance(source, Mapping) else None
            canonical_label = source.get("relation_type") if isinstance(source, Mapping) else None
            expected_prompt = (
                CANONICAL_TO_PROMPT.get(canonical_label)
                if isinstance(canonical_label, str)
                else None
            )
            if (
                not isinstance(source, Mapping)
                or source.get("document_id") not in gold_by_document
                or relation.get("canonical_relation_type") != canonical_label
                or relation.get("relation_text") != expected_prompt
                or example.get("metadata", {}).get("document_id")
                != source.get("document_id")
                or key not in gold_by_document[source["document_id"]]
            ):
                invalid.append(
                    {
                        "document_id": example.get("metadata", {}).get("document_id"),
                        "relation": relation,
                    }
                )
    return {
        "checked": checked,
        "valid": checked - len(invalid),
        "invalid": len(invalid),
        "invalid_examples": invalid[:10],
    }


def prepare_training_corpus(
    dataset: BioREDDataset,
    *,
    max_len: int = GLIREL_TRAINING_MAX_LEN,
) -> PreparedTrainingCorpus:
    """Prepare all fitting documents and compute complete coverage diagnostics."""

    if max_len != GLIREL_TRAINING_MAX_LEN:
        raise ValueError("V1 training preparation requires max_len=512")

    token_counts: list[tuple[BioREDDocument, int]] = []
    for document in dataset.documents:
        tokens, _ = _document_tokens_and_spans(document)
        token_counts.append((document, len(tokens)))

    excluded = [
        (document, token_count)
        for document, token_count in token_counts
        if token_count > max_len
    ]
    fitting = [
        (document, token_count)
        for document, token_count in token_counts
        if token_count <= max_len
    ]

    converted: list[ConvertedDocument] = [
        convert_document_to_glirel(document, split=dataset.split, max_len=max_len)
        for document, _ in fitting
    ]
    examples = tuple(item.example for item in converted)
    traceability = verify_generated_positive_origins(examples, dataset)
    if traceability["invalid"]:
        raise ValueError(
            "Generated GLiREL positives are not fully traceable to BioRED gold "
            f"relations: {traceability['invalid_examples']}"
        )

    gold_by_label = Counter(
        relation.relation_type
        for document in dataset.documents
        for relation in document.relations
    )
    included_gold_by_label = Counter(
        relation.relation_type
        for document, _ in fitting
        for relation in document.relations
    )
    excluded_gold_by_label = Counter(
        relation.relation_type
        for document, _ in excluded
        for relation in document.relations
    )
    generated_by_label = Counter(
        relation["canonical_relation_type"]
        for example in examples
        for relation in example["relations"]
    )
    unresolved = [
        diagnostic
        for converted_document in converted
        for diagnostic in converted_document.diagnostics["unresolved_gold_relations"]
    ]
    unrepresentable = [
        diagnostic
        for converted_document in converted
        for diagnostic in converted_document.diagnostics["unrepresentable_mention_pairs"]
    ]
    token_values = [token_count for _, token_count in token_counts]
    excluded_records = [
        {
            "document_id": document.id,
            "tokens": token_count,
            "gold_relations": len(document.relations),
        }
        for document, token_count in excluded
    ]
    included_gold = sum(len(document.relations) for document, _ in fitting)
    official_gold = sum(len(document.relations) for document in dataset.documents)
    stats = {
        "dataset": _dataset_identity(dataset),
        "split_policy": {
            "train": "BioRED Train only for supervised examples",
            "dev": "BioRED Dev reserved for checkpoint selection and threshold calibration",
            "test": "BioRED Test untouched until an explicitly authorized final evaluation",
        },
        "max_len": max_len,
        "documents": {
            "official": len(dataset.documents),
            "included": len(fitting),
            "excluded": len(excluded),
            "coverage_percentage": 100.0 * len(fitting) / len(dataset.documents),
        },
        "gold_relations": {
            "official": official_gold,
            "included": included_gold,
            "excluded": official_gold - included_gold,
            "coverage_percentage": 100.0 * included_gold / official_gold
            if official_gold
            else None,
            "by_label": {
                label: {
                    "official": gold_by_label[label],
                    "included": included_gold_by_label[label],
                    "excluded": excluded_gold_by_label[label],
                }
                for label in BIORED_RELATION_LABELS
            },
        },
        "mentions": {
            "official": sum(len(document.mentions) for document in dataset.documents),
            "eligible_official": sum(
                len(document.relation_mentions()) for document in dataset.documents
            ),
            "included": sum(len(document.mentions) for document, _ in fitting),
            "eligible_included": sum(
                len(document.relation_mentions()) for document, _ in fitting
            ),
        },
        "token_lengths": {
            "minimum": min(token_values),
            "maximum": max(token_values),
            "mean": sum(token_values) / len(token_values),
            "documents_over_max_len": excluded_records,
        },
        "generated_positive_relations": {
            "total": sum(generated_by_label.values()),
            "by_label": {
                label: generated_by_label[label] for label in BIORED_RELATION_LABELS
            },
            "documents": len(examples),
            "documents_without_positive": sum(
                not example["relations"] for example in examples
            ),
        },
        "diagnostics": {
            "unresolved_gold_relations": len(unresolved),
            "unresolved_gold_relation_examples": unresolved[:20],
            "unrepresentable_mention_pairs": len(unrepresentable),
            "unrepresentable_mention_pair_examples": unrepresentable[:20],
            "generated_positive_origin_check": traceability,
        },
        "negative_supervision": {
            "mechanism": (
                "GLiREL 1.2.1 native InstructBase.collate_fn generates every ordered "
                "non-self entity pair and native get_rel_labels assigns 0 when no "
                "matching gold relation exists. GLiREL.forward then includes those "
                "zero labels in binary_cross_entropy_loss."
            ),
            "training_relation_labels": list(BIORED_RELATION_LABELS),
            "glirel_relation_labels": list(GLIREL_RELATION_LABELS),
        },
    }
    return PreparedTrainingCorpus(dataset, examples, stats)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one generated artifact as canonical UTF-8 bytes atomically."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary.write_bytes(payload)
    temporary.replace(path)


def write_prepared_corpus(
    prepared: PreparedTrainingCorpus,
    output_dir: str | Path,
    *,
    config: V1TrainingConfig | None = None,
    verified_dev: Mapping[str, str] | None = None,
) -> dict[str, Path]:
    """Write ignored JSONL/statistics/config artifacts used by later GPU runs."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    jsonl_path = directory / "biored_train_glirel.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for example in prepared.examples:
            handle.write(json.dumps(example, sort_keys=True) + "\n")

    stats = dict(prepared.stats)
    stats["verified_hashes"] = {
        "train": prepared.dataset.sha256,
        "dev": dict(verified_dev) if verified_dev is not None else None,
    }
    stats_path = directory / "biored_train_stats.json"
    _write_json(stats_path, stats)
    config_path = directory / "v1_training_config.json"
    _write_json(config_path, (config or V1TrainingConfig()).to_dict())
    return {"jsonl": jsonl_path, "stats": stats_path, "config": config_path}


def load_training_examples(path: str | Path) -> list[dict[str, Any]]:
    """Load and minimally validate generated GLiREL JSONL without model loading."""

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Training JSONL not found: {path}")
    examples: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            example = json.loads(line)
            if not isinstance(example, dict):
                raise ValueError(f"Training JSONL line {line_number} is not an object")
            if len(example.get("tokenized_text", ())) > GLIREL_TRAINING_MAX_LEN:
                raise ValueError(
                    f"Training JSONL line {line_number} exceeds max_len=512; refusing truncation"
                )
            if tuple(example.get("label", ())) != GLIREL_RELATION_LABELS:
                raise ValueError(
                    f"Training JSONL line {line_number} must expose all eight GLiREL prompt labels"
                )
            if any(
                relation.get("relation_text") not in GLIREL_RELATION_LABELS
                for relation in example.get("relations", ())
            ):
                raise ValueError(
                    f"Training JSONL line {line_number} contains a non-prompt relation label"
                )
            examples.append(example)
    if not examples:
        raise ValueError(f"Training JSONL contains no examples: {path}")
    return examples


def build_training_plan(
    training_jsonl: str | Path,
    output_dir: str | Path,
    config: V1TrainingConfig | None = None,
) -> TrainingPlan:
    """Construct a later-run plan without loading a checkpoint or starting training."""

    path = Path(training_jsonl).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Training JSONL not found: {path}")
    selected = config or V1TrainingConfig()
    return TrainingPlan(path, Path(output_dir).expanduser().resolve(), selected)


def _configure_model_for_v1(model: Any, config: V1TrainingConfig) -> Any:
    """Apply V1 settings to a loaded GLiREL model before native collation."""

    base_config = getattr(model, "base_config", None)
    if base_config is None:
        raise TypeError("Loaded GLiREL model does not expose base_config")
    for name in (
        "max_len",
        "fine_tune",
        "refine_prompt",
        "refine_relation",
        "fixed_relation_types",
        "random_drop",
        "num_unseen_rel_types",
        "loss_func",
        "top_k",
        "add_entity_markers",
    ):
        setattr(base_config, name, getattr(config, name))
    if hasattr(model, "config"):
        for name in (
            "fine_tune",
            "refine_prompt",
            "refine_relation",
            "fixed_relation_types",
            "random_drop",
            "num_unseen_rel_types",
            "loss_func",
            "top_k",
            "add_entity_markers",
        ):
            setattr(model.config, name, getattr(config, name))
    if hasattr(model, "token_rep_layer"):
        token_layer = model.token_rep_layer
        if hasattr(token_layer, "bert_layer"):
            token_layer.bert_layer.fine_tune = config.fine_tune
        for parameter in token_layer.parameters():
            parameter.requires_grad = config.fine_tune
    model.set_sampling_params(
        max_types=len(BIORED_RELATION_LABELS),
        shuffle_types=False,
        random_drop=False,
        max_neg_type_ratio=0,
        max_len=config.max_len,
        num_train_rel_types=len(BIORED_RELATION_LABELS),
    )
    return model


def _load_glirel_model(config: V1TrainingConfig) -> Any:
    """Load the requested pretrained checkpoint only when an AWS action starts."""

    import torch
    from glirel import GLiREL

    device = config.device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = GLiREL.from_pretrained(
        config.checkpoint,
        map_location=device,
        local_files_only=False,
    )
    model.to(device)
    model = _configure_model_for_v1(model, config)
    return model


def _native_loader(model: Any, examples: Sequence[Mapping[str, Any]], config: V1TrainingConfig) -> Any:
    """Build GLiREL's own DataLoader and collator for fixed eight-label training."""

    # GLiREL 1.2.1 sorts b["label"] inside collate_fn. These str-compatible
    # values preserve the inference order without replacing or copying its
    # native collator; the serialized JSONL remains ordinary prompt strings.
    collator_examples = [
        {
            **example,
            "label": [
                _OrderedRelationPrompt(label) for label in example["label"]
            ],
        }
        for example in examples
    ]
    return model.create_dataloader(
        collator_examples,
        batch_size=config.train_batch_size,
        shuffle=False,
        train_relation_types=list(GLIREL_RELATION_LABELS),
    )


def _build_v1_optimizer(model: Any, config: V1TrainingConfig) -> Any:
    """Build the supported GLiREL 1.2.1 named-parameter AdamW optimizer."""

    import torch
    from transformers.pytorch_utils import ALL_LAYERNORM_LAYERS
    from transformers.trainer_pt_utils import get_parameter_names

    decay_parameter_names = {
        name
        for name in get_parameter_names(model, ALL_LAYERNORM_LAYERS)
        if "bias" not in name
    }
    parameter_groups: list[dict[str, Any]] = [
        {
            "params": [],
            "lr": config.lr_others,
            "weight_decay": config.weight_decay_other,
        },
        {"params": [], "lr": config.lr_others, "weight_decay": 0.0},
        {
            "params": [],
            "lr": config.lr_encoder,
            "weight_decay": config.weight_decay_encoder,
        },
        {"params": [], "lr": config.lr_encoder, "weight_decay": 0.0},
    ]

    trainable_parameter_ids: set[int] = set()
    grouped_parameter_ids: list[int] = []
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            continue
        parameter_id = id(parameter)
        if parameter_id in trainable_parameter_ids:
            raise RuntimeError(f"Trainable parameter appears more than once: {name}")
        trainable_parameter_ids.add(parameter_id)
        is_encoder = "token_rep_layer" in name
        should_decay = name in decay_parameter_names
        if is_encoder:
            group_index = 2 if should_decay else 3
        else:
            group_index = 0 if should_decay else 1
        parameter_groups[group_index]["params"].append(parameter)
        grouped_parameter_ids.append(parameter_id)

    if set(grouped_parameter_ids) != trainable_parameter_ids or len(
        grouped_parameter_ids
    ) != len(trainable_parameter_ids):
        raise RuntimeError("V1 optimizer parameter grouping is not an exact partition")

    return torch.optim.AdamW(parameter_groups)


def _move_batch(batch: Mapping[str, Any], device: str) -> dict[str, Any]:
    """Move native tensor fields while preserving token/label metadata."""

    import torch

    return {
        key: value.to(device) if isinstance(value, torch.Tensor) else value
        for key, value in batch.items()
    }


def calculate_scheduler_steps(
    num_steps: int, gradient_accumulation: int, warmup_ratio: float
) -> tuple[int, int]:
    """Return optimizer-update and warmup counts for microstep-based training."""

    if num_steps <= 0:
        raise ValueError("num_steps must be positive")
    if gradient_accumulation <= 0:
        raise ValueError("gradient_accumulation must be positive")
    if not 0 <= warmup_ratio < 1:
        raise ValueError("warmup_ratio must be between zero and one")
    optimizer_updates = (
        num_steps + gradient_accumulation - 1
    ) // gradient_accumulation
    warmup_steps = int(optimizer_updates * warmup_ratio)
    return optimizer_updates, warmup_steps


def _expected_relation_pair_count(example: Mapping[str, Any]) -> int:
    """Estimate native ordered non-self relation pairs for one fitting example."""

    entity_count = len(example.get("ner", ()))
    return entity_count * max(entity_count - 1, 0)


def _select_smoke_example(examples: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Select the deterministic fitting example with the largest smoke workload."""

    if not examples:
        raise ValueError("GPU smoke test requires at least one training example")

    def sort_key(example: Mapping[str, Any]) -> tuple[int, int, str]:
        metadata = example.get("metadata", {})
        document_id = str(metadata.get("document_id", ""))
        return (
            -_expected_relation_pair_count(example),
            -len(example.get("tokenized_text", ())),
            document_id,
        )

    return min(examples, key=sort_key)


def _learning_rate_snapshot(optimizer: Any) -> dict[str, float]:
    """Return the two native GLiREL learning-rate groups by role."""

    groups = optimizer.param_groups
    return {
        "others": float(groups[0]["lr"]),
        "encoder": float(groups[-1]["lr"]),
    }


def _inspect_unscaled_gradients(model: Any, torch: Any) -> dict[str, Any]:
    """Inspect all unscaled gradients with tensor-level reductions."""

    gradients = [
        parameter.grad.detach()
        for parameter in model.parameters()
        if parameter.requires_grad and parameter.grad is not None
    ]
    if not gradients:
        return {
            "gradient_tensors": 0,
            "gradients_finite": False,
            "gradient_norm_finite": False,
            "gradient_norm_nonzero": False,
            "global_unscaled_gradient_norm": None,
            "gradient_validation_error": "no trainable gradients",
        }

    finite_by_gradient = torch.stack(
        [torch.isfinite(gradient).all() for gradient in gradients]
    )
    if not bool(finite_by_gradient.all().item()):
        return {
            "gradient_tensors": len(gradients),
            "gradients_finite": False,
            "gradient_norm_finite": False,
            "gradient_norm_nonzero": False,
            "global_unscaled_gradient_norm": None,
            "gradient_validation_error": "unscaled gradients contain non-finite values",
        }

    per_gradient_norms = torch._foreach_norm(gradients, 2.0)
    global_norm = torch.linalg.vector_norm(
        torch.stack([norm.float() for norm in per_gradient_norms]), ord=2
    )
    norm_finite = bool(torch.isfinite(global_norm).item())
    if not norm_finite:
        return {
            "gradient_tensors": len(gradients),
            "gradients_finite": True,
            "gradient_norm_finite": False,
            "gradient_norm_nonzero": False,
            "global_unscaled_gradient_norm": None,
            "gradient_validation_error": "global unscaled gradient norm is non-finite",
        }
    norm_nonzero = bool(global_norm.gt(0).item())
    return {
        "gradient_tensors": len(gradients),
        "global_unscaled_gradient_norm": float(global_norm.detach().cpu()),
        "gradients_finite": True,
        "gradient_norm_finite": norm_finite,
        "gradient_norm_nonzero": norm_nonzero,
    }


def _validate_unscaled_gradients(model: Any, torch: Any) -> dict[str, Any]:
    """Validate all unscaled gradients with tensor-level reductions."""

    metrics = _inspect_unscaled_gradients(model, torch)
    if not metrics["gradients_finite"]:
        if metrics.get("gradient_validation_error") == "no trainable gradients":
            raise RuntimeError("V1 GPU smoke test produced no trainable gradients")
        raise RuntimeError(
            "V1 GPU smoke test AMP-overflow blocker: unscaled gradients contain "
            "non-finite values; GradScaler would skip optimizer.step()"
        )
    if not metrics["gradient_norm_finite"]:
        raise RuntimeError(
            "V1 GPU smoke test produced a non-finite global unscaled gradient norm"
        )
    if not metrics["gradient_norm_nonzero"]:
        raise RuntimeError(
            "V1 GPU smoke test produced a zero global unscaled gradient norm"
        )
    return metrics


def _optimizer_step_snapshot(optimizer: Any, torch: Any) -> Any:
    """Return ordered optimizer step state without scalar host synchronization."""

    step_values: list[Any] = []
    reference_device = None
    for group in optimizer.param_groups:
        for parameter in group["params"]:
            state = optimizer.state.get(parameter)
            if not state or "step" not in state:
                step_values.append(None)
                continue
            step = state["step"]
            if torch.is_tensor(step):
                value = step.detach().reshape(())
            else:
                value = torch.as_tensor(step, dtype=torch.float32)
            if reference_device is None:
                reference_device = value.device
            step_values.append(value)

    if not step_values:
        return torch.empty(0, dtype=torch.float32)

    if reference_device is None:
        reference_device = torch.device("cpu")
    return torch.stack(
        [
            (
                torch.zeros((), dtype=torch.float32, device=reference_device)
                if step is None
                else step.to(device=reference_device, dtype=torch.float32)
            )
            for step in step_values
        ]
    )


def _optimizer_step_status(optimizer: Any, torch: Any) -> dict[str, Any]:
    """Check optimizer state for a first AdamW update without reading parameters."""

    steps = _optimizer_step_snapshot(optimizer, torch)
    if not steps.numel():
        return {
            "optimizer_step_completed": False,
            "optimizer_parameters_at_step_1": 0,
        }
    parameters_at_step_1 = int(steps.eq(1).sum().item())
    return {
        "optimizer_step_completed": parameters_at_step_1 > 0,
        "optimizer_parameters_at_step_1": parameters_at_step_1,
    }


def _optimizer_step_advanced(before: Any, after: Any, torch: Any) -> bool:
    """Return whether any optimizer parameter's step state increased."""

    if before.numel() != after.numel():
        raise RuntimeError("Optimizer parameter state shape changed during training")
    return bool(torch.gt(after, before).any().item())


def _timed_smoke_stage(
    torch: Any,
    device: str,
    timings: dict[str, float],
    name: str,
    action: Any,
) -> Any:
    """Run one smoke stage with synchronized CUDA timing boundaries."""

    if device.startswith("cuda"):
        torch.cuda.synchronize(device)
    started = time.perf_counter()
    try:
        return action()
    finally:
        if device.startswith("cuda"):
            torch.cuda.synchronize(device)
        timings[name] = time.perf_counter() - started


def _peak_cuda_memory(torch: Any, device: str) -> dict[str, int | None]:
    """Read peak CUDA allocation counters, or nulls for a non-CUDA run."""

    if not device.startswith("cuda"):
        return {
            "peak_cuda_memory_allocated_bytes": None,
            "peak_cuda_memory_reserved_bytes": None,
        }
    torch.cuda.synchronize(device)
    return {
        "peak_cuda_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "peak_cuda_memory_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
    }


def run_gpu_smoke_test(plan: TrainingPlan) -> dict[str, Any]:
    """Run a bounded dynamic-AMP forward/backward/update check on one batch."""

    import torch

    config = plan.config
    device = config.device or ("cuda" if torch.cuda.is_available() else "cpu")
    stage_timings: dict[str, float] = {}
    model = _timed_smoke_stage(
        torch,
        device,
        stage_timings,
        "model_load",
        lambda: _load_glirel_model(config),
    )
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)

    def materialize_inputs() -> tuple[list[dict[str, Any]], Mapping[str, Any], Any]:
        examples = load_training_examples(plan.training_jsonl)
        selected_example = _select_smoke_example(examples)
        loader = _native_loader(model, [selected_example], config)
        return examples, selected_example, loader

    examples, selected_example, loader = _timed_smoke_stage(
        torch,
        device,
        stage_timings,
        "batch_materialization",
        materialize_inputs,
    )
    model.train()
    optimizer = _build_v1_optimizer(model, config)
    optimizer.zero_grad(set_to_none=True)
    amp_enabled = config.mixed_precision == "fp16" and device.startswith("cuda")
    scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)

    batch = _timed_smoke_stage(
        torch,
        device,
        stage_timings,
        "collator_materialization",
        lambda: _move_batch(next(iter(loader)), device),
    )

    attempts: list[dict[str, Any]] = []
    successful_attempt: dict[str, Any] | None = None
    memory = {
        "peak_cuda_memory_allocated_bytes": None,
        "peak_cuda_memory_reserved_bytes": None,
    }
    gradients_zeroed = True

    for attempt_number in range(1, SMOKE_MAX_AMP_ATTEMPTS + 1):
        attempt_timings: dict[str, float] = {}
        attempt = {
            "attempt": attempt_number,
            "loss": None,
            "gradients_finite": None,
            "gradient_norm_finite": None,
            "gradient_norm_nonzero": None,
            "global_unscaled_gradient_norm": None,
            "gradient_tensors": 0,
            "scaler_scale_before": float(scaler.get_scale()),
            "scaler_scale_after": None,
            "overflow": None,
            "optimizer_update_skipped": None,
            "optimizer_step_completed": False,
            "optimizer_parameters_at_step_1": 0,
            "stage_timings_seconds": attempt_timings,
        }
        should_retry = False
        attempt_succeeded = False
        memory_captured = False

        optimizer.zero_grad(set_to_none=True)
        try:
            def forward_pass() -> Any:
                autocast_context = (
                    torch.autocast(device_type="cuda", dtype=torch.float16)
                    if amp_enabled
                    else nullcontext()
                )
                with autocast_context:
                    output = model(batch)
                    loss = output["total_loss"]
                if not bool(torch.isfinite(loss).all()):
                    raise RuntimeError(
                        f"V1 GPU smoke test produced a non-finite loss: {loss}"
                    )
                return loss

            loss = _timed_smoke_stage(
                torch, device, attempt_timings, "forward", forward_pass
            )
            attempt["loss"] = float(loss.detach().cpu())

            _timed_smoke_stage(
                torch,
                device,
                attempt_timings,
                "backward",
                lambda: scaler.scale(loss).backward(),
            )

            def inspect_gradients() -> dict[str, Any]:
                scaler.unscale_(optimizer)
                return _inspect_unscaled_gradients(model, torch)

            gradient_metrics = _timed_smoke_stage(
                torch,
                device,
                attempt_timings,
                "gradient_validation",
                inspect_gradients,
            )
            attempt.update(gradient_metrics)
            attempt["overflow"] = not gradient_metrics["gradients_finite"]

            def optimizer_scaler_step() -> float:
                scaler.step(optimizer)
                scaler.update()
                return float(scaler.get_scale())

            scaler_scale_after = _timed_smoke_stage(
                torch,
                device,
                attempt_timings,
                "optimizer_scaler_step",
                optimizer_scaler_step,
            )
            attempt["scaler_scale_after"] = scaler_scale_after
            if scaler_scale_after < attempt["scaler_scale_before"]:
                attempt["overflow"] = True

            # Read peak memory before any post-step optimizer-state validation.
            memory = _peak_cuda_memory(torch, device)
            attempt.update(memory)
            memory_captured = True
            optimizer_status = _optimizer_step_status(optimizer, torch)
            attempt.update(optimizer_status)
            attempt["optimizer_update_skipped"] = not optimizer_status[
                "optimizer_step_completed"
            ]

            attempt_succeeded = bool(
                gradient_metrics["gradients_finite"]
                and gradient_metrics["gradient_norm_finite"]
                and gradient_metrics["gradient_norm_nonzero"]
                and optimizer_status["optimizer_step_completed"]
            )
            if attempt_succeeded:
                attempt["status"] = "PASS"
                successful_attempt = attempt
            elif attempt["overflow"] and attempt_number < SMOKE_MAX_AMP_ATTEMPTS:
                attempt["status"] = "AMP_OVERFLOW"
                attempt["retry"] = True
                should_retry = True
            elif attempt["overflow"]:
                attempt["status"] = "BLOCKER"
                attempt["blocker_reason"] = (
                    "AMP-overflow blocker: non-finite unscaled gradients persisted "
                    f"through {SMOKE_MAX_AMP_ATTEMPTS} smoke attempts"
                )
            elif not gradient_metrics["gradient_norm_nonzero"]:
                attempt["status"] = "BLOCKER"
                attempt["blocker_reason"] = (
                    "gradient-validation blocker: global unscaled gradient norm "
                    "was zero or not finite"
                )
            else:
                attempt["status"] = "BLOCKER"
                attempt["blocker_reason"] = (
                    "optimizer-step blocker: no optimizer parameter reached step 1"
                )
        except Exception as error:
            attempt["status"] = "BLOCKER"
            attempt["blocker_reason"] = "material runtime error"
            attempt["error"] = f"{type(error).__name__}: {error}"
        finally:
            if not memory_captured:
                try:
                    memory = _peak_cuda_memory(torch, device)
                    attempt.update(memory)
                except Exception as memory_error:
                    attempt["memory_error"] = (
                        f"{type(memory_error).__name__}: {memory_error}"
                    )
            try:
                optimizer.zero_grad(set_to_none=True)
            except Exception as zero_error:
                gradients_zeroed = False
                attempt["gradient_zero_error"] = (
                    f"{type(zero_error).__name__}: {zero_error}"
                )
            attempts.append(attempt)

        if attempt_succeeded:
            break
        if not should_retry:
            break

    timed_stage_names = (
        "model_load",
        "batch_materialization",
        "collator_materialization",
        "forward",
        "backward",
        "gradient_validation",
        "optimizer_scaler_step",
    )
    aggregated_timings = {
        name: float(stage_timings.get(name, 0.0)) for name in timed_stage_names
    }
    for name in timed_stage_names[3:]:
        aggregated_timings[name] = sum(
            float(attempt["stage_timings_seconds"].get(name, 0.0))
            for attempt in attempts
        )

    last_attempt = attempts[-1]
    status = "PASS" if successful_attempt is not None else "BLOCKER"
    successful_loss = (
        successful_attempt["loss"] if successful_attempt is not None else None
    )
    successful_norm = (
        successful_attempt["global_unscaled_gradient_norm"]
        if successful_attempt is not None
        else None
    )
    successful_scale = (
        successful_attempt["scaler_scale_after"]
        if successful_attempt is not None
        else None
    )
    return {
        "status": status,
        "checkpoint": config.checkpoint,
        "device": device,
        "examples_available": len(examples),
        "tokens": len(batch["tokens"][0]),
        "candidate_pairs": int(batch["rel_label"].shape[1]),
        "loss": successful_loss,
        "amp_enabled": amp_enabled,
        "attempt_count": len(attempts),
        "max_attempts": SMOKE_MAX_AMP_ATTEMPTS,
        "amp_overflow_attempts": sum(
            1 for attempt in attempts if attempt["overflow"] is True
        ),
        "scaler_scale_trajectory": [
            {
                "attempt": attempt["attempt"],
                "before": attempt["scaler_scale_before"],
                "after": attempt["scaler_scale_after"],
            }
            for attempt in attempts
        ],
        "successful_scale": successful_scale,
        "successful_loss": successful_loss,
        "successful_global_unscaled_gradient_norm": successful_norm,
        "global_unscaled_gradient_norm": (
            successful_norm
            if successful_attempt is not None
            else last_attempt["global_unscaled_gradient_norm"]
        ),
        "gradients_finite": (
            True
            if successful_attempt is not None
            else last_attempt["gradients_finite"]
        ),
        "gradient_norm_finite": last_attempt["gradient_norm_finite"],
        "gradient_norm_nonzero": last_attempt["gradient_norm_nonzero"],
        "optimizer_step_completed": successful_attempt is not None,
        "optimizer_parameters_at_step_1": last_attempt[
            "optimizer_parameters_at_step_1"
        ],
        "scaler_scale_before": last_attempt["scaler_scale_before"],
        "scaler_scale_after": last_attempt["scaler_scale_after"],
        "attempts": attempts,
        "stage_timings_seconds": aggregated_timings,
        "gradients_zeroed": gradients_zeroed,
        "blocker_reason": (
            None
            if successful_attempt is not None
            else last_attempt.get("blocker_reason", "smoke did not pass")
        ),
        "tested_example": {
            "document_id": selected_example.get("metadata", {}).get("document_id"),
            "token_count": len(selected_example.get("tokenized_text", ())),
            "entity_count": len(selected_example.get("ner", ())),
            "expected_relation_pairs": _expected_relation_pair_count(selected_example),
            "positive_relation_count": len(selected_example.get("relations", ())),
        },
        **memory,
    }


def run_training(plan: TrainingPlan) -> dict[str, Any]:
    """Run the narrow native GLiREL training loop and save periodic checkpoints."""

    import torch
    from transformers import get_cosine_schedule_with_warmup

    config = plan.config
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)
    plan.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(plan.output_dir / "v1_training_config.json", config.to_dict())

    examples = load_training_examples(plan.training_jsonl)
    model = _load_glirel_model(config)
    device = config.device or ("cuda" if torch.cuda.is_available() else "cpu")
    loader = _native_loader(model, examples, config)
    optimizer = _build_v1_optimizer(model, config)
    scheduler_total_steps, warmup_steps = calculate_scheduler_steps(
        config.num_steps, config.gradient_accumulation, config.warmup_ratio
    )
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=scheduler_total_steps,
    )
    amp_enabled = config.mixed_precision == "fp16" and device.startswith("cuda")
    scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)
    scaler_enabled = (
        bool(scaler.is_enabled()) if hasattr(scaler, "is_enabled") else amp_enabled
    )
    model.train()
    optimizer.zero_grad(set_to_none=True)
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
    iterator = iter(loader)
    last_loss = None
    updates = 0
    amp_skipped_updates = 0
    progression: list[dict[str, Any]] = []
    for step in range(1, config.num_steps + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        batch = _move_batch(batch, device)
        autocast_context = (
            torch.autocast(device_type="cuda", dtype=torch.float16)
            if amp_enabled
            else nullcontext()
        )
        with autocast_context:
            output = model(batch)
            loss = output["total_loss"]
            scaled_loss = loss / config.gradient_accumulation
        if not bool(torch.isfinite(loss).all()):
            raise RuntimeError(f"V1 training produced a non-finite loss at step {step}")
        scaler.scale(scaled_loss).backward()
        if step % config.gradient_accumulation == 0 or step == config.num_steps:
            optimizer_steps_before = _optimizer_step_snapshot(optimizer, torch)
            scaler.step(optimizer)
            scaler.update()
            optimizer_steps_after = _optimizer_step_snapshot(optimizer, torch)
            optimizer_stepped = _optimizer_step_advanced(
                optimizer_steps_before, optimizer_steps_after, torch
            )
            if optimizer_stepped:
                scheduler.step()
                updates += 1
            elif scaler_enabled:
                amp_skipped_updates += 1
            optimizer.zero_grad(set_to_none=True)
        last_loss = float(loss.detach().cpu())
        if step % config.save_every == 0 or step == config.num_steps:
            progression.append(
                {
                    "microstep": step,
                    "optimizer_updates": updates,
                    "amp_skipped_updates": amp_skipped_updates,
                    "loss": last_loss,
                    "learning_rate": _learning_rate_snapshot(optimizer),
                }
            )
        if step % config.save_every == 0 and step < config.num_steps:
            model.save_pretrained(plan.output_dir / f"step_{step}")
    if updates > scheduler_total_steps:
        raise RuntimeError(
            "V1 optimizer-update count exceeded scheduler total steps: "
            f"{updates} > {scheduler_total_steps}"
        )
    final_path = plan.output_dir / "final"
    model.save_pretrained(final_path)
    memory = _peak_cuda_memory(torch, device)
    final_scaler_scale = float(scaler.get_scale())
    summary = {
        "checkpoint": config.checkpoint,
        "output_dir": str(plan.output_dir),
        "final_checkpoint": str(final_path),
        "steps": config.num_steps,
        "optimizer_updates": updates,
        "amp_skipped_updates": amp_skipped_updates,
        "scheduler_total_steps": scheduler_total_steps,
        "intended_optimizer_updates": scheduler_total_steps,
        "warmup_steps": warmup_steps,
        "final_scaler_scale": final_scaler_scale,
        "last_loss": last_loss,
        "examples": len(examples),
        "device": device,
        "training_progression": progression,
        **memory,
    }
    _write_json(plan.output_dir / "training_summary.json", summary)
    return summary


def _config_from_args(args: argparse.Namespace) -> V1TrainingConfig:
    """Build the fixed config with only run-control overrides exposed."""

    return V1TrainingConfig(
        checkpoint=args.checkpoint,
        num_steps=args.steps,
        save_every=args.save_every,
        device=args.device,
        mixed_precision=args.mixed_precision,
        seed=args.seed,
    )


def _parser() -> argparse.ArgumentParser:
    """Create the V1-A preparation and V1-B runner command line."""

    parser = argparse.ArgumentParser(description="Prepare/train the supervised GLiREL BioRED experiment")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="prepare deterministic BioRED Train JSONL")
    prepare.add_argument("--dataset", required=True, type=Path)
    prepare.add_argument("--output-dir", type=Path, default=Path(".cache/v1/biored_train"))
    prepare.add_argument("--split", choices=("train",), default="train")

    def add_run_args(command: argparse.ArgumentParser, *, output_required: bool) -> None:
        command.add_argument("--training-jsonl", required=True, type=Path)
        command.add_argument("--checkpoint", default=DEFAULT_RELATION_MODEL)
        command.add_argument("--device", default=None)
        command.add_argument("--mixed-precision", choices=("fp16", "none"), default="fp16")
        command.add_argument("--seed", type=int, default=0)
        command.add_argument("--steps", type=int, default=4_000)
        command.add_argument("--save-every", type=int, default=1_000)
        command.add_argument("--output-dir", type=Path, required=output_required)

    smoke = subparsers.add_parser("smoke", help="run one forward/backward GPU smoke test")
    add_run_args(smoke, output_required=False)

    train = subparsers.add_parser("train", help="run the GPU fine-tuning loop")
    add_run_args(train, output_required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch preparation, smoke testing, or the later GPU training run."""

    args = _parser().parse_args(argv)
    if args.command == "prepare":
        verified_dev = verify_biored_dev_hash(args.dataset)
        dataset = load_biored(args.dataset, args.split)
        prepared = prepare_training_corpus(dataset)
        paths = write_prepared_corpus(prepared, args.output_dir)
        stats = dict(prepared.stats)
        stats["verified_hashes"] = {"train": dataset.sha256, "dev": verified_dev}
        _write_json(paths["stats"], stats)
        print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))
        return 0

    config = _config_from_args(args)
    output_dir = args.output_dir if args.command == "train" else Path(".cache/v1/smoke")
    plan = build_training_plan(args.training_jsonl, output_dir, config)
    if args.command == "smoke":
        result = run_gpu_smoke_test(plan)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    else:
        print(json.dumps(run_training(plan), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
