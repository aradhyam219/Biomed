from __future__ import annotations

import json
import os
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.relation_cli import main, openai_config_from_args
from biomedical_extractor.relation_extraction import Relation, RelationExtractionResult


class _FakeRelationExtractor:
    def extract_relations(self, text, entities):
        return RelationExtractionResult(
            (
                Relation(
                    entities[0].id,
                    entities[1].id,
                    "association",
                    text,
                    text,
                    False,
                ),
            )
        )


class RelationCLITests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_cli_overrides_preserve_explicit_background_environment_settings(self):
        with patch.dict(
            os.environ,
            {
                "BIOMEDICAL_RELATION_MODEL": "gpt-6.1-sol",
                "BIOMEDICAL_RELATION_REASONING_EFFORT": "medium",
                "BIOMEDICAL_RELATION_BACKGROUND": "true",
                "BIOMEDICAL_RELATION_SERVICE_TIER": "default",
                "BIOMEDICAL_RELATION_POLL_INTERVAL_SECONDS": "5",
                "BIOMEDICAL_RELATION_TIMEOUT_SECONDS": "1200",
            },
            clear=True,
        ):
            config = openai_config_from_args(Namespace(model=None, max_retries=0))

        self.assertEqual(config.model, "gpt-6.1-sol")
        self.assertEqual(config.reasoning_effort, "medium")
        self.assertTrue(config.background)
        self.assertEqual(config.service_tier, "default")
        self.assertEqual(config.poll_interval_seconds, 5)
        self.assertEqual(config.generation_timeout_seconds, 1200)
        self.assertEqual(config.max_retries, 0)

    def test_re_only_command_accepts_supplied_entity_json(self):
        text = "BRCA1 is associated with breast cancer."
        entities = [
            {"id": "E1", "text": "BRCA1", "type": "gene", "start": 0, "end": 5},
            {
                "id": "E2",
                "text": "breast cancer",
                "type": "disease",
                "start": 24,
                "end": 37,
            },
        ]
        output = StringIO()
        with patch(
            "biomedical_extractor.relation_cli.LLMRelationExtractor.from_openai",
            return_value=_FakeRelationExtractor(),
        ) as load, redirect_stdout(output):
            result = main(
                [
                    "--text",
                    text,
                    "--entities",
                    json.dumps(entities),
                    "--max-retries",
                    "0",
                ]
            )

        self.assertEqual(result, 0)
        config = load.call_args.args[0]
        self.assertIsInstance(config, OpenAIConfig)
        self.assertEqual(config.model, "gpt-6.1-sol")
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["entities"], [{**entity, "score": None} for entity in entities])
        self.assertEqual(payload["relations"][0]["source"], "E1")


if __name__ == "__main__":
    unittest.main()
