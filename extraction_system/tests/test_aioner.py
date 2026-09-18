from __future__ import annotations

import unittest

from biomedical_extractor.aioner import (
    AIONERBioMedExtractor,
    AIONERRawPrediction,
    normalize_aioner_predictions,
)
from biomedical_extractor.ner_evaluation import canonical_predicted_type


class _FakeAIONERRuntime:
    def __init__(self, predictions):
        self.predictions = predictions

    def predict_entities(self, text):
        return self.predictions


class AIONERAdapterTests(unittest.TestCase):
    def test_all_official_labels_map_to_canonical_taxonomy(self):
        expected = {
            "Gene": "GeneOrGeneProduct",
            "Disease": "DiseaseOrPhenotypicFeature",
            "Chemical": "ChemicalEntity",
            "Species": "OrganismTaxon",
            "CellLine": "CellLine",
            "Variant": "SequenceVariant",
        }
        for label, canonical_type in expected.items():
            self.assertEqual(canonical_predicted_type(label), canonical_type)

    def test_official_source_span_is_converted_to_entity(self):
        entities = normalize_aioner_predictions(
            "BRCA1 drives cancer",
            [(0, 5, "Gene"), {"start": 13, "end": 19, "type": "Disease"}],
        )

        self.assertEqual(entities[0].text, "BRCA1")
        self.assertEqual(entities[0].type, "Gene")
        self.assertEqual(entities[0].start, 0)
        self.assertEqual(entities[0].end, 5)
        self.assertEqual(entities[1].text, "cancer")
        self.assertEqual(entities[1].type, "Disease")

    def test_invalid_source_span_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid AIONER entity character span"):
            normalize_aioner_predictions("BRCA1", [(0, 99, "Gene")])

    def test_mismatched_prediction_text_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            normalize_aioner_predictions(
                "BRCA1",
                [{"start": 0, "end": 5, "text": "BRCA", "label": "Gene"}],
            )

    def test_missing_confidence_is_none(self):
        extractor = AIONERBioMedExtractor(
            _FakeAIONERRuntime([AIONERRawPrediction(0, 5, "Gene")])
        )

        self.assertIsNone(extractor.extract_entities("BRCA1")[0].score)


if __name__ == "__main__":
    unittest.main()
