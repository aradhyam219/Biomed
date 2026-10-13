"""Freeze Phase 2 sources and capture one actual accepted CPU reference.

Development-only tooling: source acquisition is separate from inference. The
multi-document runner uses case IDs for transport because passage/full-paper
pairs share literal document IDs; scientific document IDs remain in the fixture.
No provider calls, model downloads, or production-profile changes occur here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import uuid

from biomedical_extractor.graph_contract import contract_resource, input_fingerprints, profile_identity
from biomedical_extractor.graph_profile import _implementation, verify_ner_metadata
from biomedical_extractor.hunflair2 import normalize_hunflair2_predictions
from biomedical_extractor.ner_runners import _hunflair2_artifact, _sha256_file, run_hunflair2

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/compatibility'
EVIDENCE = ROOT / 'reports/phase2'
CASES = (
    ('sfpq-passage', 'sfpq.json', '604ce7f15b0ca00853cfc4cc07039d51059792e907d3da07c08be40730fb1b5b'),
    ('cbl-passage', 'additional.json', '558fd77eab8e192fe9b7c625b3186a6b8f1c44bcad0c7430ba3dedc6ffb7c5a6'),
    ('sfpq-full', 'PMCID:PMC11824863', '8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15'),
    ('cbl-full', 'PMCID:PMC8605525', '99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b'),
    ('hmgb1-full', 'PMCID:PMC10770459', '5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4'),
    ('pten-abstract', 'PMID:33652126', '44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6'),
    ('ezh2-abstract', 'PMID:27172794', '50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c'),
)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='utf-8')


def sha_text(value):
    return hashlib.sha256(value.encode('utf-8', errors='strict')).hexdigest()


def freeze(corpus_path):
    """Acquire only the selected source values; fail before writing on mismatch."""
    papers = read(corpus_path)['papers']
    packets = []
    entries = []
    for case_id, source, expected in CASES:
        if source.endswith('.json'):
            path = ROOT / 'tests/fixtures/baseline' / source
            raw = read(path)
            document_id, title = raw['document_id'], raw['paper_title']
            provenance = {'repository_path': path.relative_to(ROOT).as_posix(), 'acquisition_mode': 'preserved_passage'}
        else:
            matches = [paper for paper in papers if paper['paper_id'] == source]
            if len(matches) != 1:
                raise ValueError(f'{case_id}: expected exactly one acquisition entry')
            raw = matches[0]
            document_id, title = raw['paper_id'], raw['title']
            provenance = {key: raw.get(key) for key in ('acquisition_mode', 'source_url', 'source_format', 'source_checksum', 'pmcid', 'pmid')}
            provenance['acquisition_path'] = str(corpus_path)
        text = raw['text']
        if sha_text(text) != expected:
            raise ValueError(f'{case_id}: prerequisite text hash mismatch')
        packet = {'case_id': case_id, 'document_id': document_id, 'paper_title': title, 'text': text}
        entries.append({'case_id': case_id, 'document_id': document_id, 'paper_title': title,
                        'fixture': f'tests/fixtures/compatibility/{case_id}.json',
                        'provenance': provenance, 'title_sha256': sha_text(title),
                        **input_fingerprints(text, title)})
        packets.append(packet)
    profile = contract_resource('baseline-profile.json')
    _implementation(profile)
    manifest = {'starting_revision': 'e9a3184b9e76f12370657dab5f2a6457807a57c2',
                'cases': entries, 'paid_subset': ['sfpq-full', 'cbl-full'],
                'end_to_end_case': 'sfpq-full', 'cpu_profile': profile,
                'cpu_profile_identity': profile_identity(profile),
                'provider_submission_cap': 24, 'shared_repair_cap': 4,
                'sdk_submission_retries': 0,
                'conditional_live_order': ['cpu-run-1', 'cuda-run-1', 'cpu-repeat', 'cuda-repeat']}
    # Never overwrite a previously frozen corpus/configuration with new inputs.
    targets = [(FIXTURES / f"{packet['case_id']}.json", packet) for packet in packets]
    targets.append((EVIDENCE / 'manifest.json', manifest))
    for path, value in targets:
        if path.exists() and read(path) != value:
            raise ValueError(f'Frozen material differs: {path}')
    for path, value in targets:
        if not path.exists():
            write(path, value)
    print(json.dumps({'frozen_cases': len(packets), 'cpu_profile_identity': manifest['cpu_profile_identity']}))


def inventory(executable):
    """Observe all installed distributions without loading scientific packages."""
    code = 'import importlib.metadata as m,json,platform; print(json.dumps({"python":platform.python_version(),"python_implementation":platform.python_implementation(),"packages":sorted([{"name":d.metadata["Name"],"version":d.version} for d in m.distributions()],key=lambda d:d["name"].lower())}))'
    return json.loads(subprocess.check_output([str(executable), '-c', code], text=True, timeout=30))


def capture_cpu():
    """Run fresh offline predictions once, retaining failed-run diagnostics too."""
    if (EVIDENCE / 'cpu-reference.json').exists() or any((ROOT / '.cache/phase2').glob('*/run.json')):
        raise ValueError('CPU capture already attempted; inspect preserved evidence instead of repeating inference')
    manifest = read(EVIDENCE / 'manifest.json')
    profile = manifest['cpu_profile']
    if profile != contract_resource('baseline-profile.json') or profile_identity(profile) != manifest['cpu_profile_identity']:
        raise ValueError('Original CPU descriptor changed')
    _implementation(profile)
    isolated = ROOT / '.cache/hunflair2/runtime/Scripts/python.exe'
    isolated_inventory = inventory(isolated)
    versions = {p['name'].lower().replace('_', '-'): p['version'] for p in isolated_inventory['packages']}
    if isolated_inventory['python'] != profile['ner']['runtime']['python']:
        raise ValueError('Unverified CPU Python')
    for key, distribution in {'flair':'flair', 'pytorch':'torch', 'transformers':'transformers', 'spacy':'spacy', 'scispacy':'scispacy', 'en_core_sci_sm':'en-core-sci-sm'}.items():
        if versions.get(distribution) != profile['ner']['runtime'][key]:
            raise ValueError(f'Unverified CPU distribution: {distribution}')
    cache = ROOT / '.cache/hunflair2'
    artifact, revision = _hunflair2_artifact(cache, profile['ner']['model_identifier'])
    if artifact is None or revision != profile['ner']['model_revision'] or _sha256_file(artifact) != profile['ner']['model_artifact_sha256']:
        raise ValueError('Unverified CPU model artifact/revision')
    packets = []
    for entry in manifest['cases']:
        packet = read(ROOT / entry['fixture'])
        if packet['document_id'] != entry['document_id'] or packet['paper_title'] != entry['paper_title'] or sha_text(packet['paper_title']) != entry['title_sha256'] or input_fingerprints(packet['text'], packet['paper_title']) != {key: entry[key] for key in ('source_sha256', 'extraction_input_sha256')}:
            raise ValueError(f"Frozen identity mismatch: {entry['case_id']}")
        packets.append(packet)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    output = ROOT / '.cache/phase2' / run_id
    output.mkdir(parents=True, exist_ok=False)
    status = {'run_id': run_id, 'status':'started', 'arm':'accepted-windows-cpu',
              'requested_device':'cpu', 'cpu_profile_identity': manifest['cpu_profile_identity'],
              'tool_sha256': python_source_sha256(Path(__file__)),
              'tool_byte_sha256': _sha256_file(Path(__file__)),
              'tool_digest_convention': 'normalized UTF-8 Python source with LF and no BOM',
              'platform': platform.platform(),
              'machine': platform.machine(), 'main_inventory': inventory(Path(sys.executable)),
              'isolated_inventory': isolated_inventory, 'model_artifact_sha256': _sha256_file(artifact),
              'model_revision': revision, 'provider_submission_attempts': 0}
    write(output / 'run.json', status)
    print(json.dumps({'run_id':run_id, 'status':'starting actual offline CPU inference'}), flush=True)
    try:
        run = run_hunflair2([{'id':p['case_id'], 'text':p['text']} for p in packets],
                           input_path=output/'input.json', output_path=output/'raw.json',
                           python_path=isolated, runtime_cache=cache, device='cpu', offline=True)
        status.update(status='inference_completed', actual_metadata=dict(run.metadata),
                      raw_sha256=_sha256_file(output/'raw.json'))
        write(output / 'run.json', status)
        inspect_cpu(output)
        summary = read(EVIDENCE / 'cpu-reference.json')
        if not summary['accepted_cpu_comparator']:
            raise ValueError(summary['profile_verification_failure'])
        status.update(status='completed')
        write(output / 'run.json', status)
    except Exception as error:
        status.update(status='failed', error_type=type(error).__name__, error=str(error))
        write(output / 'run.json', status)
        raise
    print(json.dumps({'status':status['status'], 'run_id':run_id, 'entity_counts':summary['entity_counts']}), flush=True)


def inspect_cpu(output):
    """Retain normalized observations from an existing run without new inference.

    A profile mismatch remains BLOCKED. These values are diagnostic observations,
    never an accepted CPU comparator. Raw and normalized array order is retained.
    """
    if (EVIDENCE / 'cpu-reference.json').exists():
        raise ValueError('Historical CPU summary already exists; use revalidate-cpu')
    output = output.resolve()
    output.relative_to((ROOT / '.cache/phase2').resolve())
    manifest = read(EVIDENCE / 'manifest.json')
    status = read(output / 'run.json')
    raw = read(output / 'raw.json')
    if [document['id'] for document in raw['documents']] != [case['case_id'] for case in manifest['cases']]:
        raise ValueError('Runtime document order/count mismatch')
    counts = {}
    for case, document in zip(manifest['cases'], raw['documents']):
        packet = read(ROOT / case['fixture'])
        hashes = input_fingerprints(packet['text'], packet['paper_title'])
        if packet['document_id'] != case['document_id'] or packet['paper_title'] != case['paper_title'] or hashes != {key:case[key] for key in hashes} or document['text_sha256'] != hashes['source_sha256']:
            raise ValueError('Frozen/runtime input identity mismatch')
        entities = normalize_hunflair2_predictions(packet['text'], document['predictions'])
        if any(entity.score is not None and not math.isfinite(entity.score) for entity in entities):
            raise ValueError('Non-finite CPU score')
        write(output / f"{case['case_id']}-entities.json", {
            'case_id':case['case_id'], 'document_id':case['document_id'], **hashes,
            'entities':[entity.to_dict() for entity in entities]})
        counts[case['case_id']] = len(entities)
    try:
        _implementation(manifest['cpu_profile'])
        verify_ner_metadata(raw['metadata'], manifest['cpu_profile'])
        verified, failure = True, None
    except ValueError as error:
        verified, failure = False, str(error)
    summary = {
        'disposition':'READY_FOR_REVIEW' if verified else 'BLOCKED',
        'scope':'CPU reference prerequisite only; no Linux/CUDA compatibility conclusion',
        'run_id':status['run_id'], 'accepted_cpu_comparator':verified,
        'cpu_profile_identity':manifest['cpu_profile_identity'],
        'observed_model':{key:raw['metadata'][key] for key in ('model_identifier','model_revision','model_artifact_sha256')},
        'actual_runtime':raw['metadata']['runtime'], 'entity_counts':counts,
        'source_slices_validated':True, 'finite_scores_validated':True,
        'profile_verification_failure':failure,
        'runtime_descriptor_differences':{key:{'expected':value,'observed':raw['metadata']['runtime'].get(key)} for key,value in manifest['cpu_profile']['ner']['runtime'].items() if key != 'offset_mechanics' and raw['metadata']['runtime'].get(key) != value},
        'platform':status['platform'], 'machine':status['machine'],
        'evidence_directory':output.relative_to(ROOT).as_posix(),
        'raw_sha256':_sha256_file(output/'raw.json'),
        'capture_tool_sha256':status['tool_sha256'],
        'inventories':'Complete main/isolated installed inventories are preserved in run.json in the ignored evidence directory.',
        'provider_submission_attempts':0,
    }
    write(EVIDENCE / 'cpu-reference.json', summary)
    print(json.dumps({'disposition':summary['disposition'], 'accepted_cpu_comparator':verified, 'entity_counts':counts}))


def python_source_sha256(path):
    """Attest Python source only: UTF-8-sig decode, CRLF/CR to LF, UTF-8 encode."""
    source = path.read_bytes().decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def verify_capture_tool(path, *, source_sha256, byte_sha256):
    """Require both declared attestations of the retained capture wrapper."""
    if python_source_sha256(path) != source_sha256 or _sha256_file(path) != byte_sha256:
        raise ValueError('Retained capture-tool identity mismatch')


def revalidate_cpu(output):
    """Verify the retained CPU run without modifying its historical evidence.

    Raw/input/tool digests and normalized values are checked before acceptance.
    Captured inventory supplies distribution evidence; no interpreter inference,
    downloads, installation, or provider submissions occur in this operation.
    """
    output = output.resolve()
    output.relative_to((ROOT / '.cache/phase2').resolve())
    manifest = read(EVIDENCE / 'manifest.json')
    reference = read(EVIDENCE / 'cpu-reference.json')
    status = read(output / 'run.json')
    profile = manifest['cpu_profile']
    if profile != contract_resource('baseline-profile.json') or profile_identity(profile) != manifest['cpu_profile_identity']:
        raise ValueError('Original CPU descriptor or identity changed')
    if status['run_id'] != reference['run_id'] or status['cpu_profile_identity'] != manifest['cpu_profile_identity']:
        raise ValueError('Retained run/profile identity mismatch')
    if _sha256_file(output/'raw.json') != reference['raw_sha256']:
        raise ValueError('Retained raw-output digest mismatch')
    if status['tool_sha256'] != reference['capture_tool_sha256']:
        raise ValueError('Recorded capture-tool identities disagree')
    capture_bytes = '167dbab44af49c49fce7797345995d361aefa7f2df1c8c5866a95cf90a6b399d'
    verify_capture_tool(output/'capture-tool.py', source_sha256=status['tool_sha256'], byte_sha256=capture_bytes)
    inventory = status['isolated_inventory']
    versions = {}
    for package in inventory['packages']:
        name = package['name'].lower().replace('_', '-')
        if name in versions:
            raise ValueError('Duplicate captured distribution')
        versions[name] = package['version']
    for field in ('python', 'python_implementation'):
        if inventory.get(field) != profile['ner']['runtime'][field]:
            raise ValueError(f'Captured inventory mismatch: {field}')
    for field, distribution in {'flair':'flair', 'pytorch':'torch', 'transformers':'transformers', 'spacy':'spacy', 'scispacy':'scispacy', 'en_core_sci_sm':'en-core-sci-sm'}.items():
        if versions.get(distribution) != profile['ner']['runtime'][field]:
            raise ValueError(f'Captured inventory mismatch: {distribution}')
    _implementation(profile)
    raw = read(output/'raw.json')
    verify_ner_metadata(raw['metadata'], profile, pytorch_distribution=versions['torch'])
    for field in ('model_revision', 'model_artifact_sha256'):
        if status[field] != profile['ner'][field]:
            raise ValueError(f'Captured model mismatch: {field}')
    if status['requested_device'] != 'cpu':
        raise ValueError('Captured requested device mismatch')
    if [case['case_id'] for case in manifest['cases']] != [case[0] for case in CASES]:
        raise ValueError('Frozen case selections changed')
    if [document['id'] for document in raw['documents']] != [case[0] for case in CASES]:
        raise ValueError('Runtime case order/count mismatch')
    expected_inputs, counts = [], {}
    for case, document, (_, _, text_digest) in zip(manifest['cases'], raw['documents'], CASES):
        packet = read(ROOT/case['fixture'])
        hashes = input_fingerprints(packet['text'], packet['paper_title'])
        if (packet['case_id'] != case['case_id'] or packet['document_id'] != case['document_id']
                or packet['paper_title'] != case['paper_title'] or sha_text(packet['paper_title']) != case['title_sha256']
                or hashes != {key:case[key] for key in hashes}
                or hashes['source_sha256'] != text_digest or document['text_sha256'] != text_digest):
            raise ValueError('Frozen/runtime input identity mismatch')
        expected_inputs.append({'id':case['case_id'], 'text':packet['text']})
        entities = normalize_hunflair2_predictions(packet['text'], document['predictions'])
        if any(entity.score is not None and not math.isfinite(entity.score) for entity in entities):
            raise ValueError('Non-finite retained score')
        expected = {'case_id':case['case_id'], 'document_id':case['document_id'], **hashes,
                    'entities':[entity.to_dict() for entity in entities]}
        if read(output/f"{case['case_id']}-entities.json") != expected:
            raise ValueError('Retained normalized entity values/order changed')
        counts[case['case_id']] = len(entities)
    if read(output/'input.json') != {'documents':expected_inputs}:
        raise ValueError('Retained runner input differs from frozen sources')
    result = {
        'disposition':'BLOCKED', 'cpu_reference_prerequisite':'verified',
        'linux_nvidia_target':'still_missing', 'cuda_compatibility':'not_established',
        'profile_promotion':'not_performed', 'accepted_cpu_comparator':True,
        'run_id':status['run_id'], 'revalidated_at':datetime.now(timezone.utc).isoformat(),
        'cpu_profile_identity':manifest['cpu_profile_identity'],
        'historical_capture':{'status':status['status'], 'error_type':status.get('error_type'), 'error':status.get('error'), 'run_json_byte_sha256':_sha256_file(output/'run.json'), 'original_summary_byte_sha256':_sha256_file(EVIDENCE/'cpu-reference.json')},
        'capture_tool':{'normalized_source_sha256':status['tool_sha256'], 'byte_sha256':capture_bytes,
                        'source_convention':'Decode UTF-8 removing optional BOM; normalize CRLF and CR to LF; encode UTF-8 without BOM; SHA-256.'},
        'revalidation_tool':{'path':'tools/phase2_reference.py', 'normalized_source_sha256':python_source_sha256(Path(__file__)), 'byte_sha256':_sha256_file(Path(__file__))},
        'verification_layer_source_sha256':python_source_sha256(ROOT/'src/biomedical_extractor/graph_profile.py'),
        'pytorch_distribution':'2.14.0', 'pytorch_module_build':raw['metadata']['runtime']['pytorch'],
        'actual_device':raw['metadata']['runtime']['device'], 'cuda_available':raw['metadata']['runtime']['cuda_available'], 'cuda_runtime_version':raw['metadata']['runtime']['cuda_version'],
        'raw_byte_sha256':reference['raw_sha256'], 'entity_counts':counts,
        'all_seven_input_identities_verified':True, 'normalized_values_and_order_preserved':True,
        'source_spans_and_finite_scores_verified':True, 'protected_scientific_hashes_verified':True,
        'provider_attempts':0, 'repair_attempts':0,
    }
    write(EVIDENCE/'cpu-revalidation.json', result)
    print(json.dumps({'cpu_reference_prerequisite':'verified', 'disposition':'BLOCKED', 'entity_counts':counts}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    acquire = sub.add_parser('freeze')
    acquire.add_argument('--corpus', type=Path, required=True)
    sub.add_parser('capture-cpu')
    inspect = sub.add_parser('inspect-cpu')
    inspect.add_argument('--run-directory', type=Path, required=True)
    revalidate = sub.add_parser('revalidate-cpu')
    revalidate.add_argument('--run-directory', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze(args.corpus)
    elif args.action == 'capture-cpu':
        capture_cpu()
    elif args.action == 'inspect-cpu':
        inspect_cpu(args.run_directory)
    else:
        revalidate_cpu(args.run_directory)


if __name__ == '__main__':
    main()
