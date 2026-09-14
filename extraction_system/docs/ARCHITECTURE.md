# Biomedical Entity and Relation Extraction Architecture

> This document contains the current structural truth for the extraction subsystem.
> It is not a phase history or implementation diary. Codex should update it in place whenever later work materially changes the architecture.

## System purpose

This subsystem converts unstructured biomedical text into structured biomedical entities and relationships that can be consumed by a larger system.

Its responsibility ends at reliable extraction and normalization. Downstream knowledge-graph construction, pathway reasoning, retrieval systems, user interfaces, and other platform capabilities are outside the current subsystem boundary unless a later product change explicitly brings them into scope.

## Current production flow

```text
Biomedical text
      |
      v
Entity extraction
(currently GLiNER-BioMed)
      |
      v
Normalized biomedical entities
      |
      v
Relation extraction
(currently GLiREL)
      |
      v
Normalized structured result
(entities + relations + confidence)
```

The model choices above describe the current architecture and are not permanent architectural requirements. If a later accepted task replaces or augments them, this document should be updated to the new current truth.

The production implementation lives in `src/biomedical_extractor/`. `BiomedicalExtractor` exposes entity-only, relation-with-supplied-entities, and composed end-to-end extraction. The CLI in `biomedical_extractor.cli` is the demonstration boundary; it does not add an API or service layer.

### Entity-to-relation handoff

GLiNER returns character spans. The pipeline tokenizes source text with GLiREL's token pattern, requires every entity character span to align with those token boundaries, and sends inclusive token spans to GLiREL. GLiREL returns half-open token spans; the pipeline resolves those spans back to the existing normalized entity IDs and preserves head-to-tail direction as source-to-target direction.

Invalid offsets, schema labels, duplicate token spans, or relation references are rejected rather than silently remapped.

## Current evaluation flow

BioRED is used as annotated evaluation data. It is not part of the production runtime path.

```text
                         BioRED
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
   Entity evaluation   Relation eval.   End-to-end eval.
                       with gold
                       entities
          |                |                |
          v                v                v
   NER quality         RE quality       Full-pipeline quality
```

The three evaluation modes answer different questions:

1. **Entity extraction evaluation**
   - BioRED text is passed through the entity extractor.
   - Predicted entities are compared with BioRED gold entities.
   - Purpose: measure the entity stage independently.

2. **Relation extraction with gold entities**
   - BioRED text and BioRED human-annotated entities are given to the relation extractor.
   - Predicted relations are compared with BioRED gold relations.
   - Purpose: isolate relation-extraction quality from upstream entity errors.
   - `biomedical_extractor.biored` owns deterministic BioC parsing, normalized
     concept aggregation, threshold selection, and scoring.
   - `biomedical_extractor.biored_cli` owns the GLiREL-only evaluation command and
     incremental raw-score cache; it never loads GLiNER.

3. **End-to-end evaluation**
   - BioRED text passes through the complete production extraction path.
   - Predicted entities/relations are compared with BioRED truth.
   - Purpose: measure the behavior of the component as it will actually be used.

## Components and ownership

| Component | Responsibility | Owns | Must not own |
|---|---|---|---|
| Entity extraction | `BiomedicalExtractor.extract_entities` runs GLiNER-BioMed on input text | Entity predictions, character spans/types, entity confidence | BioRED-specific evaluation logic or downstream platform behavior |
| Relation extraction | `BiomedicalExtractor.extract_relations` runs GLiREL over supplied normalized entities | Relation predictions and relation confidence | Entity discovery, downstream graph construction, dataset-specific production assumptions |
| Normalization / pipeline boundary | `BiomedicalExtractor.extract` composes both stages into one serializable result | Stable result structure, token-span conversion, and entity/relation linkage | Biomedical knowledge-graph persistence or downstream reasoning |
| Evaluation | Measure extraction behavior against annotated data | BioRED loading/adaptation, gold-mention inference orchestration, concept aggregation, cached scores, metrics, failure examples | Production extraction semantics or model training |

The module names and paths above reflect the current repository and should change only when the implementation changes.

Runtime dependency compatibility is captured in `pyproject.toml` and locked in `uv.lock`. GLiREL's undeclared `loguru` and DeBERTa tokenizer `protobuf` requirements are explicit project dependencies; no runtime monkey patching is used.

## Stable contracts

### Production input

The production extractor accepts unstructured biomedical text.

BioRED annotation objects, PubMed-specific records, or dataset-specific structures are not required production inputs.

### Normalized output

The externally useful result contains two collections:

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
    }
  ],
  "relations": [
    {
      "source": "E1",
      "target": "E2",
      "type": "Association",
      "score": 0.91
    }
  ]
}
```

The exact code representation may follow repository conventions, but these semantics must remain clear:

- relations reference normalized entity identities;
- entity and relation types are explicit;
- confidence is preserved where the underlying model supplies it;
- output is machine-consumable and independent of the evaluation dataset.

If the public/internal result contract is intentionally changed later, update this section and the product specification in the same task.

## Hard invariants

- BioRED evaluation code must remain separable from production extraction.
- A failure in entity extraction must be distinguishable from a failure in relation extraction through independent evaluation.
- Production behavior must not require BioRED gold annotations.
- The subsystem must not silently absorb downstream responsibilities merely because extracted relations may later be used by those systems.
- Architecture should remain no more complex than needed for the current extraction requirements.

## Current supported extension points

These are legitimate areas of later evolution because they belong to the extraction problem itself:

- entity label/schema configuration;
- relation label/schema configuration;
- entity confidence thresholding;
- relation confidence thresholding;
- model replacement, tuning, or fine-tuning when evaluation evidence justifies it;
- evaluation datasets/metrics that improve confidence in extraction quality without coupling them to production.

These are extension points, not commitments to build additional abstraction around them now.

## Documentation maintenance rule

Codex is authorized and expected to maintain this file as architecture evolves.

When a later implementation task materially changes:

- the production flow;
- component responsibilities;
- major data/control flow;
- stable input/output contracts;
- architectural boundaries;
- supported extension points; or
- dependencies between production and evaluation components,

Codex should update this file **in the same task**.

Do not require a new architecture document from Talia for each phase. Preserve this file as the living source of current architectural truth.

Do not turn it into a changelog. Replace obsolete architecture with the new current state. Use version control, or a concise ADR when truly warranted, for historical rationale.
