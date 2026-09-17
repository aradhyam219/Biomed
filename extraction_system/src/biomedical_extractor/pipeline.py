"""Run the production biomedical entity-to-relation extraction pipeline.

The entity stage exposes normalized character-span entities through the local
``EntityExtractor`` contract. The relation handoff tokenizes the original text at
every entity boundary, converts each entity to GLiREL's inclusive token-span input,
and remembers the corresponding half-open token span. GLiREL predictions use those
half-open token spans, which are resolved back to the stable entity IDs exposed in
:class:`ExtractionResult`.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol, Sequence

from .entity_extraction import (
    DEFAULT_ENTITY_LABELS,
    DEFAULT_ENTITY_MODEL,
    Entity,
    EntityExtractor,
    GLiNERBioMedExtractor,
)

DEFAULT_RELATION_MODEL = "jackboyla/glirel-large-v0"

DEFAULT_RELATION_LABELS = (
    "association",
    "positive correlation",
    "negative correlation",
    "binds",
    "interacts with",
    "treats",
    "causes",
)

_GLIREL_TOKEN_PATTERN = re.compile(r"\w+(?:[-_]\w+)*|\S")


class RelationModel(Protocol):
    """Supplied-entity relation-model interface required by the pipeline."""

    def predict_relations(
        self,
        text: Sequence[str],
        labels: Sequence[str],
        *,
        threshold: float,
        ner: Sequence[Sequence[Any]],
        flat_ner: bool,
        top_k: int,
    ) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ExtractionConfig:
    """Model identifiers, schemas, thresholds, and device for one extractor."""

    entity_labels: tuple[str, ...] = DEFAULT_ENTITY_LABELS
    relation_labels: tuple[str, ...] = DEFAULT_RELATION_LABELS
    entity_threshold: float = 0.5
    relation_threshold: float = 0.5
    relation_top_k: int = -1
    entity_model: str = DEFAULT_ENTITY_MODEL
    relation_model: str = DEFAULT_RELATION_MODEL
    device: str | None = None

    def __post_init__(self) -> None:
        if not self.entity_labels or not self.relation_labels:
            raise ValueError("Entity and relation label sets must not be empty")
        if len(set(self.entity_labels)) != len(self.entity_labels):
            raise ValueError("Entity labels must be unique")
        if len(set(self.relation_labels)) != len(self.relation_labels):
            raise ValueError("Relation labels must be unique")
        for name, value in (
            ("entity_threshold", self.entity_threshold),
            ("relation_threshold", self.relation_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.relation_top_k == 0 or self.relation_top_k < -1:
            raise ValueError("relation_top_k must be -1 or a positive integer")


@dataclass(frozen=True)
class Relation:
    """Normalized directed relation whose endpoints are entity IDs."""

    source: str
    target: str
    type: str
    score: float | None


@dataclass(frozen=True)
class ExtractionResult:
    """Immutable normalized output from a complete extraction pass."""

    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Return a JSON-serializable entity/relation mapping."""

        return {
            "entities": [asdict(entity) for entity in self.entities],
            "relations": [asdict(relation) for relation in self.relations],
        }


@dataclass(frozen=True)
class _Token:
    """One GLiREL input token with half-open source-character offsets."""

    text: str
    start: int
    end: int


class BiomedicalExtractor:
    """Coordinate entity extraction, supplied-entity relations, and normalization.

    The entity stage depends on the local :class:`EntityExtractor` contract;
    GLiREL's token-span representation remains internal to the relation handoff.
    """

    def __init__(
        self,
        entity_extractor: EntityExtractor,
        relation_model: RelationModel,
        config: ExtractionConfig | None = None,
    ) -> None:
        """Bind already loaded model objects to a validated extraction config."""

        self.entity_extractor = entity_extractor
        self.relation_model = relation_model
        self.config = config or ExtractionConfig()

    @classmethod
    def from_pretrained(
        cls, config: ExtractionConfig | None = None
    ) -> BiomedicalExtractor:
        """Load the configured entity and relation checkpoints on the selected device."""

        from glirel import GLiREL
        import torch

        config = config or ExtractionConfig()
        device = config.device or ("cuda" if torch.cuda.is_available() else "cpu")
        entity_extractor = GLiNERBioMedExtractor.from_pretrained(
            model_name=config.entity_model,
            labels=config.entity_labels,
            threshold=config.entity_threshold,
            device=device,
        )
        relation_model = GLiREL.from_pretrained(
            config.relation_model, map_location=device
        )
        relation_model.eval()
        return cls(entity_extractor, relation_model, config)

    def extract(self, text: str) -> ExtractionResult:
        """Extract normalized entities and relations from ordinary biomedical text."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            return ExtractionResult(entities=(), relations=())

        entities = self.extract_entities(text)
        relations = self.extract_relations(text, entities)
        return ExtractionResult(entities=entities, relations=relations)

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Run the configured entity extractor on the supplied text."""

        return self.entity_extractor.extract_entities(text)

    def extract_relations(
        self, text: str, entities: Sequence[Entity]
    ) -> tuple[Relation, ...]:
        """Run GLiREL with supplied entities and return entity-ID relations.

        Entity offsets remain half-open character spans at this API boundary. They
        are converted internally to GLiREL's inclusive token-span NER input and
        resolved from GLiREL's half-open prediction spans back to the same IDs.
        """

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if len(entities) < 2:
            return ()
        unknown_types = {entity.type for entity in entities} - set(
            self.config.entity_labels
        )
        if unknown_types:
            raise ValueError(
                f"Entity types are outside the configured schema: {sorted(unknown_types)}"
            )

        # Supplied annotations can name a substring of a hyphenated or otherwise
        # compound token. Splitting only at their exact character boundaries keeps
        # the gold mention unchanged and gives GLiREL a representable token span.
        entity_boundaries = {
            boundary
            for entity in entities
            for boundary in (entity.start, entity.end)
        }
        tokens = _tokenize(text, entity_boundaries)
        relation_ner, entity_ids_by_span = _to_glirel_entities(
            text, tokens, entities
        )
        raw_relations = self.relation_model.predict_relations(
            [token.text for token in tokens],
            self.config.relation_labels,
            threshold=self.config.relation_threshold,
            ner=relation_ner,
            flat_ner=True,
            top_k=self.config.relation_top_k,
        )
        return self._normalize_relations(raw_relations, entity_ids_by_span)

    def _normalize_relations(
        self,
        predictions: Sequence[dict[str, Any]],
        entity_ids_by_span: dict[tuple[int, int], str],
    ) -> tuple[Relation, ...]:
        relations: list[Relation] = []
        for prediction in predictions:
            relation_type = str(prediction["label"])
            if relation_type not in self.config.relation_labels:
                raise ValueError(
                    f"Relation label {relation_type!r} is outside the configured schema"
                )
            head_span = _relation_span(prediction, "head_pos")
            tail_span = _relation_span(prediction, "tail_pos")
            try:
                source = entity_ids_by_span[head_span]
                target = entity_ids_by_span[tail_span]
            except KeyError as error:
                raise ValueError(
                    f"Relation references unknown GLiREL entity span {error.args[0]}"
                ) from error
            raw_score = prediction.get("score")
            relations.append(
                Relation(
                    source=source,
                    target=target,
                    type=relation_type,
                    score=float(raw_score) if raw_score is not None else None,
                )
            )
        return tuple(relations)


