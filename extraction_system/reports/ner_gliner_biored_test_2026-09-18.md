# GLiNER BioRED BioRED NER Evaluation

This is evidence from the model-independent NER evaluator. It is
not a production-readiness claim and does not rank future candidate models.

## Method

- Dataset: `C:\Projects\Biomed\extraction_system\.cache\BIORED\BioRED\Test.BioC.JSON` (test)
- Dataset SHA-256: `35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6`
- Documents: 100 / 100
- Gold entities by BioRED type: `{'CellLine': 50, 'Chemical': 754, 'Disease': 917, 'Gene': 1180, 'Species': 393, 'Variant': 241}`
- Predictor: `Ihor/gliner-biomed-base-v1.0`
- Threshold: `0.5`
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
- Full-schema supported taxonomy: `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon']`
- Full-schema unsupported taxonomy: `['SequenceVariant']`
DNA/RNA are not force-mapped to unrelated BioRED classes.

## Shared-class exact-match metrics

| Scope | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Micro | 1837 | 862 | 1457 | 0.6806 | 0.5577 | 0.6130 |
| `CellLine` | 25 | 124 | 25 | 0.1678 | 0.5000 | 0.2513 |
| `ChemicalEntity` | 493 | 225 | 261 | 0.6866 | 0.6538 | 0.6698 |
| `DiseaseOrPhenotypicFeature` | 492 | 146 | 425 | 0.7712 | 0.5365 | 0.6328 |
| `GeneOrGeneProduct` | 728 | 290 | 452 | 0.7151 | 0.6169 | 0.6624 |
| `OrganismTaxon` | 99 | 77 | 294 | 0.5625 | 0.2519 | 0.3480 |

Macro F1: **0.5129**

## Full-schema exact-match metrics

| Scope | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Micro | 1837 | 862 | 1457 | 0.6806 | 0.5577 | 0.6130 |
| `CellLine` | 25 | 124 | 25 | 0.1678 | 0.5000 | 0.2513 |
| `ChemicalEntity` | 493 | 225 | 261 | 0.6866 | 0.6538 | 0.6698 |
| `DiseaseOrPhenotypicFeature` | 492 | 146 | 425 | 0.7712 | 0.5365 | 0.6328 |
| `GeneOrGeneProduct` | 728 | 290 | 452 | 0.7151 | 0.6169 | 0.6624 |
| `OrganismTaxon` | 99 | 77 | 294 | 0.5625 | 0.2519 | 0.3480 |

Macro F1: **0.5129**

## Schema coverage

- Gold entities: 3294 scored / 3535 total; unscored by type: `{'Variant': 241}`
- Predicted entities: 2699 scored / 2843 total; unscored by type: `{'DNA': 91, 'RNA': 53}`

## Failure analysis

| Category | Count |
| --- | ---: |
| missed entity | 856 |
| overlapping prediction | 65 |
| schema-unscored / unsupported gold category | 241 |
| schema-unscored / unsupported predicted category | 144 |
| span mismatch | 396 |
| spurious entity | 261 |
| wrong type | 140 |

Representative records are retained in the machine-readable report.

## Graph-critical NER diagnostic

- Overall mention recall: `0.5716` (1556 / 2722)
- Comparable-class mention recall: `0.6219` (1556 / 2502)
- Overall concept recall: `0.5798` (505 / 871)
- Comparable-class concept recall: `0.6724` (505 / 751)
- This uses relation participation annotations only; it is not relation evaluation.

## Limitations

- Primary metrics use exact half-open character spans and canonical type only; no fuzzy matching is applied.
- Unsupported schema labels are reported separately and excluded from primary comparable-class metrics.
- Failure categories are deterministic diagnostics and do not change the primary counts.
- Graph-critical recall uses BioRED relation concept participation only as an NER diagnostic; no relation model is invoked.
- This report is baseline evidence and does not establish production readiness or rank a candidate model.
