"""Bounded OpenAI structured-output harness for paper-role enrichment.

Provider-specific LangChain and Pydantic values stay in this module.  The
public result is converted immediately to the provider-independent
``PaperRoleExtractionResult`` contract before it reaches the graph pipeline.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .llm_relation_extraction import OpenAIConfig
from .paper_roles import (
    PaperRole,
    PaperRoleExtractionResult,
    PaperRoleRecord,
    PaperRoleTarget,
    PaperRoleValidationError,
    validate_paper_role_result,
)


DEFAULT_PAPER_ROLE_MODEL = "gpt-5.6-luna"
DEFAULT_PAPER_ROLE_REASONING_EFFORT = "max"

PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT = """You are a conservative biomedical paper-role explainer.

Explain only the role of each requested entity within the supplied paper. Summarize what the authors use it for, investigate about it, report about it, or use it to establish scientific or experimental context.

Use only information explicitly supported by the supplied title and complete abstract. Do not add external biomedical knowledge, assumptions, or general facts about the entity. Do not invent relationships merely because an entity was mentioned.

For each requested node ID, return one independent role record. Use category "substantive" when the entity materially participates in the scientific subject matter, and "contextual" when it primarily supplies study setting, model-organism, species, population, cohort, or experimental context. Isolated Species entities should normally be contextual.

