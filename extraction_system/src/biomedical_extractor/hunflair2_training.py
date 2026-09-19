"""Training-ready Flair adapter for the selected HunFlair2 base model.

The production package deliberately does not depend on Flair.  This module
keeps Flair imports lazy so the isolated Python 3.11 runtime under
``.cache/hunflair2/runtime`` can import it without adding Flair to the main
environment.  It validates the repository-owned target gold package first,
constructs explicit paper-level train/dev/test datasets, and delegates real
fine-tuning to Flair's official ``ModelTrainer.fine_tune`` mechanism.

The smoke path is intentionally separate from target training.  It uses a tiny
synthetic fixture, records finite-loss/gradient/update/checkpoint evidence, and
stores only disposable checkpoints below the ignored smoke cache.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import shutil
from typing import Any, Mapping, Sequence

from .ner_reconnaissance import load_target_corpus
from .target_domain_pilot import (
    HUNFLAIR2_TRAINING_LABEL_BY_TYPE,
    TrainingCompatibilityError,
    assert_flat_hunflair2_gold_supported,
    load_annotation_package,
    sha256_file,
    sha256_json,
    validate_annotation_package,
)


@dataclass(frozen=True)
class HunFlair2TrainingConfig:
    """Reproducible settings for future target-domain fine-tuning."""

    base_model: str = "hunflair/hunflair2-ner"
    base_model_revision: str | None = None
    base_model_artifact_sha256: str | None = None
    random_seed: int = 17
    max_epochs: int = 10
    learning_rate: float = 5e-5
    mini_batch_size: int = 4
    gradient_accumulation_steps: int = 1
    mixed_precision: bool = False
    device: str = "cuda"
    checkpoint_location: str = ".cache/hunflair2/training/target-domain"
    output_model_location: str = ".cache/hunflair2/training/target-domain/final-model.pt"
    train_manifest: str = "reports/target_domain_pilot_2026-09-19.json"
    dev_manifest: str = "reports/target_domain_pilot_2026-09-19.json"
    test_manifest: str = "reports/target_domain_pilot_2026-09-19.json"
    canonical_corpus: str = ".cache/ner_target_domain/target_corpus.json"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "HunFlair2TrainingConfig":
        """Create a validated configuration from JSON-compatible values."""

        fields = {field.name for field in cls.__dataclass_fields__.values()}
        unknown = sorted(set(value) - fields)
        if unknown:
            raise ValueError(f"Unknown HunFlair2 training config field(s): {unknown}")
        config = cls(**{key: value[key] for key in value if key in fields})
        config.validate()
        return config

    @classmethod
    def from_path(cls, path: Path) -> "HunFlair2TrainingConfig":
        """Load and validate one JSON configuration file."""

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("HunFlair2 training config must be a JSON object")
        return cls.from_mapping(payload)

    def validate(self) -> None:
        """Reject settings that could make a future run irreproducible."""

        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative")
        if self.max_epochs <= 0:
            raise ValueError("max_epochs must be positive")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if self.mini_batch_size <= 0:
            raise ValueError("mini_batch_size must be positive")
        if self.gradient_accumulation_steps <= 0:
            raise ValueError("gradient_accumulation_steps must be positive")
        if self.device not in {"cuda", "cpu"}:
            raise ValueError("device must be 'cuda' or 'cpu'")
        for field in (
            "base_model",
            "checkpoint_location",
            "output_model_location",
            "train_manifest",
            "dev_manifest",
            "test_manifest",
            "canonical_corpus",
        ):
            if not str(getattr(self, field)):
                raise ValueError(f"{field} must not be empty")
        if self.base_model_revision is not None and not self.base_model_revision:
            raise ValueError("base_model_revision must not be empty when provided")
        if self.base_model_artifact_sha256 is not None and len(self.base_model_artifact_sha256) != 64:
            raise ValueError("base_model_artifact_sha256 must be a 64-character SHA-256")

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible configuration values."""

        return asdict(self)


def load_training_config(path: Path | None = None) -> HunFlair2TrainingConfig:
    """Load an explicit config or return the conservative documented defaults."""

    return HunFlair2TrainingConfig.from_path(path) if path else HunFlair2TrainingConfig()


