# AIONER vs HunFlair2 on BioRED Test

This is comparative NER evidence, not a production model-selection decision.

## Dataset identity

- Path: `C:\Projects\Biomed\extraction_system\.cache\BIORED\BioRED\Test.BioC.JSON`
- Split: `test`
- SHA-256: `35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6`
- Documents: 100 / 100
- Gold entities: 3535
- Gold entities by BioRED type: `{'CellLine': 50, 'Chemical': 754, 'Disease': 917, 'Gene': 1180, 'Species': 393, 'Variant': 241}`

## Model/runtime identities

- **AIONER**: `PubmedBERT-CRF-AIONER.h5`; adapter `AIONERBioMedExtractor`; device `cpu`; runtime `{'python': '3.8.20', 'stanza': '1.4.0', 'tensorflow': '2.3.0', 'transformers': '4.18.0'}`; inference duration `N/A`
- **HunFlair2**: `hunflair/hunflair2-ner`; adapter `HunFlair2BioMedExtractor`; device `cpu`; runtime `{'allow_long_sentences': True, 'device': 'cpu', 'en_core_sci_sm': '0.5.1', 'flair': '0.15.1', 'label_type': 'ner', 'model_max_length': 512, 'offset_mechanics': 'SciSpaCy sentence boundaries retain each sentence.start_position; Flair span offsets are lifted to the untouched document text and validated before serialization.', 'python': '3.11.16', 'python_implementation': 'CPython', 'pytorch': '2.14.0+cpu', 'scispacy': '0.5.1', 'sentence_splitter': 'SciSpacySentenceSplitter(en_core_sci_sm)', 'spacy': '3.4.4', 'stride': 256, 'tagger_class': 'PrefixedSequenceTagger', 'transformer_model': 'michiyasunaga/BioLinkBERT-base', 'transformers': '4.57.6', 'truncate': True}`; inference duration `90.594s`

## Shared-class head-to-head

Classes: `CellLine`, `ChemicalEntity`, `DiseaseOrPhenotypicFeature`, `GeneOrGeneProduct`, `OrganismTaxon`

| Model | TP | FP | FN | Precision | Recall | F1 | Macro F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AIONER | 3020 | 282 | 274 | 0.9146 | 0.9168 | 0.9157 | 0.9240 |
| HunFlair2 | 3127 | 168 | 167 | 0.9490 | 0.9493 | 0.9492 | 0.9368 |

### Shared-class per-type metrics

| Type | AIONER P/R/F1 | HunFlair2 P/R/F1 | HunFlair2 - AIONER F1 |
| --- | --- | --- | ---: |
| `CellLine` | 0.9778/0.8800/0.9263 | 0.8431/0.8600/0.8515 | -0.0748 |
| `ChemicalEntity` | 0.9294/0.9085/0.9188 | 0.9721/0.9721/0.9721 | 0.0533 |
| `DiseaseOrPhenotypicFeature` | 0.8688/0.8811/0.8749 | 0.9164/0.9324/0.9243 | 0.0494 |
| `GeneOrGeneProduct` | 0.9246/0.9254/0.9250 | 0.9502/0.9373/0.9437 | 0.0187 |
| `OrganismTaxon` | 0.9560/0.9949/0.9751 | 0.9924/0.9924/0.9924 | 0.0173 |

## Full-schema coverage

| Model | Supported canonical classes | Unsupported canonical classes | Micro F1 | Macro F1 |
| --- | --- | --- | ---: | ---: |
| AIONER | `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon', 'SequenceVariant']` | `[]` | 0.9136 | 0.9176 |
| HunFlair2 | `['CellLine', 'ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon']` | `['SequenceVariant']` | 0.9492 | 0.9368 |

### SequenceVariant coverage

- Gold mentions: 241
- AIONER supported: `True`; metric: `{'f1': 0.8851774530271399, 'fn': 29, 'fp': 26, 'precision': 0.8907563025210085, 'predicted': 238, 'recall': 0.8796680497925311, 'support': 241, 'tp': 212}`
- HunFlair2 supported: `False`; metric: `None`

## Graph-critical recall

| View | AIONER mention | HunFlair2 mention | AIONER concept | HunFlair2 concept |
| --- | ---: | ---: | ---: | ---: |
| Overall | 0.9126 (2484/2722) | 0.8703 (2369/2722) | 0.9334 (813/871) | 0.8404 (732/871) |
| Comparable-class | 0.9137 (2286/2502) | 0.9468 (2369/2502) | 0.9361 (703/751) | 0.9747 (732/751) |

## Decision-evidence summary

1. Shared-class micro F1 higher: **HunFlair2**; delta (HunFlair2 - AIONER) = `0.0335`.
2. Shared-class macro F1 higher: **HunFlair2**; delta (HunFlair2 - AIONER) = `0.0128`.
3. Per-type F1 higher: `{'AIONER': ['CellLine'], 'HunFlair2': ['ChemicalEntity', 'DiseaseOrPhenotypicFeature', 'GeneOrGeneProduct', 'OrganismTaxon'], 'ties': []}`.
4. Comparable graph-critical mention recall higher: **HunFlair2**; delta = `0.0332`.
5. Comparable graph-critical concept recall higher: **HunFlair2**; delta = `0.0386`.
6. SequenceVariant capability: `AIONER=True`, `HunFlair2=False`; gold mentions = `241`.
7. At least one primary shared-score difference is within `0.0100`: `False`; no production winner is declared.

## Failure-count differences

| Category | AIONER | HunFlair2 | Both count upper bound | AIONER-only count difference | HunFlair2-only count difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| missed entity | 109 | 53 | 53 | 56 | 0 |
| overlapping prediction | 9 | 4 | 4 | 5 | 0 |
| schema-unscored / unsupported gold category | 0 | 241 | 0 | 0 | 241 |
| schema-unscored / unsupported predicted category | 0 | 0 | 0 | 0 | 0 |
| span mismatch | 131 | 96 | 96 | 35 | 0 |
| spurious entity | 114 | 54 | 54 | 60 | 0 |
| wrong type | 54 | 14 | 14 | 40 | 0 |

## Limitations

- This comparison uses exact half-open source spans and canonical types; no fuzzy matching is applied.
- Shared-class metrics use the five classes supported by both adapters.
- Full-schema views retain the explicit SequenceVariant capability difference.
- Graph-critical recall uses BioRED relation participation only as an NER diagnostic; no relation model is invoked.
- Failure overlap is exact only for bounded retained representative examples; aggregate counts are reported separately.
- Inference wall-clock is descriptive for each model and is not ranked because the isolated runtimes were not executed under equivalent scopes.
- This report provides numerical evidence only and does not declare a production winner.
