# Contract 13C — Eight-paper graph damage audit

CURRENT SOL GRAPHS SHOW SIGNIFICANT MATERIAL REGRESSION

Four exact 12A reuses; four fresh Sol-medium/Standard background cases, each successful in one generation with zero repairs. No NER, role inference, auditor, second pass, repair experiment or production changes.

All headline counts below use 09B relations versus Sol relations projected through the same current deterministic assembly and graph builder on the identical packet per paper, before roles. Contract10 is the authoritative additional four-paper view in each comparison JSON. Historical graph counts are stored separately.

Confound: 09B lacks the Contract10 instruction excluding naming/alias-only relations; semantic schemas are identical. The exact prompt diff is preserved in prompt_confounds.diff. Four 09B packets have the same ID-keyed entity records as 12A but a different order; both sides use the unchanged 12A order. No historical artifacts were rewritten. Thus connectivity differences are relation-output differences, but 09B differences cannot all be attributed solely to model choice.

| Paper | Baseline nodes | Current nodes | Baseline orphans | Current orphans | New orphans | Resolved orphans | Baseline relations | Current relations | Material findings lost | Beneficial pruning | Severity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PMCID:PMC10770459 | 11 | 11 | 2 | 4 | 2 | 0 | 15 | 12 | 0 | 3 | GREEN |
| PMCID:PMC11824863 | 20 | 20 | 1 | 6 | 5 | 0 | 27 | 13 | 1 | 8 | ORANGE |
| PMCID:PMC8605525 | 20 | 20 | 5 | 6 | 1 | 0 | 35 | 26 | 5 | 3 | ORANGE |
| PMID:27172794 | 15 | 15 | 2 | 3 | 1 | 0 | 21 | 20 | 1 | 0 | YELLOW |
| PMID:27370646 | 9 | 9 | 2 | 1 | 0 | 1 | 9 | 7 | 0 | 2 | GREEN |
| PMID:31324362 | 10 | 10 | 1 | 1 | 0 | 0 | 17 | 16 | 2 | 0 | YELLOW |
| PMID:33652126 | 10 | 10 | 2 | 2 | 0 | 0 | 10 | 7 | 3 | 0 | ORANGE |
| PMID:38569671 | 16 | 16 | 4 | 4 | 0 | 0 | 19 | 17 | 0 | 2 | GREEN |

## PMCID:PMC10770459 — GREEN

Observed glucose reduction, tolerance improvement, in-vivo causality and therapeutic potential remain. New orphans are a method-only mouse edge and mis-typed tolerance fragment.

New orphans: mouse, tolerance.

- No demonstrated material finding lost.

[Full source-grounded ledger and all orphan identities](comparisons/pmcid_pmc10770459.md).

## PMCID:PMC11824863 — ORANGE

Most SFPQ outcomes survive, but explicit PI3K/AKT activation is lost and both ratio-denominator nodes become orphaned. These are meaningful signaling/topology regressions, not just alias pruning.

New orphans: proline and glutamine rich, mouse, Aβ1–42, PI3K, AKT.

- Elevated p-PI3K/PI3K ratio survives in assertion, but the edge now ends at phosphoinositide 3-kinase; supplied PI3K denominator node loses all connectivity.
- Elevated p-AKT/AKT ratio survives in assertion, but the edge now ends at protein kinase B; supplied AKT denominator node loses all connectivity.
- Explicit activation of the PI3K/AKT signaling pathway is absent from candidate assertion/predicate/effects/context. Increased ratios alone do not explicitly represent the pathway-activation finding.

Authoritative Contract10 controlled view: {'baseline_edges': 19, 'baseline_nodes': 20, 'baseline_orphans': 3, 'baseline_relations': 19, 'beneficial_pruning': 0, 'current_edges': 13, 'current_nodes': 20, 'current_orphans': 6, 'current_relations': 13, 'harmful_topology_changes': 2, 'material_findings_lost': 1, 'new_orphans': 3, 'resolved_orphans': 0}.

[Full source-grounded ledger and all orphan identities](comparisons/pmcid_pmc11824863.md).

## PMCID:PMC8605525 — ORANGE

Core Cb1-JAK2-STAT4-Runx3 mechanism remains, but the joint JAK2/STAT4 rescue experiment and several HG-HUVEC expression findings disappear; treatment potential is also lost.

New orphans: runt-related transcription factor 3.

- Potential E3/Cbl-based treatment against DM is not represented in current structured fields; retained DM disease context does not state therapeutic potential.
- JAK2 elevation in HG-induced HUVECs is lost; candidate restricts the expression result to diabetic rat tissues.
- Runx3 elevation in HG-induced HUVECs is lost; candidate restricts the expression result to diabetic rat tissues.
- STAT4 elevation in HG-induced HUVECs is lost; candidate restricts the expression result to diabetic rat tissues.
- The source's joint JAK2-and-STAT4 overexpression rescue/abrogation finding, including increased HUVEC apoptosis, is absent. Count one joint experiment, not two independent experiments.

Authoritative Contract10 controlled view: {'baseline_edges': 29, 'baseline_nodes': 20, 'baseline_orphans': 6, 'baseline_relations': 30, 'beneficial_pruning': 0, 'current_edges': 25, 'current_nodes': 20, 'current_orphans': 6, 'current_relations': 26, 'harmful_topology_changes': 0, 'material_findings_lost': 6, 'new_orphans': 0, 'resolved_orphans': 0}.

