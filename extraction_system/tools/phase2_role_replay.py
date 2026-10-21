"""One bounded role-only confirmation from the retained SFPQ pre-role graph.

No entity extraction, assembly, or relation provider is constructed here.
Run offline with --prepare; omit it only for the single authorized live run.
"""
from __future__ import annotations

import argparse
import fcntl
from hashlib import sha256
import json
from pathlib import Path

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.graph import GraphDocument, GraphNode, GraphEdge, GraphEvidence, GraphResult
from biomedical_extractor.graph_contract import export_graph, validate_graph, release_context
from biomedical_extractor.graph_profile import _implementation, _provider
from biomedical_extractor.llm_paper_roles import LLMPaperRoleExtractor
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.paper_roles import PaperRoleTarget, apply_paper_roles
from tools.phase2_downstream import ROOT, require
from tools.phase2_reference import read
from tools.phase2_sfpq_live import RecordedResponses, save, now

SAVED = ROOT / '.cache/phase2/20261015T100110167945Z-luna-cuda-composed-retry'
MARKER = ROOT / '.cache/phase2/sfpq-role-reliability-started.json'
OUTPUT = ROOT / '.cache/phase2/sfpq-role-reliability'
REPORT = ROOT / 'reports/phase2/sfpq-role-reliability.json'


def prepare():
    packet = read(ROOT / 'tests/fixtures/compatibility/sfpq-full.json')
    saved = read(SAVED / 'graph-before-roles.json')
    validation = validate_graph(saved, text=packet['text'], paper_title=packet['paper_title'])
    require(validation.source_checked, 'Saved graph source was not checked')
    require(saved['document']['id'] == packet['document_id'], 'Saved document ID differs')
    require(sha256(packet['text'].encode()).hexdigest() == read(SAVED / 'started.json')['source_sha256'],
            'Saved source identity differs')
    graph = GraphResult(
        GraphDocument(**saved['document']),
        tuple(GraphNode(**{**n, 'mentions': tuple(Entity(**e) for e in n['mentions'])}) for n in saved['nodes']),
        tuple(GraphEdge(**{**e, 'evidence': tuple(GraphEvidence(**v) for v in e['evidence'])}) for e in saved['edges']),
    )
    require(graph.to_dict() == saved, 'Saved graph roundtrip differs')
    targets = tuple(PaperRoleTarget(n.id, n.label, n.type, n.mentions) for n in graph.unconnected_nodes)
    require([t.to_dict() for t in targets] == read(SAVED / 'roles/targets.json'), 'Saved targets differ')
    require((len(graph.nodes), len(graph.edges), len(targets)) == (98, 73, 57), 'Saved counts differ')
    initial = read(SAVED / 'roles/generation-1/request.json')['input']
    require(initial.endswith(packet['text']) and '\nPaper title:\n' + packet['paper_title'] + '\n' in initial,
            'Saved role source/title differs')
    evidence = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in (
        SAVED / 'graph-before-roles.json', SAVED / 'roles/targets.json', SAVED / 'roles/generation-1/request.json',
        ROOT / 'tests/fixtures/compatibility/sfpq-full.json')}
    return packet, graph, targets, evidence


class ReplayBudget:
    """New reliability confirmation budget; historical Phase 2 caps stay intact."""
    def __init__(self, path):
        self.path = path
        self.value = {'generation_submission_cap': 3, 'output_repair_cap': 2, 'submission_attempts': []}
        require(not path.exists(), 'Role confirmation ledger exists; no repeat authorized')
        save(path, self.value)

    def reserve(self, arm, generation):
        entries = self.value['submission_attempts']
        require(arm == 'roles' and generation == len(entries) + 1 and generation <= 3,
                'Repeated/out-of-budget role generation')
        entry = {'generation': generation, 'repair': generation > 1, 'reserved_at': now(),
                 'submission_state': 'uncertain_until_observed'}
        entries.append(entry)
        save(self.path, self.value)
        return entry

    def observed(self, entry, **values):
        entry.update(values)
        save(self.path, self.value)


