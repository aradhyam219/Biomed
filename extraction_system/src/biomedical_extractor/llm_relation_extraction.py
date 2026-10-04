"""Controlled LangChain harness for evidence-grounded LLM relation extraction.

The harness owns prompt construction, OpenAI model creation, structured-output
binding, and a small repair budget.  It returns only the local relation contract
from :mod:`biomedical_extractor.relation_extraction`. The default OpenAI path
uses LangChain; an explicit background setting uses the bounded Responses
executor. Provider-specific objects remain behind this relation boundary.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .entity_extraction import Entity
from .relation_extraction import (
    RelationExtractionError,
    RelationExtractionResult,
    RelationValidationError,
    validate_relations,
)
from .responses_execution import (
    REQUEST_TIMEOUT_SECONDS,
    ResponsesBackgroundExecutor,
    ResponsesExecutionError,
)

DEFAULT_LLM_RELATION_MODEL = "gpt-5.6-luna"
DEFAULT_LLM_REASONING_EFFORT = "max"
DEFAULT_LLM_MAX_COMPLETION_TOKENS = 128000
SUPPORTED_LLM_REASONING_EFFORTS = (
    "none",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
)
SUPPORTED_LLM_SERVICE_TIERS = (
    "auto",
    "default",
    "flex",
    "scale",
    "priority",
    "fast",
)

RELATION_EXTRACTION_SYSTEM_PROMPT = """You are a conservative biomedical relation extractor.

Extract only relationships explicitly asserted by the supplied source text. Do not add biological facts from model knowledge, common sense, or the entity types. Every relation must connect two IDs from the supplied entity list. Keep the source-to-target direction expressed by the text. Do not turn a negated claim into a positive relation: set negated=true for an explicitly negated claim. Every emitted relation must include evidence copied verbatim as a contiguous substring of the source text. If the text does not assert a relation between supplied entities, return an empty relations list.

Do not emit a relation whose sole meaning is that two supplied mentions are
alternative names, abbreviations, aliases, or textual labels for the same
biomedical entity. Identity and abbreviation resolution are handled separately
by document-local entity assembly.

Use predicate as a concise, graph-friendly normalized relationship. Use assertion
as a complete source-grounded restatement of the scientific meaning represented
by that relation; it may be normalized rather than verbatim, but it must not add
information absent from the evidence. When an explicit manipulation, treatment,
perturbation, or comparable condition materially changes the meaning, record it
in intervention. Record explicit outcomes that would otherwise be lost from a
binary edge in effects, and explicit contextual qualifiers needed for
interpretation in context. Preserve intervention, effects, and context in the
assertion when they are material. `intervention`, `effects`, and `context` must
describe the relation represented by the supplied source and target endpoints.
Do not use these structured qualifiers to hide another supplied named entity as
a material third participant. If another supplied entity participates in a
distinct explicitly asserted relationship, represent that relationship
separately when supported by the text.

Use context only for an explicit biological, experimental, clinical, organismal,
tissue, cellular, disease-state, cohort, environmental, or comparable
setting/condition needed to interpret where or under what conditions the
relation holds. Do not use context for a mechanistic explanation, another
relation, another entity interaction, or free-floating information that fits
nowhere else; retain important explanatory wording in assertion or express a
separate grounded relation when appropriate.

