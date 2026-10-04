# Contract 12B — one frozen prompt refinement

The refinement does not satisfy the required scientific gate in this run: four new Cbl glucose-to-gene causal edges overstate observational evidence, and the dual-context target remains unresolved. Preserve control behavior; scientific promotion remains Talia/user's decision. No winner is declared.

This is one amendment, five completed refined generations, no paid control reruns, and no adaptive prompt edits. Production defaults and the original Contract 10 prompt remain unchanged. Talia/user retains the scientific promotion decision.

## Target findings

- Cbl/JAK2 recovery: Yes: refined [25] E55→E58 explicitly preserves the joint JAK2-and-STAT4 overexpression result. Do not interpret this as proof of an independently tested JAK2-only intervention.
- Cbl/STAT4 recovery: Yes: refined [26] E56→E58 preserves the same joint intervention and abrogation result.
- Runx3 retained: Yes: control [21] corresponds to refined [27] E57→E58.
- HG-induced HUVEC context preservation: Partial source coverage, not the requested clean metadata improvement. Refined [11–14] still retain only rat tissues; [15–18] add glucose→gene edges with HUVEC context and high-glucose intervention but unsupported causal predicates. The original dual setting is not preserved together in the existing DM edges.
- Serum deprivation → increased PTEN expression: Yes: refined PTEN [3] E19(PTEN)→E18(H9c2), expression_increased_in, with serum deprivation in intervention and increased PTEN expression in effects. Serum deprivation is not a supplied entity, so no invented condition endpoint was used.
- PTEN artificial self-edge: No PTEN self-edge in either output or graph.
- 11U endpoint/topology discipline: Preserved for all ten original relations: same endpoint IDs and directions after scientific pairing. Two explicit cohort-specific AST→ALT ratio findings aggregate to one additional graph edge. No measurement→subject edges, gene→gene cohort substitution, standalone context-edge proliferation, or exact duplicates. However, two enriched liver/hyperglycemic context values are source-supported only by the preceding sentence absent from their saved evidence.

## Frozen execution

| Case | Control → refined relations | Control → refined edges | Repairs | Seconds | Input / output / reasoning tokens | Tier |
|---|---:|---:|---:|---:|---:|---|
| pmcid_pmc11824863 | 13 → 13 | 13 → 13 | 0 | 57.261 | 3834 / 3229 / 990 | Standard/default |
| pmcid_pmc8605525 | 26 → 33 | 25 → 31 | 0 | 71.980 | 5372 / 4454 / 1026 | Standard/default |
| pmid_27172794 | 20 → 20 | 18 → 18 | 0 | 67.012 | 3839 / 3282 / 918 | Standard/default |
| pmid_33652126 | 7 → 11 | 6 → 9 | 0 | 53.055 | 3394 / 2707 / 975 | Standard/default |
| contract11u_passage_001 | 10 → 12 | 10 → 11 | 0 | 44.915 | 5486 / 2667 / 516 | Standard/default |

The last three cases succeeded on one operational recovery after initial `create_failed` APIConnectionErrors with no response IDs. A read-only provider request independently failed with DNS `gaierror(11001)`; endpoint DNS subsequently resolved. Initial records and recovery records are preserved separately. Eight create attempts are accounted for: five completed generations and three failures; none of the completed cases was rerun. Failed-attempt token usage is unavailable, not zero. No raw error messages, credentials, or endpoint URLs are stored.

## Rich-field diagnostics

Across all five cases (including flagged edges): `{"control": {"context": 38, "effects": 14, "intervention": 28}, "refined": {"context": 58, "effects": 38, "intervention": 35}}`.

On the 74 manually paired, otherwise-valid findings, control/refined population is `{"control": {"context": 37, "effects": 13, "intervention": 27}, "refined": {"context": 45, "effects": 31, "intervention": 26}}`. This avoids crediting the four unsupported glucose causal edges or other additions as enrichment of existing findings. Intervention count falls by one as the PTEN title condition moves into context; retained intervention wording is fuller in SFPQ. These pairs are scientific review proposals, not final accepted gold.

Excluding the four flagged causal edges gives 85 provisionally source-supported refined relations: 31 with intervention, 38 with effects, 54 with context. The two 11U evidence-locality concerns still apply to those otherwise-supported relations. Scientific acceptance of these records remains pending.

SFPQ has substantially fuller explicit outcomes and experimental setting; Cbl gains coverage mainly through additional edges while the original dual-context omissions persist. EZH2 gains some fields but loses maintenance outcomes on two pathway edges. See each case's matched-finding table; totals are not an optimization target.

