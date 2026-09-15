"""Command-line entry point for production biomedical extraction.

The command turns one text argument into the pipeline's normalized JSON entity and
relation payload, loading the configured GLiNER and GLiREL checkpoints on demand.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .pipeline import (
    DEFAULT_ENTITY_LABELS,
    DEFAULT_RELATION_LABELS,
    BiomedicalExtractor,
    ExtractionConfig,
)


def _parser() -> argparse.ArgumentParser:
    """Build the production extraction command-line contract."""

    parser = argparse.ArgumentParser(
        description="Extract biomedical entities and relations from text."
    )
    parser.add_argument("--text", required=True, help="Biomedical text to process")
    parser.add_argument(
        "--entity-label",
        action="append",
        dest="entity_labels",
        help="Allowed entity label (repeatable)",
    )
    parser.add_argument(
        "--relation-label",
        action="append",
        dest="relation_labels",
        help="Allowed relation label (repeatable)",
    )
    parser.add_argument("--entity-threshold", type=float, default=0.5)
    parser.add_argument("--relation-threshold", type=float, default=0.5)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI options, run one extraction, and print normalized JSON."""

    args = _parser().parse_args(argv)
    config = ExtractionConfig(
        entity_labels=tuple(args.entity_labels or DEFAULT_ENTITY_LABELS),
        relation_labels=tuple(args.relation_labels or DEFAULT_RELATION_LABELS),
        entity_threshold=args.entity_threshold,
        relation_threshold=args.relation_threshold,
        device=args.device,
    )
    extractor = BiomedicalExtractor.from_pretrained(config)
    result = extractor.extract(args.text)
    print(json.dumps({"input": args.text, **result.to_dict()}, indent=2))
    return 0
