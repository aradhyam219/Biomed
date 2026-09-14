from __future__ import annotations

import json
import unittest

from biomedical_extractor.pipeline import BiomedicalExtractor, Entity, ExtractionConfig


TEXT = "BRCA1 mutations are associated with breast cancer."


class FakeEntityModel:
    def predict_entities(self, text, labels, *, threshold):
        assert text == TEXT
        assert labels == ("gene", "disease")
        assert threshold == 0.4
        return [
            {"text": "BRCA1", "label": "gene", "start": 0, "end": 5, "score": 0.98},
            {
                "text": "breast cancer",
                "label": "disease",
                "start": 36,
                "end": 49,
                "score": 0.96,
            },
        ]


class FakeRelationModel:
    def predict_relations(self, text, labels, *, threshold, ner, flat_ner):
        assert text == [
            "BRCA1",
            "mutations",
            "are",
            "associated",
            "with",
            "breast",
            "cancer",
            ".",
        ]
        assert labels == ("association",)
        assert threshold == 0.3
        assert ner == [[0, 0, "gene", "BRCA1"], [5, 6, "disease", "breast cancer"]]
        assert flat_ner is True
        return [
            {
                "head_pos": [0, 1],
                "tail_pos": [5, 7],
                "head_text": ["BRCA1"],
                "tail_text": ["breast", "cancer"],
                "label": "association",
                "score": 0.91,
            }
        ]


def make_extractor(entity_model=None, relation_model=None):
    return BiomedicalExtractor(
        entity_model or FakeEntityModel(),
        relation_model or FakeRelationModel(),
        ExtractionConfig(
            entity_labels=("gene", "disease"),
            relation_labels=("association",),
            entity_threshold=0.4,
            relation_threshold=0.3,
        ),
    )


class PipelineTests(unittest.TestCase):
    def test_entity_handoff_and_directional_relation_normalization(self):
        result = make_extractor().extract(TEXT).to_dict()

        self.assertEqual(TEXT[result["entities"][0]["start"] : result["entities"][0]["end"]], "BRCA1")
        self.assertEqual(TEXT[result["entities"][1]["start"] : result["entities"][1]["end"]], "breast cancer")
        self.assertEqual(
            result["relations"],
            [{"source": "E1", "target": "E2", "type": "association", "score": 0.91}],
        )
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_rejects_entity_span_that_does_not_match_source_text(self):
        class BadEntityModel(FakeEntityModel):
            def predict_entities(self, text, labels, *, threshold):
                return [{"text": "BRCA2", "label": "gene", "start": 0, "end": 5, "score": 0.9}]

        with self.assertRaisesRegex(ValueError, "does not resolve"):
            make_extractor(entity_model=BadEntityModel()).extract(TEXT)

    def test_rejects_relation_to_unknown_entity_span(self):
        class BadRelationModel(FakeRelationModel):
            def predict_relations(self, text, labels, *, threshold, ner, flat_ner):
                return [{"head_pos": [0, 1], "tail_pos": [4, 5], "label": "association", "score": 0.8}]

        with self.assertRaisesRegex(ValueError, "unknown GLiREL entity span"):
            make_extractor(relation_model=BadRelationModel()).extract(TEXT)

    def test_rejects_out_of_schema_relation_label(self):
        class BadRelationModel(FakeRelationModel):
            def predict_relations(self, text, labels, *, threshold, ner, flat_ner):
                return [{"head_pos": [0, 1], "tail_pos": [5, 7], "label": "unconfigured", "score": 0.8}]

        with self.assertRaisesRegex(ValueError, "outside the configured schema"):
            make_extractor(relation_model=BadRelationModel()).extract(TEXT)

    def test_blank_text_skips_both_models(self):
        class UnexpectedModel:
            def __getattr__(self, name):
                raise AssertionError(f"Model method {name} should not be called")

        result = BiomedicalExtractor(UnexpectedModel(), UnexpectedModel()).extract("  ")
        self.assertEqual(result.to_dict(), {"entities": [], "relations": []})

    def test_relations_can_run_with_supplied_entities(self):
        class UnexpectedEntityModel:
            def predict_entities(self, text, labels, *, threshold):
                raise AssertionError("Entity extraction should not run")

        entities = (
            Entity("GOLD1", "BRCA1", "gene", 0, 5, None),
            Entity("GOLD2", "breast cancer", "disease", 36, 49, None),
        )
        extractor = make_extractor(entity_model=UnexpectedEntityModel())

        relations = extractor.extract_relations(TEXT, entities)

        self.assertEqual(relations[0].source, "GOLD1")
        self.assertEqual(relations[0].target, "GOLD2")

    def test_rejects_character_span_inside_a_glirel_token(self):
        entities = (
            Entity("E1", "BRCA1", "gene", 1, 6, None),
            Entity("E2", "TP53", "gene", 14, 18, None),
        )

        with self.assertRaisesRegex(ValueError, "does not align"):
            make_extractor().extract_relations("pBRCA1x binds TP53", entities)

    def test_rejects_duplicate_supplied_entity_ids(self):
        entities = (
            Entity("E1", "BRCA1", "gene", 0, 5, None),
            Entity("E1", "breast cancer", "disease", 36, 49, None),
        )

        with self.assertRaisesRegex(ValueError, "non-empty and unique"):
            make_extractor().extract_relations(TEXT, entities)

    def test_config_rejects_invalid_threshold(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            ExtractionConfig(entity_threshold=1.1)


if __name__ == "__main__":
    unittest.main()
