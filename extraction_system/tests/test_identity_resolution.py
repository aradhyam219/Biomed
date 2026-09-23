from __future__ import annotations

import unittest
from dataclasses import replace

from biomedical_extractor.entity_assembly import (
    _assemble_document_entities,
    assemble_document_entities,
)
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.identity_resolution import (
    ExplicitIdentityDecision,
    ExplicitIdentityResult,
    ExplicitIdentityValidationError,
    find_unresolved_explicit_identity_candidates,
    validate_explicit_identity_result,
)


def _sfpq_fixture():
    text = (
        "Prior work on SFPQ. Splicing factor proline and glutamine rich (SFPQ) "
        "regulates a target. Citrate was included."
    )
    earlier_sfpq = text.index("SFPQ")
    long_form = "proline and glutamine rich"
    long_form_start = text.index(long_form)
    abbreviation_start = text.rindex("SFPQ")
    target_start = text.index("target")
    citrate_start = text.index("Citrate")
    entities = (
        Entity("E1", "SFPQ", "Gene", earlier_sfpq, earlier_sfpq + 4, 0.9),
        Entity(
            "E2",
            long_form,
            "Gene",
            long_form_start,
            long_form_start + len(long_form),
            0.8,
        ),
        Entity("E3", "SFPQ", "Gene", abbreviation_start, abbreviation_start + 4, 0.95),
        Entity("E4", "SFPQ", "Chemical", abbreviation_start, abbreviation_start + 4, 0.4),
        Entity("E5", "target", "Protein", target_start, target_start + len("target")),
        Entity("E6", "Citrate", "Chemical", citrate_start, citrate_start + len("Citrate")),
    )
    assembly = assemble_document_entities(entities, text)
    candidates = find_unresolved_explicit_identity_candidates(entities, text, assembly)
    return text, entities, assembly, candidates


def _decision(
    candidate,
    decision="same_identity_construction",
    *,
    evidence=None,
    mention_ids=None,
):
    return ExplicitIdentityDecision(
        candidate.candidate_id,
        candidate.mention_ids if mention_ids is None else tuple(mention_ids),
        decision,
        candidate.construction if evidence is None else evidence,
    )


