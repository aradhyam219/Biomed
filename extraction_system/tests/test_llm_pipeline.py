from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from biomedical_extractor.entity_extraction import DEFAULT_ENTITY_MODEL, Entity
from biomedical_extractor.hunflair2 import (
    HUNFLAIR2_MODEL_IDENTIFIER,
    HunFlair2BioMedExtractor,
)
from biomedical_extractor.identity_resolution import (
    ExplicitIdentityDecision,
    ExplicitIdentityResult,
)
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
    "BRCA1 is associated with breast cancer.",
    "BRCA1 is associated with breast cancer",
    False,
)
from biomedical_extractor.paper_roles import (
    PaperRole,
    PaperRoleExtractionResult,
    PaperRoleRecord,
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


class _FakeIdentityVerifier:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or ExplicitIdentityResult(())

    def verify_explicit_identities(self, text, candidates):
        self.calls.append((text, tuple(candidates)))
        return self.result


class _SameEntityVerifier(_FakeIdentityVerifier):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def verify_explicit_identities(self, text, candidates):
        self.events.append("identity")
        self.calls.append((text, tuple(candidates)))
        return ExplicitIdentityResult(
            tuple(
                ExplicitIdentityDecision(
                    candidate.candidate_id,
                    candidate.mention_ids,
                    "same_identity_construction",
                    candidate.construction,
                )
                for candidate in candidates
            )
        )


class _RecordingRoleExtractor:
    def __init__(self, events):
        self.events = events
        self.targets = ()

    def extract_roles(self, title, text, targets):
        self.events.append("roles")
        self.targets = tuple(targets)
        return PaperRoleExtractionResult(
            tuple(
                PaperRoleRecord(
                    target.node_id,
                    PaperRole(
                        "contextual",
                        (f"{target.label} appears in the source.",),
                        (target.label,),
                    ),
                )
                for target in self.targets
            )
        )


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
    def test_default_pretrained_path_uses_hunflair2(self):
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
            patch(
                "biomedical_extractor.llm_pipeline.LLMExplicitIdentityVerifier.from_openai",
                return_value=_FakeIdentityVerifier(),
            ) as load_identity,
        ):
            pipeline = LLMExtractionPipeline.from_pretrained()

        self.assertIs(pipeline.entity_extractor, entity_extractor)
        self.assertIs(pipeline.relation_extractor, relation_extractor)
        self.assertIsInstance(pipeline.identity_verifier, _FakeIdentityVerifier)
        load_entities.assert_called_once_with(
            model_identifier=HUNFLAIR2_MODEL_IDENTIFIER,
            runtime_python=None,
            runtime_script=None,
            runtime_cache=Path(".cache/hunflair2"),
            device=None,
            offline=False,
        )
        load_relations.assert_called_once_with(None)
        load_identity.assert_called_once_with(None)

    def test_explicit_gliner_backend_remains_available(self):
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
            ),
            patch(
                "biomedical_extractor.llm_pipeline.LLMExplicitIdentityVerifier.from_openai",
                return_value=_FakeIdentityVerifier(),
            ),
        ):
            pipeline = LLMExtractionPipeline.from_pretrained(
                entity_backend="gliner",
                entity_labels=("gene",),
            )

        self.assertIs(pipeline.entity_extractor, entity_extractor)
        load_entities.assert_called_once_with(
            model_name=DEFAULT_ENTITY_MODEL,
            labels=("gene",),
            threshold=0.5,
            device=None,
        )

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
            patch(
                "biomedical_extractor.llm_pipeline.LLMExplicitIdentityVerifier.from_openai",
                return_value=_FakeIdentityVerifier(),
            ) as load_identity,
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
        load_identity.assert_called_once_with(None)

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
            "BRCA1 affects cancer.",
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
            "p53 decreased proliferation ability in SSC-4 cells.",
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

    def test_composed_path_exposes_graph_result_without_a_second_extraction(self):
        valid_entities = (
            Entity("E1", "BRCA1", "gene", 0, 5, 0.9),
            Entity("E2", "breast cancer", "disease", 25, 38, 0.8),
        )

        class ValidEntityExtractor:
            def __init__(self):
                self.calls = []

            def extract_entities(self, text):
                self.calls.append(text)
                return valid_entities

        entity_extractor = ValidEntityExtractor()
        relation_extractor = _FakeRelationExtractor()
        pipeline = LLMExtractionPipeline(entity_extractor, relation_extractor)

        result = pipeline.extract_graph(TEXT, document_id="paper-1")

        self.assertEqual(result.document.id, "paper-1")
        self.assertEqual(tuple(node.id for node in result.nodes), ("doc_e_001", "doc_e_002"))
        self.assertEqual(result.edges[0].source, "doc_e_001")
        self.assertEqual(result.edges[0].target, "doc_e_002")
        self.assertEqual(entity_extractor.calls, [TEXT])
        self.assertEqual(len(relation_extractor.calls), 1)

    def test_graph_path_verifies_before_relations_and_roles_and_merges_before_orphan_detection(self):
        text = (
            "Splicing factor proline and glutamine rich (SFPQ) binds target. "
            "Citrate was included."
        )
        long_form = "proline and glutamine rich"
        long_start = text.index(long_form)
        abbreviation_start = text.index("SFPQ")
        target_start = text.index("target")
        citrate_start = text.index("Citrate")
        entities = (
            Entity("E1", long_form, "Gene", long_start, long_start + len(long_form)),
            Entity("E2", "SFPQ", "Gene", abbreviation_start, abbreviation_start + 4),
            Entity("E3", "target", "Protein", target_start, target_start + 6),
            Entity("E4", "Citrate", "Chemical", citrate_start, citrate_start + 7),
        )
        relation = Relation(
            "E2",
            "E3",
            "binds",
            "SFPQ binds target",
            "SFPQ) binds target",
            False,
        )
        events = []

        class EntityExtractor:
            def extract_entities(self, supplied_text):
                return entities

        class RelationExtractor:
            def extract_relations(self, supplied_text, supplied_entities):
                events.append("relations")
                return RelationExtractionResult((relation,))

        role_extractor = _RecordingRoleExtractor(events)
        verifier = _SameEntityVerifier(events)
        pipeline = LLMExtractionPipeline(
            EntityExtractor(), RelationExtractor(), role_extractor, verifier
        )

        graph = pipeline.extract_graph(text, document_id="sfpq-paper")

        self.assertEqual(events, ["identity", "relations", "roles"])
        self.assertEqual(len(verifier.calls), 1)
        self.assertEqual(tuple(target.label for target in role_extractor.targets), ("Citrate",))
        gene = next(node for node in graph.nodes if node.type == "Gene")
        self.assertEqual(gene.aliases, (long_form, "SFPQ"))
        self.assertIsNone(gene.paper_role)
        self.assertEqual(len(graph.unconnected_nodes), 1)
        self.assertEqual(graph.unconnected_nodes[0].label, "Citrate")
        self.assertEqual(graph.unconnected_nodes[0].paper_role.category, "contextual")

    def test_graph_path_does_not_call_verifier_when_deterministic_identity_resolves_it(self):
        text = (
            "Regulatory pathway complex (RPC) was measured. "
            "Regulatory pathway complex was prevalent."
        )
        fragment = "complex"
        abbreviation = "RPC"
        full_form = "Regulatory pathway complex"
        fragment_start = text.index(fragment)
        abbreviation_start = text.index(abbreviation)
        full_start = text.rindex(full_form)
        entities = (
            Entity("E1", fragment, "Protein", fragment_start, fragment_start + len(fragment)),
            Entity("E2", abbreviation, "Protein", abbreviation_start, abbreviation_start + len(abbreviation)),
            Entity("E3", full_form, "Protein", full_start, full_start + len(full_form)),
        )
        entity_extractor = _FakeEntityExtractor()
        entity_extractor.extract_entities = lambda supplied_text: entities
        relation_extractor = _FakeRelationExtractor(RelationExtractionResult(()))
        verifier = _FakeIdentityVerifier()

        graph = LLMExtractionPipeline(
            entity_extractor, relation_extractor, identity_verifier=verifier
        ).extract_graph(text)

        self.assertEqual(len(verifier.calls), 0)
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(set(graph.nodes[0].aliases), {fragment, abbreviation, full_form})

    def test_composed_path_rechecks_custom_relation_output(self):
        invalid = Relation(
            "E1",
            "E99",
            "association",
            "BRCA1 is associated with breast cancer.",
            "BRCA1 is associated with breast cancer",
            False,
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
