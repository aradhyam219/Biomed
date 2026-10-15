"""One authorized SFPQ CPU-then-CUDA live RE comparison; never NER or roles.

Offline preparation: python -m tools.phase2_sfpq_live
Live execution: python -m tools.phase2_sfpq_live --live
Credentials must be supplied externally through the accepted environment path.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.graph_contract import contract_resource
from biomedical_extractor.graph_profile import _provider
from biomedical_extractor.llm_relation_extraction import LLMRelationExtractor, OpenAIConfig
from tools import phase2_downstream as gate

ROOT = gate.ROOT
LEDGER = ROOT / 'reports/phase2/provider-ledger.json'
REPORT = ROOT / 'reports/phase2/sfpq-live-comparison.json'
EXPERIMENT = 'sfpq-cpu-cuda-live-1'


def now():
    return datetime.now(timezone.utc).isoformat()


def safe(value, secrets=()):
    """Serialize explicit evidence values, never clients/headers/exception text."""
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, '[REDACTED]')
        return value
    if isinstance(value, dict):
        return {k: '[REDACTED]' if k.casefold() in {'authorization', 'api_key', 'access_token', 'headers'}
                else safe(v, secrets) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v, secrets) for v in value]
    return value


def save(path, value, secrets=()):
    """Durable replacement; ledger reservations reach disk before network I/O."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(safe(value, secrets), stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


@contextmanager
def exclusive_run():
    path = ROOT / '.cache/phase2/sfpq-live.lock'
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class Budget:
    def __init__(self, path, run_id):
        self.path, self.run_id = path, run_id
        self.value = gate.read(path)
        gate.require(self.value['generation_submission_cap'] == 24 and self.value['shared_output_repair_cap'] == 4, 'Budget caps changed')
        gate.require(self.value['attempts_consumed'] == len(self.value['submission_attempts']) == 0
                     and self.value['repairs_consumed'] == 0, 'Existing submissions: this contract cannot be restarted')

    def reserve(self, arm, generation):
        entries = self.value['submission_attempts']
        previous = [e for e in entries if e['arm'] == arm]
        gate.require(arm in ('cpu', 'cuda') and generation == len(previous) + 1, 'Repeated/out-of-order generation')
        gate.require(generation <= 3, 'Production repair limit exceeded')
        gate.require(arm != 'cuda' or any(e['arm'] == 'cpu' for e in entries), 'CPU must precede CUDA')
        gate.require(arm != 'cpu' or not any(e['arm'] == 'cuda' for e in entries), 'CPU after CUDA forbidden')
        repair = generation > 1
        gate.require(len(entries) < 6 and len(entries) < 24, 'Submission budget exhausted')
        gate.require(not repair or self.value['repairs_consumed'] < 4, 'Shared repair budget exhausted')
        entry = {'experiment': EXPERIMENT, 'run_id': self.run_id, 'arm': arm, 'generation': generation,
                 'repair': repair, 'reserved_at': now(), 'submission_state': 'uncertain_until_observed'}
        entries.append(entry)
        self.value.update(attempts_consumed=len(entries), repairs_consumed=sum(e['repair'] for e in entries),
                          status='live_experiment_in_progress')
        save(self.path, self.value)
        return entry

    def observed(self, entry, **values):
        entry.update(values)
        save(self.path, self.value)


def prepare(config):
    downstream = gate.read(ROOT / 'reports/phase2/downstream-drift.json')
    gate.require(downstream['final_disposition'] == 'NUMERIC_ONLY', 'Offline gate changed')
    profile = contract_resource('baseline-profile.json')
    gate.require(all(getattr(config, k) == v for k, v in profile['relation']['configuration'].items()), 'Accepted relation configuration differs')
    gate.require(config.base_url in (None, 'https://api.openai.com/v1'), 'Unexpected provider endpoint')
    packets, arms, _ = gate.verify_evidence()
    index = next(i for i, p in enumerate(packets) if p['case_id'] == 'sfpq-full')
    packet = packets[index]
    entities = [tuple(Entity(**e) for e in arm[index]) for arm in arms]
    assemblies = [assemble_document_entities(es, packet['text']) for es in entities]
    with gate.offline():
        requests = [gate.relation_request(packet['text'], es) for es in entities]
    comparison = gate.compare_requests(*requests, 'Supplied entities:\n', r'/\d+/score')
    assembly = gate.compare_values(*(a.to_dict() for a in assemblies), r'/document_entities/\d+/mentions/\d+/score')
    gate.require(comparison['classification'] == 'SCORE_ONLY' and comparison['non_score_difference_count'] == 0
                 and comparison['different_score_literals'] == 308
                 and comparison['max_abs_score_delta'] == 1.2576580047607422e-05
                 and assembly['non_score_difference_count'] == 0, 'Pre-provider scientific input drift')
    previous = downstream['cases']['sfpq-full']['relation_request']
    gate.require(all(comparison[k] == previous[k] for k in ('cpu_sha256', 'cuda_sha256')), 'Offline request identities changed')
    return packet, entities, assemblies, requests, {k: v for k, v in comparison.items() if k != 'differences'}


