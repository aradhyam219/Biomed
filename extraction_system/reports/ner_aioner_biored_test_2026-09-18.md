# AIONER PubMedBERT-CRF BioRED NER Evaluation

This is evidence from the model-independent NER evaluator. It is
not a production-readiness claim and does not rank future candidate models.

## Method

- Dataset: `C:\Projects\Biomed\extraction_system\.cache\BIORED\BioRED\Test.BioC.JSON` (test)
- Dataset SHA-256: `35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6`
- Documents: 100 / 100
- Gold entities by BioRED type: `{'CellLine': 50, 'Chemical': 754, 'Disease': 917, 'Gene': 1180, 'Species': 393, 'Variant': 241}`
- Predictor: `PubmedBERT-CRF-AIONER.h5`
- Threshold: `unspecified`
- Primary matching: exact half-open character span plus canonical type
- No fuzzy matching, relation model, LLM, or model fine-tuning was used

## Taxonomy mapping

| BioRED loader type | Canonical evaluation type |
| --- | --- |
| `CellLine` | `CellLine` |
| `Chemical` | `ChemicalEntity` |
| `Disease` | `DiseaseOrPhenotypicFeature` |
| `Gene` | `GeneOrGeneProduct` |
| `Species` | `OrganismTaxon` |
| `Variant` | `SequenceVariant` |

| Predictor label | Canonical evaluation type |
| --- | --- |
| `CellLine` | `CellLine` |
| `Chemical` | `ChemicalEntity` |
| `Disease` | `DiseaseOrPhenotypicFeature` |
| `Gene` | `GeneOrGeneProduct` |
| `Species` | `OrganismTaxon` |
| `Variant` | `SequenceVariant` |
| `cell line` | `CellLine` |
| `chemical` | `ChemicalEntity` |
| `disease` | `DiseaseOrPhenotypicFeature` |
| `gene` | `GeneOrGeneProduct` |
| `protein` | `GeneOrGeneProduct` |
| `species` | `OrganismTaxon` |

- Shared-class taxonomy: `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon']`
- Full-schema supported taxonomy: `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon', 'SequenceVariant']`
- Full-schema unsupported taxonomy: `[]`
DNA/RNA are not force-mapped to unrelated BioRED classes.

## Shared-class exact-match metrics

| Scope | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Micro | 3020 | 282 | 274 | 0.9146 | 0.9168 | 0.9157 |
| `CellLine` | 44 | 1 | 6 | 0.9778 | 0.8800 | 0.9263 |
| `ChemicalEntity` | 685 | 52 | 69 | 0.9294 | 0.9085 | 0.9188 |
| `DiseaseOrPhenotypicFeature` | 808 | 122 | 109 | 0.8688 | 0.8811 | 0.8749 |
| `GeneOrGeneProduct` | 1092 | 89 | 88 | 0.9246 | 0.9254 | 0.9250 |
| `OrganismTaxon` | 391 | 18 | 2 | 0.9560 | 0.9949 | 0.9751 |

Macro F1: **0.9240**

## Full-schema exact-match metrics

| Scope | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Micro | 3232 | 308 | 303 | 0.9130 | 0.9143 | 0.9136 |
| `CellLine` | 44 | 1 | 6 | 0.9778 | 0.8800 | 0.9263 |
| `ChemicalEntity` | 685 | 52 | 69 | 0.9294 | 0.9085 | 0.9188 |
| `DiseaseOrPhenotypicFeature` | 808 | 122 | 109 | 0.8688 | 0.8811 | 0.8749 |
| `GeneOrGeneProduct` | 1092 | 89 | 88 | 0.9246 | 0.9254 | 0.9250 |
| `OrganismTaxon` | 391 | 18 | 2 | 0.9560 | 0.9949 | 0.9751 |
| `SequenceVariant` | 212 | 26 | 29 | 0.8908 | 0.8797 | 0.8852 |

Macro F1: **0.9176**

## Schema coverage

- Gold entities: 3535 scored / 3535 total; unscored by type: `{}`
- Predicted entities: 3540 scored / 3540 total; unscored by type: `{}`

## Failure analysis

| Category | Count |
| --- | ---: |
| missed entity | 109 |
| overlapping prediction | 9 |
| schema-unscored / unsupported gold category | 0 |
| schema-unscored / unsupported predicted category | 0 |
| span mismatch | 131 |
| spurious entity | 114 |
| wrong type | 54 |

Representative records are retained in the machine-readable report.

## Graph-critical NER diagnostic

- Overall mention recall: `0.9126` (2484 / 2722)
- Comparable-class mention recall: `0.9137` (2286 / 2502)
- Overall concept recall: `0.9334` (813 / 871)
- Comparable-class concept recall: `0.9361` (703 / 751)
- This uses relation participation annotations only; it is not relation evaluation.

## Limitations

- Primary metrics use exact half-open character spans and canonical type only; no fuzzy matching is applied.
- Unsupported schema labels are reported separately and excluded from primary comparable-class metrics.
- Failure categories are deterministic diagnostics and do not change the primary counts.
- Graph-critical recall uses BioRED relation concept participation only as an NER diagnostic; no relation model is invoked.
- This report is baseline evidence and does not establish production readiness or rank a candidate model.
