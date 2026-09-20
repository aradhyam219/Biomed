# Biomedical Named-Entity Extraction: Current Specification

> This document contains the current product/domain truth for the extraction
> subsystem. It is not a roadmap, phase report, or history log. Replace stale
> behavior here when an accepted product decision changes it.

## Purpose

Given unstructured biomedical text, produce a clean, machine-consumable set of
core biomedical entity mentions with source spans, types, stable IDs, and model
confidence when available. A separate conservative transformation assembles safe
mentions into document-local entities, and the composed prototype can expose
those nodes with grounded relations as deterministic graph-ready JSON.

The active prototype uses pretrained HunFlair2 for NER and the existing grounded
LLM relation extractor downstream. Target-domain NER evaluation and fine-tuning
remain postponed; biomedical entity normalization/linking remains a later stage.

## Active product flow

```text
biomedical text
    ↓
isolated pretrained HunFlair2 runtime
    ↓
validated Entity mentions
    ├──────────────→ grounded LLM relation extraction ───┐
    │                                                     │
    └──────────────→ document-local entity assembly ──────┤
                       (assembled nodes + mention map)   ↓
                                      graph-ready result / JSON
```

The graph-ready result can be inspected in the tracked plain browser viewer:

```text
GraphResult / graph JSON
        ↓
thin viewer adapter
        ↓
Cytoscape.js
        ↓
interactive evidence-backed graph
```

The model-independent `EntityExtractor` seam remains the stable NER boundary.
HunFlair2 is the active prototype foundation through its isolated runtime bridge;
the existing GLiNER adapter remains available for compatibility and evaluation.
AIONER / PubTator-style NER remains preserved as evaluation/history evidence.

## Scope

### Active now

- core biomedical named-entity extraction from ordinary biomedical text;
- the pretrained HunFlair2 single-document runtime bridge;
- the model-independent `EntityExtractor` / `Entity` contract;
- source-span, schema, stable-ID, and confidence validation;
- the existing grounded LLM relation extractor over supplied entities;
- NER evaluation artifacts as preserved evidence, without reopening target-domain
  model selection;
- adapter/output normalization into the stable local entity representation;
- conservative document-local assembly with deterministic IDs, preserved
  mentions, and a complete mention-to-assembled-entity map;
- a frontend-neutral graph-ready JSON boundary that remaps grounded relation
  endpoints to assembled node IDs, preserves direction, negation, and evidence,
  and deterministically aggregates equivalent edges;
- a thin Cytoscape.js viewer that consumes graph JSON without provider coupling,
  shows typed nodes and directed predicates, and exposes aliases, source
  mentions, negation, and every retained evidence record through selection;
- a frozen, evaluation-only comparison of the current GLiNER baseline with the
  official AIONER PubMedBERT-CRF artifact on the official BioRED Test split;
- a frozen, evaluation-only challenger run of the official HunFlair2 five-class
  model on that same BioRED Test split, compared with AIONER without changing
  the main runtime dependency graph.
- an exploratory exact-span MedMentions ST21pv cross-schema stress test with an
  explicit UMLS semantic-type mapping to the shared ChemicalEntity and
  DiseaseOrPhenotypicFeature classes, including unsupported/ambiguous counts,
  failure categories, and a descriptive BioRED comparison;
- the primary clean independent CRAFT v5.0.2 full-text benchmark, evaluating
  AIONER and HunFlair2 on identical canonical article text while scoring only
  Protein Ontology, ChEBI, and NCBI Taxonomy mappings to the current schema.

### Deferred or out of scope

Unless a later accepted task changes this specification, the active prototype does
not include:

- biological-process extraction, process/event nodes, or process-specific conflict
  rules; it will be treated separately if required;
- target-domain NER evaluation, model selection, or fine-tuning; the existing
  reconnaissance, pilot, validator, and training-readiness assets remain
  preserved for later use;
- relation-model quality evaluation or live external-provider smoke beyond the
  existing grounded extraction seam;
- biomedical entity normalization/linking, meaning resolution of a mention to a
  canonical biomedical identity or identifier;
- collapsing the isolated HunFlair2 runtime into the production dependency graph;
- general or inferred alias resolution, cross-document identity, or external
  biomedical normalization;
- a final ontology redesign, graph infrastructure, or unrelated platform
  capabilities.

The existing LLM relation path is an active downstream capability only when
called through the composed pipeline. Legacy GLiREL relation implementations and
historical diagnostic reports remain preserved separately.

## Current entity behavior

The entity boundary used by both the entity-only and composed paths is:

```python
entities = entity_extractor.extract_entities(text)
```

The active composed prototype is constructed with
`LLMExtractionPipeline.from_pretrained()` (which defaults to HunFlair2), with
the `LLMExtractionPipeline.from_hunflair2()` convenience factory, or with
`biomedical-extract-llm` (which also defaults to HunFlair2). It runs the
isolated pretrained HunFlair2 model over the supplied document and passes the
normalized entities directly to the existing grounded relation extractor.
HunFlair2's official labels are retained unchanged in `Entity.type`.

