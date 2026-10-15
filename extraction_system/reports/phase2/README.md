# Phase 2 compatibility investigation

Offline downstream disposition: **NUMERIC_ONLY**. SFPQ live A/B provisional
scientific result: **MATERIAL_DIVERGENCE**; stop for Talia review.
The Linux/NVIDIA target is available and real CUDA inference is retained.
The CPU reference is verified; CUDA profile promotion was not performed.
Provider attempts: **2 / 24**. Repairs: **0 / 4**.

## SFPQ live A/B result

The subsequent contract authorizes two initial `sfpq-full` RE submissions in fixed
CPU-then-CUDA order, with only accepted production-required repairs (at most two
per arm/four shared). Preparation started clean at
`096ce0d0491a634687625e57def7fa3104173c4c`; the live run started clean at
`862d9ebf689a4df6a7ddb85e7e2361ae9276d971` on the same delivery branch.
The earlier missing-credential blocker was resolved by the user-authorized,
gitignored `.env`, sourced only into the execution shell. No credential value was
displayed or retained. The prepared runner was reused unchanged.

`tools/phase2_sfpq_live.py` is prepared and offline-tested. Preflight revalidates
retained evidence and the exact accepted runtime configuration: `gpt-6.1-sol`,
medium reasoning, background Responses, default service, 128000 output tokens,
unchanged prompt/schema/validator and two-repair production limit. SFPQ has 460
mentions in each arm; all initial-request differences remain confined to 308 score
literals, maximum delta `1.2576580047607422e-05`, with zero non-score differences.
The exact request hashes still match the completed offline gate.

The runner records requests/responses, parsed and validated output, diagnostics,
timestamps and IDs separately per generation. An exclusive local execution lock
and durable ledger reservations enforce counting before every SDK create call;
SDK retries remain disabled. Failed/uncertain attempts consume budget and stop the
experiment without a balancing rerun. Previously consumed submissions block a new
execution. Production bounded output repairs remain unchanged. Credential values
are excluded/redacted from retained evidence; no exception messages or client
objects are serialized. No NER or role path is invoked.

All **59** focused checks passed: eight new runner tests, five downstream tests,
four Phase 2 fixture tests, accepted Responses lifecycle/prompt/schema regressions
and relation contract checks. These cover both selected retained inputs, fixed
order/exactly two initial fake calls, repair exhaustion, uncertain submission
counting, pre-network request mutation rejection, evidence redaction and preserving
multiple/unmatched relations during alignment. Protected production sources,
configuration and fixtures remain unchanged.

[sfpq-live-comparison.json](sfpq-live-comparison.json) contains both validated
outputs, exact request hashes/lengths, diagnostics, deterministic alignment,
topology/grounding comparisons and the source-grounded scientific review.
Raw evidence is retained separately at
`.cache/phase2/20261015T073050708525Z-sfpq-live`; earlier preflight and NER evidence
remain intact. The raw runner snapshot is preserved; the tracked report adds the
review without rewriting provider output.

CPU ran first at 07:30:51 UTC on 2026-10-15, validated **50 relations** in about
118.5 seconds, then CUDA validated **62 relations** in about 121.2 seconds.
Both initial generations passed production validation. Exactly **2 initial
submissions, 0 repairs, 2 total generations**, with no transport failures,
timeouts, uncertain final states or poll errors. No role calls occurred.

The 47 deterministic one-to-one alignments were reviewed, plus two supplemental
pairs: CPU 27/CUDA 30 preserve the same potential Tau oligomerization/misfolding
claim; CPU 40/CUDA 48 encode the same HO-1-is-NRF2-target assertion with inverse
directed target-gene predicates. All indices here are zero-based. After these
supplemental pairs, one CPU output and 13 CUDA outputs remain separately listed;
several CUDA additions repeat shared results with different evidence. Nothing was
discarded or collapsed. Raw directed endpoint sets have **35 shared pairs,
1 CPU-only pair, 9 CUDA-only pairs** (36 CPU / 44 CUDA total). Accepted graph
construction yields **49 CPU / 60 CUDA edges**. No self-edges occur.

The decisive finding is CPU relation **41** versus CUDA relation **49**, both
using source mention `E380` (SFPQ) and target `E381` (Aβ), mapping to
`doc_e_010 -> doc_e_027`:

- CPU predicate: `may_mitigate_induced_oxidative_damage`.
- CUDA predicate: `induces_oxidative_damage`.
- Both assertions describe potential mitigation after SFPQ overexpression.
- The exact source at `[24565:24733]` says SFPQ overexpression could increase
  antioxidant enzymes/function and **mitigate** Aβ-induced oxidative damage.

