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
from biomedical_extractor.ner_comparison import (
    build_comparison_report,
    build_model_comparison_report,
    render_comparison_markdown,
    validate_report_arithmetic,
)
from biomedical_extractor.ner_evaluation import ALL_CANONICAL_TYPES, evaluate_biored


def _mention(mention_id, text, entity_type, start, concept_id):
    return BioREDMention(
        mention_id,
        text,
        entity_type,
        start,
        start + len(text),
        (concept_id,),
    )


class _Extractor:
    def __init__(self, entities):
        self.entities = tuple(entities)

    def extract_entities(self, text):
        return self.entities


class NERComparisonTests(unittest.TestCase):
    def test_comparison_validates_arithmetic_and_variant_coverage(self):
        document = BioREDDocument(
            "D1",
            "BRCA1 rs123",
            (
                _mention("M1", "BRCA1", "Gene", 0, "G1"),
                _mention("M2", "rs123", "Variant", 6, "V1"),
            ),
            (TypedRelation("D1", "G1", "V1", "Association"),),
        )
        dataset = BioREDDataset(
            Path("Test.BioC.JSON"), "test", "sha", "BioC", "date", "key", (document,)
        )
        gliner = evaluate_biored(
            dataset,
            _Extractor((Entity("E1", "BRCA1", "gene", 0, 5, 0.9),)),
        )
        gliner["predictor"] = {"model": "gliner", "adapter": "GLiNERBioMedExtractor"}
        aioner = evaluate_biored(
            dataset,
            _Extractor(
                (
                    Entity("E1", "BRCA1", "Gene", 0, 5),
                    Entity("E2", "rs123", "Variant", 6, 11),
                )
            ),
            supported_types=ALL_CANONICAL_TYPES,
        )
        aioner["predictor"] = {"model": "aioner", "adapter": "AIONERBioMedExtractor"}

        validate_report_arithmetic(gliner)
        comparison = build_comparison_report(gliner, aioner)

        self.assertTrue(comparison["full_schema_coverage"]["variant"]["aioner_supported"])
        self.assertFalse(comparison["full_schema_coverage"]["variant"]["gliner_supported"])
        self.assertEqual(
            comparison["shared_class_head_to_head"]["models"]["AIONER"]["micro"]["tp"],
            1,
        )
        self.assertIn("SequenceVariant coverage", render_comparison_markdown(comparison))

        hunflair2 = dict(gliner)
        hunflair2["predictor"] = {
            "model": "hunflair/hunflair2-ner",
            "adapter": "HunFlair2BioMedExtractor",
        }
        challenger = build_model_comparison_report(
            aioner,
            hunflair2,
            first_name="AIONER",
            second_name="HunFlair2",
        )
        self.assertEqual(
            challenger["shared_class_head_to_head"]["models"]["HunFlair2"]["micro"][
                "tp"
            ],
            1,
        )
        self.assertFalse(
            challenger["full_schema_coverage"]["variant"]["hunflair2_supported"]
        )
        self.assertIn("AIONER vs HunFlair2", render_comparison_markdown(challenger))


if __name__ == "__main__":
    unittest.main()
