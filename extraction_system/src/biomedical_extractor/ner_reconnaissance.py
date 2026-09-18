"""Target-domain biomedical NER acquisition and model-agreement analysis.

This module owns the evaluation-only evidence path for the nine science-team
papers. It keeps source acquisition, canonical text construction, span-
preserving diagnostics, model comparison, and review sampling separate from
production extraction and from relation extraction.

The canonical article text is assembled from meaningful title, abstract, and
body paragraphs. All prediction offsets are required to resolve against this
untouched canonical string.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import urllib.request
import xml.etree.ElementTree as ET

from .entity_extraction import Entity
from .ner_evaluation import canonical_predicted_type


TARGET_DOMAIN_DATE = "2026-09-18"
SHARED_COMPARISON_TYPES = (
    "GeneOrGeneProduct",
    "DiseaseOrPhenotypicFeature",
    "ChemicalEntity",
    "OrganismTaxon",
    "CellLine",
)
SEQUENCE_VARIANT_TYPE = "SequenceVariant"

AGREEMENT_EXACT = "exact_agreement"
AGREEMENT_TYPE = "type_disagreement"
AGREEMENT_BOUNDARY = "boundary_disagreement"
AGREEMENT_CROSS_TYPE = "cross_type_overlap"
AGREEMENT_AIONER_ONLY = "aioner_only"
AGREEMENT_HUNFLAIR2_ONLY = "hunflair2_only"
AGREEMENT_CATEGORIES = (
    AGREEMENT_EXACT,
    AGREEMENT_TYPE,
    AGREEMENT_BOUNDARY,
    AGREEMENT_CROSS_TYPE,
    AGREEMENT_AIONER_ONLY,
    AGREEMENT_HUNFLAIR2_ONLY,
)

_EXCLUDED_BODY_TAGS = {
    "ack",
    "acknowledgments",
    "fig",
    "fig-group",
    "fn-group",
    "ref",
    "ref-list",
    "supplementary-material",
    "table-wrap",
    "table-wrap-foot",
}
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_UNMATCHED_OFFSET = 10**12


TARGET_PAPER_SPECS: tuple[Mapping[str, str], ...] = (
    {
        "paper_id": "PMID:27370646",
        "pmid": "27370646",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/27370646/",
    },
    {
        "paper_id": "PMID:27172794",
        "pmid": "27172794",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/27172794/",
    },
    {
        "paper_id": "PMID:33652126",
        "pmid": "33652126",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/33652126/",
    },
    {
        "paper_id": "PMID:31324362",
        "pmid": "31324362",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/31324362/",
    },
    {
        "paper_id": "PMCID:PMC8605525",
        "pmcid": "PMC8605525",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8605525/",
    },
    {
        "paper_id": "PMCID:PMC11824863",
        "pmcid": "PMC11824863",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11824863/",
    },
    {
        "paper_id": "PMID:38569671",
        "pmid": "38569671",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/38569671/",
    },
    {
        "paper_id": "PMCID:PMC10444909",
        "pmcid": "PMC10444909",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10444909/",
    },
    {
        "paper_id": "PMCID:PMC10770459",
        "pmcid": "PMC10770459",
        "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10770459/",
    },
)


@dataclass(frozen=True)
class TextSegment:
    """One canonical text segment and its section provenance."""

    section: str
    text: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable provenance record."""

        return {
            "section": self.section,
            "text": self.text,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class TargetPaper:
    """One acquired paper represented by canonical, span-stable article text."""

    paper_id: str
    pmid: str | None
    pmcid: str | None
    title: str
    source_url: str
    acquisition_mode: str
    text: str
    segments: tuple[TextSegment, ...]
    source_checksum: str
    source_format: str
    fallback_reason: str | None = None

    @property
    def text_checksum(self) -> str:
        """Return the SHA-256 of the canonical extracted text."""

        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def section_availability(self) -> tuple[str, ...]:
        """Return stable unique section names represented in the text."""

        return tuple(dict.fromkeys(segment.section for segment in self.segments))

    @property
    def sentence_count(self) -> int:
        """Return the deterministic sentence count for the canonical text."""

        return len(sentence_spans(self.text))

    def section_for_offset(self, offset: int) -> str:
        """Return the narrowest known section containing a source offset."""

        for segment in self.segments:
            if segment.start <= offset < segment.end:
                return segment.section
        return "unknown"

    def to_dict(self, *, include_text: bool = True) -> dict[str, Any]:
        """Serialize paper metadata and optional cached canonical text."""

        result: dict[str, Any] = {
            "paper_id": self.paper_id,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "title": self.title,
            "source_url": self.source_url,
            "acquisition_mode": self.acquisition_mode,
            "text_character_count": len(self.text),
            "text_sha256": self.text_checksum,
            "source_checksum": self.source_checksum,
            "source_format": self.source_format,
            "fallback_reason": self.fallback_reason,
            "section_availability": list(self.section_availability),
            "sentence_count": self.sentence_count,
            "segments": [segment.to_dict() for segment in self.segments],
        }
        if include_text:
            result["text"] = self.text
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TargetPaper":
        """Load one cached paper and validate its text/segment checksums."""

        text = value.get("text")
        if not isinstance(text, str):
            raise ValueError("Cached target paper requires canonical text")
        segments: list[TextSegment] = []
        for raw in value.get("segments", ()):
            if not isinstance(raw, Mapping):
                raise ValueError("Cached target paper segments must be objects")
            segment = TextSegment(
                str(raw["section"]),
                str(raw["text"]),
                int(raw["start"]),
                int(raw["end"]),
            )
            if text[segment.start : segment.end] != segment.text:
                raise ValueError(
                    f"Cached segment does not resolve for {value.get('paper_id')}"
                )
            segments.append(segment)
        paper = cls(
            paper_id=str(value["paper_id"]),
            pmid=None if value.get("pmid") is None else str(value["pmid"]),
            pmcid=None if value.get("pmcid") is None else str(value["pmcid"]),
            title=str(value.get("title", "")),
            source_url=str(value["source_url"]),
            acquisition_mode=str(value["acquisition_mode"]),
            text=text,
            segments=tuple(segments),
            source_checksum=str(value["source_checksum"]),
            source_format=str(value["source_format"]),
            fallback_reason=(
                None
                if value.get("fallback_reason") is None
                else str(value["fallback_reason"])
            ),
        )
        expected = value.get("text_sha256")
        if expected is not None and paper.text_checksum != expected:
            raise ValueError(f"Cached target paper checksum mismatch: {paper.paper_id}")
        return paper


@dataclass(frozen=True)
class Alignment:
    """One deterministic one-to-one agreement or disagreement event."""

    category: str
    aioner: Entity | None
    hunflair2: Entity | None
    aioner_type: str | None
    hunflair2_type: str | None


def _local_name(tag: str) -> str:
    """Return a lowercase XML tag name without an optional namespace."""

    return tag.rsplit("}", 1)[-1].lower()


def _clean_xml_text(element: ET.Element | None) -> str:
    """Flatten inline XML markup while preserving words and punctuation."""

    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _first_element(root: ET.Element, name: str) -> ET.Element | None:
    """Find the first XML element with a local tag name."""

    return next((item for item in root.iter() if _local_name(item.tag) == name), None)


def _article_identifier(root: ET.Element, identifier_type: str) -> str | None:
    """Read one article identifier from PubMed or PMC XML."""

    for element in root.iter():
        if _local_name(element.tag) != "article-id":
            continue
        if element.attrib.get("pub-id-type") == identifier_type:
            value = _clean_xml_text(element)
            if value:
                return value
    return None


def _normalise_section_name(parts: Sequence[str]) -> str:
    """Create a readable, deterministic section path."""

    values = [value for value in parts if value]
    return " / ".join(values) if values else "body"


def _body_segments(body: ET.Element | None) -> list[tuple[str, str]]:
    """Extract prose paragraphs while excluding reference and figure noise."""

    segments: list[tuple[str, str]] = []

    def visit(element: ET.Element, section_parts: tuple[str, ...]) -> None:
        tag = _local_name(element.tag)
        if tag in _EXCLUDED_BODY_TAGS:
            return
        current_parts = section_parts
        if tag == "sec":
            title = next(
                (
                    _clean_xml_text(child)
                    for child in list(element)
                    if _local_name(child.tag) == "title"
                ),
                "",
            )
            if title:
                current_parts = section_parts + (title,)
        if tag == "p":
            text = _clean_xml_text(element)
            if text:
                segments.append((_normalise_section_name(current_parts), text))
            return
        for child in list(element):
            visit(child, current_parts)

    if body is not None:
        visit(body, ())
    return segments


def _abstract_segments(root: ET.Element) -> list[tuple[str, str]]:
    """Extract abstract paragraphs with their optional labels."""

    abstract = _first_element(root, "abstract")
    if abstract is None:
        return []
    segments: list[tuple[str, str]] = []
    for child in list(abstract):
        if _local_name(child.tag) not in {"abstracttext", "p"}:
            continue
        text = _clean_xml_text(child)
        if not text:
            continue
        label = child.attrib.get("Label") or child.attrib.get("NlmCategory")
        section = "abstract" if not label else f"abstract / {label}"
        segments.append((section, text))
    if not segments:
        text = _clean_xml_text(abstract)
        if text:
            segments.append(("abstract", text))
    return segments


def _assemble_text(
    title: str,
    abstract: Sequence[tuple[str, str]],
    body: Sequence[tuple[str, str]],
) -> tuple[str, tuple[TextSegment, ...]]:
    """Join cleaned source segments and record exact canonical offsets."""

    pieces: list[str] = []
    segments: list[TextSegment] = []
    for section, text in (("title", title), *abstract, *body):
        if not text:
            continue
        if pieces:
            pieces.append("\n\n")
        start = sum(len(piece) for piece in pieces)
        pieces.append(text)
        end = start + len(text)
        segments.append(TextSegment(section, text, start, end))
    return "".join(pieces), tuple(segments)


def _make_paper(
    *,
    paper_id: str,
    pmid: str | None,
    pmcid: str | None,
    source_url: str,
    raw: bytes,
    source_format: str,
    acquisition_mode: str,
    title: str,
    abstract: Sequence[tuple[str, str]],
    body: Sequence[tuple[str, str]],
    fallback_reason: str | None = None,
) -> TargetPaper:
    """Build one immutable paper value from parsed source segments."""

    text, segments = _assemble_text(title, abstract, body)
    return TargetPaper(
        paper_id=paper_id,
        pmid=pmid,
        pmcid=pmcid,
        title=title,
        source_url=source_url,
        acquisition_mode=acquisition_mode,
        text=text,
        segments=segments,
        source_checksum=hashlib.sha256(raw).hexdigest(),
        source_format=source_format,
        fallback_reason=fallback_reason,
    )


def parse_pubmed_xml(
    raw: bytes,
    *,
    paper_id: str,
    source_url: str,
    pmid: str | None = None,
) -> TargetPaper:
    """Parse an official PubMed XML record as an abstract-only paper."""

    root = ET.fromstring(raw)
    article = _first_element(root, "article")
    title = _clean_xml_text(_first_element(article or root, "articletitle"))
    resolved_pmid = pmid or _clean_xml_text(_first_element(root, "pmid")) or None
    pmcid = _article_identifier(root, "pmc")
    abstract = _abstract_segments(root)
    return _make_paper(
        paper_id=paper_id,
        pmid=resolved_pmid,
        pmcid=pmcid,
        source_url=source_url,
        raw=raw,
        source_format="pubmed_xml",
        acquisition_mode="abstract_only",
        title=title,
        abstract=abstract,
        body=(),
    )


def parse_pmc_xml(
    raw: bytes,
    *,
    paper_id: str,
    source_url: str,
    pmcid: str | None = None,
) -> TargetPaper:
    """Parse official PMC XML and retain prose body sections when available."""

    root = ET.fromstring(raw)
    title = _clean_xml_text(_first_element(root, "article-title"))
    pmid = _article_identifier(root, "pmid")
    resolved_pmcid = pmcid or _article_identifier(root, "pmc")
    abstract = _abstract_segments(root)
    body = _body_segments(_first_element(root, "body"))
    mode = "full_text" if body else "abstract_only"
    reason = None if body else "PMC XML contained no extractable body prose"
    return _make_paper(
        paper_id=paper_id,
        pmid=pmid,
        pmcid=resolved_pmcid,
        source_url=source_url,
        raw=raw,
        source_format="pmc_xml",
        acquisition_mode=mode,
        title=title,
        abstract=abstract,
        body=body,
        fallback_reason=reason,
    )


def _fetch_url(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
    timeout: float = 60.0,
) -> bytes:
    """Fetch one official source with an identifiable user agent."""

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "biomedical-extractor/ner-reconnaissance (research evaluation)",
            "Accept": "application/xml,text/xml,text/plain,*/*",
        },
    )
    fetch = opener or urllib.request.urlopen
    with fetch(request, timeout=timeout) as response:
        return response.read()


