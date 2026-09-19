# Biomedical Named-Entity Extraction Architecture

> This document contains the current structural truth for the extraction subsystem.
> It is not a phase history or implementation diary. Update it in place when the
> accepted architecture changes.

## System purpose

This subsystem converts unstructured biomedical text into stable, machine-consumable
biomedical entity mentions and, on the composed prototype path, source-grounded
relations. Its active foundation is pretrained HunFlair2 NER behind the existing
model-independent entity seam, followed by the existing grounded LLM relation
implementation.

Target-domain NER evaluation and fine-tuning remain postponed. Full graph
assembly, graph serialization, visualization, and biomedical identity
normalization are also outside this architecture. A separate conservative
document-local assembly layer is available for grouping safe mention identities
without changing the mention-level contract.

## Active production flow

```text
Biomedical text
      |
      v
EntityExtractor contract
(model-independent boundary)
      |
      v
Pretrained HunFlair2 NER
(isolated runtime bridge)
      |
      v
Adapter/output normalization
(raw model prediction -> Entity)
      |
      v
Validated Entity mentions
      |
      +------------------------------+
      |                              |
      v                              v
Grounded LLM relation extraction    Document-local entity assembly
      |                              (assembled nodes + mention map)
      v
ComposedExtractionResult
      |
      v
Future biomedical entity normalization/linking
(mention -> canonical biomedical identity)
      |
      v
STOP
```

The composed prototype path returns after validated entities and grounded
relations. The separate document-local assembly function can consume the same
ordered mentions and source text when downstream graph construction needs
document-local nodes; it does not change relation endpoints or the composed
result. Biomedical entity normalization/linking is not implemented.

The postponed target-domain evaluation and adaptation path is separate from the
prototype:

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

The pilot and training lane never change the prototype path. Its gold validator
rejects incomplete data at the training boundary, preserves overlap diagnostics,
and keeps model predictions separate from human annotations. The lane is not an
active acceptance target for this prototype.

The repository also contains an evaluation-only `AIONERBioMedExtractor` and a
Test-only report command. It adapts the official AIONER PubMedBERT-CRF output to
the same `EntityExtractor` boundary, preserving exact source offsets and optional
confidence values. Its legacy TensorFlow runtime, model artifact, and prediction
cache remain isolated under `.cache/`; AIONER remains evaluation-only and does not
add a production dependency or participate in the composed path.

The repository contains a production-facing `HunFlair2BioMedExtractor` and an
isolated runtime bridge for the official `hunflair/hunflair2-ner` model. The
isolated process loads Flair, splits documents with SciSpaCy, lifts sentence-
relative spans back to the untouched source text, and preserves exposed scores.
The bridge returns plain prediction records to the existing adapter, which emits
validated `Entity` values. The Flair/SciSpaCy environment and model cache remain
under `.cache/hunflair2/`; those dependencies do not enter the main production
environment. Its released flat head supports five shared labels; the postponed
pilot still permits `SequenceVariant` gold and surfaces that incompatibility
before training instead of remapping it.

The production implementation lives in `src/biomedical_extractor/`. The
`entity_extraction` module owns the model-independent `EntityExtractor` contract
and stable `Entity` value. `hunflair2` owns the isolated-runtime bridge and
HunFlair2 output normalization. `entity_assembly` owns conservative
document-local grouping, assembled node values, and the mention-ID endpoint map.
`llm_pipeline` composes the selected entity adapter with
`llm_relation_extraction`, while `relation_extraction` owns the
provider-independent grounded relation value and validation. Raw model/provider
objects do not cross these seams. The existing GLiNER adapter and legacy
`BiomedicalExtractor` path remain available for compatibility.

### GLiNER compatibility behavior

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
The active composed path selects HunFlair2 through
`LLMExtractionPipeline.from_hunflair2()` or the
`biomedical-extract-llm --entity-backend hunflair2` option. The GLiNER-BioMed
adapter remains available for the entity-only and compatibility paths, while
AIONER / PubTator-style NER remains preserved evaluation/history evidence.
Neither the postponed pilot nor the training lane changes the composed runtime
seam.

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
so Flair does not enter the main production dependency graph; the same runner is
also used by the single-document prototype bridge.
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

## Deferred downstream work

