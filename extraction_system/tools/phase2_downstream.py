"""Offline CUDA YELLOW gate over immutable retained Phase 2 NER evidence.

Run with the main environment: python -m tools.phase2_downstream.
Only recording SDK doubles are constructed; socket connections are forbidden.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from biomedical_extractor import llm_relation_extraction as relation_module, llm_paper_roles as role_module
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.graph_contract import contract_resource, input_fingerprints
from biomedical_extractor.graph_profile import _implementation
from biomedical_extractor.hunflair2 import normalize_hunflair2_predictions
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.llm_relation_extraction import LLMRelationExtractor, OpenAIConfig
from biomedical_extractor.llm_paper_roles import LLMPaperRoleExtractor
from biomedical_extractor.relation_extraction import validate_relations
from biomedical_extractor.responses_execution import strict_transport_schema
from tools.phase2_reference import CASES, read, sha_text, write

ROOT = Path(__file__).resolve().parents[1]
CPU = ROOT / '.cache/phase2/20261013T103713Z-6ce48f02'
CUDA = ROOT / '.cache/phase2/20261015T061416Z-cuda'
CPU_SHA = '11a245455e1b067742f3e24daa3338763631fed1dcc3f62d10735f368ccf57fa'
COUNTS = dict(zip((case[0] for case in CASES), (41, 66, 460, 937, 874, 33, 41)))
BASELINES = {'sfpq-passage': 'sfpq.json', 'cbl-passage': 'additional.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def differences(cpu, cuda, path=''):
    """Enumerate exact field differences without ignoring any numeric values."""
    if type(cpu) is not type(cuda):
        return [{'path': path, 'cpu': cpu, 'cuda': cuda}]
    if isinstance(cpu, dict) and cpu.keys() == cuda.keys():
        return [d for key in cpu for d in differences(cpu[key], cuda[key], f'{path}/{key}')]
    if isinstance(cpu, list) and len(cpu) == len(cuda):
        return [d for i, (a, b) in enumerate(zip(cpu, cuda)) for d in differences(a, b, f'{path}/{i}')]
    return [] if cpu == cuda else [{'path': path, 'cpu': cpu, 'cuda': cuda}]


def compare_values(cpu, cuda, score_path):
    changes = differences(cpu, cuda)
    numerical = [d for d in changes if re.fullmatch(score_path, d['path'])
                 and all(type(d[arm]) in (float, int) and math.isfinite(d[arm]) for arm in ('cpu', 'cuda'))]
    return {
        'classification': 'STRUCTURAL' if len(numerical) != len(changes) else 'SCORE_ONLY' if changes else 'IDENTICAL',
        'exact_equal': not changes,
        'score_difference_count': len(numerical),
        'non_score_difference_count': len(changes) - len(numerical),
        'max_abs_score_delta': max((abs(d['cpu'] - d['cuda']) for d in numerical), default=0),
        'cpu_sha256': sha_text(encoded(cpu)), 'cuda_sha256': sha_text(encoded(cuda)),
        'differences': changes,
    }


JSON_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|[^\s]')


def prompt_parts(prompt, marker):
    """Decode the actual builder's JSON and mask only its score number tokens.

    Tokenizing entire strings prevents score-looking text inside entity names or
    the paper from being mistaken for a confidence field. Original prompts are
    retained unchanged; masking exists only in this observational comparison.
    """
    start = prompt.index(marker) + len(marker)
    payload, size = json.JSONDecoder().raw_decode(prompt[start:])
    source = prompt[start:start + size]
    tokens = list(JSON_TOKEN.finditer(source))
    spans = [tokens[i + 2].span() for i, token in enumerate(tokens[:-2])
             if token.group() == '"score"' and tokens[i + 1].group() == ':']
    masked, cursor = '', 0
    for begin, end in spans:
        masked += source[cursor:begin] + '<confidence>'
        cursor = end
    masked += source[cursor:]
    return payload, prompt[:start] + masked + prompt[start + size:], [source[a:b] for a, b in spans]


def compare_requests(cpu, cuda, marker, score_path):
    a, masked_a, literals_a = prompt_parts(cpu['input'], marker)
    b, masked_b, literals_b = prompt_parts(cuda['input'], marker)
    result = compare_values(a, b, score_path)
    envelope_a = {k: v for k, v in cpu.items() if k != 'input'}
    envelope_b = {k: v for k, v in cuda.items() if k != 'input'}
    other_changes = differences(envelope_a, envelope_b)
    # Exact equality after masking proves every remaining character is equal,
    # including whitespace, boundaries, prompt wording, title and full source.
    non_score_text_equal = masked_a == masked_b
    result.update(
        exact_equal=cpu == cuda,
        non_score_characters_equal=non_score_text_equal,
        envelope_equal=not other_changes,
        non_score_difference_count=result['non_score_difference_count'] + len(other_changes) + int(not non_score_text_equal),
        cpu_sha256=sha_text(encoded(cpu)), cuda_sha256=sha_text(encoded(cuda)),
        cpu_prompt_sha256=sha_text(cpu['input']), cuda_prompt_sha256=sha_text(cuda['input']),
        cpu_prompt_characters=len(cpu['input']), cuda_prompt_characters=len(cuda['input']),
        cpu_prompt_utf8_bytes=len(cpu['input'].encode()), cuda_prompt_utf8_bytes=len(cuda['input'].encode()),
        cpu_request_utf8_bytes=len(encoded(cpu).encode()), cuda_request_utf8_bytes=len(encoded(cuda).encode()),
        score_literal_count=len(literals_a),
        different_score_literals=sum(a != b for a, b in zip(literals_a, literals_b)),
        score_literal_length_changes=sum(len(a) != len(b) for a, b in zip(literals_a, literals_b)),
    )
    if result['non_score_difference_count']:
        result['classification'] = 'STRUCTURAL'
    return result


class CaptureComplete(BaseException):
    """Stop after the role request, before fabricating any role judgment."""


class Recorder:
    def __init__(self, response=None):
        self.responses = self
        self.response = response
        self.requests = []

    def create(self, **request):
        require(not self.requests, 'Unexpected repair or second generation')
        self.requests.append(request)
        if self.response is None:
            raise CaptureComplete()
        return SimpleNamespace(id='offline_recording', status='completed', output_text=encoded(self.response))


@contextmanager
def offline():
    # Constructor tripwire plus socket tripwires: never load external credentials
    # or allow a real client/network request if a seam is accidentally bypassed.
    with patch('openai.OpenAI', side_effect=AssertionError('Real provider construction forbidden')), \
         patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')), \
         patch('socket.create_connection', side_effect=AssertionError('Network forbidden')):
        yield


def harness(kind, recorder):
    cls = LLMRelationExtractor if kind == 'relation' else LLMPaperRoleExtractor
    # Exercise the accepted factory and transport with an injected SDK client.
    with patch('openai.OpenAI', return_value=recorder):
        extractor = cls.from_openai(OpenAIConfig(api_key='offline-recording-only'))
    descriptor = contract_resource('baseline-profile.json')[kind]
    require(sha_text(extractor._prompt) == descriptor['prompt_sha256'], f'{kind} prompt changed')
    module = relation_module if kind == 'relation' else role_module
    schema = module._structured_payload_schema()
    require(schema.model_json_schema() == descriptor['semantic_schema'], f'{kind} schema changed')
    require(extractor._background_executor._schema == strict_transport_schema(schema), 'Transport schema changed')
    return extractor


def relation_request(text, entities):
    recorder = Recorder({'relations': []})
    result = harness('relation', recorder).extract_relations(text, entities)
    require(not result.relations and len(recorder.requests) == 1, 'Empty recording response failed')
    return recorder.requests[0]


def mention_key(entity):
    return tuple(entity[k] for k in ('text', 'type', 'start', 'end'))


def replay(packet, entities, baseline):
    """Replay saved scientific relations, rebinding only exact source mentions.

    Historical baseline mention order/IDs differ from fresh retained NER order.
    An exact one-to-one hard-field map preserves endpoints without inventing
    relations or replacing the retained ordering/identity.
    """
    require(all(packet[k] == baseline[k] for k in ('text', 'document_id', 'paper_title')), 'Replay source mismatch')
    by_key = {mention_key(e.to_dict()): e.id for e in entities}
    require(len(by_key) == len(entities) == len(baseline['entities']), 'Replay mentions not one-to-one')
    require(set(by_key) == {mention_key(e) for e in baseline['entities']}, 'Replay mention set mismatch')
    ids = {e['id']: by_key[mention_key(e)] for e in baseline['entities']}
    relations = [{**r, 'source': ids[r['source']], 'target': ids[r['target']]} for r in baseline['relations']]
    recorder = Recorder({'relations': relations})
    role_recorder = Recorder()
    role_harness = harness('roles', role_recorder)
    targets = []

    class SavedNER:
        def extract_entities(self, text):
            require(text == packet['text'], 'Replay NER source mismatch')
            return entities

    class Roles:
        def extract_roles(self, title, text, values):
            targets.extend(t.to_dict() for t in values)
            return role_harness.extract_roles(title, text, values)

    assembly = assemble_document_entities(entities, packet['text'])
    graph = build_graph_result(packet['document_id'], assembly, validate_relations(packet['text'], entities, relations))
    pipeline = LLMExtractionPipeline(SavedNER(), harness('relation', recorder), Roles())
    try:
        completed = pipeline.extract_graph(packet['text'], document_id=packet['document_id'], paper_title=packet['paper_title'])
        require(not graph.unconnected_nodes and completed == graph, 'Expected role capture')
    except CaptureComplete:
        require(bool(graph.unconnected_nodes) and len(role_recorder.requests) == 1, 'Unexpected capture stop')
    require(len(targets) == len(graph.unconnected_nodes), 'Incomplete role targets')
    return {'graph': graph.to_dict(), 'targets': targets, 'request': role_recorder.requests[0] if targets else None,
            'relation_endpoint_map': ids, 'fixed_relations': relations}


def verify_evidence():
    manifest = read(ROOT / 'reports/phase2/manifest.json')
    profile = manifest['cpu_profile']
    require(profile == contract_resource('baseline-profile.json'), 'CPU descriptor changed')
    _implementation(profile)
    provisioning = read(ROOT / 'provisioning/baseline.json')
    for name, expected in provisioning['fixtures'].items():
        require(digest(ROOT / 'tests/fixtures/baseline' / name) == expected, 'Accepted baseline fixture changed')
    require(digest(CPU / 'raw.json') == CPU_SHA, 'CPU raw hash mismatch')
    cases = [c['case_id'] for c in manifest['cases']]
    require(cases == list(COUNTS), 'Frozen case selection/order mismatch')
    raw = [read(run / 'raw.json') for run in (CPU, CUDA)]
    comparison = read(CUDA / 'comparison.json')
    require(comparison['cuda_metadata'] == raw[1]['metadata'], 'CUDA comparison metadata mismatch')
    require(comparison['cpu_reference'] == CPU.name and comparison['cuda_run'] == CUDA.name, 'Comparison run identity mismatch')
    require(set(comparison['cases']) == set(cases), 'Comparison case coverage mismatch')
    for arm in raw:
        require([d['id'] for d in arm['documents']] == cases, 'Raw case coverage/order mismatch')
        for k in ('model_identifier', 'model_revision', 'model_artifact_sha256'):
            require(arm['metadata'][k] == profile['ner'][k], f'Model identity mismatch: {k}')
    packets, arms = [], [[], []]
    for index, entry in enumerate(manifest['cases']):
        packet = read(ROOT / entry['fixture'])
        require(all(packet[k] == entry[k] for k in ('case_id', 'document_id', 'paper_title')), 'Frozen metadata mismatch')
        hashes = input_fingerprints(packet['text'], packet['paper_title'])
        require(hashes == {k: entry[k] for k in hashes} and sha_text(packet['paper_title']) == entry['title_sha256'], 'Frozen fingerprint mismatch')
        require(hashes['source_sha256'] == CASES[index][2], 'Frozen source selection changed')
        packets.append(packet)
        for arm, run in enumerate((CPU, CUDA)):
            document = raw[arm]['documents'][index]
            require(document['text_sha256'] == hashes['source_sha256'], 'Raw source mismatch')
            normalized = [e.to_dict() for e in normalize_hunflair2_predictions(packet['text'], document['predictions'])]
            retained = read(run / f"{entry['case_id']}-entities.json")
            require(retained['case_id'] == packet['case_id'] and retained['document_id'] == packet['document_id'], 'Normalized identity mismatch')
            for key in hashes.keys() & retained.keys():
                require(retained[key] == hashes[key], 'Normalized source hash mismatch')
            require(normalized == retained['entities'], 'Raw/normalized mismatch')
            require(len(normalized) == COUNTS[entry['case_id']], 'Entity count mismatch')
            require(all(type(e['score']) in (int, float) and math.isfinite(e['score']) for e in normalized), 'Non-finite/missing score')
            arms[arm].append(normalized)
        a, b = (arm[-1] for arm in arms)
        measured = compare_values(a, b, r'/\d+/score')
        first = next((i for i, (x, y) in enumerate(zip(a, b)) if x['score'] != y['score']), None)
        first_score = None if first is None else {'index': first, 'cpu': a[first]['score'], 'cuda': b[first]['score'],
                    'entity': {k: a[first][k] for k in ('text', 'type', 'start', 'end')}}
        expected = {'cpu_count': len(a), 'cuda_count': len(b), 'hard_fields_equal': measured['non_score_difference_count'] == 0,
                    'scores_exactly_equal': measured['score_difference_count'] == 0,
                    'score_difference_count': measured['score_difference_count'], 'max_abs_score_difference': measured['max_abs_score_delta'],
                    'first_hard_difference': None, 'first_score_difference': first_score}
        require(comparison['cases'][entry['case_id']] == expected, 'CUDA comparison does not represent retained files')
    inputs = {'documents': [{'id': p['case_id'], 'text': p['text']} for p in packets]}
    require(all(read(run / 'input.json') == inputs for run in (CPU, CUDA)), 'Retained runner input mismatch')
    require(comparison['disposition'] == 'YELLOW' and comparison['provider_submission_attempts'] == 0, 'Unexpected CUDA disposition/usage')
    return packets, arms, raw[1]['metadata']


def analyze():
    evidence_hashes = {str(path.relative_to(ROOT)): digest(path)
                       for run in (CPU, CUDA) for path in sorted(run.iterdir()) if path.is_file()}
    packets, arms, metadata = verify_evidence()
    details = {}
    with offline():
        for index, packet in enumerate(packets):
            case_id = packet['case_id']
            values = [arm[index] for arm in arms]
            entities = [tuple(Entity(**e) for e in value) for value in values]
            assemblies = [assemble_document_entities(es, packet['text']) for es in entities]
            requests = [relation_request(packet['text'], es) for es in entities]
            graphs = [build_graph_result(packet['document_id'], assembly, ()).to_dict() for assembly in assemblies]
            case = {
                'entity_count': len(entities[0]),
                'hard_fields_equal': all(mention_key(a) == mention_key(b) and a['id'] == b['id'] for a, b in zip(*values)),
                'finite_scores_verified': True,
                'ner': compare_values(*values, r'/\d+/score'),
                'assembled_node_count': len(assemblies[0].entities),
                'assembly': compare_values(*(a.to_dict() for a in assemblies), r'/document_entities/\d+/mentions/\d+/score'),
                'relation_request': compare_requests(*requests, 'Supplied entities:\n', r'/\d+/score'),
                'empty_response_graph': compare_values(*graphs, r'/nodes/\d+/mentions/\d+/score'),
                'role': {'coverage': 'unavailable', 'reason': 'No saved relation/topology evidence for this frozen source; no invented topology.'},
            }
            if case_id in BASELINES:
                baseline_path = ROOT / 'tests/fixtures/baseline' / BASELINES[case_id]
                baseline = read(baseline_path)
                replayed = [replay(packet, es, baseline) for es in entities]
                require(replayed[0]['fixed_relations'] == replayed[1]['fixed_relations'], 'Replay topology differs')
                role = {
                    'coverage': 'fixed_baseline_relations', 'baseline_path': str(baseline_path.relative_to(ROOT)),
                    'baseline_sha256': digest(baseline_path), 'saved_relation_count': len(baseline['relations']),
                    'endpoint_rebinding': 'Exact one-to-one (text,type,start,end); retained NER IDs/order preserved.',
                    'target_count': len(replayed[0]['targets']),
                    'targets': compare_values(*(r['targets'] for r in replayed), r'/\d+/mentions/\d+/score'),
                    'graph': compare_values(*(r['graph'] for r in replayed), r'/nodes/\d+/mentions/\d+/score'),
                }
                if replayed[0]['request'] is not None:
                    role['request'] = compare_requests(*(r['request'] for r in replayed), 'Requested entities and all source mentions:\n', r'/\d+/mentions/\d+/score')
                else:
                    require(replayed[1]['request'] is None, 'Role call presence differs')
                    role['request'] = {'classification': 'NOT_NEEDED', 'exact_equal': True, 'non_score_difference_count': 0}
                case['role'] = role
            details[case_id] = {'comparison': case, 'relation_requests': requests}
            if case_id in BASELINES:
                details[case_id]['fixed_topology_replays'] = replayed

    checks = []
    for record in details.values():
        c = record['comparison']
        checks.extend(c[k] for k in ('ner', 'assembly', 'relation_request', 'empty_response_graph'))
        checks.extend(c['role'][k] for k in ('targets', 'graph', 'request') if k in c['role'])
    material = any(c['non_score_difference_count'] for c in checks)
    require(all(digest(ROOT / path) == expected for path, expected in evidence_hashes.items()), 'Original evidence changed during analysis')
    summary = {
        'repository_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'analysis_tool': 'tools/phase2_downstream.py', 'analysis_tool_sha256': digest(Path(__file__)),
        'cpu_run': str(CPU.relative_to(ROOT)), 'cuda_run': str(CUDA.relative_to(ROOT)),
        'cpu_raw_sha256': digest(CPU / 'raw.json'), 'cuda_raw_sha256': digest(CUDA / 'raw.json'),
        'cuda_comparison_sha256': digest(CUDA / 'comparison.json'), 'cuda_metadata': metadata,
        'integrity': 'All seven raw/normalized/input/source identities, counts, finite scores and CUDA comparison verified.',
        'protected_scientific_implementation': 'baseline-profile implementation hashes verified',
        'protected_baseline_fixtures': 'provisioning/baseline.json fixture byte hashes verified',
        'original_evidence_sha256': evidence_hashes,
        'request_hash_encoding': 'Exact prompt UTF-8; request dictionary UTF-8 JSON sorted keys, compact separators.',
        'request_capture': 'Accepted factories, prompt builders and Responses executor; SDK client replaced with recorder. Timeout is the unchanged SDK transport option (60 seconds).',
        'graph_scope': 'Seven empty-response harness graphs plus fixed saved scientific relations for the two passage baselines; no provider-response equivalence claim.',
        'cases': {k: v['comparison'] for k, v in details.items()},
        'provider_submission_count': 0,
        'final_disposition': 'MATERIAL_DOWNSTREAM_DRIFT' if material else 'NUMERIC_ONLY',
        'rationale': 'Structural differences found; stop.' if material else 'Only preserved mention confidence values differ. Assembly/graph identity and fixed-topology role targets are unchanged. Relation and exercised role requests differ only in score literals; YELLOW remains pending user review.',
    }
    return summary, details


def main():
    summary, details = analyze()
    # Full prompts/difference locations stay in new ignored evidence, never in
    # the immutable original runs or the client package.
    output = ROOT / '.cache/phase2' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-downstream')
    require(not output.exists(), 'Analysis evidence already exists; preserve it')
    write(output / 'details.json', details)
    for case in summary['cases'].values():
        for section in (case, case['role']):
            for value in section.values():
                if isinstance(value, dict):
                    value.pop('differences', None)
    summary['detail_artifact'] = str((output / 'details.json').relative_to(ROOT))
    summary['detail_sha256'] = digest(output / 'details.json')
    write(ROOT / 'reports/phase2/downstream-drift.json', summary)
    print(encoded({'disposition': summary['final_disposition'], 'provider_submissions': 0, 'cases': len(summary['cases'])}))


if __name__ == '__main__':
    main()
