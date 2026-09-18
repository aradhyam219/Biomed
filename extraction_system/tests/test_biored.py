from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biomedical_extractor.biored import (
    BIORED_RELATION_LABELS,
    BioREDDocument,
    BioREDMention,
    ScoredRelation,
    TypedRelation,
    aggregate_mention_predictions,
    calibrate_threshold,
    canonical_pair,
    is_allowed_candidate,
    load_biored,
    score_relations,
    split_concept_ids,
)
from biomedical_extractor.pipeline import Relation


class BioREDTests(unittest.TestCase):
    def test_parser_preserves_offsets_multi_ids_and_canonical_relation(self):
        root = {
            "source": "BioC",
            "date": "2022",
            "key": "collection.key",
            "documents": [
                {
                    "id": "PM1",
                    "passages": [
                        {
                            "offset": 0,
                            "text": "Gene title.",
                            "annotations": [
                                {
                                    "id": "M1",
                                    "infons": {
                                        "identifier": "1, 2,1",
                                        "type": "GeneOrGeneProduct",
                                    },
                                    "text": "Gene",
                                    "locations": [{"offset": 0, "length": 4}],
                                }
                            ],
                        },
                        {
                            "offset": 12,
                            "text": "Disease abstract.",
                            "annotations": [
                                {
                                    "id": "M2",
                                    "infons": {
                                        "identifier": "D1",
                                        "type": "DiseaseOrPhenotypicFeature",
                                    },
                                    "text": "Disease",
                                    "locations": [{"offset": 12, "length": 7}],
                                }
                            ],
                        },
                    ],
                    "relations": [
                        {
                            "id": "R1",
                            "infons": {
                                "entity1": "D1",
                                "entity2": "1",
                                "type": "Association",
                                "novel": "Novel",
                            },
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Dev.BioC.JSON"
            path.write_text(json.dumps(root), encoding="utf-8")
            dataset = load_biored(path)

        document = dataset.documents[0]
        self.assertEqual(document.text, "Gene title. Disease abstract.")
        self.assertEqual(document.mentions[0].concept_ids, ("1", "2"))
        self.assertEqual(document.mentions[1].type, "Disease")
        self.assertEqual(
            document.relations,
            (TypedRelation("PM1", "1", "D1", "Association"),),
        )

    def test_ner_loader_accepts_official_test_filename(self):
        root = {
            "source": "BioC",
            "date": "2022",
            "key": "collection.key",
            "documents": [
                {
                    "id": "TEST1",
                    "passages": [{"offset": 0, "text": "BRCA1", "annotations": []}],
                    "relations": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Test.BioC.JSON"
            path.write_text(json.dumps(root), encoding="utf-8")
            dataset = load_biored(path, "test")

        self.assertEqual(dataset.split, "test")
        self.assertEqual(dataset.documents[0].id, "TEST1")

    def test_concept_pair_is_non_directional(self):
        self.assertEqual(canonical_pair("Z", "A"), ("A", "Z"))
        self.assertEqual(canonical_pair("A", "A"), ("A", "A"))

    def test_split_concept_ids_rejects_empty_components(self):
        with self.assertRaisesRegex(ValueError, "Invalid BioRED identifier"):
            split_concept_ids("1,,2")

    def test_aggregation_expands_multi_ids_and_deduplicates_mentions_and_directions(self):
        document = BioREDDocument(
            id="PM1",
            text="G1 G1 disease",
            mentions=(
                BioREDMention("M1", "G1", "Gene", 0, 2, ("1", "2")),
                BioREDMention("M2", "G1", "Gene", 3, 5, ("1",)),
                BioREDMention("M3", "disease", "Disease", 6, 13, ("D1",)),
            ),
            relations=(),
        )
        predictions = (
            Relation("M1", "M3", "association", 0.7),
            Relation("M3", "M1", "association", 0.8),
            Relation("M2", "M3", "association", 0.9),
        )

        result = aggregate_mention_predictions(document, predictions)

        self.assertEqual(
            result,
            (
                ScoredRelation("PM1", "1", "D1", "Association", 0.9),
                ScoredRelation("PM1", "2", "D1", "Association", 0.8),
            ),
        )

    def test_candidate_constraints_reject_only_unsupported_pair_families(self):
        self.assertTrue(is_allowed_candidate("Disease", "Gene", "Association"))
        self.assertTrue(is_allowed_candidate("Gene", "Chemical", "Bind"))
        self.assertTrue(is_allowed_candidate("Disease", "Chemical", "Bind"))
        self.assertTrue(is_allowed_candidate("Chemical", "Chemical", "Cotreatment"))
        self.assertFalse(is_allowed_candidate("Species", "Gene", "Association"))
        self.assertFalse(is_allowed_candidate("Gene", "Gene", "not canonical"))

    def test_scoring_distinguishes_pair_detection_from_typed_extraction(self):
        gold = {
            TypedRelation("PM1", "1", "D1", "Association"),
            TypedRelation("PM1", "2", "D2", "Positive_Correlation"),
        }
        candidates = (
            ScoredRelation("PM1", "1", "D1", "Negative_Correlation", 0.9),
            ScoredRelation("PM1", "2", "D2", "Positive_Correlation", 0.8),
            ScoredRelation("PM1", "3", "D3", "Association", 0.7),
        )

        result = score_relations(gold, candidates, 0.75)

        self.assertEqual(result["pair_only"]["tp"], 2)
        self.assertEqual(result["pair_only"]["fp"], 0)
        self.assertEqual(result["typed_micro"]["tp"], 1)
        self.assertEqual(result["typed_micro"]["fp"], 1)
        self.assertEqual(result["typed_micro"]["fn"], 1)
        self.assertEqual(result["per_label"]["Association"]["support"], 1)
        self.assertIsNone(result["per_label"]["Bind"]["recall"])

    def test_defined_zero_precision_and_recall_have_zero_f1(self):
        gold = (TypedRelation("PM1", "1", "2", "Association"),)
        candidates = (
            ScoredRelation("PM1", "3", "4", "Negative_Correlation", 0.9),
        )

        result = score_relations(gold, candidates, 0.5)

        self.assertEqual(result["typed_micro"]["precision"], 0.0)
        self.assertEqual(result["typed_micro"]["recall"], 0.0)
        self.assertEqual(result["typed_micro"]["f1"], 0.0)

    def test_threshold_calibration_reuses_scores_and_prefers_higher_tie(self):
        gold = (TypedRelation("PM1", "1", "2", "Association"),)
        candidates = (
            ScoredRelation("PM1", "1", "2", "Association", 0.8),
            ScoredRelation("PM1", "3", "4", "Association", 0.2),
        )

        threshold, result = calibrate_threshold(gold, candidates)

        self.assertEqual(threshold, 0.8)
        self.assertEqual(result["typed_micro"]["f1"], 1.0)

    def test_relation_schema_is_exact(self):
        self.assertEqual(
            BIORED_RELATION_LABELS,
            (
                "Association",
                "Positive_Correlation",
                "Negative_Correlation",
                "Bind",
                "Conversion",
                "Drug_Interaction",
                "Comparison",
                "Cotreatment",
            ),
        )


if __name__ == "__main__":
    unittest.main()
