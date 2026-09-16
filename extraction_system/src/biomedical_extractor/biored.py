"""BioRED parsing and concept-level relation scoring for gold-entity evaluation.

The official NCBI BioC JSON provides document passages, exact character-offset
mentions, normalized concept identifiers, and document-level relations. This module
keeps those dataset concerns outside the production extractor, adapts mention-level
GLiREL scores to BioRED's non-directional concept-level unit, and computes the V0-B
metrics without loading either model.

BioRED format and task semantics:
https://github.com/ncbi/BioRED
https://pmc.ncbi.nlm.nih.gov/articles/PMC9487702/
https://academic.oup.com/database/article/doi/10.1093/database/baae071/7731176
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from biomedical_extractor.pipeline import Entity, Relation


BIORED_RELATION_LABELS = (
    "Association",
    "Positive_Correlation",
    "Negative_Correlation",
    "Bind",
    "Conversion",
    "Drug_Interaction",
    "Comparison",
    "Cotreatment",
)

# Human-readable prompts are explicit so score labels can always be mapped back to
# the canonical spelling serialized by the official BioRED corpus.
CANONICAL_TO_PROMPT = {
    "Association": "association",
    "Positive_Correlation": "positive correlation",
    "Negative_Correlation": "negative correlation",
    "Bind": "bind",
    "Conversion": "conversion",
    "Drug_Interaction": "drug interaction",
    "Comparison": "comparison",
    "Cotreatment": "cotreatment",
}
PROMPT_TO_CANONICAL = {prompt: label for label, prompt in CANONICAL_TO_PROMPT.items()}

BIOC_TO_ENTITY_TYPE = {
    "DiseaseOrPhenotypicFeature": "Disease",
    "GeneOrGeneProduct": "Gene",
    "ChemicalEntity": "Chemical",
    "SequenceVariant": "Variant",
    "OrganismTaxon": "Species",
    "CellLine": "CellLine",
}
RELATION_ENTITY_TYPES = frozenset({"Disease", "Gene", "Chemical", "Variant"})
BIORED_SPLIT_FILENAMES = {
    "train": "Train.BioC.JSON",
    "dev": "Dev.BioC.JSON",
    "test": "Test.BioC.JSON",
}
ALLOWED_PAIR_FAMILIES = frozenset(
    {
        frozenset({"Disease", "Gene"}),
        frozenset({"Chemical", "Gene"}),
        frozenset({"Disease", "Variant"}),
        frozenset({"Gene"}),
        frozenset({"Chemical", "Disease"}),
        frozenset({"Chemical"}),
        frozenset({"Chemical", "Variant"}),
        frozenset({"Variant"}),
    }
)


@dataclass(frozen=True)
class BioREDMention:
    """One BioC annotation with half-open offsets and all normalized concept IDs."""

    id: str
    text: str
    type: str
    start: int
    end: int
    concept_ids: tuple[str, ...]

    def to_entity(self) -> Entity:
        """Create the V0-A supplied-entity value without invoking GLiNER."""

        return Entity(self.id, self.text, self.type, self.start, self.end, None)


@dataclass(frozen=True, order=True)
class TypedRelation:
    """A non-directional document-level concept pair and canonical relation type."""

    document_id: str
    concept_a: str
    concept_b: str
    relation_type: str


@dataclass(frozen=True)
class ScoredRelation:
    """A concept-level candidate whose score is max mention-pair evidence."""

    document_id: str
    concept_a: str
    concept_b: str
    relation_type: str
    score: float

    @property
    def typed(self) -> TypedRelation:
        return TypedRelation(
            self.document_id,
            self.concept_a,
            self.concept_b,
            self.relation_type,
        )


@dataclass(frozen=True)
class BioREDDocument:
    """Reconstructed BioRED document with gold mentions and concept relations."""

    id: str
    text: str
    mentions: tuple[BioREDMention, ...]
    relations: tuple[TypedRelation, ...]

    def relation_mentions(self) -> tuple[BioREDMention, ...]:
        """Return only mention types participating in V0-B candidate families."""

        return tuple(
            mention for mention in self.mentions if mention.type in RELATION_ENTITY_TYPES
        )


@dataclass(frozen=True)
class BioREDDataset:
    """Official BioC JSON identity plus parsed documents for one split."""

    path: Path
    split: str
    sha256: str
    source: str
    date: str
    key: str
    documents: tuple[BioREDDocument, ...]


def canonical_pair(concept_a: str, concept_b: str) -> tuple[str, str]:
    """Return BioRED's deterministic non-directional concept-pair ordering."""

    if not concept_a or not concept_b:
        raise ValueError("Concept identifiers must be non-empty")
    return tuple(sorted((concept_a, concept_b)))  # type: ignore[return-value]