def _resolve_path(path: str | Path, *, root: Path | None = None) -> Path:
    """Resolve a config path relative to the repository working directory."""

    value = Path(path)
    if value.is_absolute():
        return value
    return (root or Path.cwd()) / value


def _load_package_for_split(
    path: Path,
    split: str,
    *,
    canonical_papers: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Load one complete package and return only its requested paper split."""

    package = load_annotation_package(path)
    validate_annotation_package(
        package,
        canonical_papers=canonical_papers,
        require_complete=True,
    )
    assert_flat_hunflair2_gold_supported(package)
    examples = [item for item in package["examples"] if item.get("split") == split]
    if not examples:
        raise ValueError(f"Gold manifest {path} has no complete {split} examples")
    return {"package": package, "examples": examples}


def load_training_splits(
    config: HunFlair2TrainingConfig,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Load complete gold manifests and enforce paper-level split boundaries."""

    config.validate()
    paths = {
        "train": _resolve_path(config.train_manifest, root=root),
        "dev": _resolve_path(config.dev_manifest, root=root),
        "test": _resolve_path(config.test_manifest, root=root),
    }
    canonical_path = _resolve_path(config.canonical_corpus, root=root)
    if not canonical_path.is_file():
        raise FileNotFoundError(
            f"Canonical target corpus required for training provenance: {canonical_path}"
        )
    canonical_papers = load_target_corpus(canonical_path)
    loaded = {
        split: _load_package_for_split(
            path,
            split,
            canonical_papers=canonical_papers,
        )
        for split, path in paths.items()
    }
    first_package = loaded["train"]["package"]
    first_source = first_package.get("canonical_source", {})
    first_split = first_package.get("paper_split", {}).get("paper_splits", {})
    for split, value in loaded.items():
        package = value["package"]
        if package.get("paper_split", {}).get("paper_splits", {}) != first_split:
            raise ValueError(f"{split} manifest disagrees with train paper split")
        if package.get("canonical_source", {}).get("manifest_sha256") != first_source.get(
            "manifest_sha256"
        ):
            raise ValueError(f"{split} manifest disagrees with canonical source identity")

    paper_ids: dict[str, set[str]] = {split: set() for split in loaded}
    example_ids: dict[str, set[str]] = {split: set() for split in loaded}
    for split, value in loaded.items():
        for item in value["examples"]:
            paper_ids[split].add(str(item["paper_id"]))
            example_id = str(item["example_id"])
            if example_id in example_ids[split]:
                raise ValueError(f"Duplicate {split} example_id: {example_id}")
            example_ids[split].add(example_id)
    for left in SPLIT_NAMES:
        for right in SPLIT_NAMES:
            if left >= right:
                continue
            overlap = paper_ids[left] & paper_ids[right]
            if overlap:
                raise ValueError(
                    f"Paper leakage between {left} and {right}: {sorted(overlap)}"
                )
    expected = set(first_split)
    observed = set().union(*paper_ids.values())
    if expected != observed:
        raise ValueError(
            f"Training manifests do not cover the frozen paper split: "
            f"missing={sorted(expected - observed)}, extra={sorted(observed - expected)}"
        )
    return {
        "paths": {split: str(path) for split, path in paths.items()},
        "packages": {split: value["package"] for split, value in loaded.items()},
        "examples": {split: value["examples"] for split, value in loaded.items()},
        "paper_ids": {split: sorted(values) for split, values in paper_ids.items()},
        "example_counts": {split: len(values) for split, values in example_ids.items()},
    }


SPLIT_NAMES = ("train", "dev", "test")


def _token_span_for_char_offsets(
    sentence: Any,
    start: int,
    end: int,
    *,
    source_text: str | None = None,
) -> tuple[int, int]:
    """Resolve one exact character span to inclusive Flair token indexes."""

    tokens = list(sentence)
    matching = [
        index
        for index, token in enumerate(tokens)
        if token.start_position >= start and token.end_position <= end
    ]
    if not matching:
        raise TrainingCompatibilityError(
            f"Gold span [{start}, {end}) does not contain a complete Flair token span"
        )
    first, last = matching[0], matching[-1]
    if tokens[first].start_position != start or tokens[last].end_position != end:
        raise TrainingCompatibilityError(
            f"Gold span [{start}, {end}) cuts a Flair token boundary in "
            f"sentence {sentence.text!r}"
        )
    span = sentence[first : last + 1]
    expected_text = sentence.text[start:end] if source_text is None else source_text[start:end]
    # Flair's tokenizer preserves token character positions but normalizes
    # newline/tab whitespace inside ``Span.text``.  Gold source text remains
    # authoritative; compare whitespace-normalized forms only at this adapter
    # boundary while retaining exact source offsets in the package.
    if span.text != expected_text and " ".join(span.text.split()) != " ".join(expected_text.split()):
        raise TrainingCompatibilityError(
            f"Flair token span text {span.text!r} does not equal gold {expected_text!r}"
        )
    return first, last + 1


def _flair_sentence(item: Mapping[str, Any]) -> Any:
    """Convert one validated gold item into a labeled Flair Sentence."""

    from flair.data import Sentence

    text = str(item["text"])
    sentence = Sentence(text, use_tokenizer=True)
    if any(
        text[token.start_position : token.end_position] != token.text
        for token in sentence
    ):
        raise TrainingCompatibilityError(
            f"Flair tokenizer changed a token/source offset for {item['example_id']}"
        )
    sentence.add_metadata("example_id", str(item["example_id"]))
    sentence.add_metadata("paper_id", str(item["paper_id"]))
    sentence.add_metadata("split", str(item["split"]))
    for entity in item["entities"]:
        entity_type = str(entity["type"])
        label = HUNFLAIR2_TRAINING_LABEL_BY_TYPE.get(entity_type)
        if label is None:
            raise TrainingCompatibilityError(
                f"No flat HunFlair2 label exists for gold type {entity_type!r}"
            )
        start = int(entity["start"])
        end = int(entity["end"])
        token_start, token_end = _token_span_for_char_offsets(
            sentence,
            start,
            end,
            source_text=text,
        )
        sentence[token_start:token_end].add_label("ner", label)
    return sentence


def build_flair_corpus(training_splits: Mapping[str, Any]) -> Any:
    """Build a Flair Corpus without sampling or merging document-level splits."""

    from flair.data import Corpus
    from flair.datasets import FlairDatapointDataset

    datasets = {
        split: FlairDatapointDataset(
            [_flair_sentence(item) for item in training_splits["examples"][split]]
        )
        for split in SPLIT_NAMES
    }
    return Corpus(
        train=datasets["train"],
        dev=datasets["dev"],
        test=datasets["test"],
        name="target_domain_gold_pilot",
        sample_missing_splits=False,
        random_seed=17,
    )


def _seed_runtime(seed: int, torch: Any) -> None:
    """Seed Python and runtime RNGs before loading/train-time shuffling."""

    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _configure_flair_device(device: str, flair: Any, torch: Any) -> None:
    """Set Flair's global device and fail closed when CUDA was requested."""

    if device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA training requested, but torch.cuda.is_available() is false"
            )
        flair.device = torch.device("cuda")
    else:
        flair.device = torch.device("cpu")