CUDA's predicate contradicts both its own assertion/effects and the source. This
is a meaning-changing scientific graph label, not harmless wording. Production
graph construction preserves it unchanged; no score, prompt, predicate or output
was repaired for agreement. This supports provisional **MATERIAL_DIVERGENCE**.

Other variation is retained explicitly: a reverse NRF2/HO-1 endpoint encoding;
source-supported background/method relations; an additional hippocampal-morphology
finding; and additional PI3K/AKT pathway edges using Gene-typed SFPQ instead of
the Chemical-typed SFPQ used in both arms' phosphorylation findings. The shared
NER/assembly already contains both SFPQ types; this was not new NER drift.
Every relation has exact source-substring evidence (50/50 and 62/62), but that
mechanical grounding does not make CUDA 49's predicate scientifically supported.
Both arms set `negated=false` throughout; no negation-flag disagreement occurred.
Both preserve the important overexpression/AD-mouse, APP/Tau, antioxidant,
CREB/PSD95 and phosphorylated/total PI3K/AKT findings. Shared omissions, including
the explicit Bcl-2/Bax ratio and detailed cognitive-test timing/control context,
remain accepted-output limitations.

This one A/B cannot distinguish stochastic provider variation from sensitivity
to microscopic score literals. **The classification concerns the observed
scientific graph-output discrepancy, not proof that CUDA caused it or that CUDA
NER is invalid.** No migration failure or promotion decision is inferred.
Post-run replay revalidated saved parsed/validated outputs, both legacy Graph
Contract payloads, actual initial request hashes and zero non-score differences,
the decisive source slice, unchanged retained NER evidence and protected sources,
and absence of the credential value from retained JSON evidence. All **20** Graph
Contract and accepted baseline replay regression tests passed. Only the three
Phase 2 report/ledger files changed; the prepared runner remains unchanged.
STOP for Talia review: no CBL, repeats, roles, composed CUDA smoke, profile
promotion, scientific fixes or Phase 3. No push is authorized.

## CUDA YELLOW offline downstream gate

Started clean on `delivery/extraction-system-v1` at
`38c9d03bea65f8b09f9e00db4f6faf32a3a7ea82`, also the local origin tracking tip.
The original CPU and CUDA evidence directories were read without modification:
`.cache/phase2/20261013T103713Z-6ce48f02` and
`.cache/phase2/20261015T061416Z-cuda`. CPU raw SHA-256 remains
`11a245455e1b067742f3e24daa3338763631fed1dcc3f62d10735f368ccf57fa`.
All seven frozen source/title/document identities, runner inputs, raw-to-normalized
values, counts, finite scores and the complete CUDA `comparison.json` were checked.
No NER was rerun. Retained CUDA metadata identifies Tesla T4, `cuda:0`, CUDA 13.0,
Python 3.11.16 and PyTorch module `2.14.0+cu130`, using the pinned HunFlair2 revision
and artifact. No runtime or accepted CPU descriptor changed.

`tools/phase2_downstream.py` exercises production assembly, provider factories,
prompt builders, Responses request construction and graph construction. SDK clients
are recording doubles; real client construction and socket connections are blocked.
Relation recordings return valid empty structured results. Role recordings stop
immediately after request capture, without inventing role judgments.

| Case | Mentions | Assembled nodes | Changed RE scores | Max absolute delta | Score literal length changes |
|---|---:|---:|---:|---:|---:|
| sfpq-passage | 41 | 20 | 31 | 3.5762786865234375e-07 | 5 |
| cbl-passage | 66 | 20 | 44 | 2.4437904357910156e-06 | 13 |
| sfpq-full | 460 | 98 | 308 | 1.2576580047607422e-05 | 54 |
| cbl-full | 937 | 153 | 648 | 1.0609626770019531e-05 | 125 |
| hmgb1-full | 874 | 114 | 588 | 1.519918441772461e-05 | 117 |
| pten-abstract | 33 | 10 | 19 | 3.5762786865234375e-07 | 3 |
| ezh2-abstract | 41 | 15 | 27 | 1.6093254089355469e-06 | 4 |

Every hard NER field, including ID and array order, agrees. All assembly labels,
IDs, types, aliases, mention grouping/order, offsets and endpoint maps agree.
Complete serialized assembly differences are exclusively preserved mention scores;
there is no additional representative/score-derived field. All seven initial RE
requests differ, with **1,665 score literal differences and zero non-score
differences**. Exact comparison after masking only JSON confidence-number tokens
proves all other characters equal, including full source, boundaries and wording.
Request envelopes, system prompt hashes and structured schemas agree.

