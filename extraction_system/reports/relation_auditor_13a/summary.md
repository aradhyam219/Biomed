# Contract 13A — frozen second-pass auditor

The second pass recovered important omissions but failed the required scientific
precision gate. Preserve the Contract 12C single-pass production system. No prompt
amendment, additional experiment, automatic merge or production promotion occurred.

## Production preservation

Production prompt changed: **NO**. Production defaults changed: **NO**.
Relation schema changed: **NO**. Ordinary graph/viewer behavior changed: **NO**.
Automatic audit/merge enabled: **NO**. The implementation lives entirely under
this report path and has no ordinary extraction caller.

Verified production prompt SHA-256:
`13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f`.
Model/reasoning/tier/background remain `gpt-6.1-sol` / `medium` / `default` / `true`.
Production source and viewer files remain byte-identical; historical experiment
packages and all reused inputs are hash protected. Product and architecture
documents remain unchanged because the production architecture did not change.

## Execution and scientific review

One frozen prompt, five completed background generations, zero repairs, zero
polling errors, no Pass-1 regeneration, and no reviewer inference call.
Input/Pass-1 provenance, numbered relations, exact requests, raw and mechanically
validated outputs, per-proposal judgments, and proposed-only deltas are preserved.
`frozen_manifest.json` identifies each authoritative 12A or 11U control.

| Frozen case | Missing proposed | Valid omissions | Redundant | Unsupported | Wrong endpoint | Patches | Valid / invalid rich values | Seconds | Input / output / reasoning tokens | Repairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| PMC11824863 — SFPQ | 0 | 0 | 0 | 0 | 0 | 3 | 4 / 0 | 29.687 | 5669 / 1278 / 740 | 0 |
| PMC8605525 — Cbl | 3 | 2 | 1 | 0 | 0 | 4 | 4 / 0 | 36.188 | 8114 / 1603 / 734 | 0 |
| PMID27172794 — EZH2 | 1 | 0 | 0 | 0 | 1 | 0 | 0 / 0 | 14.781 | 6182 / 340 / 219 | 0 |
| PMID33652126 — PTEN | 1 | 1 | 0 | 0 | 0 | 2 | 2 / 1 | 38.391 | 4152 / 1487 / 993 | 0 |
| PMC10770459 passage_001 — 11U | 1 | 1 | 0 | 0 | 0 | 4 | 4 / 0 | 24.703 | 6419 / 1173 / 516 | 0 |

The six missing proposals contain **four valid material omissions**, one
redundant mechanism recasting, and one wrong scientific source endpoint: **66.7%**
admissibility. No unsupported causal, wrong-direction, alias-only or glucose-to-gene
proposal appeared. The EZH2 proposal nevertheless attributes a stem-like-cell
prognosis assertion to the generic colorectal-cancer disease endpoint.

Richness: 13 patches propose 15 values. Fourteen are admissible; one is locally
supported but hides a distinct supplied ROS interaction in a PI3K-to-PTEN effects
patch. Twelve patch records are fully admissible; one has both accepted and rejected
values. No value is unsupported, redundant, or assigned to the wrong existing
relation. Per-value justifications and before/addition comparisons are in
`scientific_review.json` and each case's `review.json` / `hypothetical_delta.json`.
Rejected proposals remain intact; no hypothetical production relation set is built.

| Rich field | Proposed values | Source-supported | Genuinely omitted | Admissible | Hidden supplied entity | Redundant / unsupported / wrong relation |
|---|---:|---:|---:|---:|---:|---|
| intervention | 1 | 1 | 1 | 1 | 0 | 0 / 0 / 0 |
| effects | 3 | 3 | 3 | 2 | 1 | 0 / 0 / 0 |
| context | 11 | 11 | 11 | 11 | 0 | 0 / 0 / 0 |

## Target findings

- **JAK2 and STAT4:** both omitted Cbl-effect reversal relations recovered,
  preserving the joint overexpression intervention and HUVEC apoptosis outcome.
  The Runx3 alternative was already represented.
- **PTEN increased expression:** recovered from the explicit serum-deprivation
  observation, using supplied serum-deficiency condition E28. No PTEN self-edge.
- **Cbl dual context:** four valid HG-induced-HUVEC additions complement existing
  DM-rat expression context without turning the setting into gene causality.
- **11U:** valid AST/ALT ratio comparison (approximately 1 versus 2), two liver/
  hyperglycemia contexts, and two staining-method contexts. Plasma/timing was
  already present and was not redundantly proposed.
- **SFPQ:** cognition/memory already represented. Useful ratio intervention/setting
  and two explicit pathway-activation interpretations recovered.
- **EZH2:** EZH2 prognosis, tumor-initiation and pathway-maintenance findings already
  represented. The additional background cell-prognosis edge is rejected for its
  disease-source endpoint. No accepted new EZH2 relation.

## Operations and verification

Observed incremental totals: **30,536 input**, **5,881 output**, **3,202 reasoning**
tokens; **143.750 seconds** summed generation latency; 39 polls, zero poll errors,
zero repairs. Reasoning tokens are part of output usage, not an additional billable
token total. Reliable model pricing or billed cost is unavailable in the existing
experiment tooling; no invented monetary estimate is reported.

An initial submission was locally blocked by sandbox socket permissions
(`WinError 10013`), before provider inference. Its safe diagnostics remain in
`preflight_socket_denial/`. An unauthenticated outside-sandbox request reached the
provider (HTTP 404); the five scientific requests then ran with network access.
This local failure is separate from the five completed generations. Failed-attempt
token telemetry is unavailable, not measured zero.

Passed: 9 focused auditor tests; 26 background/production-boundary tests;
16 relation-contract tests; 13 graph tests; 9 pipeline tests; 13 viewer tests.
All five Pass-1 graph replays equal their frozen graphs exactly; all five also pass
the actual viewer adapter's direction/evidence/visibility checks. Freeze and
production byte-equality verification pass. See `verification.json`.

Reproduce local checks with the repository `.venv` Python and
`scripts/auditor.py verify`. Paid execution is `scripts/auditor.py run`, with the
configured credentials and base URL supplied through the environment. The original
run loaded those values using the existing 12A `_environment_value` helper; it
never displayed credentials. Durable attempt files deliberately prevent repeating
completed cases. `scripts/review.py` only regenerates deterministic review artifacts.

Starting SHA: `8272e04f27df4a09cdc03df9d5f1082beaed8ef1`, verified against fetched
`origin/extraction_system_v2`. Delivery uses a normal commit/push on that branch;
the completion message records delivered/remote SHA and clean checkout evidence.

These are source-review judgments over one generation per case, not independent
gold annotations or a statistical generalization claim. Important recovery does
not offset the observed omission precision and metadata/topology-contract failures.
Stop this frozen experiment; do not tune or promote it.

SECOND-PASS AUDITOR FAILED — PRESERVE SINGLE-PASS PRODUCTION
