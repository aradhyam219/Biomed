from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.llm_pipeline import ComposedExtractionResult
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.llm_cli import main
from biomedical_extractor.relation_extraction import Relation


class _FakePipeline:
    def extract(self, text):
        return ComposedExtractionResult(
            entities=(Entity("E1", text, "gene", 0, len(text), None),),
            relations=(
                Relation("E1", "E1", "association", text, False),
            ),
        )


class LLMCLITests(unittest.TestCase):
    def test_composed_command_constructs_llm_pipeline_without_running_real_models(self):
        output = StringIO()
        with patch(
            "biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained",
            return_value=_FakePipeline(),
        ) as load, redirect_stdout(output):
            result = main(
                [
                    "--text",
                    "BRCA1",
                    "--entity-label",
                    "gene",
                    "--predicate",
                    "association",
                    "--max-retries",
                    "0",
                    "--device",
                    "cpu",
                ]
            )

        self.assertEqual(result, 0)
        kwargs = load.call_args.kwargs
        self.assertEqual(kwargs["entity_labels"], ("gene",))
        self.assertEqual(kwargs["entity_threshold"], 0.5)
        self.assertEqual(kwargs["device"], "cpu")
        self.assertIsInstance(kwargs["llm_config"], OpenAIConfig)
        self.assertEqual(kwargs["llm_config"].predicates, ("association",))
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["relations"][0]["target"], "E1")


if __name__ == "__main__":
    unittest.main()