class RecordedResponses:
    def __init__(self, responses, budget, arm, output, expected, secrets):
        self.responses, self.budget, self.arm = responses, budget, arm
        self.output, self.expected, self.secrets = output, expected, secrets
        self.generation = 0
        self.entry = None

    def capture(self, response, name):
        value = response.model_dump(mode='json')
        value['output_text'] = response.output_text
        save(self.output / f'generation-{self.generation}' / name, value, self.secrets)
        if response.status == 'completed':
            try:
                parsed = json.loads(response.output_text)
            except (ValueError, TypeError):
                parsed = {'parse_status': 'invalid_json'}
            save(self.output / f'generation-{self.generation}/parsed-output.json', parsed, self.secrets)
        self.budget.observed(self.entry, response_id=response.id, submission_state='response_observed',
                             provider_status=response.status, last_observed_at=now())

    def create(self, **request):
        if self.generation == 0:
            gate.require(request == self.expected, 'Actual initial request differs from verified request')
        gate.require(safe(request, self.secrets) == request, 'Secret detected in provider request')
        self.generation += 1
        save(self.output / f'generation-{self.generation}/request.json', request)
        self.entry = self.budget.reserve(self.arm, self.generation)
        try:
            response = self.responses.create(**request)
        except BaseException as error:
            self.budget.observed(self.entry, error_type=type(error).__name__, failed_at=now())
            raise
        self.capture(response, 'create-response.json')
        return response

    def retrieve(self, response_id, **kwargs):
        response = self.responses.retrieve(response_id, **kwargs)
        if response.status not in ('queued', 'in_progress'):
            self.capture(response, 'terminal-response.json')
        return response

    def cancel(self, response_id, **kwargs):
        response = self.responses.cancel(response_id, **kwargs)
        self.capture(response, 'cancel-response.json')
        return response


