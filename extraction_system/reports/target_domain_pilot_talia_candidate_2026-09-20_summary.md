# Talia independent target-domain NER candidate annotation

- Source packet: `extraction_system/reports/target_domain_pilot_blind_2026-09-20.json`
- Source packet SHA-256: `d20bff0cd90cebf7f39e9b1081ce3cf7a30f4c70ed5d28d2f26ec988be0929a2`
- Candidate artifact SHA-256: `a6ef56a18f27ff554caac4cb53ef7513c4fd6856e9b427ad1494abab43c1cd24`
- Examples reviewed: **137**
- Candidate status: **independent AI candidate; not adjudicated; not gold**
- Complete examples: **137**
- Complete-with-uncertainty examples: **0**
- Explicit unresolved mentions: **0**
- Candidate entities: **472**
- Negative sentences: **12**
- Overlapping candidate span pairs: **0**

## Entity counts

| Type | Count |
|---|---:|
| GeneOrGeneProduct | 253 |
| DiseaseOrPhenotypicFeature | 86 |
| ChemicalEntity | 63 |
| OrganismTaxon | 46 |
| CellLine | 24 |
| SequenceVariant | 0 |

## Annotation confidence

| Confidence | Count |
|---|---:|
| high | 397 |
| medium | 75 |
| low | 0 |

## QA

- All 137 source example IDs remain present exactly once.
- Original blind-packet sentence/provenance fields were preserved.
- Original `entities` arrays remain empty.
- Original `annotation_status` remains `unreviewed`.
- Original `annotation_complete` remains `false`.
- Every candidate span resolves exactly against its immutable sentence text.
- Every candidate entity uses one of the six approved types.
- No exact duplicate candidate entities were found.
- No model predictions or non-blind target-domain reports were consulted.
- BioRED entity-scope guidance was used as the annotation basis. External lookup was limited to biomedical identity/type clarification; Cellosaurus was used for selected cell-line checks.

This artifact is intentionally frozen before inspection of Astra's independent annotations.
