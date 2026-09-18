# GLiNER BioRED NER Baseline

This is baseline evidence from the model-independent NER evaluator. It is
not a production-readiness claim and does not rank future candidate models.

## Method

- Dataset: `C:\Projects\Biomed\extraction_system\.cache\BIORED\BioRED\Dev.BioC.JSON` (dev)
- Dataset SHA-256: `d5ab4d05673ac46fb5e3b2904d2820462dec2c4c50dfcdd8678635ff1b8ce1f5`
- Documents: 100 / 100
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
| `cell line` | `CellLine` |
| `chemical` | `ChemicalEntity` |
| `disease` | `DiseaseOrPhenotypicFeature` |
| `gene` | `GeneOrGeneProduct` |
| `protein` | `GeneOrGeneProduct` |
| `species` | `OrganismTaxon` |

SequenceVariant is currently unscored because the production schema has
no explicit variant label. DNA/RNA are also not force-mapped to unrelated
BioRED classes.

## Exact-match metrics

| Scope | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Micro | 1907 | 824 | 1376 | 0.6983 | 0.5809 | 0.6342 |
| `CellLine` | 7 | 108 | 15 | 0.0609 | 0.3182 | 0.1022 |
| `ChemicalEntity` | 531 | 215 | 291 | 0.7118 | 0.6460 | 0.6773 |
| `DiseaseOrPhenotypicFeature` | 529 | 110 | 453 | 0.8279 | 0.5387 | 0.6527 |
| `GeneOrGeneProduct` | 723 | 295 | 364 | 0.7102 | 0.6651 | 0.6869 |
| `OrganismTaxon` | 117 | 96 | 253 | 0.5493 | 0.3162 | 0.4014 |

Macro F1: **0.5041**

## Schema coverage

- Gold entities: 3283 scored / 3533 total; unscored by type: `{'Variant': 250}`
- Predicted entities: 2731 scored / 2892 total; unscored by type: `{'DNA': 107, 'RNA': 54}`

## Failure analysis

| Category | Count |
| --- | ---: |
| missed entity | 812 |
| spurious entity | 260 |
| wrong type | 91 |
| span mismatch | 395 |
| overlapping prediction | 78 |
| schema-unscored / unsupported gold category | 250 |
| schema-unscored / unsupported predicted category | 161 |

Representative records are retained in the machine-readable report.

## Graph-critical NER diagnostic

- Mention recall: `0.5803` (1597 / 2752)
- Concept recall: `0.6357` (555 / 873)
- This uses relation participation annotations only; it is not relation evaluation.

## Limitations

- Primary metrics use exact half-open character spans and canonical type only; no fuzzy matching is applied.
- Unsupported schema labels are reported separately and excluded from primary comparable-class metrics.
- Failure categories are deterministic diagnostics and do not change the primary counts.
- Graph-critical recall uses BioRED relation concept participation only as an NER diagnostic; no relation model is invoked.
- This report is baseline evidence and does not establish production readiness or rank a candidate model.
