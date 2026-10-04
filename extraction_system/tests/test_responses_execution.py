from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.llm_relation_extraction import (
    DEFAULT_LLM_MAX_COMPLETION_TOKENS,
    DEFAULT_LLM_RELATION_MODEL,
    DEFAULT_LLM_REASONING_EFFORT,
    LLMRelationExtractor,
    OpenAIConfig,
    RELATION_EXTRACTION_SYSTEM_PROMPT,
    _build_prompt,
    _parse_structured_response,
    _structured_payload_schema,
)
from biomedical_extractor.relation_extraction import (
    RelationExtractionError,
    RelationValidationError,
    validate_relations,
)
from biomedical_extractor import responses_execution
from biomedical_extractor.responses_execution import (
    MAX_CONSECUTIVE_POLL_ERRORS,
    ResponsesBackgroundExecutor,
    ResponsesExecutionError,
    strict_transport_schema,
    verify_transport_equivalence,
)


TEXT = "BRCA1 is associated with breast cancer."
ENTITIES = (
    Entity("E1", "BRCA1", "gene", 0, 5, None),
    Entity("E2", "breast cancer", "disease", 24, 37, None),
)
RELATION = {
    "source": "E1",
    "target": "E2",
    "predicate": "association",
    "assertion": "BRCA1 is associated with breast cancer.",
    "evidence": "BRCA1 is associated with breast cancer",
    "negated": False,
    "surface_form": "associated with",
}
SCHEMA = _structured_payload_schema()
API_KEY = "local-test-key-that-must-not-escape"
BASE_URL = "https://private.example.test/v1"


def _response(
    response_id: str = "resp_test_001",
    status: str = "completed",
    output_text: str | None = '{"relations": []}',
    *,
    model: str | None = "gpt-6.1-sol",
    effort: str | None = "medium",
    service_tier: str | None = "default",
    background: bool | None = True,
    usage: tuple[int, int, int] | None = (120, 50, 12),
    error: Any = None,
    incomplete_reason: str | None = None,
) -> SimpleNamespace:
    input_tokens, output_tokens, reasoning_tokens = usage or (None, None, None)
    usage_value = (
        None
        if usage is None
        else SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens),
        )
    )
    return SimpleNamespace(
        id=response_id,
        status=status,
        output_text=output_text,
        model=model,
        reasoning=SimpleNamespace(effort=effort) if effort is not None else None,
        service_tier=service_tier,
        background=background,
        usage=usage_value,
        error=error,
        incomplete_details=(
            SimpleNamespace(reason=incomplete_reason)
            if incomplete_reason is not None
            else None
        ),
    )


class _FakeResponses:
    def __init__(self, create_results=(), retrieve_results=(), cancel_result=None):
        self.create_results = list(create_results)
        self.retrieve_results = list(retrieve_results)
        self.cancel_result = cancel_result
        self.create_calls: list[dict[str, Any]] = []
        self.retrieve_calls: list[tuple[str, float]] = []
        self.cancel_calls: list[tuple[str, float]] = []
        self.after_retrieve = None

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        result = self.create_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def retrieve(self, response_id, *, timeout):
        self.retrieve_calls.append((response_id, timeout))
        result = self.retrieve_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        if self.after_retrieve is not None:
            self.after_retrieve()
        return result

    def cancel(self, response_id, *, timeout):
        self.cancel_calls.append((response_id, timeout))
        return self.cancel_result or _response(response_id, "cancelled", None)


class _FakeClient:
    def __init__(self, responses: _FakeResponses):
        self.responses = responses


class _FakeOpenAI:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.responses = _FakeResponses(
            [_response(output_text=json.dumps({"relations": [RELATION]}))]
        )
        type(self).instances.append(self)


class _FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds

    def advance(self, seconds):
        self.value += seconds


