"""Isolated Python 3.11 Flair runtime for HunFlair2 training and smoke tests.

The main project environment intentionally has no Flair dependency.  The
repository-owned launcher delegates here using ``.cache/hunflair2/runtime``;
this file is therefore safe to import only inside that prepared environment.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Sequence

from biomedical_extractor.hunflair2_training import (
    HunFlair2TrainingConfig,
    load_training_config,
    run_gpu_training_smoke,
    run_target_training,
)
from biomedical_extractor.target_domain_pilot import sha256_file, write_json


def _parser() -> argparse.ArgumentParser:
    """Build the isolated runtime command contract."""

    parser = argparse.ArgumentParser(
        description="Run HunFlair2 training readiness smoke or explicit target training."
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--train",
        action="store_true",
        help="Explicitly run future target-domain fine-tuning on validated human gold.",
    )
    parser.add_argument("--device", choices=("cuda", "cpu"))
    parser.add_argument(
        "--smoke-checkpoint",
        type=Path,
        default=Path(".cache/hunflair2/smoke/hunflair2-smoke.pt"),
    )
    parser.add_argument(
        "--smoke-output",
        type=Path,
        default=Path("reports/hunflair2_training_smoke_2026-09-19.json"),
    )
    parser.add_argument(
        "--training-output",
        type=Path,
        default=Path(
            ".cache/hunflair2/training/target-domain/training-result.json"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a bounded smoke or an explicitly requested future training run."""

    args = _parser().parse_args(argv)
    if args.smoke and args.train:
        raise ValueError("Choose either --smoke or --train")
    config = load_training_config(args.config)
    if args.device is not None:
        config = replace(config, device=args.device)
        config.validate()
    if not args.smoke and not args.train:
        print(json.dumps({"mode": "readiness", "config": config.to_dict()}, sort_keys=True))
        return 0
    if args.smoke:
        report = run_gpu_training_smoke(config, checkpoint_path=args.smoke_checkpoint)
        write_json(args.smoke_output, report)
        print(f"Smoke report: {args.smoke_output.resolve()}")
        print(f"Smoke report SHA-256: {sha256_file(args.smoke_output)}")
        return 0
    result = run_target_training(config)
    write_json(args.training_output, result)
    print(f"Training result: {args.training_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
