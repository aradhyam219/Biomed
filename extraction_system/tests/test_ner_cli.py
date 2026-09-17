from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.ner_cli import main


class _FakeEntityExtractor:
    def extract_entities(self, text):
        return (Entity("E1", text, "gene", 0, len(text), 0.9),)


class NERCLITests(unittest.TestCase):
    def test_standalone_command_prints_entity_only_contract(self):
        output = StringIO()
        with patch(
            "biomedical_extractor.ner_cli.GLiNERBioMedExtractor.from_pretrained",
            return_value=_FakeEntityExtractor(),
        ) as load, redirect_stdout(output):
            result = main(
                [
                    "--text",
                    "BRCA1",
                    "--entity-label",
                    "gene",
                    "--entity-threshold",
                    "0.4",
                    "--device",
                    "cpu",
                ]
            )

        self.assertEqual(result, 0)
        load.assert_called_once_with(labels=("gene",), threshold=0.4, device="cpu")
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "input": "BRCA1",
                "entities": [
                    {
                        "id": "E1",
                        "text": "BRCA1",
                        "type": "gene",
                        "start": 0,
                        "end": 5,
                        "score": 0.9,
                    }
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