Produce at most two concise paragraphs per entity. If the source provides only limited information, produce a shorter explanation rather than extrapolating. Provide one or more exact verbatim source substrings supporting the explanation. Role prose is node metadata only; it must not imply a graph edge or an ontology assertion.
"""


class PaperRoleExtractionError(ValueError):
    """Raised when role-provider invocation or structured output fails."""


class LLMPaperRoleExtractor:
    """Run one paper-level structured role request behind the local seam."""

    def __init__(
        self,
        model: Any,
        *,
        max_retries: int = 2,
        prompt: str = PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT,
    ) -> None:
        if not callable(getattr(model, "invoke", None)) and not callable(
            getattr(model, "with_structured_output", None)
        ):
            raise TypeError(
                "Paper-role model must expose invoke(prompt) or "
                "with_structured_output(schema)"
            )
        if max_retries < 0:
            raise ValueError("Paper-role max_retries must not be negative")
        self._max_retries = max_retries
        self._prompt = prompt
        self._model = _bind_structured_output(model)
        if not callable(getattr(self._model, "invoke", None)):
            raise TypeError("Structured paper-role model must expose callable invoke(prompt)")

    @classmethod
    def from_openai(
        cls, config: OpenAIConfig | None = None
    ) -> "LLMPaperRoleExtractor":
        """Construct the approved Responses API role path.

        Credentials, endpoint, output ceiling, and retry budget are reused from
        the existing configuration, while the role task keeps its own fixed
        model/reasoning defaults and does not alter relation extraction.
        """

        config = config or OpenAIConfig.from_environment()
        api_key = config.resolved_api_key()
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as error:  # pragma: no cover - bad installation
            raise RuntimeError(
                "The OpenAI paper-role path requires the langchain-openai dependency"
            ) from error

        kwargs: dict[str, Any] = {
            "model": DEFAULT_PAPER_ROLE_MODEL,
            "api_key": api_key,
            "use_responses_api": True,
            "reasoning": {"effort": DEFAULT_PAPER_ROLE_REASONING_EFFORT},
            "max_retries": 0,
        }
        if config.max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = config.max_completion_tokens
        if config.base_url is not None:
            kwargs["base_url"] = config.base_url
        return cls(ChatOpenAI(**kwargs), max_retries=config.max_retries)

    def extract_roles(
        self,
        title: str,
        text: str,
        targets: Sequence[PaperRoleTarget],
    ) -> PaperRoleExtractionResult:
        """Extract and validate all requested roles in one bounded call."""

        if not isinstance(title, str) or not isinstance(text, str):
            raise TypeError("paper-role title and text must be strings")
        target_values = tuple(targets)
        if not target_values:
            return PaperRoleExtractionResult(())

        prompt = _build_prompt(title, text, target_values, self._prompt)
        for attempt in range(self._max_retries + 1):
            try:
                response = self._model.invoke(prompt)
            except Exception as error:
                if not _is_retryable_output_error(error):
                    raise PaperRoleExtractionError(
                        f"Paper-role provider invocation failed: {error}"
                    ) from error
                output_error = error
            else:
                try:
                    result = _parse_result(response)
                    return validate_paper_role_result(text, target_values, result)
                except (PaperRoleValidationError, ValueError, TypeError) as error:
                    output_error = error

            if attempt >= self._max_retries:
                raise PaperRoleExtractionError(
                    "Paper-role output remained invalid after "
                    f"{attempt + 1} bounded attempt(s): {output_error}"
                ) from output_error
            prompt = _build_prompt(
                title,
                text,
                target_values,
                self._prompt,
                repair=(
                    f"The previous response failed validation: {output_error}. "
                    "Return a corrected structured response only."
                ),
            )

        raise PaperRoleExtractionError("Paper-role extraction stopped unexpectedly")


def _build_prompt(
    title: str,
    text: str,
    targets: Sequence[PaperRoleTarget],
    system_prompt: str,
    repair: str | None = None,
) -> str:
    """Build one self-contained title-plus-complete-source request."""

    prompt = (
        f"{system_prompt.strip()}\n\n"
        "Requested entities and all source mentions:\n"
        f"{json.dumps([target.to_dict() for target in targets], ensure_ascii=False, indent=2)}\n\n"
        "Paper title:\n"
        f"{title}\n\n"
        "Complete paper text supplied to the extraction pipeline:\n"
        f"{text}"
    )
    if repair:
        prompt = f"{prompt}\n\nREPAIR INSTRUCTION:\n{repair}"
    return prompt


def _bind_structured_output(model: Any) -> Any:
    """Keep Pydantic schema binding inside the provider module."""

    binder = getattr(model, "with_structured_output", None)
    if not callable(binder):
        return model
    return binder(_structured_payload_schema())


def _structured_payload_schema() -> type[Any]:
    """Create the provider-only structured role schema."""

    try:
        from pydantic import BaseModel, ConfigDict, Field, StrictStr
    except ImportError as error:  # pragma: no cover - bad installation
        raise RuntimeError("Structured paper-role extraction requires pydantic") from error

    class StructuredPaperRole(BaseModel):
        model_config = ConfigDict(extra="forbid")

        node_id: StrictStr = Field(description="Requested graph node ID")
        category: StrictStr = Field(description="substantive or contextual")
        paragraphs: list[StrictStr] = Field(
            description="One or two concise grounded paragraphs"
        )
        evidence: list[StrictStr] = Field(
            description="Exact non-empty source substrings supporting the paragraphs"
        )

    class StructuredPaperRolePayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        roles: list[StructuredPaperRole] = Field(default_factory=list)

    return StructuredPaperRolePayload


def _parse_result(response: Any) -> PaperRoleExtractionResult:
    """Convert provider/Pydantic/test-double output into local domain values."""

    payload = _response_payload(response)
    if not isinstance(payload, Mapping):
        raise PaperRoleValidationError("Structured paper-role output must be an object")
    unknown = set(payload) - {"roles"}
    if unknown:
        raise PaperRoleValidationError(
            f"Structured paper-role output has unsupported field(s): {sorted(unknown)}"
        )
    raw_roles = payload.get("roles")
    if not isinstance(raw_roles, (list, tuple)):
        raise PaperRoleValidationError("Structured paper-role roles must be a list")

    records: list[PaperRoleRecord] = []
    for index, raw_role in enumerate(raw_roles):
        mapping = _model_mapping(raw_role)
        if mapping is None:
            raise PaperRoleValidationError(
                f"Structured paper-role record at index {index} is not an object"
            )
        expected = {"node_id", "category", "paragraphs", "evidence"}
        missing = expected - set(mapping)
        extra = set(mapping) - expected
        if missing:
            raise PaperRoleValidationError(
                f"Structured paper-role record at index {index} is missing "
                f"field(s): {sorted(missing)}"
            )
        if extra:
            raise PaperRoleValidationError(
                f"Structured paper-role record at index {index} has unsupported "
                f"field(s): {sorted(extra)}"
            )
        paragraphs = mapping["paragraphs"]
        evidence = mapping["evidence"]
        if not isinstance(paragraphs, (list, tuple)) or not isinstance(
            evidence, (list, tuple)
        ):
            raise PaperRoleValidationError(
                f"Structured paper-role record at index {index} has invalid lists"
            )
        records.append(
            PaperRoleRecord(
                node_id=mapping["node_id"],
                role=PaperRole(
                    category=mapping["category"],
                    paragraphs=tuple(paragraphs),
                    evidence=tuple(evidence),
                ),
            )
        )
    return PaperRoleExtractionResult(tuple(records))


def _response_payload(response: Any) -> Any:
    """Unwrap common structured-runnable, message, and JSON responses."""

    if isinstance(response, Mapping):
        if "parsed" in response:
            if response["parsed"] is None:
                raise PaperRoleValidationError(
                    "LangChain structured paper-role output could not be parsed"
                )
            return _response_payload(response["parsed"])
        return response
    if hasattr(response, "content") and not hasattr(response, "roles"):
        return _response_payload(response.content)

    mapping = _model_mapping(response)
    if mapping is not None:
        return mapping
    if isinstance(response, (list, tuple)):
        blocks = []
        for block in response:
            if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                blocks.append(block["text"])
            elif isinstance(block, str):
                blocks.append(block)
        if blocks:
            return _response_payload("\n".join(blocks))
    if isinstance(response, str):
        candidate = response.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as error:
            raise PaperRoleValidationError(
                f"Structured paper-role output is not valid JSON: {error.msg}"
            ) from error
    raise PaperRoleValidationError(
        f"Unsupported structured paper-role response type: {type(response).__name__}"
    )


def _model_mapping(value: Any) -> Mapping[str, Any] | None:
    """Dump Pydantic/dataclass-like provider values when available."""

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
    if hasattr(value, "roles"):
        return {"roles": getattr(value, "roles")}
    return None


def _is_retryable_output_error(error: Exception) -> bool:
    """Return whether an invocation error plausibly reflects generated output."""

    if isinstance(error, (PaperRoleValidationError, json.JSONDecodeError)):
        return True
    try:
        from langchain_core.exceptions import OutputParserException
    except ImportError:  # pragma: no cover - dependency is project-required
        pass
    else:
        if isinstance(error, OutputParserException):
            return True
    try:
        from pydantic import ValidationError
    except ImportError:  # pragma: no cover - dependency is project-required
        pass
    else:
        if isinstance(error, ValidationError):
            return True
    return False


__all__ = [
    "DEFAULT_PAPER_ROLE_MODEL",
    "DEFAULT_PAPER_ROLE_REASONING_EFFORT",
    "LLMPaperRoleExtractor",
    "PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT",
    "PaperRoleExtractionError",
]
