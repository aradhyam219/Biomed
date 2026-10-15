"""Offline drift gate: meaningful differences, real request seams and evidence integrity."""
import copy
import socket
import unittest
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from tools import phase2_downstream as gate


class DownstreamDriftTests(unittest.TestCase):
    def test_only_finite_scores_at_declared_mention_paths_are_numerical(self):
        a = [{'id': 'E1', 'score': 0.9}]
        b = [{'id': 'E1', 'score': 0.9000001}]
        result = gate.compare_values(a, b, r'/\d+/score')
        self.assertEqual(result['classification'], 'SCORE_ONLY')
        self.assertEqual(result['differences'][0]['path'], '/0/score')
        for changed in ([{'id': 'E2', 'score': 0.9}], [], [{'id': 'E1', 'score': None}],
                        [{'id': 'E1', 'score': 0.9, 'alias': 'new'}]):
            with self.subTest(changed=changed):
                self.assertEqual(gate.compare_values(a, changed, r'/\d+/score')['classification'], 'STRUCTURAL')
        self.assertEqual(gate.compare_values({'score': 1.0}, {'score': 0.9}, r'/\d+/score')['classification'], 'STRUCTURAL')

    def test_real_relation_request_capture_and_non_score_tripwires(self):
        text = 'BRCA1 with text that looks like JSON: "score": 0.4'
        a = (Entity('E1', 'BRCA1', 'Gene', 0, 5, 0.9),)
        b = (Entity('E1', 'BRCA1', 'Gene', 0, 5, 0.9000001),)
        with gate.offline():
            cpu, cuda = (gate.relation_request(text, entities) for entities in (a, b))
        compare = lambda other: gate.compare_requests(cpu, other, 'Supplied entities:\n', r'/\d+/score')
        result = compare(cuda)
        self.assertEqual(result['classification'], 'SCORE_ONLY')
        self.assertEqual(result['score_literal_count'], 1)
        self.assertEqual(result['score_literal_length_changes'], 1)
        self.assertEqual(result['non_score_difference_count'], 0)
        for changed in ({**cuda, 'model': 'different'}, {**cuda, 'input': cuda['input'] + ' '},
                        {**cuda, 'input': cuda['input'].replace('Gene', 'Disease')}):
            self.assertEqual(compare(changed)['classification'], 'STRUCTURAL')
        self.assertEqual(compare(cpu)['classification'], 'IDENTICAL')

    def test_offline_guard_forbids_real_client_and_network(self):
        import openai
        with gate.offline():
            with self.assertRaisesRegex(AssertionError, 'Real provider'):
                openai.OpenAI(api_key='unused')
            with self.assertRaisesRegex(AssertionError, 'Network'):
                socket.create_connection(('127.0.0.1', 1))
        recorder = gate.Recorder({'relations': []})
        recorder.create(input='one')
        with self.assertRaisesRegex(ValueError, 'second generation'):
            recorder.create(input='two')

    @unittest.skipUnless((gate.CPU / 'raw.json').exists() and (gate.CUDA / 'raw.json').exists(), 'Retained AWS evidence required')
    def test_all_seven_retained_cases_and_fixed_baseline_role_requests(self):
        summary, details = gate.analyze()
        self.assertEqual(summary['final_disposition'], 'NUMERIC_ONLY')
        self.assertEqual(summary['provider_submission_count'], 0)
        self.assertEqual(set(summary['cases']), set(gate.COUNTS))
        for name, case in summary['cases'].items():
            self.assertTrue(case['hard_fields_equal'])
            self.assertEqual(case['entity_count'], gate.COUNTS[name])
            for field in ('assembly', 'relation_request', 'empty_response_graph'):
                self.assertEqual(case[field]['classification'], 'SCORE_ONLY')
                self.assertEqual(case[field]['non_score_difference_count'], 0)
            self.assertEqual(case['relation_request']['different_score_literals'], case['ner']['score_difference_count'])
        for name in gate.BASELINES:
            role = summary['cases'][name]['role']
            self.assertEqual(role['target_count'], 6)
            for field in ('targets', 'graph', 'request'):
                self.assertEqual(role[field]['classification'], 'SCORE_ONLY')
                self.assertEqual(role[field]['non_score_difference_count'], 0)
        self.assertEqual(sum(c['role']['coverage'] == 'unavailable' for c in summary['cases'].values()), 5)
        # Complete exact request dictionaries are retained for independent audit.
        self.assertEqual(len(details), 7)

    @unittest.skipUnless((gate.CUDA / 'comparison.json').exists(), 'Retained AWS evidence required')
    def test_corrupt_comparison_is_rejected_without_rewriting_evidence(self):
        original_read = gate.read

        def corrupted(path):
            value = original_read(path)
            if path == gate.CUDA / 'comparison.json':
                value = copy.deepcopy(value)
                value['cases']['sfpq-passage']['score_difference_count'] += 1
            return value

        with patch.object(gate, 'read', side_effect=corrupted), self.assertRaisesRegex(ValueError, 'does not represent'):
            gate.verify_evidence()


if __name__ == '__main__':
    unittest.main()
