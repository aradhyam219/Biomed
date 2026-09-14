# Biomedical Extractor

Minimal zero-shot biomedical extraction pipeline using GLiNER-BioMed for entities and GLiREL for relations.

## Setup

With [uv](https://docs.astral.sh/uv/) available:

```powershell
uv sync
```

The first run downloads model weights. Model caches, local runtimes, and virtual environments are ignored by Git.

## Demo

```powershell
uv run python demo.py
```

Paste or type biomedical text, then enter `END` on a new line to run extraction.

For scripted use, `uv run biomedical-extract --text "..."` remains available. Entity/relation labels and confidence thresholds can be supplied with `--entity-label`, `--relation-label`, `--entity-threshold`, and `--relation-threshold`.

## BioRED relation evaluation

Download the official NCBI BioRED archive, extract it locally, and run the
gold-entity development baseline with an explicit dataset path:

```powershell
uv run biored-evaluate --dataset C:\path\to\BioRED --split dev
```

Use `--limit 1` for a real-model smoke test. Raw inference scores and the
machine-readable summary default to gitignored `.cache/` files, so later threshold
scoring reuses the same inference rather than rerunning GLiREL. See
[`docs/EVALUATION.md`](docs/EVALUATION.md) for the methodology and limitations.
The current official dev split includes one 554-token document; the full command
fails fast rather than let GLiREL silently truncate its 512-token input.
