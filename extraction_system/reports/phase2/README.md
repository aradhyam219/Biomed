# Phase 2 compatibility investigation

Disposition: **BLOCKED on the missing Linux/NVIDIA target**. The CPU reference
prerequisite is now **verified** under the CPU Runtime Identity amendment.
CUDA compatibility is not established and profile promotion was not performed.
Provider attempts: **0 / 24**. Repairs: **0 / 4**.

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

No Linux/NVIDIA target or connection was supplied. Docker Desktop's internal WSL
distribution was left alone; no infrastructure was allocated or drivers modified.
Linux dual-runtime provisioning, independent artifact acquisition, CUDA execution
proof, CPU/CUDA NER and downstream request comparison, conditional Linux/CPU
checks, live scientific review and raw/public CUDA smokes remain unperformed.
No downstream compatibility or scientific-quality claim is made.

`provider-ledger.json` remains an empty ledger, not implemented submission-budget
enforcement. Before future paid calls, enforcement must cover initial, repair,
failed and uncertain submissions within the original 24-generation/4-repair cap.
The existing scientific limitations remain unchanged. Mention counts are only
diagnostic. Development tooling, fixtures and review evidence remain outside the
client package; no release wheel was built for this amendment.

## Resume

Supply one existing Linux/NVIDIA host and its credential mechanism, then continue
the original Phase 2 sequence using these verified retained CPU observations.
Do not repeat NER or substitute historical fixture predictions. The original
source selections, paid subset, budget and explicit candidate-promotion approval
gate remain in force. The amendment authorizes no remote publication, CUDA
provisioning, live calls or profile promotion; its changes remain local.

To revalidate retained evidence without inference or scientific-input acquisition:

```powershell
.venv/Scripts/python.exe tools/phase2_reference.py revalidate-cpu --run-directory .cache/phase2/20261013T103713Z-6ce48f02
```

`capture-cpu` refuses another attempt. `inspect-cpu` cannot overwrite an existing
historical summary. Revalidation writes a separate report and does not change
original raw predictions, normalized values, inventories or capture diagnostics.
