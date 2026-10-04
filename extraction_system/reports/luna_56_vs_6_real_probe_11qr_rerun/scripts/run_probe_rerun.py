"""Redirect the unchanged 11Q-R harness into a fresh rerun report area.

The original harness and frozen inputs remain untouched.  This launcher changes
only the output root and preserves the original Contract 11Q-R model key.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


NEW_REPORT = Path(__file__).resolve().parents[1]
OLD_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "reports"
    / "luna_56_vs_6_real_probe_11qr"
    / "scripts"
    / "run_probe.py"
)


def load_original() -> Any:
    """Load the unchanged original harness as a module."""

    spec = importlib.util.spec_from_file_location("contract_11qr_original", OLD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load original harness: {OLD_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def configure(module: Any) -> None:
    """Redirect only output paths; retain original frozen-input/key paths."""

    module.REPORT = NEW_REPORT
    module.SCRIPT_PATH = Path(__file__).resolve()
    module.PREFLIGHT_PATH = NEW_REPORT / "preflight.json"
    module.STATE_PATH = NEW_REPORT / "probe_state.json"


def write_execution_metadata(module: Any) -> None:
    """Record the escalated execution boundary without exposing credentials."""

    preflight_path = NEW_REPORT / "preflight.json"
    preflight_sha = hashlib.sha256(preflight_path.read_bytes()).hexdigest()
    module.write_json(
        NEW_REPORT / "execution_environment.json",
        {
            "contract": "Codex Contract 11Q-R rerun",
            "provider_execution_mode": "require_escalated",
            "provider_child_processes_inherit_mode": True,
            "original_harness": "reports/luna_56_vs_6_real_probe_11qr/scripts/run_probe.py",
            "original_aborted_report": "reports/luna_56_vs_6_real_probe_11qr",
            "fresh_report": "reports/luna_56_vs_6_real_probe_11qr_rerun",
            "copied_preflight_sha256": preflight_sha,
            "model_key_path": ".cache/model_ab_11qr/model_key.json",
            "model_mapping_disclosed": False,
        },
    )


def rewrite_summary_paths(module: Any) -> None:
    """Correct report-local artifact paths after unchanged analysis completes."""

    summary_path = NEW_REPORT / "summary.json"
    if not summary_path.is_file():
        return
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifact_paths"] = {
        "preflight": "reports/luna_56_vs_6_real_probe_11qr_rerun/preflight.json",
        "per_passage": "reports/luna_56_vs_6_real_probe_11qr_rerun/passage_<001-005>/model_<a,b>.json",
        "disagreements": "reports/luna_56_vs_6_real_probe_11qr_rerun/disagreements.md",
        "shared": "reports/luna_56_vs_6_real_probe_11qr_rerun/shared.md",
        "summary": "reports/luna_56_vs_6_real_probe_11qr_rerun/summary.md",
        "summary_json": "reports/luna_56_vs_6_real_probe_11qr_rerun/summary.json",
        "execution_environment": "reports/luna_56_vs_6_real_probe_11qr_rerun/execution_environment.json",
    }
    summary["provider_execution_mode"] = "require_escalated"
    module.write_json(summary_path, summary)


def main() -> int:
    """Run the original harness with fresh output paths."""

    module = load_original()
    configure(module)
    if "--run" in sys.argv:
        write_execution_metadata(module)
    result = module.main()
    if "--run" in sys.argv or "--analyze" in sys.argv:
        rewrite_summary_paths(module)
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