def _executor(
    client: _FakeClient,
    *,
    poll_interval_seconds: float = 3.0,
    generation_timeout_seconds: float = 900.0,
    diagnostics_callback=None,
    model: str = "gpt-6.1-sol",
    reasoning_effort: str = "medium",
    service_tier: str | None = "default",
) -> ResponsesBackgroundExecutor:
    return ResponsesBackgroundExecutor(
        client,
        model=model,
        reasoning_effort=reasoning_effort,
        max_output_tokens=128000,
        service_tier=service_tier,
        poll_interval_seconds=poll_interval_seconds,
        generation_timeout_seconds=generation_timeout_seconds,
        schema=SCHEMA,
        diagnostics_callback=diagnostics_callback,
        redaction_values=(API_KEY, BASE_URL),
    )


class OpenAIConfigTests(unittest.TestCase):
    def test_defaults_preserve_the_existing_foreground_candidate(self):
        config = OpenAIConfig(api_key=API_KEY, base_url=BASE_URL)

        self.assertEqual(config.model, DEFAULT_LLM_RELATION_MODEL)
        self.assertEqual(config.reasoning_effort, DEFAULT_LLM_REASONING_EFFORT)
        self.assertEqual(config.max_completion_tokens, DEFAULT_LLM_MAX_COMPLETION_TOKENS)
        self.assertEqual(config.max_retries, 2)
        self.assertFalse(config.background)
        self.assertIsNone(config.service_tier)
        self.assertEqual(config.poll_interval_seconds, 3.0)
        self.assertEqual(config.generation_timeout_seconds, 900.0)
        self.assertNotIn(API_KEY, repr(config))
        self.assertNotIn(BASE_URL, repr(config))

    def test_environment_can_explicitly_select_sol_medium_standard_background(self):
        values = {
            "OPENAI_API_KEY": API_KEY,
            "BIOMEDICAL_RELATION_MODEL": "gpt-6.1-sol",
            "BIOMEDICAL_RELATION_REASONING_EFFORT": "medium",
            "BIOMEDICAL_RELATION_BACKGROUND": "true",
            "BIOMEDICAL_RELATION_SERVICE_TIER": "default",
            "BIOMEDICAL_RELATION_POLL_INTERVAL_SECONDS": "4.5",
            "BIOMEDICAL_RELATION_TIMEOUT_SECONDS": "720",
        }
        with patch.dict(os.environ, values, clear=True):
            config = OpenAIConfig.from_environment()

        self.assertEqual(config.model, "gpt-6.1-sol")
        self.assertEqual(config.reasoning_effort, "medium")
        self.assertTrue(config.background)
        self.assertEqual(config.service_tier, "default")
        self.assertEqual(config.poll_interval_seconds, 4.5)
        self.assertEqual(config.generation_timeout_seconds, 720.0)
        self.assertEqual(config.max_retries, 2)
        self.assertEqual(config.max_completion_tokens, DEFAULT_LLM_MAX_COMPLETION_TOKENS)

    def test_configuration_rejects_invalid_execution_controls(self):
        invalid = (
            {"background": "true"},
            {"service_tier": "standard"},
            {"poll_interval_seconds": 0},
            {"poll_interval_seconds": float("inf")},
            {"generation_timeout_seconds": -1},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                OpenAIConfig(**values)

    def test_environment_rejects_ambiguous_background_setting(self):
        with patch.dict(os.environ, {"BIOMEDICAL_RELATION_BACKGROUND": "sometimes"}, clear=True):
            with self.assertRaisesRegex(ValueError, "must be true or false"):
                OpenAIConfig.from_environment()


class StrictTransportTests(unittest.TestCase):
    def test_public_sdk_strict_transport_preserves_semantic_schema(self):
        semantic = SCHEMA.model_json_schema()
        transport = strict_transport_schema(SCHEMA)
        verify_transport_equivalence(semantic, transport)
        canonical = json.dumps(
            transport, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self.assertEqual(
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510",
        )
        self.assertEqual(
            set(transport["required"]), set(transport["properties"])
        )
        self.assertIs(transport["additionalProperties"], False)
        properties = transport["$defs"]["StructuredRelation"]["properties"]
        for name in ("intervention", "surface_form"):
            self.assertEqual(
                {part["type"] for part in properties[name]["anyOf"]},
                {"string", "null"},
            )
        for name in ("effects", "context"):
            self.assertEqual(properties[name]["type"], "array")
            self.assertEqual(properties[name]["items"]["type"], "string")

    def test_empty_null_and_rich_payloads_keep_existing_semantics(self):
        empty = validate_relations(TEXT, ENTITIES, _parse_structured_response('{"relations": []}'))
        self.assertEqual(empty.to_dict(), {"relations": []})

        full = dict(
            RELATION,
            intervention=None,
            effects=[],
            context=[],
        )
        omitted = dict(RELATION)
        with_values = validate_relations(
            TEXT, ENTITIES, _parse_structured_response(json.dumps({"relations": [full]}))
        )
        without_values = validate_relations(
            TEXT, ENTITIES, _parse_structured_response({"relations": [omitted]})
        )
        self.assertEqual(with_values, without_values)
        self.assertEqual(with_values.relations[0].effects, ())
        self.assertEqual(with_values.relations[0].context, ())

        with self.assertRaises(RelationValidationError):
            validate_relations(
                TEXT,
                ENTITIES,
                _parse_structured_response(
                    {"relations": [{**RELATION, "unapproved": "value"}]}
                ),
            )


class BackgroundLifecycleTests(unittest.TestCase):
    def test_submission_without_response_id_fails_without_poll_cancel_or_resubmit(self):
        responses = _FakeResponses(
            [_response(response_id="", status="queued", output_text=None)]
        )
        executor = _executor(_FakeClient(responses))

        with self.assertRaises(ResponsesExecutionError) as raised:
            executor.execute("prompt", {"generation_number": 1, "repair": False})

        self.assertEqual(raised.exception.diagnostics["status"], "missing_response_id")
        self.assertIsNone(raised.exception.diagnostics["response_id"])
        self.assertEqual(len(responses.create_calls), 1)
        self.assertEqual(len(responses.retrieve_calls), 0)
        self.assertEqual(len(responses.cancel_calls), 0)

    def test_submission_polls_through_queued_and_in_progress_to_completion(self):
        responses = _FakeResponses(
            [_response(status="queued", output_text=None)],
            [
                _response(status="in_progress", output_text=None),
                _response(status="completed", output_text='{"relations": []}'),
            ],
        )
        client = _FakeClient(responses)
        snapshots = []
        executor = _executor(client, diagnostics_callback=snapshots.append)
        clock = _FakeClock()
        with patch.object(responses_execution.time, "monotonic", side_effect=clock.monotonic), patch.object(
            responses_execution.time, "sleep", side_effect=clock.sleep
        ):
            diagnostics = {"generation_number": 1, "repair": False}
            output = executor.execute("fixed prompt", diagnostics)

        self.assertEqual(output, '{"relations": []}')
        self.assertEqual(len(responses.create_calls), 1)
        self.assertEqual(len(responses.retrieve_calls), 2)
        self.assertTrue(all(call[0] == "resp_test_001" for call in responses.retrieve_calls))
        self.assertEqual([call[1] for call in responses.retrieve_calls], [60.0, 60.0])
        request = responses.create_calls[0]
        self.assertEqual(request["model"], "gpt-6.1-sol")
        self.assertEqual(request["reasoning"], {"effort": "medium"})
        self.assertEqual(request["service_tier"], "default")
        self.assertTrue(request["background"])
        self.assertFalse(request["store"])
        self.assertEqual(request["max_output_tokens"], 128000)
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertLessEqual(request["timeout"], 900)
        self.assertEqual(diagnostics["status"], "completed")
        self.assertEqual(diagnostics["response_id"], "resp_test_001")
        self.assertEqual(diagnostics["input_tokens"], 120)
        self.assertEqual(diagnostics["output_tokens"], 50)
        self.assertEqual(diagnostics["reasoning_tokens"], 12)
        self.assertEqual(diagnostics["observed_model"], "gpt-6.1-sol")
        self.assertEqual(diagnostics["observed_reasoning_effort"], "medium")
        self.assertEqual(diagnostics["observed_service_tier"], "default")
        self.assertIs(diagnostics["observed_background"], True)
        self.assertEqual(len(snapshots), 5)
        snapshots[0]["requested_model"] = "mutated"
        self.assertEqual(diagnostics["requested_model"], "gpt-6.1-sol")

    def test_transient_poll_failure_retries_same_response_without_resubmitting(self):
        class APIConnectionError(Exception):
            pass

        poll_error = APIConnectionError(
            f"Authorization: Bearer {API_KEY}; service={BASE_URL}"
        )
        responses = _FakeResponses(
            [_response(status="queued", output_text=None)],
            [poll_error, _response(status="completed", output_text='{"relations": []}')],
        )
        client = _FakeClient(responses)
        executor = _executor(client)
        clock = _FakeClock()
        with patch.object(responses_execution.time, "monotonic", side_effect=clock.monotonic), patch.object(
            responses_execution.time, "sleep", side_effect=clock.sleep
        ):
            diagnostics = {"generation_number": 1, "repair": False}
            self.assertEqual(executor.execute("prompt", diagnostics), '{"relations": []}')

        self.assertEqual(len(responses.create_calls), 1)
        self.assertEqual(len(responses.retrieve_calls), 2)
        self.assertEqual(diagnostics["poll_errors"], 1)
        self.assertEqual(diagnostics["last_poll_error_type"], "APIConnectionError")
        self.assertNotIn("error_type", diagnostics)
        self.assertNotIn(API_KEY, json.dumps(diagnostics))
        self.assertNotIn(BASE_URL, json.dumps(diagnostics))

    def test_failed_cancelled_and_incomplete_terminal_states_are_controlled(self):
        cases = (
            ("failed", "provider_failed", None, "server_error"),
            ("cancelled", "provider_cancelled", None, None),
            ("incomplete", "provider_incomplete", "max_output_tokens", None),
        )
        for status, expected, incomplete_reason, _unused in cases:
            with self.subTest(status=status):
                error = SimpleNamespace(
                    type="server_error",
                    code="server_error",
                    message=f"secret={API_KEY} url={BASE_URL}",
                ) if status == "failed" else None
                responses = _FakeResponses(
                    [
                        _response(
                            status=status,
                            output_text=None,
                            error=error,
                            incomplete_reason=incomplete_reason,
                        )
                    ]
                )
                executor = _executor(_FakeClient(responses))
                diagnostics = {"generation_number": 1, "repair": False}
                with self.assertRaises(ResponsesExecutionError) as raised:
                    executor.execute("prompt", diagnostics)

                self.assertEqual(raised.exception.diagnostics["status"], expected)
                self.assertEqual(
                    raised.exception.diagnostics["terminal_status"], status
                )
                self.assertEqual(len(responses.create_calls), 1)
                self.assertEqual(len(responses.retrieve_calls), 0)
                self.assertEqual(len(responses.cancel_calls), 0)
                self.assertNotIn(API_KEY, str(raised.exception))
                self.assertNotIn(BASE_URL, json.dumps(raised.exception.diagnostics))
                if incomplete_reason:
                    self.assertEqual(
                        raised.exception.diagnostics["incomplete_reason"],
                        incomplete_reason,
                    )

    def test_timeout_uses_remaining_request_budget_and_cancels_active_response(self):
        responses = _FakeResponses(
            [_response(status="queued", output_text=None)],
            [_response(status="queued", output_text=None)],
        )
        client = _FakeClient(responses)
        executor = _executor(
            client,
            poll_interval_seconds=3,
            generation_timeout_seconds=4,
        )
        clock = _FakeClock()
        with patch.object(responses_execution.time, "monotonic", side_effect=clock.monotonic), patch.object(
            responses_execution.time, "sleep", side_effect=clock.sleep
        ):
            with self.assertRaises(ResponsesExecutionError) as raised:
                executor.execute("prompt", {"generation_number": 1, "repair": False})

        diagnostics = raised.exception.diagnostics
        self.assertEqual(diagnostics["status"], "timeout")
        self.assertTrue(diagnostics["cancel_attempted"])
        self.assertEqual(diagnostics["cancel_status"], "cancelled")
        self.assertEqual(responses.create_calls[0]["timeout"], 4.0)
        self.assertEqual(responses.retrieve_calls[0][1], 1.0)
        self.assertEqual(responses.cancel_calls, [("resp_test_001", 5.0)])
        self.assertEqual(len(responses.create_calls), 1)

    def test_terminal_result_returned_after_deadline_remains_a_timeout(self):
        responses = _FakeResponses(
            [_response(status="queued", output_text=None)],
            [_response(status="completed", output_text='{"relations": []}')],
        )
        client = _FakeClient(responses)
        clock = _FakeClock()
        responses.after_retrieve = lambda: clock.advance(5)
        executor = _executor(
            client, poll_interval_seconds=1, generation_timeout_seconds=4
        )
        with patch.object(responses_execution.time, "monotonic", side_effect=clock.monotonic), patch.object(
            responses_execution.time, "sleep", side_effect=clock.sleep
        ):
            with self.assertRaisesRegex(ResponsesExecutionError, "timed out") as raised:
                executor.execute("prompt", {"generation_number": 1, "repair": False})

        self.assertEqual(raised.exception.diagnostics["terminal_status"], "completed")
        self.assertFalse(raised.exception.diagnostics.get("cancel_attempted", False))
        self.assertEqual(len(responses.cancel_calls), 0)

    def test_repeated_transient_poll_errors_cancel_after_finite_limit(self):
        class APIConnectionError(Exception):
            pass

        responses = _FakeResponses(
            [_response(status="in_progress", output_text=None)],
            [APIConnectionError("temporary") for _ in range(MAX_CONSECUTIVE_POLL_ERRORS)],
        )
        client = _FakeClient(responses)
        executor = _executor(client, poll_interval_seconds=1)
        clock = _FakeClock()
        with patch.object(responses_execution.time, "monotonic", side_effect=clock.monotonic), patch.object(
            responses_execution.time, "sleep", side_effect=clock.sleep
        ):
            with self.assertRaises(ResponsesExecutionError) as raised:
                executor.execute("prompt", {"generation_number": 1, "repair": False})

        self.assertEqual(raised.exception.diagnostics["status"], "polling_failed")
        self.assertEqual(raised.exception.diagnostics["poll_errors"], MAX_CONSECUTIVE_POLL_ERRORS)
        self.assertEqual(len(responses.create_calls), 1)
        self.assertEqual(len(responses.retrieve_calls), MAX_CONSECUTIVE_POLL_ERRORS)
        self.assertEqual(len(responses.cancel_calls), 1)

    def test_permanent_poll_failure_cancels_without_retrying_the_generation(self):
        class APIStatusError(Exception):
            status_code = 400

        responses = _FakeResponses(
            [_response(status="queued", output_text=None)],
            [APIStatusError(f"failed at {BASE_URL} with {API_KEY}")],
        )
        executor = _executor(_FakeClient(responses))
        with self.assertRaises(ResponsesExecutionError) as raised:
            executor.execute("prompt", {"generation_number": 1, "repair": False})

        self.assertEqual(raised.exception.diagnostics["status"], "polling_failed")
        self.assertEqual(raised.exception.diagnostics["last_poll_http_status"], 400)
        self.assertEqual(len(responses.create_calls), 1)
        self.assertEqual(len(responses.retrieve_calls), 1)
        self.assertEqual(len(responses.cancel_calls), 1)
        self.assertNotIn(API_KEY, str(raised.exception))
        self.assertNotIn(BASE_URL, json.dumps(raised.exception.diagnostics))

    def test_interruption_and_callback_failure_cancel_a_known_active_response(self):
        responses = _FakeResponses([_response(status="queued", output_text=None)])
        executor = _executor(_FakeClient(responses))
        with patch.object(responses_execution.time, "sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(ResponsesExecutionError) as interrupted:
                executor.execute("prompt", {"generation_number": 1, "repair": False})
        self.assertEqual(interrupted.exception.diagnostics["status"], "interrupted")
        self.assertEqual(len(responses.cancel_calls), 1)

        responses = _FakeResponses([_response(status="queued", output_text=None)])

        def fail_after_submit(snapshot):
            if snapshot.get("status") == "queued":
                raise RuntimeError(f"secret {API_KEY} from {BASE_URL}")

        executor = _executor(
            _FakeClient(responses), diagnostics_callback=fail_after_submit
        )
        with self.assertRaisesRegex(ResponsesExecutionError, "callback failed") as callback_error:
            executor.execute("prompt", {"generation_number": 1, "repair": False})
        self.assertEqual(
            callback_error.exception.diagnostics["status"],
            "diagnostics_callback_failed",
        )
        self.assertTrue(callback_error.exception.diagnostics["cancel_attempted"])
        self.assertEqual(len(responses.cancel_calls), 1)
        self.assertNotIn(API_KEY, str(callback_error.exception))
        self.assertNotIn(BASE_URL, json.dumps(callback_error.exception.diagnostics))

    def test_polling_rejects_a_changed_response_id_and_cancels_original(self):
        responses = _FakeResponses(
            [_response("resp_original", "queued", None)],
            [_response("resp_other", "completed", '{"relations": []}')],
        )
        executor = _executor(_FakeClient(responses))
        with self.assertRaisesRegex(ResponsesExecutionError, "different response ID") as raised:
            executor.execute("prompt", {"generation_number": 1, "repair": False})

        self.assertEqual(raised.exception.diagnostics["response_id"], "resp_original")
        self.assertEqual(responses.cancel_calls[0][0], "resp_original")


class ProductionBoundaryTests(unittest.TestCase):
    def setUp(self):
        _FakeOpenAI.instances.clear()

    def test_candidate_config_reaches_production_responses_boundary(self):
        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key=API_KEY,
            base_url=BASE_URL,
            reasoning_effort="medium",
            background=True,
            service_tier="default",
            max_retries=2,
        )
        snapshots = []
        with patch("openai.OpenAI", _FakeOpenAI):
            extractor = LLMRelationExtractor.from_openai(
                config, diagnostics_callback=snapshots.append
            )
            result = extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(len(result.relations), 1)
        client = _FakeOpenAI.instances[-1]
        self.assertEqual(client.kwargs["api_key"], API_KEY)
        self.assertEqual(client.kwargs["base_url"], BASE_URL)
        self.assertEqual(client.kwargs["max_retries"], 0)
        self.assertEqual(client.kwargs["timeout"], 60.0)
        request = client.responses.create_calls[0]
        self.assertEqual(request["input"], _build_prompt(TEXT, ENTITIES, RELATION_EXTRACTION_SYSTEM_PROMPT))
        self.assertEqual(request["model"], "gpt-6.1-sol")
        self.assertEqual(request["reasoning"], {"effort": "medium"})
        self.assertEqual(request["service_tier"], "default")
        self.assertEqual(request["max_output_tokens"], 128000)
        self.assertTrue(request["background"])
        self.assertFalse(request["store"])
        self.assertTrue(request["text"]["format"]["strict"])

        diagnostics = extractor.last_generation_diagnostics
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["generation_number"], 1)
        self.assertFalse(diagnostics[0]["repair"])
        self.assertEqual(diagnostics[0]["requested_model"], "gpt-6.1-sol")
        self.assertEqual(diagnostics[0]["observed_reasoning_effort"], "medium")
        self.assertEqual(diagnostics[0]["observed_service_tier"], "default")
        self.assertIs(diagnostics[0]["observed_background"], True)
        serialized = json.dumps(diagnostics)
        self.assertNotIn(API_KEY, serialized)
        self.assertNotIn(BASE_URL, serialized)
        snapshots[0]["requested_model"] = "changed copy"
        self.assertEqual(
            extractor.last_generation_diagnostics[0]["requested_model"],
            "gpt-6.1-sol",
        )

    def test_background_repairs_are_bounded_and_empty_input_is_a_fast_path(self):
        invalid = {"relations": [{**RELATION, "evidence": "not in source"}]}
        client = _FakeOpenAI()
        client.responses = _FakeResponses(
            [
                _response("resp_first", output_text=json.dumps(invalid)),
                _response("resp_second", output_text=json.dumps({"relations": [RELATION]})),
            ]
        )
        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key=API_KEY,
            reasoning_effort="medium",
            background=True,
            service_tier="default",
            max_retries=1,
        )
        with patch("openai.OpenAI", return_value=client):
            extractor = LLMRelationExtractor.from_openai(config)
            result = extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(len(result.relations), 1)
        self.assertEqual(len(client.responses.create_calls), 2)
        repair_prompt = client.responses.create_calls[1]["input"]
        self.assertIn(
            "REPAIR INSTRUCTION:\nThe previous response failed validation: "
            "Relation evidence must occur verbatim in the supplied source text. "
            "Return a corrected structured response only.",
            repair_prompt,
        )
        diagnostics = extractor.last_generation_diagnostics
        self.assertEqual([item["repair"] for item in diagnostics], [False, True])
        self.assertEqual([item["generation_number"] for item in diagnostics], [1, 2])
        self.assertEqual(
            [item["status"] for item in diagnostics], ["output_invalid", "success"]
        )

        empty = extractor.extract_relations("", ENTITIES)
        self.assertEqual(empty.to_dict(), {"relations": []})
        self.assertEqual(extractor.last_generation_diagnostics, ())
        self.assertEqual(len(client.responses.create_calls), 2)

    def test_background_repair_exhaustion_stops_at_the_configured_attempt_limit(self):
        invalid = {"relations": [{**RELATION, "evidence": "not in source"}]}
        client = _FakeOpenAI()
        client.responses = _FakeResponses(
            [
                _response("resp_invalid_1", output_text=json.dumps(invalid)),
                _response("resp_invalid_2", output_text=json.dumps(invalid)),
            ]
        )
        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key=API_KEY,
            reasoning_effort="medium",
            background=True,
            service_tier="default",
            max_retries=1,
        )
        with patch("openai.OpenAI", return_value=client):
            extractor = LLMRelationExtractor.from_openai(config)
            with self.assertRaisesRegex(
                RelationExtractionError, "remained invalid after 2 bounded attempt\\(s\\)"
            ):
                extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(len(client.responses.create_calls), 2)
        diagnostics = extractor.last_generation_diagnostics
        self.assertEqual([item["generation_number"] for item in diagnostics], [1, 2])
        self.assertEqual([item["repair"] for item in diagnostics], [False, True])
        self.assertEqual([item["status"] for item in diagnostics], ["output_invalid"] * 2)

    def test_background_terminal_provider_states_never_enter_output_repair(self):
        cases = (
            ("failed", SimpleNamespace(type="server_error", code="server_error", message="hidden"), None),
            ("cancelled", None, None),
            ("incomplete", None, "max_output_tokens"),
        )
        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key=API_KEY,
            reasoning_effort="medium",
            background=True,
            service_tier="default",
            max_retries=2,
        )
        for status, error, incomplete_reason in cases:
            with self.subTest(status=status):
                client = _FakeOpenAI()
                client.responses = _FakeResponses(
                    [
                        _response(
                            f"resp_{status}",
                            status,
                            None,
                            error=error,
                            incomplete_reason=incomplete_reason,
                        )
                    ]
                )
                with patch("openai.OpenAI", return_value=client):
                    extractor = LLMRelationExtractor.from_openai(config)
                    with self.assertRaisesRegex(
                        RelationExtractionError, "provider invocation failed"
                    ):
                        extractor.extract_relations(TEXT, ENTITIES)

                self.assertEqual(len(client.responses.create_calls), 1)
                diagnostics = extractor.last_generation_diagnostics
                self.assertEqual(len(diagnostics), 1)
                self.assertFalse(diagnostics[0]["repair"])
                self.assertEqual(diagnostics[0]["terminal_status"], status)
                self.assertEqual(diagnostics[0]["status"], f"provider_{status}")

    def test_completed_response_without_text_uses_the_bounded_output_repair(self):
        client = _FakeOpenAI()
        client.responses = _FakeResponses(
            [
                _response("resp_empty", output_text=None),
                _response("resp_repaired", output_text=json.dumps({"relations": []})),
            ]
        )
        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key=API_KEY,
            reasoning_effort="medium",
            background=True,
            service_tier="default",
            max_retries=1,
        )
        with patch("openai.OpenAI", return_value=client):
            extractor = LLMRelationExtractor.from_openai(config)
            result = extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(result.to_dict(), {"relations": []})
        self.assertEqual(len(client.responses.create_calls), 2)
        self.assertIn("REPAIR INSTRUCTION:", client.responses.create_calls[1]["input"])
        diagnostics = extractor.last_generation_diagnostics
        self.assertEqual([item["repair"] for item in diagnostics], [False, True])
        self.assertEqual(
            [item["output_text_received"] for item in diagnostics], [False, True]
        )

    def test_provider_failure_does_not_repair_or_expose_credentials(self):
        secret_error = RuntimeError(
            f"Authorization: Bearer {API_KEY}; endpoint={BASE_URL}; api_key={API_KEY}"
        )
        client = _FakeOpenAI()
        client.responses = _FakeResponses([secret_error])
        config = OpenAIConfig(
            model="gpt-6.1-sol",
            api_key=API_KEY,
            base_url=BASE_URL,
            reasoning_effort="medium",
            background=True,
            service_tier="default",
            max_retries=2,
        )
        with patch("openai.OpenAI", return_value=client):
            extractor = LLMRelationExtractor.from_openai(config)
            with self.assertRaisesRegex(
                RelationExtractionError, "provider invocation failed"
            ) as raised:
                extractor.extract_relations(TEXT, ENTITIES)

        self.assertEqual(len(client.responses.create_calls), 1)
        self.assertIsNone(raised.exception.__cause__)
        self.assertNotIn(API_KEY, str(raised.exception))
        self.assertNotIn(BASE_URL, str(raised.exception))
        self.assertNotIn(API_KEY, "".join(traceback.format_exception(raised.exception)))
        self.assertNotIn(BASE_URL, "".join(traceback.format_exception(raised.exception)))
        serialized = json.dumps(extractor.last_generation_diagnostics)
        self.assertNotIn(API_KEY, serialized)
        self.assertNotIn(BASE_URL, serialized)
        self.assertEqual(extractor.last_generation_diagnostics[0]["status"], "create_failed")

    def test_foreground_provider_errors_are_redacted_and_not_repaired(self):
        class _FakeRunnable:
            def invoke(self, prompt):
                raise RuntimeError(
                    f"Authorization: Bearer {API_KEY}; URL {BASE_URL}; api_key={API_KEY}"
                )

        class _FakeChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def with_structured_output(self, schema):
                return _FakeRunnable()

        with patch.dict(
            sys.modules,
            {"langchain_openai": SimpleNamespace(ChatOpenAI=_FakeChatOpenAI)},
        ):
            extractor = LLMRelationExtractor.from_openai(
                OpenAIConfig(api_key=API_KEY, base_url=BASE_URL, max_retries=2)
            )
            with self.assertRaisesRegex(
                RelationExtractionError, "provider invocation failed"
            ) as raised:
                extractor.extract_relations(TEXT, ENTITIES)

        self.assertNotIn(API_KEY, str(raised.exception))
        self.assertNotIn(BASE_URL, str(raised.exception))
        self.assertEqual(len(extractor.last_generation_diagnostics), 1)
        displayed_error = "".join(traceback.format_exception(raised.exception))
        self.assertNotIn(API_KEY, displayed_error)
        self.assertNotIn(BASE_URL, displayed_error)
        self.assertEqual(
            extractor.last_generation_diagnostics[0]["status"], "provider_failed"
        )


if __name__ == "__main__":
    unittest.main()
