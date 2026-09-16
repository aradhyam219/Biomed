from __future__ import annotations

import unittest
from pathlib import Path

from biomedical_extractor.biored import (
    BioREDDataset,
    BioREDDocument,
    TypedRelation,
)
from biomedical_extractor.biored_cli import (
    EXCLUDED_DOCUMENT_ID,
    _build_summary,
    _cache_identity,
    _complete_fit_documents,
    _default_output,
    _default_output_for_checkpoint,
    _parser,
)


class BioREDCLITests(unittest.TestCase):
    def test_final_report_is_tracked_but_subset_diagnostics_remain_cached(self):
        self.assertEqual(
            _default_output(None), Path("reports/biored_v0b_complete_fit.json")
        )
        self.assertEqual(
            _default_output(5), Path(".cache/biored_v0b_subset_summary.json")
        )

    def test_model_checkpoint_is_not_cli_configurable(self):
        with self.assertRaises(SystemExit):
            _parser().parse_args(["--dataset", "dev.json", "--model", "other"])

    def test_custom_checkpoint_uses_separate_cache_and_report_defaults(self):
        dataset = BioREDDataset(
            path=Path("Dev.BioC.JSON"),
            split="dev",
            sha256="sha",
            source="BioC",
            date="date",
            key="key",
            documents=(),
        )

        self.assertEqual(
            _cache_identity(dataset, "local/final")["model"], "local/final"
        )
        self.assertEqual(
            _default_output_for_checkpoint(None, "local/final"),
            Path(".cache/biored_v1_dev_summary.json"),
        )

    def test_complete_fit_exclusion_and_coverage_are_prediction_independent(self):
        kept = BioREDDocument(
            id="kept",
            text="short",
            mentions=(),
            relations=(TypedRelation("kept", "1", "2", "Association"),),
        )
        excluded = BioREDDocument(
            id=EXCLUDED_DOCUMENT_ID,
            text="long",
            mentions=(),
            relations=(
                TypedRelation(EXCLUDED_DOCUMENT_ID, "3", "4", "Association"),
                TypedRelation(EXCLUDED_DOCUMENT_ID, "5", "6", "Bind"),
            ),
        )
        dataset = BioREDDataset(
            path=Path("Dev.BioC.JSON"),
            split="dev",
            sha256="sha",
            source="BioC",
            date="date",
            key="key",
            documents=(kept, excluded),
        )
        sequence = {
            "documents_over_max_len": [
                {"document_id": EXCLUDED_DOCUMENT_ID, "tokens": 554}
            ]
        }

        evaluated = _complete_fit_documents(dataset.documents, sequence)
        summary = _build_summary(dataset, evaluated, (), 0)

        self.assertEqual(evaluated, (kept,))
        self.assertEqual(summary["coverage"]["documents"]["evaluated"], 1)
        self.assertEqual(summary["coverage"]["gold_relations"]["official_dev_total"], 3)
        self.assertEqual(summary["coverage"]["gold_relations"]["evaluated"], 1)
        self.assertEqual(
            summary["coverage"]["excluded_documents"][0]["gold_relations"], 2
        )

    def test_unapproved_over_limit_document_fails_closed(self):
        document = BioREDDocument("other", "text", (), ())
        sequence = {
            "documents_over_max_len": [{"document_id": "other", "tokens": 513}]
        }

        with self.assertRaisesRegex(ValueError, "unexpected over-limit"):
            _complete_fit_documents((document,), sequence)


if __name__ == "__main__":
    unittest.main()
