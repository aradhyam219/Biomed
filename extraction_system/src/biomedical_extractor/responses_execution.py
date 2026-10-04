"""Bounded OpenAI Responses background execution for relation generations.

The module owns only provider transport: it submits one structured generation,
polls its stable response ID, cancels an active job on local failure, and returns
the completed JSON text with plain, credential-free diagnostics. Domain parsing
and relation validation remain in :mod:`llm_relation_extraction`.
"""

from __future__ import annotations

from copy import deepcopy
import re
import time
from typing import Any, Callable, Mapping, Sequence


ACTIVE_STATUSES = frozenset({"queued", "in_progress"})
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "incomplete"})
MAX_CONSECUTIVE_POLL_ERRORS = 5
REQUEST_TIMEOUT_SECONDS = 60.0
CANCEL_TIMEOUT_SECONDS = 5.0
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


class ResponsesExecutionError(RuntimeError):
    """A controlled, safe-to-display background provider failure."""

    def __init__(self, message: str, diagnostics: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.diagnostics = deepcopy(dict(diagnostics))


class ResponsesBackgroundExecutor:
    """Run one bounded background Responses generation through the OpenAI SDK."""

    def __init__(
        self,
        client: Any,
        *,
        model: str,
        reasoning_effort: str,
        max_output_tokens: int | None,
        service_tier: str | None,
        poll_interval_seconds: float,
        generation_timeout_seconds: float,
        schema: type[Any],
        diagnostics_callback: Callable[[dict[str, Any]], None] | None = None,
        redaction_values: Sequence[str] = (),
    ) -> None:
        self._client = client
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_output_tokens = max_output_tokens
        self._service_tier = service_tier
        self._poll_interval_seconds = poll_interval_seconds
        self._generation_timeout_seconds = generation_timeout_seconds
        self._schema = strict_transport_schema(schema)
        self._diagnostics_callback = diagnostics_callback
        self._redaction_values = tuple(value for value in redaction_values if value)

    def execute(self, prompt: str, diagnostics: dict[str, Any]) -> str:
        """Submit exactly one generation, polling and cancelling within its deadline."""

        started = time.monotonic()
        deadline = started + self._generation_timeout_seconds
        diagnostics.update(
            requested_background=True,
            requested_model=_safe_value(self._model, self._redaction_values),
            requested_reasoning_effort=(
                self._reasoning_effort
                if self._reasoning_effort in {"none", "low", "medium", "high", "xhigh", "max"}
                else None
            ),
            requested_service_tier=_safe_service_tier(self._service_tier),
            response_id=None,
            status="create_requested",
            poll_count=0,
            poll_errors=0,
        )
        self._publish(diagnostics)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            self._fail(diagnostics, "timeout", "OpenAI Responses generation timed out")

        request: dict[str, Any] = {
            "model": self._model,
            "input": prompt,
            "reasoning": {"effort": self._reasoning_effort},
            "background": True,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "StructuredRelationPayload",
                    "schema": self._schema,
                    "strict": True,
                }
            },
            "timeout": min(REQUEST_TIMEOUT_SECONDS, remaining),
        }
        if self._max_output_tokens is not None:
            request["max_output_tokens"] = self._max_output_tokens
        if self._service_tier is not None:
            request["service_tier"] = self._service_tier

        response = None
        create_error = None
        try:
            response = self._client.responses.create(**request)
        except KeyboardInterrupt:
            diagnostics.update(status="interrupted", error_type="KeyboardInterrupt")
            diagnostics["elapsed_seconds"] = _elapsed(started)
            self._publish_after_failure(diagnostics)
            self._fail(diagnostics, "interrupted", "OpenAI Responses generation was interrupted")
        except Exception as error:
            create_error = error
        if create_error is not None:
            diagnostics.update(status="create_failed", **_safe_exception_fields(create_error))
            diagnostics["elapsed_seconds"] = _elapsed(started)
            self._publish_after_failure(diagnostics)
            self._fail(
                diagnostics,
                "create_failed",
                _safe_exception_message("submission", create_error),
            )

        _observe_response(diagnostics, response, self._redaction_values)
        if not diagnostics.get("response_id"):
            self._publish_after_failure(diagnostics)
            self._fail(
                diagnostics,
                "missing_response_id",
                "OpenAI Responses submission returned no stable response ID",
            )
        diagnostics["initial_status"] = diagnostics["status"]
        diagnostics["initial_create_latency_seconds"] = _elapsed(started)
        self._publish_with_active_response(diagnostics, response)

        if time.monotonic() >= deadline:
            self._stop_active(
                response, diagnostics, started, "timeout", "OpenAI Responses generation timed out"
            )

        consecutive_errors = 0
        while _response_status(response) in ACTIVE_STATUSES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._stop_active(
                    response,
                    diagnostics,
                    started,
                    "timeout",
                    "OpenAI Responses generation timed out",
                )

            try:
                time.sleep(min(self._poll_interval_seconds, remaining))
            except KeyboardInterrupt:
                self._stop_active(
                    response,
                    diagnostics,
                    started,
                    "interrupted",
                    "OpenAI Responses generation was interrupted",
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._stop_active(
                    response,
                    diagnostics,
                    started,
                    "timeout",
                    "OpenAI Responses generation timed out",
                )

            poll_error = None
            diagnostics["poll_count"] += 1
            try:
                polled_response = self._client.responses.retrieve(
                    diagnostics["response_id"],
                    timeout=min(REQUEST_TIMEOUT_SECONDS, remaining),
                )
            except KeyboardInterrupt:
                self._stop_active(
                    response,
                    diagnostics,
                    started,
                    "interrupted",
                    "OpenAI Responses generation was interrupted",
                )
            except Exception as error:
                poll_error = error

            if poll_error is not None:
                diagnostics["poll_errors"] += 1
                poll_fields = _safe_exception_fields(poll_error)
                diagnostics["last_poll_error_type"] = poll_fields["error_type"]
                diagnostics["last_poll_http_status"] = poll_fields["http_status"]
                consecutive_errors += 1
                transient = _is_transient_poll_error(poll_error)
                diagnostics["status"] = "polling" if transient else "polling_failed"
                diagnostics["elapsed_seconds"] = _elapsed(started)
                self._publish_with_active_response(diagnostics, response)
                if not transient or consecutive_errors >= MAX_CONSECUTIVE_POLL_ERRORS:
                    self._stop_active(
                        response,
                        diagnostics,
                        started,
                        "polling_failed",
                        _safe_exception_message("polling", poll_error),
                    )
                continue

            previous_response = response
            response = polled_response
            consecutive_errors = 0
            _observe_response(diagnostics, response, self._redaction_values)
            if diagnostics.get("response_id_mismatch"):
                self._stop_active(
                    previous_response,
                    diagnostics,
                    started,
                    "response_id_mismatch",
                    "OpenAI Responses polling returned a different response ID",
                )
            diagnostics["elapsed_seconds"] = _elapsed(started)
            self._publish_with_active_response(diagnostics, response)
            if time.monotonic() >= deadline:
                self._stop_active(
                    response,
                    diagnostics,
                    started,
                    "timeout",
                    "OpenAI Responses generation timed out",
                )

        terminal_status = diagnostics.get("status")
        diagnostics["terminal_status"] = terminal_status
        diagnostics["elapsed_seconds"] = _elapsed(started)
        if terminal_status != "completed":
            if terminal_status not in TERMINAL_STATUSES:
                self._cancel(response, diagnostics)
            diagnostics["status"] = {
                "failed": "provider_failed",
                "cancelled": "provider_cancelled",
                "incomplete": "provider_incomplete",
            }.get(terminal_status, "provider_failed")
            self._publish(diagnostics)
            self._fail(
                diagnostics,
                diagnostics["status"],
                f"OpenAI Responses generation ended with status {terminal_status}",
            )

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str):
            output_text = ""
            diagnostics["output_text_received"] = False
            diagnostics["status"] = "completed_empty_output"
        else:
            diagnostics["output_text_received"] = bool(output_text)
            diagnostics["status"] = "completed"
        self._publish(diagnostics)
        return output_text

    def _publish(self, diagnostics: dict[str, Any]) -> None:
        """Publish a copy containing only the executor's safe local fields."""

        if self._diagnostics_callback is None:
            return
        try:
            self._diagnostics_callback(deepcopy(diagnostics))
        except BaseException as error:
            diagnostics["diagnostics_callback_error_type"] = _safe_type_name(error)
            diagnostics["status"] = "diagnostics_callback_failed"
            self._fail(
                diagnostics,
                "diagnostics_callback_failed",
                "OpenAI Responses diagnostics callback failed",
            )

    def _publish_with_active_response(
        self, diagnostics: dict[str, Any], response: Any
    ) -> None:
        """Cancel a known active response if local diagnostics delivery fails."""

        try:
            self._publish(diagnostics)
        except ResponsesExecutionError as error:
            if _may_be_active(response):
                self._cancel(response, diagnostics)
            error.diagnostics.update(deepcopy(diagnostics))
            raise

    def _publish_after_failure(self, diagnostics: dict[str, Any]) -> None:
        """Make failure notification best-effort when no response can be orphaned."""

        try:
            self._publish(diagnostics)
        except ResponsesExecutionError:
            pass

    def _cancel(self, response: Any, diagnostics: dict[str, Any]) -> None:
        """Attempt a short, bounded cancellation for a known active response ID."""

        response_id = diagnostics.get("response_id")
        if not response_id or not _may_be_active(response):
            return
        diagnostics["cancel_attempted"] = True
        try:
            cancelled = self._client.responses.cancel(
                response_id, timeout=CANCEL_TIMEOUT_SECONDS
            )
        except BaseException as error:
            diagnostics["cancel_error_type"] = _safe_type_name(error)
            return
        diagnostics["cancel_status"] = _response_status(cancelled)
        diagnostics["cancel_response_id"] = _safe_response_id(
            getattr(cancelled, "id", None), self._redaction_values
        )

    def _stop_active(
        self,
        response: Any,
        diagnostics: dict[str, Any],
        started: float,
        status: str,
        message: str,
    ) -> None:
        diagnostics["status"] = status
        diagnostics["elapsed_seconds"] = _elapsed(started)
        diagnostics["terminal_status"] = _response_status(response)
        self._cancel(response, diagnostics)
        diagnostics["elapsed_seconds"] = _elapsed(started)
        self._publish_after_failure(diagnostics)
        self._fail(diagnostics, status, message)

    @staticmethod
    def _fail(
        diagnostics: dict[str, Any], status: str, message: str
    ) -> None:
        diagnostics["status"] = status
        raise ResponsesExecutionError(message, diagnostics) from None


