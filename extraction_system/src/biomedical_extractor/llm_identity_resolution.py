"""Bounded OpenAI Responses API harness for explicit identity verification.

Provider objects and structured-output parsing stay in this module. Upstream
code receives only validated, provider-independent identity decisions.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .identity_resolution import (
    ExplicitIdentityCandidate,
    ExplicitIdentityDecision,
    ExplicitIdentityResult,
    ExplicitIdentityValidationError,
    validate_explicit_identity_result,
)
from .llm_relation_extraction import (
    OpenAIConfig,
    _create_openai_chat_model,
)


EXPLICIT_IDENTITY_SYSTEM_PROMPT = """You are a conservative verifier for supplied, unresolved biomedical naming constructions.

For each candidate, answer only this question: does the complete supplied source construction explicitly introduce the parenthetical expression as a name or abbreviation for the immediately preceding long-form source phrase? Judge the source construction, not whether any supplied NER mention surface is independently synonymous with the parenthetical expression. A contained NER mention may be only a fragment of the full source phrase; that fragment status does not change what you are being asked to verify. If the construction does not clearly introduce a name or abbreviation, choose not_identity_construction or uncertain.

Use only the verbatim candidate construction and supplied mention metadata. The contained mention IDs are supplied so deterministic code can select existing, type-compatible mentions after an affirmative construction decision; do not decide which mention IDs are semantically equivalent. Do not use outside biomedical knowledge, infer abbreviation conventions, identify synonyms elsewhere in the document, infer morphology, compare unrelated mentions, create aliases, repair types, resolve cross-document identities, or merge scientifically related entities.

