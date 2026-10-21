# Entity Extraction System: Current Specification

The accepted functional baseline turns ordinary biomedical text into graph-ready
JSON through isolated pretrained HunFlair2 NER, document-local entity assembly,
grounded LLM relations, graph construction, and post-topology paper roles.
`LLMExtractionPipeline.extract_graph(text, document_id=..., paper_title=...)`
is the composed entry point. `extract()` returns normalized mentions and relations.

HunFlair2 uses its official Gene, Chemical, Disease, Species and CellLine labels.
Entities retain source text, half-open spans, IDs and optional confidence.
Relation defaults are GPT-5.6 Luna, max reasoning, background Responses and
Fast service (`fast` requested, `priority` observed). Explicit provider configuration overrides remain
supported. The production prompts and semantic schemas are frozen in
the Contract 14R artifacts referenced in `reports/phase2/luna-freeze.json`.
Provider SDK retries are disabled; malformed or invalid
output may consume the finite repair budget. Provider/role failures surface explicitly.

The delivery branch contains current runtime and tests. Research and evaluation
history remains in the research branch and baseline tag. Dataset-specific inputs
are not required in production. Entity-only and relation-only inspection remain
available through `biomedical-ner` and `biomedical-re`.

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
  pattern of the form `full form (ABBR)` with compatible types; a bounded
  Schwartz-Hearst-style alignment can recover a long-form source span and join
  several same-type mentions contained within that span;
- incompatible types, unsupported alias patterns, and uncertain candidates stay
  separate;
- assembled IDs are assigned in first-input-mention order as `doc_e_001`,
  `doc_e_002`, and so on;
- every assembled entity retains the original mention values, spans, IDs, types,
  and confidence values.

This is document-local identity evidence, not biomedical normalization or
cross-document linking. The graph boundary reuses these IDs and preserves all
constituent mentions; it does not create a second node identity system.

## Unconnected nodes and paper roles

After assembly, relation extraction, graph remapping, and alias/naming-only
self-edge cleanup, a node has degree zero when it is genuinely unconnected.
Canonical graph JSON retains every such node. Ordinary pretrained graph generation
automatically enriches every degree-zero node in one batched initial call using
the paper title, complete supplied text, and every source mention for each node.
Role output is limited to `substantive` and `contextual`, contains one or two
concise paragraphs, and retains exact verbatim source evidence. Role prose is
node metadata only: it never creates, modifies, or implies a graph edge.
The role provider uses GPT-5.6 Luna, max reasoning, Fast (`fast`) service,
and the shared background Responses executor. No degree-zero nodes means no role
provider setup or call. Provider or grounding failures raise explicitly before
a graph is returned; incomplete batches are never partially attached. Validated
records survive output repairs; at most two repairs request only failed or missing
target IDs. Species and Organism roles must be contextual. Unknown or
unattributable IDs fail explicitly. Explicit role injection remains supported,
and low-level pipeline construction keeps roles optional.

## Graph contract

`GraphResult.to_dict()` / `to_json()` emit document, nodes and edges. Node IDs
reuse assembled entity IDs. Every canonical node remains, including degree-zero
nodes. Directed edge identity is exactly remapped source, target, predicate and
negation; contributing evidence remains independently retained. Each evidence
record preserves assertion, intervention, effects, context, verbatim evidence,
optional surface form and score. Graph construction does not rewrite predicates
or infer new findings. Naming-only self-edges are suppressed after identity
collapse; grounded biological self-edges remain.

Public delivery uses Graph Contract v1 through `export_graph` and `graph_json`.
The graph CLI now emits v1 and accepts `--paper-title`, passing the exact same
value to role extraction and fingerprinting. Raw GraphResult serialization stays
unversioned. See [Graph Contract v1](../GRAPH_CONTRACT.md) for payload/null/offset
rules, exact UTF-8 text/title fingerprinting, immutable effective profile identity,
release provenance, serialized/source-aware validation and legacy/cache policy.
Offsets count Unicode code points; no Unicode or newline normalization occurs.
Legacy graphs remain displayable without fabricated provenance, but cannot be
verified cache hits. Exact literal document ID/text/title governs v1 reuse;
software or profile upgrades alone do not regenerate stored science. The initial
v1 producer preserves the original CPU descriptor and has separate derived
Luna/CPU and Linux/CUDA descriptors. Explicit `--device cuda` selects the latter;
the transport-only create deadline correction has separate derived descriptors.
The single authorized retry passed CUDA NER, RE and pre-role graph validation but
exhausted normal role-output repairs. Role reliability now preserves valid records
and targets repairs to failed IDs. The first saved-state role-only confirmation
stopped at submission because host DNS failed. After connectivity recovered, the
authorized continuation and subsequent credential-replacement confirmation each
stopped at HTTP 401 authentication failure without a response ID; no repair was
submitted. Final export remains unconfirmed
(reports/phase2/sfpq-role-reliability.json). Phase 2 remains operationally blocked,
the CUDA profile is not promoted, and no further generation is authorized.
Raw overrides remain available. Validation does not certify entailment, completeness or authenticity.

## Accepted limitations and scope

This is an accepted functional baseline, not scientific gold. Source-explicit
assembly can still produce semantic false merges. Relation outputs can omit
intervention, joint conditions, outcomes or context; quoted evidence alone does
not prove that structured findings were preserved. Model output is variable.
These limitations are retained without scientific repair in delivery cleanup.

External biomedical identity linking, cross-document resolution, biological
process/event extraction, phosphorylation/state redesign, model comparisons,
NER fine-tuning and prompt refinement are outside the current delivery task.
API services, containers, cloud deployment, concurrency engineering and viewer
packaging are later milestones. No scientific quality promotion follows from
passing deterministic or mechanical checks.

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

The summary distinguishes canonical entities from displayed entities, hidden
unconnected entities, underlying directed relations, and displayed connections.
Genuinely unconnected nodes are hidden from the default canvas but remain in the
dedicated `Unconnected entities` panel, grouped into substantive and contextual
counts. The global reveal control and each card's `Show on graph` control expose
them without fabricating edges; selecting a revealed node shows its role and
source evidence. Species is explicitly rendered as a green hexagon.

A single relation is rendered as a directly inspectable edge;
multiple relations sharing the same source and target direction are rendered as
one count-labeled bundle, while the reverse direction remains separate. Select
a node to inspect its ID, display label, type, aliases, and every source mention
with mention ID, text, half-open offsets, and score when available. Select a
bundle to choose an underlying relation, then use the back control to return to
the bundle list. Relation details continue to show source and target direction,
the complete predicate, explicit negation state, and every retained evidence
record with the complete assertion first, followed by present intervention,
effects, context, verbatim evidence, surface form, and score. Empty optional
sections are omitted. Mixed-negation bundles stay neutral on the canvas and
mark negation on the individual relation. The mixed-negation warning is a
single wrapping block. Selected elements focus their local neighborhood,
reverse directions use separate presentation lanes, and valid biological
self-edges remain supported. These display bundles and routes are
presentation-only and do not alter graph JSON semantics.

## Maintenance

Update this specification when accepted product behavior changes. Architecture
is described in `../ARCHITECTURE.md`; provisioning in `../PROVISIONING.md`.
