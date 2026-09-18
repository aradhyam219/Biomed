"""Build the tracked GLiNER versus AIONER BioRED Test report."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ner_comparison import build_comparison_report, render_comparison_markdown
from .ner_evaluation_cli import _write_json, _write_text


def _parser() -> argparse.ArgumentParser:
    """Build the comparison report command contract."""

    parser = argparse.ArgumentParser(
        description="Compare GLiNER and official AIONER BioRED Test reports."
    )
    parser.add_argument("--gliner", required=True, type=Path)
    parser.add_argument("--aioner", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def _load(path: Path) -> Mapping[str, Any]:
    """Load one machine-readable evaluator report."""

    return json.loads(path.read_text(encoding="utf-8"))


def _default_output(today: date | None = None) -> Path:
    """Return the tracked full-run comparison report path."""

    stamp = (today or date.today()).isoformat()
    return Path(f"reports/ner_gliner_vs_aioner_biored_test_{stamp}.json")


def main(argv: Sequence[str] | None = None) -> int:
    """Build and write JSON/Markdown comparison reports."""

    args = _parser().parse_args(argv)
    report = build_comparison_report(_load(args.gliner), _load(args.aioner))
    output_path = args.output or _default_output()
    markdown_path = args.markdown_output or output_path.with_suffix(".md")
    _write_json(output_path, report)
    _write_text(markdown_path, render_comparison_markdown(report))
    print(f"JSON report: {output_path.resolve()}")
    print(f"Markdown report: {markdown_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
