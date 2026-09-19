from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

from biomedical_extractor.biored import BioREDDataset, BioREDDocument
from biomedical_extractor.hunflair2 import (
    HUNFLAIR2_LABEL_TO_CANONICAL,
    HUNFLAIR2_SUPPORTED_CANONICAL_TYPES,
    HunFlair2BioMedExtractor,
    HunFlair2IsolatedRuntime,
    HunFlair2PredictionRuntime,
    normalize_hunflair2_predictions,
)
from biomedical_extractor.hunflair2_evaluation_cli import (
    FROZEN_BIORED_TEST_SHA256,
    _validate_dataset_identity,
)
from biomedical_extractor.hunflair2_runtime import _prediction_for_span
from biomedical_extractor.ner_runners import RunnerOutput


class _FakeRuntime:
    def __init__(self, predictions):
        self.predictions = predictions

    def predict_entities(self, text):
        return self.predictions


class _FakeLabel:
    def __init__(self, value, score):
        self.value = value
        self.score = score


class _FakeSpan:
    def __init__(self, text, start, end, label="Gene", score=0.73):
        self.text = text
        self.start_position = start
        self.end_position = end
        self._label = _FakeLabel(label, score)

    def get_label(self, label_type):
        self.asserted_label_type = label_type
        return self._label


class _FakeSentence:
    def __init__(self, text, start_position):
        self.text = text
        self.start_position = start_position


class HunFlair2AdapterTests(unittest.TestCase):
    def test_official_label_mapping_covers_exactly_five_shared_classes(self):
        self.assertEqual(
            HUNFLAIR2_LABEL_TO_CANONICAL,
            {
                "Gene": "GeneOrGeneProduct",
                "Chemical": "ChemicalEntity",
                "Disease": "DiseaseOrPhenotypicFeature",
                "Species": "OrganismTaxon",
                "CellLine": "CellLine",
            },
        )
        self.assertNotIn("SequenceVariant", HUNFLAIR2_SUPPORTED_CANONICAL_TYPES)

    def test_flair_like_span_preserves_document_offset_and_score(self):
        text = "α BRCA1"
        entity = normalize_hunflair2_predictions(
            text,
            (_FakeSpan("BRCA1", 2, 7, "Gene", 0.731),),
        )[0]

        self.assertEqual(entity.text, "BRCA1")
        self.assertEqual(entity.type, "Gene")
        self.assertEqual((entity.start, entity.end), (2, 7))
        self.assertEqual(entity.score, 0.731)
        self.assertEqual(text[entity.start : entity.end], entity.text)

    def test_mapping_score_and_unicode_source_are_preserved(self):
        text = "β disease"
        entity = normalize_hunflair2_predictions(
            text,
            ({"start": 2, "end": 9, "text": "disease", "label": "Disease", "score": 0.4},),
        )[0]
        self.assertEqual(entity.text, "disease")
        self.assertEqual(entity.score, 0.4)

    def test_sentence_relative_offset_is_lifted_to_document_coordinates(self):
        sentence = _FakeSentence("BRCA1", 7)
        prediction = _prediction_for_span(
            sentence,
            _FakeSpan("BRCA1", 0, 5),
            "ner",
            "Title. BRCA1",
        )
        self.assertEqual(prediction["start"], 7)
        self.assertEqual(prediction["end"], 12)
        self.assertEqual(prediction["text"], "BRCA1")

    def test_invalid_span_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid HunFlair2 entity character span"):
            normalize_hunflair2_predictions("BRCA1", [(0, 99, "Gene")])

    def test_source_text_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            normalize_hunflair2_predictions(
                "BRCA1", [{"start": 0, "end": 5, "text": "BRCA", "label": "Gene"}]
            )

    def test_unsupported_variant_prediction_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported HunFlair2 entity label"):
            normalize_hunflair2_predictions("rs123", [(0, 5, "Variant")])

    def test_runtime_cache_is_keyed_by_exact_source_text(self):
        extractor = HunFlair2BioMedExtractor(
            HunFlair2PredictionRuntime(
                {"9e5e6a8b5f5a5a5a": ()}
            )
        )
        with self.assertRaisesRegex(ValueError, "no entry"):
            extractor.extract_entities("source")

    def test_pretrained_factory_binds_the_isolated_runtime_configuration(self):
        with mock.patch(
            "biomedical_extractor.hunflair2.HunFlair2IsolatedRuntime"
        ) as runtime:
            extractor = HunFlair2BioMedExtractor.from_pretrained(
                "hunflair/hunflair2-ner",
                runtime_python=Path("runtime-python"),
                runtime_script=Path("runtime-script.py"),
                runtime_cache=Path("runtime-cache"),
                device="cuda",
                offline=True,
            )

        self.assertIsInstance(extractor, HunFlair2BioMedExtractor)
        runtime.assert_called_once_with(
            model_identifier="hunflair/hunflair2-ner",
            runtime_python=Path("runtime-python"),
            runtime_script=Path("runtime-script.py"),
            runtime_cache=Path("runtime-cache"),
            device="cuda",
            offline=True,
        )

    def test_isolated_runtime_delegates_to_the_shared_runner(self):
        runtime = HunFlair2IsolatedRuntime(
            runtime_python=Path("runtime-python"),
            runtime_script=Path("runtime-script.py"),
            runtime_cache=Path("runtime-cache"),
            device="cpu",
        )
        runner_output = RunnerOutput(
            model="HunFlair2",
            prediction_path=Path("predictions.json"),
            metadata={},
            records={
                "single-document": (
                    {"start": 0, "end": 5, "text": "BRCA1", "label": "Gene"},
                )
            },
        )
        with mock.patch(
            "biomedical_extractor.ner_runners.run_hunflair2",
            return_value=runner_output,
        ) as run:
            predictions = runtime.predict_entities("BRCA1")

        self.assertEqual(predictions, runner_output.records["single-document"])
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["python_path"], Path("runtime-python"))
        self.assertEqual(kwargs["runtime_script"], Path("runtime-script.py"))
        self.assertEqual(kwargs["runtime_cache"], Path("runtime-cache"))
        self.assertEqual(kwargs["device"], "cpu")
        self.assertEqual(kwargs["model_identifier"], "hunflair/hunflair2-ner")
        self.assertEqual(
            run.call_args.args[0],
            ({"id": "single-document", "text": "BRCA1"},),
        )

    def test_evaluation_runtime_module_does_not_load_flair_at_import(self):
        self.assertNotIn("flair", sys.modules)

    def test_frozen_dataset_identity_requires_test_hash_and_document_count(self):
        dataset = BioREDDataset(
            path=Path("Test.BioC.JSON"),
            split="test",
            sha256=FROZEN_BIORED_TEST_SHA256,
            source="BioC",
            date="date",
            key="key",
            documents=tuple(
                BioREDDocument(str(index), "", (), ()) for index in range(100)
            ),
        )
        _validate_dataset_identity(dataset)
        bad_hash = BioREDDataset(
            path=dataset.path,
            split=dataset.split,
            sha256="different",
            source=dataset.source,
            date=dataset.date,
            key=dataset.key,
            documents=dataset.documents,
        )
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            _validate_dataset_identity(bad_hash)


if __name__ == "__main__":
    unittest.main()