Leave optional intervention, effects, and context empty or null when the source
does not explicitly support them. Do not force a finite predicate ontology, add
process or event endpoints, or infer effects and context from biomedical
knowledge. Preserve the exact relation wording in surface_form when it is
useful. Do not emit explanations outside the structured response.
"""


@dataclass(frozen=True)
class OpenAIConfig:
    """External configuration for the OpenAI-backed relation path.

    API credentials are read from ``api_key_env`` unless an in-memory key is
    explicitly supplied by application configuration. The key and base URL are
    excluded from the dataclass representation and provider diagnostics.
    """

    model: str = DEFAULT_LLM_RELATION_MODEL
    api_key_env: str = "OPENAI_API_KEY"
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = field(default=None, repr=False)
    reasoning_effort: str = DEFAULT_LLM_REASONING_EFFORT
    max_completion_tokens: int | None = DEFAULT_LLM_MAX_COMPLETION_TOKENS
    max_retries: int = 2
    background: bool = False
    service_tier: str | None = None
    poll_interval_seconds: float = 3.0
    generation_timeout_seconds: float = 900.0

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("OpenAI model must be a non-empty string")
        if not isinstance(self.api_key_env, str) or not self.api_key_env.strip():
            raise ValueError("OpenAI API-key environment variable must be non-empty")
        if self.reasoning_effort not in SUPPORTED_LLM_REASONING_EFFORTS:
            raise ValueError(
                "OpenAI reasoning_effort must be one of: "
                f"{', '.join(SUPPORTED_LLM_REASONING_EFFORTS)}"
            )
        if self.max_completion_tokens is not None and self.max_completion_tokens <= 0:
            raise ValueError(
                "OpenAI max_completion_tokens must be positive when supplied"
            )
        if self.max_retries < 0:
            raise ValueError("OpenAI max_retries must not be negative")
        if not isinstance(self.background, bool):
            raise ValueError("OpenAI background must be a boolean")
        if (
            self.service_tier is not None
            and self.service_tier not in SUPPORTED_LLM_SERVICE_TIERS
        ):
            raise ValueError(
                "OpenAI service_tier must be one of: "
                f"{', '.join(SUPPORTED_LLM_SERVICE_TIERS)}"
            )
        for name, value in (
            ("poll_interval_seconds", self.poll_interval_seconds),
            ("generation_timeout_seconds", self.generation_timeout_seconds),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value <= 0
            ):
                raise ValueError(f"OpenAI {name} must be positive and finite")

    @classmethod
    def from_environment(cls) -> OpenAIConfig:
        """Read non-secret model settings and the optional API key from env vars."""

        max_completion_tokens = os.getenv("BIOMEDICAL_RELATION_MAX_COMPLETION_TOKENS")
        background = _parse_environment_bool(
            os.getenv("BIOMEDICAL_RELATION_BACKGROUND", "false"),
            "BIOMEDICAL_RELATION_BACKGROUND",
        )
        poll_interval = os.getenv("BIOMEDICAL_RELATION_POLL_INTERVAL_SECONDS")
        generation_timeout = os.getenv("BIOMEDICAL_RELATION_TIMEOUT_SECONDS")
        return cls(
            model=os.getenv("BIOMEDICAL_RELATION_MODEL", DEFAULT_LLM_RELATION_MODEL),
            api_key_env=os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY"),
            api_key=os.getenv(os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            reasoning_effort=os.getenv(
                "BIOMEDICAL_RELATION_REASONING_EFFORT",
                DEFAULT_LLM_REASONING_EFFORT,
            ),
            max_completion_tokens=(
                int(max_completion_tokens)
                if max_completion_tokens
                else DEFAULT_LLM_MAX_COMPLETION_TOKENS
            ),
            max_retries=int(os.getenv("BIOMEDICAL_RELATION_MAX_RETRIES", "2")),
            background=background,
            service_tier=os.getenv("BIOMEDICAL_RELATION_SERVICE_TIER") or None,
            poll_interval_seconds=(float(poll_interval) if poll_interval else 3.0),
            generation_timeout_seconds=(
                float(generation_timeout) if generation_timeout else 900.0
            ),
        )

    def resolved_api_key(self) -> str:
        """Return the configured key or fail before constructing a live client."""

        value = self.api_key or os.getenv(self.api_key_env)
        if not value:
            raise RuntimeError(
                f"OpenAI credentials are unavailable; set {self.api_key_env} "
                "or provide api_key through application configuration"
            )
        return value


class LLMRelationExtractor:
    """Run OpenAI or injected models behind the local relation contract."""

    def __init__(
        self,
        model: Any,
        *,
        max_retries: int = 2,
        prompt: str = RELATION_EXTRACTION_SYSTEM_PROMPT,
        diagnostics_callback: Callable[[dict[str, Any]], None] | None = None,
        redaction_values: Sequence[str] = (),
    ) -> None:
        """Bind a chat/runnable model and a finite bounded repair budget.

        A real LangChain chat model is bound to an internal Pydantic structured
        schema when it exposes ``with_structured_output``.  Test doubles may
        implement only ``invoke`` and return a mapping or JSON string; the same
        deterministic parser and validator are still applied. The LLM path
        does not impose a finite predicate ontology.
        """

        self._background_executor = (
            model if isinstance(model, ResponsesBackgroundExecutor) else None
        )
        if self._background_executor is None and not callable(
            getattr(model, "invoke", None)
        ) and not callable(getattr(model, "with_structured_output", None)):
            raise TypeError(
                "LLM relation model must expose invoke(prompt) or "
                "with_structured_output(schema)"
            )
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._max_retries = max_retries
        self._prompt = prompt
        self._model = (
            None
            if self._background_executor is not None
            else _bind_structured_output(model)
        )
        if self._model is not None and not callable(getattr(self._model, "invoke", None)):
            raise TypeError("Structured relation model must expose callable invoke(prompt)")
        self._diagnostics_callback = diagnostics_callback
        self._redaction_values = tuple(value for value in redaction_values if value)
        self._last_generation_diagnostics: list[dict[str, Any]] = []

    @property
    def last_generation_diagnostics(self) -> tuple[dict[str, Any], ...]:
        """Return copied plain-data diagnostics for each generation in the last call."""

        return tuple(deepcopy(self._last_generation_diagnostics))

    @classmethod
    def from_openai(
        cls,
        config: OpenAIConfig | None = None,
        *,
        prompt: str = RELATION_EXTRACTION_SYSTEM_PROMPT,
        diagnostics_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> LLMRelationExtractor:
        """Construct the OpenAI path with an optional explicit experimental prompt.

        Omitting ``prompt`` preserves the ordinary Contract 10 system prompt;
        overrides do not change parsing, repair, or semantic validation.
        """

        config = config or OpenAIConfig.from_environment()
        api_key = config.resolved_api_key()
        redaction_values = (api_key, config.base_url or "")
        if config.background:
            try:
                from openai import OpenAI
            except ImportError:  # pragma: no cover - dependency install failure
                raise RuntimeError(
                    "The OpenAI background relation path requires the openai dependency"
                ) from None
            kwargs: dict[str, Any] = {
                "api_key": api_key,
                "max_retries": 0,
                "timeout": REQUEST_TIMEOUT_SECONDS,
            }
            if config.base_url is not None:
                kwargs["base_url"] = config.base_url
            try:
                client = OpenAI(**kwargs)
            except Exception as error:
                raise RuntimeError(
                    "Could not initialize OpenAI background client "
                    f"({_safe_error_type(error)})"
                ) from None
            executor = ResponsesBackgroundExecutor(
                client,
                model=config.model,
                reasoning_effort=config.reasoning_effort,
                max_output_tokens=config.max_completion_tokens,
                service_tier=config.service_tier,
                poll_interval_seconds=float(config.poll_interval_seconds),
                generation_timeout_seconds=float(config.generation_timeout_seconds),
                schema=_structured_payload_schema(),
                diagnostics_callback=diagnostics_callback,
                redaction_values=redaction_values,
            )
            return cls(
                executor,
                max_retries=config.max_retries,
                prompt=prompt,
                diagnostics_callback=diagnostics_callback,
                redaction_values=redaction_values,
            )

        try:
            from langchain_openai import ChatOpenAI
        except ImportError as error:  # pragma: no cover - exercised in bad installs
            raise RuntimeError(
                "The OpenAI relation path requires the langchain-openai dependency"
            ) from error

        kwargs: dict[str, Any] = {
            "model": config.model,
            "api_key": api_key,
            "use_responses_api": True,
            "reasoning": {"effort": config.reasoning_effort},
            # Output repair is deliberately owned by this harness.  Provider
            # retries, when desired, should be configured separately by callers.
            "max_retries": 0,
        }
        if config.max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = config.max_completion_tokens
        if config.base_url is not None:
            kwargs["base_url"] = config.base_url
        if config.service_tier is not None:
            kwargs["service_tier"] = config.service_tier

        try:
            model = ChatOpenAI(**kwargs)
        except Exception as error:
            raise RuntimeError(
                f"Could not initialize OpenAI relation client ({_safe_error_type(error)})"
            ) from None
        return cls(
            model,
            max_retries=config.max_retries,
            prompt=prompt,
            diagnostics_callback=diagnostics_callback,
            redaction_values=redaction_values,
        )

    def extract_relations(
        self, text: str, entities: Sequence[Entity]
    ) -> RelationExtractionResult:
        """Extract, validate, and deduplicate grounded relations."""

        self._last_generation_diagnostics = []
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        # No supplied entity can be a valid endpoint.  Avoid a needless model
        # request, while still validating duplicate/invalid supplied IDs.
        if not entities or not text.strip():
            return validate_relations(text, entities, ())

        prompt = _build_prompt(text, entities, self._prompt)
        for attempt in range(self._max_retries + 1):
            generation_diagnostics = {
                "generation_number": attempt + 1,
                "repair": bool(attempt),
                "execution_mode": (
                    "background" if self._background_executor is not None else "invoke"
                ),
                "status": "started",
            }
            self._last_generation_diagnostics.append(generation_diagnostics)
            generation_started = time.monotonic()
            output_error: Exception | None = None
            if self._background_executor is not None:
                try:
                    response = self._background_executor.execute(
                        prompt, generation_diagnostics
                    )
                except ResponsesExecutionError as error:
                    generation_diagnostics.update(error.diagnostics)
                    raise RelationExtractionError(
                        f"LLM relation provider invocation failed: {error}"
                    ) from None
            else:
                try:
                    response = self._model.invoke(prompt)
                except Exception as error:
                    generation_diagnostics["elapsed_seconds"] = round(
                        max(0.0, time.monotonic() - generation_started), 3
                    )
                    if not _is_generated_output_error(error):
                        generation_diagnostics.update(
                            status="provider_failed",
                            error_type=_safe_error_type(error),
                        )
                        self._publish_diagnostics(generation_diagnostics)
                        raise RelationExtractionError(
                            "LLM relation provider invocation failed: "
                            f"{_safe_exception_text(error, self._redaction_values)}"
                        ) from None
                    output_error = error
                    generation_diagnostics.update(
                        status="output_invalid",
                        output_error_type=_safe_error_type(error),
                    )

            if output_error is None:
                try:
                    raw_relations = _parse_structured_response(response)
                    validated = validate_relations(text, entities, raw_relations)
                except RelationValidationError as error:
                    output_error = error
                    generation_diagnostics.update(
                        status="output_invalid",
                        output_error_type=_safe_error_type(error),
                    )
                else:
                    generation_diagnostics.update(
                        status="success",
                        elapsed_seconds=round(
                            max(0.0, time.monotonic() - generation_started), 3
                        ),
                        validated_relation_count=len(validated.relations),
                    )
                    self._publish_diagnostics(generation_diagnostics)
                    return validated

            generation_diagnostics["elapsed_seconds"] = round(
                max(0.0, time.monotonic() - generation_started), 3
            )
            self._publish_diagnostics(generation_diagnostics)

            if attempt >= self._max_retries:
                raise RelationExtractionError(
                    "LLM relation output remained invalid after "
                    f"{attempt + 1} bounded attempt(s): "
                    f"{_safe_exception_text(output_error, self._redaction_values)}"
                ) from None

            prompt = _build_prompt(
                text,
                entities,
                self._prompt,
                repair=f"The previous response failed validation: {output_error}. "
                "Return a corrected structured response only.",
            )

        # The loop always returns or raises.  Keeping this guard makes the
        # invariant explicit if the retry implementation changes later.
        raise RelationExtractionError("LLM relation extraction stopped unexpectedly")

    def _publish_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        """Send a detached copy of one safe generation snapshot to the caller."""

        if self._diagnostics_callback is None:
            return
        try:
            self._diagnostics_callback(deepcopy(diagnostics))
        except BaseException as error:
            diagnostics.update(
                status="diagnostics_callback_failed",
                diagnostics_callback_error_type=_safe_error_type(error),
            )
            raise RelationExtractionError(
                "LLM relation diagnostics callback failed"
            ) from None


# The longer name is useful to callers that want to make the framework boundary
# visible, while the shorter name keeps the public invocation ergonomic.
LangChainRelationExtractor = LLMRelationExtractor
OpenAIRelationExtractor = LLMRelationExtractor


def _build_prompt(
    text: str,
    entities: Sequence[Entity],
    system_prompt: str,
    repair: str | None = None,
) -> str:
    """Build one self-contained extraction or repair prompt."""

    entity_payload = [entity.to_dict() for entity in entities]
    prompt = (
        f"{system_prompt.strip()}\n\n"
        "Supplied entities:\n"
        f"{json.dumps(entity_payload, ensure_ascii=False, indent=2)}\n\n"
        "Source text:\n"
        f"{text}"
    )
    if repair:
        prompt = f"{prompt}\n\nREPAIR INSTRUCTION:\n{repair}"
    return prompt


def _is_generated_output_error(error: Exception) -> bool:
    """Return whether an invocation error is repairable generated output."""

    error_types: list[type[BaseException]] = [
        RelationValidationError,
        json.JSONDecodeError,
    ]
    try:
        from langchain_core.exceptions import OutputParserException
    except ImportError:  # pragma: no cover - dependency is project-required
        pass
    else:
        error_types.append(OutputParserException)
    try:
        from pydantic import ValidationError
    except ImportError:  # pragma: no cover - dependency is project-required
        pass
    else:
        error_types.append(ValidationError)
    return isinstance(error, tuple(error_types))


def _bind_structured_output(model: Any) -> Any:
    """Bind LangChain's structured output schema without exposing it downstream."""

    binder = getattr(model, "with_structured_output", None)
    if not callable(binder):
        return model
    return binder(_structured_payload_schema())


