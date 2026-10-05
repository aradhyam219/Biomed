# Contract 13C — Eight-Paper Graph Damage Audit

**Starting SHA**

```text
abcdb79a3d6215e5dc82bbb2ad1e4cf280410851
```

This is **audit only**. Do not fix anything.

## Objective

Measure how much scientific graph content the current GPT-6.1 Sol medium production configuration has lost, retained, improved, or newly orphaned across the complete frozen eight-paper set.

The question is:

```text
Are the current graphs genuinely cleaner,

or

are they cleaner partly because scientifically useful
connections have disappeared?
```

The audit must distinguish those two outcomes.

## Frozen paper set

Use exactly:

```text
PMCID:PMC10770459
PMCID:PMC11824863
PMCID:PMC8605525
PMID:27172794
PMID:27370646
PMID:31324362
PMID:33652126
PMID:38569671
```

No paper substitution.

## Baselines

Use **two baseline views** rather than pretending Contract 10 covered eight papers.

For the four Contract-10 papers:

```text
PMC11824863
PMC8605525
PMID27172794
PMID33652126
```

the authoritative baseline is the frozen **Contract 10 GPT-5.6 Luna max output**.

For the full eight-paper comparison, use the frozen **09B GPT-5.6 Luna max outputs**. 09B already contains all eight source texts, entity inputs, relation outputs and graphs.

Before comparison, verify that the 09B relation prompt and semantic schema are equivalent to the current protected Contract-10 prompt/schema. If they are not equivalent, record the exact difference as a confound; do not conceal it.

## Current condition

Current production RE:

```text
gpt-6.1-sol
reasoning = medium
service tier = default / Standard
background Responses
Contract-10 production prompt
```

Production prompt SHA must remain:

```text
13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f
```

No prompt changes.

No second pass.

No auditor.

No repair experiment.

No entity normalization.

## Reuse existing Sol outputs wherever valid

Do **not** unnecessarily rerun the four papers already frozen under 12A.

Verify exact equivalence of:

```text
source text
entity packet
production prompt
semantic schema
model
reasoning
service tier
execution semantics
```

If equivalent, reuse the existing Sol-medium outputs for:

```text
PMC11824863
PMC8605525
PMID27172794
PMID33652126
```

Only run fresh Sol-medium inference for the remaining four papers:

```text
PMC10770459
PMID27370646
PMID31324362
PMID38569671
```

If an existing output cannot legitimately be reused, state why and run only that necessary case.

## Do not run paper-role inference

Contract 13B is already validated.

Paper roles do not change degree or topology.

For this audit, determine orphan status **before paper-role enrichment** and do not spend an additional role-generation call per paper.

13B production behavior must remain untouched.

## Critical comparison design

Do not compare only the historical graph JSONs directly.

Assembly has evolved since 09B, which could confound orphan counts.

For the eight-paper relation comparison, create a **controlled projection**:

```text
same frozen source
same frozen entity mentions
same current assembly
same current graph builder

        ↙                    ↘
old Luna relations       current Sol relations
        ↓                    ↓
baseline projection      candidate projection
```

This gives both relation sets the **same current entity/graph machinery**.

Therefore:

> differences in degree and connectivity in this controlled view are attributable to relation output rather than assembly drift.

Also retain the original historical graph counts separately as product-history context.

Do not rewrite any frozen historical artifact.

## Orphan audit

For every paper, report the exact node labels in these categories:

```text
INHERITED ORPHAN
unconnected in baseline and still unconnected now

NEW ORPHAN
connected in baseline, degree zero now

RESOLVED ORPHAN
degree zero in baseline, connected now

NEW NODE / IDENTITY DIFFERENCE
cannot be directly compared because assembly/entity identity changed
```

Counts alone are insufficient.

If baseline and current happen to have the same number of orphans but different node identities, report that turnover explicitly.

For every **new orphan**, trace which baseline relation(s) previously gave that node degree > 0.

Then classify the cause as:

```text
relation omitted
relation represented through another alias/node
identity split
endpoint changed
beneficial cleanup
uncertain
```

Do not repair it.

## Relation-damage audit

A naive exact JSON diff is not acceptable because predicate wording and metadata can change while preserving the same scientific finding.

Every baseline material relation/finding must be classified as one of:

```text
RETAINED
same scientific finding survives

EQUIVALENT / REPHRASED
same finding survives with changed predicate/assertion representation

BENEFICIAL PRUNING
duplicate, naming-only, misleading, invalid self-edge,
or otherwise preferable removal

HARMFUL OMISSION
explicit scientifically material finding disappeared

HARMFUL TOPOLOGY CHANGE
finding survives only with wrong endpoint/direction
or loses a supplied material participant

UNCERTAIN
cannot defensibly determine
```

Likewise identify genuinely useful current-only relations separately from noise.

The headline number of interest is **not**:

```text
baseline relation count - current relation count
```

It is:

```text
number of materially supported scientific findings lost
```

## Severity

Give every paper one final severity:

```text
GREEN
No material regression. Differences are primarily cleanup/equivalent representation.

YELLOW
Some real losses, but central scientific story remains substantially intact.

ORANGE
Multiple meaningful findings or important nodes lost.

RED
Core mechanism/topology has been materially amputated.
```

The justification must be source-grounded.

## Required final table

Produce one eight-row table containing:

| Paper | Baseline nodes | Current nodes | Baseline orphans | Current orphans | New orphans | Resolved orphans | Baseline relations | Current relations | Material findings lost | Beneficial pruning | Severity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

Then beneath each paper provide the identities of all new orphans and the scientifically important lost findings.

## Aggregate answer

At the end report:

```text
total baseline orphans
total current orphans
total new orphans
total resolved orphans

total baseline relations
total current relations

material findings retained
material findings equivalently represented
material findings beneficially pruned
material findings genuinely lost
harmful topology changes
uncertain cases
```

Also state how many of the eight papers are:

```text
GREEN
YELLOW
ORANGE
RED
```

## Hard invariants

Do not modify:

```text
NER
entity assembly
RE prompt
RE schema
RE defaults
graph semantics
viewer
paper-role enrichment
Contract 13A
Contract 13B
```

Do not implement fixes discovered during the audit.

Do not tune anything after seeing results.

This task answers **how damaged we are**, not **how to repair the damage**.

## Artifacts

Create a focused report root such as:

```text
reports/graph_damage_audit_13c/
```

Preserve the exact candidate outputs, controlled graph projections, per-paper comparison, and concise `summary.md` / machine-readable summary.

No giant diagnostic chronology.

## Git

Normal primary checkout.

After the audit is complete and verified, commit and non-force push to:

```text
origin/extraction_system_v2
```

Standing authorization applies.

## Completion verdict

End with one of:

```text
CURRENT SOL GRAPHS ARE NET CLEANER — NO MATERIAL AMPUTATION SIGNAL
```

```text
CURRENT SOL GRAPHS SHOW LIMITED MATERIAL REGRESSION
```

```text
CURRENT SOL GRAPHS SHOW SIGNIFICANT MATERIAL REGRESSION
```

```text
CURRENT SOL GRAPHS SHOW SEVERE MATERIAL REGRESSION — MODEL MIGRATION REQUIRES RECONSIDERATION
```

## Governing principle

Cleaner graphs are useful only if the removed content is genuinely noise.

Do not optimize for fewer edges or fewer visible nodes at the cost of scientifically meaningful findings.

**We are not trying to reduce body weight by chopping off limbs. Measure what disappeared, not merely how sparse the graph became.**
