# Biomedical Named-Entity Extraction Architecture

> This document contains the current structural truth for the extraction subsystem.
> It is not a phase history or implementation diary. Update it in place when the
> accepted architecture changes.

## System purpose

This subsystem converts unstructured biomedical text into stable, machine-consumable
biomedical entity mentions. Its active responsibility is reliable core biomedical
named-entity recognition (NER), followed by evaluation and model selection.

Relation extraction and other downstream capabilities remain preserved in the
repository, but they are deferred until the named-entity layer passes an explicit
quality gate. They are not part of the active quality target described here.

## Active production flow

```text
Biomedical text
      |
      v
EntityExtractor contract
(model-independent boundary)
      |
      v
Core biomedical NER
(currently GLiNER-BioMed adapter)
      |
      v
Adapter/output normalization
(raw model prediction -> Entity)
      |
      v
NER evaluation / model selection
      |
      v
Future biomedical entity normalization/linking
(mention -> canonical biomedical identity)
      |
      v
STOP
```

The current production path stops after stable entity output. Biomedical entity
normalization/linking is not implemented. It becomes active only after the core
NER model and schema have been selected and validated.

The selected-development path is separate from production:

```text
canonical nine-paper target corpus
          |
          v
deterministic sentence pilot + frozen paper split
          |
          v
human-complete six-type gold
          |
          v
validated Flair/HunFlair2 fine-tuning lane
          |
          v
exact-span target test + BioRED/CRAFT regression
```

The pilot and training lane never change production defaults. Its gold validator
rejects incomplete data at the training boundary, preserves overlap diagnostics,
and keeps model predictions separate from human annotations.

The repository also contains an evaluation-only `AIONERBioMedExtractor` and a
Test-only report command. It adapts the official AIONER PubMedBERT-CRF output to
the same `EntityExtractor` boundary, preserving exact source offsets and optional
confidence values. Its legacy TensorFlow runtime, model artifact, and prediction
cache remain isolated under `.cache/`; AIONER is not the production default and
does not add a production dependency or replace GLiNER.

The repository also contains an evaluation-only `HunFlair2BioMedExtractor` and
an isolated runtime/report path. It loads the official `hunflair/hunflair2-ner`
model through Flair, splits complete documents with SciSpaCy, lifts sentence-
relative spans back to the original source text, and preserves exposed scores.
The Flair/SciSpaCy environment, model artifact, and prediction cache remain
under `.cache/hunflair2/`; HunFlair2 is not a production dependency or default
replacement. HunFlair2 is the selected base for non-production target-domain
development. Its released flat head supports five shared labels; the pilot still
permits `SequenceVariant` gold and surfaces that incompatibility before training
instead of remapping it.

The production implementation lives in `src/biomedical_extractor/`. The
`entity_extraction` module owns the model-independent `EntityExtractor` contract,
the stable `Entity` value, and the current GLiNER-BioMed adapter. Raw GLiNER
prediction dictionaries remain inside that adapter. Existing
`BiomedicalExtractor`, `relation_extraction`, `llm_relation_extraction`, and
`llm_pipeline` modules are preserved as deferred downstream paths; this refocus
does not change their behavior or invoke a live provider.

### Default GLiNER behavior

The default `GLiNERBioMedExtractor` call runs one model pass using the existing
core schema: `gene`, `protein`, `disease`, `chemical`, `species`, `cell line`,
`DNA`, and `RNA`. It normalizes those predictions into stable entities and does
not run a `biological process` pass or apply process-over-core arbitration.

Callers may still provide an explicit custom label set through the generic adapter
contract. Such calls do not change the normal/default schema or add a second pass.

## Stable entity contract

The model-independent boundary is:

```python
entities = entity_extractor.extract_entities(text)
```

Each entity contains:

```text
id, text, type, start, end, score
```

`start` and `end` are half-open character offsets into the supplied source text;
`score` is optional. Entity IDs are stable within one extraction result, and the
adapter validates that the source slice exactly matches `Entity.text`.

