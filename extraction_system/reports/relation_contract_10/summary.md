# Contract 10 — Four-paper regression

Status: **complete**

Selection and prompts were frozen before the first provider invocation; each paper used one live RE call and one live role call with zero live repairs.
A bounded deterministic assembly repair added generic compact CamelCase and adjacent same-type prefix-fragment support and rebuilt these artifacts from the saved live outputs; no provider was rerun.

| Paper | Canonical | Displayed | Unconnected | Relations | Edges | Genuine self | Alias candidates | Role records | RE attempts | Role attempts | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PMCID:PMC11824863 | 20 | 17 | 3 | 19 | 19 | 0 | 0 | 3 | 1 | 1 | success |
| PMCID:PMC8605525 | 20 | 14 | 6 | 30 | 29 | 0 | 0 | 6 | 1 | 1 | success |
| PMID:27172794 | 15 | 13 | 2 | 22 | 19 | 0 | 0 | 2 | 1 | 1 | success |
| PMID:33652126 | 10 | 8 | 2 | 12 | 10 | 1 | 0 | 2 | 1 | 1 | success |

Role quality review fields are stored in `roles/*.json`; they are inspection aids, not formal semantic metrics.

## Unconnected role review

| Paper | Node | Type | Category | Paragraphs | Evidence |
|---|---|---|---|---:|---:|

| PMCID:PMC11824863 | doc_e_003 (Mice) | Species | contextual | 1 | 3 |
| PMCID:PMC11824863 | doc_e_005 (proline and glutamine rich) | Gene | substantive | 1 | 3 |
| PMCID:PMC11824863 | doc_e_009 (Aβ1–42) | Gene | substantive | 1 | 1 |
| PMCID:PMC8605525 | doc_e_003 (diabetes mellitus) | Disease | substantive | 1 | 4 |
| PMCID:PMC8605525 | doc_e_010 (impaired) | Disease | substantive | 1 | 1 |
| PMCID:PMC8605525 | doc_e_013 (rats) | Species | contextual | 1 | 1 |
| PMCID:PMC8605525 | doc_e_014 (rat) | Species | contextual | 1 | 2 |
| PMCID:PMC8605525 | doc_e_016 (runt-related transcription factor 3) | Gene | substantive | 1 | 4 |
| PMCID:PMC8605525 | doc_e_018 (Human) | Species | contextual | 1 | 1 |
| PMID:27172794 | doc_e_011 (mouse) | Species | contextual | 1 | 1 |
| PMID:27172794 | doc_e_012 (human) | Species | contextual | 1 | 1 |
| PMID:33652126 | doc_e_008 (Edu) | Chemical | substantive | 1 | 2 |
| PMID:33652126 | doc_e_010 (serum deficiency) | Disease | substantive | 1 | 3 |

## Regression observations

09B values are historical comparison points; Contract 10 uses its own frozen prompt and provider outputs, so these are observations rather than isolated causal measurements.

- **PMCID:PMC11824863:** The frozen Contract 10 graph has no alias-induced self-edge output; the live SFPQ-to-AD mixed-negation bundle remains inspectable and the biological edge data is retained.
- **PMCID:PMC8605525:** The explicit casitas B-lineage lymphoma (Cbl) construction now groups the adjacent same-type fragment and abbreviation; rat/rats remain separate because this contract does not add morphology or general species coreference.
- **PMID:27172794:** The explicit parenthetical construction groups polycomb group protein, enhancer of zeste homologue 2, and EZH2 under one canonical node; no EZH2-specific rule exists.
- **PMID:33652126:** Two isolated substantive entities receive short grounded roles, while the PTEN biological self-relation knocks_down_expression_of remains in the graph.

## Viewer captures

Inline viewer captures cover each default paper view and panel, global reveal, substantive and contextual role expansion, Species styling, and the mixed-negation warning. The ignored capture directory is `.cache/relation_contract_10/screenshots/`.

Artifacts: `summary.json`, `graphs/`, `roles/`, and ignored raw per-paper results under `.cache/relation_contract_10/papers/`.