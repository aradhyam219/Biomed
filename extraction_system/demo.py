"""Preserved interactive demo for the deferred relation pipeline.

The demo collects multiline biomedical text, runs the legacy GLiNER-to-GLiREL
flow, and presents readable tables plus normalized JSON. It remains available for
relation-tooling consumers but is not the active NER path; use ``biomedical-ner``
for current core biomedical entity inspection.
"""

from __future__ import annotations

import json
import logging
import warnings

from biomedical_extractor import BiomedicalExtractor, ExtractionConfig


SEPARATOR = "=" * 50

warnings.filterwarnings("ignore", message="`torch.jit.script` is deprecated.*")
warnings.filterwarnings("ignore", message="Using `TRANSFORMERS_CACHE` is deprecated.*")
warnings.filterwarnings(
    "ignore", message="The sentencepiece tokenizer that you are converting.*"
)
logging.getLogger("transformers").setLevel(logging.ERROR)


def read_text() -> str:
    """Read multiline input until ``END`` or end-of-file."""

    print("Paste or type biomedical text below.")
    print("Enter END on a new line when finished.\n")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def section(title: str) -> None:
    """Print a visible heading between demo output sections."""

    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}\n")


def score(value: float | None) -> str:
    """Format optional model confidence for the human-readable view."""

    return "n/a" if value is None else f"{value:.2f}"


def main() -> int:
    """Run one interactive extraction and print readable and JSON views."""

    text = read_text()
    if not text:
        print("\nNo text entered. Nothing to extract.")
        return 0

    print("\nLoading models and analyzing text...", flush=True)
    extractor = BiomedicalExtractor.from_pretrained(
        ExtractionConfig(relation_threshold=0.1)
    )
    logging.getLogger("transformers").setLevel(logging.ERROR)
    output = extractor.extract(text).to_dict()

    section("INPUT")
    print(text)

    section("ENTITIES")
    if output["entities"]:
        for entity in output["entities"]:
            print(
                f"{entity['id']:<4}  {entity['text']:<24}  "
                f"{entity['type']:<14}  {score(entity['score'])}"
            )
    else:
        print("No entities detected.")

    section("RELATIONS")
    if output["relations"]:
        entity_text = {entity["id"]: entity["text"] for entity in output["entities"]}
        for relation in output["relations"]:
            print(
                f"{entity_text[relation['source']]}  ->  {relation['type']}  ->  "
                f"{entity_text[relation['target']]}    {score(relation['score'])}"
            )
    else:
        print("No relations detected.")

    section("STRUCTURED OUTPUT")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
