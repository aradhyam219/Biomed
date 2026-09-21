from __future__ import annotations

import unittest

from biomedical_extractor.entity_assembly import (
    DocumentEntity,
    DocumentEntityAssembly,
    assemble_document_entities,
)
from biomedical_extractor.entity_extraction import Entity


class DocumentEntityAssemblyTests(unittest.TestCase):
    def test_exact_repeated_mentions_share_one_node_and_remain_preserved(self):
        text = "KNTC1 interacts with KNTC1."
        second_start = text.rindex("KNTC1")
        mentions = (
            Entity("E1", "KNTC1", "Gene", 0, 5, 0.91),
            Entity("E2", "KNTC1", "Gene", second_start, second_start + 5, 0.87),
        )

        result = assemble_document_entities(mentions, text)

        self.assertIsInstance(result, DocumentEntityAssembly)
        self.assertEqual(len(result.document_entities), 1)
        document_entity = result.document_entities[0]
        self.assertIsInstance(document_entity, DocumentEntity)
        self.assertEqual(document_entity.entity_id, "doc_e_001")
        self.assertEqual(document_entity.mentions, mentions)
        self.assertEqual(
            result.mention_to_document_entity,
            {"E1": "doc_e_001", "E2": "doc_e_001"},
        )

    def test_different_surface_forms_without_source_alias_evidence_stay_separate(self):
        text = "KNTC1 and KNTC2 were measured."
        first_start = text.index("KNTC1")
        second_start = text.index("KNTC2")
        mentions = (
            Entity("E1", "KNTC1", "Gene", first_start, first_start + 5),
            Entity("E2", "KNTC2", "Gene", second_start, second_start + 5),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(
            tuple(entity.label for entity in result.document_entities),
            ("KNTC1", "KNTC2"),
        )
        self.assertEqual(
            result.mention_to_document_entity,
            {"E1": "doc_e_001", "E2": "doc_e_002"},
        )

    def test_incompatible_types_are_not_merged(self):
        text = "BRCA1"
        mentions = (
            Entity("E1", text, "Gene", 0, len(text), 0.7),
            Entity("E2", text, "Protein", 0, len(text), 0.9),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 2)
        self.assertEqual(
            tuple(entity.type for entity in result.document_entities),
            ("Gene", "Protein"),
        )
        self.assertEqual(
            result.mention_to_document_entity,
            {"E1": "doc_e_001", "E2": "doc_e_002"},
        )

    def test_explicit_full_form_abbreviation_pair_is_merged_conservatively(self):
        text = "kinetochore-associated protein 1 (KNTC1) is important."
        full_form = "kinetochore-associated protein 1"
        full_start = text.index(full_form)
        abbreviation_start = text.index("KNTC1")
        mentions = (
            Entity("E1", full_form, "Gene", full_start, full_start + len(full_form)),
            Entity("E2", "KNTC1", "Gene", abbreviation_start, abbreviation_start + 5),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 1)
        document_entity = result.document_entities[0]
        self.assertEqual(document_entity.label, "KNTC1")
        self.assertEqual(document_entity.aliases, (full_form, "KNTC1"))
        self.assertEqual(document_entity.mention_ids, ("E1", "E2"))
        self.assertEqual(
            result.mention_to_document_entity,
            {"E1": "doc_e_001", "E2": "doc_e_001"},
        )

    def test_incompatible_alias_types_are_kept_separate(self):
        text = "kinetochore-associated protein 1 (KNTC1)"
        full_form = "kinetochore-associated protein 1"
        full_start = text.index(full_form)
        abbreviation_start = text.index("KNTC1")
        mentions = (
            Entity("E1", full_form, "Gene", full_start, full_start + len(full_form)),
            Entity("E2", "KNTC1", "Protein", abbreviation_start, abbreviation_start + 5),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 2)
        self.assertEqual(
            result.mention_to_document_entity,
            {"E1": "doc_e_001", "E2": "doc_e_002"},
        )

    def test_fragmented_long_form_mentions_join_only_with_explicit_abbreviation(self):
        text = "enhancer of zeste homologue 2 (EZH2) was measured."
        first = text.index("enhancer of zeste")
        second = text.index("homologue 2")
        abbreviation = text.index("EZH2")
        mentions = (
            Entity("E1", "enhancer of zeste", "Gene", first, first + len("enhancer of zeste")),
            Entity("E2", "homologue 2", "Gene", second, second + len("homologue 2")),
            Entity("E3", "EZH2", "Gene", abbreviation, abbreviation + 4),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 1)
        self.assertEqual(result.document_entities[0].label, "EZH2")
        self.assertEqual(result.document_entities[0].mention_ids, ("E1", "E2", "E3"))
        for mention in result.document_entities[0].mentions:
            self.assertEqual(text[mention.start : mention.end], mention.text)

    def test_adjacent_prefix_fragment_joins_to_an_aligned_long_form_suffix(self):
        text = "chromatin group factor enhancer of silencing 2 (ES2) was measured."
        prefix = "chromatin group factor"
        suffix = "enhancer of silencing 2"
        prefix_start = text.index(prefix)
        suffix_start = text.index(suffix)
        abbreviation_start = text.index("ES2")
        mentions = (
            Entity("E1", prefix, "Gene", prefix_start, prefix_start + len(prefix)),
            Entity("E2", suffix, "Gene", suffix_start, suffix_start + len(suffix)),
            Entity("E3", "ES2", "Gene", abbreviation_start, abbreviation_start + 3),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 1)
        self.assertEqual(result.document_entities[0].mention_ids, ("E1", "E2", "E3"))

    def test_camel_case_abbreviation_aligns_without_entity_specific_logic(self):
        text = "cell lineage binder (Clb) was measured."
        full = "cell lineage binder"
        full_start = text.index(full)
        abbreviation_start = text.index("Clb")
        mentions = (
            Entity("E1", full, "Gene", full_start, full_start + len(full)),
            Entity("E2", "Clb", "Gene", abbreviation_start, abbreviation_start + 3),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 1)
        self.assertEqual(result.document_entities[0].aliases, (full, "Clb"))

    def test_ambiguous_parenthetical_text_does_not_create_an_alias(self):
        text = "samples (AB) were compared with controls."
        sample_start = text.index("samples")
        abbreviation_start = text.index("AB")
        mentions = (
            Entity("E1", "samples", "Disease", sample_start, sample_start + len("samples")),
            Entity("E2", "AB", "Disease", abbreviation_start, abbreviation_start + 2),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 2)
        self.assertEqual(result.mention_to_document_entity, {"E1": "doc_e_001", "E2": "doc_e_002"})

    def test_no_general_synonym_guessing_without_source_naming_evidence(self):
        text = "myocardial infarction was compared with heart attack records."
        first = text.index("myocardial infarction")
        second = text.index("heart attack")
        mentions = (
            Entity("E1", "myocardial infarction", "Disease", first, first + len("myocardial infarction")),
            Entity("E2", "heart attack", "Disease", second, second + len("heart attack")),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 2)

    def test_parenthetical_prose_with_one_capital_does_not_merge(self):
        text = "samples (Sample) were used as a model."
        first = text.index("samples")
        second = text.index("Sample")
        mentions = (
            Entity("E1", "samples", "Disease", first, first + len("samples")),
            Entity("E2", "Sample", "Disease", second, second + len("Sample")),
        )

        result = assemble_document_entities(mentions, text)

        self.assertEqual(len(result.document_entities), 2)

    def test_ids_and_mapping_are_deterministic_and_spans_are_unchanged(self):
        text = "Aspirin treats disease; aspirin helps."
        first_start = text.index("Aspirin")
        second_start = text.index("aspirin")
        disease_start = text.index("disease")
        mentions = (
            Entity("E1", "Aspirin", "Chemical", first_start, first_start + 7, 0.8),
            Entity("E2", "aspirin", "Chemical", second_start, second_start + 7, 0.7),
            Entity("E3", "disease", "Disease", disease_start, disease_start + 7, 0.6),
        )

        first = assemble_document_entities(mentions, text)
        second = assemble_document_entities(mentions, text)

        self.assertEqual(first, second)
        self.assertEqual(
            tuple(entity.entity_id for entity in first.document_entities),
            ("doc_e_001", "doc_e_002"),
        )
        self.assertEqual(set(first.mention_to_document_entity), {"E1", "E2", "E3"})
        for document_entity in first.document_entities:
            for mention in document_entity.mentions:
                self.assertEqual(text[mention.start : mention.end], mention.text)


if __name__ == "__main__":
    unittest.main()
