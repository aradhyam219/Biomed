# Biomedical Extractor

The active path is core biomedical named-entity recognition (NER) using the
model-independent `EntityExtractor` contract. Legacy relation implementations
remain preserved for later work; the composed HunFlair2 plus grounded LLM
relation prototype is available downstream but is not the active NER quality
target.

## Setup

With [uv](https://docs.astral.sh/uv/) available:

```powershell
uv sync
```

The first run downloads model weights. Model caches, local runtimes, and virtual environments are ignored by Git.

## Current focus

```text
biomedical text -> core biomedical NER -> NER evaluation / model selection
                 -> future biomedical entity normalization -> STOP
```

The entity-only GLiNER path runs one core-label pass, while the composed
`biomedical-extract-llm` path defaults to pretrained HunFlair2. Biological-process
extraction, biomedical identity linking, and live LLM calls are not part of the
current NER quality workstream. See [`docs/product/CURRENT_SPEC.md`](docs/product/CURRENT_SPEC.md)
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the current contracts.

## Active NER inspection

```powershell
uv run biomedical-ner --text "BRCA1 mutations are associated with breast cancer." --entity-label gene --entity-label disease
```

This entity-only command does not load GLiREL. Programmatic callers use the
model-independent entity contract:

```python
from biomedical_extractor import GLiNERBioMedExtractor

extractor = GLiNERBioMedExtractor.from_pretrained()
entities = extractor.extract_entities("BRCA1 mutations are associated with breast cancer.")
```

Each returned entity exposes `id`, `text`, `type`, half-open `start`/`end`
character offsets, and `score` when the model supplies one.

## Graph JSON viewer

The graph-ready JSON boundary has a small Cytoscape.js browser viewer. Launch it
from the repository root after setup:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --directory viewer
```

Open <http://127.0.0.1:8765/>. The viewer loads the tracked
`viewer/graph-fixture.json` smoke/demo payload through the thin
`viewer/adapter.js` layer. A future serialized `GraphResult.to_json()` payload
can enter through the same adapter without exposing model/provider internals to
the browser.

The summary distinguishes the underlying directed relation count from displayed
connections. A single relation remains a directly inspectable edge; multiple
relations with the same source and target direction become one count-labeled
bundle. Reverse-direction relations remain separate. Click a bundle to choose an
underlying predicate, then use the back control to return to the bundle list;
the relation detail view still exposes negation and every retained evidence
record. Node types use distinct shapes, selected elements focus their local
neighborhood, and pan, zoom, and node dragging are provided by Cytoscape.js.
Bundling and routing are presentation-only: the supplied graph JSON and its
scientific relations are not rewritten.

Run the focused adapter tests with:

```powershell
npm test --prefix viewer
```

## Preserved/deferred relation paths

The following relation paths are preserved and remain callable for existing
consumers, but they are not the active quality target and are not changed by the
current NER refocus.

The old interactive `demo.py` command is retained as a deferred GLiNER-to-GLiREL
relation-pipeline demo. It loads relation tooling and prints entities plus
relations; it is not the active NER demo:

```powershell
uv run python demo.py
```

For scripted use, the preserved `biomedical-extract` command remains available.
Entity/relation labels and confidence thresholds can be supplied with
`--entity-label`, `--relation-label`, `--entity-threshold`, and
`--relation-threshold`.

The LLM relation path accepts the normalized entities above and returns directed
relations with source/target IDs, a concise predicate, verbatim source evidence,
an explicit `negated` flag, and optional exact relation wording. Predicates are
normalized descriptions faithful to the source text; the initial LLM path does
not apply a finite ontology or request a confidence score. The provider-independent
relation contract can still preserve a score supplied by another implementation.
LangChain/OpenAI objects stay inside the relation harness.
The active OpenAI relation harness uses LangChain's explicit Responses API path
with `gpt-5.6-luna`, standard/default reasoning mode, `max` reasoning effort,
and a `128000` output-token ceiling. The compatibility
`BIOMEDICAL_RELATION_MAX_COMPLETION_TOKENS` setting is mapped to the Responses
API output-token field inside that provider seam.

For local configuration, copy `.env.example` to `.env` and add the key when the
live smoke is authorized. The documented command uses uv's existing env-file
support to load it; `.env` is ignored by Git. The model and bounded-repair
settings can also be configured with `BIOMEDICAL_RELATION_MODEL`,
`BIOMEDICAL_RELATION_MAX_COMPLETION_TOKENS`, and
`BIOMEDICAL_RELATION_MAX_RETRIES`.

```powershell
Copy-Item .env.example .env
```

Run relation extraction independently with supplied entity JSON:

```powershell
$entities = '[{"id":"E1","text":"BRCA1","type":"gene","start":0,"end":5},{"id":"E2","text":"breast cancer","type":"disease","start":24,"end":37}]'
uv run --env-file .env biomedical-re `
  --text "BRCA1 is associated with breast cancer." `
  --entities $entities
```

Run the composed HunFlair2 → LLM relation path:

```powershell
uv run --env-file .env biomedical-extract-llm `
  --text "BRCA1 is associated with breast cancer." `
  --device cpu
```

The compatibility GLiNER path remains available with
`--entity-backend gliner` and explicit `--entity-label` values.

Programmatic composition uses `LLMExtractionPipeline`; relation-only callers
can instantiate `LLMRelationExtractor` with their own `Entity` values. The
normal test suite uses fake model responses and never requires an API key.

## BioRED core NER evaluation

The model-independent evaluator compares any normalized `EntityExtractor` output
with BioRED gold mentions using exact half-open character spans and an explicit
taxonomy mapping. The current GLiNER-BioMed baseline can be run with:

```powershell
uv run biomedical-ner-evaluate --dataset C:\path\to\BioRED --device cpu
```

The command uses the existing default labels and threshold, reports comparable
micro/per-type metrics, keeps sequence-variant and unsupported predictor labels as
schema-coverage diagnostics, and writes JSON plus Markdown reports under
`reports/` for a full run. It does not invoke GLiREL or an LLM. See the committed
baseline report for the evaluated split and limitations.

## Preserved BioRED relation evaluation

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
