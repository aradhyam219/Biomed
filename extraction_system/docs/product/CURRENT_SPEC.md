# Biomedical Entity and Relation Extraction: Current Specification

> This document contains the current product/domain truth for the biomedical extraction subsystem.
> It is not a roadmap, phase report, or history log. When accepted behavior changes, replace obsolete statements with the new current truth.

## Purpose

Given unstructured biomedical text, produce a clean structured representation of:

1. biomedical entities present in the text; and
2. biomedical relationships inferred between those entities.

The result is intended to be machine-consumable by a larger system.

The immediate product objective is a credible, measurable extraction baseline rather than a claim of production-grade biomedical accuracy.

## Scope

### In scope

- biomedical named-entity extraction;
- biomedical relation extraction over detected or supplied entities;
- normalized structured output connecting relations to entity identities;
- entity and relation confidence scores where provided by the models;
- configurable entity schemas and provider-specific relation schemas where needed;
- configurable confidence thresholds;
- independent evaluation of entity extraction;
- independent evaluation of relation extraction using gold entities;
- end-to-end extraction evaluation;
- BioRED as the initial annotated evaluation sandbox;
- precision, recall, F1, and representative failure inspection where applicable.

### Out of scope

Unless a later accepted task explicitly changes this specification, the subsystem does **not** include:

- a graph database or knowledge-graph platform;
- pathway reconstruction or pathway reasoning;
- a frontend;
- PubMed/search/ingestion infrastructure;
- an entity-linking or canonical biomedical identifier platform;
- downstream recommendation or retrieval systems;
- a large speculative multi-omics ontology;
- unrelated platform refactors;
- fine-tuning performed merely because it is possible rather than because evaluation evidence justifies it.

## Current extraction behavior

The current extraction path is:

```text
Biomedical text
      ↓
EntityExtractor contract
(currently GLiNER-BioMed)
      ↓
Biomedical entities
      ↓
RelationExtractor contract
(controlled LLM path; GLiREL remains an evaluation-compatible path)
      ↓
Biomedical relations
      ↓
Normalized structured output
```

The public behavior should remain conceptually simple: one unit of biomedical text in, one normalized extraction result out.

Implementation mechanics, module boundaries, caching, loading strategy, batching, and helper structure are repository-level engineering decisions unless a later contract makes one of them externally significant.

## Entity behavior

The entity stage must:

- operate on the supplied biomedical text;
- return detected entity text and type;
- preserve location/span information needed to identify the entity occurrence;
- preserve model confidence where available;
- use a finite configured biomedical entity schema rather than attempting unrestricted ontology generation.

The entity stage exposes a small model-independent contract:

```python
entities = entity_extractor.extract_entities(text)
```

Each returned entity contains an `id`, source `text`, `type`, half-open character
offsets (`start`, `end`), and `score` when supplied by the underlying model.
GLiNER-specific prediction dictionaries remain inside the GLiNER-BioMed adapter.

The initial schema should stay bounded to the entities needed for the current extraction/evaluation work. Do not enlarge it pre-emptively to cover hypothetical future multi-omics requirements.

## Relation behavior

The relation stage must:

- operate on biomedical text together with known/detected entities;
- extract only relationships asserted by the supplied text;
- not introduce biological facts from model knowledge;
- for the initial controlled LLM path, emit a concise normalized predicate that
  faithfully describes the asserted relation without requiring a finite ontology;
- identify the directed source and target entity IDs unambiguously;
- include verbatim source-text evidence for every emitted relation;
- preserve explicit negation rather than converting a negated claim to a positive relation;
- preserve relation confidence where available;
- preserve provider-independent optional predicate restrictions for implementations
  that need them; the initial controlled LLM path does not apply one.

The relation extractor must also be usable with externally supplied/gold entities so that relation quality can be evaluated independently from entity-extraction quality.

## Normalized output contract

The result must expose entities and relations in a machine-consumable structure with equivalent semantics to:

```json
{
  "entities": [
    {
      "id": "E1",
      "text": "BRCA1",
      "type": "Gene",
      "start": 0,
      "end": 5,
      "score": 0.97
    },
    {
      "id": "E2",
      "text": "breast cancer",
      "type": "Disease",
      "start": 57,
      "end": 70,
      "score": 0.96
    }
  ],
  "relations": [
    {
      "source": "E1",
      "target": "E2",
      "predicate": "association",
      "evidence": "BRCA1 mutations are associated with breast cancer",
      "negated": false,
      "surface_form": "associated with",
      "score": 0.91
    }
  ]
}
```

