"""Run the composed GLiNER-to-controlled-LLM extraction path."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .llm_pipeline import LLMExtractionPipeline
from .relation_cli import add_llm_arguments, openai_config_from_args


def _parser() -> argparse.ArgumentParser:
    """Build the composed LLM extraction command contract."""

    parser = argparse.ArgumentParser(
        description="Extract biomedical entities, then grounded LLM relations."
    )
    parser.add_argument("--text", required=True, help="Biomedical text to process")
    parser.add_argument(
        "--entity-label",
        action="append",
        dest="entity_labels",
        help="Allowed entity label (repeatable)",
    )
    parser.add_argument("--entity-threshold", type=float, default=0.5)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    add_llm_arguments(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse options, run NER followed by LLM RE, and print JSON."""

    args = _parser().parse_args(argv)
    entity_labels = tuple(args.entity_labels) if args.entity_labels else None
    extractor = LLMExtractionPipeline.from_pretrained(
        entity_labels=entity_labels,
        entity_threshold=args.entity_threshold,
        device=args.device,
        llm_config=openai_config_from_args(args),
    )
    result = extractor.extract(args.text)
    print(json.dumps({"input": args.text, **result.to_dict()}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through project script
    raise SystemExit(main())