def strict_transport_schema(schema: type[Any]) -> dict[str, Any]:
    """Use the public OpenAI SDK converter for strict JSON Schema transport."""

    try:
        from openai import pydantic_function_tool
    except ImportError:  # pragma: no cover - dependency install failure
        raise RuntimeError("Background relation extraction requires the OpenAI SDK") from None
    try:
        converted = pydantic_function_tool(schema)
        transport = converted["function"]["parameters"]
    except Exception:
        raise RuntimeError("OpenAI SDK could not convert the relation schema") from None
    if not isinstance(transport, dict):
        raise RuntimeError("OpenAI SDK returned an invalid strict relation schema")
    verify_transport_equivalence(schema.model_json_schema(), transport)
    return transport


def verify_transport_equivalence(
    semantic_schema: Mapping[str, Any], transport_schema: Mapping[str, Any]
) -> None:
    """Require identical schema meaning apart from strict object closure rules."""

    def compare(semantic: Any, transport: Any) -> None:
        if isinstance(semantic, dict):
            expected = dict(semantic)
            if expected.get("type") == "object":
                expected["required"] = list(expected.get("properties", {}))
                expected["additionalProperties"] = False
            if expected.get("default", object()) is None:
                expected.pop("default")
            if set(expected) != set(transport):
                raise RuntimeError("OpenAI strict relation schema changed semantic fields")
            for key, value in expected.items():
                compare(value, transport[key])
        elif isinstance(semantic, list):
            if not isinstance(transport, list) or len(semantic) != len(transport):
                raise RuntimeError("OpenAI strict relation schema changed semantic lists")
            for expected_item, transport_item in zip(semantic, transport):
                compare(expected_item, transport_item)
        elif semantic != transport:
            raise RuntimeError("OpenAI strict relation schema changed semantic values")

    compare(dict(semantic_schema), dict(transport_schema))


