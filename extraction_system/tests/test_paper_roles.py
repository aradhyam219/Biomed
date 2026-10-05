from __future__ import annotations

import unittest
import json
from unittest.mock import patch, Mock

from biomedical_extractor.llm_relation_extraction import OpenAIConfig

from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.llm_paper_roles import LLMPaperRoleExtractor
from biomedical_extractor.paper_roles import (
    PaperRole,
    PaperRoleExtractionResult,
    PaperRoleRecord,
    PaperRoleTarget,
    PaperRoleValidationError,
    apply_paper_roles,
    validate_paper_role_result,
)
from biomedical_extractor.relation_extraction import RelationExtractionResult
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline


class _RoleRunnable:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.response


class _EntityExtractor:
    def __init__(self, entities):
        self.entities = entities

    def extract_entities(self, text):
        return self.entities


class _RelationExtractor:
    def __init__(self):
        self.calls = []

    def extract_relations(self, text, entities):
        self.calls.append((text, tuple(entities)))
        return RelationExtractionResult(())


class _RoleExtractor:
    def __init__(self):
        self.calls = []

    def extract_roles(self, title, text, targets):
        self.calls.append((title, text, tuple(targets)))
        return PaperRoleExtractionResult(
            tuple(
                PaperRoleRecord(
                    target.node_id,
                    PaperRole(
                        "contextual" if target.type == "Species" else "substantive",
                        (f"{target.label} was explicitly described in this paper.",),
                        (target.mentions[0].text,),
                    ),
                )
                for target in targets
            )
        )


