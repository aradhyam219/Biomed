"""Restore the evidenced Contract 14R freeze and run one genuine CUDA pipeline.

prepare builds exact descriptors and verifies frozen artifacts offline. run uses
the real isolated NER and accepted automatic-role pipeline, recording SDK calls
with durable budget reservations. No CPU control, repeats or tuning occur here.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from biomedical_extractor import llm_relation_extraction as relation, llm_paper_roles as roles
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.graph_contract import (contract_resource,
    export_graph, profile_identity, validate_graph, release_context)
from biomedical_extractor.graph_profile import _implementation, prepare_graph_export, verify_graph_profile
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.responses_execution import strict_transport_schema
from tools.phase2_reference import read
from tools.phase2_downstream import ROOT, digest, encoded, require, sha_text
from tools.phase2_sfpq_live import save, RecordedResponses, Budget

FREEZE_COMMIT = '214f3be09aebd972d2e2471a167da884566e11ed'
FREEZE_DIR = 'reports/luna_56_max_fast_source_order_smoke_20261007'
RESOURCES = ROOT / 'src/biomedical_extractor/contract_resources'
FREEZE_REPORT = ROOT / 'reports/phase2/luna-freeze.json'
SMOKE_REPORT = ROOT / 'reports/phase2/luna-cuda-smoke.json'
LEDGER = ROOT / 'reports/phase2/provider-ledger.json'
EXPERIMENT = 'phase2-luna-cuda-composed-1'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def frozen(name):
    return subprocess.check_output(['git', 'show', f'{FREEZE_COMMIT}:extraction_system/{FREEZE_DIR}/{name}'], cwd=ROOT)


def verify_freeze():
    """Verify the recorded request, exact schema objects and source-order prompt."""
    preflight = json.loads(frozen('preflight.json'))
    parity = json.loads(frozen('request_parity.json'))
    expected = preflight['candidate']
    actual = relation.OpenAIConfig()
    require(all(getattr(actual, key) == value for key, value in expected.items()), 'Frozen Luna configuration mismatch')
    artifacts = {}
    for task, module, prompt in (
        ('relation', relation, relation.RELATION_EXTRACTION_SYSTEM_PROMPT),
        ('role', roles, roles.PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT),
    ):
        for kind, schema in (('semantic', module._structured_payload_schema().model_json_schema()),
                             ('transport', strict_transport_schema(module._structured_payload_schema()))):
            name = f'{task}_{kind}_schema.json'
            archived = frozen(name)
            require(json.loads(archived) == schema, f'Frozen {task} {kind} schema mismatch')
            require(sha_text(encoded(schema)) == preflight['schemas'][task][kind + '_sha256'], 'Frozen schema hash mismatch')
            artifacts[name] = sha256(archived).hexdigest()
        require(sha_text(prompt) == preflight['schemas'][task]['prompt_sha256'], f'Frozen {task} prompt mismatch')
    packet = json.loads(frozen('inputs.json'))
    from biomedical_extractor.entity_extraction import Entity
    mentions = tuple(Entity(**e) for e in packet['entities'])
    require(list(mentions) == sorted(mentions, key=lambda e: (e.start, e.end, e.type)), 'Frozen source order mismatch')
    prompt = relation._build_prompt(packet['source']['source_text'], mentions, relation.RELATION_EXTRACTION_SYSTEM_PROMPT)
    require(sha_text(prompt) == parity['new_complete_prompt_sha256'], 'Frozen full request construction mismatch')
    require(digest(ROOT / 'src/biomedical_extractor/responses_execution.py') == parity['loaded_module_hashes']['responses_execution.py'], 'Frozen transport implementation changed')
    requests = json.loads(frozen('requests.json'))
    require(all(r['model'] == expected['model'] and r['reasoning'] == {'effort': expected['reasoning_effort']}
                and r['requested_service_tier'] == expected['service_tier'] and r['background'] is True
                for r in requests), 'Recorded frozen requests contradict candidate')
    artifacts.update({name: sha256(frozen(name)).hexdigest() for name in ('preflight.json', 'request_parity.json', 'requests.json', 'candidate.patch', 'inputs.json')})
    return {'freeze_commit': FREEZE_COMMIT, 'freeze_directory': FREEZE_DIR, 'artifact_sha256': artifacts,
            'configuration': expected, 'schemas': preflight['schemas'],
            'source_order_fixture_prompt_sha256': sha_text(prompt),
            'ordering': 'Original source-order normalized mention sequence; no score or ordering changes.',
            'api_path': 'OpenAI Responses SDK; background=True, store=False, strict JSON schema; SDK retries=0.',
            'approval_basis': 'Current leadership instruction restores the recorded 14R path. The archived report-only/not-promoted status remains historical truth.'}


def prepare():
    freeze = verify_freeze()
    old = contract_resource('baseline-profile.json')
    cpu = deepcopy(old)
    for name in cpu['implementation_sha256']:
        cpu['implementation_sha256'][name] = sha_text((ROOT / 'src/biomedical_extractor' / name).read_text(encoding='utf-8-sig'))
    cpu['relation']['configuration'] = freeze['configuration']
    for key in ('model', 'reasoning_effort', 'service_tier'):
        cpu['roles'][key] = freeze['configuration'][key]
    cuda = deepcopy(cpu)
    observed = read(ROOT / '.cache/phase2/20261015T061416Z-cuda/raw.json')['metadata']['runtime']
    cuda['ner']['runtime'] = {key: observed[key] for key in old['ner']['runtime']}
    cuda['ner']['runtime'].update(pytorch='2.14.0', pytorch_module=observed['pytorch'],
                                  cuda_available=True, cuda_version=observed['cuda_version'])
    cuda['ner'].update(platform='Linux', distribution_additions={
        'nvidia-cusparselt-cu13': '0.8.1', 'nvidia-nvshmem-cu13': '3.4.5'})
    for name, profile in (('luna-cpu-profile.json', cpu), ('linux-cuda-profile.json', cuda)):
        path = RESOURCES / name
        if path.exists():
            require(read(path) == profile, 'Existing derived profile differs; review before replacement')
        else:
            save(path, profile)
        _implementation(profile)
    freeze.update(original_cpu_profile_identity=profile_identity(old),
                  luna_cpu_profile_identity=profile_identity(cpu),
                  linux_cuda_candidate_profile_identity=profile_identity(cuda),
                  status='freeze_verified_cuda_smoke_pending')
    save(FREEZE_REPORT, freeze)
    return freeze


class SmokeBudget(Budget):
    def __init__(self, path, run_id):
        self.path, self.run_id = path, run_id
        self.value = read(path)
        entries = self.value['submission_attempts']
        require(self.value['generation_submission_cap'] == 24 and self.value['shared_output_repair_cap'] == 4, 'Phase 2 caps changed')
        require(self.value['attempts_consumed'] == len(entries) == 2 and self.value['repairs_consumed'] == 0,
                'Expected exactly the two historical Sol submissions')
        require(all(e['experiment'] != EXPERIMENT for e in entries), 'Composed smoke already attempted')

    def reserve(self, arm, generation):
        entries = self.value['submission_attempts']
        previous = [e for e in entries if e['experiment'] == EXPERIMENT and e['arm'] == arm]
        require(arm in ('relation', 'roles') and generation == len(previous) + 1 and generation <= 3, 'Unexpected/repeated smoke generation')
        require(arm != 'roles' or any(e['experiment'] == EXPERIMENT and e['arm'] == 'relation' for e in entries), 'Roles before relations')
        repair = generation > 1
        require(len(entries) < self.value['generation_submission_cap'], 'Phase 2 budget exhausted')
        require(not repair or self.value['repairs_consumed'] < self.value['shared_output_repair_cap'], 'Shared repair budget exhausted')
        entry = {'experiment': EXPERIMENT, 'run_id': self.run_id, 'arm': arm, 'generation': generation,
                 'repair': repair, 'reserved_at': stamp(), 'submission_state': 'uncertain_until_observed'}
        entries.append(entry)
        self.value.update(attempts_consumed=len(entries), repairs_consumed=sum(e['repair'] for e in entries), status='luna_cuda_smoke_in_progress')
        save(self.path, self.value)
        return entry


def run():
    """One composed smoke; instrumentation captures without replacing science."""
    freeze = verify_freeze()
    require(read(FREEZE_REPORT)['configuration'] == freeze['configuration'], 'Prepared freeze differs')
    config = relation.OpenAIConfig.from_environment()
    require(all(getattr(config, k) == v for k, v in freeze['configuration'].items()), 'Environment differs from frozen Luna path')
    secret = config.resolved_api_key()
    context = release_context(device='cuda')  # Requires the corrected committed build.
    _implementation(context.configuration)
    packet = read(ROOT / 'tests/fixtures/compatibility/sfpq-full.json')
    manifest = read(ROOT / 'reports/phase2/manifest.json')
    case = next(c for c in manifest['cases'] if c['case_id'] == 'sfpq-full')
    require(packet['document_id'] == case['document_id'] and packet['paper_title'] == case['paper_title']
            and sha_text(packet['text']) == case['source_sha256'], 'Frozen source identity differs')
    marker = ROOT / '.cache/phase2/luna-cuda-composed-started.json'
    require(not marker.exists(), 'Composed smoke already started; no repeats')
    output = ROOT / '.cache/phase2' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-luna-cuda-composed')
    budget = SmokeBudget(LEDGER, output.name)
    summary = {'status': 'started', 'disposition': 'BLOCKED', 'started_at': stamp(),
               'repository_revision': context.build_revision, 'tool_sha256': digest(Path(__file__)),
               'case_id': 'sfpq-full', 'source_sha256': case['source_sha256'],
               'evidence_directory': str(output.relative_to(ROOT)),
               'configuration': freeze['configuration'], 'schemas': freeze['schemas'],
               'candidate_profile_identity': profile_identity(context.configuration),
               'profile_promoted': False, 'smoke_submissions': 0, 'smoke_repairs': 0,
               'role_generation_occurred': False}
    save(marker, summary)
    save(output / 'started.json', summary)
    holders = {}
    import openai
    from biomedical_extractor import ner_runners
    original_client = openai.OpenAI
    original_ner = ner_runners.run_hunflair2
    original_relations = relation.LLMRelationExtractor.extract_relations
    original_roles = roles.LLMPaperRoleExtractor.extract_roles

    class SmokeResponses(RecordedResponses):
        def __init__(self, responses):
            super().__init__(responses, budget, '', output, None, (secret,))

        def create(self, **request):
            task = {'StructuredRelationPayload': 'relation', 'StructuredPaperRolePayload': 'roles'}.get(request['text']['format']['name'])
            require(task is not None, 'Unexpected provider task')
            if not self.arm:
                self.arm, self.output = task, output / task
            require(task == self.arm, 'Provider task changed')
            require(request['model'] == config.model and request['reasoning'] == {'effort': 'max'}
                    and request['service_tier'] == 'fast' and request['background'] is True
                    and request['store'] is False and request['max_output_tokens'] == 128000
                    and request['text']['format']['strict'] is True, 'Frozen SDK request mismatch')
            kind = 'relation' if task == 'relation' else 'role'
            require(sha_text(encoded(request['text']['format']['schema'])) == freeze['schemas'][kind]['transport_sha256'], 'Frozen transport schema differs')
            if self.generation == 0:
                if task == 'relation':
                    expected = relation._build_prompt(packet['text'], holders['entities'], relation.RELATION_EXTRACTION_SYSTEM_PROMPT)
                else:
                    expected = roles._build_prompt(packet['paper_title'], packet['text'], holders['targets'], roles.PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT)
                require(request['input'] == expected, 'Frozen input ordering/request semantics differ')
                self.expected = request
                summary[task + '_initial_request_sha256'] = sha_text(encoded(request))
            return super().create(**request)

    class RecordedOpenAI(original_client):
        def __init__(self, **kwargs):
            require(kwargs.get('max_retries') == 0, 'SDK retries forbidden')
            super().__init__(**kwargs)
            self.responses = SmokeResponses(self.responses)

    def capture_ner(*args, **kwargs):
        require('ner' not in holders, 'NER repeat forbidden')
        require(kwargs['device'] == 'cuda', 'Actual CUDA inference required')
        result = original_ner(*args, **kwargs)
        holders['ner'] = result
        (output / 'ner').mkdir(parents=True)
        shutil.copyfile(kwargs['input_path'], output / 'ner/input.json')
        shutil.copyfile(kwargs['output_path'], output / 'ner/raw.json')
        summary['actual_ner_metadata'] = dict(result.metadata)
        save(output / 'ner/metadata.json', summary['actual_ner_metadata'])
        return result

    def capture_relations(extractor, text, entities):
        require('relations' not in holders, 'Relation extraction repeat forbidden')
        require(text == packet['text'], 'Source changed')
        values = tuple(entities)
        require(list(values) == sorted(values, key=lambda e: (e.start, e.end, e.type)), 'Source mention order changed')
        holders['entities'] = values
        save(output / 'ner/entities.json', [e.to_dict() for e in values])
        result = original_relations(extractor, text, entities)
        holders['relations'] = result
        require(all(d.get('observed_service_tier') == 'priority' for d in extractor.last_generation_diagnostics), 'Frozen Fast processing not observed; stop before roles')
        summary.update(ner_mention_count=len(values), relation_count=len(result.relations),
                       relation_diagnostics=list(extractor.last_generation_diagnostics))
        save(output / 'relation/validated.json', result.to_dict(), (secret,))
        assembly = assemble_document_entities(values, text)
        save(output / 'assembly.json', assembly.to_dict())
        save(output / 'graph-before-roles.json', build_graph_result(packet['document_id'], assembly, result).to_dict())
        return result

    def capture_roles(extractor, title, text, targets):
        require('targets' not in holders, 'Role batch repeat forbidden')
        holders['targets'] = tuple(targets)
        summary.update(role_generation_occurred=True, role_target_count=len(targets))
        save(output / 'roles/targets.json', [t.to_dict() for t in targets])
        result = original_roles(extractor, title, text, targets)
        require(all(d.get('observed_service_tier') == 'priority' for d in extractor.last_generation_diagnostics), 'Frozen Fast role processing not observed')
        summary.update(role_diagnostics=extractor.last_generation_diagnostics)
        save(output / 'roles/validated.json', result.to_dict(), (secret,))
        return result

    def diagnostics(value):
        save(output / 'latest-diagnostics.json', value, (secret,))

    try:
        with patch('openai.OpenAI', RecordedOpenAI), patch.object(ner_runners, 'run_hunflair2', side_effect=capture_ner), \
             patch.object(relation.LLMRelationExtractor, 'extract_relations', capture_relations), \
             patch.object(roles.LLMPaperRoleExtractor, 'extract_roles', capture_roles):
            # Genuine pretrained construction: NER and lazy automatic roles remain real.
            pipeline = LLMExtractionPipeline.from_pretrained(device='cuda', llm_config=config,
                hunflair2_runtime_python=ROOT / '.cache/hunflair2/runtime/bin/python',
                hunflair2_runtime_cache=ROOT / '.cache/hunflair2', hunflair2_offline=True)
            pipeline.relation_extractor._diagnostics_callback = diagnostics
            pipeline.relation_extractor._background_executor._diagnostics_callback = diagnostics
            prepare_graph_export(pipeline, text=packet['text'], document_id=packet['document_id'],
                                 paper_title=packet['paper_title'], context=context)
            graph = pipeline.extract_graph(packet['text'], document_id=packet['document_id'], paper_title=packet['paper_title'])
            verify_graph_profile(pipeline, context, text=packet['text'])
            exported = export_graph(graph, text=packet['text'], paper_title=packet['paper_title'], context=context)
            validation = validate_graph(exported, text=packet['text'], paper_title=packet['paper_title'])
            save(output / 'graph-v1.json', exported, (secret,))
            summary.update(status='composed_smoke_passed', disposition='LINUX_CUDA_COMPATIBLE',
                           graph_nodes=len(graph.nodes), graph_edges=len(graph.edges),
                           graph_contract_format=validation.format, graph_source_checked=validation.source_checked,
                           degree_zero_nodes=len(graph.unconnected_nodes), sanity_review='pending')
    except BaseException as error:
        summary.update(status='blocked', error_type=type(error).__name__,
                       rationale='Stopped without repeats/tuning. Inspect preserved runtime/SDK evidence; no compatibility conclusion inferred.')
    finally:
        entries = [e for e in budget.value['submission_attempts'] if e['experiment'] == EXPERIMENT]
        summary.update(finished_at=stamp(), smoke_submissions=len(entries), smoke_repairs=sum(e['repair'] for e in entries),
                       phase2_total_submissions=budget.value['attempts_consumed'], phase2_total_repairs=budget.value['repairs_consumed'])
        budget.value['status'] = summary['status']
        budget.value['resume_requirement'] = 'Stop for Phase 2 closure review; no automatic retries, additional papers, controls or Phase 3.'
        save(LEDGER, budget.value)
        save(output / 'run.json', summary, (secret,))
        save(SMOKE_REPORT, summary, (secret,))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    args = parser.parse_args()
    if args.action == 'prepare':
        freeze = prepare()
        print(encoded({k: freeze[k] for k in ('status', 'original_cpu_profile_identity', 'luna_cpu_profile_identity', 'linux_cuda_candidate_profile_identity')}))
    else:
        with (ROOT / '.cache/phase2/luna-cuda-composed.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            summary = run()
        print(encoded({k: summary[k] for k in ('status', 'disposition', 'smoke_submissions', 'smoke_repairs')}))


if __name__ == '__main__':
    main()
