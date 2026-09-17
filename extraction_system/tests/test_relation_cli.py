from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.relation_cli import main
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
                    False,
                ),
            )
        )


class RelationCLITests(unittest.TestCase):
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
                    "--predicate",
                    "association",
                    "--max-retries",
                    "0",
                ]
            )

        self.assertEqual(result, 0)
        config = load.call_args.args[0]
        self.assertIsInstance(config, OpenAIConfig)
        self.assertEqual(config.predicates, ("association",))
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["entities"], [{**entity, "score": None} for entity in entities])
        self.assertEqual(payload["relations"][0]["source"], "E1")


if __name__ == "__main__":
    unittest.main()
