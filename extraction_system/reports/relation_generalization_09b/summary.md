# Contract 09B — Multi-paper relation generalization probe

Status: **complete**

Frozen implementation commit: `0330923166a6b85584c1206c7bb21ae4721b99f3`

This is a frozen abstract-level probe over the eight non-KNTC1 papers in the local target corpus. It reports runtime, validation, structural, and semantic-review evidence only. No relation precision, recall, F1, or accuracy is reported because these abstracts have no adjudicated relation gold.

## Configuration

- Source corpus: `.cache/ner_target_domain/target_corpus.json`
- Excluded development paper: `PMCID:PMC10444909`
- Relation model: `gpt-5.6-luna`
- Reasoning: `max`
- Output ceiling: `128000`
- HunFlair2 model: `hunflair/hunflair2-ner`
- Scope: title plus complete abstract; full-text body sections excluded

## Per-paper results

| Paper | Entities | Nodes | Relations | Edges | Displayed | Bundles | Provider attempts | Repairs | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PMCID:PMC10770459 | 43 | 11 | 15 | 15 | 7 | 3 | 1 | 0 | success |
| PMCID:PMC11824863 | 41 | 19 | 27 | 27 | 24 | 2 | 1 | 0 | success |
| PMCID:PMC8605525 | 66 | 20 | 35 | 33 | 29 | 4 | 1 | 0 | success |
| PMID:27172794 | 41 | 16 | 21 | 19 | 14 | 4 | 1 | 0 | success |
| PMID:27370646 | 18 | 8 | 9 | 8 | 6 | 1 | 1 | 0 | success |
| PMID:31324362 | 50 | 10 | 17 | 11 | 9 | 2 | 1 | 0 | success |
| PMID:33652126 | 33 | 11 | 10 | 10 | 9 | 1 | 1 | 0 | success |
| PMID:38569671 | 39 | 16 | 19 | 17 | 11 | 4 | 1 | 0 | success |

## Semantic audit signals

Counts and flags below are descriptive review aids. They do not claim semantic correctness. See each per-paper JSON for the full signal record.

- `PMCID:PMC10770459`: intervention=11, effects=9, context=5, plain=3, negated=0, multi_evidence_edges=0, self_edges=0
- `PMCID:PMC11824863`: intervention=8, effects=12, context=10, plain=12, negated=1, multi_evidence_edges=0, self_edges=7
- `PMCID:PMC8605525`: intervention=11, effects=4, context=19, plain=16, negated=0, multi_evidence_edges=2, self_edges=3
- `PMID:27172794`: intervention=5, effects=10, context=3, plain=10, negated=0, multi_evidence_edges=2, self_edges=0
- `PMID:27370646`: intervention=5, effects=6, context=3, plain=3, negated=0, multi_evidence_edges=1, self_edges=1
- `PMID:31324362`: intervention=10, effects=8, context=10, plain=5, negated=0, multi_evidence_edges=4, self_edges=0
- `PMID:33652126`: intervention=7, effects=2, context=8, plain=1, negated=0, multi_evidence_edges=0, self_edges=0
- `PMID:38569671`: intervention=12, effects=16, context=13, plain=1, negated=0, multi_evidence_edges=2, self_edges=0

## Visual inspection

The existing Cytoscape viewer rendered all eight successful graphs from the standalone graph JSON fixtures. No prompt, schema, layout, or bundling tuning was performed after the first live paper started.

- All eight viewer summaries matched the corresponding graph JSON counts.
- All eight pages reached the loaded state with zero browser console errors.
- Graph screenshots are local ignored artifacts under `.cache/relation_generalization_09b/screenshots/`.
- Detail captures cover a simple relation, a rich intervention/effect record with assertion first, and a multi-relation bundle.

### Graph captures

| Paper | Screenshot | Observation |
|---|---|---|
| PMCID:PMC10770459 | `.cache/relation_generalization_09b/screenshots/graph_pmcid_pmc10770459.png` | Sparse mixed-type graph; bundle labels are readable and the rich evidence panel is legible. |
| PMCID:PMC11824863 | `.cache/relation_generalization_09b/screenshots/graph_pmcid_pmc11824863.png` | Larger graph with a dense central cluster and isolated components; all nodes and connections render, with some central labels visually close. |
| PMCID:PMC8605525 | `.cache/relation_generalization_09b/screenshots/graph_pmcid_pmc8605525.png` | Densest graph in the set; central labels and edges are crowded but remain rendered without clipping or viewer errors. |
| PMID:27172794 | `.cache/relation_generalization_09b/screenshots/graph_pmid_27172794.png` | Several parallel connections around the central entities; bundle counts and directed arrows remain visible. |
| PMID:27370646 | `.cache/relation_generalization_09b/screenshots/graph_pmid_27370646.png` | Small sparse graph with readable node labels and six displayed connections. |
| PMID:31324362 | `.cache/relation_generalization_09b/screenshots/graph_pmid_31324362.png` | Compact central c-Myc graph with parallel relations; labels and arrows remain inspectable. |
| PMID:33652126 | `.cache/relation_generalization_09b/screenshots/graph_pmid_33652126.png` | Compact AKT/PTEN-centered graph; the nine displayed connections render without clipping. |
| PMID:38569671 | `.cache/relation_generalization_09b/screenshots/graph_pmid_38569671.png` | Asthma-centered graph with lower isolated nodes; directed connections and type legend render clearly. |

### Detail captures

- Simple relation with empty optional fields omitted: `.cache/relation_generalization_09b/screenshots/detail_simple.png`
- Rich intervention/effect evidence with assertion first: `.cache/relation_generalization_09b/screenshots/detail_rich_intervention_effect.png`
- Relation bundle with three underlying relations: `.cache/relation_generalization_09b/screenshots/detail_bundle.png`

Dense graphs show expected visual crowding around central hubs; this is recorded as an observation, not treated as a semantic failure or used to justify layout tuning.

## Artifacts

- `summary.json` — consolidated machine-readable report
- `papers/` — one source, extraction, assembly, graph, and runtime result per paper
- `graphs/` — standalone graph JSON for each successful paper
- `.cache/relation_generalization_09b/screenshots/` — local browser captures; intentionally ignored and not committed
