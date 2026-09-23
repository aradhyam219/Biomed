# Contract 10R-D role restoration

Accepted semantic baseline: ca8a196c49b45827933788f6aec532809a14bc79
Role provider: OpenAI Responses API, gpt-6-luna, reasoning effort max.
Role calls: 5; structural repair attempts: 1.

| Paper | Canonical nodes | Relations | Graph edges | Unconnected | Role records | Missing roles |
|---|---:|---:|---:|---:|---:|---:|
| PMCID:PMC11824863 | 19 | 19 | 19 | 2 | 2 | 0 |
| PMCID:PMC8605525 | 19 | 30 | 29 | 5 | 5 | 0 |
| PMID:27172794 | 15 | 22 | 19 | 2 | 2 | 0 |
| PMID:33652126 | 10 | 12 | 10 | 2 | 2 | 0 |

## PMC11824863 required outcomes

- Aβ source node: doc_e_008; category: substantive; paragraphs: 1; exact evidence records: 1.
- Mice: doc_e_003; category: contextual; paragraphs: 1; exact evidence records: 3.

## Semantic preservation

Each output was compared with its accepted 10R-C graph. Document identity, every non-role node field, all edges, and every relation evidence field were unchanged. Role IDs match the final degree-zero node IDs exactly.

## Frozen identity checks

- sfpq_gene_form_consolidated: PASS
- sfpq_chemical_remains_separate: PASS
- diabetes_mellitus_and_dm_consolidated: PASS
- rat_and_rats_remain_separate: PASS
- ezh2_grouping_preserved: PASS
- pten_grouping_preserved: PASS
- pten_genuine_self_edge_preserved: PASS
- only_frozen_pten_self_edge_present: PASS

## Viewer smoke

PASS for all four final graphs. Each loaded with complete role coverage, no missing-role diagnostic, and all genuine unconnected nodes hidden by default. Global and per-node reveal controls passed; the Species marker remained a green hexagon; the mixed-negation SFPQ-to-AD bundle and relation drill-down passed. Browser console errors and warnings: 0.