Alternative entity implementations must be able to satisfy this same boundary.
The GLiNER-BioMed adapter remains the production default. HunFlair2 is the
selected base for non-production target-domain development, while AIONER /
PubTator-style NER remains preserved evaluation/history evidence. Neither the
pilot nor the training lane changes the production replacement seam.

## Normalization terminology

The repository uses two distinct meanings of normalization:

- **Adapter/output normalization** converts a model-specific prediction into the
  stable local `Entity` object. This is implemented in the current adapter.
- **Biomedical entity normalization/linking** resolves a mention to a canonical
  biomedical identity or identifier. This is not implemented and is deferred
  until NER selection and validation are complete.

The second capability must not be inferred from the first, and no model-specific
prediction object crosses the `EntityExtractor` boundary.

## NER evaluation flow

BioRED remains evaluation infrastructure rather than a production dependency.
The active evaluation question is entity quality:

```text
BioRED biomedical text
          |
          v
   EntityExtractor
          |
          v
  Predicted core entities
          |
          v
  BioRED gold entities
          |
          v
 NER quality / model selection
```

Evaluation code remains separate from production extraction and must not leak
BioRED-specific input assumptions into the entity adapter.

The active implementation is `ner_evaluation.py`, which consumes normalized
`Entity` values and BioRED's parsed mentions, applies an explicit taxonomy mapping,
and computes exact-span/type metrics plus bounded failure diagnostics. The
`biomedical-ner-evaluate` command runs the current default GLiNER adapter and
writes a machine-readable report with a Markdown companion under `reports/`.
The evaluator can accept another adapter at the same `EntityExtractor` boundary;
model internals do not cross into scoring. The frozen GLiNER Test report and the
official AIONER and HunFlair2 Test reports expose shared five-class and
full-schema views, while `biomedical-ner-compare` and
`biomedical-ner-compare-aioner-hunflair2` produce deterministic head-to-head
comparisons. HunFlair2 inference is delegated to a standalone isolated runtime
so Flair does not enter the production dependency graph.
Optional graph-critical recall is derived from BioRED relation participation and
is strictly an NER diagnostic; no relation model is invoked.

Target-domain reconnaissance is a separate evaluation flow. The
`biomedical-ner-target-domain` command acquires the nine specified science-team
papers from official NCBI/PubMed/PMC sources, records full-text versus
abstract-only coverage and source checksums, runs the isolated AIONER and
HunFlair2 challengers on identical canonical text, and writes deterministic
agreement, sentence-level entity co-occurrence, and human-review artifacts under
`reports/`. It has no target gold labels and therefore cannot establish model
correctness or select a production winner. The `biomedical-ner-medmentions`
command runs an exploratory cross-schema stress test on the official MedMentions
ST21pv test split using explicit UMLS semantic-type mappings; unsupported and
ambiguous annotations remain visible in the report and are excluded from primary
metrics. The `biomedical-ner-craft` command is the primary clean independent
cross-corpus benchmark: it evaluates both challengers on all 97 official CRAFT
full-text articles, maps only Protein Ontology, ChEBI, and NCBI Taxonomy to the
current schema, validates canonical source offsets, and writes tracked JSON and
Markdown evidence. Neither flow invokes a relation model or infers relations
from entity co-occurrence.

The `biomedical-ner-target-domain-pilot` command reuses that canonical cache and
selects complete sentences from all nine papers with deterministic per-paper
hard-case, entity-rich, and general-coverage groups. It writes a tracked
machine-readable annotation template and reviewer Markdown packet with exact
canonical offsets, paper-level train/dev/test assignment, provenance checksums,
and prediction context that is never copied into gold. The
`biomedical-ner-target-domain-validate` command validates spans, types,
duplicates, completion state, provenance, and explicit overlap diagnostics. The
`biomedical-ner-hunflair2-train` launcher delegates to the prepared Flair 0.15.1
runtime: `--smoke` performs one synthetic CUDA forward/backward/update/checkpoint
cycle, while `--train` is an explicit future operation that requires complete
human gold and uses only train data for optimization, dev for selection, and test
for final evaluation.

## Deferred downstream paths

