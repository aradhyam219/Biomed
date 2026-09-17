"""Standalone command-line entry point for biomedical entity extraction."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .entity_extraction import (
    DEFAULT_ENTITY_LABELS,
    GLiNERBioMedExtractor,
)


def _parser() -> argparse.ArgumentParser:
    """Build the entity-only inspection command."""

    parser = argparse.ArgumentParser(
        description="Extract biomedical entities from text with GLiNER-BioMed."
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Load only the entity model, run one extraction, and print JSON."""

    args = _parser().parse_args(argv)
    labels = tuple(args.entity_labels or DEFAULT_ENTITY_LABELS)
    extractor = GLiNERBioMedExtractor.from_pretrained(
        labels=labels,
        threshold=args.entity_threshold,
        device=args.device,
    )
    entities = extractor.extract_entities(args.text)
    print(
        json.dumps(
            {"input": args.text, "entities": [entity.to_dict() for entity in entities]},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
