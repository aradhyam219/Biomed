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
The next model has not been selected. Current evaluation candidates include the
GLiNER-BioMed baseline, AIONER / PubTator-style NER, and HunFlair2; these are
comparison candidates, not a preselected winner.

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
| Evaluation | Measure core NER against annotated data | Dataset adaptation, metrics, and model comparison | Production extraction semantics or model training |

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
- The architecture must not grow speculative ontology, graph, relation, or model
  infrastructure before the NER quality gate.

## Current supported extension points

These are legitimate next steps because they belong to the active NER problem:

- core entity label/schema configuration;
- entity confidence thresholding;
- comparison or replacement of the entity model behind `EntityExtractor`;
- NER evaluation datasets and metrics that improve confidence in model selection.

The current candidates are evaluation inputs only. No replacement model,
dependency, fine-tuning path, or biomedical linking implementation is selected by
this architecture.

## Documentation maintenance rule

Codex should update this file in the same task whenever an accepted implementation
materially changes the production flow, component responsibilities, stable entity
contract, architectural boundaries, or supported extension points.

Do not turn this document into a changelog. Replace obsolete architecture with the
new current state; use version control or a concise ADR for historical rationale
when it genuinely needs to survive.
