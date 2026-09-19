"""Run the composed GLiNER-to-controlled-LLM extraction path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Sequence

from .hunflair2 import HUNFLAIR2_MODEL_IDENTIFIER
from .llm_pipeline import LLMExtractionPipeline
from .relation_cli import add_llm_arguments, openai_config_from_args


def _parser() -> argparse.ArgumentParser:
    """Build the composed LLM extraction command contract."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract biomedical entities, then grounded LLM relations using "
            "GLiNER or pretrained HunFlair2."
        )
    )
    parser.add_argument("--text", required=True, help="Biomedical text to process")
    parser.add_argument(
        "--output-format",
        choices=("composed", "graph"),
        default="composed",
        help="Structured output contract; graph emits assembled nodes and grounded edges.",
    )
    parser.add_argument(
        "--document-id",
        default="input",
        help="Stable source document ID used by graph output.",
    )
    parser.add_argument(
        "--entity-backend",
        "--ner-backend",
        choices=("gliner", "hunflair2"),
        default="gliner",
        help="Entity model backend; use hunflair2 for the active prototype path.",
    )
    parser.add_argument(
        "--entity-label",
        action="append",
        dest="entity_labels",
        help="Allowed entity label (repeatable)",
    )
    parser.add_argument("--entity-threshold", type=float, default=0.5)
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument(
        "--hunflair2-model",
        default=HUNFLAIR2_MODEL_IDENTIFIER,
        help="Pretrained HunFlair2 model identifier.",
    )
    parser.add_argument(
        "--hunflair2-runtime-python",
        type=Path,
        help="Dedicated Python executable containing Flair and SciSpaCy.",
    )
    parser.add_argument(
        "--hunflair2-runtime-script",
        type=Path,
        help="Optional isolated HunFlair2 runtime script.",
    )
    parser.add_argument(
        "--hunflair2-runtime-cache",
        type=Path,
        default=Path(".cache/hunflair2"),
        help="Ignored HunFlair2 model/runtime cache root.",
    )
    parser.add_argument(
        "--hunflair2-offline",
        action="store_true",
        help="Require the isolated HunFlair2 runtime to use cached artifacts only.",
    )
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
        entity_backend=args.entity_backend,
        hunflair2_model=args.hunflair2_model,
        hunflair2_runtime_python=args.hunflair2_runtime_python,
        hunflair2_runtime_script=args.hunflair2_runtime_script,
        hunflair2_runtime_cache=args.hunflair2_runtime_cache,
        hunflair2_offline=args.hunflair2_offline,
    )
    if args.output_format == "graph":
        print(extractor.extract_graph(args.text, document_id=args.document_id).to_json())
    else:
        result = extractor.extract(args.text)
        print(
            json.dumps(
                {"input": args.text, **result.to_dict()},
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through project script
    raise SystemExit(main())
