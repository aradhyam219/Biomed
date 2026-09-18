# Biomedical Named-Entity Extraction: Current Specification

> This document contains the current product/domain truth for the extraction
> subsystem. It is not a roadmap, phase report, or history log. Replace stale
> behavior here when an accepted product decision changes it.

## Purpose

Given unstructured biomedical text, produce a clean, machine-consumable set of
core biomedical entity mentions with source spans, types, stable IDs, and model
confidence when available.

The active objective is a credible, measurable named-entity recognition (NER)
baseline. Relation extraction and biomedical entity normalization/linking are
downstream capabilities, not the current quality target.

## Active product flow

```text
biomedical text
    ↓
core biomedical NER
    ↓
NER evaluation / model selection
    ↓
future biomedical entity normalization
    ↓
STOP
```

The next entity model has not been selected. The current GLiNER-BioMed adapter is
the baseline; AIONER / PubTator-style NER and HunFlair2 are evaluation candidates,
not preselected winners. The model-independent entity interface is intentionally
preserved so those candidates can be compared or substituted behind the same
boundary.

## Scope

### Active now

- core biomedical named-entity extraction from ordinary biomedical text;
- the model-independent `EntityExtractor` / `Entity` contract;
- source-span, schema, stable-ID, and confidence validation;
- configurable core labels and entity confidence thresholds;
- NER evaluation and evidence-based model selection;
- adapter/output normalization into the stable local entity representation.

### Deferred or out of scope

Unless a later accepted task changes this specification, the active NER workstream
does not include:

- biological-process extraction, process/event nodes, or process-specific conflict
  rules; it will be treated separately if required;
- relation extraction changes, relation evaluation, or live LLM calls;
- biomedical entity normalization/linking, meaning resolution of a mention to a
  canonical biomedical identity or identifier;
- a new NER model or dependency;
- fine-tuning, a final ontology redesign, graph infrastructure, or unrelated
  platform capabilities.

Existing LLM and legacy GLiREL relation implementations remain preserved and
callable, but relation extraction is deferred until core NER passes an explicit
quality gate. Existing historical diagnostic reports remain available.

## Current entity behavior

The production entity boundary is:

```python
entities = entity_extractor.extract_entities(text)
```

When labels are omitted, the default GLiNER-BioMed path runs one model pass over
the existing core schema:

```text
gene, protein, disease, chemical, species, cell line, DNA, RNA
```

There is no default `biological process` pass and no process-over-core arbitration.
Callers may explicitly supply a custom label set through the generic adapter
contract; that does not alter the normal default schema or create a second pass.

The entity stage must:

- operate on the supplied biomedical text;
- return the detected mention text and configured type;
- preserve exact half-open character offsets into the source text;
- assign stable IDs within one extraction result;
- preserve model confidence where available; and
- keep model-specific prediction dictionaries inside the adapter.

The core schema remains bounded for this task. It must not be expanded or
redesigned before the NER evaluation and model-selection work provides evidence.

## Stable entity contract

Each returned entity contains exactly this conceptual data:

```text
id
text
type
start
end
score
```

`start` is inclusive and `end` is exclusive. The source slice
`text[start:end]` must equal the entity's `text`. `score` is optional and may be
`None` when the underlying implementation does not provide confidence.

The `EntityExtractor` boundary is model-independent. GLiNER-specific output,
loading details, and prediction dictionaries must not leak to downstream callers;
an alternative implementation must be able to return the same `Entity` values.

## Normalization terminology

Two different operations are intentionally distinguished:

- **Adapter/output normalization:** model-specific prediction → stable local
  `Entity` object. This is implemented now.
- **Biomedical entity normalization/linking:** mention → canonical biomedical
  identity or identifier. This is not implemented. It becomes active only after
  the core NER model and schema are selected and validated.

Stable local `Entity` output must not be described as biomedical identity linking.

## NER evaluation

BioRED is evaluation infrastructure, not a production dependency. The active
evaluation mode is:

```text
BioRED text
    ↓
EntityExtractor
    ↓
Predicted core entities
    ↕
BioRED gold entities
    ↓
NER quality / model selection
```

Evaluation must report the relevant coverage and span/type behavior without
silently changing, truncating, or discarding production inputs. Dataset-specific
assumptions remain in evaluation code rather than the production entity path.

The current BioRED NER evaluator accepts any implementation of
`EntityExtractor.extract_entities(text)`, maps predictor labels and BioRED gold
types through an explicit evaluation taxonomy, and reports deterministic exact
half-open-span/type micro and per-type metrics. Gene and protein predictions share
the `GeneOrGeneProduct` evaluation class. BioRED sequence variants remain a
reported schema-coverage gap because the current production schema has no explicit
variant label; DNA and RNA are not force-mapped to an unrelated gold class.

The evaluator also preserves bounded machine-readable failure examples and may
report graph-critical entity recall from BioRED relation participation without
invoking or evaluating a relation model. Its primary metrics do not use fuzzy
matching.

Relation-specific and end-to-end evaluation infrastructure is preserved as
deferred work; it is not an active acceptance target for the current NER phase.

## Quality gate and replacement seam

The next NER phase may compare the current GLiNER-BioMed baseline with AIONER /
PubTator-style NER and HunFlair2 behind the same `EntityExtractor` boundary.
These candidates are not a model-selection decision. The quality gate must be
explicitly passed using the agreed NER evaluation evidence before biomedical
entity normalization/linking or relation work becomes active.

No replacement model, dependency, training run, or linking implementation is
introduced by this specification.

## Product invariants

- Production input is ordinary biomedical text, independent of BioRED metadata.
- The active quality workstream is core biomedical NER only.
- Default extraction does not run biological-process extraction or process
  precedence logic.
- Entity and relation code may remain separately callable, but relation extraction
  is deferred until the NER quality gate.
- The `EntityExtractor` / `Entity` contract remains model-independent.
- Adapter/output normalization is distinct from biomedical identity normalization.
- Biomedical entity normalization/linking is not implemented in this task.
- Output is machine-consumable and does not require model-specific objects.
- No new model, dependency, ontology, graph, or fine-tuning path is added for this
  refocus.

## Acceptance examples

### Core NER extraction

Given text containing a gene and disease mention, the entity extractor returns
stable entity values whose spans resolve exactly to the source mentions. The
default GLiNER path makes one core-label pass.

### Model-independent replacement

An alternative NER implementation can be evaluated by satisfying
`EntityExtractor.extract_entities(text)` and returning the same stable entity
fields, without exposing its model-specific prediction format.

### Deferred downstream work

Relation implementations remain available to existing callers, but no relation
change or live provider request is required or performed before the explicit NER
quality gate.

## Related architecture

See [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## Maintenance rule

Update this file in the same task whenever an accepted change materially alters the
current product/domain behavior. Do not append phase history or preserve obsolete
behavior beside current truth; use version control or an ADR for rationale that
genuinely needs to survive.
