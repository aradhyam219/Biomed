# Exploratory MedMentions cross-schema stress test

This is an exploratory cross-schema stress test using explicit UMLS semantic-type mappings. It is not clean model-selection evidence comparable to BioRED or CRAFT. UMLS normalization is intentionally out of scope.

## Dataset identity

- Split: test
- Documents: 879
- Corpus URL: https://raw.githubusercontent.com/chanzuckerberg/MedMentions/master/st21pv/data/corpus_pubtator.txt.gz
- Corpus SHA-256: 66c89275ec6f68ad402f1289167126e1cd5fc1e024c256a201255d60b961c271
- Split URL: https://raw.githubusercontent.com/chanzuckerberg/MedMentions/master/full/data/corpus_pubtator_pmids_test.txt
- Split SHA-256: fece5bcb8c61edf8de73884980b80daf274132ef6d69f0d195c0114acbfdd4ab

## Explicit semantic-type mapping

| Semantic type | Canonical class |
|---|---|
| T033 | DiseaseOrPhenotypicFeature |
| T037 | DiseaseOrPhenotypicFeature |
| T047 | DiseaseOrPhenotypicFeature |
| T103 | ChemicalEntity |
| T184 | DiseaseOrPhenotypicFeature |
| T190 | DiseaseOrPhenotypicFeature |
| T191 | DiseaseOrPhenotypicFeature |

Unsupported and ambiguous gold annotations are retained in counts but excluded from primary precision, recall, and F1.

## Exact NER results

| Model | Gold scored | Predicted scored | Precision | Recall | Micro F1 | Macro F1 |
|---|---:|---:|---:|---:|---:|---:|
| AIONER | 10980 | 8552 | 0.3829680020156211 | 0.293266448003087 | 0.3321678321678322 | 0.31188667030121303 |
| HunFlair2 | 10980 | 8767 | 0.38656078191814297 | 0.304289286401231 | 0.3405262874670398 | 0.31641108124628947 |

### Per type

| Type | AIONER P | AIONER R | AIONER F1 | HunFlair2 P | HunFlair2 R | HunFlair2 F1 |
|---|---:|---:|---:|---:|---:|---:|
| ChemicalEntity | 0.7982681205901219 | 0.35105782792665724 | 0.4876567398119122 | 0.7760754272245138 | 0.37062051498522586 | 0.5016665079516237 |
| DiseaseOrPhenotypicFeature | 0.11431535269709543 | 0.1681929181929182 | 0.13611660079051383 | 0.11062408682947193 | 0.16104527499240354 | 0.1311556545409552 |

## Failure categories

| Category | AIONER | HunFlair2 |
|---|---:|---:|
| missed_scored_gold | 7326 | 7234 |
| spurious_scored_prediction | 4898 | 5021 |
| same_span_different_type | 12 | 11 |
| overlapping_same_type_boundary | 521 | 483 |
| overlapping_different_type | 81 | 88 |
| unsupported_gold_semantic_type | 29177 | 29177 |
| ambiguous_gold_semantic_type | 0 | 0 |
| unsupported_predicted_type | 6434 | 6330 |

## BioRED comparison

- MedMentions ordering: ['HunFlair2', 'AIONER']
- BioRED ordering: ['HunFlair2', 'AIONER']
- Ordering differs: False

## Independence and caveats

- MedMentions is absent from the documented AIONER and HunFlair2 supervised training recipes checked for these artifacts.
- Exact source spans and explicit canonical types are required; no fuzzy or ontology-linking credit is given.
- BioRED and MedMentions use different annotation conventions, so scores should not be treated as directly interchangeable.
