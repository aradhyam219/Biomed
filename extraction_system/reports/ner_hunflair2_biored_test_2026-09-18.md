# HunFlair2 BioRED NER Evaluation

This is evidence from the model-independent NER evaluator. It is
not a production-readiness claim and does not rank future candidate models.

## Method

- Dataset: `C:\Projects\Biomed\extraction_system\.cache\BIORED\BioRED\Test.BioC.JSON` (test)
- Dataset SHA-256: `35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6`
- Documents: 100 / 100
- Gold entities by BioRED type: `{'CellLine': 50, 'Chemical': 754, 'Disease': 917, 'Gene': 1180, 'Species': 393, 'Variant': 241}`
- Predictor: `hunflair/hunflair2-ner`
- Threshold: `unspecified`
- Primary matching: exact half-open character span plus canonical type
- No fuzzy matching, relation model, LLM, or model fine-tuning was used

## Runtime and inference

- Runtime versions: `{'allow_long_sentences': True, 'device': 'cpu', 'en_core_sci_sm': '0.5.1', 'flair': '0.15.1', 'label_type': 'ner', 'model_max_length': 512, 'offset_mechanics': 'SciSpaCy sentence boundaries retain each sentence.start_position; Flair span offsets are lifted to the untouched document text and validated before serialization.', 'python': '3.11.16', 'python_implementation': 'CPython', 'pytorch': '2.14.0+cpu', 'scispacy': '0.5.1', 'sentence_splitter': 'SciSpacySentenceSplitter(en_core_sci_sm)', 'spacy': '3.4.4', 'stride': 256, 'tagger_class': 'PrefixedSequenceTagger', 'transformer_model': 'michiyasunaga/BioLinkBERT-base', 'transformers': '4.57.6', 'truncate': True}`
- Model revision: `3af2b8972f7af2910ce8d9ae724da09b3d7a166c`
- Model artifact SHA-256: `245a099b660c1e2b682e0a1216feac140d5be36c4c6ca8c715af682efa685de6`
- Inference duration: `90.59423610000522` seconds
- Inference scope: `All supplied document text; SciSpacy sentence segmentation; Flair long-sentence striding when required; no truncation.`
- Offset mechanics: `SciSpaCy sentence boundaries retain each sentence.start_position; Flair span offsets are lifted to the untouched document text and validated before serialization.`

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
| Micro | 3127 | 168 | 167 | 0.9490 | 0.9493 | 0.9492 |
| `CellLine` | 43 | 8 | 7 | 0.8431 | 0.8600 | 0.8515 |
| `ChemicalEntity` | 733 | 21 | 21 | 0.9721 | 0.9721 | 0.9721 |
| `DiseaseOrPhenotypicFeature` | 855 | 78 | 62 | 0.9164 | 0.9324 | 0.9243 |
| `GeneOrGeneProduct` | 1106 | 58 | 74 | 0.9502 | 0.9373 | 0.9437 |
| `OrganismTaxon` | 390 | 3 | 3 | 0.9924 | 0.9924 | 0.9924 |

Macro F1: **0.9368**

## Full-schema exact-match metrics

| Scope | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Micro | 3127 | 168 | 167 | 0.9490 | 0.9493 | 0.9492 |
| `CellLine` | 43 | 8 | 7 | 0.8431 | 0.8600 | 0.8515 |
| `ChemicalEntity` | 733 | 21 | 21 | 0.9721 | 0.9721 | 0.9721 |
| `DiseaseOrPhenotypicFeature` | 855 | 78 | 62 | 0.9164 | 0.9324 | 0.9243 |
| `GeneOrGeneProduct` | 1106 | 58 | 74 | 0.9502 | 0.9373 | 0.9437 |
| `OrganismTaxon` | 390 | 3 | 3 | 0.9924 | 0.9924 | 0.9924 |

Macro F1: **0.9368**

## Schema coverage

- Gold entities: 3294 scored / 3535 total; unscored by type: `{'Variant': 241}`
- Predicted entities: 3295 scored / 3295 total; unscored by type: `{}`

## Failure analysis

| Category | Count |
| --- | ---: |
| missed entity | 53 |
| spurious entity | 54 |
| wrong type | 14 |
| span mismatch | 96 |
| overlapping prediction | 4 |
| schema-unscored / unsupported gold category | 241 |
| schema-unscored / unsupported predicted category | 0 |

Representative records are retained in the machine-readable report.

## Graph-critical NER diagnostic

- Overall mention recall: `0.8703` (2369 / 2722)
- Comparable-class mention recall: `0.9468` (2369 / 2502)
- Overall concept recall: `0.8404` (732 / 871)
- Comparable-class concept recall: `0.9747` (732 / 751)
- This uses relation participation annotations only; it is not relation evaluation.

## Limitations

- Primary metrics use exact half-open character spans and canonical type only; no fuzzy matching is applied.
- Unsupported schema labels are reported separately and excluded from primary comparable-class metrics.
- Failure categories are deterministic diagnostics and do not change the primary counts.
- Graph-critical recall uses BioRED relation concept participation only as an NER diagnostic; no relation model is invoked.
- This report is baseline evidence and does not establish production readiness or rank a candidate model.