The example represents the text `BRCA1 mutations are associated with an increased risk of breast cancer.`; production offsets must always reflect the actual input text.

The implementation may use typed objects internally, but it must be possible to obtain an equivalent normalized serializable representation.

The controlled relation boundary is provider-independent. LangChain/OpenAI
objects may be used by the initial LLM implementation but must not appear in
this output or be required by downstream consumers. Deterministic validation
rejects missing fields, dangling entity IDs, unsupported evidence, and malformed
relations; exact duplicate records are emitted once.
The provider-independent relation value may retain an optional score for
implementations that supply one, but the initial LLM structured-output schema
does not request or fabricate a relation confidence score.

## Confidence thresholds

Entity and relation confidence thresholds are part of the extraction configuration.

They should not be treated as arbitrary permanent constants. Where practical, thresholds should be chosen or revised using evaluation evidence, initially from BioRED development data or the closest appropriate evaluation split.

Threshold tuning must remain small and evidence-driven. It is not permission to overfit the demo set.

## BioRED's role

BioRED is an **evaluation resource**, not a production subsystem.

Production extraction must continue to work on ordinary biomedical text without BioRED annotations.

BioRED is used to provide:

- realistic biomedical text;
- human-annotated entities;
- human-annotated relationships;
- quantitative comparison against known truth;
- failure examples for deciding where future improvement effort should go.

Dataset adapters/readers must remain outside the production extraction dependency chain.

## Required evaluation modes

### 1. Entity extraction evaluation

```text
BioRED text
    ↓
Entity extractor
    ↓
Predicted entities
    ↕
BioRED gold entities
```

Purpose: measure whether the entity stage recognizes the relevant biomedical entities.

### 2. Relation extraction evaluation with gold entities

```text
BioRED text + BioRED gold entities
              ↓
       Relation extractor
              ↓
      Predicted relations
              ↕
      BioRED gold relations
```

Purpose: measure relation extraction itself without conflating its errors with upstream NER errors.

### 3. End-to-end evaluation

```text
BioRED text
    ↓
Entity extractor
    ↓
Relation extractor
    ↓
Predicted structured result
    ↕
BioRED truth
```

Purpose: measure the actual text-to-relations system.

Where the dataset/schema alignment makes the metric meaningful, report precision, recall, and F1 for the relevant evaluation unit. Also retain representative failure examples because aggregate metrics alone will not identify the responsible stage.

## Current quality strategy

The order of work is:

1. establish a working end-to-end zero-shot extraction path;
2. evaluate entity extraction independently;
3. evaluate relation extraction independently with gold entities;
4. evaluate the full pipeline;
5. inspect failures;
6. adjust only schemas, thresholds, or similarly bounded configuration when evidence supports it;
7. consider fine-tuning or more substantial model changes only after the baseline identifies a real need.

Do not fine-tune by default.

## Product invariants

- The subsystem's core product remains **biomedical text → structured entities and relations**.
- Production extraction is dataset-independent.
- BioRED remains an evaluation resource unless a later explicit product decision changes that role.
- Entity-stage and relation-stage performance must remain independently diagnosable.
- Output must remain usable by another software component without requiring model-specific internal objects.
- Improvements should target demonstrated extraction weaknesses rather than expand product scope.

## Acceptance examples

### Basic extraction

Given biomedical text containing a gene and disease relationship, the system should be able to return the detected entities and a permitted relation between them in normalized structured form when the models support that prediction.

### Relation-isolation evaluation

Given BioRED text and its gold entity annotations, the relation extractor can be evaluated against BioRED gold relations without first running the production entity extractor.

### Dataset independence

Given biomedical text that did not originate from BioRED, the production extraction path still accepts and processes it without requiring BioRED metadata.

## Related architecture

See `../ARCHITECTURE.md`.

## Maintenance rule

Codex should update this file in the same task whenever an accepted change materially alters the current product/domain behavior described here.

Do not append phase history or preserve obsolete behavior alongside current behavior. Replace stale truth. Use version control or an ADR for historical rationale when that rationale genuinely needs to survive.
