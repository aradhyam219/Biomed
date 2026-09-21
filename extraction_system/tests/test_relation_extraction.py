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
                "assertion": "BRCA1 is associated with breast cancer.",
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
        self.assertEqual(result.relations[0].effects, ())
        self.assertEqual(result.relations[0].context, ())
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
                [{key: value for key, value in payload.items() if key != "assertion"}],
            )
        with self.assertRaisesRegex(RelationValidationError, "boolean"):
            validate_relations(
                TEXT,
                ENTITIES,
                [{**payload, "negated": "false"}],
            )

    def test_generic_semantic_shapes_are_grounded_without_a_finite_ontology(self):
        cases = (
            (
                "GeneA interacts with GeneB.",
                {
                    "predicate": "interacts with",
                    "assertion": "GeneA interacts with GeneB.",
                    "evidence": "GeneA interacts with GeneB",
                    "negated": False,
                },
            ),
            (
                "GeneA knockdown decreases GeneB expression in cells.",
                {
                    "predicate": "decreases expression of",
                    "assertion": "GeneA knockdown decreases GeneB expression in cells.",
                    "evidence": "GeneA knockdown decreases GeneB expression in cells",
                    "negated": False,
                    "intervention": "GeneA knockdown",
                    "effects": ["decreased GeneB expression"],
                    "context": ["cells"],
                },
            ),
            (
                "Drug X treatment reduced viability and migration of cells.",
                {
                    "predicate": "reduces",
                    "assertion": "Drug X treatment reduced viability and migration of cells.",
                    "evidence": "Drug X treatment reduced viability and migration of cells",
                    "negated": False,
                    "intervention": "Drug X treatment",
                    "effects": ["reduced viability", "reduced migration"],
                    "context": ["cells"],
                },
            ),
            (
                "GeneA associates with GeneB in liver tissue.",
                {
                    "predicate": "associates with",
                    "assertion": "GeneA associates with GeneB in liver tissue.",
                    "evidence": "GeneA associates with GeneB in liver tissue",
                    "negated": False,
                    "context": ["liver tissue"],
                },
            ),
            (
                "GeneA does not bind GeneB.",
                {
                    "predicate": "binds",
                    "assertion": "GeneA does not bind GeneB.",
                    "evidence": "GeneA does not bind GeneB",
                    "negated": True,
                },
            ),
            (
                "GeneB overexpression rescued the effect of GeneA knockdown.",
                {
                    "predicate": "rescues",
                    "assertion": "GeneB overexpression rescued the effect of GeneA knockdown.",
                    "evidence": "GeneB overexpression rescued the effect of GeneA knockdown",
                    "negated": False,
                    "intervention": "GeneB overexpression",
                    "effects": ["rescued the effect of GeneA knockdown"],
                },
            ),
        )

        for text, semantic_fields in cases:
            payload = {
                "source": "E1",
                "target": "E2",
                **semantic_fields,
            }
            result = validate_relations(text, ENTITIES, [payload])
            relation = result.relations[0]
            self.assertIsInstance(relation.effects, tuple)
            self.assertIsInstance(relation.context, tuple)
            self.assertEqual(relation.assertion, semantic_fields["assertion"])

    def test_validation_rejects_malformed_semantic_fields(self):
        payload = valid_payload()["relations"][0]

        invalid_values = (
            ("assertion", "", "assertion"),
            ("intervention", "", "intervention"),
            ("effects", [""], "effects"),
            ("context", ["valid", 3], "context"),
        )
        for field_name, value, message in invalid_values:
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(RelationValidationError, message):
                    validate_relations(
                        TEXT,
                        ENTITIES,
                        [{**payload, field_name: value}],
                    )

    def test_rich_fields_survive_structured_output_parser_validation_and_serialization(self):
        text = "GeneA knockdown reduced GeneB expression in hepatoma cells."
        payload = {
            "relations": [
                {
                    "source": "E1",
                    "target": "E2",
                    "predicate": "reduces expression of",
                    "assertion": "GeneA knockdown reduced GeneB expression in hepatoma cells.",
                    "intervention": "GeneA knockdown",
                    "effects": ["reduced GeneB expression"],
                    "context": ["hepatoma cells"],
                    "evidence": "GeneA knockdown reduced GeneB expression in hepatoma cells",
                    "negated": False,
                }
            ]
        }
        runnable = _FakeRunnable([payload])

        result = LLMRelationExtractor(runnable, max_retries=0).extract_relations(
            text, ENTITIES
        )

        relation = result.relations[0]
        self.assertEqual(relation.intervention, "GeneA knockdown")
        self.assertEqual(relation.effects, ("reduced GeneB expression",))
        self.assertEqual(relation.context, ("hepatoma cells",))
        serialized = result.to_dict()["relations"][0]
        self.assertEqual(serialized["assertion"], payload["relations"][0]["assertion"])
        self.assertEqual(serialized["effects"], ("reduced GeneB expression",))
        self.assertEqual(serialized["context"], ("hepatoma cells",))

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
        self.assertIn("graph-friendly normalized relationship", runnable.prompts[0])
        self.assertIn("complete source-grounded restatement", runnable.prompts[0])
        self.assertIn("material third participant", runnable.prompts[0])
        self.assertIn("Use context only for an explicit biological", runnable.prompts[0])
        self.assertIn("alternative names, abbreviations, aliases", runnable.prompts[0])
        self.assertIn("document-local entity assembly", runnable.prompts[0])
        self.assertNotIn("KNTC1", runnable.prompts[0])
        self.assertNotIn("CDK1", runnable.prompts[0])
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
                        "assertion": "BRCA1 is associated with breast cancer.",
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
        for field_name in ("assertion", "intervention", "effects", "context"):
            self.assertIn(field_name, relation_model.model_fields)
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
        self.assertTrue(captured["use_responses_api"])
        self.assertEqual(captured["reasoning"], {"effort": "max"})
        self.assertNotIn("reasoning_effort", captured)
        self.assertEqual(captured["max_completion_tokens"], 128000)
        self.assertNotIn("temperature", captured)
        self.assertNotIn("max_tokens", captured)

    def test_responses_payload_maps_compatibility_settings(self):
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model="gpt-5.6-luna",
            api_key="test-key",
            use_responses_api=True,
            reasoning={"effort": "max"},
            max_completion_tokens=128000,
        )

        payload = model._get_request_payload("Return a structured response.")

        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["reasoning"], {"effort": "max"})
        self.assertEqual(payload["max_output_tokens"], 128000)
        self.assertNotIn("max_completion_tokens", payload)
        self.assertNotIn("reasoning_effort", payload)
        self.assertIn("input", payload)
        self.assertNotIn("messages", payload)

    def test_environment_defaults_match_luna_live_smoke_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            config = OpenAIConfig.from_environment()

        self.assertEqual(config.reasoning_effort, "max")
        self.assertEqual(config.max_completion_tokens, 128000)

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