Role coverage uses the two saved passage relation baselines: 13 SFPQ relations
and 26 CBL relations. Saved endpoint IDs are rebound one-to-one by exact
`(text,type,start,end)` because historical mention order differs from retained NER.
Both arms preserve retained IDs/order and receive the same saved relations.
Both passages have six degree-zero targets. Node IDs, target order, names, types
and all mention identities/text/offsets agree. **Role targets serialize scores**:
SFPQ has eight differing score literals (maximum delta `2.384185791015625e-07`),
CBL four (`1.1920928955078125e-07`). Both role requests are score-only, with zero
non-score differences; title and complete source are exact. CBL has one changed
score-literal length; SFPQ has none. The saved CBL baseline has no role judgments,
but its fixed relations do support target/request construction. No role topology
was fabricated for the other five sources, which lack saved relation evidence.

Graph comparisons cover all seven empty-response harness graphs and both saved
passage relation topologies, including production endpoint remapping/self-edge
cleanup. Graph-facing identity, aliases, mentions and edges agree; retained node
mention scores differ. This does not establish equivalence of future live relation
responses or scientific quality.

Machine-readable results, per-case exact prompt/request hashes, lengths and evidence
digests are in [downstream-drift.json](downstream-drift.json). Its separate ignored
detail artifact retains every differing field location, exact recorded requests,
role targets and fixed-topology replay data. Original evidence is not overwritten.
Protected implementation/profile hashes, prompt/schema hashes and accepted fixture
byte hashes pass. All **68** focused tests passed: new comparison/zero-network
checks, Phase 2 fixtures, relations, paper roles, Graph Contract, CPU profile and
both baseline replays. Production scientific sources/configuration remain unchanged.

The offline gate stopped for Talia's review without live execution. Its successor
SFPQ authorization and completed live result are recorded above. CBL, repeat controls,
promotion, composed live smoke and Phase 3 remain later decisions. The remaining
question concerns provider sensitivity to these score-only input differences.

## Frozen boundary

Original local preparation started clean at
`e9a3184b9e76f12370657dab5f2a6457807a57c2`; the CPU identity amendment started
clean at `a52474f7176082e59938e04eb0cf7e82b7a5822b`, with no intervening changes.
The seven exact sources, titles, literal IDs, fingerprints, accepted configuration,
paid subset and smoke input remain frozen in `manifest.json` and the maintained
source-only compatibility fixtures. All seven contract text hashes match.
The source-grounded checklist was prepared before any provider calls.

The original descriptor and canonical CPU identity remain unchanged:
`ees-cfeec6ccd400b9f44abbef35551944aa074ee3d79d3e5ec18dd7d7551c76e0de`.
All protected scientific implementation files, model artifacts, prompts, schemas
and accepted baseline fixtures remain unchanged. No candidate CUDA descriptor
exists and no tags or release identity were changed. The research checkout remains
untouched apart from the original read-only acquisition of five source entries.

## Historical capture and separate successful revalidation

One fresh offline CPU inference captured all seven sources in retained run
`.cache/phase2/20261013T103713Z-6ce48f02`. Its original verification failed:
installed distribution release `2.14.0` versus actual module build `2.14.0+cpu`.
Historical `cpu-reference.json` and ignored `run.json` preserve that failure.
They were not rewritten as successful capture events.

The amendment corrects the existing profile-verification layer. The literal
module build `2.14.0+cpu` is accepted only with the original descriptor, captured
or same-interpreter distribution release `2.14.0`, actual device `cpu`, CUDA
runtime null and CUDA availability false. CUDA/custom suffixes, other releases,
missing evidence and contradictions remain rejected. No general version
normalization, runtime reporting rewrite or bypass was added.

`cpu-revalidation.json` records successful retained-run verification separately:

- Original raw-output SHA-256 matches `11a245455e1b067742f3e24daa3338763631fed1dcc3f62d10735f368ccf57fa`.
- Retained capture source and byte attestations match their declared conventions.
- Captured isolated inventory and actual model/runtime metadata satisfy the corrected check.
- All seven source identities and exact runner inputs match the frozen manifest.
- All 2,452 normalized Entity values, IDs and array order match the retained values.
- Every mention resolves to its exact source slice and every provided score is finite.
- Protected scientific implementation hashes match the unchanged original descriptor.

