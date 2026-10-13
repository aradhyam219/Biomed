# Current Architecture

## Data flow

Ordinary biomedical text -> isolated HunFlair2 -> validated Entity mentions ->
document-local assembly -> grounded LLM relations -> graph construction and
naming-only self-edge cleanup -> degree-zero detection -> batched paper roles ->
deterministic GraphResult -> versioned export/serialized validation ->
Graph Contract v1 JSON -> existing Cytoscape viewer.

## Ownership and boundaries

- `entity_extraction.py`: shared Entity and EntityExtractor contracts.
- `hunflair2.py`: prediction normalization and subprocess bridge. The main
  runtime never imports Flair or SciSpaCy.
- `ner_runners.py` and `hunflair2_runtime.py`: isolated invocation, model identity,
  sentence splitting, document-offset lifting and plain prediction output.
- `entity_assembly.py`: unchanged conservative document-local grouping and
  complete mention-to-entity mapping, preserving original mentions.
- `relation_extraction.py`: grounded domain values and deterministic structural,
  endpoint and source-evidence validation; no scientific truth judgment.
- `llm_relation_extraction.py` and `responses_execution.py`: unchanged prompts,
  semantic schemas, bounded repair, strict provider transport and background
  lifecycle. Provider objects and credentials stay within this boundary.
- `llm_pipeline.py`: existing orchestration through extract/extract_graph. Ordinary
  pretrained construction enables automatic roles, with lazy provider setup
  only when final degree-zero nodes exist. Low-level injection keeps roles optional.
- `paper_roles.py` and `llm_paper_roles.py`: atomic, grounded node metadata for
  unconnected nodes; roles never alter topology.
- `graph.py`: stable assembled node IDs, endpoint mapping, evidence-preserving
  edge aggregation, self-edge cleanup and deterministic JSON serialization.
- `graph_contract.py`: pure exact-input fingerprints, versioned export, strict
  serialization, packaged offline schemas, graph/source validation and pure cache
  eligibility. It surrounds the unchanged graph core without a second graph model.
- `graph_profile.py`: narrow baseline preflight and verification of effective
  bound providers, pinned NER artifacts/runtime and actual returned metadata.
  A private NER profile binding carries the selected interpreter outside the
  descriptor so the CPU-only module-build check can corroborate its distribution
  release before relations. Raw producer seams do not require profile adoption. Unsupported v1 scientific
  overrides fail before paid extraction; NER drift fails before relation submission.
- `contract_resources/`: installed schemas, normative vectors and minimal recorded
  profile material. The wheel build hook embeds a clean delivered revision and
  production-resource digests; installed contract operations require no Git/cwd.
- `viewer/`: unchanged presentation adapter and Cytoscape UI. Bundles, reveal
  controls and routing affect presentation only.

Two separate Python environments remain required: the locked main environment
and isolated Flair/SciSpaCy environment. Provisioning recreates pinned artifacts;
ignored research environments are not delivery dependencies. See PROVISIONING.md.

## Contracts and invariants

Production accepts ordinary text independently of evaluation datasets. Mention
spans resolve exactly to source text. Assembly remains document-local, not
external biomedical normalization. Relations consume only supplied mention IDs
and exact source evidence. Edge identity uses source/target/predicate/negation;
rich semantic fields stay on each evidence record. Canonical unconnected nodes
remain in JSON. Roles are one/two paragraphs with exact source evidence and
substantive/contextual categories. No role metadata fabricates an edge.

The provider-independent EntityExtractor, RelationExtractor and PaperRoleExtractor
seams support injected implementations without exposing provider SDK objects.
Graph JSON remains the frontend-neutral consumer boundary. Accepted product
behavior and limitations are in product/CURRENT_SPEC.md. The immutable baseline
manifest and deterministic fixtures record delivery behavior, not scientific gold.

See [Graph Contract v1](GRAPH_CONTRACT.md) for public compatibility and input
identity rules. Legacy validation/classification needs no viewer adapter or migration.