The existing GLiNER-BioMed path remains available for compatibility and runs one
model pass over its core schema when selected:

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

The `EntityExtractor` boundary is model-independent. Model-specific output,
loading details, and prediction dictionaries must not leak to downstream callers;
an alternative implementation must be able to return the same `Entity` values.

## Document-local entity assembly

The production package also exposes `assemble_document_entities(entities, text)`
as a separate transformation over an ordered mention result. It returns
document-local entities and a deterministic map from every original mention ID
to exactly one assembled entity ID. It does not change `Entity` or rewrite
grounded relation endpoints. `LLMExtractionPipeline.extract_graph()` is the
explicit orchestration seam that combines this assembly result with grounded
relations through the graph boundary.

The identity rules are intentionally conservative:

- repeated mentions merge only after superficial whitespace/case normalization
  and compatible type comparison;
- a full-form mention and abbreviation merge only for an unambiguous source
  pattern of the form `full form (ABBR)` with compatible types;
- incompatible types, unsupported alias patterns, and uncertain candidates stay
  separate;
- assembled IDs are assigned in first-input-mention order as `doc_e_001`,
  `doc_e_002`, and so on;
- every assembled entity retains the original mention values, spans, IDs, types,
  and confidence values.

This is document-local identity evidence, not biomedical normalization or
cross-document linking. The graph boundary reuses these IDs and preserves all
constituent mentions; it does not create a second node identity system.

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
matching. The current challenger comparison uses a shared five-class view and a
full-schema view so AIONER's explicit SequenceVariant support, and HunFlair2's
lack of that class, are reported rather than silently remapped or discarded.
The official AIONER runtime remains evaluation-only. HunFlair2's model artifact
and Flair/SciSpaCy dependencies remain isolated behind the production-facing
single-document bridge; the bridge does not add those dependencies to the main
environment.

The target-domain reconnaissance command uses the same source text for both
challengers and records PMID/PMCID, title, source URL, acquisition mode, section
boundaries, character count, and checksums. Its exact-span/type agreement
categories are deterministic diagnostics: exact agreement, same-span type
disagreement, same-type boundary overlap, cross-type overlap, and model-only
mentions. Sentence-level entity co-occurrence is reported only as a graph-candidate
diagnostic; no edge, predicate, or relation score is produced. The report keeps
SequenceVariant as an AIONER-only schema observation and retains CellLine in the
shared view.

The target-domain pilot command selects approximately 20 complete sentences per
paper using deterministic per-paper hard-case, stable entity-rich, and general
coverage groups. It preserves canonical source offsets, section/provenance
checksums, and a paper-level 6/1/2 split. Its ``entities`` arrays are empty until
a human reviewer supplies exhaustive annotations; HunFlair2 and prior AIONER
outputs remain separate reviewer suggestions. The validator rejects malformed
spans, unsupported types, and exact duplicates, reports overlap/nesting without
rewriting gold, and requires explicit completion before training or scoring.
The frozen pretrained HunFlair2 artifact is prediction-only evidence and does not
claim target-domain metrics while gold is incomplete.

The target training entry point consumes only validated, complete pilot gold and
uses Flair's development split for model selection while keeping the paper-level
test split out of training. The released HunFlair2 head is flat five-class Flair
NER; a human ``SequenceVariant`` annotation remains valid pilot gold but stops
training explicitly until a compatible representation is authorized. No gold is
auto-filled or inferred from model agreement.

The MedMentions experiment is an exploratory cross-schema stress test using
explicit UMLS semantic-type mappings. UMLS identifiers are retained as source
metadata but are not used for linking or scoring. Only explicit semantic types
mapped to ChemicalEntity or DiseaseOrPhenotypicFeature receive primary exact NER
metrics; unsupported and ambiguous gold annotations and unsupported predictions
are counted separately. It is not clean model-selection evidence comparable to
BioRED or CRAFT.

CRAFT is the primary clean independent cross-corpus benchmark for the current NER
decision. The evaluation uses the official CRAFT v5.0.2 full-text release and
identical canonical article text for AIONER and HunFlair2. Only Protein Ontology,
ChEBI, and NCBI Taxonomy annotations map to GeneOrGeneProduct, ChemicalEntity,
and OrganismTaxon respectively. Cell Ontology is not mapped to CellLine,
Sequence Ontology is not mapped to SequenceVariant, and GO annotations remain
out of scope. Unsupported and ambiguous CRAFT annotations remain explicit in
machine-readable reports and are excluded from primary metrics.

The grounded relation path is an active composition capability. Relation-specific
quality evaluation remains deferred; the graph boundary is a deterministic
serialization seam over already validated relation output, and the browser
viewer is a presentation-only consumer of that seam.

## Quality gate and replacement seam

