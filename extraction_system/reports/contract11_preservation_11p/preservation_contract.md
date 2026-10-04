# Contract 11P — Preserve and Integrate Contract 11 Work

## Intent

Make the valuable Contract 11 work durable in the primary repository history and eliminate dependence on the temporary Codex worktree.

The recent Contract 11 experiments intentionally used a no-commit/no-push policy. That restriction is now superseded.

The desired durable state is:

```text
origin/extraction_system_v2
    contains:
        reusable Contract 11 engineering
        scientifically important experiment artifacts
        reproducible model-selection infrastructure
        supplemental Candidate D records

while:
        Contract 10 production behavior remains unchanged
```

After successful preservation, integration, push, and verification, retire the temporary Contract 11 worktree.

---

# 1. Establish repository truth first

Before modifying anything, inspect:

- the primary repository checkout;
- the Contract 11 worktree;
- all worktree registrations;
- current branches and HEADs;
- tracked modifications;
- untracked files;
- ignored files where relevant;
- commits created since the protected Contract 10-era state;
- the complete worktree-only diff.

Do **not** reset, clean, prune, delete, move, or overwrite anything before determining exact state.

Do not assume a particular worktree branch or HEAD from prior reports. Use actual Git state.

---

# 2. Preserve reusable Contract 11 engineering

Identify and make durable the reusable engineering introduced during Contracts 11S/11S-R/11T/11U and the supplemental Candidate D run, including where actually present:

- OpenAI Responses API execution support used by the RE experiment path;
- background-mode request submission;
- response polling;
- timeout handling;
- explicit cancellation;
- stable response-ID handling where useful;
- usage/telemetry extraction;
- reasoning-token reporting where available;
- service-tier verification;
- strict structured-output transport-schema conversion;
- preservation of Contract 10 semantic validation behind that transport schema;
- candidate model/config parameterization;
- benchmark/model-selection harness;
- blinded-output generation;
- model-key/unblinding support;
- latency reporting;
- repair-count reporting;
- cost-estimation/reporting machinery;
- reproducibility/configuration metadata;
- focused tests for the above.

Preserve useful implementation through existing architecture where sensible.

Do **not** create a parallel production RE architecture merely because the benchmark path evolved separately.

---

# 3. Preserve scientifically important experiment artifacts

Retain the final artifacts needed to reconstruct and audit the recent experiment.

This includes authoritative/reproducible records for:

## Original Contract 11U trial

Candidates:

```text
Candidate A
Candidate B
Candidate C
```

Preserve, where present:

- exact source passage;
- exact supplied entity packet;
- frozen candidate outputs;
- original blinded packet;
- hashes/freeze metadata;
- model mapping;
- operation measurements;
- token/reasoning usage;
- repair counts;
- cost calculations;
- candidate configuration;
- final scientifically relevant result records.

The original A/B/C blind experiment must remain identifiable as the original Contract 11U experiment.

Do not rewrite its history after unblinding.

---

## Supplemental Candidate D

Also preserve the later:

```text
GPT-6.1 Sol
reasoning = xhigh
service tier = Standard
```

run and its artifacts.

Candidate D must be clearly labelled:

```text
supplemental experiment
outside original Contract 11U blind trial
model identity known before scientific comparison
```

Do not present Candidate D as though it participated in the original blinded A/B/C experiment.

Preserve its:

- exact validated relation output;
- source/entity identity with the original trial;
- model/configuration;
- runtime;
- input/output/reasoning tokens;
- repairs/polling errors;
- cost calculation;
- hash/freeze metadata where already generated.

Current reported operational result:

```text
runtime:
    171.6 seconds

input tokens:
    5,223

output tokens:
    10,004

reasoning tokens:
    7,768

validated relations:
    12

unique evidence spans:
    10

repairs:
    0

polling errors:
    0

estimated passage cost:
    $0.1131

estimated total including synthetic control:
    $0.1168
```

Preserve repository-generated authoritative values if they differ from this summary.

---

# 4. Preserve the scientific audit trail

The important distinction must survive in durable records:

```text
Original 11U:
    Candidate C won the frozen blind scientific review.

After unblinding:
    Candidate C = GPT-6.1 Sol medium Standard.

Supplemental D:
    GPT-6.1 Sol xhigh Standard was tested later
    for additional scientific/operational comparison.
```

Do not overwrite or mutate the original frozen blind review merely to incorporate D.

If a supplemental comparison record is preserved, keep it separate from the original freeze.

---

# 5. Hard invariants

## Protect Contract 10

This task is preservation/integration only.

Do **not** yet:

- change the production RE default model;
- promote GPT-6.1 Sol medium into production;
- promote GPT-6.1 Sol xhigh into production;
- migrate the ordinary production RE path to background execution;
- change the Contract 10 prompt;
- change Contract 10 relation semantics;
- redesign the relation schema;
- change entity assembly;
- alter graph semantics;
- change viewer behavior;
- introduce process/event nodes;
- perform unrelated cleanup or refactoring.