class PaperRoleContractTests(unittest.TestCase):
    def _graph_with_unconnected_nodes(self):
        text = "GeneA affects disease. GeneX was studied in mice."
        gene_a = text.index("GeneA")
        disease = text.index("disease")
        gene_x = text.index("GeneX")
        mice = text.index("mice")
        entities = (
            Entity("E1", "GeneA", "Gene", gene_a, gene_a + 5),
            Entity("E2", "disease", "Disease", disease, disease + 7),
            Entity("E3", "GeneX", "Gene", gene_x, gene_x + 5),
            Entity("E4", "mice", "Species", mice, mice + 4),
        )
        relation = (
            __import__("biomedical_extractor.relation_extraction", fromlist=["Relation"])
            .Relation("E1", "E2", "affects", "GeneA affects disease.", "GeneA affects disease", False),
        )
        graph = build_graph_result("paper-1", assemble_document_entities(entities, text), relation)
        return text, graph

    def test_role_records_attach_only_to_genuinely_unconnected_nodes(self):
        text, graph = self._graph_with_unconnected_nodes()
        targets = tuple(
            PaperRoleTarget(node.id, node.label, node.type, node.mentions)
            for node in graph.unconnected_nodes
        )
        result = PaperRoleExtractionResult(
            (
                PaperRoleRecord(
                    "doc_e_003",
                    PaperRole("substantive", ("GeneX was studied in mice.",), ("GeneX",)),
                ),
                PaperRoleRecord(
                    "doc_e_004",
                    PaperRole("contextual", ("Mice supplied the experimental context.",), ("mice",)),
                ),
            )
        )

        enriched = apply_paper_roles(graph, text, result)

        self.assertEqual(
            [node.id for node in enriched.nodes if node.paper_role],
            ["doc_e_003", "doc_e_004"],
        )
        self.assertIsNone(enriched.nodes[0].paper_role)
        self.assertEqual(enriched.edges, graph.edges)
        self.assertEqual(enriched.to_dict()["nodes"][2]["paper_role"]["category"], "substantive")

    def test_species_role_must_be_contextual_and_evidence_is_verbatim(self):
        text, graph = self._graph_with_unconnected_nodes()
        targets = tuple(
            PaperRoleTarget(node.id, node.label, node.type, node.mentions)
            for node in graph.unconnected_nodes
        )
        bad_category = PaperRoleExtractionResult(
            (
                PaperRoleRecord("doc_e_003", PaperRole("substantive", ("GeneX was studied.",), ("GeneX",))),
                PaperRoleRecord("doc_e_004", PaperRole("substantive", ("Mice were used.",), ("mice",))),
            )
        )
        with self.assertRaisesRegex(PaperRoleValidationError, "Species target"):
            validate_paper_role_result(text, targets, bad_category)

        bad_evidence = PaperRoleExtractionResult(
            (
                PaperRoleRecord("doc_e_003", PaperRole("substantive", ("GeneX was studied.",), ("not in source",))),
                PaperRoleRecord("doc_e_004", PaperRole("contextual", ("Mice were used.",), ("mice",))),
            )
        )
        with self.assertRaisesRegex(PaperRoleValidationError, "verbatim"):
            validate_paper_role_result(text, targets, bad_evidence)

    def test_unknown_node_ids_and_provider_objects_do_not_cross_domain_seam(self):
        text, graph = self._graph_with_unconnected_nodes()
        targets = tuple(
            PaperRoleTarget(node.id, node.label, node.type, node.mentions)
            for node in graph.unconnected_nodes
        )
        unknown = PaperRoleExtractionResult(
            (
                PaperRoleRecord("doc_e_999", PaperRole("substantive", ("Short.",), ("GeneX",))),
                PaperRoleRecord("doc_e_004", PaperRole("contextual", ("Mice were used.",), ("mice",))),
            )
        )
        with self.assertRaisesRegex(PaperRoleValidationError, "unknown node"):
            validate_paper_role_result(text, targets, unknown)

        with self.assertRaises(PaperRoleValidationError):
            validate_paper_role_result(text, targets, {"roles": []})

    def test_thin_source_support_allows_one_short_paragraph(self):
        role = PaperRole("substantive", ("GeneX was measured.",), ("GeneX was measured.",))
        self.assertEqual(len(role.paragraphs), 1)
        self.assertEqual(len(role.evidence), 1)

    def test_provider_returns_one_local_record_per_target_in_one_call(self):
        text = "GeneX was measured. mice supplied context."
        entities = (
            Entity("E1", "GeneX", "Gene", 0, 5),
            Entity("E2", "mice", "Species", text.index("mice"), text.index("mice") + 4),
        )
        targets = (
            PaperRoleTarget("doc_e_001", "GeneX", "Gene", (entities[0],)),
            PaperRoleTarget("doc_e_002", "mice", "Species", (entities[1],)),
        )
        runnable = _RoleRunnable(
            {
                "roles": [
                    {
                        "node_id": "doc_e_001",
                        "category": "substantive",
                        "paragraphs": ["GeneX was measured."],
                        "evidence": ["GeneX was measured."],
                    },
                    {
                        "node_id": "doc_e_002",
                        "category": "contextual",
                        "paragraphs": ["Mice supplied context."],
                        "evidence": ["mice supplied context."],
                    },
                ]
            }
        )
        extractor = LLMPaperRoleExtractor(runnable, max_retries=0)

        result = extractor.extract_roles("A short paper", text, targets)

        self.assertEqual([record.node_id for record in result.records], ["doc_e_001", "doc_e_002"])
        self.assertEqual(len(runnable.prompts), 1)
        self.assertIn("A short paper", runnable.prompts[0])
        self.assertIn('"text": "GeneX"', runnable.prompts[0])

    def test_pipeline_enriches_after_graph_cleanup_without_changing_edges(self):
        text = "GeneX was studied in mice."
        entities = (
            Entity("E1", "GeneX", "Gene", 0, 5),
            Entity("E2", "mice", "Species", text.index("mice"), text.index("mice") + 4),
        )
        role_extractor = _RoleExtractor()
        pipeline = LLMExtractionPipeline(_EntityExtractor(entities), _RelationExtractor(), role_extractor)

        graph = pipeline.extract_graph(text, document_id="paper-1", paper_title="A paper")

        self.assertEqual(len(role_extractor.calls), 1)
        self.assertEqual(len(role_extractor.calls[0][2]), 2)
        self.assertEqual(len(graph.edges), 0)
        self.assertEqual([node.paper_role.category for node in graph.nodes], ["substantive", "contextual"])


    def _ordinary_pipeline(self, entities, relations, injected=None):
        with (
            patch("biomedical_extractor.llm_pipeline.HunFlair2BioMedExtractor.from_pretrained",
                  return_value=_EntityExtractor(entities)),
            patch("biomedical_extractor.llm_pipeline.LLMRelationExtractor.from_openai",
                  return_value=relations),
        ):
            return LLMExtractionPipeline.from_pretrained(paper_role_extractor=injected)

    def test_ordinary_graph_batches_zero_one_and_several_orphans_lazily(self):
        text = "GeneA affects disease. GeneX was studied in mice."
        entities = tuple(mention for node in self._graph_with_unconnected_nodes()[1].nodes
                         for mention in node.mentions)
        from biomedical_extractor.relation_extraction import Relation
        relation = Relation("E1", "E2", "affects", "GeneA affects disease.",
                            "GeneA affects disease", False)
        connected = Mock()
        connected.extract_relations.return_value = RelationExtractionResult((relation,))
        for count in (0, 1, 2):
            with self.subTest(orphans=count):
                roles = _RoleExtractor()
                pipeline = self._ordinary_pipeline(entities[:2 + count], connected)
                with patch("biomedical_extractor.llm_pipeline.LLMPaperRoleExtractor.from_openai",
                           return_value=roles) as factory:
                    factory.assert_not_called()
                    graph = pipeline.extract_graph(text)
                    self.assertEqual(factory.call_count, int(count > 0))
                self.assertEqual(len(roles.calls), int(count > 0))
                self.assertEqual(sum(node.paper_role is not None for node in graph.nodes), count)
                if count:
                    self.assertEqual(len(roles.calls[0][2]), count)
                before = build_graph_result("input", assemble_document_entities(entities[:2 + count], text),
                                            (relation,)).to_dict()
                after = graph.to_dict()
                for node in after["nodes"]:
                    node.pop("paper_role", None)
                self.assertEqual(after, before)

    def test_ordinary_injected_role_extractor_bypasses_default_factory(self):
        text = "GeneX"
        roles = _RoleExtractor()
        pipeline = self._ordinary_pipeline((Entity("E1", text, "Gene", 0, 5),),
                                           _RelationExtractor(), roles)
        with patch("biomedical_extractor.llm_pipeline.LLMPaperRoleExtractor.from_openai") as factory:
            self.assertIsNotNone(pipeline.extract_graph(text).nodes[0].paper_role)
            factory.assert_not_called()

    def test_missing_record_fails_atomically_and_preserves_original_graph(self):
        text, graph = self._graph_with_unconnected_nodes()
        original = graph.to_dict()
        partial = PaperRoleExtractionResult((PaperRoleRecord(
            graph.unconnected_nodes[0].id, PaperRole("substantive", ("GeneX was studied.",), ("GeneX",))),))
        with self.assertRaisesRegex(PaperRoleValidationError, "missing node"):
            apply_paper_roles(graph, text, partial)
        self.assertEqual(graph.to_dict(), original)
        broken = Mock()
        broken.extract_roles.return_value = partial
        entities = tuple(mention for node in graph.nodes for mention in node.mentions)
        pipeline = self._ordinary_pipeline(entities, _RelationExtractor(), broken)
        with self.assertRaisesRegex(PaperRoleValidationError, "missing node"):
            pipeline.extract_graph(text)

    def test_background_role_transport_configuration_and_bounded_repair(self):
        client = Mock()
        good = {"roles": [{"node_id": "N1", "category": "substantive",
                           "paragraphs": ["GeneX was measured."], "evidence": ["GeneX"]}]}
        client.responses.create.side_effect = [
            Mock(id="resp_bad", status="completed", output_text=json.dumps({"roles": []}),
                 output=[], error=None, incomplete_details=None),
            Mock(id="resp_good", status="completed", output_text=json.dumps(good),
                 output=[], error=None, incomplete_details=None),
        ]
        config = OpenAIConfig(api_key="test-key", model="custom-relation-model",
                              reasoning_effort="low", background=False, service_tier="flex",
                              max_retries=1)
        with patch("openai.OpenAI", return_value=client) as factory:
            extractor = LLMPaperRoleExtractor.from_openai(config)
        target = PaperRoleTarget("N1", "GeneX", "Gene", (Entity("E1", "GeneX", "Gene", 0, 5),))
        result = extractor.extract_roles("Title", "GeneX was measured.", (target,))
        self.assertEqual(len(result.records), 1)
        self.assertEqual(client.responses.create.call_count, 2)
        request = client.responses.create.call_args_list[0].kwargs
        self.assertEqual(request["model"], "gpt-6.1-sol")
        self.assertEqual(request["reasoning"], {"effort": "medium"})
        self.assertEqual(request["service_tier"], "default")
        self.assertTrue(request["background"])
        self.assertEqual(request["text"]["format"]["name"], "StructuredPaperRolePayload")
        schema = request["text"]["format"]["schema"]
        self.assertEqual(schema["required"], ["roles"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual([d["repair"] for d in extractor.last_generation_diagnostics], [False, True])
        self.assertEqual(factory.call_args.kwargs["max_retries"], 0)

    def test_background_provider_failure_is_explicit_and_never_repaired(self):
        from biomedical_extractor.llm_paper_roles import PaperRoleExtractionError
        client = Mock()
        client.responses.create.side_effect = RuntimeError("provider unavailable")
        with patch("openai.OpenAI", return_value=client):
            extractor = LLMPaperRoleExtractor.from_openai(OpenAIConfig(api_key="test-key"))
        target = PaperRoleTarget("N1", "GeneX", "Gene", ())
        with self.assertRaisesRegex(PaperRoleExtractionError, "provider invocation failed"):
            extractor.extract_roles("Title", "GeneX", (target,))
        self.assertEqual(client.responses.create.call_count, 1)


if __name__ == "__main__":
    unittest.main()
