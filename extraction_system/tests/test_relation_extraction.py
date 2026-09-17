from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from typing import get_args
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.llm_relation_extraction import (
    DEFAULT_LLM_RELATION_MODEL,
    LLMRelationExtractor,
    OpenAIConfig,
)
from biomedical_extractor.relation_extraction import (
    Relation,
    RelationExtractionError,
    RelationExtractionResult,
    RelationValidationError,
    validate_relations,
)


TEXT = "BRCA1 is associated with breast cancer."
ENTITIES = (
    Entity("E1", "BRCA1", "gene", 0, 5, None),
    Entity("E2", "breast cancer", "disease", 24, 37, None),
)


def valid_payload():
    return {
        "relations": [
            {
                "source": "E1",
                "target": "E2",
                "predicate": "association",
                "evidence": "BRCA1 is associated with breast cancer",
                "negated": False,
                "surface_form": "associated with",
            }
        ]
    }


class _FakeRunnable:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class _StructuredBindingModel:
    def __init__(self):
        self.schema = None
        self.bound = _FakeRunnable([])

    def invoke(self, prompt):
        raise AssertionError("The unbound model should not be invoked")

    def with_structured_output(self, schema):
        self.schema = schema
        return self.bound


class RelationContractTests(unittest.TestCase):
    def test_valid_relation_is_normalized_and_exact_duplicates_are_removed(self):
        payload = valid_payload()["relations"][0]

        result = validate_relations(
            TEXT,
            ENTITIES,
            [payload, payload],
            allowed_predicates=("association",),
        )

        self.assertEqual(result, RelationExtractionResult((Relation(**payload),)))
        self.assertEqual(result.to_dict()["relations"][0]["negated"], False)
        self.assertEqual(result.relations[0].source_entity_id, "E1")
        self.assertEqual(result.relations[0].type, "association")

    def test_validation_rejects_dangling_ids_and_unsupported_evidence(self):
        payload = valid_payload()["relations"][0]

        with self.assertRaisesRegex(RelationValidationError, "target entity ID"):
            validate_relations(
                TEXT,
                ENTITIES,
                [{**payload, "target": "E99"}],
                allowed_predicates=("association",),
            )
        with self.assertRaisesRegex(RelationValidationError, "evidence"):
            validate_relations(
                TEXT,
                ENTITIES,
                [{**payload, "evidence": "not in source"}],
                allowed_predicates=("association",),
            )

    def test_validation_rejects_missing_required_fields_and_non_boolean_negation(self):
        payload = valid_payload()["relations"][0]

        with self.assertRaisesRegex(RelationValidationError, "missing required"):
            validate_relations(
                TEXT,
                ENTITIES,
                [{key: value for key, value in payload.items() if key != "evidence"}],
            )
        with self.assertRaisesRegex(RelationValidationError, "boolean"):
            validate_relations(
                TEXT,
                ENTITIES,
                [{**payload, "negated": "false"}],
            )

    def test_llm_harness_builds_prompt_and_returns_local_contract(self):
        payload = valid_payload()
        payload["relations"][0]["predicate"] = "associated with"
        runnable = _FakeRunnable([payload])
        extractor = LLMRelationExtractor(
            runnable,
            max_retries=0,
        )

        result = extractor.extract_relations(TEXT, ENTITIES)

        self.assertIsInstance(result, RelationExtractionResult)
        self.assertEqual(result.relations[0].predicate, "associated with")
        self.assertIn("Do not add biological facts", runnable.prompts[0])
        self.assertIn("concise normalized predicate", runnable.prompts[0])
        self.assertNotIn("Allowed predicates", runnable.prompts[0])
        self.assertIn('"id": "E1"', runnable.prompts[0])
        self.assertIn(TEXT, runnable.prompts[0])

    def test_langchain_structured_binding_stays_inside_the_harness(self):
        model = _StructuredBindingModel()
        extractor = LLMRelationExtractor(
            model,
            max_retries=0,
        )
        model.bound.responses.append(
            model.schema(
                relations=[
                    {
                        "source": "E1",
                        "target": "E2",
                        "predicate": "associated with",
                        "evidence": "BRCA1 is associated with breast cancer",
                        "negated": False,
                    }
                ]
            )
        )

        result = extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(result.relations[0].source, "E1")
        self.assertIn("relations", model.schema.model_fields)
        relation_model = get_args(model.schema.model_fields["relations"].annotation)[0]
        self.assertNotIn("score", relation_model.model_fields)

    def test_llm_harness_repairs_malformed_output_with_bounded_retry(self):
        runnable = _FakeRunnable([{"wrong": []}, valid_payload()])
        extractor = LLMRelationExtractor(
            runnable,
            max_retries=1,
        )

        extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(len(runnable.prompts), 2)
        self.assertIn("REPAIR INSTRUCTION", runnable.prompts[1])

    def test_llm_harness_rejects_invalid_final_output_after_retry_budget(self):
        runnable = _FakeRunnable(
            [{"relations": [{"source": "E1", "target": "E2"}]}]
        )
        extractor = LLMRelationExtractor(
            runnable,
            max_retries=0,
        )

        with self.assertRaises(RelationExtractionError):
            extractor.extract_relations(TEXT, ENTITIES)

    def test_no_entities_do_not_trigger_a_model_request(self):
        runnable = _FakeRunnable([valid_payload()])
        extractor = LLMRelationExtractor(runnable, max_retries=0)

        result = extractor.extract_relations(TEXT, ())

        self.assertEqual(result.relations, ())
        self.assertEqual(runnable.prompts, [])

    def test_provider_failure_is_not_retried_as_output_repair(self):
        runnable = _FakeRunnable(
            [RuntimeError("network unavailable"), valid_payload()]
        )
        extractor = LLMRelationExtractor(runnable, max_retries=2)

        with self.assertRaisesRegex(
            RelationExtractionError, "provider invocation failed"
        ):
            extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(len(runnable.prompts), 1)

    def test_openai_defaults_use_luna_reasoning_without_sampling_parameters(self):
        captured = {}

        class _FakeChatOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def invoke(self, prompt):
                return {"relations": []}

        with patch.dict(
            sys.modules,
            {"langchain_openai": SimpleNamespace(ChatOpenAI=_FakeChatOpenAI)},
        ):
            LLMRelationExtractor.from_openai(OpenAIConfig(api_key="test-key"))

        self.assertEqual(OpenAIConfig().model, DEFAULT_LLM_RELATION_MODEL)
        self.assertEqual(captured["model"], "gpt-5.6-luna")
        self.assertEqual(captured["reasoning_effort"], "high")
        self.assertEqual(captured["max_completion_tokens"], 8192)
        self.assertNotIn("temperature", captured)
        self.assertNotIn("max_tokens", captured)

    def test_environment_defaults_match_luna_live_smoke_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            config = OpenAIConfig.from_environment()

        self.assertEqual(config.reasoning_effort, "high")
        self.assertEqual(config.max_completion_tokens, 8192)

    def test_environment_overrides_luna_reasoning_and_completion_budget(self):
        with patch.dict(
            os.environ,
            {
                "BIOMEDICAL_RELATION_REASONING_EFFORT": "xhigh",
                "BIOMEDICAL_RELATION_MAX_COMPLETION_TOKENS": "2048",
            },
        ):
            config = OpenAIConfig.from_environment()

        self.assertEqual(config.reasoning_effort, "xhigh")
        self.assertEqual(config.max_completion_tokens, 2048)


if __name__ == "__main__":
    unittest.main()