def _structured_payload_schema() -> type[Any]:
    """Create the internal Pydantic schema passed only to LangChain."""

    try:
        from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr
    except ImportError as error:  # pragma: no cover - bad dependency installation
        raise RuntimeError(
            "Structured OpenAI relation extraction requires pydantic"
        ) from error

    class StructuredRelation(BaseModel):
        model_config = ConfigDict(extra="forbid")

        source: StrictStr = Field(description="Supplied source entity ID")
        target: StrictStr = Field(description="Supplied target entity ID")
        predicate: StrictStr = Field(
            description=(
                "Concise normalized predicate faithfully describing the asserted relation"
            )
        )
        assertion: StrictStr = Field(
            description=(
                "Complete source-grounded restatement of the scientific meaning; "
                "do not add information absent from the evidence"
            )
        )
        evidence: StrictStr = Field(description="Verbatim contiguous source-text evidence")
        negated: StrictBool = Field(description="Whether the asserted relation is explicitly negated")
        intervention: StrictStr | None = Field(
            default=None,
            description=(
                "Optional explicit intervention or perturbation material to the assertion; "
                "leave null when not applicable"
            ),
        )
        effects: list[StrictStr] = Field(
            default_factory=list,
            description=(
                "Optional explicit effects or outcomes; do not infer them and use an "
                "empty list when not applicable"
            ),
        )
        context: list[StrictStr] = Field(
            default_factory=list,
            description=(
                "Optional explicit biological, experimental, clinical, organismal, "
                "tissue, cellular, disease-state, cohort, environmental, or "
                "comparable setting/condition needed to interpret where or under "
                "what conditions the relation holds; do not use for mechanisms, "
                "another relation, or another entity interaction"
            ),
        )
        surface_form: StrictStr | None = Field(
            default=None, description="Optional verbatim relation wording"
        )

    class StructuredRelationPayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        relations: list[StructuredRelation] = Field(default_factory=list)

    return StructuredRelationPayload


