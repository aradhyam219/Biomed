# Target-domain biomedical NER reconnaissance

AIONER and HunFlair2 were compared on the science-team papers using the same canonical article text. There is no target-domain gold annotation, so this report does not claim correctness or select a production model.

## Corpus acquisition

- Papers: 9
- Full text: 3 (PMCID:PMC8605525, PMCID:PMC11824863, PMCID:PMC10770459)
- Abstract only: 6 (PMID:27370646, PMID:27172794, PMID:33652126, PMID:31324362, PMID:38569671, PMCID:PMC10444909)
- Characters: 135309
- Sentences: 999

| Paper | PMID | PMCID | Mode | Characters | Sections |
|---|---:|---|---|---:|---|
| PMID:27370646 | 27370646 |  | abstract_only | 1217 | title, abstract |
| PMID:27172794 | 27172794 |  | abstract_only | 1620 | title, abstract |
| PMID:33652126 | 33652126 |  | abstract_only | 1516 | title, abstract |
| PMID:31324362 | 31324362 |  | abstract_only | 1814 | title, abstract / BACKGROUND, abstract / METHODS, abstract / RESULTS, abstract / CONCLUSIONS |
| PMCID:PMC8605525 | 34798872 | PMC8605525 | full_text | 47245 | title, abstract, Background, Materials and methods / Ethical statement, Materials and methods / Bioinformatics analysis, Materials and methods / Mouse model of DM, Materials and methods / Hematoxylin–eosin (HE) staining, Materials and methods / Measurement of vasodilation, Materials and methods / Immunohistochemistry (IHC), Materials and methods / Isolation of HUVECs, Materials and methods / Cell culture and infection, Materials and methods / Western blot analysis, Materials and methods / Reverse transcription quantitative polymerase chain reaction (RT-qPCR), Materials and methods / Ubiquitination assay, Materials and methods / Half-life assay, Materials and methods / NO detection, Materials and methods / Flow cytometry, Materials and methods / Chromatin immunoprecipitation (ChIP)-qPCR, Materials and methods / Terminal deoxynucleotidyl transferase (TdT)-mediated 2'-deoxyuridine 5'-triphosphate nick end-labeling (TUNEL) staining, Materials and methods / Statistical analysis, Results / Cbl is poorly expressed in aortic tissues of DM rats and HG-induced cell model, Results / Cbl inhibits the JAK2/STAT4 pathway and affects endothelial cell apoptosis, Results / Cbl inhibits the JAK2/STAT4 pathway through promoting JAK2 protein ubiquitination, Results / STAT4 promotes the expression of Runx3 by regulating the H3K4me3 level in the promoter region of Runx3, Results / STAT4 promotes HUVEC apoptosis through Runx3, Results / Cbl inhibits HUVEC apoptosis by inhibiting the activation of the JAK2/STAT4 pathway through reducing Runx3 expression, Results / Cbl alleviates HUVEC dysfunction in DM rats by inhibiting the activation of the JAK2/STAT4 pathway through reducing Runx3 expression, Discussion, Conclusion, Supplementary Information |
| PMCID:PMC11824863 | 39949834 | PMC11824863 | full_text | 30020 | title, abstract, 1. Introduction, 2. Materials and Methods / 2.1. Animals, 2. Materials and Methods / 2.2. Brain Stereotaxic Instrument Injection, 2. Materials and Methods / 2.3. Aβ1–42 Solution Preparation, 2. Materials and Methods / 2.4. AAV9-Green Fluorescent Protein (GFP) Injection, 2. Materials and Methods / 2.5. Western Blotting, 2. Materials and Methods / 2.6. Hematoxylin and Eosin (HE) Staining, 2. Materials and Methods / 2.7. Immunofluorescence Experiment, 2. Materials and Methods / 2.8. Novel Object Recognition (NOR) Experiment, 2. Materials and Methods / 2.9. Y-Maze Test, 2. Materials and Methods / 2.10. Statistical Analysis, 3. Results / 3.1. Successful Establishment of the AD Model and Improved Memory and Cognition in AD Mice Following SFPQ Overexpression, 3. Results / 3.2. Overexpressed SFPQ Colocalized With CA1 Neurons and Improved the Arrangement of Hippocampal Cells in AD Mice, 3. Results / 3.3. Overexpression of SFPQ Downregulated AD-Related Marker Proteins and Upregulated the Expression of Memory and Synapse-Associated Proteins, 3. Results / 3.4. Overexpression of SFPQ Enhanced Antioxidant and Antiapoptotic Capacities in Hippocampal Cells of the AD Mouse Model, 3. Results / 3.5. Overexpression of SFPQ Activated the PI3K/AKT Pathway, 4. Discussion, 5. Conclusions, 6. Limitations |
| PMID:38569671 | 38569671 |  | abstract_only | 1765 | title, abstract / BACKGROUND, abstract / METHOD, abstract / RESULTS, abstract / CONCLUSION |
| PMCID:PMC10444909 | 37621322 | PMC10444909 | abstract_only | 1909 | title, abstract |
| PMCID:PMC10770459 | 38187339 | PMC10770459 | full_text | 48203 | title, abstract, Introduction, Materials and methods / Animal model, Materials and methods / Oral glucose tolerance test (OGTT) and metabolic cage analysis, Materials and methods / Plasma HMGB1 and Cystatin C quantification, Materials and methods / Plasma AST/ALT quantification, Materials and methods / Mouse/Rat metabolic discovery Assay® Array (MRDMET12), Materials and methods / Histological staining, Materials and methods / Immunoblot, Materials and methods / Polymerase Chain Reaction (PCR), Materials and methods / Bulk RNA sequence analysis, Materials and methods / Statistical analysis, Results / HMGB1 knockdown and hyperglycemia model characterization, Results / Knockdown of HMGB1 mitigates severe hyperglycemia during development, Results / Systemic knockdown of HMGB1 restored glucose tolerance by dynamic assessment of glucose tolerance, Results / HMGB1 knockdown decreases hepatic liver damage in hyperglycemic mice, Results / Liver RNA sequencing identified significant changes in oxidative stress, lipid metabolism and autophagy related pathways, Results / RNA sequencing identified insulin signaling and glucose metabolism pathways to be altered in skeletal muscle, Discussion, Data availability statement, Funding, Additional Information, CRediT authorship contribution statement, Declaration of Competing interest |