## Prompt

`prompt_refined.txt` is exactly `prompt_control.txt` plus one newline and the following amendment. No other control prompt text was changed.

```text
Relation selection and relation enrichment are separate decisions.

Remain conservative when deciding whether a relation should exist. Do not create
additional relations merely to increase coverage or to capture intervention,
effects, or context.

Before finalizing the response, perform a final source-grounded coverage check
for explicit relations between supplied entities. When a coordinated statement
explicitly names multiple supplied entities as independently participating in
the same asserted relationship, preserve each explicitly supported relation
rather than selecting only one representative participant. Expand only when the
source grammar and evidence independently support each participant's relation.

Do not omit a direct explicit experimental result merely because a broader
mechanistic, interpretive, or summary relation concerning the same topic has
already been extracted.

Once a relation is explicitly supported and selected, re-read its evidence and
preserve all explicit information that materially belongs to that relation.
Do not leave intervention, effects, or context empty when the source explicitly
states a relevant intervention, outcome, or experimental/biological condition.

Populate those fields only from explicit source wording. Do not infer missing
information, use external biomedical knowledge, use context as a dumping ground,
or hide another material supplied entity inside metadata when it should be
represented by a separate grounded relation.

Prefer omission over unsupported inference, but prefer explicit preservation
over unnecessary omission.
```

## Validation and limits

170 Python tests, including the 25 lifecycle/configuration/transport cases, and 13 viewer tests passed. All ten graphs pass the unchanged viewer adapter and Cytoscape element conversion, preserving direction, evidence, rich fields, node reveals, and input JSON. This verifies viewer data compatibility; no new browser interaction test was performed.

Evidence substring, endpoint ID, schema, repair and graph checks are mechanical. They do not prove causality, scientific endpoint meaning, or metadata entailment. All five refined outputs were manually read against the frozen passages here; judgments are review proposals, not independent gold labels. One completion per prompt and case cannot separate all sampling variability from prompt effects. Exact duplicates are measured after existing normalization; raw provider duplicates dropped by validation cannot be inferred from these counts.

## Review artifacts

`frozen_set_manifest.json` records file/input/request/prompt/schema hashes and control equivalence. `telemetry.json` includes saved control telemetry, initial failures, and effective completions. Each case folder contains unchanged input, control, initial refined output, attempt events, comparison and (where needed) one recovery. `graphs/control/` and `graphs/refined/` contain all ten graphs. `scientific_review.json` records explicit judgments and equivalence pairs; `verification.json` records mechanical checks. Historical 12A and 11U artifacts remain untouched.

## Remaining promotion risks

- Cbl [15–18] converts an expression observation in a high-glucose setting into glucose-driven decreases/increases. Exact verbatim evidence does not validate this causal edge meaning.
- The requested DM-rat-tissue/HG-HUVEC dual setting is still missing from existing Cbl/JAK2/Runx3/STAT4 DM-edge context.
- 11U [7–8] adds liver/hyperglycemic-state context from an adjacent sentence outside saved evidence; source-level truth is not sufficient for the assertion-within-evidence requirement.
- EZH2 loses explicit maintenance outcomes on the two Wnt/β-catenin pathway edges while adding a low-value patient→CRC edge and changing the representation of high EZH2 expression.
- SFPQ adds a near-redundant title result edge with another predicate and substantially expands evidence/intervention wording. No exact duplicate explosion, but graph readability can worsen.
- One generation per prompt/case is not a statistical estimate of improvement; Talia should review qualified pathway/member and joint-intervention representations before any later promotion.

## PMCID:PMC11824863 / pmcid_pmc11824863

13 → 13 relations; 13 → 13 graph edges.

All major SFPQ result/mechanism findings remain. Explicit APP, Tau, GST, HO-1, Bcl-2/Bax and PI3K/AKT ratio outcomes are more fully populated. AAV/hippocampal manipulation is carried in evidence and metadata, with longer evidence spans. Selection is not an unqualified improvement because a title result repeats the abstract result using a distinct predicate.

### Scientifically distinct findings and review flags

Control [3] SFPQ overexpression in the hippocampus of AD mice is no longer a standalone setup edge; its explicit AAV/hippocampal information is retained on refined result edges [4–8,10–11]. No major scientifically distinct finding was lost.

Refined [0] is a title formulation of cognition/memory improvement already represented by refined [4]; it is additional source evidence rather than a new experimental finding.

