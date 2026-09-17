"""Controlled LangChain harness for evidence-grounded LLM relation extraction.

The harness owns prompt construction, OpenAI model creation, structured-output
binding, and a small repair budget.  It returns only the local relation contract
from :mod:`biomedical_extractor.relation_extraction`.
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

DEFAULT_LLM_RELATION_MODEL = "gpt-4o-mini"
DEFAULT_RELATION_PREDICATES = (
    "association",
    "positive correlation",
    "negative correlation",
    "binds",
    "interacts with",
    "treats",
    "causes",
)

RELATION_EXTRACTION_SYSTEM_PROMPT = """You are a conservative biomedical relation extractor.

Extract only relationships explicitly asserted by the supplied source text. Do not add biological facts from model knowledge, common sense, or the entity types. Every relation must connect two IDs from the supplied entity list. Keep the source-to-target direction expressed by the text. Do not turn a negated claim into a positive relation: set negated=true for an explicitly negated claim. Every emitted relation must include evidence copied verbatim as a contiguous substring of the source text. If the text does not assert a relation between supplied entities, return an empty relations list.

Use one concise predicate from the allowed predicate list. Preserve the exact
relation wording in surface_form when it is useful. Do not emit explanations
outside the structured response.
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
    temperature: float = 0.0
    max_tokens: int | None = 1024
    max_retries: int = 2
    predicates: tuple[str, ...] = DEFAULT_RELATION_PREDICATES

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("OpenAI model must be a non-empty string")
        if not isinstance(self.api_key_env, str) or not self.api_key_env.strip():
            raise ValueError("OpenAI API-key environment variable must be non-empty")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("OpenAI temperature must be between 0 and 2")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("OpenAI max_tokens must be positive when supplied")
        if self.max_retries < 0:
            raise ValueError("OpenAI max_retries must not be negative")
        _validate_predicates(self.predicates)

    @classmethod
    def from_environment(cls) -> OpenAIConfig:
        """Read non-secret model settings and the optional API key from env vars."""

        max_tokens = os.getenv("BIOMEDICAL_RELATION_MAX_TOKENS")
        return cls(
            model=os.getenv("BIOMEDICAL_RELATION_MODEL", DEFAULT_LLM_RELATION_MODEL),
            api_key_env=os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY"),
            api_key=os.getenv(os.getenv("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            max_tokens=int(max_tokens) if max_tokens else 1024,
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
        predicates: Sequence[str] = DEFAULT_RELATION_PREDICATES,
        max_retries: int = 2,
        prompt: str = RELATION_EXTRACTION_SYSTEM_PROMPT,
    ) -> None:
        """Bind a chat/runnable model and a finite bounded repair budget.

        A real LangChain chat model is bound to an internal Pydantic structured
        schema when it exposes ``with_structured_output``.  Test doubles may
        implement only ``invoke`` and return a mapping or JSON string; the same
        deterministic parser and validator are still applied.
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
        _validate_predicates(predicates)
        self._predicates = tuple(predicates)
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
            "temperature": config.temperature,
            # Output repair is deliberately owned by this harness.  Provider
            # retries, when desired, should be configured separately by callers.
            "max_retries": 0,
        }
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        if config.base_url is not None:
            kwargs["base_url"] = config.base_url

        return cls(
            ChatOpenAI(**kwargs),
            predicates=config.predicates,
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
            return validate_relations(
                text, entities, (), allowed_predicates=self._predicates
            )

        prompt = _build_prompt(text, entities, self._predicates, self._prompt)
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._model.invoke(prompt)
                raw_relations = _parse_structured_response(response)
                return validate_relations(
                    text,
                    entities,
                    raw_relations,
                    allowed_predicates=self._predicates,
                )
            except Exception as error:
                last_error = error
                if attempt >= self._max_retries:
                    raise RelationExtractionError(
                        "LLM relation extraction failed after "
                        f"{attempt + 1} bounded attempt(s): {error}"
                    ) from error
                prompt = _build_prompt(
                    text,
                    entities,
                    self._predicates,
                    self._prompt,
                    repair=f"The previous response failed validation: {error}. "
                    "Return a corrected structured response only.",
                )

        # The loop always returns or raises.  Keeping this guard makes the
        # invariant explicit if the retry implementation changes later.
        raise RelationExtractionError("LLM relation extraction stopped unexpectedly") from last_error


# The longer name is useful to callers that want to make the framework boundary
# visible, while the shorter name keeps the public invocation ergonomic.
LangChainRelationExtractor = LLMRelationExtractor
OpenAIRelationExtractor = LLMRelationExtractor


def _validate_predicates(predicates: Sequence[str]) -> None:
    """Validate a finite predicate schema before prompting or scoring."""

    if not predicates or any(
        not isinstance(predicate, str) or not predicate.strip()
        for predicate in predicates
    ):
        raise ValueError("Relation predicates must contain non-empty strings")
    if len(set(predicates)) != len(predicates):
        raise ValueError("Relation predicates must be unique")


def _build_prompt(
    text: str,
    entities: Sequence[Entity],
    predicates: Sequence[str],
    system_prompt: str,
    repair: str | None = None,
) -> str:
    """Build one self-contained extraction or repair prompt."""

    entity_payload = [entity.to_dict() for entity in entities]
    prompt = (
        f"{system_prompt.strip()}\n\n"
        f"Allowed predicates (use exact spelling): {json.dumps(list(predicates))}\n\n"
        "Supplied entities:\n"
        f"{json.dumps(entity_payload, ensure_ascii=False, indent=2)}\n\n"
        "Source text:\n"
        f"{text}"
    )
    if repair:
        prompt = f"{prompt}\n\nREPAIR INSTRUCTION:\n{repair}"
    return prompt


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
        predicate: StrictStr = Field(description="One allowed concise relation predicate")
        evidence: StrictStr = Field(description="Verbatim contiguous source-text evidence")
        negated: StrictBool = Field(description="Whether the asserted relation is explicitly negated")
        surface_form: StrictStr | None = Field(
            default=None, description="Optional verbatim relation wording"
        )
        score: float | None = Field(
            default=None, description="Optional provider confidence from 0 to 1"
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
