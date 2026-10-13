"""Versioned graph delivery and offline serialized validation.

The unchanged GraphResult owns scientific payload construction. This boundary
adds exact input identity and validated release/profile provenance; it never
repairs serialized data. Graph-only checks cannot establish scientific truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata, resources
import json
import math
from pathlib import Path
import re
import subprocess

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

from .graph import GraphResult
from .paper_roles import _is_species_type


class GraphValidationError(ValueError):
    """A local field/record violates the delivery contract."""


def contract_resource(name: str) -> dict | list:
    """Load packaged contract material independently of the working directory."""
    return json.loads(resources.files(__package__).joinpath('contract_resources', name).read_text(encoding='utf-8'))


def input_fingerprints(text: str, paper_title: str = '') -> dict[str, str]:
    """Hash exact strict UTF-8 text and length-framed text/title; never normalize."""
    if not isinstance(text, str) or not isinstance(paper_title, str):
        raise GraphValidationError('text and paper_title must be Unicode strings')
    try:
        t, h = text.encode('utf-8'), paper_title.encode('utf-8')
        framed = b'EES-INPUT-V1' + len(t).to_bytes(8, 'big') + t + len(h).to_bytes(8, 'big') + h
    except (UnicodeEncodeError, OverflowError) as error:
        raise GraphValidationError('text/title must have valid Unicode and UINT64 UTF-8 lengths') from error
    return {'source_sha256': sha256(t).hexdigest(), 'extraction_input_sha256': sha256(framed).hexdigest()}


def _plain(value, path='$'):
    # json.dumps accepts tuples and integer object keys; the wire contract does not.
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeEncodeError as error:
            raise GraphValidationError(f'{path}: malformed Unicode') from error
        return
    if type(value) is list:
        for i, item in enumerate(value):
            _plain(item, f'{path}[{i}]')
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for key, item in value.items():
            _plain(item, f'{path}.{key}')
        return
    raise GraphValidationError(f'{path}: requires plain finite JSON data')


@dataclass(frozen=True)
class ValidationResult:
    """Classification and the explicitly limited scope of successful validation."""
    format: str
    source_checked: bool
    limitation: str


def validate_graph(data: dict, *, text: str | None = None, paper_title: str = '') -> ValidationResult:
    """Validate plain legacy/v1 data without mutation or network resolution.

    Supplying exact text/title also checks hashes, code-point spans and verbatim
    quotes. Assertions, qualifiers and role prose remain permitted paraphrases.
    """
    _plain(data)
    versioned = isinstance(data, dict) and 'schema_version' in data
    schema = contract_resource('graph-v1.schema.json' if versioned else 'graph-legacy.schema.json')
    checker = FormatChecker()

    @checker.checks('date-time')
    def utc_timestamp(value):
        if not isinstance(value, str):
            return True  # Type errors belong to the schema's type constraint.
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z', value):
            return False
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return False
        return True

    validator = Draft202012Validator(schema, format_checker=checker, registry=Registry())
    error = next(validator.iter_errors(data), None)
    if error:
        path = '$' + ''.join(f'[{p}]' if isinstance(p, int) else f'.{p}' for p in error.absolute_path)
        raise GraphValidationError(f'{path}: {error.message}')
    fingerprints = input_fingerprints(text, paper_title) if text is not None else None
    if text is None and paper_title != '':
        raise GraphValidationError('paper_title requires source text context')
    if fingerprints and versioned:
        for key, expected in fingerprints.items():
            if data['provenance'][key] != expected:
                raise GraphValidationError(f'$.provenance.{key}: exact input hash mismatch')
    nodes, edges = data['nodes'], data['edges']
    ids, mention_ids = set(), set()
    for kind, records in [('nodes', nodes), ('edges', edges)]:
        for i, record in enumerate(records):
            if record['id'] in ids:
                raise GraphValidationError(f'$.{kind}[{i}].id: duplicate element ID {record["id"]!r}')
            ids.add(record['id'])
    node_ids = {node['id'] for node in nodes}
    connected = set()
    for i, edge in enumerate(edges):
        for key in ('source', 'target'):
            if edge[key] not in node_ids:
                raise GraphValidationError(f'$.edges[{i}].{key}: dangling endpoint')
            connected.add(edge[key])
        if text is not None:
            for j, evidence in enumerate(edge['evidence']):
                if evidence['text'] not in text:
                    raise GraphValidationError(f'$.edges[{i}].evidence[{j}].text: not a source substring')
                if evidence['surface_form'] is not None and evidence['surface_form'] not in text:
                    raise GraphValidationError(f'$.edges[{i}].evidence[{j}].surface_form: not a source substring')
    for i, node in enumerate(nodes):
        for j, mention in enumerate(node['mentions']):
            path = f'$.nodes[{i}].mentions[{j}]'
            if mention['id'] in mention_ids:
                raise GraphValidationError(f'{path}.id: duplicate mention membership')
            mention_ids.add(mention['id'])
            if type(mention['start']) is not int or type(mention['end']) is not int:
                raise GraphValidationError(f'{path}: offsets must be JSON integers')
            if not mention['start'] < mention['end']:
                raise GraphValidationError(f'{path}.end: must exceed start')
            if text is not None and (mention['end'] > len(text) or text[mention['start']:mention['end']] != mention['text']):
                raise GraphValidationError(f'{path}: invalid Unicode code-point source slice')
        role = node.get('paper_role')
        if role:
            if node['id'] in connected:
                raise GraphValidationError(f'$.nodes[{i}].paper_role: requires degree zero')
            if _is_species_type(node['type']) and role['category'] != 'contextual':
                raise GraphValidationError(f'$.nodes[{i}].paper_role.category: species requires contextual')
            if text is not None:
                for j, quote in enumerate(role['evidence']):
                    if quote not in text:
                        raise GraphValidationError(f'$.nodes[{i}].paper_role.evidence[{j}]: not a source substring')
    return ValidationResult('v1' if versioned else 'legacy', text is not None,
        'Does not certify scientific entailment, completeness or producer authenticity.' if text is not None else
        'Structure/integrity only; source grounding, entailment, completeness and producer authenticity are unchecked.')


@dataclass(frozen=True)
class CacheEligibility:
    """Explicit pure reuse decision; invalid and legacy artifacts never hit."""
    eligible: bool
    reason: str


def cache_eligibility(data: dict, *, document_id: str, text: str, paper_title: str = '') -> CacheEligibility:
    """Require valid v1 data and exact literal ID/text/title, independent of release."""
    try:
        _document_id(document_id)
        input_fingerprints(text, paper_title)
        validation = validate_graph(data, text=text, paper_title=paper_title)
    except (GraphValidationError, TypeError, ValueError) as error:
        return CacheEligibility(False, f'invalid/ineligible: {error}')
    if validation.format == 'legacy':
        return CacheEligibility(False, 'legacy has no verifiable input provenance')
    if data['document']['id'] != document_id:
        return CacheEligibility(False, 'literal document ID mismatch')
    return CacheEligibility(True, 'exact document/text/title match')


def _document_id(value):
    if not isinstance(value, str) or not value.strip():
        raise GraphValidationError('document.id must be a nonblank literal string')
    value.encode('utf-8')


@dataclass(frozen=True)
class ExportContext:
    """Explicit release and recorded effective configuration for export/replay.

    Explicit context is an attestation by the caller, not producer authentication.
    Live callers should use prepare_graph_export and verify_graph_profile.
    """
    extractor_version: str
    build_revision: str
    configuration: dict

    def __post_init__(self):
        try:
            installed = metadata.version('biomedical-extractor')
        except metadata.PackageNotFoundError as error:
            raise GraphValidationError('installed extractor release metadata unavailable') from error
        if self.extractor_version != installed:
            raise GraphValidationError('extractor_version must agree with installed release')
        if not isinstance(self.build_revision, str) or not re.fullmatch('[0-9a-f]{40}', self.build_revision):
            raise GraphValidationError('build_revision must be a full lowercase Git commit SHA')
        profile_identity(self.configuration)


def profile_identity(configuration: dict) -> str:
    """Bind the sole supported immutable profile to its complete recorded descriptor."""
    _plain(configuration)
    expected = contract_resource('baseline-profile.json')
    if configuration != expected:
        raise GraphValidationError('unsupported effective extraction configuration for v1 baseline profile')
    return 'ees-' + sha256(json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def release_context() -> ExportContext:
    """Read wheel build identity without Git; clean source checkouts may use Git.

    Wheel source digests detect modified installed production files. A checkout
    without packaged identity must be clean before its revision is advertised.
    """
    package = Path(__file__).parent
    build_resource = package/'contract_resources'/'release.json'
    if build_resource.is_file():
        build = json.loads(build_resource.read_text(encoding='utf-8'))
        for name, expected in build['source_sha256'].items():
            if sha256((package/name).read_bytes()).hexdigest() != expected:
                raise GraphValidationError(f'modified installed production resource: {name}')
        version, revision = build['version'], build['revision']
    else:
        root = package.parent.parent
        if not (root/'pyproject.toml').is_file():
            raise GraphValidationError('required packaged build metadata unavailable')
        try:
            status = subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--','.'], cwd=root, text=True)
            if status.strip():
                raise GraphValidationError('modified/unidentified source build; commit changes or supply explicit test context')
            revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
            import tomllib
            version = tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
        except (OSError, subprocess.CalledProcessError) as error:
            raise GraphValidationError('required clean source build metadata unavailable') from error
    return ExportContext(version, revision, contract_resource('baseline-profile.json'))


def export_graph(graph: GraphResult, *, text: str, paper_title: str = '', context: ExportContext,
                 generated_at: str | None = None) -> dict:
    """Export a completed graph once, preserving payload exactly and checking source."""
    if not isinstance(graph, GraphResult):
        raise TypeError('graph must be GraphResult')
    # Recheck mutable recorded configuration at the boundary.
    context.__post_init__()
    hashes = input_fingerprints(text, paper_title)
    stamp = generated_at if generated_at is not None else datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    data = {'schema_version':'1.0', **graph.to_dict(), 'provenance':{
        'extractor_version':context.extractor_version, 'build_revision':context.build_revision,
        'extraction_profile':profile_identity(context.configuration), **hashes, 'generated_at':stamp}}
    validate_graph(data, text=text, paper_title=paper_title)
    return data


def graph_json(data: dict, *, indent: int | None = 2) -> str:
    """Validate and strictly reserialize existing data, preserving generation time."""
    validate_graph(data)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=indent, allow_nan=False)
