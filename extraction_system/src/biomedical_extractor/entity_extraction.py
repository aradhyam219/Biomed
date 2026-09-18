"""Stable entity-extraction contract and the GLiNER-BioMed adapter.

The public entity boundary uses normalized character spans and does not expose
GLiNER prediction dictionaries. Model loading and conversion stay in
``GLiNERBioMedExtractor`` so another entity model can implement the same
``EntityExtractor`` protocol without changing downstream code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol, Sequence

DEFAULT_ENTITY_MODEL = "Ihor/gliner-biomed-base-v1.0"
DEFAULT_ENTITY_LABELS = (
    "gene",
    "disease",
    "chemical",
    "species",
    "cell line",
    "DNA",
    "RNA",
)
DEFAULT_CORE_ENTITY_LABELS = (
    "gene",
    "protein",
    "disease",
    "chemical",
    "species",
    "cell line",
    "DNA",
    "RNA",
)
DEFAULT_PROCESS_ENTITY_LABELS = ("biological process",)
DEFAULT_ENTITY_LABEL_PASSES = (
    DEFAULT_CORE_ENTITY_LABELS,
    DEFAULT_PROCESS_ENTITY_LABELS,
)


class EntityExtractor(Protocol):
    """Small contract for extracting normalized entities from source text."""

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Return entities whose offsets refer to the supplied text."""


@dataclass(frozen=True)
class Entity:
    """Normalized entity with a stable ID and half-open character offsets."""

    id: str
    text: str
    type: str
    start: int
    end: int
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the machine-consumable entity representation."""

        return asdict(self)


class _GLiNERModel(Protocol):
    """Raw model surface used only inside the GLiNER adapter."""

    def predict_entities(
        self, text: str, labels: Sequence[str], *, threshold: float
    ) -> Sequence[Mapping[str, Any]]: ...


class GLiNERBioMedExtractor:
    """Adapt GLiNER-BioMed predictions to the stable entity contract."""

    def __init__(
        self,
        model: _GLiNERModel,
        labels: Sequence[str] | None = None,
        threshold: float = 0.5,
    ) -> None:
        self._model = model
        self._label_passes = _resolve_label_passes(labels)
        self._threshold = threshold
        for label_pass in self._label_passes:
            _validate_labels(label_pass)
        _validate_threshold(threshold)

    @classmethod
    def from_pretrained(
        cls,
        model_name: str = DEFAULT_ENTITY_MODEL,
        labels: Sequence[str] | None = None,
        threshold: float = 0.5,
        device: str | None = None,
    ) -> GLiNERBioMedExtractor:
        """Load one GLiNER-BioMed model for the configured label passes."""

        from gliner import GLiNER
        import torch

        selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        model = GLiNER.from_pretrained(model_name, map_location=selected_device)
        model.eval()
        return cls(model, labels, threshold)

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Run GLiNER and normalize predictions against the original text."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            return ()

        entities: list[Entity] = []
        for labels in self._label_passes:
            predictions = self._model.predict_entities(
                text, labels, threshold=self._threshold
            )
            entities.extend(_normalize_predictions(text, predictions, labels))
        return _merge_entities(entities)


def _resolve_label_passes(
    labels: Sequence[str] | None,
) -> tuple[tuple[str, ...], ...]:
    """Resolve omitted labels to the default core-plus-process passes."""

    if labels is None:
        return DEFAULT_ENTITY_LABEL_PASSES
    return (tuple(labels),)


def _validate_labels(labels: Sequence[str]) -> None:
    """Validate the finite label schema used for one entity extractor."""

    if not labels or any(not isinstance(label, str) or not label for label in labels):
        raise ValueError("Entity labels must contain non-empty strings")
    if len(set(labels)) != len(labels):
        raise ValueError("Entity labels must be unique")


def _validate_threshold(threshold: float) -> None:
    """Validate the confidence threshold before model inference."""

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Entity threshold must be between 0 and 1")


def _normalize_predictions(
    text: str,
    predictions: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
) -> tuple[Entity, ...]:
    """Convert raw GLiNER dictionaries into validated normalized entities."""

    configured_labels = set(labels)
    entities: list[Entity] = []
    for index, prediction in enumerate(predictions, start=1):
        start = int(prediction["start"])
        end = int(prediction["end"])
        predicted_text = str(prediction["text"])
        label = str(prediction["label"])
        if not 0 <= start < end <= len(text):
            raise ValueError(f"Invalid entity character span: [{start}, {end})")
        if text[start:end] != predicted_text:
            raise ValueError(
                f"Entity span [{start}, {end}) does not resolve to {predicted_text!r}"
            )
        if label not in configured_labels:
            raise ValueError(f"Entity label {label!r} is outside the configured schema")
        raw_score = prediction.get("score")
        entities.append(
            Entity(
                id=f"E{index}",
                text=predicted_text,
                type=label,
                start=start,
                end=end,
                score=float(raw_score) if raw_score is not None else None,
            )
        )
    return tuple(entities)


def _merge_entities(entities: Sequence[Entity]) -> tuple[Entity, ...]:
    """Deduplicate, order, and reassign IDs for merged model detections."""

    unique: dict[tuple[int, int, str, str], Entity] = {}
    for entity in entities:
        key = (entity.start, entity.end, entity.type, entity.text)
        # The first pass occurrence is deterministic and its model score is kept
        # without synthesizing or reconciling a new confidence value.
        unique.setdefault(key, entity)

    ordered = sorted(
        unique.values(),
        key=lambda entity: (entity.start, entity.end, entity.type, entity.text),
    )
    return tuple(
        Entity(
            id=f"E{index}",
            text=entity.text,
            type=entity.type,
            start=entity.start,
            end=entity.end,
            score=entity.score,
        )
        for index, entity in enumerate(ordered, start=1)
    )