The model-selection work has selected a candidate for the next production-integration proof.

It has **not** yet authorized changing the production default.

---

# 6. Preserve semantic/transport separation

The strict OpenAI transport schema is a provider wire representation.

The Contract 10 semantic schema remains the application/domain contract.

The intended boundary remains conceptually:

```text
Contract 10 semantic schema
        ↓
strict provider transport conversion
        ↓
Responses API
        ↓
Contract 10 parsing / validation
```

Do not change domain semantics merely to satisfy provider strict-schema rules.

---

# 7. Secrets and local state

Never commit:

- API keys;
- authorization headers;
- credentials;
- `.env` secrets;
- unrelated private files;
- full environment dumps containing secrets;
- SDK/provider caches;
- temporary debug output;
- abandoned retry debris;
- large generated files with no reproducibility/audit value.

Inspect staged content before committing.

---

# 8. Git integration

Target durable branch:

```text
origin/extraction_system_v2
```

Determine the safest integration mechanism from actual Git state.

Possible cases:

### If work exists as uncommitted worktree changes

Create coherent commit(s), then integrate them into `extraction_system_v2`.

### If work exists on a temporary branch

Preserve coherent commits there, then merge or cherry-pick into `extraction_system_v2` using the smallest clean mechanism.

### If `extraction_system_v2` is currently checked out elsewhere

Respect Git worktree rules.

Do not force around worktree protections.

Do not force-push.

Ren has standing authorization for ordinary task-related non-force pushes to:

```text
origin/extraction_system_v2
```

Push the final integrated state once validation succeeds.

---

# 9. Commit structure

Prefer a small number of coherent commits.

A sensible separation, if repository reality supports it, would be approximately:

```text
1. reusable Contract 11 execution / benchmark infrastructure
2. preserved Contract 11U + Candidate D experiment records
```

This is non-binding.

Use repository conventions and choose the cleanest structure after inspection.

Avoid both:

- one opaque dump containing unrelated material;
- excessive micro-commits.

---

# 10. Validation

Treat this as an elevated integration task.

At minimum establish that:

1. reusable Contract 11 infrastructure is durably tracked;
2. background-mode support remains functional in the experimental path;
3. strict transport conversion preserves Contract 10 semantic validation;
4. benchmark/model-selection tooling remains usable or reproducible;
5. original A/B/C experiment records remain intact;
6. Candidate D is clearly supplemental;
7. production RE defaults have not changed;
8. Contract 10 prompt/schema semantics have not changed;
9. graph/viewer behavior has not changed;
10. no secrets or accidental debug/cache files entered history;
11. `extraction_system_v2` contains the intended commits;
12. `origin/extraction_system_v2` contains the resulting state after push;
13. the primary checkout is clean.

Use existing repository test commands.

Escalate validation only where the integration surface justifies it.

Do not repeatedly rerun unchanged successful tests without a new reason.

---

# 11. Worktree retirement

Only after all meaningful Contract 11 state is:

```text
tracked
→ committed
→ integrated into extraction_system_v2
→ pushed to origin
→ verified
```

perform a final worktree-only state check.

Confirm there are no meaningful:

- modified files;
- untracked files;
- experiment records;
- code changes;

remaining exclusively in the temporary worktree.

Then remove the Contract 11 worktree using normal Git worktree mechanisms.

Prune stale worktree metadata if appropriate.

Do not manually delete the directory while Git still registers it as a worktree.

After this task, ordinary work should resume from the normal `extraction_system_v2` checkout rather than automatically creating another worktree.

---

# 12. Implementation freedom

Inspect the repository and determine the smallest coherent integration that satisfies this contract.

Follow existing architecture and repository conventions.

Suggested mechanics are non-binding unless required above.

If some Contract 11 implementation is clearly benchmark-only, keep it appropriately isolated rather than promoting it into production modules.

If repository reality conflicts materially with this contract, report the concrete conflict and safest options rather than destructively resolving it.

---

# 13. Completion report

Keep the final report concise.

Report:

## Preserved

- reusable engineering;
- original Contract 11U scientific artifacts;
- supplemental Candidate D artifacts.

## Git

- relevant starting HEAD;
- resulting `extraction_system_v2` HEAD;
- commits created;
- integration mechanism used;
- confirmation of push to `origin/extraction_system_v2`.

## Verified

- tests/checks performed;
- Contract 10 production defaults unchanged;
- prompt/schema semantics unchanged;
- no secrets committed;
- no meaningful Contract 11 state remains only in the temporary worktree.

## Retired

- whether the Contract 11 worktree was successfully removed.

## Remaining risk/deviation

Only material unresolved items.

---

# Final boundary

**Do not begin the GPT-6.1 Sol production integration/migration in this task.**

Contract 11P ends when the recent work is safely preserved, integrated, pushed, verified, and the temporary worktree is retired.