No NER was rerun, model downloaded, dependency reinstalled or provider request
submitted during the amendment. The runtime, model and scientific behavior were
not replaced. The user's independent inspection reported matching `version.py`,
`torch_cpu.dll` and `c10.dll` hashes in the research and delivery environments;
this amendment does not repeat or fabricate that inspection.

## Tool provenance

The original capture digest uses this Python-source convention: decode UTF-8,
remove an optional UTF-8 BOM, normalize CRLF and CR to LF, encode UTF-8 without a
BOM, then compute SHA-256.

- Original normalized-source digest: `4c91aa5bf35300640c277a37ff5832f82712ad3e56da35098a8e7273a3857c9d`.
- Retained-file byte digest: `167dbab44af49c49fce7797345995d361aefa7f2df1c8c5866a95cf90a6b399d`.

The retained `capture-tool.py` is the original wrapper. The modified inspection/
revalidation tool is `tools/phase2_reference.py`; its separate source/byte hashes
are recorded in `cpu-revalidation.json`, along with the corrected verifier's
source hash. It is not represented as the original capture tool.
This source normalization applies only to Python-source attestation. Scientific
text and titles, Graph Contract fingerprints and raw-output digests retain their
existing exact-input rules.

## Verification and remaining scope

The amendment passed 8 focused profile regressions, 19 Graph Contract tests,
4 Phase 2 fixture/attestation checks and 1 replay test covering both accepted
baseline graphs exactly. Interpreter-binding regression uses fake inference and
provider boundaries, never real NER/provider execution. Original viewer checks
remain the previously passed 14 checks; they were not repeated for this change.

At the CPU amendment, no Linux/NVIDIA target had been supplied. That historical
blocker is resolved by the existing AWS host and retained CUDA run described above.
The amendment itself left Docker Desktop/WSL and infrastructure untouched.
Live scientific review, conditional repeat controls, profile promotion and composed
live smoke remain outside this completed offline gate.

At the amendment, `provider-ledger.json` was an empty ledger without executable
enforcement. The SFPQ runner now enforces durable accounting for initial, repair,
failed and uncertain submissions within the original 24-generation/4-repair cap;
the ledger now records the two authorized SFPQ initial submissions and no repairs.
The existing scientific limitations remain unchanged. Mention counts are only
diagnostic. Development tooling, fixtures and review evidence remain outside the
client package; no release wheel was built for this amendment.

## Live CPU binding correction

The follow-up correction started clean at
`2cebf867d6e4a1f4896f781fa83b548745f4f9f8`. Composed-path regressions first
reproduced a relation invocation after replacing the NER or relation section.
The private binding now retains the authoritative descriptor by reference and
validates its complete canonical configuration at the post-NER checkpoint,
for both accepted module versions. Replaced sections and in-place NER drift now
raise before either relation or role extraction; unchanged operation still
reaches the mocked providers. All 12 focused profile tests, 19 Graph Contract
tests and the replay test covering both baselines passed.

The existing seven-input observations were revalidated without fresh inference;
`cpu-revalidation.json` now identifies the corrected verification-layer source.
Capture-tool/raw-output identities, original capture failure, normalized values,
CPU profile identity and protected scientific files remain unchanged. No viewer
checks were repeated. That correction is included in the starting delivery HEAD
and its origin tracking tip; it is no longer an unpushed local correction.

## Resume

The host prerequisite, offline downstream gate and authorized SFPQ live comparison
are complete. The provisional MATERIAL_DIVERGENCE result awaits Talia review.
The original source selections, budget and explicit candidate-promotion approval
gate remain in force. The offline gate consumed no provider submissions. Its focused
commit remains local because delivery-branch publication requires explicit
authorization under the repository guide.

To reproduce the offline downstream observation using retained evidence:

```bash
.venv/bin/python -m tools.phase2_downstream
```

Each execution creates a separate ignored detail directory and updates the current
summary. It never changes either retained NER run. The older CPU revalidation
report preserves the historical missing-host disposition; the current gate is
recorded separately in `downstream-drift.json`.

To revalidate retained evidence without inference or scientific-input acquisition:

```powershell
.venv/Scripts/python.exe tools/phase2_reference.py revalidate-cpu --run-directory .cache/phase2/20261013T103713Z-6ce48f02
```

`capture-cpu` refuses another attempt. `inspect-cpu` cannot overwrite an existing
historical summary. Revalidation writes a separate report and does not change
original raw predictions, normalized values, inventories or capture diagnostics.