def _prepare_flair_environment(device: str) -> None:
    """Set Flair's pre-import device convention for isolated runtime calls."""

    os.environ["FLAIR_DEVICE"] = "0" if device == "cuda" else "cpu"


def _module_version(name: str) -> str | None:
    """Read a runtime package version without importing optional modules."""

    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _runtime_metadata(flair: Any, torch: Any, *, requested_device: str) -> dict[str, Any]:
    """Capture the runtime and actual compute device for an evidence artifact."""

    cuda = torch.cuda.is_available()
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "flair": getattr(flair, "__version__", None),
        "torch": getattr(torch, "__version__", None),
        "transformers": _module_version("transformers"),
        "scispacy": _module_version("scispacy"),
        "requested_device": requested_device,
        "actual_device": str(getattr(flair, "device", requested_device)),
        "cuda_available": cuda,
        "cuda_device": torch.cuda.get_device_name(0) if cuda else None,
        "cuda_version": getattr(torch.version, "cuda", None),
    }


def _find_model_artifact(base_model: str) -> tuple[str | None, str | None]:
    """Return an existing local model file and its digest when base_model is a path."""

    path = Path(base_model)
    if not path.is_file():
        return None, None
    return str(path.resolve()), sha256_file(path)


def _assert_model_labels(model: Any) -> None:
    """Ensure the released head contains all flat labels used by target gold."""

    dictionary = getattr(model, "label_dictionary", None)
    if dictionary is None:
        raise TrainingCompatibilityError("Loaded HunFlair2 model has no label dictionary")
    labels = set(dictionary.get_items())
    missing = []
    for label in HUNFLAIR2_TRAINING_LABEL_BY_TYPE.values():
        if not any(
            candidate in labels
            for candidate in (label, f"S-{label}", f"B-{label}")
        ):
            missing.append(label)
    if missing:
        raise TrainingCompatibilityError(
            f"Loaded HunFlair2 head cannot represent labels: {missing}"
        )


