"""No network: SFPQ source selection, request identity, budgets and safe evidence."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import phase2_downstream as gate
from tools import phase2_sfpq_live as live
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.relation_extraction import validate_relations


SECRET = 'test-credential-must-never-be-in-evidence'


class Response:
    def __init__(self, text):
        self.id, self.status, self.output_text = 'resp_offline', 'completed', text

    def model_dump(self, **kwargs):
        return {'id': self.id, 'status': self.status, 'output_text': self.output_text,
                'authorization': SECRET, 'metadata': {'test': SECRET}}


class FakeOpenAI:
    plans = []
    calls = []

    def __init__(self, **kwargs):
        self.max_retries = kwargs['max_retries']
        self.base_url = 'https://api.openai.com/v1'
        plan = iter(self.plans.pop(0))

        def create(**request):
            self.calls.append(request)
            item = next(plan)
            if isinstance(item, BaseException):
                raise item
            return Response(item)

        self.responses = SimpleNamespace(create=create)


class SFPQLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = OpenAIConfig(api_key=SECRET)
        cls.prepared = live.prepare(cls.config)

    def ledger(self, directory):
        path = directory / 'ledger.json'
        live.save(path, {'generation_submission_cap': 24, 'shared_output_repair_cap': 4,
                         'submission_attempts': [], 'attempts_consumed': 0, 'repairs_consumed': 0})
        return path

    def run_fake(self, directory, plans):
        ledger = self.ledger(directory)
        FakeOpenAI.plans, FakeOpenAI.calls = copy.deepcopy(plans), []
        # Real production factory/executor/validator run with fake SDK class.
        with gate.offline(), patch('openai.OpenAI', FakeOpenAI), patch.object(live, 'prepare', return_value=self.prepared):
            result = live.execute(self.config, directory / 'evidence', ledger, directory / 'report.json')
        return result, ledger

    def test_preflight_selects_retained_full_paper_and_score_only_difference(self):
        packet, entities, _, requests, comparison = self.prepared
        self.assertEqual(packet['case_id'], 'sfpq-full')
        self.assertEqual([len(es) for es in entities], [460, 460])
        for run, es, request in zip((gate.CPU, gate.CUDA), entities, requests):
            self.assertEqual([e.to_dict() for e in es], gate.read(run / 'sfpq-full-entities.json')['entities'])
            self.assertTrue(request['input'].endswith(packet['text']))
        self.assertEqual(comparison['non_score_difference_count'], 0)
        self.assertEqual(comparison['different_score_literals'], 308)

    def test_two_initials_in_fixed_order_and_no_secrets_or_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result, ledger = self.run_fake(directory, [['{"relations":[]}'], ['{"relations":[]}']])
            self.assertEqual(result['status'], 'both_arms_validated')
            self.assertEqual(result['provider_submission_count'], 2)
            self.assertEqual(result['repair_count'], 0)
            self.assertEqual([e['arm'] for e in gate.read(ledger)['submission_attempts']], ['cpu', 'cuda'])
            self.assertEqual(FakeOpenAI.calls, self.prepared[3])
            self.assertFalse(FakeOpenAI.plans)
            for path in directory.rglob('*.json'):
                self.assertNotIn(SECRET, path.read_text())
            self.assertTrue((directory / 'evidence/cpu/generation-1/parsed-output.json').exists())
            with self.assertRaisesRegex(ValueError, 'cannot be restarted'):
                live.Budget(ledger, 'retry')

    def test_production_output_repair_counted_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, ledger = self.run_fake(Path(temporary), [['invalid JSON', '{"relations":[]}'], ['{"relations":[]}']])
            self.assertEqual(result['status'], 'both_arms_validated')
            self.assertEqual(result['provider_submission_count'], 3)
            self.assertEqual(result['repair_count'], 1)
            self.assertEqual([e['repair'] for e in gate.read(ledger)['submission_attempts']], [False, True, False])
            self.assertIn('REPAIR INSTRUCTION:', FakeOpenAI.calls[1]['input'])

    def test_transport_failure_is_conservatively_counted_and_cuda_not_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, ledger = self.run_fake(Path(temporary), [[RuntimeError(SECRET)], ['{"relations":[]}']])
            self.assertEqual(result['status'], 'operationally_inconclusive')
            self.assertEqual(result['provider_submission_count'], 1)
            self.assertEqual(len(FakeOpenAI.calls), 1)
            self.assertEqual(len(FakeOpenAI.plans), 1)
            self.assertEqual(gate.read(ledger)['submission_attempts'][0]['submission_state'], 'uncertain_until_observed')
            self.assertNotIn(SECRET, json.dumps(result))

    def test_budget_persisted_before_create_and_no_repeated_initials(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ledger = self.ledger(directory)
            budget = live.Budget(ledger, 'test')

            def create(**request):
                self.assertEqual(gate.read(ledger)['attempts_consumed'], 1)
                raise RuntimeError('simulated uncertain submission')

            recorder = live.RecordedResponses(SimpleNamespace(create=create), budget, 'cpu', directory / 'cpu', {}, (SECRET,))
            with self.assertRaises(RuntimeError):
                recorder.create()
            with self.assertRaises(ValueError):
                budget.reserve('cpu', 1)
            budget.reserve('cpu', 2); budget.reserve('cpu', 3)
            with self.assertRaises(ValueError):
                budget.reserve('cpu', 4)
            budget.reserve('cuda', 1); budget.reserve('cuda', 2); budget.reserve('cuda', 3)
            self.assertEqual(gate.read(ledger)['attempts_consumed'], 6)
            self.assertEqual(gate.read(ledger)['repairs_consumed'], 4)
            with self.assertRaises(ValueError):
                budget.reserve('cuda', 4)

    def test_actual_request_mutation_stops_before_reservation_or_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ledger = self.ledger(directory)
            budget = live.Budget(ledger, 'test')
            responses = SimpleNamespace(create=lambda **kwargs: self.fail('Network seam reached'))
            recorder = live.RecordedResponses(responses, budget, 'cpu', directory / 'cpu', {'input': 'expected'}, (SECRET,))
            with self.assertRaisesRegex(ValueError, 'Actual initial request'):
                recorder.create(input='changed')
            self.assertEqual(gate.read(ledger)['attempts_consumed'], 0)

    def test_alignment_preserves_multiple_claims_negation_and_unmatched_relations(self):
        packet, entities, assemblies, _, _ = self.prepared
        common = {'source': entities[0][0].id, 'target': entities[0][1].id, 'assertion': 'Saved test output',
                  'evidence': packet['text'][:40], 'negated': False}
        cpu = [{**common, 'predicate': 'decreases'}, {**common, 'predicate': 'associates'},
               {**common, 'predicate': 'negated_claim', 'negated': True}]
        cuda = [{**common, 'predicate': 'associates', 'assertion': 'Different wording'},
                {**common, 'predicate': 'decreases', 'intervention': 'Condition'},
                {**common, 'source': common['target'], 'target': common['source'], 'predicate': 'reverse'}]
        results = [validate_relations(packet['text'], es, values) for es, values in zip(entities, (cpu, cuda))]
        compared = live.compare_relations(packet, assemblies, results)
        self.assertEqual(len(compared['aligned_relations']), 2)
        self.assertEqual(compared['cpu_unaligned_indices'], [2])
        self.assertEqual(compared['cuda_unaligned_indices'], [2])
        self.assertEqual(len(compared['cuda_only_endpoint_pairs']), 1)
        self.assertEqual(compared['provisional_scientific_classification'], 'AMBIGUOUS')

    def test_three_invalid_cpu_outputs_exhaust_production_repair_budget_and_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, _ = self.run_fake(Path(temporary), [['invalid'] * 3, ['{"relations":[]}']])
            self.assertEqual(result['status'], 'operationally_inconclusive')
            self.assertEqual(result['provider_submission_count'], 3)
            self.assertEqual(result['repair_count'], 2)
            self.assertEqual(len(FakeOpenAI.plans), 1)


if __name__ == '__main__':
    unittest.main()