The current prototype boundary remains model-independent at `EntityExtractor`.
The selected HunFlair2 base is callable through the isolated runtime bridge and
feeds the existing grounded relation path. Target-domain gold, NER evaluation,
and fine-tuning remain postponed; no fine-tuned replacement model or biomedical
identity-linking implementation is introduced here. AIONER and the HunFlair2
runtime dependencies remain isolated from the main production environment.

## Product invariants

- Production input is ordinary biomedical text, independent of BioRED metadata.
- The active prototype workstream is core biomedical NER followed by grounded
  relation composition.
- Default extraction does not run biological-process extraction or process
  precedence logic.
- Relations may be extracted only from supplied normalized entities and verbatim
  source evidence through the existing validation path.
- The `EntityExtractor` / `Entity` contract remains model-independent.
- Adapter/output normalization is distinct from biomedical identity normalization.
- Document-local assembly is a separate deterministic layer over mentions and
  never changes the `Entity` or grounded relation contracts.
- Assembly preserves every mention and maps each mention ID to exactly one
  document-local entity ID.
- Graph output reuses assembled node IDs, rejects dangling relation endpoints,
  preserves direction, negation, and verbatim evidence, does not rewrite
  predicates, and retains grounded relations when endpoint remapping produces a
  self-edge.
- Biomedical entity normalization/linking is not implemented in this task.
- Output is machine-consumable and does not require model-specific objects.
- HunFlair2 is the active prototype NER foundation, while its Flair/SciSpaCy
  runtime remains isolated and target-domain fine-tuning remains postponed.
- Target-domain reports cannot claim correctness or a production model winner
  without target-domain gold labels.
- Sentence co-occurrence diagnostics cannot create relation outputs.
- Official corpus fallbacks and unsupported cross-corpus mappings must remain
  explicit in machine-readable reports.

## Acceptance examples

### Core NER extraction

Given text containing a gene and disease mention, the entity extractor returns
stable entity values whose spans resolve exactly to the source mentions. The
HunFlair2 prototype path preserves official labels and model scores.

### Composed extraction

`LLMExtractionPipeline.from_hunflair2()` accepts ordinary biomedical text and
returns a `ComposedExtractionResult` containing those entities plus only
source-grounded relations whose endpoints reference the extracted entity IDs.

### Model-independent replacement

An alternative NER implementation can be evaluated by satisfying
`EntityExtractor.extract_entities(text)` and returning the same stable entity
fields, without exposing its model-specific prediction format.

### Document-local assembly

Given repeated compatible mentions, assembly returns one deterministic node while
retaining all mention values. Given an explicit source phrase such as
`kinetochore-associated protein 1 (KNTC1)`, compatible full-form and abbreviation
mentions may share one node with `KNTC1` as the display label. Unsupported alias
patterns and incompatible types remain separate, and the mention endpoint map is
complete.

### Graph-ready output

`LLMExtractionPipeline.extract_graph(text, document_id=...)` returns one node for
each assembled document entity and remaps grounded relation endpoints to those
node IDs. Equivalent endpoint/predicate/negation claims share one edge with all
source-evidence records retained, including when the remapped edge is a
self-edge. The result exposes `to_dict()` and deterministic `to_json()`
serialization and contains no frontend styling.

### Deferred downstream work

Entity normalization/linking, target domain NER evaluation, and fine-tuning remain
outside this prototype milestone. The viewer does not change extraction semantics.

### Graph JSON viewer

Launch the local viewer from the repository root after the normal environment
setup:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --directory viewer
```

Open `http://127.0.0.1:8765/`. The page fetches the static
`viewer/graph-fixture.json` smoke/demo payload, adapts its `nodes` and `edges`
through `viewer/adapter.js`, and renders them with Cytoscape.js. Replacing that
fixture with serialized `GraphResult.to_json()` output does not require a
backend contract change.

The summary distinguishes underlying directed relations from displayed
connections. A single relation is rendered as a directly inspectable edge;
multiple relations sharing the same source and target direction are rendered as
one count-labeled bundle, while the reverse direction remains separate. Select
a node to inspect its ID, display label, type, aliases, and every source mention
with mention ID, text, half-open offsets, and score when available. Select a
bundle to choose an underlying relation, then use the back control to return to
the bundle list. Relation details continue to show source and target direction,
the complete predicate, explicit negation state, and every retained evidence
record with surface form and score when available. Mixed-negation bundles stay
neutral on the canvas and mark negation on the individual relation. Selected
elements focus their local neighborhood, reverse directions use separate
presentation lanes, and valid self-edges remain supported. These display
bundles and routes are presentation-only and do not alter graph JSON semantics.

## Related architecture

See [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## Maintenance rule

Update this file in the same task whenever an accepted change materially alters the
current product/domain behavior. Do not append phase history or preserve obsolete
behavior beside current truth; use version control or an ADR for rationale that
genuinely needs to survive.