def _gradient_norm(model: Any, torch: Any) -> Any:
    """Compute a finite global L2 gradient norm."""

    gradients = [
        parameter.grad.detach()
        for parameter in model.parameters()
        if parameter.grad is not None
    ]
    if not gradients:
        return torch.tensor(0.0, device=next(model.parameters()).device)
    return torch.sqrt(
        torch.stack([torch.sum(gradient.float() ** 2) for gradient in gradients]).sum()
    )


def _tiny_smoke_sentences() -> list[Any]:
    """Create a non-evaluative, token-aligned synthetic smoke fixture."""

    from flair.data import Sentence

    examples = [
        ("BRCA1 causes cancer.", ((0, 5, "Gene"), (13, 19, "Disease"))),
        ("TP53 in human cells.", ((0, 4, "Gene"), (8, 13, "Species"), (14, 19, "CellLine"))),
    ]
    sentences = []
    for text, entities in examples:
        sentence = Sentence(text, use_tokenizer=True)
        if sentence.to_original_text() != text:
            raise RuntimeError("Smoke fixture was changed by Flair tokenization")
        for start, end, label in entities:
            first, last = _token_span_for_char_offsets(sentence, start, end)
            sentence[first:last].add_label("ner", label)
        sentences.append(sentence)
    return sentences


