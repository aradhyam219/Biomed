"""No network: bounded saved-state role replay through the real role harness."""
from importlib.metadata import version
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.graph import GraphDocument, GraphNode, GraphResult
from biomedical_extractor.graph_contract import ExportContext, delivery_profile, validate_graph
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.paper_roles import PaperRoleTarget
from tools import phase2_role_replay as replay


class Response:
    def __init__(self, roles):
        self.id, self.status = 'resp_test', 'completed'
        self.output_text = json.dumps({'roles': roles})
        self.output, self.error, self.incomplete_details = [], None, None

    def model_dump(self, **kwargs):
        return {'id': self.id, 'status': self.status, 'output_text': self.output_text}


class RoleReplayTests(unittest.TestCase):
    def test_role_only_replay_preserves_graph_exports_and_cannot_restart(self):
        packet = {'text': 'GeneX', 'paper_title': 'Title', 'document_id': 'paper'}
        graph = GraphResult(GraphDocument('paper'), (GraphNode('A', 'GeneX', 'Gene', (Entity('E1', 'GeneX', 'Gene', 0, 5),)),), ())
        targets = (PaperRoleTarget('A', 'GeneX', 'Gene', graph.nodes[0].mentions),)
        good = {'node_id': 'A', 'category': 'substantive', 'paragraphs': ['GeneX was measured.'], 'evidence': ['GeneX']}
        config = OpenAIConfig(api_key='offline-test')
        ctx = ExportContext(version('biomedical-extractor'), 'a' * 40, delivery_profile('cuda'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (patch.object(replay, 'ROOT', root),
                  patch.object(replay, 'OUTPUT', root / 'output'),
                  patch.object(replay, 'MARKER', root / 'started.json'),
                  patch.object(replay, 'REPORT', root / 'report.json'),
                  patch.object(replay, 'prepare', return_value=(packet, graph, targets, {})),
                  patch.object(replay, 'release_context', return_value=ctx),
                  patch.object(replay.OpenAIConfig, 'from_environment', return_value=config),
                  patch('openai.resources.responses.Responses.create', side_effect=[Response([]), Response([good])]) as create):
                result = replay.run()
                self.assertEqual(result['status'], 'passed', result)
                self.assertEqual((result['provider_submissions'], result['provider_repairs']), (2, 1))
                exported = json.loads((root / 'output/graph-v1.json').read_text())
                self.assertTrue(validate_graph(exported, text='GeneX', paper_title='Title').source_checked)
                self.assertEqual(exported['edges'], [])
                self.assertEqual(exported['nodes'][0]['paper_role']['evidence'], ['GeneX'])
                self.assertTrue(all(c.kwargs['text']['format']['name'] == 'StructuredPaperRolePayload'
                                    for c in create.call_args_list))
                with self.assertRaisesRegex(ValueError, 'already started'):
                    replay.run()
                self.assertEqual(create.call_count, 2)

    def test_reservation_precedes_submission_and_cap_survives_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            budget = replay.ReplayBudget(path)
            recorder = replay.RecordedResponses(SimpleNamespace(create=lambda **kwargs: self.fail('Not reached')),
                                                budget, 'roles', Path(directory), {}, ())
            for generation in (1, 2, 3):
                budget.reserve('roles', generation)
            with self.assertRaisesRegex(ValueError, 'out-of-budget'):
                recorder.create()
            self.assertEqual(len(json.loads(path.read_text())['submission_attempts']), 3)
            with self.assertRaisesRegex(ValueError, 'no repeat'):
                replay.ReplayBudget(path)
