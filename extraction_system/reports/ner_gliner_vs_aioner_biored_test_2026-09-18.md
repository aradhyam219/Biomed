# GLiNER vs AIONER on BioRED Test

This is comparative NER evidence, not a production model-selection decision.

## Dataset identity

- Path: `C:\Projects\Biomed\extraction_system\.cache\BIORED\BioRED\Test.BioC.JSON`
- Split: `test`
- SHA-256: `35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6`
- Documents: 100 / 100
- Gold entities: 3535
- Gold entities by BioRED type: `{'CellLine': 50, 'Chemical': 754, 'Disease': 917, 'Gene': 1180, 'Species': 393, 'Variant': 241}`

## Model/runtime identities

- **GLiNER**: `Ihor/gliner-biomed-base-v1.0`; adapter `GLiNERBioMedExtractor`; device `cpu`; runtime `{}`
- **AIONER**: `PubmedBERT-CRF-AIONER.h5`; adapter `AIONERBioMedExtractor`; device `cpu`; runtime `{'python': '3.8.20', 'stanza': '1.4.0', 'tensorflow': '2.3.0', 'transformers': '4.18.0'}`

## Shared-class head-to-head

Classes: `CellLine`, `ChemicalEntity`, `DiseaseOrPhenotypicFeature`, `GeneOrGeneProduct`, `OrganismTaxon`

| Model | TP | FP | FN | Precision | Recall | F1 | Macro F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GLiNER | 1837 | 862 | 1457 | 0.6806 | 0.5577 | 0.6130 | 0.5129 |
| AIONER | 3020 | 282 | 274 | 0.9146 | 0.9168 | 0.9157 | 0.9240 |

### Shared-class per-type metrics

| Type | GLiNER P/R/F1 | AIONER P/R/F1 | AIONER - GLiNER F1 |
| --- | --- | --- | ---: |
| `CellLine` | 0.1678/0.5000/0.2513 | 0.9778/0.8800/0.9263 | 0.6751 |
| `ChemicalEntity` | 0.6866/0.6538/0.6698 | 0.9294/0.9085/0.9188 | 0.2490 |
| `DiseaseOrPhenotypicFeature` | 0.7712/0.5365/0.6328 | 0.8688/0.8811/0.8749 | 0.2421 |
| `GeneOrGeneProduct` | 0.7151/0.6169/0.6624 | 0.9246/0.9254/0.9250 | 0.2626 |
| `OrganismTaxon` | 0.5625/0.2519/0.3480 | 0.9560/0.9949/0.9751 | 0.6271 |

## Full-schema coverage

| Model | Supported canonical classes | Unsupported canonical classes | Micro F1 | Macro F1 |
| --- | --- | --- | ---: | ---: |
| GLiNER | `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon']` | `['SequenceVariant']` | 0.6130 | 0.5129 |
| AIONER | `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon', 'SequenceVariant']` | `[]` | 0.9136 | 0.9176 |

### SequenceVariant coverage

- Gold mentions: 241
- GLiNER supported: `False`; metric: `None`
- AIONER supported: `True`; metric: `{'f1': 0.8851774530271399, 'fn': 29, 'fp': 26, 'precision': 0.8907563025210085, 'predicted': 238, 'recall': 0.8796680497925311, 'support': 241, 'tp': 212}`

## Graph-critical recall

| View | GLiNER mention | AIONER mention | GLiNER concept | AIONER concept |
| --- | ---: | ---: | ---: | ---: |
| Overall | 0.5716 (1556/2722) | 0.9126 (2484/2722) | 0.5798 (505/871) | 0.9334 (813/871) |
| Comparable-class | 0.6219 (1556/2502) | 0.9137 (2286/2502) | 0.6724 (505/751) | 0.9361 (703/751) |

## Failure-count differences

| Category | GLiNER | AIONER | Both count upper bound | GLiNER-only difference | AIONER-only difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| missed entity | 856 | 109 | 109 | 747 | 0 |
| overlapping prediction | 65 | 9 | 9 | 56 | 0 |
| schema-unscored / unsupported gold category | 241 | 0 | 0 | 241 | 0 |
| schema-unscored / unsupported predicted category | 144 | 0 | 0 | 144 | 0 |
| span mismatch | 396 | 131 | 131 | 265 | 0 |
| spurious entity | 261 | 114 | 114 | 147 | 0 |
| wrong type | 140 | 54 | 54 | 86 | 0 |

## Limitations

- This comparison uses exact half-open source spans and canonical types; no fuzzy matching is applied.
- Shared-class metrics use the five classes supported by both adapters.
- Full-schema views retain the explicit SequenceVariant capability gap for GLiNER.
- Graph-critical recall uses BioRED relation participation only as an NER diagnostic; no relation model is invoked.
- Published AIONER scores are context only; this report does not declare a production winner or rank HunFlair2.
- Failure overlap is exact only for retained representative examples; aggregate both fields are upper bounds and only fields are count differences.
- Inference wall-clock is not compared because the isolated official AIONER run and GLiNER evaluation were not timed with identical scopes; AIONER was run on CPU.
