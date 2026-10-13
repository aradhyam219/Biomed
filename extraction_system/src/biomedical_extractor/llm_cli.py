"""Run the composed HunFlair2-to-controlled-LLM extraction path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Sequence

from .graph_contract import export_graph, graph_json, input_fingerprints, release_context, _document_id
from .graph_profile import check_graph_options, prepare_graph_export, verify_graph_profile
from .hunflair2 import HUNFLAIR2_MODEL_IDENTIFIER
from .llm_pipeline import LLMExtractionPipeline
from .relation_cli import add_llm_arguments, openai_config_from_args


def _parser() -> argparse.ArgumentParser:
    """Build the composed LLM extraction command contract."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract biomedical entities, then grounded LLM relations using "
            "pretrained HunFlair2."
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
        choices=("hunflair2",),
        default="hunflair2",
        help=(
            "Entity model backend; defaults to pretrained HunFlair2. "
        ),
    )
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
    parser.add_argument("--paper-title", default="", help="Exact title supplied to paper roles and fingerprinting.")
    add_llm_arguments(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse options, run NER followed by LLM RE, and print JSON."""

    args = _parser().parse_args(argv)
    config = openai_config_from_args(args)
    context = None
    if args.output_format == "graph":
        input_fingerprints(args.text, args.paper_title)
        _document_id(args.document_id)
        context = release_context()
        check_graph_options(config, model=args.hunflair2_model, device=args.device,
                            runtime_script=args.hunflair2_runtime_script)
    extractor = LLMExtractionPipeline.from_pretrained(
        device=args.device,
        llm_config=config,
        entity_backend=args.entity_backend,
        hunflair2_model=args.hunflair2_model,
        hunflair2_runtime_python=args.hunflair2_runtime_python,
        hunflair2_runtime_script=args.hunflair2_runtime_script,
        hunflair2_runtime_cache=args.hunflair2_runtime_cache,
        hunflair2_offline=args.hunflair2_offline,
    )
    if args.output_format == "graph":
        context = prepare_graph_export(extractor, text=args.text, document_id=args.document_id,
                                       paper_title=args.paper_title, context=context)
        graph = extractor.extract_graph(args.text, document_id=args.document_id, paper_title=args.paper_title)
        verify_graph_profile(extractor, context, text=args.text)
        print(graph_json(export_graph(graph, text=args.text, paper_title=args.paper_title, context=context)))
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
