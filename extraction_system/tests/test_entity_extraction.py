from __future__ import annotations

import unittest

from biomedical_extractor.entity_extraction import (
    Entity,
    GLiNERBioMedExtractor,
)


TEXT = "BRCA1 mutations are associated with breast cancer."


class FakeGLiNERModel:
    def __init__(self, predictions):
        self.predictions = predictions
        self.calls = []

    def predict_entities(self, text, labels, *, threshold):
        self.calls.append((text, labels, threshold))
        return self.predictions


class EntityExtractionTests(unittest.TestCase):
    def test_gliner_adapter_returns_standard_entities_with_source_spans(self):
        model = FakeGLiNERModel(
            [
                {
                    "text": "BRCA1",
                    "label": "gene",
                    "start": 0,
                    "end": 5,
                    "score": 0.98,
                },
                {
                    "text": "breast cancer",
                    "label": "disease",
                    "start": 36,
                    "end": 49,
                },
            ]
        )
        extractor = GLiNERBioMedExtractor(
            model, labels=("gene", "disease"), threshold=0.4
        )

        entities = extractor.extract_entities(TEXT)

        self.assertEqual(
            entities,
            (
                Entity("E1", "BRCA1", "gene", 0, 5, 0.98),
                Entity("E2", "breast cancer", "disease", 36, 49, None),
            ),
        )
        self.assertEqual(model.calls, [(TEXT, ("gene", "disease"), 0.4)])
        for entity in entities:
            self.assertEqual(TEXT[entity.start : entity.end], entity.text)
            self.assertIsInstance(entity, Entity)

    def test_entity_result_has_only_model_independent_fields(self):
        model = FakeGLiNERModel(
            [{"text": "BRCA1", "label": "gene", "start": 0, "end": 5}]
        )
        entity = GLiNERBioMedExtractor(model, labels=("gene",)).extract_entities(TEXT)[0]

        self.assertEqual(
            entity.to_dict(),
            {
                "id": "E1",
                "text": "BRCA1",
                "type": "gene",
                "start": 0,
                "end": 5,
                "score": None,
            },
        )

    def test_adapter_rejects_a_prediction_that_does_not_map_to_source_text(self):
        model = FakeGLiNERModel(
            [{"text": "BRCA2", "label": "gene", "start": 0, "end": 5}]
        )

        with self.assertRaisesRegex(ValueError, "does not resolve"):
            GLiNERBioMedExtractor(model, labels=("gene",)).extract_entities(TEXT)

    def test_blank_text_does_not_call_model(self):
        model = FakeGLiNERModel([])

        self.assertEqual(
            GLiNERBioMedExtractor(model, labels=("gene",)).extract_entities("  "), ()
        )
        self.assertEqual(model.calls, [])

    def test_invalid_entity_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            GLiNERBioMedExtractor(FakeGLiNERModel([]), threshold=1.1)


if __name__ == "__main__":
    unittest.main()