def compare_relations(packet, assemblies, results):
    """Conservative deterministic alignment; ambiguous multiples stay explicit."""
    values = [[r.to_dict() for r in result.relations] for result in results]
    maps = [a.mention_to_document_entity for a in assemblies]
    groups = []
    for relations, mapping in zip(values, maps):
        grouped = defaultdict(list)
        for i, relation in enumerate(relations):
            grouped[(mapping[relation['source']], mapping[relation['target']], relation['negated'])].append(i)
        groups.append(grouped)
    aligned, unmatched = [], [set(range(len(v))) for v in values]
    for key in sorted(set(groups[0]) & set(groups[1])):
        a, b = groups[0][key], groups[1][key]
        for i in a:
            candidates = [j for j in b if j in unmatched[1] and values[0][i] == values[1][j]]
            if len(candidates) == 1:
                j = candidates[0]
                aligned.append({'cpu_index': i, 'cuda_index': j, 'method': 'exact_relation'})
                unmatched[0].remove(i); unmatched[1].remove(j)
        for field in ('predicate', 'evidence'):
            for i in a:
                if i not in unmatched[0]:
                    continue
                candidates = [j for j in b if j in unmatched[1] and values[0][i][field] == values[1][j][field]]
                if len(candidates) == 1:
                    j = candidates[0]
                    reverse = [k for k in a if k in unmatched[0] and values[0][k][field] == values[1][j][field]]
                    if len(reverse) == 1:
                        aligned.append({'cpu_index': i, 'cuda_index': j, 'method': f'unique_pair_negation_and_{field}'})
                        unmatched[0].remove(i); unmatched[1].remove(j)
        a, b = [i for i in a if i in unmatched[0]], [j for j in b if j in unmatched[1]]
        if len(a) == len(b) == 1:
            aligned.append({'cpu_index': a[0], 'cuda_index': b[0], 'method': 'unique_directed_node_pair_and_negation'})
            unmatched[0].remove(a[0]); unmatched[1].remove(b[0])
    for pair in aligned:
        a, b = values[0][pair['cpu_index']], values[1][pair['cuda_index']]
        pair['field_differences'] = gate.differences(a, b)
    topology = []
    for relations, mapping in zip(values, maps):
        counts = Counter((mapping[r['source']], mapping[r['target']]) for r in relations)
        topology.append(counts)
    pairs = sorted(set(topology[0]) | set(topology[1]))
    grounding = []
    for relations in values:
        records = []
        for i, r in enumerate(relations):
            evidence, cursor, locations = r['evidence'], 0, []
            while (start := packet['text'].find(evidence, cursor)) >= 0:
                locations.append({'start': start, 'end': start + len(evidence)})
                cursor = start + 1
            records.append({'index': i, 'exact_source_substring': bool(locations), 'source_locations': locations})
        grounding.append(records)
    graphs = [build_graph_result(packet['document_id'], assembly, result).to_dict() for assembly, result in zip(assemblies, results)]
    return {
        'relation_counts': [len(v) for v in values], 'exact_output_equal': values[0] == values[1],
        'validated_relations': dict(zip(('cpu', 'cuda'), values)), 'aligned_relations': aligned,
        'cpu_unaligned_indices': sorted(unmatched[0]), 'cuda_unaligned_indices': sorted(unmatched[1]),
        'alignment_rule': 'Within assembled directed pair and negation: exact relation, unique reciprocal predicate/evidence, then unique remaining pair. Ambiguous multiples remain unaligned.',
        'unaligned_candidates': [{'cpu_index': i, 'cuda_indices': [j for j in sorted(unmatched[1])
                                 if maps[0][values[0][i]['source']] == maps[1][values[1][j]['source']]
                                 and maps[0][values[0][i]['target']] == maps[1][values[1][j]['target']]]} for i in sorted(unmatched[0])],
        'endpoint_pairs': [{'source': a, 'target': b, 'self_edge': a == b, 'cpu_relation_count': topology[0][a, b],
                            'cuda_relation_count': topology[1][a, b]} for a, b in pairs],
        'cpu_only_endpoint_pairs': [list(p) for p in pairs if p not in topology[1]],
        'cuda_only_endpoint_pairs': [list(p) for p in pairs if p not in topology[0]],
        'shared_endpoint_pair_count': len(set(topology[0]) & set(topology[1])),
        'negation_counts': [dict(Counter(str(r['negated']) for r in arm)) for arm in values],
        'negation_by_endpoint_pair': [{'source': a, 'target': b, **{
            arm: dict(Counter(str(r['negated']) for r in relations if mapping[r['source']] == a and mapping[r['target']] == b))
            for arm, relations, mapping in zip(('cpu', 'cuda'), values, maps)}} for a, b in pairs],
        'grounding': dict(zip(('cpu', 'cuda'), grounding)),
        'grounding_limit': 'Substring grounding is mechanical; scientific support and qualifier equivalence require source review.',
        'assembled_node_labels': {n['id']: {'label': n['label'], 'type': n['type'], 'aliases': n['aliases']} for n in graphs[0]['nodes']},
        'graph_topology': {arm: [{'source': edge['source'], 'target': edge['target'], 'predicate': edge['predicate'],
                                 'negated': edge['negated']} for edge in graph['edges']]
                           for arm, graph in zip(('cpu', 'cuda'), graphs)},
        'provisional_scientific_classification': 'AMBIGUOUS',
        'rationale': 'Awaiting source-grounded review of generated claims, unmatched relations and structured qualifiers.',
    }