def _parse_structured_response(response: Any) -> tuple[Mapping[str, Any], ...]:
    """Convert LangChain/Pydantic or test-double output to raw relation mappings."""

    payload = _response_payload(response)
    if not isinstance(payload, Mapping):
        raise RelationValidationError("Structured LLM output must be a JSON object")
    if "relations" not in payload:
        raise RelationValidationError("Structured LLM output is missing relations")
    unknown = set(payload) - {"relations"}
    if unknown:
        raise RelationValidationError(
            f"Structured LLM output has unsupported field(s): {sorted(unknown)}"
        )
    raw_relations = payload["relations"]
    if not isinstance(raw_relations, (list, tuple)):
        raise RelationValidationError("Structured LLM relations must be a list")

    normalized: list[Mapping[str, Any]] = []
    for index, raw_relation in enumerate(raw_relations):
        mapping = _model_mapping(raw_relation)
        if mapping is None:
            raise RelationValidationError(
                f"Structured relation at index {index} is not an object"
            )
        normalized.append(mapping)
    return tuple(normalized)


def _response_payload(response: Any) -> Any:
    """Unwrap common structured-runnable, message, and JSON-string responses."""

    if isinstance(response, Mapping):
        if "parsed" in response:
            if response["parsed"] is None:
                raise RelationValidationError(
                    f"LangChain structured output could not be parsed: "
                    f"{response.get('parsing_error', 'unknown parser error')}"
                )
            return _response_payload(response["parsed"])
        return response

    # An unstructured LangChain AIMessage can expose both ``content`` and a
    # model-dump mapping.  Prefer its content unless it is already a structured
    # payload with a relations field.
    if hasattr(response, "content") and not hasattr(response, "relations"):
        return _response_payload(response.content)

    mapping = _model_mapping(response)
    if mapping is not None:
        return mapping

    if isinstance(response, (list, tuple)):
        text_blocks = []
        for block in response:
            if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                text_blocks.append(block["text"])
            elif isinstance(block, str):
                text_blocks.append(block)
        if text_blocks:
            return _response_payload("\n".join(text_blocks))

    if isinstance(response, str):
        candidate = _strip_code_fence(response)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as error:
            raise RelationValidationError(
                f"Structured LLM output is not valid JSON: {error.msg}"
            ) from error

    raise RelationValidationError(
        f"Unsupported structured LLM response type: {type(response).__name__}"
    )


