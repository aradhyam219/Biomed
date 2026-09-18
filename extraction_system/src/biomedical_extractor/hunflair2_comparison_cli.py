"""Build the tracked AIONER versus HunFlair2 BioRED Test reports."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ner_comparison import (
    build_model_comparison_report,
    render_model_comparison_markdown,
)
from .ner_evaluation_cli import _write_json, _write_text


def _parser() -> argparse.ArgumentParser:
    """Build the AIONER/HunFlair2 comparison command contract."""

    parser = argparse.ArgumentParser(
        description="Compare AIONER and official HunFlair2 BioRED Test reports."
    )
    parser.add_argument("--aioner", required=True, type=Path)
    parser.add_argument("--hunflair2", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def _load(path: Path) -> Mapping[str, Any]:
    """Load one machine-readable evaluator report."""

    return json.loads(path.read_text(encoding="utf-8"))


def _default_output(today: date | None = None) -> Path:
    """Return the tracked AIONER/HunFlair2 report path."""

    stamp = (today or date.today()).isoformat()
    return Path(f"reports/ner_aioner_vs_hunflair2_biored_test_{stamp}.json")


def main(argv: Sequence[str] | None = None) -> int:
    """Build and write the deterministic comparison reports."""

    args = _parser().parse_args(argv)
    report = build_model_comparison_report(
        _load(args.aioner),
        _load(args.hunflair2),
        first_name="AIONER",
        second_name="HunFlair2",
    )
    output_path = args.output or _default_output()
    markdown_path = args.markdown_output or output_path.with_suffix(".md")
    _write_json(output_path, report)
    _write_text(markdown_path, render_model_comparison_markdown(report))
    print(f"JSON report: {output_path.resolve()}")
    print(f"Markdown report: {markdown_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
