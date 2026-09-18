from __future__ import annotations

import unittest
from pathlib import Path

from biomedical_extractor.biored import (
    BioREDDataset,
    BioREDDocument,
    BioREDMention,
    TypedRelation,
)
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.ner_evaluation import (
    FAILURE_MISSED_ENTITY,
    FAILURE_OVERLAPPING_PREDICTION,
    FAILURE_SPAN_MISMATCH,
    FAILURE_SPURIOUS_ENTITY,
    FAILURE_UNSUPPORTED_GOLD,
    FAILURE_UNSUPPORTED_PREDICTED,
    FAILURE_WRONG_TYPE,
    evaluate_biored,
    score_entity_mentions,
)


def _gold(
    mention_id: str,
    text: str,
    entity_type: str,
    start: int,
    concept_id: str = "C1",
) -> BioREDMention:
    return BioREDMention(
        mention_id,
        text,
        entity_type,
        start,
        start + len(text),
        (concept_id,),
    )


def _pred(
    entity_id: str,
    text: str,
    entity_type: str,
    start: int,
    score: float = 0.9,
) -> Entity:
    return Entity(entity_id, text, entity_type, start, start + len(text), score)


class NEREvaluationTests(unittest.TestCase):
    def test_exact_span_and_type_is_true_positive(self):
        score = score_entity_mentions(
            "D1",
            "BRCA1",
            (_gold("M1", "BRCA1", "Gene", 0),),
            (_pred("E1", "BRCA1", "gene", 0),),
        )

        self.assertEqual(score.metrics["micro"]["tp"], 1)
        self.assertEqual(score.metrics["micro"]["fp"], 0)
        self.assertEqual(score.metrics["micro"]["fn"], 0)
        self.assertEqual(score.metrics["micro"]["f1"], 1.0)
        self.assertEqual(score.matched_gold_ids, frozenset({"M1"}))

    def test_gene_and_protein_share_gene_or_gene_product_mapping(self):
        score = score_entity_mentions(
            "D1",
            "p53",
            (_gold("M1", "p53", "Gene", 0),),
            (_pred("E1", "p53", "protein", 0),),
        )

        self.assertEqual(score.metrics["micro"]["f1"], 1.0)
        self.assertIn("GeneOrGeneProduct", score.metrics["per_type"])

    def test_same_span_wrong_type_is_reported_without_exact_match(self):
        score = score_entity_mentions(
            "D1",
            "BRCA1",
            (_gold("M1", "BRCA1", "Gene", 0),),
            (_pred("E1", "BRCA1", "disease", 0),),
        )

        self.assertEqual(score.metrics["micro"]["tp"], 0)
        self.assertEqual(score.metrics["micro"]["fp"], 1)
        self.assertEqual(score.metrics["micro"]["fn"], 1)
        self.assertEqual(score.failure_counts[FAILURE_WRONG_TYPE], 1)

    def test_overlapping_same_type_span_is_boundary_diagnostic(self):
        score = score_entity_mentions(
            "D1",
            "BRCA1",
            (_gold("M1", "BRCA1", "Gene", 0),),
            (_pred("E1", "BRCA", "gene", 0),),
        )

        self.assertEqual(score.metrics["micro"]["f1"], 0.0)
        self.assertEqual(score.failure_counts[FAILURE_SPAN_MISMATCH], 1)

    def test_overlapping_different_type_is_separate_diagnostic(self):
        score = score_entity_mentions(
            "D1",
            "BRCA1",
            (_gold("M1", "BRCA1", "Gene", 0),),
            (_pred("E1", "BRCA", "disease", 0),),
        )

        self.assertEqual(score.failure_counts[FAILURE_OVERLAPPING_PREDICTION], 1)
        self.assertEqual(score.failure_counts[FAILURE_WRONG_TYPE], 0)

    def test_missed_and_spurious_entities_are_stable_categories(self):
        score = score_entity_mentions(
            "D1",
            "BRCA1 TP53",
            (_gold("M1", "BRCA1", "Gene", 0),),
            (_pred("E1", "TP53", "gene", 6),),
        )

        self.assertEqual(score.failure_counts[FAILURE_MISSED_ENTITY], 1)
        self.assertEqual(score.failure_counts[FAILURE_SPURIOUS_ENTITY], 1)

    def test_unsupported_gold_is_reported_and_not_counted_as_false_negative(self):
        score = score_entity_mentions(
            "D1",
            "rs123",
            (_gold("M1", "rs123", "Variant", 0),),
            (),
        )

        self.assertEqual(score.metrics["micro"]["fn"], 0)
        self.assertEqual(score.gold_unscored_counts, {"Variant": 1})
        self.assertEqual(score.failure_counts[FAILURE_UNSUPPORTED_GOLD], 1)

    def test_unsupported_prediction_is_reported_separately(self):
        score = score_entity_mentions(
            "D1",
            "DNA1",
            (),
            (_pred("E1", "DNA1", "DNA", 0),),
        )

        self.assertEqual(score.metrics["micro"]["fp"], 0)
        self.assertEqual(score.predicted_unscored_counts, {"DNA": 1})
        self.assertEqual(score.failure_counts[FAILURE_UNSUPPORTED_PREDICTED], 1)

    def test_micro_per_type_and_macro_metrics_are_aggregated(self):
        score = score_entity_mentions(
            "D1",
            "BRCA1 cancer",
            (
                _gold("M1", "BRCA1", "Gene", 0),
                _gold("M2", "cancer", "Disease", 6),
            ),
            (
                _pred("E1", "BRCA1", "gene", 0),
                _pred("E2", "cancer", "chemical", 6),
            ),
        )

        self.assertEqual(score.metrics["micro"]["tp"], 1)
        self.assertEqual(score.metrics["micro"]["fp"], 1)
        self.assertEqual(score.metrics["micro"]["fn"], 1)
        self.assertEqual(
            score.metrics["per_type"]["GeneOrGeneProduct"]["f1"], 1.0
        )
        self.assertEqual(
            score.metrics["per_type"]["DiseaseOrPhenotypicFeature"]["fn"], 1
        )
        self.assertAlmostEqual(score.metrics["macro_f1"], 1 / 3)

    def test_graph_critical_recall_is_ner_only_and_has_mention_and_concept_views(self):
        document = BioREDDocument(
            id="D1",
            text="BRCA1 cancer",
            mentions=(
                _gold("M1", "BRCA1", "Gene", 0, "G1"),
                _gold("M2", "cancer", "Disease", 6, "D1"),
            ),
            relations=(TypedRelation("D1", "G1", "D1", "Association"),),
        )
        dataset = BioREDDataset(
            path=Path("Dev.BioC.JSON"),
            split="dev",
            sha256="sha",
            source="BioC",
            date="date",
            key="key",
            documents=(document,),
        )

        class GeneOnlyExtractor:
            def extract_entities(self, text: str) -> tuple[Entity, ...]:
                return (_pred("E1", "BRCA1", "gene", 0),)

        report = evaluate_biored(dataset, GeneOnlyExtractor())
        graph = report["graph_critical_entity_recall"]

        self.assertEqual(graph["mention_level"]["recognized"], 1)
        self.assertEqual(graph["mention_level"]["gold"], 2)
        self.assertEqual(graph["mention_level"]["recall"], 0.5)
        self.assertEqual(graph["concept_level"]["recognized"], 1)
        self.assertEqual(graph["concept_level"]["gold"], 2)
        self.assertEqual(graph["concept_level"]["recall"], 0.5)


if __name__ == "__main__":
    unittest.main()