def _pubmed_url(pmid: str) -> str:
    """Return the official PubMed XML E-utilities endpoint."""

    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&retmode=xml"
    )


def _pmc_url(pmcid: str) -> str:
    """Return the official PMC XML E-utilities endpoint."""

    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pmc&id={pmcid}&retmode=xml"
    )


def acquire_target_corpus(
    cache_dir: Path,
    *,
    refresh: bool = False,
    opener: Callable[..., Any] | None = None,
) -> tuple[TargetPaper, ...]:
    """Acquire all obtainable target papers from official NCBI XML sources."""

    cache_dir = Path(cache_dir)
    raw_dir = cache_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    papers: list[TargetPaper] = []
    for spec in TARGET_PAPER_SPECS:
        paper_id = spec["paper_id"]
        source_url = spec["source_url"]
        pmid = spec.get("pmid")
        pmcid = spec.get("pmcid")

        pubmed_raw: bytes | None = None
        if pmcid is None:
            if pmid is None:
                raise ValueError(f"Target paper lacks PMID and PMCID: {paper_id}")
            pubmed_path = raw_dir / f"{paper_id.replace(':', '_')}_pubmed.xml"
            if refresh or not pubmed_path.exists():
                pubmed_raw = _fetch_url(_pubmed_url(pmid), opener=opener)
                pubmed_path.write_bytes(pubmed_raw)
            else:
                pubmed_raw = pubmed_path.read_bytes()
            discovered = parse_pubmed_xml(
                pubmed_raw,
                paper_id=paper_id,
                source_url=source_url,
                pmid=pmid,
            )
            pmcid = discovered.pmcid

        if pmcid is not None:
            pmc_path = raw_dir / f"{paper_id.replace(':', '_')}_pmc.xml"
            try:
                if refresh or not pmc_path.exists():
                    pmc_raw = _fetch_url(_pmc_url(pmcid), opener=opener)
                    pmc_path.write_bytes(pmc_raw)
                else:
                    pmc_raw = pmc_path.read_bytes()
                paper = parse_pmc_xml(
                    pmc_raw,
                    paper_id=paper_id,
                    source_url=source_url,
                    pmcid=pmcid,
                )
                if paper.acquisition_mode == "full_text":
                    papers.append(paper)
                    continue
            except Exception as error:
                fallback_reason = f"PMC acquisition failed: {type(error).__name__}: {error}"
            else:
                if pmid is None:
                    pmid = paper.pmid
                fallback_reason = (
                    "PMC source was accessible but yielded no extractable body prose"
                )
        else:
            fallback_reason = "No PMCID was discoverable from official PubMed metadata"

        if pubmed_raw is None:
            if pmid is None:
                raise ValueError(f"Cannot fall back to PubMed without PMID: {paper_id}")
            pubmed_path = raw_dir / f"{paper_id.replace(':', '_')}_pubmed.xml"
            if refresh or not pubmed_path.exists():
                pubmed_raw = _fetch_url(_pubmed_url(pmid), opener=opener)
                pubmed_path.write_bytes(pubmed_raw)
            else:
                pubmed_raw = pubmed_path.read_bytes()
        abstract_paper = parse_pubmed_xml(
            pubmed_raw,
            paper_id=paper_id,
            source_url=source_url,
            pmid=pmid,
        )
        papers.append(
            TargetPaper(
                paper_id=abstract_paper.paper_id,
                pmid=abstract_paper.pmid,
                pmcid=pmcid or abstract_paper.pmcid,
                title=abstract_paper.title,
                source_url=abstract_paper.source_url,
                acquisition_mode="abstract_only",
                text=abstract_paper.text,
                segments=abstract_paper.segments,
                source_checksum=abstract_paper.source_checksum,
                source_format=abstract_paper.source_format,
                fallback_reason=fallback_reason,
            )
        )
    expected = {spec["paper_id"] for spec in TARGET_PAPER_SPECS}
    if {paper.paper_id for paper in papers} != expected:
        raise ValueError("Target corpus acquisition did not produce all requested papers")
    return tuple(papers)


