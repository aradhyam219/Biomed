"""Frozen Luna request identity and CUDA pre-provider gates; no live execution."""
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import tempfile
from unittest import TestCase, main
from unittest.mock import patch

from biomedical_extractor.graph_contract import (contract_resource, delivery_profile, ExportContext,
    GraphValidationError, profile_identity, validate_graph)
from biomedical_extractor.graph_profile import check_graph_options, verify_ner_metadata
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.ner_runners import RunnerOutput
from tools import phase2_luna_cuda as smoke


def prior_submissions():
    return [{'experiment': 'historical-sol', 'repair': False} for _ in range(2)] + [
        {'experiment': smoke.PRIOR_EXPERIMENT, 'repair': False, 'generation': 1,
         'submission_state': 'uncertain_until_observed'}]


class Response:
    status = 'completed'
    service_tier = 'priority'
    model = 'gpt-5.6-luna'
    reasoning = {'effort': 'max'}
    background = True

    def __init__(self, payload, number):
        self.id, self.output_text = f'resp_fake_{number}', json.dumps(payload)

    def model_dump(self, **kwargs):
        return {'id': self.id, 'status': self.status, 'output_text': self.output_text,
                'model': self.model, 'service_tier': self.service_tier}


class FakeOpenAI:
    calls = []
    connect_nodes = True
    base_url = 'https://api.openai.com/v1'

    def __init__(self, **kwargs):
        self.max_retries = kwargs['max_retries']
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs['text']['format']['name'] == 'StructuredRelationPayload':
            text = kwargs['input'].split('Source text:\n', 1)[1]
            relations = [{'source': 'E1', 'target': 'E2', 'predicate': 'test_relation',
                          'assertion': text[:65], 'evidence': text[:65], 'negated': False}] if self.connect_nodes else []
            return Response({'relations': relations}, len(self.calls))
        targets, _ = json.JSONDecoder().raw_decode(kwargs['input'].split('Requested entities and all source mentions:\n', 1)[1])
        return Response({'roles': [{'node_id': t['node_id'], 'category': 'contextual',
                                   'paragraphs': ['Offline fake role.'], 'evidence': [t['mentions'][0]['text']]} for t in targets]}, len(self.calls))