def run():
    packet, graph, targets, evidence = prepare()
    require(not MARKER.exists(), 'Role confirmation already started; no repeat authorized')
    context = release_context(device='cuda')
    _implementation(context.configuration)
    config = OpenAIConfig.from_environment()
    require(config.max_retries == 2 and config.max_completion_tokens == 128000
            and config.poll_interval_seconds == 3 and config.generation_timeout_seconds == 900,
            'Frozen role limits differ')
    secret = config.resolved_api_key()
    extractor = LLMPaperRoleExtractor.from_openai(config)
    _provider(extractor, 'roles', context.configuration)
    summary = {'status': 'started', 'started_at': now(), 'case_id': 'sfpq-full',
               'implementation_revision': context.build_revision, 'saved_state_sha256': evidence,
               'evidence_directory': str(OUTPUT.relative_to(ROOT)),
               'configuration': {k: context.configuration['roles'][k] for k in (
                   'model', 'reasoning_effort', 'service_tier', 'background', 'max_retries')},
               'nodes': len(graph.nodes), 'edges': len(graph.edges), 'role_targets': len(targets),
               'ner_submissions': 0, 'relation_submissions': 0,
               'graph_contract_result': 'not_reached'}
    save(MARKER, summary)
    budget = ReplayBudget(OUTPUT / 'ledger.json')
    executor = extractor._background_executor

    class RoleResponses(RecordedResponses):
        def create(self, **request):
            require(request['model'] == 'gpt-5.6-luna' and request['reasoning'] == {'effort': 'max'}
                    and request['service_tier'] == 'fast' and request['background'] is True,
                    'Frozen role provider request differs')
            require(request['text']['format']['name'] == 'StructuredPaperRolePayload', 'Non-role request forbidden')
            if self.generation == 0:
                self.expected = request
            return super().create(**request)

    executor._client.responses = RoleResponses(executor._client.responses, budget, 'roles',
                                               OUTPUT / 'roles', None, (secret,))
    executor._diagnostics_callback = lambda value: save(OUTPUT / 'latest-diagnostics.json', value, (secret,))
    try:
        result = extractor.extract_roles(packet['paper_title'], packet['text'], targets)
        save(OUTPUT / 'roles/validated.json', result.to_dict(), (secret,))
        enriched = apply_paper_roles(graph, packet['text'], result)
        bare = enriched.to_dict()
        for node in bare['nodes']:
            node.pop('paper_role', None)
        require(bare == graph.to_dict(), 'Role attachment changed graph topology or source metadata')
        exported = export_graph(enriched, text=packet['text'], paper_title=packet['paper_title'], context=context)
        validation = validate_graph(exported, text=packet['text'], paper_title=packet['paper_title'])
        save(OUTPUT / 'graph-v1.json', exported, (secret,))
        summary.update(status='passed', graph_contract_result=validation.format,
                       source_checked=validation.source_checked, attached_roles=len(result.records),
                       observed_service_tiers=[d.get('observed_service_tier') for d in extractor.last_generation_diagnostics])
    except BaseException as error:
        summary.update(status='blocked', error_type=type(error).__name__)
    finally:
        save(OUTPUT / 'roles/retained-valid.json', extractor.last_validated_result.to_dict(), (secret,))
        entries = budget.value['submission_attempts']
        summary.update(finished_at=now(), provider_submissions=len(entries),
                       provider_repairs=sum(e['repair'] for e in entries),
                       retained_valid_roles=len(extractor.last_validated_result.records),
                       role_diagnostics=extractor.last_generation_diagnostics)
        save(OUTPUT / 'run.json', summary, (secret,))
        save(REPORT, summary, (secret,))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        _, graph, targets, evidence = prepare()
        print(json.dumps({'nodes': len(graph.nodes), 'edges': len(graph.edges),
                          'targets': len(targets), 'saved_state_sha256': evidence}))
    else:
        with (ROOT / '.cache/phase2/sfpq-role-reliability.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = run()
        print(json.dumps({k: result[k] for k in ('status', 'provider_submissions', 'provider_repairs', 'graph_contract_result')}))


if __name__ == '__main__':
    main()