The controlled LLM relation implementation is an active downstream capability of
the composed HunFlair2 path. It accepts only the normalized entities returned by
the entity seam and returns relations after the existing evidence, endpoint, and
negation validation. The legacy GLiREL-compatible relation/evaluation path and
its historical diagnostics remain preserved separately.

Target-domain NER evaluation, model selection, and fine-tuning remain postponed.
Full graph assembly, graph serialization, visualization, and external biomedical
normalization are not part of this path. The separate document-local assembly
layer is limited to deterministic mention grouping and endpoint mapping.

Biological-process extraction is likewise deferred and, if required later, will be
treated as a separate decision rather than added to the default core-NER pass.

## Components and ownership

| Component | Responsibility | Owns | Must not own |
|---|---|---|---|
| Entity extraction | `entity_extraction.EntityExtractor` runs the configured entity adapter on input text | Stable entity IDs, source spans/types, and model confidence | GLiNER-specific output outside the adapter, BioRED assumptions, or relation logic |
| Adapter/output normalization | Convert one model's predictions into the local `Entity` value | Span integrity, schema validation, and stable output fields | Canonical biomedical identity linking or downstream reasoning |
| Document-local entity assembly | Group safe same-document mentions and expose assembled nodes plus a mention-ID map | Deterministic node IDs, mention preservation, and type-compatible identity evidence | Biomedical normalization, cross-document identity, graph serialization, or relation rewriting |
| Biomedical entity normalization/linking | Future mention-to-identity resolution | Not implemented in the current path | Model selection before the NER quality gate |
| Relation extraction | Existing grounded LLM relation implementation over supplied normalized entities | Source-grounded relation fields, endpoint integrity, evidence, negation, and validation | Entity discovery, graph assembly, or unsupported biological inference |
| Evaluation and adaptation readiness | Measure core NER and prepare controlled target adaptation | Dataset adaptation, metrics, challenger adapters, model comparison, target-domain pilot/validator, frozen baseline, and isolated training readiness | Production extraction semantics, pseudo-gold, incomplete-gold training, or production model replacement |

## Hard architectural invariants

- Production entity extraction accepts ordinary biomedical text and does not
  require BioRED annotations.
- The `EntityExtractor` boundary remains model-independent.
- Raw model predictions do not cross the adapter boundary.
- Entity spans always refer to the original source text.
- The entity stage is core NER only; it has no biological-process pass or
  process-specific conflict rule.
- Biomedical entity normalization/linking is not implemented in this task.
- The grounded LLM relation path consumes only supplied normalized entities and
  remains evidence- and endpoint-validated.
- The official AIONER runtime and artifact remain evaluation-only and isolated from
  the production dependency graph.
- The official HunFlair2 runtime, SciSpaCy splitter, model artifact, and
  target-adaptation lane remain isolated from the main production dependency graph;
  the production-facing bridge invokes that runtime without importing it.
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
- The postponed HunFlair2 adaptation lane must not use target-paper model
  predictions, AIONER output, or model agreement as gold.
- Document-local assembly is deterministic, preserves every original mention,
  and never silently merges incompatible entity types.
- The architecture must not grow speculative ontology, full-graph, or external
  normalization infrastructure beyond the grounded relation and document-local
  assembly contracts.

## Current supported extension points

These are legitimate next steps because they belong to the active NER problem:

- core entity label/schema configuration;
- entity confidence thresholding;
- comparison or replacement of the entity model behind `EntityExtractor`;
- NER evaluation datasets and metrics that improve confidence in model selection;
- the existing isolated HunFlair2 runtime configuration and composed pipeline
  seam;
- validated target-domain gold and non-production HunFlair2 adaptation after the
  explicit human-annotation gate, when that work is resumed.

HunFlair2 is the active prototype NER foundation. No target-domain fine-tuned
model exists until the human gold gate is completed, and no target-domain
evaluation claim is made by this path.

## Documentation maintenance rule

Codex should update this file in the same task whenever an accepted implementation
materially changes the production flow, component responsibilities, stable entity
contract, architectural boundaries, or supported extension points.

Do not turn this document into a changelog. Replace obsolete architecture with the
new current state; use version control or a concise ADR for historical rationale
when it genuinely needs to survive.
