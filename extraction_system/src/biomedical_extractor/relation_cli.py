"""Run relation extraction on source text and caller-supplied entities."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .entity_extraction import Entity
from .llm_relation_extraction import (
    DEFAULT_LLM_RELATION_MODEL,
    LLMRelationExtractor,
    OpenAIConfig,
)


def add_llm_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared provider and bounded-repair options to an LLM CLI parser."""

    parser.add_argument(
        "--model",
        default=None,
        help=(
            "OpenAI model name; defaults to BIOMEDICAL_RELATION_MODEL or "
            f"{DEFAULT_LLM_RELATION_MODEL}"
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Maximum bounded repair retries after malformed output",
    )


def openai_config_from_args(args: argparse.Namespace) -> OpenAIConfig:
    """Combine CLI overrides with non-secret environment configuration."""

    environment = OpenAIConfig.from_environment()
    return OpenAIConfig(
        model=args.model or environment.model,
        api_key_env=environment.api_key_env,
        api_key=environment.api_key,
        base_url=environment.base_url,
        reasoning_effort=environment.reasoning_effort,
        max_completion_tokens=environment.max_completion_tokens,
        max_retries=(
            environment.max_retries
            if args.max_retries is None
            else args.max_retries
        ),
    )


def _parser() -> argparse.ArgumentParser:
    """Build the independent relation-extraction command contract."""

    parser = argparse.ArgumentParser(
        description="Extract grounded relations from text and supplied entities."
    )
    parser.add_argument("--text", required=True, help="Biomedical text to process")
    parser.add_argument(
        "--entities",
        "--entities-json",
        required=True,
        dest="entities_json",
        help="JSON array of normalized entities from EntityExtractor",
    )
    add_llm_arguments(parser)
    return parser


def _parse_entities(raw_json: str) -> tuple[Entity, ...]:
    """Parse the stable entity JSON accepted by the RE-only command."""

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as error:
        raise ValueError(f"--entities must be valid JSON: {error.msg}") from error
    if not isinstance(payload, list):
        raise ValueError("--entities must be a JSON array")

    entities: list[Entity] = []
    fields = {"id", "text", "type", "start", "end", "score"}
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Entity at index {index} must be a JSON object")
        unknown = set(item) - fields
        if unknown:
            raise ValueError(
                f"Entity at index {index} has unsupported field(s): {sorted(unknown)}"
            )
        required = fields - {"score"}
        missing = required - set(item)
        if missing:
            raise ValueError(
                f"Entity at index {index} is missing field(s): {sorted(missing)}"
            )
        try:
            entities.append(Entity(**item))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid entity at index {index}: {error}") from error
    return tuple(entities)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse options, run RE on supplied entities, and print normalized JSON."""

    args = _parser().parse_args(argv)
    entities = _parse_entities(args.entities_json)
    extractor = LLMRelationExtractor.from_openai(openai_config_from_args(args))
    result = extractor.extract_relations(args.text, entities)
    print(
        json.dumps(
            {
                "input": args.text,
                "entities": [entity.to_dict() for entity in entities],
                **result.to_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through project script
    raise SystemExit(main())
