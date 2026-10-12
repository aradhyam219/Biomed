"""Inspect normalized entities from the isolated pretrained HunFlair2 runtime."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections.abc import Sequence
from .hunflair2 import HunFlair2BioMedExtractor

def main(argv: Sequence[str] | None = None) -> int:
    """Run entity-only inference on ordinary biomedical text and print JSON."""
    parser = argparse.ArgumentParser(description="Extract biomedical entities with HunFlair2.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--runtime-python", type=Path)
    parser.add_argument("--runtime-cache", type=Path, default=Path(".cache/hunflair2"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    extractor = HunFlair2BioMedExtractor.from_pretrained(runtime_python=args.runtime_python, runtime_cache=args.runtime_cache, device=args.device, offline=args.offline)
    print(json.dumps({"input": args.text, "entities": [e.to_dict() for e in extractor.extract_entities(args.text)]}, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
