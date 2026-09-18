"""Evaluation-only adapter for the official HunFlair2 biomedical NER model.

The Flair runtime is intentionally not imported by this module.  The isolated
evaluation runner converts Flair spans into plain prediction mappings before
they cross into this adapter, keeping the production dependency graph and the
``EntityExtractor`` boundary model-independent.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .entity_extraction import Entity, EntityExtractor


HUNFLAIR2_MODEL_IDENTIFIER = "hunflair/hunflair2-ner"
HUNFLAIR2_OFFICIAL_REPOSITORY = "https://github.com/flairNLP/flair"
HUNFLAIR2_LABEL_TO_CANONICAL: Mapping[str, str] = {
    "Gene": "GeneOrGeneProduct",
    "Chemical": "ChemicalEntity",
    "Disease": "DiseaseOrPhenotypicFeature",
    "Species": "OrganismTaxon",
    "CellLine": "CellLine",
}
HUNFLAIR2_SUPPORTED_CANONICAL_TYPES = tuple(
    sorted(set(HUNFLAIR2_LABEL_TO_CANONICAL.values()))
)


@dataclass(frozen=True)
class HunFlair2RawPrediction:
    """One HunFlair2 span after conversion from a Flair-like object."""

    start: int
    end: int
    label: str
    text: str | None = None
    score: float | None = None


class HunFlair2Runtime(Protocol):
    """Minimal raw prediction surface exposed by the isolated runner."""

    def predict_entities(self, text: str) -> Sequence[object]:
        """Return document-relative HunFlair2 predictions for one source text."""


class HunFlair2BioMedExtractor:
    """Adapt official HunFlair2 predictions to normalized local entities."""

    def __init__(self, runtime: HunFlair2Runtime) -> None:
        self._runtime = runtime

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Run the isolated runtime and validate every source-relative span."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            return ()
        predictions = self._runtime.predict_entities(text)
        return normalize_hunflair2_predictions(text, predictions)


class HunFlair2PredictionRuntime:
    """Serve cached runner predictions keyed by exact source-text SHA-256."""

    def __init__(
        self,
        predictions_by_text_sha256: Mapping[str, Sequence[object]],
    ) -> None:
        self._predictions = {
            str(key): tuple(value)
            for key, value in predictions_by_text_sha256.items()
        }

    def predict_entities(self, text: str) -> Sequence[object]:
        """Return predictions only for a source text present in the cache."""

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        try:
            return self._predictions[digest]
        except KeyError as error:
            raise ValueError(
                "HunFlair2 prediction cache has no entry for the supplied source text"
            ) from error


def normalize_hunflair2_predictions(
    source_text: str,
    predictions: Sequence[object],
) -> tuple[Entity, ...]:
    """Convert Flair-like predictions without changing text or confidence.

    The adapter accepts plain mappings/sequences for cached runner output and a
    deliberately small structural interface for deterministic fake Flair spans.
    Actual Flair objects are inspected only here; none are returned downstream.
    """

    entities: list[Entity] = []
    for index, prediction in enumerate(predictions, start=1):
        raw = _coerce_raw_prediction(prediction)
        if raw.label not in HUNFLAIR2_LABEL_TO_CANONICAL:
            raise ValueError(f"Unsupported HunFlair2 entity label: {raw.label!r}")
        if not 0 <= raw.start < raw.end <= len(source_text):
            raise ValueError(
                f"Invalid HunFlair2 entity character span: [{raw.start}, {raw.end})"
            )
        source_slice = source_text[raw.start : raw.end]
        if raw.text is not None and raw.text != source_slice:
            raise ValueError(
                f"HunFlair2 span [{raw.start}, {raw.end}) does not resolve to "
                f"{raw.text!r}"
            )
        entities.append(
            Entity(
                id=f"E{index}",
                text=source_slice,
                type=raw.label,
                start=raw.start,
                end=raw.end,
                score=raw.score,
            )
        )
    return tuple(entities)


def _coerce_raw_prediction(prediction: object) -> HunFlair2RawPrediction:
    """Extract plain fields from cached values or a Flair-like span object."""

    if isinstance(prediction, HunFlair2RawPrediction):
        return prediction
    if isinstance(prediction, Mapping):
        return _coerce_mapping_prediction(prediction)
    if isinstance(prediction, (str, bytes)):
        raise TypeError("HunFlair2 predictions must not be strings")

    if all(hasattr(prediction, attribute) for attribute in ("start_position", "end_position")):
        start = int(getattr(prediction, "start_position"))
        end = int(getattr(prediction, "end_position"))
        raw_text = getattr(prediction, "text", None)
        label, score = _read_structured_label(prediction)
        if label is None:
            raise ValueError("Flair-like HunFlair2 span has no NER label")
        return HunFlair2RawPrediction(
            start,
            end,
            label,
            None if raw_text is None else str(raw_text),
            score,
        )

    try:
        values = tuple(prediction)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(
            "HunFlair2 predictions must be mappings, HunFlair2RawPrediction "
            "values, Flair-like spans, or three/four-item sequences"
        ) from error
    if len(values) not in (3, 4):
        raise ValueError(
            "HunFlair2 sequence predictions must contain start, end, label, "
            "and optionally score"
        )
    score = None if len(values) == 3 or values[3] is None else float(values[3])
    return HunFlair2RawPrediction(int(values[0]), int(values[1]), str(values[2]), score=score)


def _coerce_mapping_prediction(
    prediction: Mapping[str, Any],
) -> HunFlair2RawPrediction:
    """Read the plain cache form or Flair's ``Span.to_dict`` shape."""

    try:
        start = prediction["start"] if "start" in prediction else prediction["start_pos"]
        end = prediction["end"] if "end" in prediction else prediction["end_pos"]
    except KeyError as error:
        raise ValueError(
            "HunFlair2 prediction mapping requires start/end or start_pos/end_pos"
        ) from error

    label = prediction.get("label", prediction.get("type"))
    score = prediction.get("score", prediction.get("confidence"))
    if label is None:
        labels = prediction.get("labels")
        if isinstance(labels, Sequence) and not isinstance(labels, (str, bytes)) and labels:
            first_label = labels[0]
            if isinstance(first_label, Mapping):
                label = first_label.get("value", first_label.get("label"))
                score = first_label.get("confidence", first_label.get("score", score))
    if label is None:
        raise ValueError("HunFlair2 prediction mapping requires a label/type")
    return HunFlair2RawPrediction(
        int(start),
        int(end),
        str(label),
        None if prediction.get("text") is None else str(prediction["text"]),
        None if score is None else float(score),
    )


def _read_structured_label(prediction: object) -> tuple[str | None, float | None]:
    """Read one Flair ``Span`` label without importing Flair types."""

    label_object: object | None = None
    get_label = getattr(prediction, "get_label", None)
    if callable(get_label):
        try:
            label_object = get_label("ner")
        except TypeError:
            label_object = get_label()
    if label_object is None:
        labels = getattr(prediction, "labels", None)
        if isinstance(labels, Sequence) and labels:
            label_object = labels[0]
    if label_object is None:
        label_object = getattr(prediction, "label", None)
    if label_object is None:
        return None, None

    value = getattr(label_object, "value", label_object)
    score = getattr(label_object, "score", None)
    return str(value), None if score is None else float(score)


__all__ = [
    "HUNFLAIR2_LABEL_TO_CANONICAL",
    "HUNFLAIR2_MODEL_IDENTIFIER",
    "HUNFLAIR2_OFFICIAL_REPOSITORY",
    "HUNFLAIR2_SUPPORTED_CANONICAL_TYPES",
    "HunFlair2BioMedExtractor",
    "HunFlair2PredictionRuntime",
    "HunFlair2RawPrediction",
    "normalize_hunflair2_predictions",
]