def execute(config, output, ledger_path=LEDGER, report_path=REPORT):
    packet, entities, assemblies, requests, preflight = prepare(config)
    # Resolve credentials before reserving budget or creating a live run.
    secret = config.resolved_api_key()
    gate.require(not output.exists(), 'Never overwrite a live evidence directory')
    budget = Budget(ledger_path, output.name)
    output.mkdir(parents=True)
    revision = gate.subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    summary = {'experiment': EXPERIMENT, 'repository_revision': revision, 'timestamp': now(), 'case_id': 'sfpq-full',
               'tool_sha256': gate.digest(Path(__file__)), 'source_sha256': gate.sha_text(packet['text']),
               'document_id': packet['document_id'], 'title_sha256': gate.sha_text(packet['paper_title']),
               'execution_order': ['cpu', 'cuda'], 'status': 'started', 'evidence_directory': str(output),
               'cpu_evidence': str(gate.CPU), 'cuda_evidence': str(gate.CUDA), 'preflight': preflight,
               'configuration': contract_resource('baseline-profile.json')['relation'], 'arms': {},
               'provider_submission_count': 0, 'repair_count': 0,
               'provisional_scientific_classification': 'AMBIGUOUS', 'rationale': 'Execution not complete.'}
    save(output / 'run.json', summary)
    results = []
    try:
        for arm, es, expected in zip(('cpu', 'cuda'), entities, requests):
            arm_output = output / arm
            save(arm_output / 'entities.json', [e.to_dict() for e in es])
            state = {'started_at': now(), 'entity_digest': gate.sha_text(gate.encoded([e.to_dict() for e in es])),
                     'entity_file_sha256': gate.digest((gate.CPU if arm == 'cpu' else gate.CUDA) / 'sfpq-full-entities.json'),
                     'request_sha256': gate.sha_text(gate.encoded(expected)), 'request_utf8_bytes': len(gate.encoded(expected).encode())}
            summary['arms'][arm] = state

            def diagnostics(value):
                state['latest_diagnostics'] = value
                save(arm_output / 'diagnostics.json', state, (secret,))

            extractor = LLMRelationExtractor.from_openai(config, diagnostics_callback=diagnostics)
            _provider(extractor, 'relation', contract_resource('baseline-profile.json'))
            executor = extractor._background_executor
            gate.require(executor._client.max_retries == 0, 'SDK retries must be disabled')
            recorder = RecordedResponses(executor._client.responses, budget, arm, arm_output, expected, (secret,))
            executor._client = SimpleNamespace(responses=recorder)
            started = time.monotonic()
            result = extractor.extract_relations(packet['text'], es)
            state.update(status='validated', finished_at=now(), elapsed_seconds=time.monotonic() - started,
                         generation_diagnostics=extractor.last_generation_diagnostics,
                         provider_submission_count=recorder.generation, repair_count=recorder.generation - 1,
                         relation_count=len(result.relations))
            save(arm_output / 'validated-relations.json', result.to_dict(), (secret,))
            save(arm_output / 'diagnostics.json', state, (secret,))
            results.append(result)
            save(output / 'run.json', summary, (secret,))
        summary.update(status='both_arms_validated', comparison=compare_relations(packet, assemblies, results))
    except BaseException as error:
        if summary['arms']:
            summary['arms'][arm].update(status='failed', finished_at=now())
        summary.update(status='operationally_inconclusive', error_type=type(error).__name__,
                       rationale='Stopped without repeats after execution failure; inspect preserved diagnostics and conservative ledger.')
    finally:
        summary.update(finished_at=now(), provider_submission_count=budget.value['attempts_consumed'],
                       repair_count=budget.value['repairs_consumed'])
        budget.value['status'] = summary['status']
        save(ledger_path, budget.value)
        save(output / 'run.json', summary, (secret,))
        save(report_path, summary, (secret,))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    config = OpenAIConfig.from_environment()
    if not args.live:
        gate.require(not REPORT.exists() or gate.read(REPORT)['status'] in ('blocked_missing_credential', 'prepared_not_executed'),
                     'Preserve existing live result; offline preparation cannot replace it')
        packet, entities, _, requests, preflight = prepare(config)
        output = ROOT / '.cache/phase2' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-sfpq-live-preflight')
        credential_present = bool(config.api_key or os.getenv(config.api_key_env))
        summary = {
            'experiment': EXPERIMENT, 'repository_revision': gate.subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'tool_sha256': gate.digest(Path(__file__)),
            'timestamp': now(), 'case_id': packet['case_id'], 'evidence_directory': str(output),
            'status': 'prepared_not_executed' if credential_present else 'blocked_missing_credential',
            'execution_order': ['cpu', 'cuda'], 'cpu_evidence': str(gate.CPU), 'cuda_evidence': str(gate.CUDA),
            'source_sha256': gate.sha_text(packet['text']), 'preflight': preflight,
            'document_id': packet['document_id'], 'title_sha256': gate.sha_text(packet['paper_title']),
            'entity_digests': dict(zip(('cpu', 'cuda'), (gate.sha_text(gate.encoded([e.to_dict() for e in es])) for es in entities))),
            'configuration': contract_resource('baseline-profile.json')['relation'],
            'provider_submission_count': 0, 'repair_count': 0, 'validated_relations': None,
            'provisional_scientific_classification': 'AMBIGUOUS',
            'rationale': 'No live experiment performed; scientific equivalence cannot be assessed.' +
                         ('' if credential_present else ' No accepted OpenAI credential is available in this process.'),
        }
        save(output / 'preflight.json', summary)
        for arm, request in zip(('cpu', 'cuda'), requests):
            save(output / f'{arm}-request.json', request)
        save(REPORT, summary)
        print(gate.encoded({k: summary[k] for k in ('status', 'provider_submission_count', 'repair_count')}))
        return
    with exclusive_run():
        output = ROOT / '.cache/phase2' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-sfpq-live')
        summary = execute(config, output)
    print(gate.encoded({k: summary[k] for k in ('status', 'provider_submission_count', 'repair_count')}))


if __name__ == '__main__':
    main()