- Refined [0] and [4] share assembled SFPQ→AD endpoints but have different cognition/recognition predicates: near-redundant graph connections, not exact duplicates.
- Evidence for refined [10–11] spans the setup and several result sentences so the extra AAV/hippocampal wording is traceable, but increases reading burden.
- No unsupported new causal edges identified in this case. Brain-neuron wording remains in effects rather than a separately populated context field; completeness is still imperfect.

Unpaired records below require interpretation: predicate/mention changes alone do not establish scientific novelty.

Control unpaired relations:

- [3] E16 (SFPQ) → E17 (AD): overexpressed_in_model_of. Adeno-associated virus was administered to overexpress SFPQ in the hippocampus of AD mice.

Refined unpaired relations:

- [0] E1 (SFPQ) → E2 (AD): improves_cognition_and_memory_in. SFPQ overexpression improves cognition and memory in AD mice.

### Same-finding field and endpoint changes

Pairs below were manually assessed for scientific equivalence; indices are zero-based in the preserved relation arrays.

| Control → refined index | Endpoint / predicate change | Rich-field change |
|---|---|---|
| 1 → 2 | {} | {"effects": {"control": [], "refined": ["Antioxidant-related functions", "Regulation of gene expression within brain neurons"]}} |
| 2 → 3 | {"predicate": {"control": "establishes_model_of", "refined": "induces_disease_model"}} | {"context": {"control": ["mouse model"], "refined": ["Mouse model"]}, "effects": {"control": ["establishment of an AD mouse model"], "refined": ["Establishment of an AD mouse model"]}, "intervention": {"control": "lateral ventricular injection of amyloid-beta1–42", "refined": "Lateral ventricular injection of amyloid-beta1–42"}} |
| 4 → 4 | {} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampus"]}, "effects": {"control": ["improved recognition", "improved memory"], "refined": ["Improved recognition", "Improved memory"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 5 → 5 | {"predicate": {"control": "reduces_protein_levels", "refined": "reduces_protein_level"}} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampal SFPQ overexpression"]}, "effects": {"control": [], "refined": ["Reduced amyloid precursor protein"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 6 → 6 | {"predicate": {"control": "reduces_protein_levels", "refined": "reduces_protein_level"}} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampal SFPQ overexpression"]}, "effects": {"control": [], "refined": ["Reduced Tau protein"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 7 → 7 | {} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampal SFPQ overexpression"]}, "effects": {"control": [], "refined": ["Upregulated glutathione S-transferase"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 8 → 8 | {} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampal SFPQ overexpression"]}, "effects": {"control": [], "refined": ["Upregulated heme oxygenase-1"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 9 → 9 | {"predicate": {"control": "increased_ratio_to", "refined": "has_increased_ratio_to"}} | {"effects": {"control": [], "refined": ["Increased Bcl-2-to-Bax ratio"]}} |
| 10 → 10 | {} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampal SFPQ overexpression"]}, "effects": {"control": [], "refined": ["Elevated phosphorylated PI3K-to-PI3K ratio"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 11 → 11 | {} | {"context": {"control": ["AD mice"], "refined": ["AD mice", "Hippocampal SFPQ overexpression"]}, "effects": {"control": [], "refined": ["Elevated phosphorylated AKT-to-AKT ratio"]}, "intervention": {"control": "SFPQ overexpression", "refined": "Adeno-associated virus administration to overexpress SFPQ in the hippocampus"}} |
| 12 → 12 | {"predicate": {"control": "potential_preventive_and_therapeutic_target_for", "refined": "potential_prevention_and_treatment_target_for"}} | {} |

### Grounding and graph comparison

All normalized relations pass Contract 10 validation. Both graphs retain the same 20 nodes and exact rich evidence projection. Exact edge-key differences (including wording changes) and complete assertions/evidence are in `comparison.json`.

Rich diagnostics: `{"control": {"context": 9, "effects": 3, "intervention": 9}, "refined": {"context": 9, "effects": 11, "intervention": 9}}`. These population counts do not certify scientific completeness.

## PMCID:PMC8605525 / pmcid_pmc8605525

26 → 33 relations; 25 → 31 graph edges.

The two targeted JAK2/STAT4 relationships are recovered and Runx3 remains. All control findings remain represented. However, four new glucose→gene causal predicates exceed the observational wording, so the required conservative selection gate is not satisfied.

### Scientifically distinct findings and review flags

None identified after scientific equivalence pairing. Most apparent exact-key differences are predicate wording changes.

Refined [25–26] recover the JAK2/STAT4 joint-overexpression abrogation finding. [32] adds a tentative future Cbl-based DM-treatment interpretation explicitly qualified in the source. [15–18] attempt to express the omitted HG-HUVEC observations but misstate them as glucose-caused expression changes; do not accept these as recovered causal findings.

- Material unsupported causal pattern: [15] glucose reduces Cbl expression; [16–18] glucose increases JAK2, Runx3 and STAT4 expression. Evidence says only that expression differs in DM rat tissues and HG-induced HUVECs.
- Dual context unresolved: [11–14] still omit HG-induced HUVECs from DM gene-expression edges. Added causal edges do not cure that metadata omission.
- Joint grammar: [25–26] retain intervention "Overexpression of JAK2 and STAT4" and the joint assertion. There is no evidence here of two independently tested individual overexpression experiments. Both supplied participants have explicit edges, so the other participant is not hidden solely in metadata.
- No exact duplicate relation/graph-evidence explosion. Several Cbl→endothelial-dysfunction title/result/conclusion records remain semantically overlapping as in control. Effects/context on many existing edges remain empty despite fuller results being available.

Unpaired records below require interpretation: predicate/mention changes alone do not establish scientific novelty.

Control unpaired relations:

None.

Refined unpaired relations:

- [15] E36 (glucose) → E46 (Cbl): reduces_expression. Cbl was reduced in high-glucose-induced HUVECs.
- [16] E36 (glucose) → E43 (JAK2): increases_expression. JAK2 was elevated in high-glucose-induced HUVECs.
- [17] E36 (glucose) → E44 (Runx3): increases_expression. Runx3 was elevated in high-glucose-induced HUVECs.
- [18] E36 (glucose) → E45 (STAT4): increases_expression. STAT4 was elevated in high-glucose-induced HUVECs.
- [25] E55 (JAK2) → E58 (Cb1): abrogates_effect_on_endothelial_function. Overexpression of JAK2 and STAT4 increased apoptosis of HUVECs and abrogated the effect of Cb1 on endothelial function.
- [26] E56 (STAT4) → E58 (Cb1): abrogates_effect_on_endothelial_function. Overexpression of JAK2 and STAT4 increased apoptosis of HUVECs and abrogated the effect of Cb1 on endothelial function.
- [32] E65 (Cbl) → E66 (DM): proposed_treatment_for. The evidence might support a novel Cbl-based treatment against DM in the future.

### Same-finding field and endpoint changes

Pairs below were manually assessed for scientific equivalence; indices are zero-based in the preserved relation arrays.

| Control → refined index | Endpoint / predicate change | Rich-field change |
|---|---|---|
| 0 → 0 | {"predicate": {"control": "attenuates", "refined": "alleviates"}} | {"intervention": {"control": "Cbl overexpression", "refined": "Overexpression of Cbl"}} |
| 1 → 1 | {} | {"intervention": {"control": "Cbl overexpression", "refined": "Overexpression of Cbl"}} |
| 2 → 2 | {} | {"intervention": {"control": "Cbl overexpression", "refined": "Overexpression of Cbl"}} |
| 4 → 3 | {} | {"intervention": {"control": "Cbl overexpression", "refined": "Overexpression of Cbl"}} |
| 5 → 5 | {"predicate": {"control": "classified_as", "refined": "is_a"}} | {} |
| 6 → 6 | {"predicate": {"control": "characterized_by_impairment_of", "refined": "characterized_by_impaired_function"}} | {} |
| 7 → 7 | {"predicate": {"control": "characterized_by_impaired_bioavailability_of", "refined": "characterized_by_impaired_bioavailability"}} | {} |
| 9 → 9 | {"predicate": {"control": "induces_model_of", "refined": "induces"}} | {"intervention": {"control": "Intraperitoneal injection of streptozotocin", "refined": "intraperitoneal injection of streptozotocin"}} |
| 10 → 10 | {"predicate": {"control": "induces_model_of", "refined": "induces"}} | {"context": {"control": ["human umbilical vein endothelial cells", "in vitro model"], "refined": ["Human umbilical vein endothelial cells (HUVECs)", "in vitro model"]}, "intervention": {"control": "Culture in high glucose", "refined": "culture in high glucose condition"}} |
| 11 → 11 | {"predicate": {"control": "expression_decreased_in", "refined": "has_reduced_expression_in"}} | {} |
| 12 → 12 | {"predicate": {"control": "expression_increased_in", "refined": "has_elevated_expression_in"}} | {} |
| 13 → 13 | {"predicate": {"control": "expression_increased_in", "refined": "has_elevated_expression_in"}} | {} |
| 14 → 14 | {"predicate": {"control": "expression_increased_in", "refined": "has_elevated_expression_in"}} | {} |
| 15 → 19 | {} | {"effects": {"control": ["restored vasodilation", "suppressed apoptosis of HUVECs"], "refined": ["restoring vasodilation", "suppressing apoptosis of HUVECs"]}, "intervention": {"control": "Cbl overexpression", "refined": "overexpression of Cbl"}} |
| 16 → 20 | {"predicate": {"control": "increases_production_of", "refined": "increases_production"}} | {"intervention": {"control": "Cbl overexpression", "refined": "overexpression of Cbl"}} |
| 17 → 21 | {"predicate": {"control": "enhances_ubiquitination_of", "refined": "enhances_ubiquitination"}} | {} |
| 18 → 22 | {"predicate": {"control": "decreases_expression_of", "refined": "decreases_expression"}} | {} |
| 19 → 23 | {"predicate": {"control": "decreases_expression_of", "refined": "decreases_expression"}} | {} |
| 20 → 24 | {"predicate": {"control": "increases_expression_of", "refined": "increases_expression"}} | {} |
| 21 → 27 | {"predicate": {"control": "abrogates_endothelial_effect_of", "refined": "abrogates_effect_on_endothelial_function"}} | {"context": {"control": ["human umbilical vein endothelial cells"], "refined": ["HUVECs"]}, "intervention": {"control": "Runx3 overexpression", "refined": "Overexpression of Runx3"}} |
| 22 → 28 | {} | {"context": {"control": ["diabetes mellitus"], "refined": ["DM"]}} |
| 23 → 29 | {} | {"context": {"control": ["diabetes mellitus"], "refined": ["DM"]}} |
| 24 → 30 | {} | {"context": {"control": ["diabetes mellitus"], "refined": ["DM"]}} |
| 25 → 31 | {"predicate": {"control": "inhibits_expression_of", "refined": "inhibits_expression"}} | {"context": {"control": ["diabetes mellitus"], "refined": ["DM"]}} |

### Grounding and graph comparison

All normalized relations pass Contract 10 validation. Both graphs retain the same 20 nodes and exact rich evidence projection. Exact edge-key differences (including wording changes) and complete assertions/evidence are in `comparison.json`.

Rich diagnostics: `{"control": {"context": 15, "effects": 2, "intervention": 9}, "refined": {"context": 21, "effects": 4, "intervention": 15}}`. These population counts do not certify scientific completeness.

## PMID:27172794 / pmid_27172794

20 → 20 relations; 18 → 18 graph edges.

Core EZH2 knockdown, marker-subpopulation, tumor-initiation, Wnt/β-catenin, p21cip1 requirement and EPZ-6438 findings remain. Richness is mixed: some outcomes/settings improve, while maintenance effects disappear from the two pathway edges. Representation of the advanced-stage expression finding changes endpoints/direction relative to control.

### Scientifically distinct findings and review flags

Control [8] explicitly represented lower expression in non-CCS-like cells; refined [8] retains that comparison in the assertion/context of its CCS edge, so it is not a lost scientific observation. Control [3] EZH2→CRC high expression is recast as refined [4] patients→EZH2; the advanced-stage setting remains.

Refined [3] patients→CRC has_disease is explicit cohort information but adds a low-value context relation. It is not a new mechanism or experimental result.

- Endpoint/direction representation change: control [3] E13(EZH2)→E10(CRC) becomes refined [4] E9(patients)→E12(EZH2). This is a different representation of the same observation, not a claimed reversal of biological regulation.
- Control [12–13] effects contain maintenance of CCS-like properties; refined [12–13] effects are empty even though assertions retain that explicit outcome.
- Refined [9–10] correctly keep CD133+/CD44+ as a jointly marker-defined subpopulation rather than inventing independent reductions of marker expression. The added explanatory wording is more verbose.
- No newly unsupported biological causality identified; pre-existing group/pathway projection conventions remain for review.

Unpaired records below require interpretation: predicate/mention changes alone do not establish scientific novelty.

Control unpaired relations:

- [8] E19 (EZH2) → E21 (CCS): less_highly_expressed_in. EZH2 expression was lower in the non-CCS-like cell subpopulation than in the CCS-like cell subpopulation.

Refined unpaired relations:

- [3] E9 (patients) → E10 (CRC): has_disease. The patients had advanced-stage CRC.

### Same-finding field and endpoint changes

Pairs below were manually assessed for scientific equivalence; indices are zero-based in the preserved relation arrays.

| Control → refined index | Endpoint / predicate change | Rich-field change |
|---|---|---|
| 0 → 0 | {} | {"effects": {"control": [], "refined": ["colorectal cancer stem-like cell expansion"]}} |
| 3 → 4 | {"predicate": {"control": "highly_expressed_in", "refined": "highly_expresses"}, "source": {"control": "E13", "refined": "E9"}, "target": {"control": "E10", "refined": "E12"}} | {"context": {"control": ["Advanced-stage CRC"], "refined": ["patients with advanced stage CRC"]}} |
| 4 → 5 | {"predicate": {"control": "highly_expressed_in", "refined": "expressed_in"}} | {"context": {"control": [], "refined": ["tumor tissues"]}} |
| 5 → 6 | {} | {"context": {"control": ["Tumor tissues"], "refined": ["tumor tissues"]}, "effects": {"control": [], "refined": ["poor patient prognosis"]}} |
| 6 → 7 | {"predicate": {"control": "reduces_cell_proliferation", "refined": "silencing_reduces_cell_proliferation"}} | {"context": {"control": [], "refined": ["CRC cells"]}, "effects": {"control": ["Reduced CRC cell proliferation"], "refined": ["reduced CRC cell proliferation"]}, "intervention": {"control": "EZH2 silencing", "refined": "silencing EZH2"}} |
| 7 → 8 | {"predicate": {"control": "more_highly_expressed_in", "refined": "preferentially_expressed_in"}} | {"context": {"control": [], "refined": ["CCS-like cell subpopulation compared with the non-CCS-like cell subpopulation"]}} |
| 9 → 9 | {"predicate": {"control": "reduces_marker_positive_subpopulation", "refined": "knockdown_reduces_marker_defined_subpopulation"}} | {"effects": {"control": ["Significant reduction of the double-positive subpopulation"], "refined": ["significantly reduced CD133+/CD44+ subpopulation"]}} |
| 10 → 10 | {"predicate": {"control": "reduces_marker_positive_subpopulation", "refined": "knockdown_reduces_marker_defined_subpopulation"}} | {"effects": {"control": ["Significant reduction of the double-positive subpopulation"], "refined": ["significantly reduced CD133+/CD44+ subpopulation"]}} |
| 11 → 11 | {"predicate": {"control": "impairs_initiating_capacity", "refined": "knockdown_impairs_initiating_capacity"}} | {"context": {"control": ["Re-implantation mouse model"], "refined": ["re-implantation mouse model"]}, "effects": {"control": ["Strong impairment of tumor-initiating capacity"], "refined": ["strongly impaired tumor-initiating capacity"]}} |
| 12 → 12 | {} | {"context": {"control": ["Gene expression data from 433 human CRC specimens from TCGA database", "In vitro results"], "refined": ["gene expression data from 433 human CRC specimens from TCGA database", "in vitro results"]}, "effects": {"control": ["Maintenance of CCS-like cell properties"], "refined": []}} |
| 13 → 13 | {} | {"context": {"control": ["Gene expression data from 433 human CRC specimens from TCGA database", "In vitro results"], "refined": ["gene expression data from 433 human CRC specimens from TCGA database", "in vitro results"]}, "effects": {"control": ["Maintenance of CCS-like cell properties"], "refined": []}} |
| 18 → 18 | {} | {"effects": {"control": ["Prevention of CRC progression"], "refined": ["prevented CRC progression"]}, "intervention": {"control": "EPZ-6438 treatment", "refined": "EPZ-6438"}} |
| 19 → 19 | {} | {"effects": {"control": [], "refined": ["maintenance of CCS-like cell characteristics"]}} |

### Grounding and graph comparison

All normalized relations pass Contract 10 validation. Both graphs retain the same 15 nodes and exact rich evidence projection. Exact edge-key differences (including wording changes) and complete assertions/evidence are in `comparison.json`.

Rich diagnostics: `{"control": {"context": 5, "effects": 7, "intervention": 5}, "refined": {"context": 9, "effects": 8, "intervention": 5}}`. These population counts do not certify scientific completeness.

## PMID:33652126 / pmid_33652126

7 → 11 relations; 6 → 9 graph edges.

The direct serum-deprivation PTEN-expression result is recovered with supplied PTEN/H9c2 endpoints and explicit serum-deprivation intervention. No PTEN knockdown self-edge is added. Original mechanisms and measured ROS effects remain; reversal metadata gains explicit outcomes.

### Scientifically distinct findings and review flags

None. Control [6] uses AKT E26; refined [8] uses its explicit full-name protein kinase B E25, which assembles to the same node.

[3] recovers increased PTEN expression in serum-deprived H9c2 cells. [6] separately preserves PI3K-inhibitor reversal of ROS suppression from "All these effects could be reversed". [9–10] project the conclusion's PI3K/AKT pathway involvement onto supplied pathway members using qualified participates_in_pathway_involved_in predicates.

- No artificial PTEN→PTEN relation or graph self-edge.
- Refined [9–10] are qualified pathway-member projections of a group-level conclusion, not independently measured PI3K-only/AKT-only cytotoxicity effects. Their additional graph value is a reviewer judgment.
- The title serum-deprivation information moves from intervention to context in [0]; the information is preserved despite one fewer populated intervention in that matched relation.
- The inhibitor→PTEN reversal edge [5] omits ROS from its metadata while the separate grounded inhibitor→ROS edge [6] captures that supplied material participant.

Unpaired records below require interpretation: predicate/mention changes alone do not establish scientific novelty.

Control unpaired relations:

None.

Refined unpaired relations:

- [3] E19 (PTEN) → E18 (H9c2): expression_increased_in. PTEN expression increased in H9c2 cells under serum deprivation.
- [6] E22 (phosphatidylinositol 3-kinase) → E21 (ROS): inhibition_reverses_suppression_of_production. A phosphatidylinositol 3-kinase inhibitor could reverse the suppression of serum deprivation-induced ROS production observed in the knockdown experiment.
- [9] E30 (PI3K) → E32 (cytotoxicity): participates_in_pathway_involved_in. PI3K participates in the PTEN/PI3K/AKT pathway implicated in serum deprivation-induced cytotoxicity in H9c2 cells.
- [10] E31 (AKT) → E32 (cytotoxicity): participates_in_pathway_involved_in. AKT participates in the PTEN/PI3K/AKT pathway implicated in serum deprivation-induced cytotoxicity in H9c2 cells.

### Same-finding field and endpoint changes

Pairs below were manually assessed for scientific equivalence; indices are zero-based in the preserved relation arrays.

| Control → refined index | Endpoint / predicate change | Rich-field change |
|---|---|---|
| 0 → 0 | {} | {"context": {"control": ["H9c2 cells"], "refined": ["H9c2 cells", "serum deprivation"]}, "intervention": {"control": "serum deprivation", "refined": null}} |
| 1 → 1 | {} | {"context": {"control": [], "refined": ["cardiomyocytes"]}} |
| 2 → 2 | {"predicate": {"control": "used_to_model_apoptosis_of", "refined": "models_apoptosis_process_of"}} | {} |
| 3 → 4 | {} | {"effects": {"control": [], "refined": ["inhibited ROS production"]}} |
| 4 → 5 | {} | {"effects": {"control": [], "refined": ["reversal of inhibition of cell apoptosis", "reversal of inhibition of DNA damage", "reversal of increased cell proliferation"]}, "intervention": {"control": "PI3K inhibition following PTEN knockdown using siRNA", "refined": "phosphatidylinositol 3-kinase inhibitor following PTEN knockdown using siRNA"}} |
| 6 → 8 | {"source": {"control": "E26", "refined": "E25"}} | {} |

### Grounding and graph comparison

All normalized relations pass Contract 10 validation. Both graphs retain the same 10 nodes and exact rich evidence projection. Exact edge-key differences (including wording changes) and complete assertions/evidence are in `comparison.json`.

Rich diagnostics: `{"control": {"context": 5, "effects": 0, "intervention": 4}, "refined": {"context": 9, "effects": 4, "intervention": 5}}`. These population counts do not certify scientific completeness.

## PMCID:PMC10770459 / contract11u_passage_001

10 → 12 relations; 10 → 11 graph edges.

All ten original scientific relations retain exactly the same supplied endpoint IDs/directions. Rich fields preserve explicitly measured outcomes, cohort identity, plasma sampling and times. Two new AST/ALT ratio relations are explicitly quantified and aggregate into one edge with separate evidence per cohort. Edge discipline stays clean, but two metadata entries are not bounded by their saved evidence.

### Scientifically distinct findings and review flags

None after pairing.

[4] AST/ALT ratio ≈1 in iHMGB1 KO TMX STZ mice and [5] ratio ≈2 in HMGB1 Flox TMX STZ mice. These are source-explicit measurement relationships, not measurement→subject edges.

- No gratuitous measurement→subject edges, gene→gene cohort substitution, new standalone context relations, or exact duplicate relations. Cohort names remain explicit qualifiers; mice endpoints remain the frozen species mentions.
- Evidence fidelity regression at [7–8]: Liver and Hyperglycemic state are present in context/assertion but only the preceding sentence supplies them; the saved evidence begins with "HMGB1 Flox TMX STZ mice displayed". The values are source-supported, but strict assertion-within-supporting-evidence coverage is incomplete.
- Ratios [4–5] share the AST→ALT graph key but contain distinct cohort-specific values; two evidence records on one edge are useful aggregation rather than duplication.

Unpaired records below require interpretation: predicate/mention changes alone do not establish scientific novelty.

Control unpaired relations:

None.

Refined unpaired relations:

- [4] E527 (AST) → E528 (ALT): has_ratio_to. The AST-to-ALT ratio in iHMGB1 KO TMX STZ mice was approximately 1.
- [5] E535 (AST) → E536 (ALT): has_ratio_to. HMGB1 Flox TMX STZ mice exhibited an AST-to-ALT ratio of around 2, substantially higher than the ratio of approximately 1 in iHMGB1 KO TMX STZ mice.

### Same-finding field and endpoint changes

Pairs below were manually assessed for scientific equivalence; indices are zero-based in the preserved relation arrays.

| Control → refined index | Endpoint / predicate change | Rich-field change |
|---|---|---|
| 0 → 0 | {} | {"effects": {"control": ["Hyperglycemia reduction"], "refined": ["hyperglycemia reduction"]}} |
| 1 → 1 | {"predicate": {"control": "has_comparable_levels_of", "refined": "has_comparable_plasma_levels_of"}} | {"context": {"control": ["Plasma samples collected 10 weeks after the last injection"], "refined": ["Plasma samples", "10 weeks post last injection", "HMGB1 Flox TMX STZ and iHMGB1 KO TMX STZ mouse groups"]}, "effects": {"control": [], "refined": ["Comparable plasma ALT levels between the two groups"]}} |
| 2 → 2 | {"predicate": {"control": "has_elevated_levels_of", "refined": "has_elevated_plasma_levels_of"}} | {"context": {"control": ["Plasma samples collected 10 weeks after the last injection"], "refined": ["Plasma samples", "10 weeks post last injection", "HMGB1 Flox TMX STZ mouse cohort"]}, "effects": {"control": [], "refined": ["Significantly elevated plasma AST levels relative to iHMGB1 KO TMX STZ mice"]}} |
| 5 → 7 | {"predicate": {"control": "has_increased_droplets_of", "refined": "has_increased_droplet_accumulation_of"}} | {"context": {"control": [], "refined": ["Liver", "Hyperglycemic state", "HMGB1 Flox TMX STZ mouse cohort"]}, "effects": {"control": [], "refined": ["Increased macrovesicular lipid droplets relative to iHMGB1 KO TMX STZ mice"]}} |
| 6 → 8 | {} | {"context": {"control": [], "refined": ["Liver", "Hyperglycemic state", "HMGB1 Flox TMX STZ mouse cohort"]}, "effects": {"control": [], "refined": ["Greater signs of mononuclear inflammatory infiltration relative to iHMGB1 KO TMX STZ mice"]}} |
| 7 → 9 | {} | {"context": {"control": [], "refined": ["HMGB1 Flox TMX STZ mouse cohort"]}, "effects": {"control": [], "refined": ["Increased glycogen storage"]}} |
| 8 → 10 | {} | {"context": {"control": [], "refined": ["HMGB1 Flox TMX STZ mouse cohort"]}, "effects": {"control": [], "refined": ["Increased lipid uptake"]}} |
| 9 → 11 | {"predicate": {"control": "has_elevated_levels_of", "refined": "has_elevated_plasma_levels_of"}} | {"context": {"control": ["Plasma samples collected 10 weeks after hyperglycemia development"], "refined": ["Plasma samples", "10 weeks post hyperglycemia development", "iHMGB1 KO TMX STZ mouse cohort"]}, "effects": {"control": [], "refined": ["Significantly elevated circulating Cystatin C levels relative to HMGB1 Flox TMX STZ mice"]}} |

### Grounding and graph comparison

All normalized relations pass Contract 10 validation. Both graphs retain the same 18 nodes and exact rich evidence projection. Exact edge-key differences (including wording changes) and complete assertions/evidence are in `comparison.json`.

Rich diagnostics: `{"control": {"context": 4, "effects": 2, "intervention": 1}, "refined": {"context": 10, "effects": 11, "intervention": 1}}`. These population counts do not certify scientific completeness.
