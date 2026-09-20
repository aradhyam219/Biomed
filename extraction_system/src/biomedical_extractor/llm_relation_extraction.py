"""Controlled LangChain harness for evidence-grounded LLM relation extraction.

The harness owns prompt construction, OpenAI model creation, structured-output
binding, and a small repair budget.  It returns only the local relation contract
from :mod:`biomedical_extractor.relation_extraction`.  The active OpenAI path
uses LangChain's explicit Responses API integration; provider-specific response
objects remain inside this module.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .entity_extraction import Entity
from .relation_extraction import (
    RelationExtractionError,
    RelationExtractionResult,
    RelationValidationError,
    validate_relations,
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

RELATION_EXTRACTION_SYSTEM_PROMPT = """You are a conservative biomedical relation extractor.

Extract only relationships explicitly asserted by the supplied source text. Do not add biological facts from model knowledge, common sense, or the entity types. Every relation must connect two IDs from the supplied entity list. Keep the source-to-target direction expressed by the text. Do not turn a negated claim into a positive relation: set negated=true for an explicitly negated claim. Every emitted relation must include evidence copied verbatim as a contiguous substring of the source text. If the text does not assert a relation between supplied entities, return an empty relations list.

Use predicate as a concise, graph-friendly normalized relationship. Use assertion
as a complete source-grounded restatement of the scientific meaning represented
by that relation; it may be normalized rather than verbatim, but it must not add
information absent from the evidence. When an explicit manipulation, treatment,
perturbation, or comparable condition materially changes the meaning, record it
in intervention. Record explicit outcomes that would otherwise be lost from a
binary edge in effects, and explicit contextual qualifiers needed for
interpretation in context. Preserve intervention, effects, and context in the
assertion when they are material.

Leave optional intervention, effects, and context empty or null when the source
does not explicitly support them. Do not force a finite predicate ontology, add
process or event endpoints, or infer effects and context from biomedical
knowledge. Preserve the exact relation wording in surface_form when it is
useful. Do not emit explanations outside the structured response.
"""


@dataclass(frozen=True)
class OpenAIConfig:
    """External configuration for the initial OpenAI-backed relation path.

    API credentials are read from ``api_key_env`` unless an in-memory key is
    explicitly supplied by application configuration.  The key is excluded from
    the dataclass representation and is never serialized by this package.
    """

    model: str = DEFAULT_LLM_RELATION_MODEL
    api_key_env: str = "OPENAI_API_KEY"
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
    reasoning_effort: str = DEFAULT_LLM_REASONING_EFFORT
    max_completion_tokens: int | None = DEFAULT_LLM_MAX_COMPLETION_TOKENS
    max_retries: int = 2

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

    @classmethod
    def from_environment(cls) -> OpenAIConfig:
        """Read non-secret model settings and the optional API key from env vars."""

        max_completion_tokens = os.getenv("BIOMEDICAL_RELATION_MAX_COMPLETION_TOKENS")
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
    """Run a LangChain-compatible chat model behind the local RE contract."""

    def __init__(
        self,
        model: Any,
        *,
        max_retries: int = 2,
        prompt: str = RELATION_EXTRACTION_SYSTEM_PROMPT,
    ) -> None:
        """Bind a chat/runnable model and a finite bounded repair budget.

        A real LangChain chat model is bound to an internal Pydantic structured
        schema when it exposes ``with_structured_output``.  Test doubles may
        implement only ``invoke`` and return a mapping or JSON string; the same
        deterministic parser and validator are still applied. The LLM path
        does not impose a finite predicate ontology.
        """

        if not callable(getattr(model, "invoke", None)) and not callable(
            getattr(model, "with_structured_output", None)
        ):
            raise TypeError(
                "LLM relation model must expose invoke(prompt) or "
                "with_structured_output(schema)"
            )
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._max_retries = max_retries
        self._prompt = prompt
        self._model = _bind_structured_output(model)
        if not callable(getattr(self._model, "invoke", None)):
            raise TypeError("Structured relation model must expose callable invoke(prompt)")

    @classmethod
    def from_openai(
        cls, config: OpenAIConfig | None = None
    ) -> LLMRelationExtractor:
        """Construct the initial OpenAI provider path from external config."""

        config = config or OpenAIConfig.from_environment()
        api_key = config.resolved_api_key()
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

        return cls(
            ChatOpenAI(**kwargs),
            max_retries=config.max_retries,
        )

    def extract_relations(
        self, text: str, entities: Sequence[Entity]
    ) -> RelationExtractionResult:
        """Extract, validate, and deduplicate grounded relations."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        # No supplied entity can be a valid endpoint.  Avoid a needless model
        # request, while still validating duplicate/invalid supplied IDs.
        if not entities or not text.strip():
            return validate_relations(text, entities, ())

        prompt = _build_prompt(text, entities, self._prompt)
        for attempt in range(self._max_retries + 1):
            try:
                response = self._model.invoke(prompt)
            except Exception as error:
                if not _is_generated_output_error(error):
                    raise RelationExtractionError(
                        f"LLM relation provider invocation failed: {error}"
                    ) from error
                output_error = error
            else:
                try:
                    raw_relations = _parse_structured_response(response)
                    return validate_relations(text, entities, raw_relations)
                except RelationValidationError as error:
                    output_error = error

            if attempt >= self._max_retries:
                raise RelationExtractionError(
                    "LLM relation output remained invalid after "
                    f"{attempt + 1} bounded attempt(s): {output_error}"
                ) from output_error

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
                "Optional explicit contextual qualifiers needed for interpretation; "
                "do not infer them and use an empty list when not applicable"
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