[Full source-grounded ledger and all orphan identities](comparisons/pmcid_pmc8605525.md).

## PMID:27172794 — YELLOW

The central EZH2/p21cip1/Wnt/beta-catenin mechanism and EPZ-6438 result remain; the explicit CCS contribution to poor prognosis is omitted.

New orphans: patients.

- Explicit CRC stem-like cells contributing to poor patient prognosis is absent; EZH2-to-prognosis is a different finding. Historical disease-level endpoint was imprecise, but the assertion supplied the material stem-cell claim.

Authoritative Contract10 controlled view: {'baseline_edges': 19, 'baseline_nodes': 15, 'baseline_orphans': 2, 'baseline_relations': 22, 'beneficial_pruning': 0, 'current_edges': 18, 'current_nodes': 15, 'current_orphans': 3, 'current_relations': 20, 'harmful_topology_changes': 0, 'material_findings_lost': 1, 'new_orphans': 1, 'resolved_orphans': 0}.

[Full source-grounded ledger and all orphan identities](comparisons/pmid_27172794.md).

## PMID:27370646 — GREEN

All demonstrated p53 knockdown phenotypes and VEGF suppression survive; the added cell-line relation is useful. Omitted mutation knowledge-gap claim is separately uncertain.

New orphans: none.

- No demonstrated material finding lost.

[Full source-grounded ledger and all orphan identities](comparisons/pmid_27370646.md).

## PMID:31324362 — YELLOW

Core activity/outcome/inhibitor reversal findings survive, but GLS/GS mediation of both cadherin outcomes is no longer explicitly represented.

New orphans: none.

- The explicit dependence of E-cadherin inhibition on enhanced GLS and GS activity is absent from current structured assertions/intervention/effects/context. Coexisting activity edges are not a stated causal mediation.
- The explicit dependence of N-cadherin promotion on enhanced GLS and GS activity is likewise absent. The outcome survives, but this mechanistic finding does not.

[Full source-grounded ledger and all orphan identities](comparisons/pmid_31324362.md).

## PMID:33652126 — ORANGE

Central PTEN/PI3K/AKT framework remains, but specific apoptosis/DNA-damage/proliferation reversal outcomes disappear. Contract10 additionally reveals loss of serum-deprivation PTEN upregulation.

New orphans: none.

- Reversal of PTEN-knockdown suppression of apoptosis is lost from structured meaning; generic effects does not specify apoptosis.
- Reversal of PTEN-knockdown suppression of DNA damage is lost from structured meaning.
- Reversal of PTEN-knockdown increased proliferation is lost from structured meaning.

Authoritative Contract10 controlled view: {'baseline_edges': 10, 'baseline_nodes': 10, 'baseline_orphans': 2, 'baseline_relations': 12, 'beneficial_pruning': 0, 'current_edges': 6, 'current_nodes': 10, 'current_orphans': 2, 'current_relations': 7, 'harmful_topology_changes': 0, 'material_findings_lost': 4, 'new_orphans': 0, 'resolved_orphans': 0}.

[Full source-grounded ledger and all orphan identities](comparisons/pmid_33652126.md).

## PMID:38569671 — GREEN

KIF23/pyroptosis/p53 mechanism, inflammatory factors and in-vitro/in-vivo results remain; method-only edges are replaced by results.

New orphans: none.

- No demonstrated material finding lost.

[Full source-grounded ledger and all orphan identities](comparisons/pmid_38569671.md).

## Aggregate (09B controlled view)

- baseline_nodes: 111
- current_nodes: 111
- baseline_orphans: 19
- current_orphans: 27
- new_orphans: 9
- resolved_orphans: 1
- baseline_relations: 153
- current_relations: 118
- baseline_edges: 132
- current_edges: 106
- material_findings_lost: 12
- beneficial_pruning: 18
- harmful_topology_changes: 2
- material_findings_retained: 13
- material_findings_equivalently_represented: 91
- material_findings_beneficially_pruned: 18
- material_findings_genuinely_lost: 12
- uncertain_cases: 3
- structured_losses_recoverable_from_evidence: 10
- losses_absent_from_candidate_evidence_too: 2

- GREEN: 3
- YELLOW: 2
- ORANGE: 3
- RED: 0

Lost findings count distinct source-supported structured meaning, including lost material mechanistic/setting/outcome qualifiers. They are separate from two harmful SFPQ topology changes. Many lost meanings remain recoverable by reading the original source sentence in candidate evidence: this audit does not claim their source text was erased. A quote alone does not encode the missing result as an asserted graph finding. Each omission records whether its exact baseline evidence remains in candidate quotes. Beneficial pruning counts naming/method/redundant units; it does not imply those were material biological results. Full per-baseline relation coverage is verified in the machine-readable ledgers.

No RED verdict: the eight abstracts still retain their main experimental frameworks. The signal nevertheless spans five papers and includes missing signaling, rescue, mechanistic and intervention-response content; fewer edges cannot be called a net scientific improvement.

Authoritative Contract10 also exposes two losses not represented by 09B: Cbl reduction in HG-HUVECs and serum-deprivation PTEN upregulation. Thus the union of the two baseline views identifies 14 distinct structured losses; the eight-row table/aggregate deliberately remain the controlled full-eight 09B comparison. Do not add the two baseline totals.
CURRENT SOL GRAPHS SHOW SIGNIFICANT MATERIAL REGRESSION