def run_gpu_training_smoke(
    config: HunFlair2TrainingConfig,
    *,
    checkpoint_path: Path,
) -> dict[str, Any]:
    """Run one actual forward/backward/optimizer/checkpoint smoke step."""

    config.validate()
    _prepare_flair_environment(config.device)
    import torch
    import flair
    from flair.data import Sentence
    from flair.nn import Classifier

    _configure_flair_device(config.device, flair, torch)
    _seed_runtime(config.random_seed, torch)
    model = Classifier.load(config.base_model)
    _assert_model_labels(model)
    model.to(flair.device)
    model.train()
    sentences = _tiny_smoke_sentences()
    trainable_before = {
        name: parameter.detach().clone()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
    optimizer.zero_grad(set_to_none=True)
    loss, token_count = model.forward_loss(sentences[:1])
    finite_loss = bool(torch.isfinite(loss).item())
    if not finite_loss:
        raise RuntimeError(f"Smoke forward loss is not finite: {loss.item()}")
    loss.backward()
    norm = _gradient_norm(model, torch)
    finite_gradients = all(
        parameter.grad is None or bool(torch.isfinite(parameter.grad).all().item())
        for parameter in model.parameters()
    )
    non_zero_gradient = bool(torch.isfinite(norm).item() and norm.item() > 0.0)
    if not finite_gradients or not non_zero_gradient:
        raise RuntimeError(
            f"Smoke gradients failed: finite={finite_gradients}, norm={norm.item()}"
        )
    optimizer.step()
    changed_parameters = any(
        not torch.equal(trainable_before[name], parameter.detach())
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    )
    if not changed_parameters:
        raise RuntimeError("Smoke optimizer step did not change trainable parameters")

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(checkpoint_path)
    if not checkpoint_path.is_file() or checkpoint_path.stat().st_size == 0:
        raise RuntimeError("Smoke checkpoint was not written")
    reloaded = Classifier.load(checkpoint_path)
    reloaded.to(flair.device)
    reloaded.eval()
    inference_sentence = Sentence("BRCA1 causes cancer.", use_tokenizer=True)
    reloaded.predict([inference_sentence], mini_batch_size=1)
    if not isinstance(inference_sentence.get_spans("ner"), list):
        raise RuntimeError("Reloaded smoke checkpoint did not support inference")
    peak_memory = (
        torch.cuda.max_memory_allocated() / (1024 * 1024)
        if torch.cuda.is_available()
        else None
    )
    artifact_path, artifact_sha256 = _find_model_artifact(config.base_model)
    return {
        "schema_version": 1,
        "smoke_kind": "hunflair2_training_plumbing",
        "disposable": True,
        "model_selection_candidate": False,
        "config": config.to_dict(),
        "runtime": _runtime_metadata(flair, torch, requested_device=config.device),
        "base_model": {
            "identifier": config.base_model,
            "revision": config.base_model_revision,
            "configured_artifact_sha256": config.base_model_artifact_sha256,
            "local_artifact": artifact_path,
            "artifact_sha256": artifact_sha256,
        },
        "fixture": {
            "synthetic": True,
            "sentence_count": len(sentences),
            "evaluative_target_gold_used": False,
        },
        "forward": {
            "loss": float(loss.detach().cpu().item()),
            "token_count": int(token_count),
            "finite_loss": finite_loss,
        },
        "backward": {
            "finite_gradients": finite_gradients,
            "global_gradient_norm": float(norm.detach().cpu().item()),
            "non_zero_gradient": non_zero_gradient,
        },
        "optimizer": {"parameter_changed": changed_parameters},
        "checkpoint": {
            "path": str(checkpoint_path),
            "sha256": sha256_file(checkpoint_path),
            "reloaded": True,
            "inference_after_reload": True,
        },
        "peak_cuda_memory_mib": peak_memory,
    }


def run_target_training(
    config: HunFlair2TrainingConfig,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Fine-tune HunFlair2 on validated human gold using Flair's trainer."""

    config.validate()
    _prepare_flair_environment(config.device)
    training_splits = load_training_splits(config, root=root)
    import torch
    import flair
    from flair.nn import Classifier
    from flair.trainers import ModelTrainer

    _configure_flair_device(config.device, flair, torch)
    _seed_runtime(config.random_seed, torch)
    corpus = build_flair_corpus(training_splits)
    model = Classifier.load(config.base_model)
    _assert_model_labels(model)
    model.to(flair.device)
    checkpoint_location = _resolve_path(config.checkpoint_location, root=root)
    chunk_size = None
    if config.gradient_accumulation_steps > 1:
        chunk_size = max(1, config.mini_batch_size // config.gradient_accumulation_steps)
    trainer = ModelTrainer(model, corpus)
    result = trainer.fine_tune(
        base_path=checkpoint_location,
        learning_rate=config.learning_rate,
        mini_batch_size=config.mini_batch_size,
        mini_batch_chunk_size=chunk_size,
        max_epochs=config.max_epochs,
        train_with_dev=False,
        train_with_test=False,
        monitor_test=False,
        use_final_model_for_eval=False,
        save_final_model=True,
        save_optimizer_state=False,
        embeddings_storage_mode="none",
        use_amp=config.mixed_precision,
    )
    best_model = checkpoint_location / "best-model.pt"
    final_model = checkpoint_location / "final-model.pt"
    selected_model = best_model if best_model.is_file() else final_model
    if not selected_model.is_file():
        raise RuntimeError(
            "Flair training completed without a best-model.pt or final-model.pt"
        )
    output_model = _resolve_path(config.output_model_location, root=root)
    output_model.parent.mkdir(parents=True, exist_ok=True)
    if output_model != selected_model:
        shutil.copy2(selected_model, output_model)
    return {
        "schema_version": 1,
        "training_kind": "hunflair2_target_domain_finetune",
        "config": config.to_dict(),
        "runtime": _runtime_metadata(flair, torch, requested_device=config.device),
        "training_manifests": training_splits["paths"],
        "paper_ids": training_splits["paper_ids"],
        "example_counts": training_splits["example_counts"],
        "test_evaluation": result,
        "test_used_for_training": False,
        "checkpoint_location": str(checkpoint_location),
        "selected_model": {
            "source": str(selected_model),
            "output": str(output_model),
            "sha256": sha256_file(output_model),
            "selected_from_dev": best_model.is_file(),
        },
    }


__all__ = [
    "HunFlair2TrainingConfig",
    "build_flair_corpus",
    "load_training_config",
    "load_training_splits",
    "run_gpu_training_smoke",
    "run_target_training",
]
