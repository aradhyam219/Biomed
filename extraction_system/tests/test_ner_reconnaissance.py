from __future__ import annotations

import unittest

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.ner_reconnaissance import (
    AGREEMENT_AIONER_ONLY,
    AGREEMENT_BOUNDARY,
    AGREEMENT_CROSS_TYPE,
    AGREEMENT_EXACT,
    AGREEMENT_HUNFLAIR2_ONLY,
    AGREEMENT_TYPE,
    TargetPaper,
    TextSegment,
    align_entity_predictions,
    build_review_packet,
    build_target_domain_report,
    parse_pmc_xml,
    parse_pubmed_xml,
    sentence_cooccurrence_diagnostics,
    sentence_spans,
    summarize_alignments,
)


def _entity(entity_id: str, text: str, entity_type: str, start: int) -> Entity:
    return Entity(entity_id, text, entity_type, start, start + len(text), 0.9)


class NERReconnaissanceTests(unittest.TestCase):
    def test_pmc_parser_marks_full_text_and_preserves_segments(self):
        raw = b"""
        <article>
          <front>
            <article-meta>
              <article-id pub-id-type="pmid">12345</article-id>
              <article-id pub-id-type="pmc">PMC12345</article-id>
              <article-title>BRCA1 in cancer</article-title>
              <abstract><p>BRCA1 was measured.</p></abstract>
            </article-meta>
          </front>
          <body>
            <sec><title>Introduction</title><p>BRCA1 regulates repair.</p></sec>
            <sec><title>Results</title><p>Cells showed a response.</p></sec>
            <ref-list><ref><mixed-citation>Noise</mixed-citation></ref></ref-list>
          </body>
        </article>
        """
        paper = parse_pmc_xml(
            raw,
            paper_id="PMCID:PMC12345",
            source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12345/",
        )

        self.assertEqual(paper.acquisition_mode, "full_text")
        self.assertEqual(paper.pmid, "12345")
        self.assertNotIn("Noise", paper.text)
        for segment in paper.segments:
            self.assertEqual(paper.text[segment.start : segment.end], segment.text)
        self.assertEqual(paper.text_checksum, paper.to_dict()["text_sha256"])

    def test_pubmed_parser_marks_abstract_only(self):
        raw = b"""
        <PubmedArticleSet><PubmedArticle><MedlineCitation>
          <PMID>123</PMID><Article>
            <ArticleTitle>TP53 disease</ArticleTitle>
            <Abstract><AbstractText Label="BACKGROUND">TP53 matters.</AbstractText></Abstract>
          </Article>
        </MedlineCitation></PubmedArticle></PubmedArticleSet>
        """
        paper = parse_pubmed_xml(
            raw,
            paper_id="PMID:123",
            source_url="https://pubmed.ncbi.nlm.nih.gov/123/",
            pmid="123",
        )

        self.assertEqual(paper.acquisition_mode, "abstract_only")
        self.assertEqual(paper.section_availability, ("title", "abstract / BACKGROUND"))
        self.assertIn("TP53 matters.", paper.text)

    def test_alignment_categories_are_explicit_and_deterministic(self):
        text = "BRCA1 cancer cells"
        self.assertEqual(
            align_entity_predictions(
                (_entity("a1", "BRCA1", "Gene", 0),),
                (_entity("h1", "BRCA1", "Gene", 0),),
            )[0].category,
            AGREEMENT_EXACT,
        )
        self.assertEqual(
            align_entity_predictions(
                (_entity("a1", "cancer", "Disease", 6),),
                (_entity("h1", "cancer", "Chemical", 6),),
            )[0].category,
            AGREEMENT_TYPE,
        )
        self.assertEqual(
            align_entity_predictions(
                (_entity("a1", "cells", "CellLine", 13),),
                (_entity("h1", "cell", "CellLine", 13),),
            )[0].category,
            AGREEMENT_BOUNDARY,
        )
        self.assertEqual(
            align_entity_predictions(
                (_entity("a1", "cancer", "Disease", 6),),
                (_entity("h1", "canc", "Chemical", 6),),
            )[0].category,
            AGREEMENT_CROSS_TYPE,
        )
        categories = [
            alignment.category
            for alignment in align_entity_predictions(
                (_entity("a1", "BRCA1", "Gene", 0),),
                (_entity("h1", "cells", "CellLine", 13),),
            )
        ]
        self.assertIn(AGREEMENT_AIONER_ONLY, categories)
        self.assertIn(AGREEMENT_HUNFLAIR2_ONLY, categories)

    def test_sentence_diagnostics_count_pairs_without_relations(self):
        text = "BRCA1 causes cancer. Cells express TP53."
        entities = (
            _entity("e1", "BRCA1", "Gene", 0),
            _entity("e2", "cancer", "Disease", 13),
            _entity("e3", "Cells", "CellLine", 22),
            _entity("e4", "TP53", "Gene", 36),
        )

        spans = sentence_spans(text)
        diagnostics = sentence_cooccurrence_diagnostics(text, entities)

        self.assertEqual(len(spans), 2)
        self.assertEqual(diagnostics["sentences_containing_at_least_one_entity"], 2)
        self.assertEqual(diagnostics["sentences_containing_at_least_two_entities"], 2)
        self.assertEqual(diagnostics["distinct_entity_pairs_cooccurring_within_sentence"], 2)
        self.assertEqual(diagnostics["entity_class_combinations"]["DiseaseOrPhenotypicFeature ↔ GeneOrGeneProduct"], 1)

    def test_review_sampling_and_per_type_statistics_are_repeatable(self):
        entities_a = (_entity("a1", "BRCA1", "Gene", 0),)
        entities_h = (_entity("h1", "BRCA1", "Gene", 0),)
        alignments = align_entity_predictions(entities_a, entities_h)
        summary = summarize_alignments(
            alignments,
            selected_types=("GeneOrGeneProduct",),
        )
        candidate = {
            "paper_id": "PMID:1",
            "category": AGREEMENT_EXACT,
            "entity_class": "GeneOrGeneProduct",
            "source_span": {"start": 0, "end": 5, "text": "BRCA1"},
        }

        self.assertEqual(summary["counts"][AGREEMENT_EXACT], 1)
        self.assertEqual(summary["by_entity_class"]["GeneOrGeneProduct"]["exact_agreement_fraction"], 1.0)
        first = build_review_packet([candidate] * 3, target_count=10)
        second = build_review_packet([candidate] * 3, target_count=10)
        self.assertEqual(first, second)
        self.assertEqual(first["selection"]["selected_count"], 1)

    def test_review_sampling_covers_later_categories_when_capacity_allows(self):
        candidates = [
            {
                "paper_id": f"PMID:exact-{index}",
                "category": AGREEMENT_EXACT,
                "entity_class": f"class-{index}",
                "source_span": {"start": index, "end": index + 1, "text": "x"},
            }
            for index in range(5)
        ]
        candidates.extend(
            [
                {
                    "paper_id": "PMID:type",
                    "category": AGREEMENT_TYPE,
                    "entity_class": "GeneOrGeneProduct",
                    "source_span": {"start": 20, "end": 21, "text": "x"},
                },
                {
                    "paper_id": "PMID:multi",
                    "category": "multi_entity_sentence",
                    "entity_class": "multiple",
                    "source_span": {"start": 30, "end": 31, "text": "x"},
                },
            ]
        )

        packet = build_review_packet(candidates, target_count=3)
        selected_categories = {
            example["category"] for example in packet["examples"]
        }
        self.assertEqual(packet["selection"]["selected_count"], 3)
        self.assertIn(AGREEMENT_TYPE, selected_categories)
        self.assertIn("multi_entity_sentence", selected_categories)

    def test_target_report_keeps_variant_and_cellline_views_separate(self):
        text = "BRCA1 rs123 cells"
        paper = TargetPaper(
            paper_id="PMID:1",
            pmid="1",
            pmcid=None,
            title="BRCA1",
            source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
            acquisition_mode="abstract_only",
            text=text,
            segments=(TextSegment("title", text, 0, len(text)),),
            source_checksum="source",
            source_format="pubmed_xml",
        )
        report, review = build_target_domain_report(
            (paper,),
            {
                paper.paper_id: (
                    _entity("a1", "BRCA1", "Gene", 0),
                    _entity("a2", "rs123", "Variant", 6),
                    _entity("a3", "cells", "CellLine", 12),
                )
            },
            {
                paper.paper_id: (
                    _entity("h1", "BRCA1", "Gene", 0),
                    _entity("h2", "cells", "CellLine", 12),
                )
            },
            review_target_count=10,
        )

        self.assertEqual(report["sequence_variant"]["aioner_prediction_count"], 1)
        self.assertEqual(report["cell_line"]["prediction_counts"]["AIONER"], 1)
        self.assertEqual(report["cell_line"]["shared_exact_agreements"], 1)
        self.assertGreater(review["selection"]["selected_count"], 0)
        self.assertLessEqual(review["selection"]["selected_count"], 10)


if __name__ == "__main__":
    unittest.main()
