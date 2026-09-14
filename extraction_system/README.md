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
