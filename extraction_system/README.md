# Biomedical Extractor

Minimal biomedical extraction pipeline using GLiNER-BioMed for entities, a
controlled OpenAI/LLM relation path, and the preserved GLiREL evaluation path.

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

## Entity-only inspection

NER can be run without loading GLiREL:

```powershell
uv run biomedical-ner --text "BRCA1 mutations are associated with breast cancer." --entity-label gene --entity-label disease
```

Programmatic callers use the model-independent entity contract:

```python
from biomedical_extractor import GLiNERBioMedExtractor

extractor = GLiNERBioMedExtractor.from_pretrained()
entities = extractor.extract_entities("BRCA1 mutations are associated with breast cancer.")
```

Each returned entity exposes `id`, `text`, `type`, half-open `start`/`end`
character offsets, and `score` when the model supplies one.

## Controlled LLM relation extraction

The LLM relation path accepts the normalized entities above and returns directed
relations with source/target IDs, a concise predicate, verbatim source evidence,
an explicit `negated` flag, and optional exact relation wording or score. The
LangChain/OpenAI objects stay inside the relation harness. Set `OPENAI_API_KEY`
in the process environment; model and bounded-repair settings can also be
configured with `BIOMEDICAL_RELATION_MODEL`, `BIOMEDICAL_RELATION_MAX_TOKENS`,
and `BIOMEDICAL_RELATION_MAX_RETRIES`.

Run relation extraction independently with supplied entity JSON:

```powershell
$entities = '[{"id":"E1","text":"BRCA1","type":"gene","start":0,"end":5},{"id":"E2","text":"breast cancer","type":"disease","start":24,"end":37}]'
uv run biomedical-re `
  --text "BRCA1 is associated with breast cancer." `
  --entities $entities `
  --predicate association
```

Run the composed GLiNER → LLM relation path:

```powershell
uv run biomedical-extract-llm `
  --text "BRCA1 is associated with breast cancer." `
  --entity-label gene `
  --entity-label disease `
  --predicate association `
  --device cpu
```

Programmatic composition uses `LLMExtractionPipeline`; relation-only callers
can instantiate `LLMRelationExtractor` with their own `Entity` values. The
normal test suite uses fake model responses and never requires an API key.

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
