# Biomedical Named-Entity Extraction Architecture

> This document contains the current structural truth for the extraction subsystem.
> It is not a phase history or implementation diary. Update it in place when the
> accepted architecture changes.

## System purpose

This subsystem converts unstructured biomedical text into stable, machine-consumable
biomedical entity mentions, source-grounded relations, and a frontend-neutral
graph-ready JSON representation. Its active foundation is pretrained HunFlair2 NER
behind the existing model-independent entity seam, followed by the existing
grounded LLM relation implementation.

Target-domain NER evaluation and fine-tuning remain postponed. The graph viewer
consumes this architecture's JSON boundary, while external biomedical identity
normalization remains outside the active path. A conservative document-local
identity layer groups only exact, compatible, source-explicit mentions without
changing the mention-level contract, and the graph boundary combines its output
with grounded relations.

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
      v
Deterministic document-local identity assembly
(exact repeats, aligned explicit abbreviations, exact same-document recovery)
      |
      v
Bounded verifier for remaining eligible explicit parentheticals
(one structured batch only when candidates exist)
      |
      v
Final document-local nodes + mention map
(original mentions preserved)
      |
      v
Grounded LLM relation extraction
(over the supplied mention IDs)
      |
      v
Graph construction and alias/naming-only self-edge cleanup
      |
      v
Genuinely unconnected-node detection
      |
      v
Optional paper-role enrichment
      |
      v
GraphResult / graph JSON
      |
      v
Future biomedical entity normalization/linking
(mention -> canonical biomedical identity)
      |
      v
STOP
```

The composed prototype path can return validated entities and grounded relations
or expose them through ``extract_graph`` as a deterministic ``GraphResult``. The
pipeline performs only eligible explicit-identity verification before relation
extraction; the verifier sees bounded source constructions and compatible
mention IDs, while the relation extractor still receives the unchanged mention
values. The graph boundary consumes the final assembly map, remaps relation
endpoints, and retains verbatim relation evidence. After remapping it suppresses
only naming- or alias-only self-relations; genuine biological self-relations
remain. The pipeline then exposes degree-zero nodes for optional paper-role
enrichment. The graph boundary itself does not perform inference, generalized
biomedical identity normalization, or frontend styling.

The tracked browser prototype is a separate downstream consumer of the same
graph-ready JSON boundary:

```text
GraphResult / graph JSON
        |
        v
viewer/adapter.js
(graph values -> display model -> Cytoscape elements)
        |
        v
Cytoscape.js interactive graph
        |
        v
