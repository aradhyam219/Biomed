# Graph Contract v1

Public graph delivery uses `export_graph(GraphResult, text=..., paper_title=...,
context=...)`, then `graph_json(...)`. The raw GraphResult serializers remain
unversioned, deterministic internal seams. The root is `schema_version: "1.0"`,
`document`, `provenance`, `nodes`, `edges`; the latter three scientific fields
are copied exactly, preserving nested values and array order.

## Payload and validation

Packaged Draft 2020-12 schemas close serializer-owned objects to unknown fields.
Document IDs, IDs, labels, types, predicates and quoted/prose values are nonblank
strings preserved literally. Nodes have id/label/type/aliases/mentions and may
omit paper_role; absence is not null. Mentions have id/text/type/start/end/score.
Edges have id/source/target/predicate/negated/evidence. Evidence retains
text/assertion/intervention/effects/context/surface_form/score. Scores are always
present, finite numbers in [0,1] or null. Intervention and surface_form are
nonblank strings or null; effects/context/aliases may be empty arrays. Nodes
retain at least one mention and edges at least one evidence record.

Roles contain substantive/contextual category, one/two nonblank paragraphs and
nonempty quoted evidence. Roles attach only to degree-zero nodes; Species and
Organism use contextual roles. Roles remain optional on low-level graphs.
Biological self-edges and canonical unconnected nodes remain valid. Predicates
and entity types remain free-form; no ontology restriction is added.

Offsets are zero-based Unicode code-point positions in the exact source,
start-inclusive/end-exclusive, with `0 <= start < end <= len(text)` and exact
mention slice equality. JavaScript/Java/.NET consumers must translate UTF-16
indices; offsets are neither bytes, UTF-16 units nor graphemes. CRLF, combining
characters and non-BMP characters are not normalized.

`validate_graph(plain_data, text=..., paper_title=...)` checks shapes, finite JSON,
unique node/edge IDs in the shared viewer namespace, unique mention membership,
endpoints, spans, roles, hashes and verbatim edge/role evidence. Every non-null
evidence surface_form must also be a verbatim source substring, for v1 and
supported legacy data. Assertions,
interventions, effects, context and role paragraphs may be paraphrases. Without
text it checks only structure/integrity and explicitly reports that limitation.
It never repairs data. It performs no network schema resolution. Source-aware
checks do not certify entailment, completeness or producer authenticity.

## Exact fingerprints

`input_fingerprints(text, paper_title="")` uses strict UTF-8 without a BOM.
Omitted/empty titles agree; null, non-string and unpaired surrogate inputs fail.
Do not trim, case-fold, normalize Unicode, whitespace or newlines.

Let T and H be the exact UTF-8 text/title bytes. `source_sha256` is SHA256(T).
`extraction_input_sha256` is SHA256 of precisely:

```
ASCII("EES-INPUT-V1") || UINT64_BIG_ENDIAN(len(T)) || T
                      || UINT64_BIG_ENDIAN(len(H)) || H
```

The prefix is 12 bytes, without any extra delimiter. Lengths count bytes and
must fit unsigned 64-bit integers. Both digests are 64 lowercase hexadecimal
characters. Document ID is compared separately and never hashed here. JSON
formatting is not scientific identity. Packaged `fingerprint-examples.json`
contains all three normative conformance vectors, including non-BMP/CRLF inputs.
Use `contract_resource(name)` to access schemas/examples independently of cwd.

## Release and profile provenance

Provenance requires installed extractor_version, opaque extraction_profile,
both hashes, generated_at and build_revision. Schema version, software release
and extraction profile are separate identities. The revision is a full lowercase
40-character source commit. generated_at is assigned once at new export as an
actual UTC calendar timestamp with T separator and trailing Z; reserialization
preserves it. Explicit timestamps support deterministic replay. Legacy loading
never invents a historical timestamp.

Release wheels embed their clean source revision and production-resource byte
digests at build time. Installed export needs neither Git nor a source checkout;
missing metadata or modified packaged production resources fail clearly. Clean
editable checkouts may discover their source revision using Git. Dirty editable
checkouts require explicit test provenance and cannot advertise an automatic
clean revision. Wheel builds refuse uncommitted source changes.