Return exactly one result for every candidate and no other candidate or mention IDs. The mention_ids list must contain exactly all supplied IDs for that candidate. Use only same_identity_construction, not_identity_construction, or uncertain. For same_identity_construction, copy the complete supplied source construction verbatim into evidence. For the other decisions, evidence may be empty. Do not add explanatory prose."""


class ExplicitIdentityVerificationError(RuntimeError):
    """Raised when the bounded verifier cannot return valid local decisions."""


class LLMExplicitIdentityVerifier:
    """Verify unresolved explicit constructions through a structured LLM seam."""

    def __init__(
        self,
        model: Any,
        *,
        max_retries: int = 2,
        prompt: str = EXPLICIT_IDENTITY_SYSTEM_PROMPT,
    ) -> None:
        if not callable(getattr(model, "invoke", None)) and not callable(
            getattr(model, "with_structured_output", None)
        ):
            raise TypeError(
                "Identity model must expose invoke(prompt) or "
                "with_structured_output(schema)"
            )
        if max_retries < 0:
            raise ValueError("Identity max_retries must not be negative")
        self._max_retries = max_retries
        self._prompt = prompt
        self._model = _bind_structured_output(model)
        if not callable(getattr(self._model, "invoke", None)):
            raise TypeError("Structured identity model must expose invoke(prompt)")

    @classmethod
    def from_openai(
        cls, config: OpenAIConfig | None = None
    ) -> LLMExplicitIdentityVerifier:
        """Construct the verifier using the current shared Responses API config."""

        config = config or OpenAIConfig.from_environment()
        return cls(
            _create_openai_chat_model(config),
            max_retries=config.max_retries,
        )

    def verify_explicit_identities(
        self, text: str, candidates: Sequence[ExplicitIdentityCandidate]
    ) -> ExplicitIdentityResult:
        """Return validated decisions for one batched set of local candidates."""

        if not isinstance(text, str):
            raise TypeError("Explicit identity source text must be a string")
        candidate_values = tuple(candidates)
        if not candidate_values:
            return ExplicitIdentityResult(())

        prompt = _build_prompt(candidate_values, self._prompt)
        for attempt in range(self._max_retries + 1):
            try:
                response = self._model.invoke(prompt)
            except Exception as error:
                raise ExplicitIdentityVerificationError(
                    f"Explicit identity provider invocation failed: {error}"
                ) from error
            try:
                result = _parse_result(response)
                validate_explicit_identity_result(text, candidate_values, result)
                return result
            except (ExplicitIdentityValidationError, TypeError, ValueError) as error:
                if attempt >= self._max_retries:
                    raise ExplicitIdentityVerificationError(
                        "Explicit identity output remained invalid after "
                        f"{attempt + 1} bounded attempt(s): {error}"
                    ) from error
                prompt = _build_prompt(
                    candidate_values,
                    self._prompt,
                    repair=(
                        f"The previous response failed validation: {error}. "
                        "Return a corrected complete structured response only."
                    ),
                )
        raise ExplicitIdentityVerificationError(
            "Explicit identity verification stopped unexpectedly"
        )


def _build_prompt(
    candidates: Sequence[ExplicitIdentityCandidate],
    system_prompt: str,
    repair: str | None = None,
) -> str:
    """Build a source-limited request containing only eligible constructions."""

    values = [
        {
            "candidate_id": candidate.candidate_id,
            "source_construction": candidate.construction,
            "construction_long_form": candidate.long_form,
            "parenthetical_expression": candidate.abbreviation,
            "contained_long_form_mentions": [
                {
                    "mention_id": mention.id,
                    "text": mention.text,
                    "type": mention.type,
                }
                for mention in candidate.long_form_mentions
            ],
            "parenthetical_mentions": [
                {
                    "mention_id": mention.id,
                    "text": mention.text,
                    "type": mention.type,
                }
                for mention in candidate.abbreviation_mentions
            ],
        }
        for candidate in candidates
    ]
    prompt = (
        f"{system_prompt.strip()}\n\n"
        "Unresolved explicit naming candidates from the supplied source, in source order:\n"
        f"{json.dumps(values, ensure_ascii=False, indent=2)}"
    )
    if repair:
        prompt = f"{prompt}\n\nREPAIR INSTRUCTION:\n{repair}"
    return prompt


def _bind_structured_output(model: Any) -> Any:
    """Bind the finite Pydantic response schema inside the provider harness."""

    binder = getattr(model, "with_structured_output", None)
    if not callable(binder):
        return model
    return binder(_structured_payload_schema())


def _structured_payload_schema() -> type[Any]:
    """Create the provider-only strict structured output schema."""

    try:
        from typing import Literal

        from pydantic import BaseModel, ConfigDict, Field, StrictStr
    except ImportError as error:  # pragma: no cover - exercised in bad installs
        raise RuntimeError(
            "Structured identity verification requires pydantic"
        ) from error

    class StructuredIdentityDecision(BaseModel):
        model_config = ConfigDict(extra="forbid")

        candidate_id: StrictStr = Field(description="One supplied candidate ID")
        mention_ids: list[StrictStr] = Field(
            description="Exactly the supplied mention IDs for this candidate"
        )
        decision: Literal[
            "same_identity_construction",
            "not_identity_construction",
            "uncertain",
        ] = Field(
            description="Whether the source explicitly introduces this parenthetical as a name or abbreviation"
        )
        evidence: StrictStr = Field(
            description="Complete verbatim source construction for same_identity_construction; otherwise empty"
        )

    class StructuredIdentityPayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        decisions: list[StructuredIdentityDecision] = Field(
            description="Exactly one identity decision per supplied candidate"
        )

    return StructuredIdentityPayload


def _parse_result(response: Any) -> ExplicitIdentityResult:
    """Convert provider output into the local identity result value."""

    payload = _response_payload(response)
    if not isinstance(payload, Mapping):
        raise ExplicitIdentityValidationError(
            "Structured identity output must be an object"
        )
    if set(payload) != {"decisions"}:
        raise ExplicitIdentityValidationError(
            "Structured identity output must contain only decisions"
        )
    raw_decisions = payload.get("decisions")
    if not isinstance(raw_decisions, (list, tuple)):
        raise ExplicitIdentityValidationError(
            "Structured identity decisions must be a list"
        )
    decisions: list[ExplicitIdentityDecision] = []
    for index, raw in enumerate(raw_decisions):
        if not isinstance(raw, Mapping) or set(raw) != {
            "candidate_id",
            "mention_ids",
            "decision",
            "evidence",
        }:
            raise ExplicitIdentityValidationError(
                f"Identity decision {index} has missing or unsupported fields"
            )
        candidate_id = raw["candidate_id"]
        mention_ids = raw["mention_ids"]
        decision = raw["decision"]
        evidence = raw["evidence"]
        if (
            not isinstance(candidate_id, str)
            or not isinstance(mention_ids, (list, tuple))
            or any(not isinstance(value, str) for value in mention_ids)
            or not isinstance(decision, str)
            or not isinstance(evidence, str)
        ):
            raise ExplicitIdentityValidationError(
                f"Identity decision {index} has invalid field types"
            )
        decisions.append(
            ExplicitIdentityDecision(
                candidate_id,
                tuple(mention_ids),
                decision,
                evidence,
            )
        )
    return ExplicitIdentityResult(tuple(decisions))


def _response_payload(response: Any) -> Any:
    """Read mapping, JSON string, or provider Pydantic output uniformly."""

    if isinstance(response, str):
        try:
            return json.loads(response)
        except json.JSONDecodeError as error:
            raise ExplicitIdentityValidationError(
                f"Structured identity output is not valid JSON: {error.msg}"
            ) from error
    if isinstance(response, Mapping):
        return response
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    if hasattr(response, "decisions"):
        return {"decisions": getattr(response, "decisions")}
    raise ExplicitIdentityValidationError(
        f"Unsupported structured identity response type: {type(response).__name__}"
    )


__all__ = [
    "EXPLICIT_IDENTITY_SYSTEM_PROMPT",
    "ExplicitIdentityVerificationError",
    "LLMExplicitIdentityVerifier",
]
