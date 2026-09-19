from __future__ import annotations

import unittest

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.ner_reconnaissance import TargetPaper, TextSegment
from biomedical_extractor.target_domain_pilot import (
    APPROVED_ENTITY_TYPES,
    AnnotationValidationError,
    TrainingCompatibilityError,
    assert_flat_hunflair2_gold_supported,
    build_pilot_package,
    build_split_manifest,
    evaluate_pilot_predictions,
    validate_annotation_package,
)


def _papers() -> tuple[TargetPaper, ...]:
    """Create the nine-paper shape with stable canonical offsets for unit tests."""

    identifiers = (
        "PMID:27370646",
        "PMID:27172794",
        "PMID:33652126",
        "PMID:31324362",
        "PMCID:PMC8605525",
        "PMCID:PMC11824863",
        "PMID:38569671",
        "PMCID:PMC10444909",
        "PMCID:PMC10770459",
    )
    text = "BRCA1 causes cancer."
    return tuple(
        TargetPaper(
            paper_id=paper_id,
            pmid=paper_id.split(":", 1)[1] if paper_id.startswith("PMID:") else None,
            pmcid=paper_id.split(":", 1)[1] if paper_id.startswith("PMCID:") else None,
            title="Pilot",
            source_url="https://example.invalid",
            acquisition_mode="full_text",
            text=text,
            segments=(TextSegment("Introduction", text, 0, len(text)),),
            source_checksum=f"source-{paper_id}",
            source_format="test",
        )
        for paper_id in identifiers
    )


class TargetDomainPilotTests(unittest.TestCase):
    def test_package_is_exhaustive_template_and_split_is_paper_level(self):
        papers = _papers()
        predictions = {
            paper.paper_id: (Entity("H1", "BRCA1", "Gene", 0, 5, 0.9),)
            for paper in papers
        }
        package = build_pilot_package(papers, predictions, target_per_paper=20)
        summary = validate_annotation_package(package, canonical_papers=papers)

        self.assertEqual(package["approved_entity_types"], list(APPROVED_ENTITY_TYPES))
        self.assertEqual(package["selection"]["selected_count"], 9)
        self.assertEqual(summary.incomplete_count, 9)
        self.assertEqual(summary.entity_count, 0)
        self.assertEqual(
            {item["split"] for item in package["examples"]}, {"train", "dev", "test"}
        )
        self.assertTrue(
            all(not item["entities"] for item in package["examples"]),
            "model suggestions must never populate gold",
        )
        self.assertTrue(
            all(item["prediction_context"]["hunflair2"] for item in package["examples"])
        )
        split_counts = {
            split: len(
                {
                    item["paper_id"]
                    for item in package["examples"]
                    if item["split"] == split
                }
            )
            for split in ("train", "dev", "test")
        }
        self.assertEqual(split_counts, {"train": 6, "dev": 1, "test": 2})

    def test_validator_rejects_bad_span_type_and_duplicate(self):
        papers = _papers()
        package = build_pilot_package(papers, {}, target_per_paper=1)
        item = package["examples"][0]
        item["annotation_complete"] = True
        item["annotation_status"] = "complete"
        item["entities"] = [
            {"start": 0, "end": 99, "text": "BRCA1", "type": "NotApproved"},
            {"start": 0, "end": 99, "text": "BRCA1", "type": "NotApproved"},
        ]
        with self.assertRaises(AnnotationValidationError):
            validate_annotation_package(package, canonical_papers=papers)

    def test_overlaps_are_reported_and_training_does_not_silently_change_gold(self):
        papers = _papers()
        package = build_pilot_package(papers, {}, target_per_paper=1)
        item = package["examples"][0]
        for example in package["examples"]:
            example["annotation_complete"] = True
            example["annotation_status"] = "complete"
        item["annotation_complete"] = True
        item["annotation_status"] = "complete"
        item["entities"] = [
            {"start": 0, "end": 5, "text": "BRCA1", "type": "GeneOrGeneProduct"},
            {"start": 0, "end": 4, "text": "BRCA", "type": "SequenceVariant"},
        ]
        summary = validate_annotation_package(package, canonical_papers=papers)
        self.assertEqual(summary.overlaps[0]["example_id"], item["example_id"])
        with self.assertRaisesRegex(TrainingCompatibilityError, "overlapping"):
            assert_flat_hunflair2_gold_supported(package)

    def test_complete_negative_sentence_can_be_validated_for_training(self):
        papers = _papers()
        package = build_pilot_package(papers, {}, target_per_paper=1)
        for item in package["examples"]:
            item["annotation_complete"] = True
            item["annotation_status"] = "complete"
        summary = validate_annotation_package(package, canonical_papers=papers, require_complete=True)
        self.assertEqual(summary.complete_count, 9)
        self.assertEqual(summary.entity_count, 0)

    def test_completion_state_must_be_boolean_and_consistent(self):
        papers = _papers()
        package = build_pilot_package(papers, {}, target_per_paper=1)
        item = package["examples"][0]
        item["annotation_complete"] = "true"
        with self.assertRaises(AnnotationValidationError):
            validate_annotation_package(package)
        item["annotation_complete"] = False
        item["annotation_status"] = "complete"
        with self.assertRaises(AnnotationValidationError):
            validate_annotation_package(package)

    def test_exact_evaluation_reports_per_type_and_failure_categories(self):
        papers = _papers()
        package = build_pilot_package(papers, {}, target_per_paper=1)
        target = next(item for item in package["examples"] if item["split"] == "test")
        for item in package["examples"]:
            item["annotation_complete"] = True
            item["annotation_status"] = "complete"
        target["entities"] = [
            {"start": 0, "end": 5, "text": "BRCA1", "type": "GeneOrGeneProduct"},
        ]
        predictions = {
            target["example_id"]: [
                {"start": 0, "end": 5, "text": "BRCA1", "type": "Gene", "score": 0.8}
            ]
        }
        result = evaluate_pilot_predictions(package, predictions, split="test")
        self.assertEqual(result["micro"]["tp"], 1)
        self.assertEqual(result["per_type"]["GeneOrGeneProduct"]["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