def _observe_response(
    diagnostics: dict[str, Any], response: Any, redaction_values: Sequence[str]
) -> None:
    """Copy only known safe scalar metadata from an SDK response object."""

    status = _response_status(response)
    diagnostics["status"] = status
    response_id = _safe_response_id(getattr(response, "id", None), redaction_values)
    if diagnostics.get("response_id") is None:
        diagnostics["response_id"] = response_id
    elif response_id != diagnostics["response_id"]:
        diagnostics["response_id_mismatch"] = True
    diagnostics["observed_model"] = _safe_value(
        getattr(response, "model", None), redaction_values
    )
    diagnostics["observed_reasoning_effort"] = _reasoning_effort(response)
    diagnostics["observed_service_tier"] = _safe_service_tier(
        getattr(response, "service_tier", None)
    )
    background = getattr(response, "background", None)
    diagnostics["observed_background"] = background if isinstance(background, bool) else None
    _observe_usage(diagnostics, getattr(response, "usage", None))
    error = getattr(response, "error", None)
    if error is not None:
        diagnostics["provider_error_type"] = _safe_value(
            _field(error, "type"), redaction_values
        )
        diagnostics["provider_error_code"] = _safe_value(
            _field(error, "code"), redaction_values
        )
    incomplete_details = getattr(response, "incomplete_details", None)
    incomplete_reason = _field(incomplete_details, "reason")
    if incomplete_reason in {"max_output_tokens", "content_filter"}:
        diagnostics["incomplete_reason"] = incomplete_reason


