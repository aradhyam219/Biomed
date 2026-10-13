from pathlib import Path
import json, unittest
from biomedical_extractor.hunflair2 import HunFlair2BioMedExtractor
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.paper_roles import PaperRole, PaperRoleRecord, PaperRoleExtractionResult
from biomedical_extractor.relation_extraction import validate_relations

FIXTURES = Path(__file__).parent / 'fixtures' / 'baseline'

class BaselineReplayTests(unittest.TestCase):
    def test_saved_stages_reproduce_complete_accepted_graphs(self):
        for path in sorted(FIXTURES.glob('*.json')):
            with self.subTest(case=path.name):
                case = json.loads(path.read_text(encoding='utf-8'))
                class NER:
                    def predict_entities(self, text):
                        self_test.assertEqual(text, case['text'])
                        return sorted(case['ner_predictions'], key=lambda r: next(int(e['id'][1:]) for e in case['entities'] if e['start']==r['start'] and e['end']==r['end']))
                class RE:
                    def extract_relations(self, text, entities):
                        self_test.assertEqual([e.to_dict() for e in entities], case['entities'])
                        return validate_relations(text, entities, case['relations'])
                class Roles:
                    def extract_roles(self, paper_title, text, targets):
                        self_test.assertEqual(text, case['text'])
                        self_test.assertEqual(paper_title, case['paper_title'])
                        self_test.assertEqual({t.node_id for t in targets}, {r['node_id'] for r in case['roles']})
                        return PaperRoleExtractionResult(tuple(PaperRoleRecord(r['node_id'], PaperRole(**r['paper_role'])) for r in case['roles']))
                self_test = self
                normalized = HunFlair2BioMedExtractor(NER()).extract_entities(case['text'])
                self.assertEqual({e.id: e.to_dict() for e in normalized}, {e['id']: e for e in case['entities']})
                class SavedNER:
                    def extract_entities(self, text):
                        by_id = {e.id: e for e in normalized}
                        return tuple(by_id[e['id']] for e in case['entities'])
                # The recorded RE input order is retained, including its original IDs.
                pipeline = LLMExtractionPipeline(SavedNER(), RE(), Roles() if case['roles'] else None)
                graph = pipeline.extract_graph(case['text'], document_id=case['document_id'], paper_title=case['paper_title'])
                self.assertEqual(graph.to_dict(), case['expected_graph'])
                self.assertEqual(json.loads(graph.to_json()), case['expected_graph'])
                from biomedical_extractor import export_graph, ExportContext, contract_resource, validate_graph
                from importlib.metadata import version
                context = ExportContext(version('biomedical-extractor'), 'a' * 40, contract_resource('baseline-profile.json'))
                exported = export_graph(graph, text=case['text'], paper_title=case['paper_title'], context=context, generated_at='2026-10-13T00:00:00Z')
                self.assertEqual({k: exported[k] for k in ('document', 'nodes', 'edges')}, case['expected_graph'])
                validate_graph(exported, text=case['text'], paper_title=case['paper_title'])

if __name__ == '__main__':
    unittest.main()
