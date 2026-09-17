# V2 Entity-Extraction Foundation Report

## Review status

- Project: `C:\Projects\Biomed\extraction_system`
- Branch: `extraction_system_v2`
- Base commit: `d375133d49e98995a1b80ee4f73fd2ebce480330`
- Scope: entity extraction foundation only
- Implementation state: ready for review and handoff

This report describes the V2 entity-extraction work in this branch. It is a
tracked reviewer-facing report; no model weights, caches, virtual environments,
or generated runtime artifacts are included.

## Executive summary

The existing GLiNER-BioMed entity path was separated from the combined
GLiNER-to-GLiREL pipeline behind a small model-independent contract. Downstream
code now consumes normalized `Entity` values rather than GLiNER prediction
dictionaries. A standalone `biomedical-ner` command was added, the existing
combined pipeline was adapted to consume the same contract, and focused tests
cover conversion, source-span integrity, optional confidence, and CLI output.

The pre-existing relation and BioRED evaluation code was preserved. No relation
logic, LLM integration, graph functionality, ontology linking, or benchmarking
was added.

## Starting point and repository constraints

The branch started at the clean pre-supervised-training V2 base commit listed
above. Existing NER behavior lived in `pipeline.py` as a raw
`predict_entities(...)` model protocol inside a combined extractor that also
loaded GLiREL. The repository already used:

- `pyproject.toml` for project metadata and console scripts;
- `uv.lock` for reproducible dependency resolution;
- `uv sync` as the canonical environment setup command;
- `unittest` discovery for focused tests;
- `reports/` for tracked reviewer-visible reports;
- ignored `.cache/`, `.venv/`, `.python/`, and `.tools/` directories for local
  runtime state.

The implementation preserved those conventions and staged only paths under
`extraction_system`.

## Delivered implementation

### 1. Stable entity-extraction contract

Added `src/biomedical_extractor/entity_extraction.py` with:

- `EntityExtractor`, a small structural protocol exposing:

  ```python
  entities = entity_extractor.extract_entities(text)
  ```

- `Entity`, an immutable normalized value containing:

  ```text
  id
  text
  type
  start
  end
  score
  ```

- `Entity.to_dict()` for machine-consumable serialization.

Entity offsets are half-open character spans, so `text[start:end]` must equal
the returned entity text. Confidence is represented as `float | None` because
the contract preserves a score when the model supplies one without inventing a
score when it does not.

### 2. GLiNER-BioMed adapter

`GLiNERBioMedExtractor` now owns all GLiNER-specific concerns:

- loading the configured GLiNER-BioMed checkpoint;
- selecting CPU or CUDA when loading from pretrained;
- passing configured labels and threshold to GLiNER;
- converting raw GLiNER dictionaries to normalized `Entity` values;
- assigning deterministic `E1`, `E2`, ... IDs in prediction order;
- validating offsets, source-text correspondence, configured labels, and scores.

Raw model state and the private raw-model protocol remain inside this module.
The adapter returns tuples of normalized entities and never exposes GLiNER
prediction dictionaries to downstream callers.

Blank or whitespace-only input returns an empty tuple without invoking the
model. Invalid source spans, mismatched returned text, unsupported labels, and
invalid thresholds fail explicitly.

### 3. Combined pipeline integration

`BiomedicalExtractor` now accepts an `EntityExtractor` rather than a raw
GLiNER-shaped model. Its entity-only method delegates to the contract, while
the existing relation handoff continues to consume normalized character spans
and preserve entity IDs.

`BiomedicalExtractor.from_pretrained(...)` now constructs the
`GLiNERBioMedExtractor` adapter before loading the existing relation model. The
relation conversion, supplied-entity path, token-boundary preservation, and
BioRED gold-entity isolation remain unchanged in behavior.

The BioRED evaluator's forbidden-entity test double was updated to implement the
new contract, so the evaluator still fails loudly if production NER is invoked
accidentally.

### 4. Standalone NER execution

Added `src/biomedical_extractor/ner_cli.py` and the `biomedical-ner` project
script. It loads only the entity adapter and prints:

```json
{
  "input": "...",
  "entities": [
    {
      "id": "E1",
      "text": "BRCA1",
      "type": "gene",
      "start": 0,
      "end": 5,
      "score": 0.99
    }
  ]
}
```