def split_concept_ids(raw_identifier: str) -> tuple[str, ...]:
    """Expand a comma-delimited BioRED identifier without consulting relations.

    The official development BioC JSON serializes ambiguous/multi-concept mention
    identifiers as comma-separated values. Every identifier is retained, stripped,
    and deduplicated in source order; a predicted mention pair later expands to the
    Cartesian product of both endpoint ID sets.
    """

    identifiers = tuple(dict.fromkeys(part.strip() for part in raw_identifier.split(",")))
    if not identifiers or any(not identifier for identifier in identifiers):
        raise ValueError(f"Invalid BioRED identifier: {raw_identifier!r}")
    return identifiers


def resolve_biored_path(dataset_path: str | Path, split: str = "dev") -> Path:
    """Resolve an official BioC JSON file or directory for one split.

    V0-B continues to call this function with ``split="dev"``. Train and test
    support exists for the isolated V1 experiment data path; it does not change
    the production extraction path or the V0-B evaluation protocol.
    """

    normalized_split = split.lower()
    try:
        filename = BIORED_SPLIT_FILENAMES[normalized_split]
    except KeyError as error:
        raise ValueError(
            f"BioRED split must be one of {tuple(BIORED_SPLIT_FILENAMES)}"
        ) from error
    path = Path(dataset_path).expanduser().resolve()
    if path.is_dir():
        candidates = (path / filename, path / "BioRED" / filename)
        path = next((candidate for candidate in candidates if candidate.is_file()), path)
    if not path.is_file():
        raise FileNotFoundError(f"BioRED {normalized_split} BioC JSON not found: {path}")
    if path.name.casefold() != filename.casefold():
        raise ValueError(
            f"BioRED {normalized_split} dataset file must be the official {filename} split"
        )
    return path


def load_biored(dataset_path: str | Path, split: str = "dev") -> BioREDDataset:
    """Parse official BioRED BioC JSON with exact passage offsets and gold IDs.

    Passage offsets are document-relative. Gaps between title and abstract are filled
    with spaces so every annotation's BioC half-open ``[offset, offset + length)``
    bounds continue to select its original mention text.
    """

    path = resolve_biored_path(dataset_path, split)
    raw_bytes = path.read_bytes()
    root = json.loads(raw_bytes)
    documents = tuple(_parse_document(document) for document in root["documents"])
    if len({document.id for document in documents}) != len(documents):
        raise ValueError("BioRED document IDs must be unique")
    return BioREDDataset(
        path=path,
        split=split.lower(),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        source=str(root.get("source", "")),
        date=str(root.get("date", "")),
        key=str(root.get("key", "")),
        documents=documents,
    )