class ExplicitIdentityResolutionTests(unittest.TestCase):
    def test_candidate_is_bounded_verbatim_and_keeps_same_type_mentions_only(self):
        text, entities, assembly, candidates = _sfpq_fixture()

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(
            candidate.construction,
            "Splicing factor proline and glutamine rich (SFPQ)",
        )
        self.assertEqual(candidate.long_form, "Splicing factor proline and glutamine rich")
        self.assertEqual(tuple(entity.id for entity in candidate.long_form_mentions), ("E2",))
        self.assertEqual(tuple(entity.id for entity in candidate.abbreviation_mentions), ("E3",))
        self.assertNotIn("E4", candidate.mention_ids)
        self.assertEqual(
            text[candidate.construction_start : candidate.construction_end],
            candidate.construction,
        )
        self.assertNotEqual(
            candidate.long_form_group_id, candidate.abbreviation_group_id
        )

    def test_grounded_identity_construction_merges_only_compatible_mentions(self):
        text, entities, assembly, candidates = _sfpq_fixture()
        candidate = candidates[0]
        result = ExplicitIdentityResult((_decision(candidate),))

        pairs = validate_explicit_identity_result(text, candidates, result)
        resolved = _assemble_document_entities(
            entities, text, verified_identity_pairs=pairs
        )

        self.assertEqual(pairs, (("E2", "E3"),))
        self.assertEqual(
            resolved.mention_to_document_entity["E2"],
            resolved.mention_to_document_entity["E3"],
        )
        self.assertEqual(
            resolved.mention_to_document_entity["E3"],
            resolved.mention_to_document_entity["E1"],
        )
        self.assertNotEqual(
            resolved.mention_to_document_entity["E3"],
            resolved.mention_to_document_entity["E4"],
        )
        self.assertEqual(assembly.mention_to_document_entity["E2"], "doc_e_002")
        self.assertEqual(entities[1].text, "proline and glutamine rich")
        self.assertEqual(entities[1].score, 0.8)

    def test_negative_and_uncertain_decisions_never_merge(self):
        text, _, _, candidates = _sfpq_fixture()
        candidate = candidates[0]
        for value in ("not_identity_construction", "uncertain"):
            with self.subTest(decision=value):
                pairs = validate_explicit_identity_result(
                    text,
                    candidates,
                    ExplicitIdentityResult((_decision(candidate, value),)),
                )
                self.assertEqual(pairs, ())

    def test_invalid_evidence_unknown_ids_duplicate_and_missing_outputs_fail_closed(self):
        text, _, _, candidates = _sfpq_fixture()
        candidate = candidates[0]
        invalid_results = (
            ExplicitIdentityResult(
                (_decision(candidate, evidence="SFPQ"),)
            ),
            ExplicitIdentityResult(
                (_decision(candidate, mention_ids=(*candidate.mention_ids, "E999")),)
            ),
            ExplicitIdentityResult((_decision(candidate), _decision(candidate))),
            ExplicitIdentityResult(()),
        )
        for result in invalid_results:
            with self.subTest(result=result), self.assertRaises(
                ExplicitIdentityValidationError
            ):
                validate_explicit_identity_result(text, candidates, result)

    def test_incompatible_types_cannot_be_merged_even_with_exact_evidence(self):
        text, _, _, candidates = _sfpq_fixture()
        candidate = candidates[0]
        chemical_abbreviation = replace(
            candidate.abbreviation_mentions[0], type="Chemical"
        )
        incompatible = replace(
            candidate, abbreviation_mentions=(chemical_abbreviation,)
        )
        result = ExplicitIdentityResult((_decision(incompatible),))

        with self.assertRaises(ExplicitIdentityValidationError):
            validate_explicit_identity_result(text, (incompatible,), result)

    def test_incompatible_parenthetical_mentions_are_not_eligible(self):
        text = "Splicing factor proline and glutamine rich (SFPQ) regulates a target."
        long_form = "proline and glutamine rich"
        long_start = text.index(long_form)
        abbreviation_start = text.index("SFPQ")
        entities = (
            Entity("E1", long_form, "Gene", long_start, long_start + len(long_form)),
            Entity("E2", "SFPQ", "Chemical", abbreviation_start, abbreviation_start + 4),
        )
        assembly = assemble_document_entities(entities, text)

        candidates = find_unresolved_explicit_identity_candidates(
            entities, text, assembly
        )

        self.assertEqual(candidates, ())
        self.assertEqual(len(assembly.document_entities), 2)

    def test_ambiguous_or_non_naming_parentheticals_are_not_eligible(self):
        text = "A and B (AB) were compared. GeneX (GeneY) was also measured."
        forms = (
            ("A", "Gene"),
            ("B", "Gene"),
            ("AB", "Gene"),
            ("GeneX", "Gene"),
            ("GeneY", "Gene"),
        )
        entities = tuple(
            Entity(
                f"E{index}", form, entity_type, text.index(form), text.index(form) + len(form)
            )
            for index, (form, entity_type) in enumerate(forms, start=1)
        )
        assembly = assemble_document_entities(entities, text)

        candidates = find_unresolved_explicit_identity_candidates(
            entities, text, assembly
        )

        self.assertEqual(candidates, ())
        self.assertEqual(len(assembly.document_entities), len(entities))

        compound_text = (
            "Cbl, JAK2, runt-related transcription factor 3 (Runx3) was measured."
        )
        compound_forms = (
            ("Cbl", "Gene"),
            ("JAK2", "Gene"),
            ("runt-related transcription factor 3", "Gene"),
            ("Runx3", "Gene"),
        )
        compound_entities = tuple(
            Entity(
                f"C{index}",
                form,
                entity_type,
                compound_text.index(form),
                compound_text.index(form) + len(form),
            )
            for index, (form, entity_type) in enumerate(compound_forms, start=1)
        )
        compound_assembly = assemble_document_entities(compound_entities, compound_text)
        compound_candidates = find_unresolved_explicit_identity_candidates(
            compound_entities, compound_text, compound_assembly
        )

        self.assertEqual(compound_candidates, ())

        adversarial = (
            ("cells (control) were collected.", "cells", "control"),
            ("mice (adult) were studied.", "mice", "adult"),
            ("protein expression (high) was recorded.", "protein expression", "high"),
            ("drug treatment (treated) was assigned.", "drug treatment", "treated"),
            ("patients (n=20) were recruited.", "patients", "n=20"),
            ("GeneA (GeneB) was measured.", "GeneA", "GeneB"),
        )
        for index, (prose, long_form, parenthetical) in enumerate(adversarial):
            with self.subTest(source=prose):
                long_start = prose.index(long_form)
                short_start = prose.index(parenthetical)
                prose_mentions = (
                    Entity(
                        f"N{index}a",
                        long_form,
                        "Gene",
                        long_start,
                        long_start + len(long_form),
                    ),
                    Entity(
                        f"N{index}b",
                        parenthetical,
                        "Gene",
                        short_start,
                        short_start + len(parenthetical),
                    ),
                )
                prose_candidates = find_unresolved_explicit_identity_candidates(
                    prose_mentions,
                    prose,
                    assemble_document_entities(prose_mentions, prose),
                )
                self.assertEqual(prose_candidates, ())

        prose_text = "Alpha regulatory binding protein (for comparison) was measured."
        prose_entities = (
            Entity(
                "P1",
                "Alpha regulatory binding protein",
                "Gene",
                0,
                len("Alpha regulatory binding protein"),
            ),
            Entity(
                "P2",
                "comparison",
                "Gene",
                prose_text.index("comparison"),
                prose_text.index("comparison") + len("comparison"),
            ),
        )
        prose_assembly = assemble_document_entities(prose_entities, prose_text)
        prose_candidates = find_unresolved_explicit_identity_candidates(
            prose_entities, prose_text, prose_assembly
        )

        self.assertEqual(prose_candidates, ())


if __name__ == "__main__":
    unittest.main()
