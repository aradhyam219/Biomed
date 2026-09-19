"""Launch the isolated HunFlair2 Flair training runtime."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence


def _parser() -> argparse.ArgumentParser:
    """Build the main-environment launcher contract."""

    parser = argparse.ArgumentParser(
        description="Launch HunFlair2 training or the bounded GPU smoke test."
    )
    parser.add_argument("--runtime-python", type=Path)
    parser.add_argument("--runtime-script", type=Path)
    return parser


def _runtime_python(explicit: Path | None) -> Path:
    """Resolve the prepared Linux or Windows isolated runtime."""

    candidates = (
        explicit,
        Path(".cache/hunflair2/runtime/bin/python"),
        Path(".cache/hunflair2/runtime/Scripts/python.exe"),
    )
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "HunFlair2 runtime Python not found; expected "
        ".cache/hunflair2/runtime/bin/python"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Delegate arguments to the isolated Python 3.11 runtime."""

    args, remainder = _parser().parse_known_args(argv)
    # Do not resolve the virtualenv's bin/python symlink; the target interpreter
    # alone does not activate the runtime site-packages.
    runtime_python = _runtime_python(args.runtime_python)
    runtime_script = (
        args.runtime_script or Path("src/biomedical_extractor/hunflair2_training_runtime.py")
    ).resolve()
    source_root = str(Path("src").resolve())
    environment = os.environ.copy()
    runtime_cache = Path(".cache/hunflair2").resolve()
    environment.update(
        {
            "FLAIR_CACHE_ROOT": str(runtime_cache / "flair"),
            "HF_HOME": str(runtime_cache / "huggingface"),
            "TRANSFORMERS_CACHE": str(runtime_cache / "huggingface"),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_root
        if not existing_pythonpath
        else source_root + os.pathsep + existing_pythonpath
    )
    command = [str(runtime_python), str(runtime_script), *remainder]
    result = subprocess.run(command, env=environment, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
