"""CRAFT full-text cross-corpus NER parsing, scoring, and reporting.

The evaluator reads the official CRAFT v5.0.2 native Knowtator release and
reuses :func:`ner_evaluation.score_entity_mentions` for exact half-open span
and canonical-type scoring.  CRAFT's ontology identifiers are retained only as
provenance; they are never normalized or linked.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET

from .biored import BioREDMention
from .entity_extraction import Entity
from .ner_evaluation import (
    FAILURE_CATEGORIES,
    _metric_counts,
    score_entity_mentions,
)


CRAFT_SOURCE_REPOSITORY = "https://github.com/lhunter-lab/CRAFT"
CRAFT_RELEASE_URL = f"{CRAFT_SOURCE_REPOSITORY}/releases/tag/v5.0.2"
CRAFT_RELEASE_VERSION = "v5.0.2"
CRAFT_RELEASE_COMMIT_SHA = "2abe82b8bb8089448b84937d5f61d8c218011322"

# These are the only modules with defensible mappings to the current product
# taxonomy.  The short internal labels are the labels accepted by the existing
# model-independent NER evaluator's BioRED gold adapter.
CRAFT_MODULE_TO_CANONICAL: Mapping[str, tuple[str, str]] = {
    "PR": ("Protein Ontology", "GeneOrGeneProduct"),
    "CHEBI": ("ChEBI", "ChemicalEntity"),
    "NCBITaxon": ("NCBI Taxonomy", "OrganismTaxon"),
}
CRAFT_SCORED_TYPES = (
    "GeneOrGeneProduct",
    "ChemicalEntity",
    "OrganismTaxon",
)
CRAFT_MODULE_VARIANTS: Mapping[str, str] = {
    "CHEBI": "CHEBI",
    "CL": "CL",
    "GO_BP": "GO_BP",
    "GO_CC": "GO_CC",
    "GO_MF": "GO_MF",
    "MONDO": "MONDO_without_genotype_annotations",
    "MOP": "MOP",
    "NCBITaxon": "NCBITaxon",
    "PR": "PR",
    "SO": "SO",
    "UBERON": "UBERON",
}
CRAFT_MODULE_DESCRIPTIONS: Mapping[str, str] = {
    "CL": "Cell Ontology (excluded; not CellLine)",
    "GO_BP": "Gene Ontology biological process (out of scope)",
    "GO_CC": "Gene Ontology cellular component (out of scope)",
    "GO_MF": "Gene Ontology molecular function (out of scope)",
    "MONDO": "MONDO disease ontology (not mapped in the current schema)",
    "MOP": "Molecular Process Ontology (not mapped in the current schema)",
    "SO": "Sequence Ontology (excluded; not SequenceVariant)",
    "UBERON": "Uberon anatomy ontology (not mapped in the current schema)",
}
CRAFT_INTERNAL_TYPE = {
    "GeneOrGeneProduct": "Gene",
    "ChemicalEntity": "Chemical",
    "OrganismTaxon": "Species",
}


def _sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest for one byte string."""

    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    """Hash one source or generated artifact in bounded chunks."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_sha256(paths: Sequence[Path], root: Path) -> str:
    """Hash sorted relative paths, sizes, and contents as one source manifest."""

    rows = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        rows.append(
            "\t".join(
                (
                    path.relative_to(root).as_posix(),
                    str(path.stat().st_size),
                    _sha256_file(path),
                )
            )
        )
    return _sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))


def _git_revision(root: Path) -> str | None:
    """Return the source checkout revision when the official clone is present."""

    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={root}",
                "-C",
                str(root),
                "rev-parse",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else None


def _read_ids(path: Path) -> tuple[str, ...]:
    """Read one CRAFT PMID split file without changing source identifiers."""

    return tuple(value.strip() for value in path.read_text(encoding="utf-8").splitlines() if value.strip())


@dataclass(frozen=True)
class CRAFTMention:
    """One CRAFT concept annotation and its schema-mapping decision."""

    id: str
    ontology: str
    ontology_id: str | None
    text: str
    start: int
    end: int
    spans: tuple[tuple[int, int], ...]
    canonical_type: str | None
    mapping_status: str

    def to_biored_mention(self) -> BioREDMention:
        """Adapt the mention to the existing evaluator's gold mention shape."""

        if self.mapping_status == "scored" and self.canonical_type:
            entity_type = CRAFT_INTERNAL_TYPE[self.canonical_type]
        else:
            entity_type = f"CRAFT_{self.mapping_status.upper()}:{self.ontology}"
        concept_ids = (self.ontology_id,) if self.ontology_id else ()
        return BioREDMention(
            id=self.id,
            text=self.text,
            type=entity_type,
            start=self.start,
            end=self.end,
            concept_ids=concept_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the annotation while retaining ontology provenance."""

        return {
            "id": self.id,
            "ontology": self.ontology,
            "ontology_id": self.ontology_id,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "spans": [list(span) for span in self.spans],
            "canonical_type": self.canonical_type,
            "mapping_status": self.mapping_status,
        }


@dataclass(frozen=True)
class CRAFTDocument:
    """One official CRAFT article with canonical text and all selected metadata."""

    id: str
    pmid: str
    text: str
    text_path: Path
    split: str
    mentions: tuple[CRAFTMention, ...]

    @property
    def text_sha256(self) -> str:
        """Return the checksum of the exact text sent to both models."""

        return _sha256_bytes(self.text.encode("utf-8"))

    def to_runner_document(self) -> dict[str, str]:
        """Return the model-independent runner input record."""

        return {"id": self.id, "text": self.text}

    def to_dict(self) -> dict[str, Any]:
        """Serialize document identity and bounded per-module gold accounting."""

        status_counts = Counter(mention.mapping_status for mention in self.mentions)
        module_counts = Counter(mention.ontology for mention in self.mentions)
        return {
            "id": self.id,
            "pmid": self.pmid,
            "split": self.split,
            "text_sha256": self.text_sha256,
            "text_characters": len(self.text),
            "text_source": self.text_path.name,
            "gold_mentions": len(self.mentions),
            "gold_mentions_by_module": dict(sorted(module_counts.items())),
            "gold_mentions_by_mapping_status": dict(sorted(status_counts.items())),
        }


@dataclass(frozen=True)
class CRAFTDataset:
    """Official CRAFT release identity plus parsed full-text articles."""

    source_root: Path
    release_version: str
    source_revision: str | None
    documents: tuple[CRAFTDocument, ...]
    text_manifest_sha256: str
    annotation_manifest_sha256: str
    source_manifest_sha256: str

    @property
    def document_ids(self) -> frozenset[str]:
        """Return the exact set of runner document IDs."""

        return frozenset(document.id for document in self.documents)

    def to_dict(self, *, include_documents: bool = True) -> dict[str, Any]:
        """Serialize release, source, and canonical-text identity."""

        status_counts = Counter(
            mention.mapping_status
            for document in self.documents
            for mention in document.mentions
        )
        module_counts = Counter(
            mention.ontology
            for document in self.documents
            for mention in document.mentions
        )
        result: dict[str, Any] = {
            "name": "CRAFT",
            "release_version": self.release_version,
            "source_repository": CRAFT_SOURCE_REPOSITORY,
            "official_source_location": CRAFT_SOURCE_REPOSITORY,
            "official_release_location": CRAFT_RELEASE_URL,
            "source_root": str(self.source_root),
            "source_revision": self.source_revision,
            "expected_release_commit": CRAFT_RELEASE_COMMIT_SHA,
            "release_identity_verified": self.source_revision == CRAFT_RELEASE_COMMIT_SHA,
            "document_count": len(self.documents),
            "text_manifest_sha256": self.text_manifest_sha256,
            "annotation_manifest_sha256": self.annotation_manifest_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "gold_mentions_total": sum(module_counts.values()),
            "gold_mentions_by_module": dict(sorted(module_counts.items())),
            "gold_mentions_by_mapping_status": dict(sorted(status_counts.items())),
        }
        if include_documents:
            result["documents"] = [document.to_dict() for document in self.documents]
        return result


def _parse_annotation_file(
    path: Path,
    *,
    document_id: str,
    source_text: str,
    ontology: str,
) -> tuple[CRAFTMention, ...]:
    """Parse one native Knowtator file and validate every source fragment."""

    root = ET.parse(path).getroot()
    expected_source = f"{document_id.split(':', 1)[-1]}.txt"
    raw_annotations: list[tuple[str, tuple[tuple[int, int], ...], str, str | None]] = []
    if root.tag == "knowtator-project":
        documents = root.findall("document")
        if len(documents) != 1:
            raise ValueError(f"CRAFT Knowtator-2 file must contain one document: {path.name}")
        document = documents[0]
        if document.attrib.get("id") != document_id.split(":", 1)[-1]:
            raise ValueError(f"CRAFT Knowtator-2 document ID mismatch in {path.name}")
        if document.attrib.get("text-file") != expected_source:
            raise ValueError(f"CRAFT Knowtator-2 text source mismatch in {path.name}")
        for annotation in document.findall("annotation"):
            spans = tuple(
                (int(node.attrib["start"]), int(node.attrib["end"]))
                for node in annotation.findall("span")
            )
            class_node = annotation.find("class")
            ontology_id = (
                str(class_node.attrib.get("id", ""))
                if class_node is not None
                else None
            )
            raw_annotations.append(
                (
                    str(annotation.attrib.get("id", "")),
                    spans,
                    " ... ".join((node.text or "") for node in annotation.findall("span")),
                    ontology_id,
                )
            )
    else:
        if root.attrib.get("textSource") != expected_source:
            raise ValueError(
                f"CRAFT {ontology} textSource mismatch in {path.name}: "
                f"{root.attrib.get('textSource')!r} != {expected_source!r}"
            )
        class_ids: dict[str, str | None] = {}
        for class_mention in root.findall("classMention"):
            mention_id = str(class_mention.attrib.get("id", ""))
            values = class_mention.findall("mentionClass")
            class_ids[mention_id] = (
                str(values[0].attrib.get("id", "")) if len(values) == 1 else None
            )
        for annotation in root.findall("annotation"):
            mention_node = annotation.find("mention")
            raw_id = str(mention_node.attrib.get("id", "")) if mention_node is not None else ""
            spans = tuple(
                (int(node.attrib["start"]), int(node.attrib["end"]))
                for node in annotation.findall("span")
            )
            raw_annotations.append(
                (
                    raw_id,
                    spans,
                    annotation.findtext("spannedText") or "",
                    class_ids.get(raw_id),
                )
            )

    mentions: list[CRAFTMention] = []
    seen_ids: set[str] = set()
    for index, (raw_id, spans, spanned_text, ontology_id) in enumerate(raw_annotations, start=1):
        if not raw_id:
            raise ValueError(f"CRAFT annotation {path.name}:{index} has no mention ID")
        if raw_id in seen_ids:
            raise ValueError(f"Duplicate CRAFT mention ID {raw_id!r} in {path.name}")
        seen_ids.add(raw_id)
        if not spans:
            raise ValueError(f"CRAFT annotation {path.name}:{raw_id} has no span")
        for start, end in spans:
            if not 0 <= start <= end <= len(source_text):
                raise ValueError(
                    f"CRAFT span out of bounds in {path.name}:{raw_id}: [{start}, {end})"
                )
        fragments = tuple(source_text[start:end] for start, end in spans)
        has_zero_length_span = any(start == end for start, end in spans)
        if len(spans) == 1 and not has_zero_length_span:
            if fragments[0] != spanned_text:
                raise ValueError(
                    f"CRAFT offset mismatch in {path.name}:{raw_id}: "
                    f"{spanned_text!r} != {fragments[0]!r}"
                )
        elif len(spans) > 1 and " ... ".join(fragments) != spanned_text:
            raise ValueError(
                f"CRAFT discontinuous offset mismatch in {path.name}:{raw_id}"
            )
        if len(spans) > 1 or has_zero_length_span:
            mapping_status = "ambiguous"
            canonical_type = None
        elif ontology in CRAFT_MODULE_TO_CANONICAL and ontology_id:
            mapping_status = "scored"
            canonical_type = CRAFT_MODULE_TO_CANONICAL[ontology][1]
        elif ontology in CRAFT_MODULE_TO_CANONICAL:
            mapping_status = "ambiguous"
            canonical_type = None
        else:
            mapping_status = "unsupported"
            canonical_type = None
        mentions.append(
            CRAFTMention(
                id=f"{document_id}:{ontology}:{raw_id}",
                ontology=ontology,
                ontology_id=ontology_id,
                text=spanned_text,
                start=min(start for start, _ in spans),
                end=max(end for _, end in spans),
                spans=spans,
                canonical_type=canonical_type,
                mapping_status=mapping_status,
            )
        )
    return tuple(mentions)


def _module_annotation_dir(source_root: Path, module: str) -> Path:
    """Resolve one selected non-extension CRAFT annotation variant."""

    base = (
        source_root
        / "concept-annotation"
        / module
        / CRAFT_MODULE_VARIANTS[module]
    )
    native = base / "knowtator"
    if native.is_dir():
        return native
    knowtator_two = base / "knowtator-2"
    if knowtator_two.is_dir():
        return knowtator_two
    return native


def load_craft(source_root: str | Path, *, release_version: str = CRAFT_RELEASE_VERSION) -> CRAFTDataset:
    """Load and validate all 97 official CRAFT full-text articles.

    The release's plain-text article files are the canonical source sent to both
    challengers.  Native annotations from unsupported modules are parsed into
    explicit metadata so their exclusion cannot silently inflate primary scores.
    """

    root = Path(source_root).expanduser().resolve()
    text_dir = root / "articles" / "txt"
    ids_dir = root / "articles" / "ids"
    if not text_dir.is_dir() or not ids_dir.is_dir():
        raise FileNotFoundError(f"CRAFT release root is missing articles/txt or articles/ids: {root}")
    text_paths = tuple(sorted(text_dir.glob("*.txt"), key=lambda path: path.name))
    if not text_paths:
        raise ValueError(f"CRAFT release contains no canonical text files: {root}")
    texts: dict[str, tuple[str, Path]] = {}
    for path in text_paths:
        pmid = path.stem
        if pmid in texts:
            raise ValueError(f"Duplicate CRAFT article ID: {pmid}")
        texts[pmid] = (path.read_text(encoding="utf-8"), path)
    article_ids = set(texts)
    split_by_pmid: dict[str, str] = {}
    for split in ("train", "dev", "test"):
        split_path = ids_dir / f"craft-ids-{split}.txt"
        if not split_path.is_file():
            raise FileNotFoundError(f"Missing CRAFT split identity file: {split_path}")
        for pmid in _read_ids(split_path):
            previous = split_by_pmid.setdefault(pmid, split)
            if previous != split:
                raise ValueError(f"CRAFT PMID occurs in multiple splits: {pmid}")
    if set(split_by_pmid) != article_ids:
        raise ValueError("CRAFT split files do not cover exactly the canonical text files")

    parsed_by_module: dict[str, dict[str, tuple[CRAFTMention, ...]]] = {}
    annotation_paths: list[Path] = []
    for module in sorted(CRAFT_MODULE_VARIANTS):
        directory = _module_annotation_dir(root, module)
        if not directory.is_dir():
            raise FileNotFoundError(f"Missing CRAFT annotation directory: {directory}")
        files = tuple(sorted(directory.glob("*.xml"), key=lambda path: path.name))
        file_ids = {path.name.split(".", 1)[0] for path in files}
        if file_ids != article_ids:
            missing = sorted(article_ids - file_ids)
            extra = sorted(file_ids - article_ids)
            raise ValueError(
                f"CRAFT {module} annotation coverage mismatch; missing={missing[:5]}, extra={extra[:5]}"
            )
        module_documents: dict[str, tuple[CRAFTMention, ...]] = {}
        for path in files:
            pmid = path.name.split(".", 1)[0]
            document_id = f"PMID:{pmid}"
            module_documents[pmid] = _parse_annotation_file(
                path,
                document_id=document_id,
                source_text=texts[pmid][0],
                ontology=module,
            )
        parsed_by_module[module] = module_documents
        annotation_paths.extend(files)

    documents: list[CRAFTDocument] = []
    for pmid in sorted(texts):
        document_id = f"PMID:{pmid}"
        mentions = [
            mention
            for module in sorted(parsed_by_module)
            for mention in parsed_by_module[module][pmid]
        ]
        mentions.sort(key=lambda item: (item.start, item.end, item.ontology, item.id))
        documents.append(
            CRAFTDocument(
                id=document_id,
                pmid=pmid,
                text=texts[pmid][0],
                text_path=texts[pmid][1],
                split=split_by_pmid[pmid],
                mentions=tuple(mentions),
            )
        )
    text_manifest_sha256 = _manifest_sha256(text_paths, root)
    annotation_manifest_sha256 = _manifest_sha256(annotation_paths, root)
    source_manifest_sha256 = _sha256_bytes(
        f"{text_manifest_sha256}\n{annotation_manifest_sha256}\n".encode("ascii")
    )
    return CRAFTDataset(
        source_root=root,
        release_version=release_version,
        source_revision=_git_revision(root),
        documents=tuple(documents),
        text_manifest_sha256=text_manifest_sha256,
        annotation_manifest_sha256=annotation_manifest_sha256,
        source_manifest_sha256=source_manifest_sha256,
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    """Return a bounded ratio or ``None`` for an empty denominator."""

    return numerator / denominator if denominator else None


def _independence_verification() -> dict[str, Any]:
    """Return the documented supervised-training independence check."""

    return {
        "CRAFT_listed_in_training_recipe": {
            "AIONER": False,
            "HunFlair2": False,
        },
        "authoritative_sources_checked": [
            "https://doi.org/10.1093/bioinformatics/btad310",
            "https://github.com/ncbi/AIONER",
            "https://github.com/flairNLP/flair/blob/master/resources/docs/HUNFLAIR2_TUTORIAL_3_TRAINING_NER.md",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC11453098/",
        ],
        "documented_training_corpora": {
            "AIONER": [
                "BioRED",
                "NLM-Gene",
                "GNormPlus",
                "NCBI Disease",
                "NLM-Chem",
                "BC5CDR",
                "Linnaeus",
                "Species-800",
                "tmVar3",
                "BioID",
            ],
            "HunFlair2": [
                "BioRED",
                "NLM Gene",
                "GNormPlus",
                "SCAI",
                "NLM Chem",
                "Linnaeus",
                "S800",
                "NCBI Disease",
            ],
        },
        "independent_under_documented_supervised_training": True,
        "qualification": (
            "This establishes absence from the documented supervised training "
            "recipes checked for the exact cached artifacts; it does not establish "
            "absence from every possible pretraining source."
        ),
    }


def evaluate_craft(
    dataset: CRAFTDataset,
    predictions_by_model: Mapping[str, Mapping[str, Sequence[Entity]]],
    *,
    predictor_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    report_date: str | None = None,
    example_limit: int = 5,
) -> dict[str, Any]:
    """Score both challengers against CRAFT using the shared NER evaluator."""

    if example_limit < 0:
        raise ValueError("example_limit must not be negative")
    expected_ids = dataset.document_ids
    model_reports: dict[str, Any] = {}
    metadata = predictor_metadata or {}
    gold_status_counts = Counter(
        mention.mapping_status
        for document in dataset.documents
        for mention in document.mentions
    )
    gold_module_counts = Counter(
        mention.ontology
        for document in dataset.documents
        for mention in document.mentions
    )
    for model_name, predictions in predictions_by_model.items():
        if set(predictions) != set(expected_ids):
            missing = sorted(expected_ids - set(predictions))
            extra = sorted(set(predictions) - expected_ids)
            raise ValueError(
                f"{model_name} predictions do not cover CRAFT exactly; "
                f"missing={missing[:5]}, extra={extra[:5]}"
            )
        document_scores = {}
        for document in dataset.documents:
            document_scores[document.id] = score_entity_mentions(
                document.id,
                document.text,
                tuple(mention.to_biored_mention() for mention in document.mentions),
                predictions[document.id],
                scored_types=CRAFT_SCORED_TYPES,
                failure_example_limit=example_limit,
            )
        per_type_counts: dict[str, Counter[str]] = {
            entity_type: Counter() for entity_type in CRAFT_SCORED_TYPES
        }
        failure_counts: Counter[str] = Counter()
        failure_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
        predicted_total = 0
        predicted_scored = 0
        for score in document_scores.values():
            failure_counts.update(score.failure_counts)
            predicted_total += score.predicted_scored_count + sum(
                score.predicted_unscored_counts.values()
            )
            predicted_scored += score.predicted_scored_count
            for category, records in score.failure_examples.items():
                remaining = example_limit - len(failure_examples[category])
                if remaining > 0:
                    failure_examples[category].extend(
                        record.to_dict() for record in records[:remaining]
                    )
            for entity_type, metric in score.metrics["per_type"].items():
                per_type_counts[entity_type]["tp"] += metric["tp"]
                per_type_counts[entity_type]["fp"] += metric["fp"]
                per_type_counts[entity_type]["fn"] += metric["fn"]
                per_type_counts[entity_type]["gold"] += metric["support"]
                per_type_counts[entity_type]["predicted"] += metric["predicted"]
        per_type = {
            entity_type: _metric_counts(
                values["tp"],
                values["fp"],
                values["fn"],
                gold=values["gold"],
                predicted=values["predicted"],
            )
            for entity_type, values in per_type_counts.items()
        }
        micro = _metric_counts(
            sum(values["tp"] for values in per_type_counts.values()),
            sum(values["fp"] for values in per_type_counts.values()),
            sum(values["fn"] for values in per_type_counts.values()),
            gold=sum(values["gold"] for values in per_type_counts.values()),
            predicted=sum(values["predicted"] for values in per_type_counts.values()),
        )
        macro_values = [metric["f1"] for metric in per_type.values() if metric["f1"] is not None]
        model_reports[model_name] = {
            "predictor": dict(metadata.get(model_name, {})),
            "counts": {
                "documents_evaluated": len(dataset.documents),
                "gold_mentions": sum(len(document.mentions) for document in dataset.documents),
                "gold_scored_mentions": gold_status_counts["scored"],
                "gold_unsupported_mentions": gold_status_counts["unsupported"],
                "gold_ambiguous_mentions": gold_status_counts["ambiguous"],
                "gold_mentions_by_module": dict(sorted(gold_module_counts.items())),
                "predicted_mentions": predicted_total,
                "predicted_scored_mentions": predicted_scored,
                "predicted_unsupported_mentions": predicted_total - predicted_scored,
            },
            "schema_coverage": {
                "gold": {
                    "total": sum(gold_status_counts.values()),
                    "scored": gold_status_counts["scored"],
                    "unsupported": gold_status_counts["unsupported"],
                    "ambiguous": gold_status_counts["ambiguous"],
                    "scored_fraction": _ratio(
                        gold_status_counts["scored"], sum(gold_status_counts.values())
                    ),
                },
                "predicted": {
                    "total": predicted_total,
                    "scored": predicted_scored,
                    "unsupported": predicted_total - predicted_scored,
                    "scored_fraction": _ratio(predicted_scored, predicted_total),
                },
            },
            "metrics": {
                "matching": "exact half-open character span and canonical evaluation type",
                "scored_types": list(CRAFT_SCORED_TYPES),
                "micro": micro,
                "macro_f1": sum(macro_values) / len(macro_values) if macro_values else None,
                "per_type": per_type,
            },
            "failure_analysis": {
                "counts": {
                    category: failure_counts.get(category, 0)
                    for category in FAILURE_CATEGORIES
                },
                "examples": {
                    category: failure_examples.get(category, [])
                    for category in FAILURE_CATEGORIES
                },
                "example_limit_per_category": example_limit,
            },
        }
    report: dict[str, Any] = {
        "evaluation_name": "AIONER versus HunFlair2 on CRAFT full-text NER",
        "report_date": report_date,
        "dataset": dataset.to_dict(include_documents=True),
        "mapping": {
            "scored_modules": {
                module: {
                    "ontology": description,
                    "canonical_type": canonical,
                }
                for module, (description, canonical) in CRAFT_MODULE_TO_CANONICAL.items()
            },
            "excluded_modules": dict(sorted(CRAFT_MODULE_DESCRIPTIONS.items())),
            "scored_types": list(CRAFT_SCORED_TYPES),
            "unsupported_and_ambiguous_are_excluded_from_primary_metrics": True,
            "ontology_normalization_scored": False,
        },
        "source_offset_validation": {
            "canonical_source": "articles/txt/*.txt",
            "all_contiguous_annotation_spans_match_source_text": True,
            "all_discontinuous_annotation_fragments_match_source_text": True,
            "discontinuous_and_zero_length_annotations_excluded_as_ambiguous": True,
        },
        "models": model_reports,
        "independence_verification": _independence_verification(),
        "limitations": [
            "Primary metrics use exact half-open source spans and canonical types only; no fuzzy matching is applied.",
            "Only Protein Ontology, ChEBI, and NCBI Taxonomy annotations contribute to primary metrics.",
            "Cell Ontology is not mapped to CellLine, and Sequence Ontology is not mapped to SequenceVariant.",
            "GO annotations and all other CRAFT ontology modules remain explicit unsupported metadata.",
            "Discontinuous Knowtator annotations are retained as ambiguous metadata and excluded because they do not define one exact half-open span.",
            "Ontology identifiers are provenance only; normalization and linking are out of scope.",
            "This report is cross-corpus evidence and does not make the production-model decision.",
        ],
    }
    model_names = list(model_reports)
    if model_names:
        report["comparison"] = {
            "micro_f1_order": sorted(
                model_names,
                key=lambda model: (
                    -(model_reports[model]["metrics"]["micro"]["f1"] or -1.0),
                    model,
                ),
            ),
            "failure_count_difference_HunFlair2_minus_AIONER": {
                category: model_reports.get("HunFlair2", {})
                .get("failure_analysis", {})
                .get("counts", {})
                .get(category, 0)
                - model_reports.get("AIONER", {})
                .get("failure_analysis", {})
                .get("counts", {})
                .get(category, 0)
                for category in FAILURE_CATEGORIES
            },
        }
    validate_craft_report_arithmetic(report)
    return report


def validate_craft_report_arithmetic(report: Mapping[str, Any]) -> None:
    """Validate count-derived metrics and schema-accounting invariants."""

    expected_types = set(CRAFT_SCORED_TYPES)
    for model_name, model_report in report.get("models", {}).items():
        metrics = model_report["metrics"]
        per_type = metrics["per_type"]
        if set(per_type) != expected_types:
            raise ValueError(f"{model_name} CRAFT per-type metrics have unexpected classes")
        tp = sum(metric["tp"] for metric in per_type.values())
        fp = sum(metric["fp"] for metric in per_type.values())
        fn = sum(metric["fn"] for metric in per_type.values())
        gold = sum(metric["support"] for metric in per_type.values())
        predicted = sum(metric["predicted"] for metric in per_type.values())
        micro = metrics["micro"]
        if (micro["tp"], micro["fp"], micro["fn"], micro["support"], micro["predicted"]) != (
            tp,
            fp,
            fn,
            gold,
            predicted,
        ):
            raise ValueError(f"{model_name} CRAFT micro counts are inconsistent")
        counts = model_report["counts"]
        if counts["gold_scored_mentions"] != gold:
            raise ValueError(f"{model_name} CRAFT gold support is inconsistent")
        if counts["predicted_scored_mentions"] != predicted:
            raise ValueError(f"{model_name} CRAFT predicted support is inconsistent")
        if counts["predicted_mentions"] != predicted + counts["predicted_unsupported_mentions"]:
            raise ValueError(f"{model_name} CRAFT prediction accounting is inconsistent")
        macro_values = [metric["f1"] for metric in per_type.values() if metric["f1"] is not None]
        expected_macro = sum(macro_values) / len(macro_values) if macro_values else None
        if metrics["macro_f1"] != expected_macro:
            raise ValueError(f"{model_name} CRAFT macro F1 is inconsistent")


def _display_metric(value: Any) -> str:
    """Render one metric compactly for Markdown without changing JSON values."""

    return "—" if value is None else str(value)


def render_craft_markdown(report: Mapping[str, Any]) -> str:
    """Render a concise reviewer-facing CRAFT evidence report."""

    dataset = report["dataset"]
    model_input = report.get("model_input", {})
    lines = [
        "# AIONER versus HunFlair2 on CRAFT full-text NER",
        "",
        "CRAFT is the primary clean independent cross-corpus benchmark for the current NER model-selection question.",
        "",
        "## Dataset identity",
        "",
        f"- Release: {dataset['release_version']}",
        f"- Official source: {dataset['official_source_location']}",
        f"- Official release: {dataset['official_release_location']}",
        f"- Source revision: {dataset['source_revision']}",
        f"- Release identity verified: {dataset['release_identity_verified']}",
        f"- Articles evaluated: {dataset['document_count']}",
        f"- Text manifest SHA-256: {dataset['text_manifest_sha256']}",
        f"- Annotation manifest SHA-256: {dataset['annotation_manifest_sha256']}",
        f"- Combined source manifest SHA-256: {dataset['source_manifest_sha256']}",
        f"- Shared model-input SHA-256: {model_input.get('sha256', 'recorded by CLI')}",
        "- Identical canonical model input: AIONER and HunFlair2",
        "",
        "## Ontology mapping",
        "",
        "| CRAFT module | Canonical class | Primary scoring |",
        "|---|---|---|",
    ]
    for module, mapping in report["mapping"]["scored_modules"].items():
        lines.append(f"| {mapping['ontology']} (`{module}`) | {mapping['canonical_type']} | yes |")
    lines.extend(
        [
            "",
            "Unsupported and ambiguous annotations remain in the accounting below and are excluded from primary metrics.",
            "",
            "| Gold mapping status | Count |",
            "|---|---:|",
        ]
    )
    for status, count in sorted(dataset["gold_mentions_by_mapping_status"].items()):
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "## Exact NER results", "", "| Model | Gold scored | Predicted | Precision | Recall | Micro F1 | Macro F1 |", "|---|---:|---:|---:|---:|---:|---:|"])
    for model, model_report in report["models"].items():
        metrics = model_report["metrics"]
        micro = metrics["micro"]
        lines.append(
            f"| {model} | {model_report['counts']['gold_scored_mentions']} | "
            f"{model_report['counts']['predicted_scored_mentions']} | "
            f"{_display_metric(micro['precision'])} | {_display_metric(micro['recall'])} | "
            f"{_display_metric(micro['f1'])} | {_display_metric(metrics['macro_f1'])} |"
        )
    lines.extend(["", "### Per type", "", "| Type | AIONER P | AIONER R | AIONER F1 | HunFlair2 P | HunFlair2 R | HunFlair2 F1 |", "|---|---:|---:|---:|---:|---:|---:|"])
    for entity_type in CRAFT_SCORED_TYPES:
        values = []
        for model in ("AIONER", "HunFlair2"):
            metric = report["models"][model]["metrics"]["per_type"][entity_type]
            values.extend((metric["precision"], metric["recall"], metric["f1"]))
        lines.append(
            f"| {entity_type} | {_display_metric(values[0])} | {_display_metric(values[1])} | {_display_metric(values[2])} | "
            f"{_display_metric(values[3])} | {_display_metric(values[4])} | {_display_metric(values[5])} |"
        )
    lines.extend(["", "## Failure taxonomy", "", "| Category | AIONER | HunFlair2 |", "|---|---:|---:|"])
    for category in FAILURE_CATEGORIES:
        lines.append(
            f"| {category} | {report['models']['AIONER']['failure_analysis']['counts'][category]} | "
            f"{report['models']['HunFlair2']['failure_analysis']['counts'][category]} |"
        )
    lines.extend(["", "## Artifact identity", ""])
    for model, model_report in report["models"].items():
        predictor = model_report["predictor"]
        lines.extend(
            [
                f"### {model}",
                "",
                f"- Model: {predictor.get('model')}",
                f"- Artifact SHA-256: {predictor.get('model_artifact_sha256')}",
                f"- Runtime: `{json.dumps(predictor.get('runtime', {}), sort_keys=True)}`",
                "",
            ]
        )
    independence = report["independence_verification"]
    lines.extend(
        [
            "## Benchmark independence",
            "",
            "- CRAFT listed in documented AIONER training recipe: "
            f"{independence['CRAFT_listed_in_training_recipe']['AIONER']}",
            "- CRAFT listed in documented HunFlair2 training recipe: "
            f"{independence['CRAFT_listed_in_training_recipe']['HunFlair2']}",
            f"- Independent under documented supervised training: {independence['independent_under_documented_supervised_training']}",
            f"- Qualification: {independence['qualification']}",
            "",
            "## Caveats",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "CRAFTDataset",
    "CRAFTDocument",
    "CRAFTMention",
    "CRAFT_MODULE_TO_CANONICAL",
    "CRAFT_RELEASE_COMMIT_SHA",
    "CRAFT_RELEASE_URL",
    "CRAFT_RELEASE_VERSION",
    "CRAFT_SCORED_TYPES",
    "evaluate_craft",
    "load_craft",
    "render_craft_markdown",
    "validate_craft_report_arithmetic",
]