node/edge detail panels with source evidence
```

The viewer owns presentation-only Cytoscape classes and layout metadata. It
groups relations only by identical source and target direction, retains the
underlying relation objects for inspection, and assigns pair-aware routing
metadata for display. It does not run extraction, infer relations, rewrite
predicates, or require a specific NER or relation provider. The checked-in
fixture is a smoke/demo input; the same adapter can receive serialized backend
output later.

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
HunFlair2 output normalization. `entity_assembly` owns conservative deterministic
document-local grouping, assembled node values, and the mention-ID endpoint map.
It recovers a complete literal source form when an existing compatible mention
has the same superficially normalized text. `identity_resolution` defines
eligible unresolved parenthetical candidates and validates exact-evidence
decisions; `llm_identity_resolution` owns the bounded structured Responses API
harness using the shared OpenAI configuration. No verifier request occurs for
an empty candidate set. `llm_pipeline` defaults the composed path to HunFlair2
and completes identity resolution before relation extraction and role selection
while composing the selected entity adapter with
`llm_relation_extraction`, while `relation_extraction` owns the
provider-independent grounded relation value and validation. The relation value
keeps a concise predicate alongside a complete source-grounded assertion,
optional intervention/effects/context qualifiers, and verbatim evidence;
validation checks structure and traceability but does not claim to prove the
semantic summary. `graph` owns the typed graph result, endpoint remapping,
deterministic edge aggregation, alias/naming-only self-edge cleanup, degree-zero
detection, and JSON serialization. Graph edge identity uses only the remapped
source and target, predicate, and negation state; each contributing
`GraphEvidence` record retains its own assertion, intervention, effects,
context, verbatim text, surface form, and score. `paper_roles` owns the
provider-independent role value, target contract, exact-evidence validation,
and node-only enrichment; `llm_paper_roles` owns the separate Responses API
structured-output harness. Raw model/provider objects do not cross these seams. The
existing GLiNER adapter and legacy
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
The active composed path defaults to HunFlair2 through
`LLMExtractionPipeline.from_pretrained()` and the
`biomedical-extract-llm` command. `LLMExtractionPipeline.from_hunflair2()` and
the explicit `--entity-backend hunflair2` selection remain available. The
GLiNER-BioMed adapter remains available through an explicit compatibility
selection, while AIONER / PubTator-style NER remains preserved
evaluation/history evidence.
Neither the postponed pilot nor the training lane changes the composed runtime
seam.

## Normalization terminology

The repository uses two distinct meanings of normalization:

- **Adapter/output normalization** converts a model-specific prediction into the
  stable local `Entity` object. This is implemented in the current adapter.
- **External biomedical entity normalization/linking** resolves a mention to an
  ontology identifier or an identity not explicitly established in the supplied
  document. This is not implemented and is deferred until NER selection and
  validation are complete. Local source-explicit identity assembly remains a
  separate, bounded operation.

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
negation validation. Its active OpenAI provider path uses LangChain's explicit
Responses API integration with `gpt-6-luna`, standard/default reasoning mode,
`reasoning.effort=max`, and a `128000` output-token ceiling. The public
`max_completion_tokens` configuration name remains for compatibility and is
mapped to the Responses API output-token field below this provider-independent
seam; structured output and bounded repair also remain inside the harness. The
legacy GLiREL-compatible relation/evaluation path and its historical diagnostics
remain preserved separately.

Target-domain NER evaluation, model selection, and fine-tuning remain postponed.
External biomedical normalization remains outside this path. The graph boundary
consumes final mention grouping and is limited to endpoint mapping, exact-key
edge aggregation, naming-only self-edge cleanup, degree-zero detection, evidence
preservation, optional node roles, and JSON serialization; the viewer consumes
that boundary without adding graph semantics.

Biological-process extraction is likewise deferred and, if required later, will be
treated as a separate decision rather than added to the default core-NER pass.

## Components and ownership

| Component | Responsibility | Owns | Must not own |
|---|---|---|---|
| Entity extraction | `entity_extraction.EntityExtractor` runs the configured entity adapter on input text | Stable entity IDs, source spans/types, and model confidence | GLiNER-specific output outside the adapter, BioRED assumptions, or relation logic |
| Adapter/output normalization | Convert one model's predictions into the local `Entity` value | Span integrity, schema validation, and stable output fields | Canonical biomedical identity linking or downstream reasoning |
| Document-local entity assembly | Group safe same-document mentions and expose assembled nodes plus a mention-ID map | Deterministic node IDs, mention preservation, bounded abbreviation alignment, exact same-document full-form recovery, and type-compatible source evidence | External normalization, cross-document identity, graph serialization, or relation rewriting |
| Explicit identity verification | Decide whether an eligible source construction explicitly introduces its parenthetical as a name or abbreviation for the preceding long-form phrase | Bounded candidates, finite construction decisions, exact source evidence, and compatible contained mention IDs for deterministic assembly | Judging isolated NER fragments as synonyms, synonym discovery, morphology, outside knowledge, type repair, or cross-document identity |
| Pipeline orchestration | Run final identity mapping before downstream relation and role stages | Conditional verifier invocation, unchanged mention values, and ordered graph composition | Provider response parsing or graph presentation semantics |
| Graph boundary | Convert assembled nodes and grounded mention relations into a stable graph result | Document ID, node identity reuse, endpoint remapping, alias/naming-only self-edge cleanup, degree-zero detection, source/target/predicate/negation edge aggregation, per-evidence rich semantics, and JSON serialization | Model inference, semantic predicate rewriting, graph-database state, or frontend styling |
| Paper-role domain seam | Validate and attach grounded explanations for degree-zero nodes | Minimal category, one/two paragraphs, exact source evidence, and unchanged edge topology | Provider SDK objects, graph inference, ontology assertions, or roles for connected nodes |
| Graph viewer | Render graph JSON as an inspectable directed Cytoscape.js graph | Presentation mapping, hidden/revealed unconnected nodes, role panel, species styling, pan/zoom, node/edge selection, aliases, mentions, negation styling, and per-evidence assertion/metadata display | Extraction, provider assumptions, relation inference, predicate rewriting, or graph persistence |
| External biomedical entity normalization/linking | Resolve mentions beyond source-explicit document-local constructions | Not implemented in the current path | Model selection before the NER quality gate |
| Relation extraction | Existing grounded LLM relation implementation over supplied normalized entities | Predicate, complete assertion, optional intervention/effects/context, verbatim evidence, endpoint integrity, negation, and validation | Entity discovery, graph assembly, graph propagation of rich semantics, or unsupported biological inference |
| Evaluation and adaptation readiness | Measure core NER and prepare controlled target adaptation | Dataset adaptation, metrics, challenger adapters, model comparison, target-domain pilot/validator, frozen baseline, and isolated training readiness | Production extraction semantics, pseudo-gold, incomplete-gold training, or production model replacement |

## Hard architectural invariants

- Production entity extraction accepts ordinary biomedical text and does not
  require BioRED annotations.
- The `EntityExtractor` boundary remains model-independent.
- Raw model predictions do not cross the adapter boundary.
- Entity spans always refer to the original source text.
- The entity stage is core NER only; it has no biological-process pass or
  process-specific conflict rule.
- External biomedical entity normalization/linking is not implemented.
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
- Deterministic local assembly and accepted verifier decisions preserve every
  original mention and never merge incompatible entity types. Identity is
  finalized before relation endpoint remapping, degree-zero detection, and
  paper-role generation; uncertain candidates remain separate.
- The graph boundary must not emit dangling endpoints, discard relation evidence,
  rewrite predicates, or introduce frontend-specific styling. It suppresses only
  alias/naming-only self-relations after endpoint identity collapse; genuine
  grounded biological self-edges remain. Edge aggregation must not use rich
  assertion, intervention, effects, or context fields as identity keys; those
  values remain independent on each contributing evidence record.
- Degree-zero nodes remain canonical graph nodes. Optional paper-role metadata is
  source-grounded, limited to `substantive`/`contextual`, contains one or two
  paragraphs, and never changes edge topology.
- The graph viewer must consume only graph-ready JSON and must not infer,
  reverse, or semantically rewrite nodes, edges, predicates, negation, or
  evidence. It hides degree-zero nodes only by default presentation state and
  retains global/per-node reveal controls. It omits absent optional semantic
  fields while exposing present assertion, intervention, effects, context,
  surface form, score, and paper-role values.
- The architecture must not grow speculative ontology, graph-database, or
  external normalization infrastructure beyond the graph-ready JSON boundary.

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