def _parse_document(raw: Mapping[str, Any]) -> BioREDDocument:
    document_id = str(raw["id"])
    passages = sorted(raw["passages"], key=lambda passage: int(passage["offset"]))
    if not passages:
        raise ValueError(f"BioRED document {document_id} has no passages")
    text_end = max(int(passage["offset"]) + len(passage["text"]) for passage in passages)
    text_chars = [" "] * text_end
    mentions: list[BioREDMention] = []
    seen_mention_ids: set[str] = set()

    for passage in passages:
        passage_start = int(passage["offset"])
        passage_text = str(passage["text"])
        passage_end = passage_start + len(passage_text)
        if any(character != " " for character in text_chars[passage_start:passage_end]):
            raise ValueError(f"BioRED document {document_id} has overlapping passages")
        text_chars[passage_start:passage_end] = passage_text
        for annotation in passage.get("annotations", ()):
            mention_id = str(annotation["id"])
            if not mention_id or mention_id in seen_mention_ids:
                raise ValueError(f"Duplicate BioRED mention ID {mention_id!r} in {document_id}")
            seen_mention_ids.add(mention_id)
            locations = annotation["locations"]
            if len(locations) != 1:
                raise ValueError(
                    f"BioRED mention {document_id}:{mention_id} must have one location"
                )
            location = locations[0]
            start = int(location["offset"])
            end = start + int(location["length"])
            raw_type = str(annotation["infons"]["type"])
            try:
                entity_type = BIOC_TO_ENTITY_TYPE[raw_type]
            except KeyError as error:
                raise ValueError(f"Unknown BioRED entity type {raw_type!r}") from error
            mentions.append(
                BioREDMention(
                    id=mention_id,
                    text=str(annotation["text"]),
                    type=entity_type,
                    start=start,
                    end=end,
                    concept_ids=split_concept_ids(
                        str(annotation["infons"]["identifier"])
                    ),
                )
            )

    text = "".join(text_chars)
    for mention in mentions:
        if not 0 <= mention.start < mention.end <= len(text):
            raise ValueError(f"Invalid BioRED mention bounds in {document_id}:{mention.id}")
        if text[mention.start : mention.end] != mention.text:
            raise ValueError(
                f"BioRED offset mismatch in {document_id}:{mention.id}: {mention.text!r}"
            )

    relations: set[TypedRelation] = set()
    pair_labels: dict[tuple[str, str], str] = {}
    for relation in raw.get("relations", ()):
        infons = relation["infons"]
        label = str(infons["type"])
        if label not in BIORED_RELATION_LABELS:
            raise ValueError(f"Unknown BioRED relation label {label!r}")
        concept_a, concept_b = canonical_pair(
            str(infons["entity1"]), str(infons["entity2"])
        )
        pair = (concept_a, concept_b)
        previous = pair_labels.setdefault(pair, label)
        if previous != label:
            raise ValueError(
                f"BioRED document {document_id} has multiple labels for pair {pair}"
            )
        relations.add(TypedRelation(document_id, concept_a, concept_b, label))

    return BioREDDocument(
        id=document_id,
        text=text,
        mentions=tuple(sorted(mentions, key=lambda mention: (mention.start, mention.end))),
        relations=tuple(sorted(relations)),
    )


def is_allowed_candidate(type_a: str, type_b: str, relation_type: str) -> bool:
    """Apply the eight published BioRED concept-pair families.

    The official dev corpus contains exceptions to the guideline's illustrative
    relation-specific examples (chemical-chemical Bind and chemical-gene Cotreatment),
    so V0-B deliberately does not invent a stricter label/type matrix. The ``relation_type``
    check still ensures only canonical BioRED labels enter candidate scoring.
    """

    family = frozenset({type_a, type_b})
    return family in ALLOWED_PAIR_FAMILIES and relation_type in BIORED_RELATION_LABELS


def aggregate_mention_predictions(
    document: BioREDDocument,
    predictions: Sequence[Relation],
) -> tuple[ScoredRelation, ...]:
    """Convert mention predictions to maximum-score concept-label candidates.

    GLiREL endpoints refer to supplied mention IDs. Each endpoint expands to all of
    that mention's normalized IDs (Cartesian product for multi-ID annotations), then
    direction is removed by sorting the concept pair. Repeated mentions, opposite
    GLiREL directions, and duplicate predictions collapse by maximum score. Gold
    relations are never consulted while selecting concept IDs or scores.
    """

    mentions_by_id = {mention.id: mention for mention in document.relation_mentions()}
    scores: dict[tuple[str, str, str], float] = {}
    for prediction in predictions:
        try:
            source = mentions_by_id[prediction.source]
            target = mentions_by_id[prediction.target]
            canonical_label = PROMPT_TO_CANONICAL[prediction.type]
        except KeyError as error:
            raise ValueError(
                f"Unknown mention or prompt label in prediction: {error.args[0]}"
            ) from error
        if prediction.score is None:
            raise ValueError("GLiREL evaluation predictions must contain scores")
        if not is_allowed_candidate(source.type, target.type, canonical_label):
            continue
        for source_id in source.concept_ids:
            for target_id in target.concept_ids:
                concept_a, concept_b = canonical_pair(source_id, target_id)
                key = (concept_a, concept_b, canonical_label)
                scores[key] = max(scores.get(key, float("-inf")), prediction.score)

    return tuple(
        ScoredRelation(document.id, concept_a, concept_b, label, score)
        for (concept_a, concept_b, label), score in sorted(scores.items())
    )


