# AIONER versus HunFlair2 on CRAFT full-text NER

CRAFT is the primary clean independent cross-corpus benchmark for the current NER model-selection question.

## Dataset identity

- Release: v5.0.2
- Official source: https://github.com/lhunter-lab/CRAFT
- Official release: https://github.com/lhunter-lab/CRAFT/releases/tag/v5.0.2
- Source revision: 2abe82b8bb8089448b84937d5f61d8c218011322
- Release identity verified: True
- Articles evaluated: 97
- Text manifest SHA-256: 1ecf91effe39ea9dccbee8f959b621bf6cb123b106b74e145357376e1f8c959d
- Annotation manifest SHA-256: c8eff2d37121defb90bd5ad841e4ca089f745da0865819070b995c04f1a957f9
- Combined source manifest SHA-256: 1d7300c5bc712278d4cb4485cc119a31dcda5d802a402fe17f846c8253bb1017
- Shared model-input SHA-256: a128a4549bedb940b59e47267f45c28ef163c36b9ce3cad1f7fbdc741c339744
- Identical canonical model input: AIONER and HunFlair2

## Ontology mapping

| CRAFT module | Canonical class | Primary scoring |
|---|---|---|
| Protein Ontology (`PR`) | GeneOrGeneProduct | yes |
| ChEBI (`CHEBI`) | ChemicalEntity | yes |
| NCBI Taxonomy (`NCBITaxon`) | OrganismTaxon | yes |

Unsupported and ambiguous annotations remain in the accounting below and are excluded from primary metrics.

| Gold mapping status | Count |
|---|---:|
| ambiguous | 2015 |
| scored | 40496 |
| unsupported | 57112 |

## Exact NER results

| Model | Gold scored | Predicted | Precision | Recall | Micro F1 | Macro F1 |
|---|---:|---:|---:|---:|---:|---:|
| AIONER | 40496 | 31653 | 0.718826019650586 | 0.5618579612801264 | 0.6307225325368335 | 0.6189590415614658 |
| HunFlair2 | 40496 | 43984 | 0.646689705347399 | 0.7023903595416832 | 0.6733901515151515 | 0.689386990529396 |

### Per type

| Type | AIONER P | AIONER R | AIONER F1 | HunFlair2 P | HunFlair2 R | HunFlair2 F1 |
|---|---:|---:|---:|---:|---:|---:|
| GeneOrGeneProduct | 0.665944540727903 | 0.5932072558857584 | 0.6274749948969177 | 0.568024861878453 | 0.7054333376216819 | 0.6293157864534517 |
| ChemicalEntity | 0.6387024608501118 | 0.42510422870756404 | 0.5104595029501162 | 0.5909513480012395 | 0.56789755807028 | 0.5791951404707669 |
| OrganismTaxon | 0.9460302604897832 | 0.5797724882898384 | 0.7189426268373637 | 0.9544924154025671 | 0.7819520122359239 | 0.8596500446639693 |

## Failure taxonomy

| Category | AIONER | HunFlair2 |
|---|---:|---:|
| missed entity | 15322 | 5842 |
| spurious entity | 6479 | 9330 |
| wrong type | 104 | 193 |
| span mismatch | 2143 | 5700 |
| overlapping prediction | 174 | 317 |
| schema-unscored / unsupported gold category | 59127 | 59127 |
| schema-unscored / unsupported predicted category | 4555 | 5213 |

## Artifact identity

### AIONER

- Model: PubmedBERT-CRF-AIONER.h5
- Artifact SHA-256: 78ed76db6355b50002dbf5b51dc6ad9d2ca7dee0abe830f51c4e6329033a23c7
- Runtime: `{"decoder": "crf", "entity_scope": "ALL", "max_batch_characters": 200000, "max_batch_documents": 128, "max_sentence_tokens": 256, "offset_mechanics": "Official AIONER token/BIO output is lifted sequentially onto the untouched document text and validated; the upstream mutable-remainder offset restorer is not used.", "python": "3.8.20", "python_implementation": "CPython", "stanza": "1.4.0", "tensorflow": "2.3.0", "transformers": "4.18.0"}`

### HunFlair2

- Model: hunflair/hunflair2-ner
- Artifact SHA-256: 245a099b660c1e2b682e0a1216feac140d5be36c4c6ca8c715af682efa685de6
- Runtime: `{"allow_long_sentences": true, "device": "cpu", "en_core_sci_sm": "0.5.1", "flair": "0.15.1", "label_type": "ner", "model_max_length": 512, "offset_mechanics": "Flair span text is resolved against the model sentence; that sentence is located in the untouched source and the lifted span is validated before serialization.", "python": "3.11.16", "python_implementation": "CPython", "pytorch": "2.14.0+cpu", "scispacy": "0.5.1", "sentence_splitter": "SciSpacySentenceSplitter(en_core_sci_sm)", "spacy": "3.4.4", "stride": 256, "tagger_class": "PrefixedSequenceTagger", "transformer_model": "michiyasunaga/BioLinkBERT-base", "transformers": "4.57.6", "truncate": true}`

## Benchmark independence

- CRAFT listed in documented AIONER training recipe: False
- CRAFT listed in documented HunFlair2 training recipe: False
- Independent under documented supervised training: True
- Qualification: This establishes absence from the documented supervised training recipes checked for the exact cached artifacts; it does not establish absence from every possible pretraining source.

## Caveats

- Primary metrics use exact half-open source spans and canonical types only; no fuzzy matching is applied.
- Only Protein Ontology, ChEBI, and NCBI Taxonomy annotations contribute to primary metrics.
- Cell Ontology is not mapped to CellLine, and Sequence Ontology is not mapped to SequenceVariant.
- GO annotations and all other CRAFT ontology modules remain explicit unsupported metadata.
- Discontinuous Knowtator annotations are retained as ambiguous metadata and excluded because they do not define one exact half-open span.
- Ontology identifiers are provenance only; normalization and linking are out of scope.
- This report is cross-corpus evidence and does not make the production-model decision.
