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
EntityExtractor contract
(currently GLiNER-BioMed adapter)
      |
      v
Normalized biomedical entities
      |
      v
RelationExtractor contract
(controlled LLM path; GLiREL compatibility path remains available)
      |
      v
Normalized structured result
(entities + relations + confidence)
```

The model choices above describe the current architecture and are not permanent architectural requirements. If a later accepted task replaces or augments them, this document should be updated to the new current truth.

The production implementation lives in `src/biomedical_extractor/`. The
`entity_extraction` module owns the model-independent `EntityExtractor` contract,
normalized `Entity` value, and GLiNER-BioMed adapter. `BiomedicalExtractor`
exposes entity-only, relation-with-supplied-entities, and composed end-to-end
extraction for the existing GLiREL path. `relation_extraction` owns the
provider-independent grounded relation contract and deterministic validation;
`llm_relation_extraction` owns the LangChain/OpenAI harness; and
`llm_pipeline.LLMExtractionPipeline` composes the existing NER contract with
that LLM relation contract. The CLIs are developer boundaries; they do not add
an API or service layer.

### Entity-to-relation handoff

The entity contract returns half-open character spans. The pipeline tokenizes
source text with GLiREL's token pattern, requires every entity character span to
align with those token boundaries, and sends inclusive token spans to GLiREL.
GLiREL returns half-open token spans; the pipeline resolves those spans back to
the existing normalized entity IDs and preserves head-to-tail direction as
source-to-target direction.

Invalid offsets, schema labels, duplicate token spans, or relation references are rejected rather than silently remapped.

The controlled LLM handoff sends the original text and serialized normalized
entities to `RelationExtractor`. The harness requires structured relation
fields, then the local validator checks supplied endpoint IDs, concise
predicates, verbatim evidence and optional surface forms before returning
relations. The initial LLM path does not apply a finite predicate ontology;
other provider implementations may use the contract's optional predicate
restriction. It preserves direction and explicit negation; it does not attempt
to decide biological truth or request a confidence score from the LLM.

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
| Entity extraction | `entity_extraction.EntityExtractor` runs the configured entity adapter on input text | Normalized entity IDs, character spans/types, entity confidence | GLiNER-specific output outside the adapter, BioRED-specific evaluation logic, or downstream platform behavior |
| Relation extraction | `relation_extraction.RelationExtractor` runs a configured implementation over supplied normalized entities | Directed endpoint IDs, concise predicates, source evidence, negation, and optional confidence | Entity discovery, biological truth adjudication, downstream graph construction, dataset-specific production assumptions |
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
      "predicate": "association",
      "evidence": "BRCA1 is associated with breast cancer",
      "negated": false,
      "surface_form": "associated with",
      "score": 0.91
    }
  ]
}
```

The exact code representation may follow repository conventions, but these semantics must remain clear:

- relations reference normalized entity identities;
- entity and relation predicates are explicit;
- every controlled-LLM relation carries verbatim source evidence and an explicit negation state;
- confidence is preserved where the underlying model supplies it;
- output is machine-consumable and independent of the evaluation dataset.

If the public/internal result contract is intentionally changed later, update this section and the product specification in the same task.

The entity-only contract is:

```python
entities = entity_extractor.extract_entities(text)
```

It returns normalized entities with `id`, `text`, `type`, half-open `start` and
`end` offsets, and optional `score`. The current implementation is
`GLiNERBioMedExtractor`; its raw GLiNER dictionaries do not cross this boundary.

The controlled relation contract is:

```python
result = relation_extractor.extract_relations(text, entities)
```

Each relation contains `source`, `target`, `predicate`, verbatim `evidence`,
boolean `negated`, and optional `surface_form` and `score`. The relation
contract is provider-independent; LangChain and OpenAI objects remain inside
the LLM harness. The initial LLM schema omits `score`; the provider-independent
field remains available for implementations that supply calibrated confidence.
The preserved `BiomedicalExtractor`/GLiREL path continues to serve the existing
GLiREL-compatible extraction and BioRED evaluation code.

## Hard invariants

- BioRED evaluation code must remain separable from production extraction.
- A failure in entity extraction must be distinguishable from a failure in relation extraction through independent evaluation.
- Production behavior must not require BioRED gold annotations.
- No relation may reference an entity ID outside the supplied normalized entity set.
- Relation evidence must occur verbatim in the supplied source text.
- Provider-specific objects and unbounded retries must not cross the relation boundary.
- The subsystem must not silently absorb downstream responsibilities merely because extracted relations may later be used by those systems.
- Architecture should remain no more complex than needed for the current extraction requirements.

## Current supported extension points

These are legitimate areas of later evolution because they belong to the extraction problem itself:

- entity label/schema configuration;
- provider-specific relation label/schema configuration when an implementation
  requires it; the initial controlled LLM path intentionally has no finite
  predicate ontology;
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