def select_one_label_per_pair(
    candidates: Iterable[ScoredRelation],
) -> tuple[ScoredRelation, ...]:
    """Keep the highest scoring label for each document/concept pair.

    Equal scores use canonical BioRED label order as a deterministic tie-break. This
    operation happens only after mention-to-concept maximum-score aggregation.
    """

    label_rank = {label: index for index, label in enumerate(BIORED_RELATION_LABELS)}
    selected: dict[tuple[str, str, str], ScoredRelation] = {}
    for candidate in candidates:
        key = (candidate.document_id, candidate.concept_a, candidate.concept_b)
        previous = selected.get(key)
        if previous is None or (candidate.score, -label_rank[candidate.relation_type]) > (
            previous.score,
            -label_rank[previous.relation_type],
        ):
            selected[key] = candidate
    return tuple(sorted(selected.values(), key=lambda item: item.typed))


def _counts(gold: set[Any], predicted: set[Any]) -> dict[str, Any]:
    """Count exact set matches and derive P/R/F1 with undefined values as ``None``."""

    true_positive = len(gold & predicted)
    false_positive = len(predicted - gold)
    false_negative = len(gold - predicted)
    precision = true_positive / len(predicted) if predicted else None
    recall = true_positive / len(gold) if gold else None
    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def score_relations(
    gold: Iterable[TypedRelation],
    candidates: Iterable[ScoredRelation],
    threshold: float,
) -> dict[str, Any]:
    """Score pair-only and typed concept relations at one threshold.

    Typed TP/FP/FN are exact matches on document, canonical concept pair, and label.
    Pair-only TP/FP/FN drop the label before set comparison. Novelty is absent from
    both units. At most one candidate label per concept pair is retained before the
    inclusive ``score >= threshold`` decision.
    """

    gold_set = set(gold)
    selected = select_one_label_per_pair(candidates)
    predicted_scored = tuple(item for item in selected if item.score >= threshold)
    predicted_set = {item.typed for item in predicted_scored}
    gold_pairs = {
        (item.document_id, item.concept_a, item.concept_b) for item in gold_set
    }
    predicted_pairs = {
        (item.document_id, item.concept_a, item.concept_b) for item in predicted_set
    }
    per_label: dict[str, dict[str, Any]] = {}
    for label in BIORED_RELATION_LABELS:
        label_gold = {item for item in gold_set if item.relation_type == label}
        label_predicted = {item for item in predicted_set if item.relation_type == label}
        per_label[label] = {
            "support": len(label_gold),
            **_counts(label_gold, label_predicted),
        }
    return {
        "threshold": threshold,
        "predicted_before_threshold": len(selected),
        "predicted_after_threshold": len(predicted_set),
        "gold_relations": len(gold_set),
        "pair_only": _counts(gold_pairs, predicted_pairs),
        "typed_micro": _counts(gold_set, predicted_set),
        "per_label": per_label,
        "predictions": predicted_scored,
    }


def calibrate_threshold(
    gold: Iterable[TypedRelation], candidates: Iterable[ScoredRelation]
) -> tuple[float, dict[str, Any]]:
    """Choose dev typed-micro-F1 threshold from one reusable candidate score set.

    Every distinct score is a possible inclusive decision boundary; ``1.0`` is also
    considered for the empty/high-precision endpoint. Exact F1 ties choose the higher
    threshold, which is the requested higher-precision operating preference.
    """

    gold_tuple = tuple(gold)
    candidate_tuple = tuple(candidates)
    thresholds = sorted({0.0, 1.0, *(item.score for item in candidate_tuple)})
    results = [score_relations(gold_tuple, candidate_tuple, value) for value in thresholds]
    selected = max(
        results,
        key=lambda result: (
            result["typed_micro"]["f1"] or 0.0,
            result["typed_micro"]["precision"] or 0.0,
            result["threshold"],
        ),
    )
    return float(selected["threshold"]), selected


def serialize_scored_relations(candidates: Sequence[ScoredRelation]) -> list[dict[str, Any]]:
    """Convert cached concept candidates to JSON-compatible dictionaries."""

    return [asdict(candidate) for candidate in candidates]


def deserialize_scored_relations(raw: Sequence[Mapping[str, Any]]) -> tuple[ScoredRelation, ...]:
    """Restore JSON concept candidates while validating their canonical labels."""

    candidates = tuple(ScoredRelation(**item) for item in raw)
    unknown = {item.relation_type for item in candidates} - set(BIORED_RELATION_LABELS)
    if unknown:
        raise ValueError(f"Cached predictions contain unknown labels: {sorted(unknown)}")
    return candidates