def _tokenize(
    text: str, required_boundaries: set[int] | None = None
) -> tuple[_Token, ...]:
    """Tokenize text while preserving any supplied entity character boundaries.

    GLiREL's regular expression normally joins hyphenated words. BioRED can annotate
    a substring of such a token (and occasionally a prefix such as ``H3`` in
    ``H3K36me3``). ``required_boundaries`` therefore splits matching tokens without
    changing or widening the original half-open entity character spans.
    """

    boundaries = required_boundaries or set()
    tokens: list[_Token] = []
    for match in _GLIREL_TOKEN_PATTERN.finditer(text):
        cuts = [
            match.start(),
            *sorted(
                boundary
                for boundary in boundaries
                if match.start() < boundary < match.end()
            ),
            match.end(),
        ]
        tokens.extend(
            _Token(text[start:end], start, end)
            for start, end in zip(cuts, cuts[1:])
        )
    return tuple(tokens)


def _to_glirel_entities(
    text: str, tokens: Sequence[_Token], entities: Sequence[Entity]
) -> tuple[list[list[Any]], dict[tuple[int, int], str]]:
    """Convert character-span entities to GLiREL spans and an ID lookup.

    ``relation_ner`` uses GLiREL's inclusive ``[start_token, end_token]`` input.
    ``entity_ids_by_span`` uses half-open ``(start_token, end_token)`` keys because
    that is how GLiREL reports relation endpoints.
    """

    starts = {token.start: index for index, token in enumerate(tokens)}
    ends = {token.end: index for index, token in enumerate(tokens)}
    relation_ner: list[list[Any]] = []
    entity_ids_by_span: dict[tuple[int, int], str] = {}
    seen_entity_ids: set[str] = set()

    for entity in entities:
        if not entity.id or entity.id in seen_entity_ids:
            raise ValueError(f"Entity ID must be non-empty and unique: {entity.id!r}")
        seen_entity_ids.add(entity.id)
        if entity.start not in starts or entity.end not in ends:
            raise ValueError(
                f"Entity {entity.id} span [{entity.start}, {entity.end}) does not align "
                "with GLiREL token boundaries"
            )
        start_token = starts[entity.start]
        end_token_inclusive = ends[entity.end]
        if start_token > end_token_inclusive:
            raise ValueError(f"Entity {entity.id} resolves to an invalid token span")
        # One endpoint lookup bridges GLiREL's inclusive NER input and half-open
        # relation output without changing the normalized entity identity.
        token_span = (start_token, end_token_inclusive + 1)
        if token_span in entity_ids_by_span:
            raise ValueError(f"Multiple entities resolve to GLiREL token span {token_span}")
        if text[entity.start : entity.end] != entity.text:
            raise ValueError(f"Entity {entity.id} no longer resolves to its source text")

        relation_ner.append(
            [start_token, end_token_inclusive, entity.type, entity.text]
        )
        entity_ids_by_span[token_span] = entity.id

    return relation_ner, entity_ids_by_span


def _relation_span(prediction: dict[str, Any], key: str) -> tuple[int, int]:
    """Validate and normalize one half-open GLiREL prediction endpoint."""

    raw_span = prediction[key]
    if not isinstance(raw_span, (list, tuple)) or len(raw_span) != 2:
        raise ValueError(f"Invalid GLiREL {key}: {raw_span!r}")
    return int(raw_span[0]), int(raw_span[1])
