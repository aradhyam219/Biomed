from __future__ import annotations

import json
import os
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

    def extract_graph(self, text, *, document_id, paper_title=""):
        entity = Entity("E1", text, "gene", 0, len(text), None)
        assembly = assemble_document_entities((entity,), text)
        return build_graph_result(document_id, assembly, ())


class LLMCLITests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)


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
        from biomedical_extractor import ExportContext, contract_resource
        from importlib.metadata import version
        context = ExportContext(version('biomedical-extractor'), 'a'*40, contract_resource('baseline-profile.json'))
        fake = _FakePipeline()
        output = StringIO()
        with patch("biomedical_extractor.llm_cli.release_context", return_value=context), \
             patch("biomedical_extractor.llm_cli.prepare_graph_export", return_value=context), \
             patch("biomedical_extractor.llm_cli.verify_graph_profile"), \
             patch.object(fake, "extract_graph", wraps=fake.extract_graph) as extract, \
             patch("biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained", return_value=fake), redirect_stdout(output):
            result = main(["--text", "BRCA1", "--output-format", "graph", "--document-id", "paper-1", "--paper-title", "Title"])
        self.assertEqual(result, 0)
        extract.assert_called_once_with("BRCA1", document_id="paper-1", paper_title="Title")
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["document"], {"id": "paper-1"})
        self.assertEqual(payload["nodes"][0]["id"], "doc_e_001")
        from biomedical_extractor import input_fingerprints
        self.assertEqual(payload["provenance"]["extraction_input_sha256"], input_fingerprints("BRCA1", "Title")["extraction_input_sha256"])

    def test_graph_upfront_errors_never_construct_provider(self):
        from biomedical_extractor import ExportContext, contract_resource, GraphValidationError
        from importlib.metadata import version
        context = ExportContext(version('biomedical-extractor'), 'a'*40, contract_resource('baseline-profile.json'))
        for options in (["--model", "other"], ["--max-retries", "0"], ["--hunflair2-model", "other"], ["--document-id", " "]):
            with patch("biomedical_extractor.llm_cli.release_context", return_value=context), \
                 patch("biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained") as load:
                with self.assertRaises(GraphValidationError):main(["--text", "BRCA1", "--output-format", "graph", *options])
                load.assert_not_called()
        with patch("biomedical_extractor.llm_cli.release_context", side_effect=GraphValidationError("missing revision")), \
             patch("biomedical_extractor.llm_cli.LLMExtractionPipeline.from_pretrained") as load:
            with self.assertRaises(GraphValidationError):main(["--text", "BRCA1", "--output-format", "graph"])
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