The repository still contains both the controlled LLM relation implementation and
the legacy GLiREL-compatible relation/evaluation path. They remain callable and
their historical diagnostics remain available, but relation extraction is deferred
until core NER passes an explicit quality gate. This task does not modify, debug,
evaluate, extend, or live-smoke those paths.

Biological-process extraction is likewise deferred and, if required later, will be
treated as a separate decision rather than added to the default core-NER pass.

## Components and ownership

| Component | Responsibility | Owns | Must not own |
|---|---|---|---|
| Entity extraction | `entity_extraction.EntityExtractor` runs the configured entity adapter on input text | Stable entity IDs, source spans/types, and model confidence | GLiNER-specific output outside the adapter, BioRED assumptions, or relation logic |
| Adapter/output normalization | Convert one model's predictions into the local `Entity` value | Span integrity, schema validation, and stable output fields | Canonical biomedical identity linking or downstream reasoning |
| Biomedical entity normalization/linking | Future mention-to-identity resolution | Not implemented in the current path | Model selection before the NER quality gate |
| Relation extraction (deferred) | Existing relation implementations over supplied normalized entities | Preserved downstream relation contracts | Active quality priority or changes in this refocus |
| Evaluation and adaptation readiness | Measure core NER and prepare controlled target adaptation | Dataset adaptation, metrics, challenger adapters, model comparison, target-domain pilot/validator, frozen baseline, and isolated training readiness | Production extraction semantics, pseudo-gold, incomplete-gold training, or production model replacement |

## Hard architectural invariants

- Production entity extraction accepts ordinary biomedical text and does not
  require BioRED annotations.
- The `EntityExtractor` boundary remains model-independent.
- Raw model predictions do not cross the adapter boundary.
- Entity spans always refer to the original source text.
- The default entity path is core NER only; it has no biological-process pass or
  process-specific conflict rule.
- Biomedical entity normalization/linking is not implemented in this task.
- Existing relation paths remain preserved but are outside the active workstream.
- The official AIONER runtime and artifact remain evaluation-only and isolated from
  the production dependency graph.
- The official HunFlair2 runtime, SciSpaCy splitter, model artifact, and
  target-adaptation lane remain isolated from the production dependency graph.
- Target-domain source acquisition must preserve canonical text offsets and make
  full-text/abstract-only fallback explicit; raw sources and prediction caches
  remain ignored under `.cache/`, while reviewer-facing summaries are tracked
  under `reports/`.
- Target-domain agreement and sentence co-occurrence are descriptive NER
  diagnostics only; they must not be promoted to relation extraction or target
  correctness claims.
- MedMentions remains an exploratory cross-schema stress test; its explicit UMLS
  mapping and exact source spans cannot silently enter the primary metrics or be
  presented as clean model-selection evidence.
- CRAFT is the primary clean independent cross-corpus benchmark. Its source
  release, article text, annotation manifests, exact offset checks, and isolated
  model artifact identities are recorded in the reviewer-facing report.
- The selected HunFlair2 adaptation lane is non-production and must not use
  target-paper model predictions, AIONER output, or model agreement as gold.
- The architecture must not grow speculative ontology, graph, relation, or model
  infrastructure before the NER quality gate.

## Current supported extension points

These are legitimate next steps because they belong to the active NER problem:

- core entity label/schema configuration;
- entity confidence thresholding;
- comparison or replacement of the entity model behind `EntityExtractor`;
- NER evaluation datasets and metrics that improve confidence in model selection;
- validated target-domain gold and non-production HunFlair2 adaptation after the
  explicit human-annotation gate.

HunFlair2 is selected for this development lane only. It is not the production
default, and no target-domain fine-tuned model exists until the human gold gate is
completed.

## Documentation maintenance rule

Codex should update this file in the same task whenever an accepted implementation
materially changes the production flow, component responsibilities, stable entity
contract, architectural boundaries, or supported extension points.

Do not turn this document into a changelog. Replace obsolete architecture with the
new current state; use version control or a concise ADR for historical rationale
when it genuinely needs to survive.
