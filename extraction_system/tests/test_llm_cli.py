from __future__ import annotations

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from biomedical_extractor.llm_pipeline import ComposedExtractionResult
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.llm_cli import main
from biomedical_extractor.relation_extraction import Relation


class _FakePipeline:
    def extract(self, text):
        return ComposedExtractionResult(
            entities=(Entity("E1", text, "gene", 0, len(text), None),),
            relations=(
                Relation(
                    "E1",
                    "E1",
                    "association",
                    text,
                    text,
                    False,
                ),
            ),
        )

    def extract_graph(self, text, *, document_id):
        entity = Entity("E1", text, "gene", 0, len(text), None)
        assembly = assemble_document_entities((entity,), text)
        return build_graph_result(document_id, assembly, ())


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
                    "--entity-backend",
                    "gliner",
                    "--entity-label",
                    "gene",
                    "--max-retries",
                    "0",
                    "--device",
                    "cpu",
                ]
            )

        self.assertEqual(result, 0)
        kwargs = load.call_args.kwargs
        self.assertEqual(kwargs["entity_backend"], "gliner")
        self.assertEqual(kwargs["entity_labels"], ("gene",))
        self.assertEqual(kwargs["entity_threshold"], 0.5)
        self.assertEqual(kwargs["device"], "cpu")
        self.assertIsInstance(kwargs["llm_config"], OpenAIConfig)
        self.assertEqual(kwargs["llm_config"].model, "gpt-6-luna")
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["relations"][0]["target"], "E1")

    def test_composed_command_defaults_to_hunflair2(self):
        output = StringIO()
        with patch(
            "biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained",
            return_value=_FakePipeline(),
        ) as load, redirect_stdout(output):
            result = main(["--text", "BRCA1", "--max-retries", "0"])

        self.assertEqual(result, 0)
        self.assertEqual(load.call_args.kwargs["entity_backend"], "hunflair2")

    def test_composed_command_can_select_the_hunflair2_prototype_backend(self):
        output = StringIO()
        with patch(
            "biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained",
            return_value=_FakePipeline(),
        ) as load, redirect_stdout(output):
            result = main(
                [
                    "--text",
                    "BRCA1",
                    "--entity-backend",
                    "hunflair2",
                    "--hunflair2-runtime-python",
                    "runtime-python",
                    "--hunflair2-runtime-cache",
                    "runtime-cache",
                    "--max-retries",
                    "0",
                ]
            )

        self.assertEqual(result, 0)
        kwargs = load.call_args.kwargs
        self.assertEqual(kwargs["entity_backend"], "hunflair2")
        self.assertEqual(kwargs["hunflair2_model"], "hunflair/hunflair2-ner")
        self.assertEqual(kwargs["hunflair2_runtime_python"].name, "runtime-python")
        self.assertEqual(kwargs["hunflair2_runtime_cache"].name, "runtime-cache")

    def test_composed_command_can_emit_graph_json(self):
        output = StringIO()
        with patch(
            "biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained",
            return_value=_FakePipeline(),
        ) as load, redirect_stdout(output):
            result = main(
                [
                    "--text",
                    "BRCA1",
                    "--output-format",
                    "graph",
                    "--document-id",
                    "paper-1",
                    "--max-retries",
                    "0",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(load.call_args.kwargs["entity_backend"], "hunflair2")
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["document"], {"id": "paper-1"})
        self.assertEqual(payload["nodes"][0]["id"], "doc_e_001")
        self.assertEqual(payload["edges"], [])


if __name__ == "__main__":
    unittest.main()
