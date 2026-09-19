from __future__ import annotations

import json
import unittest

from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.graph import (
    GraphConstructionError,
    build_graph_result,
)
from biomedical_extractor.relation_extraction import Relation, RelationExtractionResult


class GraphBoundaryTests(unittest.TestCase):
    def test_assembled_entities_become_nodes_with_all_mentions(self):
        text = "kinetochore-associated protein 1 (KNTC1) affects disease."
        full_form = "kinetochore-associated protein 1"
        mentions = (
            Entity("E1", full_form, "Gene", 0, len(full_form), 0.7),
            Entity("E2", "KNTC1", "Gene", text.index("KNTC1"), text.index("KNTC1") + 5, 0.9),
            Entity(
                "E3",
                "disease",
                "Disease",
                text.index("disease"),
                text.index("disease") + len("disease"),
                0.8,
            ),
        )

        graph = build_graph_result(
            "paper-1", assemble_document_entities(mentions, text), ()
        )

        self.assertEqual(graph.document.id, "paper-1")
        self.assertEqual(tuple(node.id for node in graph.nodes), ("doc_e_001", "doc_e_002"))
        self.assertEqual(graph.nodes[0].label, "KNTC1")
        self.assertEqual(graph.nodes[0].type, "Gene")
        self.assertEqual(tuple(mention.id for mention in graph.nodes[0].mentions), ("E1", "E2"))
        self.assertEqual(graph.nodes[0].aliases, (full_form, "KNTC1"))

    def test_relation_endpoints_remap_to_assembled_node_ids(self):
        text = "kinetochore-associated protein 1 (KNTC1) affects disease."
        full_form = "kinetochore-associated protein 1"
        mentions = (
            Entity("E1", full_form, "Gene", 0, len(full_form)),
            Entity("E2", "KNTC1", "Gene", text.index("KNTC1"), text.index("KNTC1") + 5),
            Entity("E3", "disease", "Disease", text.index("disease"), text.index("disease") + 7),
        )
        relation = Relation("E2", "E3", "affects", "KNTC1) affects disease", False)

        graph = build_graph_result(
            "paper-1", assemble_document_entities(mentions, text), (relation,)
        )

        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].source, "doc_e_001")
        self.assertEqual(graph.edges[0].target, "doc_e_002")

    def test_missing_endpoint_mapping_fails_without_dangling_edge(self):
        text = "BRCA1 affects disease."
        mentions = (
            Entity("E1", "BRCA1", "Gene", 0, 5),
            Entity("E2", "disease", "Disease", 14, 21),
        )
        relation = Relation("E1", "E99", "affects", "BRCA1 affects disease", False)

        with self.assertRaisesRegex(GraphConstructionError, "target mention ID 'E99'"):
            build_graph_result(
                "paper-1", assemble_document_entities(mentions, text), (relation,)
            )

    def test_evidence_direction_and_negation_are_preserved(self):
        text = "BRCA1 does not affect disease."
        disease_start = text.index("disease")
        mentions = (
            Entity("E1", "BRCA1", "Gene", 0, 5),
            Entity("E2", "disease", "Disease", disease_start, disease_start + 7),
        )
        relation = Relation(
            "E1",
            "E2",
            "affects",
            "BRCA1 does not affect disease",
            True,
            surface_form="does not affect",
            score=0.64,
        )

        graph = build_graph_result(
            "paper-1", assemble_document_entities(mentions, text), (relation,)
        )

        edge = graph.edges[0]
        self.assertEqual((edge.source, edge.target), ("doc_e_001", "doc_e_002"))
        self.assertEqual(edge.predicate, "affects")
        self.assertTrue(edge.negated)
        self.assertEqual(edge.evidence[0].text, relation.evidence)
        self.assertEqual(edge.evidence[0].surface_form, relation.surface_form)
        self.assertEqual(edge.evidence[0].score, relation.score)

    def test_duplicate_conceptual_edges_aggregate_all_evidence_deterministically(self):
        text = "BRCA1 inhibits cancer. BRCA1 inhibits cancer."
        first_gene = text.index("BRCA1")
        second_gene = text.rindex("BRCA1")
        first_disease = text.index("cancer")
        second_disease = text.rindex("cancer")
        mentions = (
            Entity("E1", "BRCA1", "Gene", first_gene, first_gene + 5),
            Entity("E2", "cancer", "Disease", first_disease, first_disease + 6),
            Entity("E3", "BRCA1", "Gene", second_gene, second_gene + 5),
            Entity("E4", "cancer", "Disease", second_disease, second_disease + 6),
        )
        relations = (
            Relation("E3", "E4", "inhibits", "BRCA1 inhibits cancer", False, score=0.8),
            Relation("E1", "E2", "inhibits", "BRCA1 inhibits cancer", False, score=0.2),
        )

        graph = build_graph_result(
            "paper-1", assemble_document_entities(mentions, text), relations
        )

        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].id, "doc_r_001")
        self.assertEqual(
            tuple(evidence.score for evidence in graph.edges[0].evidence), (0.2, 0.8)
        )
        self.assertEqual(len(graph.edges[0].evidence), 2)

    def test_assembly_induced_self_edges_are_suppressed_but_explicit_self_is_retained(self):
        text = "BRCA1 interacts with BRCA1."
        first = text.index("BRCA1")
        second = text.rindex("BRCA1")
        mentions = (
            Entity("E1", "BRCA1", "Gene", first, first + 5),
            Entity("E2", "BRCA1", "Gene", second, second + 5),
        )
        assembly = assemble_document_entities(mentions, text)

        assembly_induced = Relation("E1", "E2", "interacts", "BRCA1 interacts with BRCA1", False)
        explicit_self = Relation("E1", "E1", "self-associates", "BRCA1 interacts with BRCA1", False)

        suppressed = build_graph_result("paper-1", assembly, (assembly_induced,))
        retained = build_graph_result("paper-1", assembly, (explicit_self,))

        self.assertEqual(suppressed.edges, ())
        self.assertEqual(len(retained.edges), 1)
        self.assertEqual(retained.edges[0].source, retained.edges[0].target)

    def test_result_and_json_are_deterministic_and_json_serializable(self):
        text = "BRCA1 affects disease; drug affects BRCA1."
        mentions = (
            Entity("E1", "BRCA1", "Gene", 0, 5),
            Entity("E2", "disease", "Disease", 14, 21),
            Entity("E3", "drug", "Chemical", 23, 27),
        )
        relations = RelationExtractionResult(
            (
                Relation("E3", "E1", "affects", "drug affects BRCA1", False),
                Relation("E1", "E2", "affects", "BRCA1 affects disease", False),
            )
        )
        assembly = assemble_document_entities(mentions, text)

        first = build_graph_result("paper-1", assembly, relations)
        second = build_graph_result("paper-1", assembly, relations)

        self.assertEqual(first, second)
        self.assertEqual(first.to_json(), second.to_json())
        payload = json.loads(first.to_json())
        self.assertEqual(payload, first.to_dict())
        self.assertEqual(
            {node["id"] for node in payload["nodes"]},
            {edge[field] for edge in payload["edges"] for field in ("source", "target")},
        )


if __name__ == "__main__":
    unittest.main()
