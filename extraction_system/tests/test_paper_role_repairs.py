"""Offline behavior checks for isolated, bounded paper-role repair."""
import json
import unittest
from unittest.mock import Mock

from biomedical_extractor.llm_paper_roles import (
    LLMPaperRoleExtractor, PaperRoleExtractionError,
    PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT,
)
from biomedical_extractor.paper_roles import PaperRoleTarget, PaperRoleValidationError


def role(node_id, **changes):
    return {"node_id": node_id, "category": "substantive",
            "paragraphs": ["GeneX was measured."], "evidence": ["GeneX"], **changes}


class PaperRoleRepairTests(unittest.TestCase):
    def setUp(self):
        self.targets = tuple(PaperRoleTarget(n, n, 'Gene', ()) for n in ('A', 'B', 'C'))

    def extractor(self, *responses, retries=2):
        model = Mock(spec=['invoke'])
        model.invoke.side_effect = responses
        return LLMPaperRoleExtractor(model, max_retries=retries), model

    def requested(self, model):
        return [json.loads(call.args[0].split('Requested entities and all source mentions:\n')[1]
                           .split('\n\nPaper title:')[0]) for call in model.invoke.call_args_list]

    def test_preserves_valid_records_repairs_only_invalid_and_missing_in_order(self):
        first = role('A', paragraphs=['Original valid prose.'])
        extractor, model = self.extractor(
            {'roles': [role('B', evidence=['invented']), first]},
            {'roles': [role('C'), role('B', evidence=['still invented'])]},
            {'roles': [role('B')]},
        )
        result = extractor.extract_roles('Title', 'GeneX was measured.', self.targets)
        self.assertEqual([r.node_id for r in result.records], ['A', 'B', 'C'])
        self.assertEqual(result.records[0].role.paragraphs, ('Original valid prose.',))
        self.assertEqual([[t['node_id'] for t in req] for req in self.requested(model)],
                         [['A', 'B', 'C'], ['B', 'C'], ['B']])
        self.assertIn('verbatim', model.invoke.call_args_list[1].args[0])
        self.assertEqual([d['validated_role_count'] for d in extractor.last_generation_diagnostics], [1, 2, 3])

    def test_duplicate_and_malformed_records_are_isolated(self):
        extractor, model = self.extractor(
            {'roles': [role('A'), role('B'), role('B'), role('C', paragraphs='invalid')]},
            {'roles': [role('C'), role('B')]},
        )
        result = extractor.extract_roles('Title', 'GeneX', self.targets)
        self.assertEqual(len(result.records), 3)
        self.assertEqual([t['node_id'] for t in self.requested(model)[1]], ['B', 'C'])
        self.assertEqual(extractor.last_generation_diagnostics[0]['failed_target_errors']['B'], 'Duplicate records')

    def test_exhaustion_preserves_valid_records_and_stops_at_budget(self):
        extractor, model = self.extractor({'roles': [role('A')]}, {'roles': []}, {'roles': []})
        with self.assertRaisesRegex(PaperRoleExtractionError, '3 bounded attempt'):
            extractor.extract_roles('Title', 'GeneX', self.targets)
        self.assertEqual(model.invoke.call_count, 3)
        self.assertEqual([r.node_id for r in extractor.last_validated_result.records], ['A'])
        self.assertEqual(set(extractor.last_generation_diagnostics[-1]['failed_target_errors']), {'B', 'C'})

    def test_unsolicited_or_unattributable_record_fails_closed_preserving_valid(self):
        for extra in (role('unknown'), {'category': 'substantive'}, None, role([])):
            with self.subTest(extra=extra):
                extractor, model = self.extractor({'roles': [role('A'), extra]})
                with self.assertRaisesRegex(PaperRoleExtractionError, 'invalid record IDs'):
                    extractor.extract_roles('Title', 'GeneX', self.targets)
                self.assertEqual(model.invoke.call_count, 1)
                self.assertEqual([r.node_id for r in extractor.last_validated_result.records], ['A'])

    def test_repair_cannot_overwrite_accepted_record(self):
        extractor, model = self.extractor({'roles': [role('A')]}, {'roles': [role('A'), role('B'), role('C')]})
        with self.assertRaisesRegex(PaperRoleExtractionError, 'invalid record IDs'):
            extractor.extract_roles('Title', 'GeneX', self.targets)
        self.assertEqual(model.invoke.call_count, 2)
        self.assertEqual(extractor.last_validated_result.records[0].role.paragraphs, ('GeneX was measured.',))

    def test_species_and_organism_require_contextual_without_coercion(self):
        for kind in ('Species', 'Organism'):
            with self.subTest(kind=kind):
                target = PaperRoleTarget('A', 'model', kind, ())
                extractor, model = self.extractor({'roles': [role('A')]},
                                                   {'roles': [role('A', category='contextual')]})
                result = extractor.extract_roles('Title', 'GeneX', (target,))
                self.assertEqual(result.records[0].role.category, 'contextual')
                self.assertEqual(model.invoke.call_count, 2)
        self.assertIn('Species or Organism MUST use category "contextual"', PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT)

    def test_invalid_envelope_retries_only_unresolved_and_provider_failure_stops(self):
        extractor, model = self.extractor({'roles': [role('A')]}, 'not json', RuntimeError('unavailable'))
        with self.assertRaisesRegex(PaperRoleExtractionError, 'provider invocation failed'):
            extractor.extract_roles('Title', 'GeneX', self.targets)
        self.assertEqual([r.node_id for r in extractor.last_validated_result.records], ['A'])
        self.assertEqual([t['node_id'] for t in self.requested(model)[2]], ['B', 'C'])

    def test_empty_and_duplicate_inputs_do_not_submit_and_state_resets(self):
        extractor, model = self.extractor({'roles': [role('A')]})
        extractor.extract_roles('Title', 'GeneX', self.targets[:1])
        self.assertEqual(extractor.extract_roles('Title', 'GeneX', ()).records, ())
        self.assertEqual(extractor.last_validated_result.records, ())
        with self.assertRaises(PaperRoleValidationError):
            extractor.extract_roles('Title', 'GeneX', self.targets[:1] * 2)
        self.assertEqual(model.invoke.call_count, 1)
