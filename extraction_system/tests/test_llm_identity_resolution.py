from __future__ import annotations

import unittest
from unittest.mock import patch

from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.entity_assembly import _assemble_document_entities
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.identity_resolution import (
    ExplicitIdentityCandidate,
    ExplicitIdentityResult,
    find_unresolved_explicit_identity_candidates,
    validate_explicit_identity_result,
)
from biomedical_extractor.llm_identity_resolution import (
    ExplicitIdentityVerificationError,
    LLMExplicitIdentityVerifier,
)
from biomedical_extractor.llm_relation_extraction import OpenAIConfig


def _fixture():
    text = (
        "Prior work on SFPQ. Splicing factor proline and glutamine rich (SFPQ) "
        "regulates a target."
    )
    long_form = "proline and glutamine rich"
    long_start = text.index(long_form)
    abbreviation_start = text.rindex("SFPQ")
    entities = (
        Entity("E1", long_form, "Gene", long_start, long_start + len(long_form)),
        Entity("E2", "SFPQ", "Gene", abbreviation_start, abbreviation_start + 4),
    )
    assembly = assemble_document_entities(entities, text)
    candidate = find_unresolved_explicit_identity_candidates(
        entities, text, assembly
    )[0]
    return text, candidate


def _payload(
    candidate,
    *,
    mention_ids=None,
    decision="same_identity_construction",
    evidence=None,
):
    return {
        "decisions": [
            {
                "candidate_id": candidate.candidate_id,
                "mention_ids": list(
                    candidate.mention_ids if mention_ids is None else mention_ids
                ),
                "decision": decision,
                "evidence": candidate.construction if evidence is None else evidence,
            }
        ]
    }


