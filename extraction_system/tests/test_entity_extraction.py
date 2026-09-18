from __future__ import annotations

import unittest
from unittest.mock import patch

from biomedical_extractor.entity_extraction import (
    DEFAULT_CORE_ENTITY_LABELS,
    DEFAULT_ENTITY_MODEL,
    DEFAULT_PROCESS_ENTITY_LABELS,
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


class PassAwareGLiNERModel:
    def __init__(self):
        self.calls = []
        self.eval_calls = 0

    def eval(self):
        self.eval_calls += 1
        return self

    def predict_entities(self, text, labels, *, threshold):
        labels = tuple(labels)
        self.calls.append((text, labels, threshold))
        if labels == DEFAULT_CORE_ENTITY_LABELS:
            return [
                {
                    "text": "p53",
                    "label": "gene",
                    "start": 0,
                    "end": 3,
                    "score": 0.9,
                }
            ]
        if labels == DEFAULT_PROCESS_ENTITY_LABELS:
            return [
                {
                    "text": "apoptosis",
                    "label": "biological process",
                    "start": 11,
                    "end": 20,
                    "score": 0.8,
                },
                {
                    "text": "apoptosis",
                    "label": "biological process",
                    "start": 11,
                    "end": 20,
                    "score": 0.8,
                },
            ]
        raise AssertionError(f"Unexpected label pass: {labels!r}")


class EntityExtractionTests(unittest.TestCase):
    def test_default_path_runs_two_passes_and_merges_deterministically(self):
        text = "p53 causes apoptosis"
        model = PassAwareGLiNERModel()

        entities = GLiNERBioMedExtractor(model).extract_entities(text)

        self.assertEqual(
            model.calls,
            [
                (text, DEFAULT_CORE_ENTITY_LABELS, 0.5),
                (text, DEFAULT_PROCESS_ENTITY_LABELS, 0.5),
            ],
        )
        self.assertEqual(
            entities,
            (
                Entity("E1", "p53", "gene", 0, 3, 0.9),
                Entity("E2", "apoptosis", "biological process", 11, 20, 0.8),
            ),
        )

    def test_default_loader_reuses_one_model_for_both_passes(self):
        text = "p53 causes apoptosis"
        model = PassAwareGLiNERModel()

        with patch(
            "gliner.GLiNER.from_pretrained", return_value=model
        ) as load:
            extractor = GLiNERBioMedExtractor.from_pretrained(device="cpu")
            extractor.extract_entities(text)

        load.assert_called_once_with(DEFAULT_ENTITY_MODEL, map_location="cpu")
        self.assertEqual(model.eval_calls, 1)
        self.assertEqual(len(model.calls), 2)

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