class LunaCUDAProfileTests(TestCase):
    def test_complete_leadership_freeze_is_recovered(self):
        freeze = smoke.verify_freeze()
        self.assertEqual(freeze['configuration'], {
            'model': 'gpt-5.6-luna', 'reasoning_effort': 'max', 'service_tier': 'fast',
            'background': True, 'max_completion_tokens': 128000, 'max_retries': 2,
            'poll_interval_seconds': 3.0, 'generation_timeout_seconds': 900.0})
        self.assertEqual(freeze['schemas']['relation']['prompt_sha256'], '13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f')
        self.assertEqual(freeze['schemas']['relation']['transport_sha256'], 'b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510')

    def test_old_cpu_identity_remains_immutable_and_new_profiles_are_distinct(self):
        old = contract_resource('baseline-profile.json')
        self.assertEqual(profile_identity(old), 'ees-cfeec6ccd400b9f44abbef35551944aa074ee3d79d3e5ec18dd7d7551c76e0de')
        self.assertEqual(len({profile_identity(p) for p in (old, delivery_profile(), delivery_profile('cuda'))}), 3)
        check_graph_options(OpenAIConfig(), model=old['ner']['model_identifier'], device='cuda')
        self.assertEqual(delivery_profile()['ner'], old['ner'])
        counterfeit = deepcopy(delivery_profile('cuda'))
        counterfeit['ner']['runtime']['pytorch_module'] = '2.14.0+custom'
        with self.assertRaises(GraphValidationError):
            profile_identity(counterfeit)

    def test_cuda_module_build_is_exact_and_does_not_weaken_cpu_acceptance(self):
        profile = delivery_profile('cuda')
        metadata = self.metadata(profile)
        verify_ner_metadata(metadata, profile, pytorch_distribution='2.14.0')
        for field, wrong in [('pytorch', '2.14.0+cpu'), ('device', 'cpu'), ('cuda_available', False), ('cuda_version', '12.8'), ('stride', 1)]:
            changed = deepcopy(metadata); changed['runtime'][field] = wrong
            with self.subTest(field=field), self.assertRaises(GraphValidationError):
                verify_ner_metadata(changed, profile, pytorch_distribution='2.14.0')
        with self.assertRaises(GraphValidationError):
            verify_ner_metadata(metadata, profile)
        with self.assertRaises(GraphValidationError):
            verify_ner_metadata(metadata, contract_resource('baseline-profile.json'), pytorch_distribution='2.14.0')

    @staticmethod
    def metadata(profile):
        runtime = deepcopy(profile['ner']['runtime'])
        runtime['pytorch'] = runtime.pop('pytorch_module')
        return {k: profile['ner'][k] for k in ('model_identifier', 'model_revision', 'model_artifact_sha256')} | {'runtime': runtime}

    def dry_smoke(self, *, connect_nodes=True, bad_metadata=False, missing_addition=False):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        profile = delivery_profile('cuda')
        metadata = self.metadata(profile)
        if bad_metadata:
            metadata['runtime']['device'] = 'cpu'
        freeze = smoke.verify_freeze()
        packet = smoke.read(smoke.ROOT / 'tests/fixtures/compatibility/sfpq-full.json')
        smoke.save(root / 'tests/fixtures/compatibility/sfpq-full.json', packet)
        smoke.save(root / 'reports/phase2/manifest.json', {'cases': [{'case_id': 'sfpq-full',
            'document_id': packet['document_id'], 'paper_title': packet['paper_title'], 'source_sha256': smoke.sha_text(packet['text'])}]})
        freeze_path, ledger, report = root / 'freeze.json', root / 'ledger.json', root / 'report.json'
        smoke.save(freeze_path, freeze)
        smoke.save(ledger, {'generation_submission_cap': 24, 'shared_output_repair_cap': 4,
            'attempts_consumed': 3, 'repairs_consumed': 0,
            'submission_attempts': prior_submissions()})
        (root / '.cache/phase2').mkdir(parents=True)
        versions = {k: profile['ner']['runtime'][k] for k in ('python', 'flair', 'pytorch', 'transformers', 'scispacy', 'spacy', 'en_core_sci_sm')}
        versions.update(platform='Linux', distribution_additions=deepcopy(profile['ner']['distribution_additions']))
        if missing_addition:
            versions['distribution_additions'].pop('nvidia-nvshmem-cu13')
        ner_calls = []

        def fake_ner(documents, **kwargs):
            ner_calls.append(kwargs)
            text = packet['text']
            predictions = [{'text': text[start:end], 'start': start, 'end': end, 'label': kind, 'score': .9}
                           for start, end, kind in [(18, 22, 'Gene'), (56, 58, 'Disease')]]
            smoke.save(kwargs['input_path'], {'documents': list(documents)})
            smoke.save(kwargs['output_path'], {'metadata': metadata, 'documents': [{'id': 'single-document', 'predictions': predictions}]})
            return RunnerOutput('HunFlair2', kwargs['output_path'], metadata, {'single-document': predictions})

        FakeOpenAI.calls, FakeOpenAI.connect_nodes = [], connect_nodes
        ctx = ExportContext(version('biomedical-extractor'), 'a' * 40, profile)
        config = OpenAIConfig(api_key='offline-sentinel-credential')
        with patch.object(smoke, 'ROOT', root), patch.object(smoke, 'LEDGER', ledger), patch.object(smoke, 'SMOKE_REPORT', report), \
             patch.object(smoke, 'FREEZE_REPORT', freeze_path), patch.object(smoke, 'verify_freeze', return_value=freeze), \
             patch.object(smoke, 'release_context', return_value=ctx), patch('openai.OpenAI', FakeOpenAI), \
             patch.object(OpenAIConfig, 'from_environment', return_value=config), \
             patch('biomedical_extractor.ner_runners.run_hunflair2', side_effect=fake_ner), \
             patch('biomedical_extractor.graph_profile._isolated_versions', return_value=versions), \
             patch('biomedical_extractor.graph_profile._hunflair2_artifact', return_value=(Path('artifact'), profile['ner']['model_revision'])), \
             patch('biomedical_extractor.graph_profile._sha256_file', return_value=profile['ner']['model_artifact_sha256']):
            summary = smoke.run()
            with self.assertRaisesRegex(ValueError, 'already started'):
                smoke.run()
        for path in root.rglob('*.json'):
            self.assertNotIn(config.api_key, path.read_text())
        return summary, ner_calls, FakeOpenAI.calls, root

    def test_composed_dry_smoke_runs_ner_once_and_no_roles_when_connected(self):
        summary, ner, calls, root = self.dry_smoke()
        self.assertEqual(summary['disposition'], 'LINUX_CUDA_COMPATIBLE')
        self.assertEqual(len(ner), 1)
        self.assertEqual(ner[0]['device'], 'cuda')
        self.assertEqual(len(calls), 1)
        self.assertEqual(summary['smoke_submissions'], 1)
        self.assertEqual(summary['phase2_total_submissions'], 4)
        self.assertFalse(summary['role_generation_occurred'])
        output = root / summary['evidence_directory']
        self.assertTrue(validate_graph(smoke.read(output / 'graph-v1.json'), text=smoke.read(root / 'tests/fixtures/compatibility/sfpq-full.json')['text'],
            paper_title=smoke.read(root / 'tests/fixtures/compatibility/sfpq-full.json')['paper_title']).source_checked)

    def test_roles_occur_only_as_natural_degree_zero_pipeline_stage(self):
        summary, ner, calls, _ = self.dry_smoke(connect_nodes=False)
        self.assertEqual(summary['disposition'], 'LINUX_CUDA_COMPATIBLE')
        self.assertEqual(len(ner), 1)
        self.assertEqual(len(calls), 2)
        self.assertTrue(summary['role_generation_occurred'])
        self.assertEqual(summary['role_target_count'], 2)
        self.assertEqual([c['text']['format']['name'] for c in calls], ['StructuredRelationPayload', 'StructuredPaperRolePayload'])
        for call in calls:
            self.assertEqual((call['model'], call['reasoning'], call['service_tier']), ('gpt-5.6-luna', {'effort': 'max'}, 'fast'))

    def test_wrong_actual_ner_device_stops_before_any_provider_submission(self):
        summary, ner, calls, _ = self.dry_smoke(bad_metadata=True)
        self.assertEqual(summary['disposition'], 'BLOCKED')
        self.assertEqual(len(ner), 1)
        self.assertEqual(calls, [])
        self.assertEqual(summary['smoke_submissions'], 0)

    def test_missing_cuda_package_stops_before_ner_and_provider(self):
        summary, ner, calls, _ = self.dry_smoke(missing_addition=True)
        self.assertEqual(summary['disposition'], 'BLOCKED')
        self.assertEqual(ner, [])
        self.assertEqual(calls, [])

    def test_shared_budget_counts_repairs_and_rejects_extra_generations(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / 'ledger.json'
            smoke.save(ledger, {'generation_submission_cap': 24, 'shared_output_repair_cap': 4,
                'attempts_consumed': 3, 'repairs_consumed': 0,
                'submission_attempts': prior_submissions()})
            budget = smoke.SmokeBudget(ledger, 'test')
            with self.assertRaises(ValueError):
                budget.reserve('roles', 1)
            for task in ('relation', 'roles'):
                for generation in (1, 2, 3):
                    budget.reserve(task, generation)
                with self.assertRaises(ValueError):
                    budget.reserve(task, 4)
            saved = smoke.read(ledger)
            self.assertEqual(saved['attempts_consumed'], 9)
            self.assertEqual(saved['repairs_consumed'], 4)
            self.assertEqual(saved['submission_attempts'][:2], [{'experiment': 'historical-sol', 'repair': False}] * 2)
            self.assertEqual(saved['submission_attempts'][2], prior_submissions()[2])
            with self.assertRaises(ValueError):
                smoke.SmokeBudget(ledger, 'forbidden-third-attempt')


if __name__ == '__main__':
    main()
