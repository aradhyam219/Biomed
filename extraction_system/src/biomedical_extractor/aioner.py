"""Evaluation-only adapter for the official AIONER output contract.

The released AIONER runtime is intentionally not imported by the production
package.  It depends on a legacy TensorFlow/Transformers stack, so an isolated
runner can expose its raw ``(start, end, label)`` predictions to this module.
This adapter validates those predictions against the original source text and
returns the repository's model-independent :class:`Entity` values.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .entity_extraction import Entity, EntityExtractor


AIONER_LABEL_TO_CANONICAL: Mapping[str, str] = {
    "Gene": "GeneOrGeneProduct",
    "Disease": "DiseaseOrPhenotypicFeature",
    "Chemical": "ChemicalEntity",
    "Species": "OrganismTaxon",
    "CellLine": "CellLine",
    "Variant": "SequenceVariant",
}
AIONER_SUPPORTED_CANONICAL_TYPES = tuple(sorted(set(AIONER_LABEL_TO_CANONICAL.values())))


@dataclass(frozen=True)
class AIONERRawPrediction:
    """One official AIONER-style prediction before source-span validation."""

    start: int
    end: int
    label: str
    text: str | None = None
    score: float | None = None


class AIONERRuntime(Protocol):
    """Minimal raw prediction surface exposed by an isolated AIONER runner."""

    def predict_entities(self, text: str) -> Sequence[object]:
        """Return raw AIONER predictions for one source string."""


class AIONERBioMedExtractor:
    """Adapt official AIONER predictions to the stable local entity contract."""

    def __init__(self, runtime: AIONERRuntime) -> None:
        self._runtime = runtime

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Run the supplied isolated runtime and validate every source span."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            return ()
        predictions = self._runtime.predict_entities(text)
        return normalize_aioner_predictions(text, predictions)


class AIONERPredictionRuntime:
    """Serve cached official predictions keyed by source-text SHA-256.

    This is used by the evaluation CLI after the isolated upstream runner has
    written its PubTator output.  A digest key keeps the EntityExtractor surface
    text-only while rejecting missing or ambiguous document predictions.
    """

    def __init__(
        self,
        predictions_by_text_sha256: Mapping[str, Sequence[object]],
    ) -> None:
        self._predictions = {
            str(key): tuple(value)
            for key, value in predictions_by_text_sha256.items()
        }

    def predict_entities(self, text: str) -> Sequence[object]:
        """Return cached predictions for exactly one known source text."""

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        try:
            return self._predictions[digest]
        except KeyError as error:
            raise ValueError(
                "AIONER prediction cache has no entry for the supplied source text"
            ) from error


def normalize_aioner_predictions(
    source_text: str,
    predictions: Sequence[object],
) -> tuple[Entity, ...]:
    """Convert and validate raw AIONER predictions without inventing scores.

    The official runner emits three-item sequences ``[start, end, label]``.  A
    mapping form is also accepted for deterministic tests and cached integrations;
    its optional ``text`` and ``score`` fields are validated/preserved when
    present.  Unknown labels and corrupt offsets fail closed.
    """

    entities: list[Entity] = []
    for index, prediction in enumerate(predictions, start=1):
        raw = _coerce_raw_prediction(prediction)
        if raw.label not in AIONER_LABEL_TO_CANONICAL:
            raise ValueError(f"Unsupported AIONER entity label: {raw.label!r}")
        if not 0 <= raw.start < raw.end <= len(source_text):
            raise ValueError(
                f"Invalid AIONER entity character span: [{raw.start}, {raw.end})"
            )
        source_slice = source_text[raw.start : raw.end]
        if raw.text is not None and raw.text != source_slice:
            raise ValueError(
                f"AIONER span [{raw.start}, {raw.end}) does not resolve to "
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


def _coerce_raw_prediction(prediction: object) -> AIONERRawPrediction:
    """Normalize mapping or official three-item sequence representations."""

    if isinstance(prediction, AIONERRawPrediction):
        return prediction
    if isinstance(prediction, Mapping):
        try:
            label = prediction["label"] if "label" in prediction else prediction["type"]
            start = prediction["start"]
            end = prediction["end"]
        except KeyError as error:
            raise ValueError(
                "AIONER prediction mapping requires start, end, and label/type"
            ) from error
        raw_score = prediction.get("score")
        score = None if raw_score is None else float(raw_score)
        raw_text = prediction.get("text")
        return AIONERRawPrediction(
            int(start),
            int(end),
            str(label),
            None if raw_text is None else str(raw_text),
            score,
        )
    if isinstance(prediction, (str, bytes)):
        raise TypeError("AIONER predictions must not be strings")
    try:
        values = tuple(prediction)  # type: ignore[arg-type]
    except TypeError as error:
        raise TypeError(
            "AIONER predictions must be mappings, AIONERRawPrediction values, "
            "or three-item sequences"
        ) from error
    if len(values) != 3:
        raise ValueError(
            "Official AIONER sequence predictions must contain start, end, label"
        )
    return AIONERRawPrediction(int(values[0]), int(values[1]), str(values[2]))


__all__ = [
    "AIONERBioMedExtractor",
    "AIONER_LABEL_TO_CANONICAL",
    "AIONERPredictionRuntime",
    "AIONERRawPrediction",
    "AIONER_SUPPORTED_CANONICAL_TYPES",
    "normalize_aioner_predictions",
]
