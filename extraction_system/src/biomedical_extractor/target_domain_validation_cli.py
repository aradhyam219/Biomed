"""Validate a target-domain annotation package before any training run."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .ner_reconnaissance import load_target_corpus
from .target_domain_pilot import (
    load_annotation_package,
    validate_annotation_package,
)


def _parser() -> argparse.ArgumentParser:
    """Build the validator command contract."""

    parser = argparse.ArgumentParser(description="Validate target-domain NER gold JSON.")
    parser.add_argument(
        "package",
        type=Path,
        nargs="?",
        default=Path("reports/target_domain_pilot_2026-09-19.json"),
    )
    parser.add_argument("--canonical-corpus", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the package and print overlap/incompleteness accounting."""

    args = _parser().parse_args(argv)
    package = load_annotation_package(args.package)
    canonical = None
    if args.canonical_corpus is not None:
        canonical = load_target_corpus(args.canonical_corpus)
    summary = validate_annotation_package(
        package,
        canonical_papers=canonical,
        require_complete=args.require_complete,
    )
    import json

    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