class _FakeStructuredModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []
        self.schema = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, prompt):
        self.prompts.append(prompt)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class LLMIdentityResolutionTests(unittest.TestCase):
    def test_one_bounded_structured_call_returns_provider_independent_result(self):
        text, candidate = _fixture()
        model = _FakeStructuredModel((_payload(candidate),))
        verifier = LLMExplicitIdentityVerifier(model)

        result = verifier.verify_explicit_identities(text, (candidate,))

        self.assertIsInstance(result, ExplicitIdentityResult)
        self.assertEqual(len(model.prompts), 1)
        self.assertIsNotNone(model.schema)
        self.assertIn(candidate.construction, model.prompts[0])
        self.assertIn('"mention_id": "E1"', model.prompts[0])
        self.assertIn('"mention_id": "E2"', model.prompts[0])
        self.assertIn('"source_construction"', model.prompts[0])
        self.assertIn('"construction_long_form"', model.prompts[0])
        self.assertIn("not whether any supplied NER mention surface is independently synonymous", model.prompts[0])
        self.assertNotIn('"score"', model.prompts[0])
        self.assertNotIn('"start"', model.prompts[0])
        self.assertNotIn('"long_form_group_id"', model.prompts[0])
        self.assertEqual(result.decisions[0].decision, "same_identity_construction")
        self.assertEqual(result.decisions[0].mention_ids, candidate.mention_ids)
        self.assertEqual(result.decisions[0].evidence, candidate.construction)

    def test_generic_fragmented_long_form_construction_maps_deterministically(self):
        # XARB is an explicit source-defined label that does not pass the
        # deterministic abbreviation aligner, so this exercises the verifier.
        text = "Alpha regulatory binding protein (XARB) was detected."
        fragment = "regulatory binding protein"
        fragment_start = text.index(fragment)
        abbreviation_start = text.index("XARB")
        entities = (
            Entity("G1", fragment, "Gene", fragment_start, fragment_start + len(fragment)),
            Entity("G2", "XARB", "Gene", abbreviation_start, abbreviation_start + 4),
        )
        assembly = assemble_document_entities(entities, text)
        candidates = find_unresolved_explicit_identity_candidates(
            entities, text, assembly
        )
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]

        model = _FakeStructuredModel((_payload(candidate),))
        result = LLMExplicitIdentityVerifier(model).verify_explicit_identities(
            text, candidates
        )
        pairs = validate_explicit_identity_result(text, candidates, result)
        resolved = _assemble_document_entities(
            entities, text, verified_identity_pairs=pairs
        )

        self.assertEqual(candidate.construction, "Alpha regulatory binding protein (XARB)")
        self.assertEqual(candidate.long_form, "Alpha regulatory binding protein")
        self.assertEqual(tuple(item.text for item in candidate.long_form_mentions), (fragment,))
        self.assertEqual(result.decisions[0].decision, "same_identity_construction")
        self.assertEqual(result.decisions[0].evidence, candidate.construction)
        self.assertEqual(pairs, (("G1", "G2"),))
        self.assertEqual(
            resolved.mention_to_document_entity["G1"],
            resolved.mention_to_document_entity["G2"],
        )
        self.assertIn('"text": "regulatory binding protein"', model.prompts[0])
        self.assertIn('"construction_long_form": "Alpha regulatory binding protein"', model.prompts[0])

    def test_arb_positive_verifies_the_complete_source_construction(self):
        text = "Alpha regulatory binding protein (ARB) was detected."
        fragment = "regulatory binding protein"
        fragment_start = text.index(fragment)
        abbreviation_start = text.index("ARB")
        fragment_mention = Entity(
            "A1", fragment, "Gene", fragment_start, fragment_start + len(fragment)
        )
        abbreviation_mention = Entity(
            "A2", "ARB", "Gene", abbreviation_start, abbreviation_start + 3
        )
        construction = "Alpha regulatory binding protein (ARB)"
        # ARB is already handled by deterministic abbreviation alignment in
        # normal discovery; this synthetic candidate isolates the corrected
        # verifier contract for a full source phrase plus a contained fragment.
        candidate = ExplicitIdentityCandidate(
            candidate_id="identity_arb",
            construction=construction,
            construction_start=text.index(construction),
            construction_end=text.index(construction) + len(construction),
            long_form="Alpha regulatory binding protein",
            abbreviation="ARB",
            long_form_group_id="before-long-form",
            abbreviation_group_id="before-abbreviation",
            long_form_mentions=(fragment_mention,),
            abbreviation_mentions=(abbreviation_mention,),
        )
        model = _FakeStructuredModel((_payload(candidate),))
        result = LLMExplicitIdentityVerifier(model).verify_explicit_identities(
            text, (candidate,)
        )
        pairs = validate_explicit_identity_result(text, (candidate,), result)
        resolved = _assemble_document_entities(
            (fragment_mention, abbreviation_mention),
            text,
            verified_identity_pairs=pairs,
        )

        self.assertEqual(result.decisions[0].decision, "same_identity_construction")
        self.assertEqual(result.decisions[0].evidence, construction)
        self.assertEqual(pairs, (("A1", "A2"),))
        self.assertEqual(
            resolved.mention_to_document_entity["A1"],
            resolved.mention_to_document_entity["A2"],
        )
        self.assertIn('"text": "regulatory binding protein"', model.prompts[0])
        self.assertIn('"text": "ARB"', model.prompts[0])
        self.assertIn('"source_construction": "Alpha regulatory binding protein (ARB)"', model.prompts[0])

    def test_invalid_first_result_uses_one_finite_repair_attempt(self):
        text, candidate = _fixture()
        model = _FakeStructuredModel(
            (
                _payload(candidate, mention_ids=("E1", "unknown")),
                _payload(candidate),
            )
        )
        verifier = LLMExplicitIdentityVerifier(model, max_retries=1)

        result = verifier.verify_explicit_identities(text, (candidate,))

        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(len(model.prompts), 2)
        self.assertIn("REPAIR INSTRUCTION", model.prompts[1])

    def test_candidate_batch_is_local_and_empty_batch_makes_no_model_call(self):
        _, original_candidate = _fixture()
        full_text = f"Unrelated content appears first. {original_candidate.construction} regulates a target."
        long_form = "proline and glutamine rich"
        long_start = full_text.index(long_form)
        abbreviation_start = full_text.rindex("SFPQ")
        entities = (
            Entity("E1", long_form, "Gene", long_start, long_start + len(long_form)),
            Entity("E2", "SFPQ", "Gene", abbreviation_start, abbreviation_start + 4),
        )
        assembly = assemble_document_entities(entities, full_text)
        candidate = find_unresolved_explicit_identity_candidates(
            entities, full_text, assembly
        )[0]
        model = _FakeStructuredModel((_payload(candidate),))
        verifier = LLMExplicitIdentityVerifier(model)

        verifier.verify_explicit_identities(full_text, (candidate,))
        self.assertEqual(len(model.prompts), 1)
        self.assertNotIn("Unrelated content", model.prompts[0])

        empty_model = _FakeStructuredModel(())
        empty_verifier = LLMExplicitIdentityVerifier(empty_model)
        self.assertEqual(empty_verifier.verify_explicit_identities("", ()).decisions, ())
        self.assertEqual(empty_model.prompts, [])

    def test_provider_factory_reuses_the_shared_openai_configuration(self):
        config = OpenAIConfig(model="gpt-6-luna", api_key="test-key")
        model = _FakeStructuredModel(())
        with patch(
            "biomedical_extractor.llm_identity_resolution._create_openai_chat_model",
            return_value=model,
        ) as create_model:
            verifier = LLMExplicitIdentityVerifier.from_openai(config)

        self.assertIsInstance(verifier, LLMExplicitIdentityVerifier)
        self.assertEqual(verifier._max_retries, config.max_retries)
        create_model.assert_called_once_with(config)

    def test_parser_rejects_unknown_decisions(self):
        text, candidate = _fixture()
        model = _FakeStructuredModel(
            (_payload(candidate, decision="probably_same_identity_construction"),)
        )
        verifier = LLMExplicitIdentityVerifier(model, max_retries=0)

        with self.assertRaises(ExplicitIdentityVerificationError):
            verifier.verify_explicit_identities(text, (candidate,))


if __name__ == "__main__":
    unittest.main()