It supports repeated `--entity-label`, `--entity-threshold`, and `--device`
options. It does not load GLiREL.

### 5. Public package surface

The package exports `Entity`, `EntityExtractor`,
`GLiNERBioMedExtractor`, `DEFAULT_ENTITY_LABELS`, and
`DEFAULT_ENTITY_MODEL` alongside the existing combined extractor types.

### 6. Documentation and tests

Updated:

- `README.md` with setup, programmatic use, and standalone NER invocation;
- `docs/product/CURRENT_SPEC.md` with the model-independent entity contract;
- `docs/ARCHITECTURE.md` with the adapter boundary and ownership rules;
- existing pipeline tests to inject the new contract;
- new adapter and standalone CLI tests.

## Environment and dependency decision

The canonical setup remains:

```powershell
uv sync
```

The locked environment was verified with `uv sync --locked`. The lockfile did
not require dependency changes because GLiNER's existing runtime dependencies
were already present.

Existing GLiREL-related dependencies were intentionally retained because the
pre-existing relation and BioRED evaluation modules remain in this V2 base.
They are not imported or loaded by `entity_extraction.py` or the
`biomedical-ner` command. Removing them while retaining those existing modules
would have broken the repository's current combined/evaluation paths and would
have expanded this NER task into unrelated cleanup.

The real GLiNER-BioMed checkpoint was already available in the local Hugging
Face cache for verification. That cache is outside the repository and is not
tracked. Fresh developers should expect the first model-backed invocation to
download the checkpoint; model weights are not part of Git.

## Usage

### Programmatic

```python
from biomedical_extractor import GLiNERBioMedExtractor

extractor = GLiNERBioMedExtractor.from_pretrained()
entities = extractor.extract_entities(
    "BRCA1 mutations are associated with breast cancer."
)

for entity in entities:
    print(entity.to_dict())
```

### Standalone CLI

```powershell
uv run biomedical-ner `
  --device cpu `
  --entity-label gene `
  --entity-label disease `
  --text "BRCA1 mutations are associated with breast cancer."
```

### Focused test suite

```powershell
uv run python -m unittest discover -s tests -v
```

## Verification evidence

The following checks passed for this implementation:

1. `uv sync --locked` completed successfully and installed the editable
   `biomedical-extractor` package.
2. `uv run --locked biomedical-ner --help` exposed the standalone command and
   its expected options.
3. An offline CPU real-model smoke extraction returned:

   - `E1`: `BRCA1`, type `gene`, span `[0, 5)`;
   - `E2`: `breast cancer`, type `disease`, span `[36, 49)`.

   Both returned spans mapped exactly back to the source text. The model also
   supplied confidence scores, which were preserved in the output.

4. `uv run --locked python -m unittest discover -s tests -v` passed all 29
   tests, including the existing BioRED/pipeline tests and the new entity and
   standalone CLI tests.
5. Python bytecode compilation for `src` and `tests` passed.
6. `git diff --check` passed; only expected line-ending normalization warnings
   were reported by Git on Windows.

## Focused test coverage

The new tests verify:

- raw GLiNER predictions become `Entity` values rather than leaking dictionaries;
- IDs, labels, text, spans, and optional scores are preserved;
- returned spans map exactly to the source text;
- mismatched source text is rejected;
- blank input avoids model invocation;
- invalid thresholds are rejected;
- the standalone command emits the entity-only JSON contract;
- the combined pipeline consumes a contract implementation and continues to
  preserve relation endpoint IDs and compound-token boundaries.

## Non-goals and remaining limitations

- No relation extraction behavior was designed or expanded in this task.
- No LLM, LangChain/LangGraph, graph, ontology-linking, or frontend work was
  added.
- No comparison against another NER model was performed.
- No model fine-tuning or benchmark was run.
- The default adapter is GLiNER-BioMed; replacement models need only implement
  the small `EntityExtractor` contract.
- The default checkpoint and label schema remain the existing project choices;
  threshold selection remains configuration rather than a new calibration path.

## Handoff state

The intended commit contains the implementation, focused tests, current
documentation updates, and this report. No virtual environment, model weight,
cache, secret, or generated runtime artifact is intended to be committed. The
branch is ready to be pushed for Talia's review without rewriting any existing
history.