def _observe_usage(diagnostics: dict[str, Any], usage: Any) -> None:
    """Extract token counts without retaining SDK usage or detail objects."""

    if usage is None:
        return
    diagnostics["input_tokens"] = _safe_count(_field(usage, "input_tokens"))
    diagnostics["output_tokens"] = _safe_count(_field(usage, "output_tokens"))
    output_details = _field(usage, "output_tokens_details")
    diagnostics["reasoning_tokens"] = _safe_count(
        _field(output_details, "reasoning_tokens")
    )


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _reasoning_effort(response: Any) -> str | None:
    reasoning = getattr(response, "reasoning", None)
    effort = _safe_value(_field(reasoning, "effort"))
    return effort if effort in {"none", "low", "medium", "high", "xhigh", "max"} else None


def _response_status(response: Any) -> str:
    status = getattr(response, "status", None)
    if isinstance(status, str) and status in ACTIVE_STATUSES | TERMINAL_STATUSES:
        return status
    return "unknown"


def _may_be_active(response: Any) -> bool:
    """Treat unfamiliar states as active until the provider proves termination."""

    return _response_status(response) not in TERMINAL_STATUSES


def _safe_response_id(value: Any, redaction_values: Sequence[str] = ()) -> str | None:
    if (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)
        and not value.lower().startswith("sk-")
        and not any(secret in value for secret in redaction_values)
    ):
        return value
    return None


def _safe_value(value: Any, redaction_values: Sequence[str] = ()) -> str | None:
    if (
        isinstance(value, str)
        and _SAFE_VALUE.fullmatch(value)
        and not value.lower().startswith("sk-")
        and not any(secret in value for secret in redaction_values)
    ):
        return value
    return None


def _safe_service_tier(value: Any) -> str | None:
    safe = _safe_value(value)
    return safe if safe in {"auto", "default", "flex", "scale", "priority", "fast"} else None


def _safe_count(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _safe_type_name(error: BaseException) -> str:
    return _safe_value(type(error).__name__) or "ProviderError"


def _safe_exception_fields(error: BaseException) -> dict[str, Any]:
    status_code = getattr(error, "status_code", None)
    return {
        "error_type": _safe_type_name(error),
        "http_status": status_code if isinstance(status_code, int) and not isinstance(status_code, bool) else None,
    }


def _safe_exception_message(operation: str, error: BaseException) -> str:
    fields = _safe_exception_fields(error)
    suffix = (
        f"{fields['error_type']}, HTTP {fields['http_status']}"
        if fields["http_status"] is not None
        else fields["error_type"]
    )
    return f"OpenAI Responses background {operation} failed ({suffix})"


def _is_transient_poll_error(error: BaseException) -> bool:
    names = {base.__name__ for base in type(error).__mro__}
    if "APIConnectionError" in names or "APITimeoutError" in names:
        return True
    status = getattr(error, "status_code", None)
    return isinstance(status, int) and not isinstance(status, bool) and (
        status >= 500 or status in (408, 429)
    )


def _elapsed(started: float) -> float:
    return round(max(0.0, time.monotonic() - started), 3)