The sole initial profile binds the recorded CPU HunFlair2 artifact/revision,
runtime/preprocessing/settings, scientific implementation digests, relation
model/reasoning/tier/mode/prompt/semantic schema and generation/repair settings,
and the independent fixed role model/reasoning/tier/mode/prompt/schema/settings.
The immutable original baseline manifest remains untouched. Profile material is
packaged; no profile registry or generic override support is introduced. Cache
locations and credential values are excluded. Unsupported CUDA, models, prompts,
producer injections or other scientific settings fail at the v1 boundary.
Raw low-level APIs still support their existing configurations. Once a descriptor
is validated as equivalent to the supported baseline, its profile ID is derived
from the authoritative packaged descriptor; equivalent accepted numeric
representations share the canonical ID.

For live baseline extraction call `prepare_graph_export` before extraction,
then `verify_graph_profile` after it and export with the returned context.
Preflight verifies bound providers, local model bytes and isolated distribution
versions without importing models; actual returned NER metadata is checked
before relation submission. Prepared pipelines also validate the selected per-call
role producer before extraction, and postflight checks the producer actually
invoked on that call. Unprepared low-level per-call injection remains available.
This requires an already provisioned baseline;
contract operations and fixed-stage replay themselves require no model runtime.
Explicit ExportContext is a caller attestation of recorded release/configuration,
intended for offline replay or an independently verified build; it does not
authenticate arbitrary producers. Never invent a baseline identity for injected
producers. Consumers validate profile field shape, not a local allow-list.

## Legacy and cache policy

Only absence of schema_version denotes legacy. A present null, malformed or
unsupported version fails, with no fallback. Supported legacy shapes include
both rich saved baseline graphs and the shipped older viewer evidence shape
(text/surface_form/score); rich fields are checked when present. Loading retains
all original values and never fabricates missing semantic fields or provenance.

`cache_eligibility(data, document_id=..., text=..., paper_title=...)` is a pure
validation decision, not a store/resolver. It requires valid v1 structure,
integrity/source checks and exact literal document ID and both input hashes.
PMC123, pmc123 and PMCID:PMC123 differ; no trimming or identity equivalence is
performed. Old software/build/profile provenance alone never disqualifies a
valid matching artifact. Legacy is displayable but never an automatically
verified hit. Invalid artifacts return an explicit invalid/ineligible result.

## CLI and scope

`biomedical-extract-llm --output-format graph --document-id paper-1
--paper-title "Exact title" --text "Exact text"` emits v1, invokes extract_graph
once and supplies the same title to roles and hashing. Upfront input, release
and configuration errors fail before provider submission. Default composed,
entity-only and relation-only commands retain their contracts. The existing
viewer consumes additive v1 root metadata unchanged.

Offline mechanical compatibility is not scientific acceptance. This phase adds
no service, cache storage, deployment, viewer implementation change, model work
or scientific repair.

## CPU distribution release and module build

The original immutable descriptor's `ner.runtime.pytorch = "2.14.0"` records
PyTorch's installed distribution release, read through `importlib.metadata` in
the selected isolated interpreter. The demonstrated CPU module reports the
literal build `2.14.0+cpu`. Verification accepts that additional value only for
the original CPU descriptor, with corroborating distribution release `2.14.0`,
actual device `cpu`, CUDA runtime version null and CUDA availability false.
Missing corroboration, CUDA/custom suffixes, different releases and contradictory
CUDA evidence fail. No suffix stripping or generic version normalization occurs.
Compatible original exact-version observations retain their existing behavior;
explicit CUDA evidence is rejected even when the module version matches exactly.

Live preflight reads the selected inference interpreter's distribution metadata.
A private runtime binding in the verification layer lets the protected NER bridge
read that same interpreter again when corroborating the additional module build,
before relation submission. The binding retains the authoritative descriptor by
reference and validates its complete canonical configuration at every post-NER
checkpoint; unsupported in-place mutations and replaced sections fail before
relations, for both accepted module values. The binding is outside the scientific descriptor and
public JSON; descriptor bytes and canonical CPU identity remain unchanged.
Postflight retains model/runtime/producer checks and per-call role verification.
Retained-run revalidation uses the captured isolated inventory together with the
actual inference metadata. This correction establishes no CUDA support.
