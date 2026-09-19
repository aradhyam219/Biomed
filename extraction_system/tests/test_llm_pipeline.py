from __future__ import annotations

import unittest
from unittest.mock import patch

from biomedical_extractor.entity_extraction import DEFAULT_ENTITY_MODEL, Entity
from biomedical_extractor.hunflair2 import HunFlair2BioMedExtractor
from biomedical_extractor.llm_pipeline import ComposedExtractionResult, LLMExtractionPipeline
from biomedical_extractor.relation_extraction import (
    Relation,
    RelationExtractionResult,
    RelationValidationError,
)


TEXT = "BRCA1 is associated with breast cancer."
ENTITIES = (
    Entity("E1", "BRCA1", "gene", 0, 5, 0.9),
    Entity("E2", "breast cancer", "disease", 24, 37, 0.8),
)
RELATION = Relation(
    "E1",
    "E2",
    "association",
    "BRCA1 is associated with breast cancer",
    False,
)


class _FakeEntityExtractor:
    def __init__(self):
        self.calls = []

    def extract_entities(self, text):
        self.calls.append(text)
        return ENTITIES


class _FakeRelationExtractor:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or RelationExtractionResult((RELATION,))

    def extract_relations(self, text, entities):
        self.calls.append((text, tuple(entities)))
        return self.result


class _FakeHunFlair2Runtime:
    def predict_entities(self, text):
        return (
            {"start": 0, "end": 5, "text": "BRCA1", "label": "Gene", "score": 0.91},
            {
                "start": 14,
                "end": 20,
                "text": "cancer",
                "label": "Disease",
                "score": 0.87,
            },
        )


class LLMPipelineTests(unittest.TestCase):
    def test_default_pretrained_path_uses_adapter_default_schema(self):
        entity_extractor = _FakeEntityExtractor()
        relation_extractor = _FakeRelationExtractor()

        with (
            patch(
                "biomedical_extractor.llm_pipeline.GLiNERBioMedExtractor.from_pretrained",
                return_value=entity_extractor,
            ) as load_entities,
            patch(
                "biomedical_extractor.llm_pipeline.LLMRelationExtractor.from_openai",
                return_value=relation_extractor,
            ) as load_relations,
        ):
            pipeline = LLMExtractionPipeline.from_pretrained()

        self.assertIs(pipeline.entity_extractor, entity_extractor)
        self.assertIs(pipeline.relation_extractor, relation_extractor)
        load_entities.assert_called_once_with(
            model_name=DEFAULT_ENTITY_MODEL,
            labels=None,
            threshold=0.5,
            device=None,
        )
        load_relations.assert_called_once_with(None)

    def test_hunflair2_factory_uses_the_same_grounded_relation_pipeline(self):
        entity_extractor = _FakeEntityExtractor()
        relation_extractor = _FakeRelationExtractor()
        with (
            patch(
                "biomedical_extractor.llm_pipeline.HunFlair2BioMedExtractor.from_pretrained",
                return_value=entity_extractor,
            ) as load_entities,
            patch(
                "biomedical_extractor.llm_pipeline.LLMRelationExtractor.from_openai",
                return_value=relation_extractor,
            ) as load_relations,
        ):
            pipeline = LLMExtractionPipeline.from_hunflair2(
                runtime_python="runtime-python",
                runtime_cache="runtime-cache",
                device="cpu",
            )

        self.assertIs(pipeline.entity_extractor, entity_extractor)
        self.assertIs(pipeline.relation_extractor, relation_extractor)
        load_entities.assert_called_once_with(
            model_identifier="hunflair/hunflair2-ner",
            runtime_python="runtime-python",
            runtime_script=None,
            runtime_cache="runtime-cache",
            device="cpu",
            offline=False,
        )
        load_relations.assert_called_once_with(None)

    def test_composed_path_runs_ner_then_relation_extraction(self):
        entity_extractor = _FakeEntityExtractor()
        relation_extractor = _FakeRelationExtractor()
        pipeline = LLMExtractionPipeline(entity_extractor, relation_extractor)

        result = pipeline.extract(TEXT)

        self.assertIsInstance(result, ComposedExtractionResult)
        self.assertEqual(result.entities, ENTITIES)
        self.assertEqual(result.relations, (RELATION,))
        self.assertEqual(entity_extractor.calls, [TEXT])
        self.assertEqual(relation_extractor.calls, [(TEXT, ENTITIES)])
        self.assertEqual(result.to_dict()["relations"][0]["evidence"], RELATION.evidence)

    def test_hunflair2_entities_compose_with_grounded_relations(self):
        text = "BRCA1 affects cancer."
        entity_extractor = HunFlair2BioMedExtractor(_FakeHunFlair2Runtime())
        relation = Relation(
            "E1",
            "E2",
            "affects",
            "BRCA1 affects cancer",
            True,
            surface_form="affects",
        )
        relation_extractor = _FakeRelationExtractor(
            RelationExtractionResult((relation,))
        )

        result = LLMExtractionPipeline(entity_extractor, relation_extractor).extract(text)

        self.assertEqual(tuple(entity.type for entity in result.entities), ("Gene", "Disease"))
        self.assertEqual(result.entities[0].id, "E1")
        self.assertEqual(result.entities[1].id, "E2")
        self.assertEqual(result.relations, (relation,))
        self.assertIn(result.relations[0].source, {entity.id for entity in result.entities})
        self.assertIn(result.relations[0].target, {entity.id for entity in result.entities})
        self.assertTrue(result.relations[0].negated)

    def test_composed_path_accepts_merged_process_entities(self):
        text = "p53 decreased proliferation ability in SSC-4 cells."
        entities = (
            Entity("E1", "p53", "gene", 0, 3, 0.9),
            Entity(
                "E2",
                "proliferation ability",
                "biological process",
                13,
                34,
                0.8,
            ),
            Entity("E3", "SSC-4 cells", "cell line", 35, 46, 0.95),
        )
        relation = Relation(
            "E1",
            "E2",
            "decreased",
            "p53 decreased proliferation ability",
            False,
        )

        class MergedEntityExtractor:
            def extract_entities(self, supplied_text):
                self.text = supplied_text
                return entities

        entity_extractor = MergedEntityExtractor()
        relation_extractor = _FakeRelationExtractor(
            RelationExtractionResult((relation,))
        )
        pipeline = LLMExtractionPipeline(entity_extractor, relation_extractor)

        result = pipeline.extract(text)

        self.assertEqual(result.entities, entities)
        self.assertEqual(result.relations, (relation,))
        self.assertEqual(relation_extractor.calls, [(text, entities)])

    def test_composed_path_rechecks_custom_relation_output(self):
        invalid = Relation(
            "E1", "E99", "association", "BRCA1 is associated with breast cancer", False
        )
        pipeline = LLMExtractionPipeline(
            _FakeEntityExtractor(),
            _FakeRelationExtractor(RelationExtractionResult((invalid,))),
        )

        with self.assertRaises(RelationValidationError):
            pipeline.extract(TEXT)

    def test_blank_text_skips_both_stages(self):
        entity_extractor = _FakeEntityExtractor()
        relation_extractor = _FakeRelationExtractor()
        result = LLMExtractionPipeline(entity_extractor, relation_extractor).extract(" ")

        self.assertEqual(result.to_dict(), {"entities": [], "relations": []})
        self.assertEqual(entity_extractor.calls, [])
        self.assertEqual(relation_extractor.calls, [])


if __name__ == "__main__":
    unittest.main()
