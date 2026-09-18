from __future__ import annotations

import unittest

from biomedical_extractor.cross_corpus import (
    MEDMENTIONS_SCORED_TYPES,
    MedMentionsDataset,
    evaluate_medmentions,
    medmentions_semantic_type_mapping,
    parse_medmentions_pubtator,
    validate_medmentions_report_arithmetic,
)
from biomedical_extractor.entity_extraction import Entity


class CrossCorpusTests(unittest.TestCase):
    def test_medmentions_mapping_scores_explicit_types_and_rejects_ambiguous(self):
        self.assertEqual(
            medmentions_semantic_type_mapping(("T103",))["canonical_type"],
            "ChemicalEntity",
        )
        self.assertEqual(
            medmentions_semantic_type_mapping(("T047",))["canonical_type"],
            "DiseaseOrPhenotypicFeature",
        )
        self.assertEqual(
            medmentions_semantic_type_mapping(("T103", "T047"))["status"],
            "ambiguous",
        )
        self.assertEqual(
            medmentions_semantic_type_mapping(("T074",))["status"],
            "unsupported",
        )

    def test_pubtator_parser_preserves_offsets_and_mapping_status(self):
        raw = (
            b"1|t|TP53 and aspirin\n"
            b"1|a|TP53 is relevant.\n"
            b"1\t0\t4\tTP53\tT047\tC1\n"
            b"1\t9\t16\taspirin\tT103\tC2\n"
            b"1\t0\t4\tTP53\tT074\tC1\n"
            b"1\t0\t4\tTP53\tT047|T103\tC1\n\n"
        )
        documents = parse_medmentions_pubtator(raw, selected_ids=("1",))

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document.text[0:4], "TP53")
        self.assertEqual(document.mentions[0].mapping_status, "scored")
        self.assertEqual(document.mentions[1].canonical_type, "ChemicalEntity")
        self.assertEqual(document.mentions[2].mapping_status, "unsupported")
        self.assertEqual(document.mentions[3].mapping_status, "ambiguous")

    def test_exact_metrics_and_failure_counts_are_arithmetic(self):
        raw = (
            b"1|t|TP53 aspirin\n"
            b"1|a|causes disease.\n"
            b"1\t0\t4\tTP53\tT047\tC1\n"
            b"1\t5\t12\taspirin\tT103\tC2\n"
            b"1\t20\t28\tdisease.\tT074\tC3\n\n"
        )
        document = parse_medmentions_pubtator(raw)[0]
        dataset = MedMentionsDataset(
            split="test",
            corpus_url="corpus",
            corpus_sha256="corpus-sha",
            split_url="split",
            split_sha256="split-sha",
            source_repository="repo",
            documents=(document,),
        )
        predictions = {
            "AIONER": {
                "1": (
                    Entity("e1", "TP53", "Disease", 0, 4, 0.9),
                    Entity("e2", "aspirin", "Chemical", 5, 12, 0.9),
                    Entity("e3", "TP53 aspirin", "Disease", 0, 12, 0.2),
                )
            },
            "HunFlair2": {
                "1": (
                    Entity("h1", "TP53", "Chemical", 0, 4, 0.9),
                    Entity("h2", "aspirin", "Chemical", 5, 12, 0.9),
                )
            },
        }
        report = evaluate_medmentions(dataset, predictions)
        validate_medmentions_report_arithmetic(report)

        self.assertEqual(
            report["evidence_role"],
            "exploratory cross-schema stress test using explicit UMLS semantic-type mappings",
        )
        self.assertFalse(report["clean_model_selection_evidence"])

        self.assertEqual(
            report["models"]["AIONER"]["metrics"]["micro"]["tp"],
            2,
        )
        self.assertEqual(
            report["models"]["HunFlair2"]["metrics"]["micro"]["tp"],
            1,
        )
        self.assertEqual(
            report["models"]["HunFlair2"]["failure_counts"]["same_span_different_type"],
            1,
        )
        self.assertEqual(
            report["models"]["AIONER"]["counts"]["gold_unsupported_mentions"],
            1,
        )
        self.assertEqual(
            set(report["models"]["AIONER"]["metrics"]["per_type"]),
            set(MEDMENTIONS_SCORED_TYPES),
        )


if __name__ == "__main__":
    unittest.main()