## Agreement on shared classes

- Exact agreement events: 1972
- Exact agreement fraction: 0.7691107644305772
- Total alignment events: 2564

| Class | Exact | Type | Boundary | Cross-type | AIONER-only | HunFlair2-only |
|---|---:|---:|---:|---:|---:|---:|
| GeneOrGeneProduct | 960 | 33 | 30 | 1 | 32 | 144 |
| DiseaseOrPhenotypicFeature | 355 | 0 | 5 | 1 | 12 | 99 |
| ChemicalEntity | 368 | 33 | 20 | 1 | 17 | 145 |
| OrganismTaxon | 263 | 0 | 1 | 1 | 1 | 48 |
| CellLine | 26 | 0 | 0 | 0 | 0 | 3 |

## Prediction volume and graph-candidate diagnostics

| Model | Entities | Sentences with entities | Sentences with >=2 entities | Entity pairs |
|---|---:|---:|---:|---:|
| AIONER | 2126 | 626 | 496 | 4444 |
| HunFlair2 | 2502 | 722 | 577 | 5567 |

## Schema-specific observations

- AIONER SequenceVariant predictions: 1
- AIONER CellLine predictions: 26
- HunFlair2 CellLine predictions: 29
- CellLine exact agreements: 26

## Interpretation

- Dominant shared-class disagreement category: hunflair2_only (439 events).
- More predicted entities does not mean more correct entities.
- Model agreement is reconnaissance evidence only; no target-domain precision, recall, or F1 is reported.
- The BioRED ordering cannot be declared stable or unstable without target-domain gold labels.

## Human-review packet

- Deterministic selected examples: 75
- See ner_target_domain_review_packet_2026-09-18.json and its Markdown companion.

## Deferred / future evidence

- CRAFT: deferred. CRAFT mapping was not added to this target report because its ontology-specific concept annotations require a separate, reviewable mapping decision; no broad collapse into BioRED CellLine or SequenceVariant was made.
- BioNLP 2013 Cancer Genetics: BioNLP 2013 Cancer Genetics is a plausible later target-adjacent benchmark because it is cancer-focused and contains gene, simple chemical, organism, and cancer/pathology annotations. Its training-corpus overlap must be checked against the exact model artifacts before use.

## Limitations

- Target papers have no gold annotations; all target-domain findings are reconnaissance evidence.
- Exact agreement fraction is exact alignments divided by deterministic one-to-one alignment events.
- Boundary and overlap categories are greedy, deterministic diagnostics, not correctness judgments.
- Sentence segmentation is a lightweight punctuation-based splitter and preserves canonical-text offsets.
- Raw NCBI XML and model prediction caches remain under ignored .cache paths.