def write_target_corpus(papers: Sequence[TargetPaper], path: Path) -> None:
    """Write a deterministic ignored cache containing canonical article text."""

    payload = {
        "schema_version": 1,
        "papers": [paper.to_dict(include_text=True) for paper in papers],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_target_corpus(path: Path) -> tuple[TargetPaper, ...]:
    """Load and validate a cached canonical target corpus."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported target corpus cache schema")
    papers = tuple(TargetPaper.from_dict(value) for value in payload.get("papers", ()))
    if len(papers) != len(TARGET_PAPER_SPECS):
        raise ValueError("Target corpus cache does not contain all requested papers")
    return papers


def sentence_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Split text deterministically while preserving half-open source offsets."""

    if not text:
        return ()
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BOUNDARY.finditer(text):
        end = match.start()
        if text[start:end].strip():
            spans.append((start, end))
        start = match.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return tuple(spans)


def _overlap(left: Entity, right: Entity) -> bool:
    """Return whether two entity spans overlap."""

    return max(left.start, right.start) < min(left.end, right.end)


def _canonical_type(entity: Entity) -> str | None:
    """Map an adapter label to the comparison taxonomy."""

    canonical = canonical_predicted_type(entity.type)
    if canonical:
        return canonical
    if entity.type in set(SHARED_COMPARISON_TYPES) | {SEQUENCE_VARIANT_TYPE}:
        return entity.type
    return None


def _validate_entities(text: str, entities: Sequence[Entity], model: str) -> None:
    """Fail closed when a cached model prediction violates source offsets."""

    for entity in entities:
        if not isinstance(entity, Entity):
            raise TypeError(f"{model} returned {type(entity).__name__}, expected Entity")
        if not 0 <= entity.start < entity.end <= len(text):
            raise ValueError(
                f"{model} returned invalid span [{entity.start}, {entity.end})"
            )
        if text[entity.start : entity.end] != entity.text:
            raise ValueError(
                f"{model} span [{entity.start}, {entity.end}) does not resolve"
            )


def align_entity_predictions(
    aioner: Sequence[Entity],
    hunflair2: Sequence[Entity],
    *,
    allowed_types: Sequence[str] | None = None,
) -> tuple[Alignment, ...]:
    """Create deterministic one-to-one agreement/disagreement alignments."""

    allowed = None if allowed_types is None else set(allowed_types)
    left = [
        entity
        for entity in aioner
        if allowed is None or _canonical_type(entity) in allowed
    ]
    right = [
        entity
        for entity in hunflair2
        if allowed is None or _canonical_type(entity) in allowed
    ]
    candidates: list[tuple[int, int, int, int, int, int, str]] = []
    priority = {
        AGREEMENT_EXACT: 0,
        AGREEMENT_TYPE: 1,
        AGREEMENT_BOUNDARY: 2,
        AGREEMENT_CROSS_TYPE: 3,
    }
    for left_index, left_entity in enumerate(left):
        for right_index, right_entity in enumerate(right):
            left_type = _canonical_type(left_entity)
            right_type = _canonical_type(right_entity)
            if not _overlap(left_entity, right_entity):
                continue
            if (
                left_entity.start == right_entity.start
                and left_entity.end == right_entity.end
                and left_type == right_type
            ):
                category = AGREEMENT_EXACT
            elif (
                left_entity.start == right_entity.start
                and left_entity.end == right_entity.end
            ):
                category = AGREEMENT_TYPE
            elif left_type == right_type:
                category = AGREEMENT_BOUNDARY
            else:
                category = AGREEMENT_CROSS_TYPE
            candidates.append(
                (
                    priority[category],
                    min(left_entity.start, right_entity.start),
                    min(left_entity.end, right_entity.end),
                    left_index,
                    right_index,
                    len(candidates),
                    category,
                )
            )
    candidates.sort()
    matched_left: set[int] = set()
    matched_right: set[int] = set()
    alignments: list[Alignment] = []
    for _, _, _, left_index, right_index, _, category in candidates:
        if left_index in matched_left or right_index in matched_right:
            continue
        matched_left.add(left_index)
        matched_right.add(right_index)
        left_entity = left[left_index]
        right_entity = right[right_index]
        alignments.append(
            Alignment(
                category,
                left_entity,
                right_entity,
                _canonical_type(left_entity),
                _canonical_type(right_entity),
            )
        )
    for index, entity in enumerate(left):
        if index not in matched_left:
            alignments.append(
                Alignment(
                    AGREEMENT_AIONER_ONLY,
                    entity,
                    None,
                    _canonical_type(entity),
                    None,
                )
            )
    for index, entity in enumerate(right):
        if index not in matched_right:
            alignments.append(
                Alignment(
                    AGREEMENT_HUNFLAIR2_ONLY,
                    None,
                    entity,
                    None,
                    _canonical_type(entity),
                )
            )
    return tuple(
        sorted(
            alignments,
            key=lambda item: (
                min(
                    item.aioner.start
                    if item.aioner is not None
                    else _UNMATCHED_OFFSET,
                    item.hunflair2.start
                    if item.hunflair2 is not None
                    else _UNMATCHED_OFFSET,
                ),
                item.category,
                item.aioner_type or "",
                item.hunflair2_type or "",
            ),
        )
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    """Return a bounded ratio with an explicit undefined value."""

    return numerator / denominator if denominator else None


def summarize_alignments(
    alignments: Sequence[Alignment],
    *,
    selected_types: Sequence[str],
) -> dict[str, Any]:
    """Summarize alignment counts globally and by canonical entity class."""

    selected = tuple(selected_types)
    selected_set = set(selected)
    counts: Counter[str] = Counter(item.category for item in alignments)
    per_type: dict[str, Counter[str]] = {
        entity_type: Counter() for entity_type in selected
    }
    for item in alignments:
        types = {
            value for value in (item.aioner_type, item.hunflair2_type) if value
        }
        for entity_type in types & selected_set:
            per_type[entity_type][item.category] += 1
    total = sum(counts.values())
    return {
        "counts": {
            category: counts.get(category, 0) for category in AGREEMENT_CATEGORIES
        },
        "total_alignment_events": total,
        "exact_agreement_fraction": _ratio(counts[AGREEMENT_EXACT], total),
        "by_entity_class": {
            entity_type: {
                "counts": {
                    category: per_type[entity_type].get(category, 0)
                    for category in AGREEMENT_CATEGORIES
                },
                "exact_agreement_fraction": _ratio(
                    per_type[entity_type].get(AGREEMENT_EXACT, 0),
                    sum(per_type[entity_type].values()),
                ),
            }
            for entity_type in selected
        },
    }


def sentence_cooccurrence_diagnostics(
    text: str,
    entities: Sequence[Entity],
) -> dict[str, Any]:
    """Count sentence-level entity and pair candidates without inferring relations."""

    spans = sentence_spans(text)
    containing_one = 0
    containing_two = 0
    pair_count = 0
    combinations: Counter[str] = Counter()
    for sentence_start, sentence_end in spans:
        sentence_entities = [
            entity
            for entity in entities
            if max(sentence_start, entity.start) < min(sentence_end, entity.end)
        ]
        if sentence_entities:
            containing_one += 1
        if len(sentence_entities) >= 2:
            containing_two += 1
        pair_count += len(sentence_entities) * (len(sentence_entities) - 1) // 2
        for index, left in enumerate(sentence_entities):
            left_type = _canonical_type(left) or left.type
            for right in sentence_entities[index + 1 :]:
                right_type = _canonical_type(right) or right.type
                combinations[" ↔ ".join(sorted((left_type, right_type)))] += 1
    return {
        "sentence_count": len(spans),
        "sentences_containing_at_least_one_entity": containing_one,
        "sentences_containing_at_least_two_entities": containing_two,
        "distinct_entity_pairs_cooccurring_within_sentence": pair_count,
        "entity_class_combinations": dict(sorted(combinations.items())),
    }


def _entity_payload(entity: Entity | None) -> dict[str, Any] | None:
    """Serialize one local entity for reports and review examples."""

    if entity is None:
        return None
    return {
        "id": entity.id,
        "text": entity.text,
        "type": entity.type,
        "canonical_type": _canonical_type(entity),
        "start": entity.start,
        "end": entity.end,
        "score": entity.score,
    }


def _context_for_span(
    paper: TargetPaper,
    start: int,
    end: int,
) -> dict[str, Any]:
    """Return sentence context and section provenance for one source span."""

    sentence = next(
        (
            (sentence_start, sentence_end)
            for sentence_start, sentence_end in sentence_spans(paper.text)
            if max(sentence_start, start) < min(sentence_end, end)
        ),
        (max(0, start - 120), min(len(paper.text), end + 120)),
    )
    sentence_start, sentence_end = sentence
    return {
        "section": paper.section_for_offset(start),
        "sentence": {
            "start": sentence_start,
            "end": sentence_end,
            "text": paper.text[sentence_start:sentence_end],
        },
        "source_span": {
            "start": start,
            "end": end,
            "text": paper.text[start:end],
        },
    }


def _alignment_candidate(paper: TargetPaper, alignment: Alignment) -> dict[str, Any]:
    """Turn one alignment into a human-review candidate."""

    entities = [
        entity for entity in (alignment.aioner, alignment.hunflair2) if entity
    ]
    start = min(entity.start for entity in entities)
    end = max(entity.end for entity in entities)
    candidate = {
        "paper_id": paper.paper_id,
        "pmid": paper.pmid,
        "pmcid": paper.pmcid,
        "category": alignment.category,
        "entity_class": alignment.aioner_type or alignment.hunflair2_type,
        "aioner_prediction": _entity_payload(alignment.aioner),
        "hunflair2_prediction": _entity_payload(alignment.hunflair2),
    }
    candidate.update(_context_for_span(paper, start, end))
    return candidate


def _sentence_candidates(
    paper: TargetPaper,
    aioner: Sequence[Entity],
    hunflair2: Sequence[Entity],
) -> list[dict[str, Any]]:
    """Build review candidates for sentences exposing multiple entities."""

    candidates: list[dict[str, Any]] = []
    for start, end in sentence_spans(paper.text):
        a_entities = [
            entity
            for entity in aioner
            if max(start, entity.start) < min(end, entity.end)
        ]
        h_entities = [
            entity
            for entity in hunflair2
            if max(start, entity.start) < min(end, entity.end)
        ]
        if len(a_entities) + len(h_entities) < 2:
            continue
        candidates.append(
            {
                "paper_id": paper.paper_id,
                "pmid": paper.pmid,
                "pmcid": paper.pmcid,
                "category": "multi_entity_sentence",
                "entity_class": "multiple",
                "section": paper.section_for_offset(start),
                "sentence": {
                    "start": start,
                    "end": end,
                    "text": paper.text[start:end],
                },
                "source_span": {
                    "start": start,
                    "end": end,
                    "text": paper.text[start:end],
                },
                "aioner_prediction": [
                    _entity_payload(entity) for entity in a_entities
                ],
                "hunflair2_prediction": [
                    _entity_payload(entity) for entity in h_entities
                ],
            }
        )
    return candidates


def build_review_packet(
    candidates: Sequence[Mapping[str, Any]],
    *,
    target_count: int = 75,
) -> dict[str, Any]:
    """Select deterministic stratified review examples without model judgment."""

    if not 0 <= target_count <= 100:
        raise ValueError("review target_count must be between 0 and 100")
    unique: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        key = hashlib.sha256(
            json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        unique.setdefault(key, candidate)
    buckets: defaultdict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for candidate in unique.values():
        bucket = (
            str(candidate.get("category", "")),
            str(candidate.get("paper_id", "")),
            str(candidate.get("entity_class", "")),
        )
        buckets[bucket].append(candidate)
    for values in buckets.values():
        values.sort(
            key=lambda value: hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        )
    selected: list[Mapping[str, Any]] = []
    offsets = {bucket: 0 for bucket in buckets}
    while len(selected) < target_count:
        progressed = False
        for bucket in sorted(buckets):
            index = offsets[bucket]
            if index >= len(buckets[bucket]):
                continue
            selected.append(buckets[bucket][index])
            offsets[bucket] = index + 1
            progressed = True
            if len(selected) >= target_count:
                break
        if not progressed:
            break
    return {
        "schema_version": 1,
        "selection": {
            "method": "sha256-sorted round-robin over category/paper/entity-class buckets",
            "target_count": target_count,
            "candidate_count": len(unique),
            "selected_count": len(selected),
        },
        "examples": [dict(example) for example in selected],
    }


def _model_entity_counts(entities: Sequence[Entity]) -> dict[str, int]:
    """Count predictions by canonical type, retaining unsupported labels."""

    counts: Counter[str] = Counter(
        _canonical_type(entity) or entity.type for entity in entities
    )
    return dict(sorted(counts.items()))


def _model_totals(
    model_name: str,
    papers: Sequence[TargetPaper],
    model_predictions: Mapping[str, Sequence[Entity]],
    predictor_metadata: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate prediction volume and graph diagnostics for one model."""

    by_type: Counter[str] = Counter()
    by_paper: dict[str, int] = {}
    graph: Counter[str] = Counter()
    pair_combinations: Counter[str] = Counter()
    for paper in papers:
        entities = tuple(model_predictions[paper.paper_id])
        by_type.update(_model_entity_counts(entities))
        by_paper[paper.paper_id] = len(entities)
        diagnostics = sentence_cooccurrence_diagnostics(paper.text, entities)
        graph["sentences_containing_at_least_one_entity"] += diagnostics[
            "sentences_containing_at_least_one_entity"
        ]
        graph["sentences_containing_at_least_two_entities"] += diagnostics[
            "sentences_containing_at_least_two_entities"
        ]
        graph["distinct_entity_pairs_cooccurring_within_sentence"] += diagnostics[
            "distinct_entity_pairs_cooccurring_within_sentence"
        ]
        pair_combinations.update(diagnostics["entity_class_combinations"])
    return {
        "entity_count": sum(by_type.values()),
        "entity_count_by_type": dict(sorted(by_type.items())),
        "entity_count_by_paper": dict(sorted(by_paper.items())),
        "graph_sentence_totals": dict(sorted(graph.items())),
        "entity_class_combinations": dict(sorted(pair_combinations.items())),
        "predictor": dict(predictor_metadata.get(model_name, {})),
    }


def build_target_domain_report(
    papers: Sequence[TargetPaper],
    aioner_predictions: Mapping[str, Sequence[Entity]],
    hunflair2_predictions: Mapping[str, Sequence[Entity]],
    *,
    predictor_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    review_target_count: int = 75,
    report_date: str = TARGET_DOMAIN_DATE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build target-domain reconnaissance and its deterministic review packet."""

    expected_ids = {paper.paper_id for paper in papers}
    if (
        set(aioner_predictions) != expected_ids
        or set(hunflair2_predictions) != expected_ids
    ):
        raise ValueError("Both target-domain prediction sets must cover every paper")
    metadata = predictor_metadata or {}
    paper_reports: list[dict[str, Any]] = []
    review_candidates: list[Mapping[str, Any]] = []
    all_shared: list[Alignment] = []
    all_full: list[Alignment] = []
    total_sentences = 0
    for paper in papers:
        aioner = tuple(aioner_predictions[paper.paper_id])
        hunflair2 = tuple(hunflair2_predictions[paper.paper_id])
        _validate_entities(paper.text, aioner, "AIONER")
        _validate_entities(paper.text, hunflair2, "HunFlair2")
        shared = align_entity_predictions(
            aioner, hunflair2, allowed_types=SHARED_COMPARISON_TYPES
        )
        full = align_entity_predictions(aioner, hunflair2)
        all_shared.extend(shared)
        all_full.extend(full)
        review_candidates.extend(_alignment_candidate(paper, item) for item in full)
        review_candidates.extend(_sentence_candidates(paper, aioner, hunflair2))
        total_sentences += paper.sentence_count
        paper_reports.append(
            {
                "paper_id": paper.paper_id,
                "pmid": paper.pmid,
                "pmcid": paper.pmcid,
                "title": paper.title,
                "acquisition_mode": paper.acquisition_mode,
                "text_character_count": len(paper.text),
                "sentence_count": paper.sentence_count,
                "aioner": {
                    "entity_count": len(aioner),
                    "entity_count_by_type": _model_entity_counts(aioner),
                    "graph": sentence_cooccurrence_diagnostics(paper.text, aioner),
                },
                "hunflair2": {
                    "entity_count": len(hunflair2),
                    "entity_count_by_type": _model_entity_counts(hunflair2),
                    "graph": sentence_cooccurrence_diagnostics(paper.text, hunflair2),
                },
                "agreement": {
                    "shared_classes": summarize_alignments(
                        shared, selected_types=SHARED_COMPARISON_TYPES
                    ),
                    "full_schema": summarize_alignments(
                        full,
                        selected_types=SHARED_COMPARISON_TYPES
                        + (SEQUENCE_VARIANT_TYPE,),
                    ),
                },
            }
        )

    shared_summary = summarize_alignments(
        all_shared, selected_types=SHARED_COMPARISON_TYPES
    )
    full_summary = summarize_alignments(
        all_full,
        selected_types=SHARED_COMPARISON_TYPES + (SEQUENCE_VARIANT_TYPE,),
    )
    model_data = {
        "AIONER": _model_totals(
            "AIONER", papers, aioner_predictions, metadata
        ),
        "HunFlair2": _model_totals(
            "HunFlair2", papers, hunflair2_predictions, metadata
        ),
    }
    sequence_variant_count = model_data["AIONER"]["entity_count_by_type"].get(
        SEQUENCE_VARIANT_TYPE, 0
    )
    cellline_counts = {
        model: data["entity_count_by_type"].get("CellLine", 0)
        for model, data in model_data.items()
    }
    report: dict[str, Any] = {
        "evaluation_name": (
            "Target-domain biomedical NER reconnaissance: "
            "AIONER versus HunFlair2"
        ),
        "report_date": report_date,
        "comparison": {
            "models": ["AIONER", "HunFlair2"],
            "shared_comparison_types": list(SHARED_COMPARISON_TYPES),
            "sequence_variant_model": "AIONER",
        },
        "source": {
            "papers_requested": len(papers),
            "papers": [paper.to_dict(include_text=False) for paper in papers],
            "full_text_papers": [
                paper.paper_id
                for paper in papers
                if paper.acquisition_mode == "full_text"
            ],
            "abstract_only_papers": [
                paper.paper_id
                for paper in papers
                if paper.acquisition_mode == "abstract_only"
            ],
            "total_character_count": sum(len(paper.text) for paper in papers),
            "total_sentence_count": total_sentences,
        },
        "models": model_data,
        "agreement": {
            "shared_classes": shared_summary,
            "full_schema": full_summary,
            "disagreement_by_entity_class": shared_summary["by_entity_class"],
            "by_paper": {
                item["paper_id"]: item["agreement"]["shared_classes"]
                for item in paper_reports
            },
        },
        "paper_summaries": paper_reports,
        "sequence_variant": {
            "aioner_prediction_count": sequence_variant_count,
            "hunflair2_prediction_count": 0,
            "by_paper": {
                item["paper_id"]: item["aioner"]["entity_count_by_type"].get(
                    SEQUENCE_VARIANT_TYPE, 0
                )
                for item in paper_reports
            },
            "interpretation": (
                "AIONER-only schema coverage; no gold labels are available "
                "for target papers."
            ),
        },
        "cell_line": {
            "prediction_counts": cellline_counts,
            "shared_exact_agreements": full_summary["by_entity_class"]["CellLine"][
                "counts"
            ][AGREEMENT_EXACT],
            "disagreement_counts": {
                category: full_summary["by_entity_class"]["CellLine"]["counts"][
                    category
                ]
                for category in AGREEMENT_CATEGORIES
                if category != AGREEMENT_EXACT
            },
        },
        "graph_relevant_view": {
            "definition": (
                "Sentence-level entity co-occurrence only; no relation "
                "extraction or relation inference."
            ),
            "models": {
                model: data["graph_sentence_totals"]
                for model, data in model_data.items()
            },
        },
        "review_packet_summary": {
            "target_count": review_target_count,
            "categories": sorted(
                Counter(candidate["category"] for candidate in review_candidates).items()
            ),
        },
        "answers": {
            "exact_agreement_rate_shared_classes": shared_summary[
                "exact_agreement_fraction"
            ],
            "most_disagreement_classes": sorted(
                (
                    (
                        entity_type,
                        sum(
                            count
                            for category, count in details["counts"].items()
                            if category != AGREEMENT_EXACT
                        ),
                    )
                    for entity_type, details in shared_summary[
                        "by_entity_class"
                    ].items()
                ),
                key=lambda item: (-item[1], item[0]),
            ),
            "model_entity_count_difference": (
                model_data["HunFlair2"]["entity_count"]
                - model_data["AIONER"]["entity_count"]
            ),
            "dominant_disagreement_category": max(
                (
                    (category, count)
                    for category, count in shared_summary["counts"].items()
                    if category != AGREEMENT_EXACT
                ),
                key=lambda item: (item[1], item[0]),
                default=(None, 0),
            ),
            "cellline_observation": (
                "CellLine mentions are present in the target predictions; "
                "their materiality is descriptive only because no target "
                "gold exists."
            ),
            "hunflair2_biored_advantage": (
                "Target-domain reconnaissance cannot establish correctness "
                "or transfer of the BioRED ordering without target gold labels."
            ),
        },
        "independence_and_scope": {
            "gold_available": False,
            "precision_recall_f1_reported": False,
            "agreement_is_not_correctness": True,
            "relation_extraction_run": False,
            "llm_run": False,
            "gliner_run": False,
            "craft_status": "deferred",
            "craft_reason": (
                "CRAFT mapping was not added to this target report because "
                "its ontology-specific concept annotations require a separate, "
                "reviewable mapping decision; no broad collapse into BioRED "
                "CellLine or SequenceVariant was made."
            ),
            "future_benchmark_note": (
                "BioNLP 2013 Cancer Genetics is a plausible later "
                "target-adjacent benchmark because it is cancer-focused and "
                "contains gene, simple chemical, organism, and cancer/pathology "
                "annotations. Its training-corpus overlap must be checked "
                "against the exact model artifacts before use."
            ),
        },
        "limitations": [
            "Target papers have no gold annotations; all target-domain findings are reconnaissance evidence.",
            "Exact agreement fraction is exact alignments divided by deterministic one-to-one alignment events.",
            "Boundary and overlap categories are greedy, deterministic diagnostics, not correctness judgments.",
            "Sentence segmentation is a lightweight punctuation-based splitter and preserves canonical-text offsets.",
            "Raw NCBI XML and model prediction caches remain under ignored .cache paths.",
        ],
    }
    review_packet = build_review_packet(
        review_candidates, target_count=review_target_count
    )
    report["review_packet_summary"]["selected_count"] = review_packet["selection"][
        "selected_count"
    ]
    return report, review_packet


def render_target_domain_markdown(report: Mapping[str, Any]) -> str:
    """Render a compact reviewer-facing target-domain reconnaissance report."""

    source = report["source"]
    agreement = report["agreement"]["shared_classes"]
    models = report["models"]
    lines = [
        "# Target-domain biomedical NER reconnaissance",
        "",
        "AIONER and HunFlair2 were compared on the science-team papers using the "
        "same canonical article text. There is no target-domain gold annotation, "
        "so this report does not claim correctness or select a production model.",
        "",
        "## Corpus acquisition",
        "",
        f"- Papers: {source['papers_requested']}",
        f"- Full text: {len(source['full_text_papers'])} "
        f"({', '.join(source['full_text_papers'])})",
        f"- Abstract only: {len(source['abstract_only_papers'])} "
        f"({', '.join(source['abstract_only_papers'])})",
        f"- Characters: {source['total_character_count']}",
        f"- Sentences: {source['total_sentence_count']}",
        "",
        "| Paper | PMID | PMCID | Mode | Characters | Sections |",
        "|---|---:|---|---|---:|---|",
    ]
    for paper in source["papers"]:
        lines.append(
            f"| {paper['paper_id']} | {paper.get('pmid') or ''} | "
            f"{paper.get('pmcid') or ''} | {paper['acquisition_mode']} | "
            f"{paper['text_character_count']} | "
            f"{', '.join(paper['section_availability'])} |"
        )
    lines.extend(
        [
            "",
            "## Agreement on shared classes",
            "",
            f"- Exact agreement events: {agreement['counts']['exact_agreement']}",
            f"- Exact agreement fraction: {agreement['exact_agreement_fraction']}",
            f"- Total alignment events: {agreement['total_alignment_events']}",
            "",
            "| Class | Exact | Type | Boundary | Cross-type | AIONER-only | HunFlair2-only |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for entity_type, values in agreement["by_entity_class"].items():
        counts = values["counts"]
        lines.append(
            f"| {entity_type} | {counts['exact_agreement']} | "
            f"{counts['type_disagreement']} | {counts['boundary_disagreement']} | "
            f"{counts['cross_type_overlap']} | {counts['aioner_only']} | "
            f"{counts['hunflair2_only']} |"
        )
    lines.extend(
        [
            "",
            "## Prediction volume and graph-candidate diagnostics",
            "",
            "| Model | Entities | Sentences with entities | Sentences with >=2 entities | Entity pairs |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for model in ("AIONER", "HunFlair2"):
        data = models[model]
        graph = data["graph_sentence_totals"]
        lines.append(
            f"| {model} | {data['entity_count']} | "
            f"{graph['sentences_containing_at_least_one_entity']} | "
            f"{graph['sentences_containing_at_least_two_entities']} | "
            f"{graph['distinct_entity_pairs_cooccurring_within_sentence']} |"
        )
    lines.extend(
        [
            "",
            "## Schema-specific observations",
            "",
            f"- AIONER SequenceVariant predictions: "
            f"{report['sequence_variant']['aioner_prediction_count']}",
            f"- AIONER CellLine predictions: "
            f"{report['cell_line']['prediction_counts']['AIONER']}",
            f"- HunFlair2 CellLine predictions: "
            f"{report['cell_line']['prediction_counts']['HunFlair2']}",
            f"- CellLine exact agreements: "
            f"{report['cell_line']['shared_exact_agreements']}",
            "",
            "## Interpretation",
            "",
            f"- Dominant shared-class disagreement category: "
            f"{report['answers']['dominant_disagreement_category'][0]} "
            f"({report['answers']['dominant_disagreement_category'][1]} events).",
            "- More predicted entities does not mean more correct entities.",
            "- Model agreement is reconnaissance evidence only; no target-domain "
            "precision, recall, or F1 is reported.",
            "- The BioRED ordering cannot be declared stable or unstable without "
            "target-domain gold labels.",
            "",
            "## Human-review packet",
            "",
            f"- Deterministic selected examples: "
            f"{report['review_packet_summary']['selected_count']}",
            f"- See ner_target_domain_review_packet_{report['report_date']}.json "
            "and its Markdown companion.",
            "",
            "## Deferred / future evidence",
            "",
            f"- CRAFT: {report['independence_and_scope']['craft_status']}. "
            f"{report['independence_and_scope']['craft_reason']}",
            f"- BioNLP 2013 Cancer Genetics: "
            f"{report['independence_and_scope']['future_benchmark_note']}",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


__all__ = [
    "AGREEMENT_AIONER_ONLY",
    "AGREEMENT_BOUNDARY",
    "AGREEMENT_CATEGORIES",
    "AGREEMENT_CROSS_TYPE",
    "AGREEMENT_EXACT",
    "AGREEMENT_HUNFLAIR2_ONLY",
    "AGREEMENT_TYPE",
    "Alignment",
    "SHARED_COMPARISON_TYPES",
    "SEQUENCE_VARIANT_TYPE",
    "TARGET_DOMAIN_DATE",
    "TARGET_PAPER_SPECS",
    "TargetPaper",
    "TextSegment",
    "acquire_target_corpus",
    "align_entity_predictions",
    "build_review_packet",
    "build_target_domain_report",
    "load_target_corpus",
    "parse_pmc_xml",
    "parse_pubmed_xml",
    "render_target_domain_markdown",
    "sentence_cooccurrence_diagnostics",
    "sentence_spans",
    "summarize_alignments",
    "write_target_corpus",
]