def _model_mapping(value: Any) -> Mapping[str, Any] | None:
    """Dump a Pydantic/dataclass-like structured value when possible."""

    if isinstance(value, Mapping):
        return value
    dumper = getattr(value, "model_dump", None)
    if callable(dumper):
        dumped = dumper()
        return dumped if isinstance(dumped, Mapping) else None
    legacy_dumper = getattr(value, "dict", None)
    if callable(legacy_dumper):
        dumped = legacy_dumper()
        return dumped if isinstance(dumped, Mapping) else None
    if hasattr(value, "relations"):
        return {"relations": getattr(value, "relations")}
    return None


def _strip_code_fence(value: str) -> str:
    """Accept a JSON code fence from a non-structured test double only."""

    candidate = value.strip()
    if not candidate.startswith("```"):
        return candidate
    lines = candidate.splitlines()
    if lines:
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_environment_bool(value: str, name: str) -> bool:
    """Parse a deliberate true/false environment setting without guessing."""

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _safe_error_type(error: BaseException) -> str:
    """Return a bounded exception class label without its provider message."""

    name = type(error).__name__
    return name if re.fullmatch(r"[A-Za-z0-9_]{1,80}", name) else "ProviderError"


def _safe_exception_text(error: BaseException, secrets: Sequence[str]) -> str:
    """Keep useful local error context while stripping credentials and URLs."""

    try:
        message = str(error)
    except BaseException:
        return _safe_error_type(error)
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
            trimmed = secret.rstrip("/")
            if trimmed and trimmed != secret:
                message = message.replace(trimmed, "[REDACTED]")
    message = re.sub(r"(?i)https?://[^\s\"'<>]+", "[REDACTED_URL]", message)
    message = re.sub(r"(?i)\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED]", message)
    message = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)
    message = re.sub(
        r"(?i)(api[_-]?key|authorization)(\s*[:=]\s*)[\"']?[^,\s\"']+",
        r"\1\2[REDACTED]",
        message,
    )
    return message[:500] if message else _safe_error_type(error)
