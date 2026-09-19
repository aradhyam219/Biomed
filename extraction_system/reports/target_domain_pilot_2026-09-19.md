# Target-domain gold pilot annotation packet

This packet is a human annotation template. Existing HunFlair2 and AIONER outputs are suggestions only; they are not gold labels.

- Status: `awaiting_human_gold_annotations`
- Selected sentences: 137
- Annotation convention: `Python/Unicode character offsets relative to the selected sentence, half-open [start, end); sentence text is unchanged from canonical source.`
- Gold policy: annotate every target-schema entity in each sentence, including sentences with no entities.

## Paper split

| Paper | Split | Mode | Characters | Sentences |
|---|---|---|---:|---:|
| PMCID:PMC10444909 | dev | abstract_only | 1909 | 15 |
| PMCID:PMC10770459 | train | full_text | 48203 | 337 |
| PMCID:PMC11824863 | train | full_text | 30020 | 205 |
| PMCID:PMC8605525 | test | full_text | 47245 | 380 |
| PMID:27172794 | train | abstract_only | 1620 | 13 |
| PMID:27370646 | train | abstract_only | 1217 | 8 |
| PMID:31324362 | train | abstract_only | 1814 | 13 |
| PMID:33652126 | train | abstract_only | 1516 | 13 |
| PMID:38569671 | test | abstract_only | 1765 | 15 |

## Annotation items

### 1. `targetpilot-ef7273c16b444984`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `title`
- Sentence: `s0001`; canonical offsets: `[0, 70)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> KNTC1 knockdown inhibits proliferation and metastases of liver cancer.

HunFlair2 suggestions:
- `[0, 5)` 'KNTC1' — Gene (score=1.0000)
- `[43, 69)` 'metastases of liver cancer' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 2. `targetpilot-0bd486919f1bb9c1`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0002`; canonical offsets: `[72, 173)`
- Sampling: `A` — model_disagreement:hunflair2_only
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> To investigate the mechanism of kinetochore-associated protein 1 (KNTC1) in hepatocellular carcinoma.

HunFlair2 suggestions:
- `[32, 64)` 'kinetochore-associated protein 1' — Gene (score=1.0000)
- `[66, 71)` 'KNTC1' — Gene (score=1.0000)
- `[76, 100)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 3. `targetpilot-d5b05be56ea5a2bf`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0003`; canonical offsets: `[174, 250)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> To query the TCGA database for KNTC1 expression in hepatocellular carcinoma.

HunFlair2 suggestions:
- `[31, 36)` 'KNTC1' — Gene (score=1.0000)
- `[51, 75)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 4. `targetpilot-3938eb63a5e6d7a7`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0004`; canonical offsets: `[251, 369)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Detection of protein and mRNA levels of KNTC1 in hepatocellular carcinoma cell lines SK-Hep-1, Huh7, HepG2 and SNU449.

HunFlair2 suggestions:
- `[40, 45)` 'KNTC1' — Gene (score=1.0000)
- `[49, 73)` 'hepatocellular carcinoma' — Disease (score=1.0000)
- `[85, 93)` 'SK-Hep-1' — CellLine (score=0.8794)
- `[95, 99)` 'Huh7' — CellLine (score=0.9952)
- `[101, 106)` 'HepG2' — CellLine (score=0.9940)
- `[111, 117)` 'SNU449' — CellLine (score=0.9953)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 5. `targetpilot-1db5e578a7c2fbf1`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0005`; canonical offsets: `[370, 478)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Cell proliferation, migration and invasion ability were examined after KNTC1 knockdown in SK-Hep-1 and Huh7.

HunFlair2 suggestions:
- `[71, 76)` 'KNTC1' — Gene (score=1.0000)
- `[90, 98)` 'SK-Hep-1' — CellLine (score=0.8904)
- `[103, 107)` 'Huh7' — CellLine (score=0.9951)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 6. `targetpilot-b39ed8ce2ba76e6f`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0006`; canonical offsets: `[479, 614)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Proteins related to KNTC1 were identified through protein interregulation, and their role in hepatocellular carcinoma was investigated.

HunFlair2 suggestions:
- `[20, 25)` 'KNTC1' — Gene (score=1.0000)
- `[93, 117)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 7. `targetpilot-bb06e130ef29a669`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0007`; canonical offsets: `[615, 762)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Our results showed that KNTC1 was significantly upregulated in hepatocellular carcinoma tissues and was associated with poorer prognostic survival.

HunFlair2 suggestions:
- `[24, 29)` 'KNTC1' — Gene (score=1.0000)
- `[63, 87)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 8. `targetpilot-386eb829a946e1bd`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0008`; canonical offsets: `[763, 924)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> The expression of KNTC1 in hepatocellular carcinoma cell lines SK-Hep-1, Huh7, HepG2 and SNU449 was significantly higher than that in normal hepatocyte line L02.

HunFlair2 suggestions:
- `[18, 23)` 'KNTC1' — Gene (score=1.0000)
- `[27, 51)` 'hepatocellular carcinoma' — Disease (score=1.0000)
- `[63, 71)` 'SK-Hep-1' — CellLine (score=0.9117)
- `[73, 77)` 'Huh7' — CellLine (score=0.9953)
- `[79, 84)` 'HepG2' — CellLine (score=0.9941)
- `[89, 95)` 'SNU449' — CellLine (score=0.9954)
- `[157, 160)` 'L02' — CellLine (score=0.9951)

AIONER suggestions (when available):
- `[79, 84)` 'HepG2' — CellLine

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 9. `targetpilot-2a1616e7ce0fad78`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0009`; canonical offsets: `[925, 1044)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Knockdown of KNTC1 in SK-Hep-1 and Huh7 significantly inhibited cell viability, migration ability and invasion ability.

HunFlair2 suggestions:
- `[13, 18)` 'KNTC1' — Gene (score=1.0000)
- `[22, 30)` 'SK-Hep-1' — CellLine (score=0.9172)
- `[35, 39)` 'Huh7' — CellLine (score=0.9952)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 10. `targetpilot-551bcefd77293e04`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0010`; canonical offsets: `[1045, 1171)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> KNTC1 is involved in the regulation of hepatocellular carcinoma through its interaction with cyclin-dependent kinase 1 (CDK1).

HunFlair2 suggestions:
- `[0, 5)` 'KNTC1' — Gene (score=1.0000)
- `[39, 63)` 'hepatocellular carcinoma' — Disease (score=1.0000)
- `[93, 118)` 'cyclin-dependent kinase 1' — Gene (score=1.0000)
- `[120, 124)` 'CDK1' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 11. `targetpilot-e620e1bfc02d0de2`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0011`; canonical offsets: `[1172, 1375)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Knockdown of KNTC1 inhibited CDK1 expression, while CDK1 overexpression was able to rescue the regulation of KNTC1 on the viability, migration and invasive ability of hepatocellular carcinoma cell lines.

HunFlair2 suggestions:
- `[13, 18)` 'KNTC1' — Gene (score=1.0000)
- `[29, 33)` 'CDK1' — Gene (score=1.0000)
- `[52, 56)` 'CDK1' — Gene (score=1.0000)
- `[109, 114)` 'KNTC1' — Gene (score=1.0000)
- `[167, 191)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 12. `targetpilot-ad97870a43b740d9`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0012`; canonical offsets: `[1376, 1575)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Knockdown of KNTC1 was found to resulted a cell cycle arrest at the S-phase, potentially through the modulation of CDK1, leading to decreased migration and invasion of hepatocellular carcinoma cells.

HunFlair2 suggestions:
- `[13, 18)` 'KNTC1' — Gene (score=1.0000)
- `[115, 119)` 'CDK1' — Gene (score=1.0000)
- `[168, 192)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 13. `targetpilot-68e25a15488931a2`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0013`; canonical offsets: `[1576, 1670)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Moreover, knockdown of KNTC1 in mouse transplanted tumors significantly inhibits tumor growth.

HunFlair2 suggestions:
- `[23, 28)` 'KNTC1' — Gene (score=1.0000)
- `[32, 37)` 'mouse' — Species (score=1.0000)
- `[51, 57)` 'tumors' — Disease (score=1.0000)
- `[81, 86)` 'tumor' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[32, 37)` 'mouse' — Species

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 14. `targetpilot-bae6c80e3e59b89b`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0014`; canonical offsets: `[1671, 1833)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> Inhibition of high expression of KNTC1 in hepatocellular carcinoma was effective in suppressing the progression of hepatocellular carcinoma cells after knockdown.

HunFlair2 suggestions:
- `[33, 38)` 'KNTC1' — Gene (score=1.0000)
- `[42, 66)` 'hepatocellular carcinoma' — Disease (score=1.0000)
- `[115, 139)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[33, 38)` 'KNTC1' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 15. `targetpilot-673701bbec16460f`

- Paper: `PMCID:PMC10444909` (PMID `37621322`, PMCID `PMC10444909`)
- Split: `dev`; section: `abstract`
- Sentence: `s0015`; canonical offsets: `[1834, 1909)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `e781be6d7f69cb7acb0af6251cc2bd8ec5139908da50e0f577c5b342b392f250`

> It may be a potential target for the treatment of hepatocellular carcinoma.

HunFlair2 suggestions:
- `[50, 74)` 'hepatocellular carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 16. `targetpilot-cb502b16715ed40a`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `abstract`
- Sentence: `s0003`; canonical offsets: `[413, 606)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> In this study, we explored the role of high mobility group box 1 (HMGB1) in hyperglycemia, a protein implicated in initiating inflammation and strongly correlated with DM onset and progression.

HunFlair2 suggestions:
- `[39, 64)` 'high mobility group box 1' — Gene (score=1.0000)
- `[66, 71)` 'HMGB1' — Gene (score=1.0000)
- `[76, 89)` 'hyperglycemia' — Disease (score=1.0000)
- `[126, 138)` 'inflammation' — Disease (score=1.0000)
- `[168, 170)` 'DM' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 17. `targetpilot-6cf97f8125a92159`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Introduction`
- Sentence: `s0017`; canonical offsets: `[3007, 3204)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Consequently, achieving normoglycemia constitutes the most efficacious therapeutic outcome for individuals with DM, aiming to prevent the onset of diabetes-related complications [[12], [13], [14]].

HunFlair2 suggestions:
- `[112, 114)` 'DM' — Disease (score=1.0000)
- `[147, 177)` 'diabetes-related complications' — Disease (score=0.9678)

AIONER suggestions (when available):
- `[147, 155)` 'diabetes' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 18. `targetpilot-2b5026569bd20f63`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Introduction`
- Sentence: `s0026`; canonical offsets: `[4826, 5045)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> In addition, it has also been proposed that HMGB1 may interfere with insulin signaling through the insulin receptor/AKT pathway, resulting in insulin resistance and, consequently, disruptions in glucose metabolism [34].

HunFlair2 suggestions:
- `[44, 49)` 'HMGB1' — Gene (score=1.0000)
- `[69, 76)` 'insulin' — Gene (score=1.0000)
- `[99, 115)` 'insulin receptor' — Gene (score=1.0000)
- `[116, 119)` 'AKT' — Gene (score=1.0000)
- `[142, 160)` 'insulin resistance' — Disease (score=1.0000)
- `[195, 202)` 'glucose' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 19. `targetpilot-5e4cb1d2b0d63b63`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Introduction`
- Sentence: `s0034`; canonical offsets: `[6083, 6262)`
- Sampling: `A` — model_disagreement:cross_type_overlap
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Our hypothesis postulates that systemic conditional knockdown of HMGB1 in hyperglycemic mice will lead to a significant reduction in glucose levels and enhanced glucose tolerance.

HunFlair2 suggestions:
- `[65, 70)` 'HMGB1' — Gene (score=1.0000)
- `[74, 87)` 'hyperglycemic' — Disease (score=1.0000)
- `[88, 92)` 'mice' — Species (score=1.0000)
- `[133, 140)` 'glucose' — Chemical (score=1.0000)
- `[161, 178)` 'glucose tolerance' — Disease (score=0.8569)

AIONER suggestions (when available):
- `[74, 87)` 'hyperglycemic' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 20. `targetpilot-d98791452ffbe7a5`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Introduction`
- Sentence: `s0035`; canonical offsets: `[6263, 6496)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Furthermore, we hypothesize that RNA sequencing will identify relevant altered pathways in our model, aiding in the elucidation of the mechanism of action we seek to pursue understanding the role of HMGB1 in glucose regulation in DM.

HunFlair2 suggestions:
- `[199, 204)` 'HMGB1' — Gene (score=1.0000)
- `[208, 215)` 'glucose' — Chemical (score=1.0000)
- `[230, 232)` 'DM' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 21. `targetpilot-33061626488cf2cc`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Materials and methods / Histological staining`
- Sentence: `s0079`; canonical offsets: `[12669, 12834)`
- Sampling: `A` — model_disagreement:hunflair2_only
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Liver samples were obtained from the same cohort of HMGB1 Flox TMX STZ and iHMGB1 KO TMX STZ mice that have hyperglycemia developed for 10 weeks post last injection.

HunFlair2 suggestions:
- `[52, 57)` 'HMGB1' — Gene (score=1.0000)
- `[67, 70)` 'STZ' — Chemical (score=1.0000)
- `[75, 81)` 'iHMGB1' — Gene (score=1.0000)
- `[89, 92)` 'STZ' — Chemical (score=1.0000)
- `[93, 97)` 'mice' — Species (score=1.0000)
- `[108, 121)` 'hyperglycemia' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 22. `targetpilot-b7bd7b744523fc66`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / HMGB1 knockdown and hyperglycemia model characterization`
- Sentence: `s0139`; canonical offsets: `[19461, 19715)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> By measuring carbon dioxide production (VCO2) and oxygen consumption (VO2) and calculating the Respiratory Exchange Ratio (RER), we found that the NC + STZ group utilized a greater proportion of non-lipid sources compared to the HFD and HFD + STZ groups.

HunFlair2 suggestions:
- `[13, 27)` 'carbon dioxide' — Chemical (score=1.0000)
- `[50, 56)` 'oxygen' — Chemical (score=1.0000)
- `[152, 155)` 'STZ' — Chemical (score=1.0000)
- `[199, 204)` 'lipid' — Chemical (score=1.0000)
- `[243, 246)` 'STZ' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 23. `targetpilot-0fa0d10872f1db65`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / HMGB1 knockdown and hyperglycemia model characterization`
- Sentence: `s0145`; canonical offsets: `[20166, 20267)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Our results showed that the HMGB1 gene was absent only in iHMGB1 KO mice that received TMX injection.

HunFlair2 suggestions:
- `[28, 33)` 'HMGB1' — Gene (score=1.0000)
- `[68, 72)` 'mice' — Species (score=1.0000)
- `[87, 90)` 'TMX' — Chemical (score=1.0000)

AIONER suggestions (when available):
- `[58, 64)` 'iHMGB1' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 24. `targetpilot-6be02629521c80da`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / HMGB1 knockdown and hyperglycemia model characterization`
- Sentence: `s0148`; canonical offsets: `[20479, 20745)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> (C) Representative Western blot images and quantification of HMGB1 levels in different tissues (liver, kidney, heart, and lung) harvested from iHMGB1 KO TMX STZ and HMGB1 Flox TMX STZ mice showing a significant decrease in HMGB1 expression in iHMGB1 KO TMX STZ mice.

HunFlair2 suggestions:
- `[61, 66)` 'HMGB1' — Gene (score=1.0000)
- `[157, 160)` 'STZ' — Chemical (score=1.0000)
- `[165, 170)` 'HMGB1' — Gene (score=1.0000)
- `[180, 183)` 'STZ' — Chemical (score=1.0000)
- `[184, 188)` 'mice' — Species (score=1.0000)
- `[223, 228)` 'HMGB1' — Gene (score=1.0000)
- `[257, 260)` 'STZ' — Chemical (score=1.0000)
- `[261, 265)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- `[257, 260)` 'STZ' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 25. `targetpilot-3c894fd3a3b35fff`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / HMGB1 knockdown and hyperglycemia model characterization`
- Sentence: `s0157`; canonical offsets: `[21162, 21366)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> 3Impact of HMGB1 Knockdown on Hyperglycemia Development and Glucose Tolerance(A) Glucose levels in iHMGB1 KO TMX STZ and HMGB1 Flox TMX STZ mice show no significant difference pre- and post-TMX injection.

HunFlair2 suggestions:
- `[11, 16)` 'HMGB1' — Gene (score=1.0000)
- `[30, 43)` 'Hyperglycemia' — Disease (score=1.0000)
- `[60, 77)` 'Glucose Tolerance' — Chemical (score=0.7427)
- `[81, 88)` 'Glucose' — Chemical (score=1.0000)
- `[113, 116)` 'STZ' — Chemical (score=1.0000)
- `[121, 126)` 'HMGB1' — Gene (score=1.0000)
- `[136, 139)` 'STZ' — Chemical (score=1.0000)
- `[140, 144)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- `[190, 193)` 'TMX' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 26. `targetpilot-a686ae4e0f955c2f`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / HMGB1 knockdown decreases hepatic liver damage in hyperglycemic mice`
- Sentence: `s0193`; canonical offsets: `[26076, 26443)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Our assessment of the plasma samples collected from HMGB1 Flox TMX STZ and iHMGB1 KO TMX STZ mice following 10 weeks post last injection revealed that although ALT levels were comparable between the two groups, HMGB1 Flox TMX STZ mice displayed significantly elevated levels of AST, an indicator of liver damage, compared to iHMGB1 KO TMX STZ mice (Supplemental Figs.

HunFlair2 suggestions:
- `[52, 57)` 'HMGB1' — Gene (score=1.0000)
- `[67, 70)` 'STZ' — Chemical (score=1.0000)
- `[75, 81)` 'iHMGB1' — Gene (score=0.9998)
- `[89, 92)` 'STZ' — Chemical (score=1.0000)
- `[93, 97)` 'mice' — Species (score=1.0000)
- `[160, 163)` 'ALT' — Gene (score=1.0000)
- `[211, 216)` 'HMGB1' — Gene (score=1.0000)
- `[226, 229)` 'STZ' — Chemical (score=1.0000)
- `[230, 234)` 'mice' — Species (score=1.0000)
- `[278, 281)` 'AST' — Gene (score=1.0000)
- `[299, 311)` 'liver damage' — Disease (score=1.0000)
- `[325, 331)` 'iHMGB1' — Gene (score=0.9998)
- `[339, 342)` 'STZ' — Chemical (score=1.0000)
- `[343, 347)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 27. `targetpilot-b471da77e5cdfcda`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / RNA sequencing identified insulin signaling and glucose metabolism pathways to be altered in skeletal muscle`
- Sentence: `s0231`; canonical offsets: `[31425, 31576)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Our IPA analysis revealed unique pathways altered in skeletal muscle in iHMGB1 KO TMX STZ mice, which were distinct from those identified in the liver.

HunFlair2 suggestions:
- `[72, 78)` 'iHMGB1' — Gene (score=1.0000)
- `[86, 89)` 'STZ' — Chemical (score=1.0000)
- `[90, 94)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 28. `targetpilot-01d6fe15d4c1a98b`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Results / RNA sequencing identified insulin signaling and glucose metabolism pathways to be altered in skeletal muscle`
- Sentence: `s0249`; canonical offsets: `[34166, 34256)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> 5
>
> DM is a complex disease that involves both metabolic dysfunction and inflammation [39].

HunFlair2 suggestions:
- `[3, 5)` 'DM' — Disease (score=1.0000)
- `[46, 67)` 'metabolic dysfunction' — Disease (score=1.0000)
- `[72, 84)` 'inflammation' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 29. `targetpilot-2d9327b0cff747a3`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Discussion`
- Sentence: `s0275`; canonical offsets: `[38451, 38704)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> This discovery carries substantial relevance, as numerous investigations have substantiated that the attenuation of blood glucose concentrations can markedly diminish the incidence of diabetes-related complications observed in clinical contexts [58,59].

HunFlair2 suggestions:
- `[116, 129)` 'blood glucose' — Chemical (score=1.0000)
- `[184, 192)` 'diabetes' — Disease (score=0.9999)
- `[193, 200)` 'related' — Disease (score=0.8596)

AIONER suggestions (when available):
- `[122, 129)` 'glucose' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 30. `targetpilot-c2d67dc0709aacc9`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Discussion`
- Sentence: `s0317`; canonical offsets: `[45535, 45674)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Additionally, we aim to explore the potential tissue-specific effects of HMGB1 knockdown to further elucidate the exact mechanisms at play.

HunFlair2 suggestions:
- `[73, 78)` 'HMGB1' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 31. `targetpilot-d6b298b40113097a`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Data availability statement`
- Sentence: `s0320`; canonical offsets: `[46242, 46541)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> The data that support the findings of this is available in the MENDELEY DATA repository: Mota Alvidrez, Roberto (2023), “Restoring Glucose Balance: Conditional HMGB1 Knockdown Mitigates Hyperglycemia in A Streptozotocin Induced Mouse Model”, Mendeley Data, V1, https://doi.org/10.17632/ryz5h94pyh.1.

HunFlair2 suggestions:
- `[131, 138)` 'Glucose' — Chemical (score=1.0000)
- `[160, 165)` 'HMGB1' — Gene (score=1.0000)
- `[186, 199)` 'Hyperglycemia' — Disease (score=1.0000)
- `[205, 219)` 'Streptozotocin' — Chemical (score=1.0000)
- `[228, 233)` 'Mouse' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 32. `targetpilot-786dc70e012a4f00`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Funding`
- Sentence: `s0321`; canonical offsets: `[46543, 46828)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> NIGMS 3R35GM119526-07S1 to RIMA; 10.13039/100008237Department of Surgery and Pittsburgh Liver Research Center P&F Award Funding for RIMA (P30 DK120531); 10.13039/100000050NHLBI R25HL145817 to RIMA; 10.13039/100006108NCATS KL2 TR001448 funding for RIMA (10.13039/100007179UNM HSC CTSC).

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 33. `targetpilot-1b6bcb4b5b6bd7de`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Additional Information`
- Sentence: `s0322`; canonical offsets: `[46830, 47024)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Raw data, methods, protocols, software, hardware and other outputs – associated with the paper data is included in the MENDELEY Data Repository included in the Data Availability Statement above.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 34. `targetpilot-95717cc839f1aecc`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `CRediT authorship contribution statement`
- Sentence: `s0324`; canonical offsets: `[47160, 47252)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> Gowtham Annarapu: Visualization, Methodology, Investigation, Formal analysis, Data curation.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 35. `targetpilot-19dc21baee43d529`

- Paper: `PMCID:PMC10770459` (PMID `38187339`, PMCID `PMC10770459`)
- Split: `train`; section: `Declaration of Competing interest`
- Sentence: `s0337`; canonical offsets: `[48089, 48203)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`

> The authors declare the following financial interests/personal relationships which may be considered as potential.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 36. `targetpilot-145086f5c3e42891`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `abstract`
- Sentence: `s0004`; canonical offsets: `[525, 641)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> In this study, an AD mouse model was established through lateral ventricular injection of amyloid-beta1–42 (Aβ1–42).

HunFlair2 suggestions:
- `[18, 20)` 'AD' — Disease (score=1.0000)
- `[21, 26)` 'mouse' — Species (score=1.0000)
- `[90, 106)` 'amyloid-beta1–42' — Gene (score=1.0000)
- `[108, 114)` 'Aβ1–42' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 37. `targetpilot-455b4eb4c26f6da9`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `1. Introduction`
- Sentence: `s0019`; canonical offsets: `[2574, 2887)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Research indicates that although the brain utilizes approximately 20% of the body's oxygen intake, the high proportion of polyunsaturated fatty acids in neuronal membranes and the limited capacity of the antioxidant system render neurons particularly vulnerable to the deleterious effects of oxidative stress [2].

HunFlair2 suggestions:
- `[84, 90)` 'oxygen' — Chemical (score=1.0000)
- `[122, 149)` 'polyunsaturated fatty acids' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 38. `targetpilot-8e5f71a3513bee67`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `1. Introduction`
- Sentence: `s0024`; canonical offsets: `[3652, 3904)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Moreover, hyperphosphorylation of Tau, microtubule disturbances, and Tau accumulation have been observed to promote ROS production [10], while oxidative stress also contributes to the formation of phosphorylated-Tau (p-Tau) and neurofibrillary tangles.

HunFlair2 suggestions:
- `[34, 37)` 'Tau' — Gene (score=0.9953)
- `[69, 72)` 'Tau' — Gene (score=0.9901)
- `[116, 119)` 'ROS' — Chemical (score=1.0000)
- `[212, 215)` 'Tau' — Gene (score=0.9979)
- `[219, 222)` 'Tau' — Gene (score=0.9930)

AIONER suggestions (when available):
- `[228, 251)` 'neurofibrillary tangles' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 39. `targetpilot-0c27136b96e54f49`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `1. Introduction`
- Sentence: `s0030`; canonical offsets: `[4856, 5016)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Additionally, SFPQ has been found to affect the transcriptional elongation of particularly long genes, those over 100 kilobases, in the developing murine brain.

HunFlair2 suggestions:
- `[14, 18)` 'SFPQ' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[147, 153)` 'murine' — Species

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 40. `targetpilot-2d83611b1c61d63f`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `1. Introduction`
- Sentence: `s0036`; canonical offsets: `[5933, 6187)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> SFPQ levels were found to be decreased in the postmortem brains of patients with rapidly progressing AD (rpAD), sporadic Creutzfeldt–Jakob disease (sCJD, a rapidly progressive form of dementia), and in 3xTg (amyloid precursor protein [APP]/PS1/Tau) mice.

HunFlair2 suggestions:
- `[0, 4)` 'SFPQ' — Gene (score=1.0000)
- `[67, 75)` 'patients' — Species (score=1.0000)
- `[101, 103)` 'AD' — Disease (score=1.0000)
- `[105, 109)` 'rpAD' — Disease (score=1.0000)
- `[112, 146)` 'sporadic Creutzfeldt–Jakob disease' — Disease (score=1.0000)
- `[148, 152)` 'sCJD' — Disease (score=1.0000)
- `[184, 192)` 'dementia' — Disease (score=1.0000)
- `[208, 233)` 'amyloid precursor protein' — Gene (score=1.0000)
- `[235, 238)` 'APP' — Gene (score=1.0000)
- `[240, 243)` 'PS1' — Gene (score=1.0000)
- `[244, 247)` 'Tau' — Gene (score=1.0000)
- `[249, 253)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 41. `targetpilot-bd0273fecd8d70ec`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `1. Introduction`
- Sentence: `s0039`; canonical offsets: `[6521, 6615)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Additionally, there was a notable colocalization of SFPQ with p-Tau in the extranuclear space.

HunFlair2 suggestions:
- `[52, 56)` 'SFPQ' — Gene (score=1.0000)
- `[62, 67)` 'p-Tau' — Gene (score=0.9999)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 42. `targetpilot-904a13a4e0fd11dc`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.1. Animals`
- Sentence: `s0054`; canonical offsets: `[8639, 8682)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> (License number: SCXK [Beijing] 2019-0010).

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 43. `targetpilot-731d27e572faca32`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.1. Animals`
- Sentence: `s0056`; canonical offsets: `[8749, 8933)`
- Sampling: `A` — model_disagreement:hunflair2_only
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Following the adeno-associated virus (AAV) injection, three mice in the control group and three in the experimental group expired prior to the repetition of the behavioral experiments.

HunFlair2 suggestions:
- `[14, 36)` 'adeno-associated virus' — Species (score=0.9989)
- `[38, 41)` 'AAV' — Species (score=0.9999)
- `[60, 64)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 44. `targetpilot-c4186d65df653391`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.2. Brain Stereotaxic Instrument Injection`
- Sentence: `s0062`; canonical offsets: `[9692, 9931)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> To develop an animal model of AD, we referred to the stereotaxic atlas of the mouse brain and selected the right lateral ventricle (coordinates: anterior/posterior: −0.94 mm, medial/lateral: −1.5 mm, dorsal/ventral: −2.1 mm) for injection.

HunFlair2 suggestions:
- `[30, 32)` 'AD' — Disease (score=1.0000)
- `[78, 83)` 'mouse' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 45. `targetpilot-de2734fed0c53c00`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.3. Aβ1–42 Solution Preparation`
- Sentence: `s0066`; canonical offsets: `[10227, 10334)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The solution was aliquoted into 200 μL in centrifuge tubes to prevent repeated freezing and thawing cycles.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 46. `targetpilot-7b1ab0597a157566`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.4. AAV9-Green Fluorescent Protein (GFP) Injection`
- Sentence: `s0069`; canonical offsets: `[10492, 10725)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The experimental group utilized an AAV-GFP system to overexpress SFPQ in the bilateral hippocampus, as guided by the stereotaxic atlas of the mouse brain (anterior/posterior: −2.3 mm; medial/lateral: ±2 mm; dorsal/ventral: ±1.75 mm).

HunFlair2 suggestions:
- `[142, 147)` 'mouse' — Species (score=0.9999)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 47. `targetpilot-9639fc4aa161068d`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.5. Western Blotting`
- Sentence: `s0075`; canonical offsets: `[11425, 11643)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The proteins on the gel were electrotransferred onto PVDF membranes and then membranes were blocked with a blocking solution for 2 h at room temperature, followed by incubation with a primary antibody at 4°C overnight.

HunFlair2 suggestions:
- `[53, 57)` 'PVDF' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 48. `targetpilot-6809e7c22e0fea83`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.5. Western Blotting`
- Sentence: `s0076`; canonical offsets: `[11644, 12213)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The primary antibodies used were those raised against SFPQ (Abcam, 1:10,000), APP (Proteintech, 1:1000), Tau (CST, 1:1000), GST (glutathione S-transferase) (Abcam, 1:5000), HO-1 (heme oxygenase-1) (Abcam, 1:2000), Bcl-2 (Abcam, 1:2000), Bax (Abcam, 1:2,000), PSD95 (Abcam, 1:2000), p-CREB (cAMP response element-binding) (Abcam, 1:5000), AKT (Abcam, 1:1000), phosphorylated protein kinase B (p-AKT) (Abcam, 1:1000), PI3K (Abcam, 1:1000), phosphorylated phosphoinositide 3-kinase (p-PI3K) (Abcam, 1:1000), β-tubulin (Abcam, 1:1000), and GAPDH (Abcam, 1:10,000) proteins.

HunFlair2 suggestions:
- `[54, 58)` 'SFPQ' — Gene (score=0.9999)
- `[60, 65)` 'Abcam' — Gene (score=1.0000)
- `[78, 81)` 'APP' — Gene (score=0.9999)
- `[105, 108)` 'Tau' — Gene (score=0.9993)
- `[110, 113)` 'CST' — Gene (score=0.9999)
- `[124, 127)` 'GST' — Gene (score=1.0000)
- `[129, 154)` 'glutathione S-transferase' — Gene (score=1.0000)
- `[157, 162)` 'Abcam' — Gene (score=1.0000)
- `[173, 177)` 'HO-1' — Gene (score=1.0000)
- `[179, 195)` 'heme oxygenase-1' — Gene (score=1.0000)
- `[198, 203)` 'Abcam' — Gene (score=1.0000)
- `[214, 219)` 'Bcl-2' — Gene (score=1.0000)
- `[221, 226)` 'Abcam' — Gene (score=1.0000)
- `[237, 240)` 'Bax' — Gene (score=1.0000)
- `[242, 247)` 'Abcam' — Gene (score=1.0000)
- `[259, 264)` 'PSD95' — Gene (score=1.0000)
- `[266, 271)` 'Abcam' — Gene (score=1.0000)
- `[282, 288)` 'p-CREB' — Gene (score=0.9999)
- `[290, 319)` 'cAMP response element-binding' — Gene (score=0.9999)
- `[322, 327)` 'Abcam' — Gene (score=1.0000)
- `[338, 341)` 'AKT' — Gene (score=1.0000)
- `[343, 348)` 'Abcam' — Gene (score=1.0000)
- `[374, 390)` 'protein kinase B' — Gene (score=0.9998)
- `[392, 397)` 'p-AKT' — Gene (score=0.9999)
- `[400, 405)` 'Abcam' — Gene (score=0.9999)
- `[416, 420)` 'PI3K' — Gene (score=1.0000)
- `[422, 427)` 'Abcam' — Gene (score=1.0000)
- `[453, 478)` 'phosphoinositide 3-kinase' — Gene (score=0.9998)
- `[480, 486)` 'p-PI3K' — Gene (score=0.9999)
- `[489, 494)` 'Abcam' — Gene (score=0.9999)
- `[505, 514)` 'β-tubulin' — Gene (score=1.0000)
- `[516, 521)` 'Abcam' — Gene (score=1.0000)
- `[536, 541)` 'GAPDH' — Gene (score=0.9999)
- `[543, 548)` 'Abcam' — Gene (score=0.9999)

AIONER suggestions (when available):
- `[482, 486)` 'PI3K' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 49. `targetpilot-c90a81de99d35af5`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.5. Western Blotting`
- Sentence: `s0077`; canonical offsets: `[12214, 12491)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The membrane was washed three times with TBST (Tris-buffered saline with 0.1% Tween 20) for 15 min each time, followed by incubation with horseradish peroxidase (HRP)-labeled goat antirabbit/antimouse IgG (1:5000), HRP-linked antibody (CST, 1:2000) at room temperature for 2 h.

HunFlair2 suggestions:
- `[41, 45)` 'TBST' — Chemical (score=0.5692)
- `[47, 51)` 'Tris' — Chemical (score=0.9724)
- `[52, 60)` 'buffered' — Chemical (score=0.7863)
- `[61, 67)` 'saline' — Chemical (score=0.8110)
- `[78, 86)` 'Tween 20' — Chemical (score=0.9999)
- `[150, 160)` 'peroxidase' — Gene (score=0.9998)
- `[162, 165)` 'HRP' — Gene (score=0.9995)
- `[175, 179)` 'goat' — Species (score=0.9994)
- `[201, 204)` 'IgG' — Gene (score=0.9614)
- `[215, 218)` 'HRP' — Gene (score=0.9888)
- `[236, 239)` 'CST' — Gene (score=0.7969)

AIONER suggestions (when available):
- `[47, 67)` 'Tris-buffered saline' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 50. `targetpilot-ffe77a826e991cf3`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.5. Western Blotting`
- Sentence: `s0078`; canonical offsets: `[12492, 12564)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The membrane was then washed three times with TBST for 15 min each time.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- `[46, 50)` 'TBST' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 51. `targetpilot-3a449de8d8e5f047`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `2. Materials and Methods / 2.10. Statistical Analysis`
- Sentence: `s0116`; canonical offsets: `[16474, 16708)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The independent t-test was employed for data meeting both normality and homogeneity of variance assumptions, while Welch's t-test was utilized for data satisfying the normality condition but not the homogeneity of variance assumption.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 52. `targetpilot-169f965bd3cabb06`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `3. Results / 3.5. Overexpression of SFPQ Activated the PI3K/AKT Pathway`
- Sentence: `s0152`; canonical offsets: `[22077, 22228)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Compared to the Vector group, the SFPQ overexpression group exhibited increased expression of PI3K, p-PI3K, and enhanced p-PI3K/PI3K ratio (Figure 5A).

HunFlair2 suggestions:
- `[34, 38)` 'SFPQ' — Chemical (score=1.0000)
- `[94, 98)` 'PI3K' — Gene (score=1.0000)
- `[102, 106)` 'PI3K' — Gene (score=1.0000)
- `[123, 127)` 'PI3K' — Gene (score=1.0000)
- `[128, 132)` 'PI3K' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 53. `targetpilot-fd64574b73378c34`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `3. Results / 3.5. Overexpression of SFPQ Activated the PI3K/AKT Pathway`
- Sentence: `s0153`; canonical offsets: `[22229, 22320)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Additionally, the expressions of AKT, P-AKT, and p-AKT/AKT ratio were elevated (Figure 5B).

HunFlair2 suggestions:
- `[33, 36)` 'AKT' — Gene (score=1.0000)
- `[40, 43)` 'AKT' — Gene (score=1.0000)
- `[51, 54)` 'AKT' — Gene (score=1.0000)
- `[55, 58)` 'AKT' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 54. `targetpilot-df02ded961bf0cb7`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `4. Discussion`
- Sentence: `s0168`; canonical offsets: `[24090, 24246)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> The present study demonstrated that overexpressing SFPQ in the hippocampus of AD mice significantly elevated the levels of antioxidant enzymes GST and HO-1.

HunFlair2 suggestions:
- `[51, 55)` 'SFPQ' — Chemical (score=0.9969)
- `[78, 80)` 'AD' — Disease (score=1.0000)
- `[81, 85)` 'mice' — Species (score=1.0000)
- `[143, 146)` 'GST' — Gene (score=1.0000)
- `[151, 155)` 'HO-1' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 55. `targetpilot-5d8e4124a75aac7a`

- Paper: `PMCID:PMC11824863` (PMID `39949834`, PMCID `PMC11824863`)
- Split: `train`; section: `4. Discussion`
- Sentence: `s0186`; canonical offsets: `[26513, 26705)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `8a43f612139aa84939933831a5bc7f5420122549fd69081d635b7becb80d2a15`

> Although this study did not explore the specific function of SFPQ as a splicing factor, the observed decrease in Tau following SFPQ overexpression may be associated with its splicing function.

HunFlair2 suggestions:
- `[61, 65)` 'SFPQ' — Gene (score=1.0000)
- `[113, 116)` 'Tau' — Gene (score=0.9999)
- `[127, 131)` 'SFPQ' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 56. `targetpilot-66bd3ca868888788`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Background`
- Sentence: `s0023`; canonical offsets: `[4507, 4663)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> As a member of E3 ubiquitin ligase, Cbl negatively regulates the receptor tyrosine kinase signaling by ubiquitination and natural killer cell function [11].

HunFlair2 suggestions:
- `[15, 34)` 'E3 ubiquitin ligase' — Gene (score=1.0000)
- `[36, 39)` 'Cbl' — Gene (score=1.0000)
- `[65, 89)` 'receptor tyrosine kinase' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 57. `targetpilot-5e72e9c2113c20dc`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Background`
- Sentence: `s0029`; canonical offsets: `[5712, 5815)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Also, p-JAK level has been detected to be diminished by knocking out Cbl in activated 293 T cells [18].

HunFlair2 suggestions:
- `[8, 11)` 'JAK' — Gene (score=1.0000)
- `[69, 72)` 'Cbl' — Gene (score=1.0000)
- `[86, 91)` '293 T' — CellLine (score=0.9269)

AIONER suggestions (when available):
- `[86, 91)` '293 T' — CellLine

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 58. `targetpilot-535c4bc51d6b53f3`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Ethical statement`
- Sentence: `s0035`; canonical offsets: `[6780, 6954)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> This experiment was approved by the Ethics Committee of Yantai Affiliated Hospital of Binzhou Medical University and conducted in compliance with the Declaration of Helsinki.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 59. `targetpilot-bcee42e4957c74c6`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Bioinformatics analysis`
- Sentence: `s0041`; canonical offsets: `[7720, 7940)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> The downloaded raw data was analyzed by the Affy R package and the limma R package was applied to identify differentially expressed genes (DEGs) with |logFoldChange|> 1 and adjusted p value < 0.05 as the threshold value.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 60. `targetpilot-c7911e0cd350889a`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Mouse model of DM`
- Sentence: `s0051`; canonical offsets: `[9221, 9348)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Then, rats were weighted and blood samples were collected to determine blood glucose, followed by lentivirus infection in vivo.

HunFlair2 suggestions:
- `[6, 10)` 'rats' — Species (score=1.0000)
- `[77, 84)` 'glucose' — Chemical (score=0.8409)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 61. `targetpilot-c249fbb51e2eceb2`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Hematoxylin–eosin (HE) staining`
- Sentence: `s0056`; canonical offsets: `[9818, 10061)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> The paraffin-embedded sections were baked, dewaxed with xylene, dehydrated with ethanol of gradient concentrations, and stained with hematoxylin (Beyotime Biotechnology Co., Ltd., Shanghai, China) for 5 min and with eosin (Beyotime) for 2 min.

HunFlair2 suggestions:
- `[4, 12)` 'paraffin' — Chemical (score=1.0000)
- `[56, 62)` 'xylene' — Chemical (score=1.0000)
- `[80, 87)` 'ethanol' — Chemical (score=1.0000)
- `[133, 144)` 'hematoxylin' — Chemical (score=1.0000)
- `[216, 221)` 'eosin' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 62. `targetpilot-b204fd25bad6d92c`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Immunohistochemistry (IHC)`
- Sentence: `s0067`; canonical offsets: `[11602, 11932)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> After blocked with goat serum (Solarbio, Beijing, China) for 20 min, the sections were incubated with anti-rabbit Cbl (1: 200, PA5-8292, Invitrogen, Carlsbad, CA, USA), anti-rabbit p-JAK2 (1: 2000, ab32101, Abcam, UK), anti-rabbit p-STAT4 (1: 100, ab28815, Abcam), and anti-mouse Runx3 (1: 500, ab135248, Abcam) overnight at 4 °C.

HunFlair2 suggestions:
- `[19, 23)` 'goat' — Species (score=1.0000)
- `[107, 113)` 'rabbit' — Species (score=1.0000)
- `[114, 117)` 'Cbl' — Gene (score=1.0000)
- `[174, 180)` 'rabbit' — Species (score=1.0000)
- `[183, 187)` 'JAK2' — Gene (score=1.0000)
- `[224, 230)` 'rabbit' — Species (score=1.0000)
- `[233, 238)` 'STAT4' — Gene (score=1.0000)
- `[274, 279)` 'mouse' — Species (score=1.0000)
- `[280, 285)` 'Runx3' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[295, 303)` 'ab135248' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 63. `targetpilot-7697dcd30f971ea2`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Cell culture and infection`
- Sentence: `s0078`; canonical offsets: `[13424, 13572)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Primary HUVECs were cultured in Dulbecco’s Modified Eagle Medium (DMEM; Gibco) containing 10% FBS (Gibco) or HG medium (Gibco) at 37 °C with 5% CO2.

HunFlair2 suggestions:
- `[32, 64)` 'Dulbecco’s Modified Eagle Medium' — Chemical (score=1.0000)
- `[66, 70)` 'DMEM' — Chemical (score=1.0000)
- `[109, 118)` 'HG medium' — Chemical (score=1.0000)
- `[144, 147)` 'CO2' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 64. `targetpilot-8b4808d4707e6f8d`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Western blot analysis`
- Sentence: `s0086`; canonical offsets: `[15055, 15501)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> The primary antibodies used in the experiment included: anti-rabbit Cbl (1: 2000, ab32027, Abcam), anti-rabbit endothelial NO synthase (eNOS) (1: 1000, ab76198, Abcam), anti-rabbit JAK2 (1: 5000, ab108596, Abcam), anti-rabbit p-JAK2 (1: 2000, ab32101, Abcam), anti-rabbit STAT4 (1: 2000, ab235946, Abcam), anti-rabbit p-STAT4 (1: 1000, ab28815, Abcam), anti-mouse Runx3 (1: 2000, ab135248, Abcam), and anti-mouse β-actin (1: 5000, ab8225, Abcam).

HunFlair2 suggestions:
- `[61, 67)` 'rabbit' — Species (score=1.0000)
- `[68, 71)` 'Cbl' — Gene (score=1.0000)
- `[104, 110)` 'rabbit' — Species (score=1.0000)
- `[111, 134)` 'endothelial NO synthase' — Gene (score=1.0000)
- `[136, 140)` 'eNOS' — Gene (score=1.0000)
- `[174, 180)` 'rabbit' — Species (score=1.0000)
- `[181, 185)` 'JAK2' — Gene (score=1.0000)
- `[219, 225)` 'rabbit' — Species (score=1.0000)
- `[228, 232)` 'JAK2' — Gene (score=0.9980)
- `[265, 271)` 'rabbit' — Species (score=1.0000)
- `[272, 277)` 'STAT4' — Gene (score=1.0000)
- `[311, 317)` 'rabbit' — Species (score=1.0000)
- `[320, 325)` 'STAT4' — Gene (score=0.9995)
- `[358, 363)` 'mouse' — Species (score=1.0000)
- `[364, 369)` 'Runx3' — Gene (score=0.9999)
- `[407, 412)` 'mouse' — Species (score=1.0000)
- `[413, 420)` 'β-actin' — Gene (score=0.9999)

AIONER suggestions (when available):
- `[336, 343)` 'ab28815' — Variant

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 65. `targetpilot-df5d0f6e2f8cecda`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Materials and methods / Chromatin immunoprecipitation (ChIP)-qPCR`
- Sentence: `s0114`; canonical offsets: `[19169, 19234)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> The sequences of Runx3 are listed in Additional file 1: Table S2.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 66. `targetpilot-1dc4ef75321c8338`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Results / Cbl is poorly expressed in aortic tissues of DM rats and HG-induced cell model`
- Sentence: `s0138`; canonical offsets: `[22036, 22127)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> F Quantification of fasting blood glucose and body weight of rat before and after modeling.

HunFlair2 suggestions:
- `[28, 41)` 'blood glucose' — Chemical (score=0.9998)
- `[61, 64)` 'rat' — Species (score=1.0000)

AIONER suggestions (when available):
- `[34, 41)` 'glucose' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 67. `targetpilot-0e4a05b9dbfad4f1`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Results / Cbl inhibits the JAK2/STAT4 pathway and affects endothelial cell apoptosis`
- Sentence: `s0200`; canonical offsets: `[27670, 27835)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Further Western blot analysis on eNOS protein level determination in HG-induced HUVECs revealed downregulation of eNOS, which was reversed by overexpressed Cbl (Fig.

HunFlair2 suggestions:
- `[33, 37)` 'eNOS' — Gene (score=1.0000)
- `[69, 71)` 'HG' — Chemical (score=1.0000)
- `[114, 118)` 'eNOS' — Gene (score=1.0000)
- `[156, 159)` 'Cbl' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 68. `targetpilot-4251e00e101f0733`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Results / STAT4 promotes the expression of Runx3 by regulating the H3K4me3 level in the promoter region of Runx3`
- Sentence: `s0245`; canonical offsets: `[31636, 31698)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> The sh-STAT4-1 was selected for following ChIP-qPCR on HUVECs.

HunFlair2 suggestions:
- `[7, 12)` 'STAT4' — Gene (score=0.9993)

AIONER suggestions (when available):
- `[7, 14)` 'STAT4-1' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 69. `targetpilot-ee5d73806122f5fd`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Results / STAT4 promotes the expression of Runx3 by regulating the H3K4me3 level in the promoter region of Runx3`
- Sentence: `s0267`; canonical offsets: `[32923, 33068)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> G ChIP-qPCR of relative H3K4me3 and STAT4 recruitment level in HUVECs under Con treatment and transfection with sh-STAT4-1, oe-STAT4 or controls.

HunFlair2 suggestions:
- `[24, 31)` 'H3K4me3' — Gene (score=0.9999)
- `[36, 41)` 'STAT4' — Gene (score=0.9999)
- `[115, 121)` 'STAT4-' — Gene (score=0.8218)
- `[127, 132)` 'STAT4' — Gene (score=0.9999)

AIONER suggestions (when available):
- `[115, 122)` 'STAT4-1' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 70. `targetpilot-bbcaffd6418f0984`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Results / Cbl alleviates HUVEC dysfunction in DM rats by inhibiting the activation of the JAK2/STAT4 pathway through reducing Runx3 expression`
- Sentence: `s0326`; canonical offsets: `[39515, 39705)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Compared with that of the oe-NC-treated rats, the serum NO content of the oe-Cbl + oe-NC-treated rats increased while the treatment of oe-Runx3 decreased the increase induced by oe-Cbl (Fig.

HunFlair2 suggestions:
- `[40, 44)` 'rats' — Species (score=1.0000)
- `[56, 58)` 'NO' — Chemical (score=1.0000)
- `[77, 80)` 'Cbl' — Gene (score=1.0000)
- `[97, 101)` 'rats' — Species (score=1.0000)
- `[138, 143)` 'Runx3' — Gene (score=1.0000)
- `[181, 184)` 'Cbl' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 71. `targetpilot-4b2e0eda41a70f22`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Results / Cbl alleviates HUVEC dysfunction in DM rats by inhibiting the activation of the JAK2/STAT4 pathway through reducing Runx3 expression`
- Sentence: `s0332`; canonical offsets: `[40155, 40254)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> 7Cbl improves HUVEC dysfunction by inhibiting Runx3 expression and inactivating JAK2/STAT4 pathway.

HunFlair2 suggestions:
- `[46, 51)` 'Runx3' — Gene (score=1.0000)
- `[80, 84)` 'JAK2' — Gene (score=1.0000)
- `[85, 90)` 'STAT4' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[0, 4)` '7Cbl' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 72. `targetpilot-ab3e6b166ec45189`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Discussion`
- Sentence: `s0349`; canonical offsets: `[42425, 42527)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Improvement of NO bioavailability and production thus becomes one of promising therapeutic strategies.

HunFlair2 suggestions:
- `[15, 17)` 'NO' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 73. `targetpilot-b00521e590e2c485`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Discussion`
- Sentence: `s0366`; canonical offsets: `[45266, 45444)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Cryptotanshinone, fat-soluble phenanthrene quinone, inhibits cell progression of lung tumors by increasing CD4+ T cell toxicity through activation of the JAK2/STAT4 pathway [37].

HunFlair2 suggestions:
- `[0, 16)` 'Cryptotanshinone' — Chemical (score=1.0000)
- `[30, 50)` 'phenanthrene quinone' — Chemical (score=1.0000)
- `[81, 92)` 'lung tumors' — Disease (score=1.0000)
- `[107, 110)` 'CD4' — Gene (score=0.9928)
- `[119, 127)` 'toxicity' — Disease (score=1.0000)
- `[154, 158)` 'JAK2' — Gene (score=1.0000)
- `[159, 164)` 'STAT4' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 74. `targetpilot-1d425a1985959ac5`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Discussion`
- Sentence: `s0371`; canonical offsets: `[46026, 46284)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> Moreover, we indicated that silencing of STAT4 stimulated the production of NO in HUVECs and inhibited apoptosis, which was reversed by overexpression of Runx3; moreover, the overexpressed Runx3 alleviated the inhibitory effect of Cbl on apoptosis of HUVECs.

HunFlair2 suggestions:
- `[41, 46)` 'STAT4' — Gene (score=1.0000)
- `[154, 159)` 'Runx3' — Gene (score=1.0000)
- `[189, 194)` 'Runx3' — Gene (score=1.0000)
- `[231, 234)` 'Cbl' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 75. `targetpilot-95753a6e9fade835`

- Paper: `PMCID:PMC8605525` (PMID `34798872`, PMCID `PMC8605525`)
- Split: `test`; section: `Conclusion`
- Sentence: `s0374`; canonical offsets: `[46632, 46801)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `99355676f17885e8920e1f56447b8c6aff219cb6be09d76777084e339261a39b`

> In conclusion, this study elucidates the mechanism that Cbl alleviates endothelial dysfunction in DM through inhibiting the JAK2/STAT4 pathway and Runx3 expression (Fig.

HunFlair2 suggestions:
- `[56, 59)` 'Cbl' — Chemical (score=1.0000)
- `[71, 94)` 'endothelial dysfunction' — Disease (score=1.0000)
- `[98, 100)` 'DM' — Disease (score=1.0000)
- `[124, 128)` 'JAK2' — Gene (score=1.0000)
- `[129, 134)` 'STAT4' — Gene (score=1.0000)
- `[147, 152)` 'Runx3' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 76. `targetpilot-4e3ca758e2609754`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `title`
- Sentence: `s0001`; canonical offsets: `[0, 103)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> EZH2 promotes colorectal cancer stem-like cell expansion by activating p21cip1-Wnt/β-catenin signaling.

HunFlair2 suggestions:
- `[0, 4)` 'EZH2' — Gene (score=1.0000)
- `[14, 31)` 'colorectal cancer' — Disease (score=1.0000)
- `[71, 82)` 'p21cip1-Wnt' — Gene (score=1.0000)
- `[83, 92)` 'β-catenin' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[79, 82)` 'Wnt' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 77. `targetpilot-1a15180e1e5e6e4c`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0002`; canonical offsets: `[105, 259)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Because colorectal cancer (CRC) stem-like cells (CCS-like cells) contribute to poor patient prognosis, these cells are a potential target for CRC therapy.

HunFlair2 suggestions:
- `[8, 25)` 'colorectal cancer' — Disease (score=1.0000)
- `[27, 30)` 'CRC' — Disease (score=1.0000)
- `[84, 91)` 'patient' — Species (score=1.0000)
- `[142, 145)` 'CRC' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 78. `targetpilot-0f46c4f054dd3fd4`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0003`; canonical offsets: `[260, 354)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> However, the mechanism underlying the maintenance of CCS-like cell properties remains unclear.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 79. `targetpilot-20376b03421895c7`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0004`; canonical offsets: `[355, 493)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Here, we found that patients with advanced stage CRC expressed high levels of polycomb group protein enhancer of zeste homologue 2 (EZH2).

HunFlair2 suggestions:
- `[20, 28)` 'patients' — Species (score=1.0000)
- `[49, 52)` 'CRC' — Disease (score=1.0000)
- `[78, 100)` 'polycomb group protein' — Gene (score=0.9594)
- `[101, 130)` 'enhancer of zeste homologue 2' — Gene (score=1.0000)
- `[132, 136)` 'EZH2' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[20, 28)` 'patients' — Species

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 80. `targetpilot-ac29f268f37aa250`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0005`; canonical offsets: `[494, 574)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> High expression of EZH2 in tumor tissues correlated with poor patient prognosis.

HunFlair2 suggestions:
- `[19, 23)` 'EZH2' — Gene (score=1.0000)
- `[27, 32)` 'tumor' — Disease (score=1.0000)
- `[62, 69)` 'patient' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 81. `targetpilot-20f792c3269715d1`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0006`; canonical offsets: `[575, 633)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Conversely, silencing EZH2 reduced CRC cell proliferation.

HunFlair2 suggestions:
- `[22, 26)` 'EZH2' — Gene (score=1.0000)
- `[35, 38)` 'CRC' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 82. `targetpilot-e504b22a4d3cf300`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0007`; canonical offsets: `[634, 758)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Surprisingly, EZH2 was more highly expressed in the CCS-like cell subpopulation than in the non-CCS-like cell subpopulation.

HunFlair2 suggestions:
- `[14, 18)` 'EZH2' — Gene (score=1.0000)
- `[52, 55)` 'CCS' — Disease (score=0.9984)
- `[96, 99)` 'CCS' — Disease (score=0.9173)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 83. `targetpilot-0012569b6d4a915f`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0008`; canonical offsets: `[759, 1002)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> EZH2 knockdown significantly reduced the CD133+/CD44+ subpopulation, suppressed mammosphere formation, and decreased the expression of self-renewal-related genes and strongly impaired tumor-initiating capacity in a re-implantation mouse model.

HunFlair2 suggestions:
- `[0, 4)` 'EZH2' — Gene (score=1.0000)
- `[41, 47)` 'CD133+' — Gene (score=1.0000)
- `[48, 52)` 'CD44' — Gene (score=1.0000)
- `[184, 189)` 'tumor' — Disease (score=1.0000)
- `[231, 236)` 'mouse' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 84. `targetpilot-b933104b6c21da71`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0009`; canonical offsets: `[1003, 1193)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Gene expression data from 433 human CRC specimens from TCGA database and in vitro results revealed that EZH2 helped maintain CCS-like cell properties by activating the Wnt/β-catenin pathway.

HunFlair2 suggestions:
- `[30, 35)` 'human' — Species (score=1.0000)
- `[36, 39)` 'CRC' — Disease (score=1.0000)
- `[104, 108)` 'EZH2' — Gene (score=1.0000)
- `[168, 171)` 'Wnt' — Gene (score=1.0000)
- `[172, 181)` 'β-catenin' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 85. `targetpilot-d15580a6d6df876e`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0010`; canonical offsets: `[1194, 1336)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> We further revealed that p21cip1-mediated arrest of the cell cycle at G1/S phase is required for EZH2 activation of the Wnt/β-catenin pathway.

HunFlair2 suggestions:
- `[25, 41)` 'p21cip1-mediated' — Gene (score=1.0000)
- `[97, 101)` 'EZH2' — Gene (score=1.0000)
- `[120, 123)` 'Wnt' — Gene (score=1.0000)
- `[124, 133)` 'β-catenin' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[124, 133)` 'β-catenin' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 86. `targetpilot-a182c59a63b1d123`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0011`; canonical offsets: `[1337, 1434)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Moreover, the specific EZH2 inhibitor EPZ-6438, a clinical trial drug, prevented CRC progression.

HunFlair2 suggestions:
- `[23, 27)` 'EZH2' — Gene (score=1.0000)
- `[38, 46)` 'EPZ-6438' — Chemical (score=1.0000)
- `[81, 84)` 'CRC' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[81, 84)` 'CRC' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 87. `targetpilot-1b0389ecafe85c51`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0012`; canonical offsets: `[1435, 1566)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> Collectively, these findings revealed EZH2 maintaining CCS-like cell characteristics by arresting the cell cycle at the G1/S phase.

HunFlair2 suggestions:
- `[38, 42)` 'EZH2' — Gene (score=1.0000)
- `[55, 58)` 'CCS' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 88. `targetpilot-879385abbccf6abf`

- Paper: `PMID:27172794` (PMID `27172794`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0013`; canonical offsets: `[1567, 1620)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `50d58062a480653e0f414aad9e62aca434898fa3fcc6f372722454bd75407a0c`

> These results indicate a new approach to CRC therapy.

HunFlair2 suggestions:
- `[41, 44)` 'CRC' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 89. `targetpilot-83686e1ec716208d`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `title`
- Sentence: `s0001`; canonical offsets: `[0, 137)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> Knocking down of p53 triggers apoptosis and autophagy, concomitantly with inhibition of migration on SSC-4 oral squamous carcinoma cells.

HunFlair2 suggestions:
- `[17, 20)` 'p53' — Gene (score=1.0000)
- `[101, 106)` 'SSC-4' — CellLine (score=0.9910)
- `[107, 130)` 'oral squamous carcinoma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 90. `targetpilot-bac8e19d90e292dc`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0002`; canonical offsets: `[139, 314)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> Oral squamous cell carcinoma (OSCC) is a malignancy with elevated prevalence and somber prognosis due to the fact that most of the patients are diagnosed at an advanced stage.

HunFlair2 suggestions:
- `[0, 28)` 'Oral squamous cell carcinoma' — Disease (score=1.0000)
- `[30, 34)` 'OSCC' — Disease (score=1.0000)
- `[41, 51)` 'malignancy' — Disease (score=1.0000)
- `[131, 139)` 'patients' — Species (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 91. `targetpilot-5fdc2f1676532da5`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0003`; canonical offsets: `[315, 436)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> p53 has a crucial role in proliferation and apoptosis during the occurrence and development of numerous malignant tumors.

HunFlair2 suggestions:
- `[0, 3)` 'p53' — Gene (score=1.0000)
- `[104, 120)` 'malignant tumors' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[0, 3)` 'p53' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 92. `targetpilot-d2c5f6c330df722b`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0004`; canonical offsets: `[437, 557)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> The impact of mutated p53 on the development and progression of OSCC is unclear and might have therapeutic implications.

HunFlair2 suggestions:
- `[22, 25)` 'p53' — Gene (score=1.0000)
- `[64, 68)` 'OSCC' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[64, 68)` 'OSCC' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 93. `targetpilot-75f4b12b77feca72`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0005`; canonical offsets: `[558, 765)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> Using an in vitro RNA interference experiment, we have evaluated the impact of p53 knockdown on cell viability, apoptosis, migration, and gene expression for key genes involved in apoptosis and angiogenesis.

HunFlair2 suggestions:
- `[79, 82)` 'p53' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 94. `targetpilot-e3149c6545474829`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0006`; canonical offsets: `[766, 899)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells.

HunFlair2 suggestions:
- `[46, 49)` 'p53' — Gene (score=1.0000)
- `[121, 126)` 'SSC-4' — CellLine (score=0.9928)

AIONER suggestions (when available):
- `[121, 126)` 'SSC-4' — CellLine

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 95. `targetpilot-2089aea1c9f60957`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0007`; canonical offsets: `[900, 995)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> Moreover, we observed that this has decreased migration and has blocked the expression of VEGF.

HunFlair2 suggestions:
- `[90, 94)` 'VEGF' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 96. `targetpilot-ebd97c2212d062cc`

- Paper: `PMID:27370646` (PMID `27370646`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0008`; canonical offsets: `[996, 1217)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `e4e9073658c15ecdee8014aa584944b8dfdbd589aa11090156b8fef17eb84c82`

> In conclusion, our research provides a proof that a direct connection between p53 knockdown and OSCC cell death can be established, therefore opening new potential directions in OSCC molecular therapeutics and management.

HunFlair2 suggestions:
- `[78, 81)` 'p53' — Gene (score=1.0000)
- `[96, 100)` 'OSCC' — Disease (score=1.0000)
- `[178, 182)` 'OSCC' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 97. `targetpilot-84f6c0dff983f226`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `title`
- Sentence: `s0001`; canonical offsets: `[0, 134)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> c-Myc Overexpression Promotes Oral Cancer Cell Proliferation and Migration by Enhancing Glutaminase and Glutamine Synthetase Activity.

HunFlair2 suggestions:
- `[0, 5)` 'c-Myc' — Gene (score=1.0000)
- `[30, 41)` 'Oral Cancer' — Disease (score=1.0000)
- `[88, 99)` 'Glutaminase' — Gene (score=1.0000)
- `[104, 124)` 'Glutamine Synthetase' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 98. `targetpilot-27b668215986ee2b`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / BACKGROUND`
- Sentence: `s0002`; canonical offsets: `[136, 288)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> This study aimed to investigate whether glutaminase (GLS) and glutamine synthetase (GS) are involved in c-Myc-mediated tumor development in oral cancer.

HunFlair2 suggestions:
- `[40, 51)` 'glutaminase' — Gene (score=1.0000)
- `[53, 56)` 'GLS' — Gene (score=1.0000)
- `[62, 82)` 'glutamine synthetase' — Gene (score=1.0000)
- `[84, 86)` 'GS' — Gene (score=1.0000)
- `[104, 109)` 'c-Myc' — Gene (score=1.0000)
- `[119, 124)` 'tumor' — Disease (score=1.0000)
- `[140, 151)` 'oral cancer' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 99. `targetpilot-ceb9d21fbcd048ed`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / METHODS`
- Sentence: `s0003`; canonical offsets: `[290, 516)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> The correlation between the expressions of c-Myc, GLS, and GS in clinical samples and the clinicopathologic features of oral cancer were examined using immunohistochemistry and quantitative real-time polymerase chain reaction.

HunFlair2 suggestions:
- `[43, 48)` 'c-Myc' — Gene (score=1.0000)
- `[50, 53)` 'GLS' — Gene (score=1.0000)
- `[59, 61)` 'GS' — Gene (score=1.0000)
- `[120, 131)` 'oral cancer' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 100. `targetpilot-b2de2c6441bc4f0e`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / METHODS`
- Sentence: `s0004`; canonical offsets: `[517, 739)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> After overexpressing the c-Myc gene and using an inhibitor of GLS or GS, functional experiments were performed to confirm the effects of c-Myc, GLS and GS on proliferation, cell cycle and migration in KB oral cancer cells.

HunFlair2 suggestions:
- `[25, 30)` 'c-Myc' — Gene (score=1.0000)
- `[62, 65)` 'GLS' — Gene (score=0.9999)
- `[69, 71)` 'GS' — Gene (score=0.9997)
- `[137, 142)` 'c-Myc' — Gene (score=1.0000)
- `[144, 147)` 'GLS' — Gene (score=1.0000)
- `[152, 154)` 'GS' — Gene (score=1.0000)
- `[201, 203)` 'KB' — CellLine (score=0.9940)
- `[204, 215)` 'oral cancer' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 101. `targetpilot-e505d22e5d9defaa`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / METHODS`
- Sentence: `s0005`; canonical offsets: `[740, 903)`
- Sampling: `A` — model_disagreement:type_disagreement
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> The expressions of E-cadherin and N-cadherin were determined by immunofluorescence assays in KB cells overexpressing c-Myc in the presence of GLS or GS inhibitors.

HunFlair2 suggestions:
- `[19, 29)` 'E-cadherin' — Gene (score=1.0000)
- `[34, 44)` 'N-cadherin' — Gene (score=1.0000)
- `[93, 95)` 'KB' — CellLine (score=0.9942)
- `[117, 122)` 'c-Myc' — Gene (score=1.0000)
- `[142, 145)` 'GLS' — Gene (score=1.0000)
- `[149, 151)` 'GS' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[142, 145)` 'GLS' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 102. `targetpilot-3dcdc75ac43dca73`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / RESULTS`
- Sentence: `s0006`; canonical offsets: `[905, 1004)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> The protein expression of GS was correlated with the Tumor, Lymph Node, and Metastasis (TNM) stage.

HunFlair2 suggestions:
- `[26, 28)` 'GS' — Gene (score=1.0000)
- `[53, 86)` 'Tumor, Lymph Node, and Metastasis' — Disease (score=0.9823)
- `[88, 91)` 'TNM' — Disease (score=0.9839)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 103. `targetpilot-7aae56cfdbf236ff`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / RESULTS`
- Sentence: `s0007`; canonical offsets: `[1005, 1083)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> In addition, c-Myc mRNA levels were positively correlated with GS mRNA levels.

HunFlair2 suggestions:
- `[13, 18)` 'c-Myc' — Gene (score=1.0000)
- `[63, 65)` 'GS' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 104. `targetpilot-b7acdc5015fae58e`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / RESULTS`
- Sentence: `s0008`; canonical offsets: `[1084, 1238)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> Overexpression of c-Myc increased the colonies derived from oral cancer cells and caused more cells to be in S phase compared with the mock-vehicle group.

HunFlair2 suggestions:
- `[18, 23)` 'c-Myc' — Gene (score=1.0000)
- `[60, 71)` 'oral cancer' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[18, 23)` 'c-Myc' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 105. `targetpilot-7de08f48e9b06cff`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / RESULTS`
- Sentence: `s0009`; canonical offsets: `[1239, 1346)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> The migratory speed of KB cells was promoted by overexpression of c-Myc compared to the mock-vehicle group.

HunFlair2 suggestions:
- `[23, 25)` 'KB' — CellLine (score=0.9948)
- `[66, 71)` 'c-Myc' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[23, 25)` 'KB' — CellLine

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 106. `targetpilot-f962a68a0e658980`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / RESULTS`
- Sentence: `s0010`; canonical offsets: `[1347, 1435)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> However, these effects were effectively reversed in the presence of GLS or GS inhibitor.

HunFlair2 suggestions:
- `[68, 71)` 'GLS' — Chemical (score=0.9999)
- `[75, 77)` 'GS' — Gene (score=0.9999)

AIONER suggestions (when available):
- `[68, 71)` 'GLS' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 107. `targetpilot-2eaa3d413a62d35e`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / RESULTS`
- Sentence: `s0011`; canonical offsets: `[1436, 1577)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> Furthermore, c-Myc could inhibit E-cadherin protein expression while promoting N-cadherin expression by enhancing the activity of GLS and GS.

HunFlair2 suggestions:
- `[13, 18)` 'c-Myc' — Gene (score=1.0000)
- `[33, 43)` 'E-cadherin' — Gene (score=1.0000)
- `[79, 89)` 'N-cadherin' — Gene (score=1.0000)
- `[130, 133)` 'GLS' — Gene (score=0.9972)
- `[138, 140)` 'GS' — Gene (score=0.9984)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 108. `targetpilot-85f27d53c80c129a`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / CONCLUSIONS`
- Sentence: `s0012`; canonical offsets: `[1579, 1687)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> c-Myc overexpression promotes oral cancer cell proliferation and migration by enhancing GLS and GS activity.

HunFlair2 suggestions:
- `[0, 5)` 'c-Myc' — Gene (score=1.0000)
- `[30, 41)` 'oral cancer' — Disease (score=1.0000)
- `[88, 91)` 'GLS' — Gene (score=1.0000)
- `[96, 98)` 'GS' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 109. `targetpilot-d3ebde837dd0786f`

- Paper: `PMID:31324362` (PMID `31324362`, PMCID `None`)
- Split: `train`; section: `abstract / CONCLUSIONS`
- Sentence: `s0013`; canonical offsets: `[1688, 1814)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `75c352846198e57b5bf66f031a22f88885df2892fd35d56366ba4cff14cc1d50`

> Our findings are beneficial for the identification of novel molecular targets for the prevention and treatment of oral cancer.

HunFlair2 suggestions:
- `[114, 125)` 'oral cancer' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 110. `targetpilot-1382b8be3fb4c048`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `title`
- Sentence: `s0001`; canonical offsets: `[0, 102)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> PTEN mediates serum deprivation-induced cytotoxicity in H9c2 cells via the PI3K/AKT signaling pathway.

HunFlair2 suggestions:
- `[0, 4)` 'PTEN' — Gene (score=1.0000)
- `[40, 52)` 'cytotoxicity' — Disease (score=1.0000)
- `[56, 60)` 'H9c2' — CellLine (score=0.9947)
- `[75, 79)` 'PI3K' — Gene (score=1.0000)
- `[80, 83)` 'AKT' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 111. `targetpilot-453cd78f419fef15`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0002`; canonical offsets: `[104, 214)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> The pathogenesis of acute myocardial infarction (AMI) is associated with cardiomyocyte necrosis and apoptosis.

HunFlair2 suggestions:
- `[20, 47)` 'acute myocardial infarction' — Disease (score=1.0000)
- `[49, 52)` 'AMI' — Disease (score=1.0000)
- `[87, 95)` 'necrosis' — Disease (score=0.9893)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 112. `targetpilot-75c236f31ab7390a`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0003`; canonical offsets: `[215, 365)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> Numerous studies have determined the regulatory effects of Phosphatase and tensin homolog (PTEN) cell proliferation and apoptosis in other cell types.

HunFlair2 suggestions:
- `[59, 89)` 'Phosphatase and tensin homolog' — Gene (score=1.0000)
- `[91, 95)` 'PTEN' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 113. `targetpilot-594d189f1f0be387`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0004`; canonical offsets: `[366, 430)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> However, the potential role of PTEN in cardiomyocyte is unclear.

HunFlair2 suggestions:
- `[31, 35)` 'PTEN' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 114. `targetpilot-9fc2a556c896c547`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0005`; canonical offsets: `[431, 557)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> In this study, we used H9c2 cells cultured under serum deprivation to simulate the apoptosis process of myocardial infarction.

HunFlair2 suggestions:
- `[23, 27)` 'H9c2' — CellLine (score=0.9949)
- `[104, 125)` 'myocardial infarction' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[23, 27)` 'H9c2' — CellLine

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 115. `targetpilot-c1a2c6afc9140f8a`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0006`; canonical offsets: `[558, 643)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> Small interference RNA (siRNA) of PTEN was used to knock down the expression of PTEN.

HunFlair2 suggestions:
- `[34, 38)` 'PTEN' — Gene (score=1.0000)
- `[80, 84)` 'PTEN' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 116. `targetpilot-b6ecd052d6532285`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0007`; canonical offsets: `[644, 683)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> Cell viability was determined by CCK-8.

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- `[33, 38)` 'CCK-8' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 117. `targetpilot-860f11ae1196189b`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0008`; canonical offsets: `[684, 789)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> Cell proliferation was examined by Edu staining, and the protein expression was analyzed by Western blot.

HunFlair2 suggestions:
- `[35, 38)` 'Edu' — Chemical (score=0.9905)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 118. `targetpilot-101102d68aa54ae6`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0009`; canonical offsets: `[790, 907)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> We also evaluated the generation of ROS, the degree of DNA damage, and cell apoptosis using immunofluorescence assay.

HunFlair2 suggestions:
- `[36, 39)` 'ROS' — Chemical (score=1.0000)

AIONER suggestions (when available):
- `[36, 39)` 'ROS' — Chemical

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 119. `targetpilot-75819ab393af98c8`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0010`; canonical offsets: `[908, 996)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> As a result, we observed that serum deprivation in H9c2 cells increased PTEN expression.

HunFlair2 suggestions:
- `[51, 55)` 'H9c2' — CellLine (score=0.9945)
- `[72, 76)` 'PTEN' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 120. `targetpilot-9c2c6b81b6703ede`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0011`; canonical offsets: `[997, 1174)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> Functionally, the PTEN knockdown experiment using siRNA inhibited serum deprivation-induced cell apoptosis, ROS production, and DNA damage, whereas increased cell proliferation.

HunFlair2 suggestions:
- `[18, 22)` 'PTEN' — Gene (score=1.0000)
- `[108, 111)` 'ROS' — Chemical (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 121. `targetpilot-4df95724d3ece230`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0012`; canonical offsets: `[1175, 1386)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> All these effects could be reversed by phosphatidylinositol 3-kinase (PI3K) inhibitor, which indicated the PI3K/protein kinase B (AKT) might be the critical component of the PTEN effects during serum deficiency.

HunFlair2 suggestions:
- `[39, 68)` 'phosphatidylinositol 3-kinase' — Gene (score=1.0000)
- `[70, 74)` 'PI3K' — Gene (score=1.0000)
- `[107, 111)` 'PI3K' — Gene (score=1.0000)
- `[112, 128)` 'protein kinase B' — Gene (score=1.0000)
- `[130, 133)` 'AKT' — Gene (score=1.0000)
- `[174, 178)` 'PTEN' — Gene (score=1.0000)
- `[194, 210)` 'serum deficiency' — Disease (score=0.9952)

AIONER suggestions (when available):
- `[70, 74)` 'PI3K' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 122. `targetpilot-119d9baadaab8c3f`

- Paper: `PMID:33652126` (PMID `33652126`, PMCID `None`)
- Split: `train`; section: `abstract`
- Sentence: `s0013`; canonical offsets: `[1387, 1516)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `44ee744a2e60c788db16927b63cda446174733d38c5e1cdb13e112af30f295e6`

> In conclusion, our study indicated the role of the PTEN/PI3K/AKT pathway in serum deprivation-induced cytotoxicity in H9c2 cells.

HunFlair2 suggestions:
- `[51, 55)` 'PTEN' — Gene (score=1.0000)
- `[56, 60)` 'PI3K' — Gene (score=1.0000)
- `[61, 64)` 'AKT' — Gene (score=1.0000)
- `[102, 114)` 'cytotoxicity' — Disease (score=1.0000)
- `[118, 122)` 'H9c2' — CellLine (score=0.9946)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 123. `targetpilot-703f21749ae69267`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `title`
- Sentence: `s0001`; canonical offsets: `[0, 81)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Knockdown of KIF23 alleviates the progression of asthma by inhibiting pyroptosis.

HunFlair2 suggestions:
- `[13, 18)` 'KIF23' — Gene (score=1.0000)
- `[49, 55)` 'asthma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 124. `targetpilot-f0c78206df668f3a`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / BACKGROUND`
- Sentence: `s0002`; canonical offsets: `[83, 190)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Asthma is a chronic disease affecting the lower respiratory tract, which can lead to death in severe cases.

HunFlair2 suggestions:
- `[0, 6)` 'Asthma' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 125. `targetpilot-93de8e8142b668a8`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / BACKGROUND`
- Sentence: `s0003`; canonical offsets: `[191, 316)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> The cause of asthma is not fully known, so exploring its potential mechanism is necessary for the targeted therapy of asthma.

HunFlair2 suggestions:
- `[13, 19)` 'asthma' — Disease (score=1.0000)
- `[118, 124)` 'asthma' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[118, 124)` 'asthma' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 126. `targetpilot-8a6cfccb00c6f74d`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / METHOD`
- Sentence: `s0004`; canonical offsets: `[318, 374)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Asthma mouse model was established with ovalbumin (OVA).

HunFlair2 suggestions:
- `[0, 6)` 'Asthma' — Disease (score=1.0000)
- `[7, 12)` 'mouse' — Species (score=1.0000)
- `[40, 49)` 'ovalbumin' — Gene (score=0.9925)
- `[51, 54)` 'OVA' — Gene (score=0.9568)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 127. `targetpilot-aa0325a8b1155793`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / METHOD`
- Sentence: `s0005`; canonical offsets: `[375, 476)`
- Sampling: `A` — model_disagreement:aioner_only
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> H&E staining, immunohistochemistry and ELISA were used to detect the inflammatory response in asthma.

HunFlair2 suggestions:
- `[94, 100)` 'asthma' — Disease (score=1.0000)

AIONER suggestions (when available):
- `[69, 81)` 'inflammatory' — Disease

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 128. `targetpilot-427d088c40f63d45`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / METHOD`
- Sentence: `s0006`; canonical offsets: `[477, 564)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Transcriptome sequencing was performed to screen differentially expressed genes (DEGs).

HunFlair2 suggestions:
- none recorded

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 129. `targetpilot-e5e6d105e14770b0`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / METHOD`
- Sentence: `s0007`; canonical offsets: `[565, 706)`
- Sampling: `C` — deterministic_general_coverage
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> The role of KIF23 silencing in cell viability, proliferation and apoptosis was explored by cell counting kit-8, EdU assay and flow cytometry.

HunFlair2 suggestions:
- `[12, 17)` 'KIF23' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 130. `targetpilot-532114a18d554ffc`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / METHOD`
- Sentence: `s0008`; canonical offsets: `[707, 823)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Effects of KIF23 knockdown on inflammation, oxidative stress and pyroptosis were detected by ELISA and western blot.

HunFlair2 suggestions:
- `[11, 16)` 'KIF23' — Gene (score=1.0000)
- `[30, 42)` 'inflammation' — Disease (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 131. `targetpilot-320c7d930396c64a`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / METHOD`
- Sentence: `s0009`; canonical offsets: `[824, 950)`
- Sampling: `A` — model_disagreement:boundary_disagreement
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> After screening KIF23-related signalling pathways, the effect of KIF23 on p53 signalling pathway was explored by western blot.

HunFlair2 suggestions:
- `[16, 29)` 'KIF23-related' — Gene (score=1.0000)
- `[65, 70)` 'KIF23' — Gene (score=1.0000)
- `[74, 77)` 'p53' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[74, 77)` 'p53' — Gene

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 132. `targetpilot-8012b8f84244d200`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / RESULTS`
- Sentence: `s0010`; canonical offsets: `[952, 1154)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> In the asthma model, the levels of caspase-3, IgG in serum and inflammatory factors (interleukin (IL)-1β, KC and tumour necrosis factor (TNF)-α) in serum and bronchoalveolar lavage fluid were increased.

HunFlair2 suggestions:
- `[7, 13)` 'asthma' — Disease (score=1.0000)
- `[35, 44)` 'caspase-3' — Gene (score=1.0000)
- `[46, 49)` 'IgG' — Gene (score=0.9998)
- `[63, 75)` 'inflammatory' — Disease (score=1.0000)
- `[85, 104)` 'interleukin (IL)-1β' — Gene (score=1.0000)
- `[106, 108)` 'KC' — Gene (score=1.0000)
- `[113, 143)` 'tumour necrosis factor (TNF)-α' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 133. `targetpilot-51c095255a500004`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / RESULTS`
- Sentence: `s0011`; canonical offsets: `[1155, 1281)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Transcriptome sequencing showed that there were 352 DEGs in the asthma model, and 7 hub genes including KIF23 were identified.

HunFlair2 suggestions:
- `[64, 70)` 'asthma' — Disease (score=1.0000)
- `[104, 109)` 'KIF23' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 134. `targetpilot-01a2670f85a93b43`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / RESULTS`
- Sentence: `s0012`; canonical offsets: `[1282, 1426)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Knockdown of KIF23 increased cell proliferation and inhibited apoptosis, inflammation and pyroptosis of BEAS-2B cells induced by IL-13 in vitro.

HunFlair2 suggestions:
- `[13, 18)` 'KIF23' — Gene (score=1.0000)
- `[73, 85)` 'inflammation' — Disease (score=1.0000)
- `[104, 111)` 'BEAS-2B' — CellLine (score=0.9864)
- `[129, 134)` 'IL-13' — Gene (score=1.0000)

AIONER suggestions (when available):
- `[104, 111)` 'BEAS-2B' — CellLine

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 135. `targetpilot-43342dbd0616a81a`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / RESULTS`
- Sentence: `s0013`; canonical offsets: `[1427, 1573)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> In vivo experiments verified that knockdown of KIF23 inhibited oxidative stress, inflammation and pyroptosis to alleviate OVA-induced asthma mice.

HunFlair2 suggestions:
- `[47, 52)` 'KIF23' — Gene (score=1.0000)
- `[81, 93)` 'inflammation' — Disease (score=1.0000)
- `[122, 125)` 'OVA' — Gene (score=1.0000)
- `[134, 140)` 'asthma' — Disease (score=1.0000)
- `[141, 145)` 'mice' — Species (score=1.0000)

AIONER suggestions (when available):
- `[141, 145)` 'mice' — Species

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 136. `targetpilot-9045f672150be31c`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / RESULTS`
- Sentence: `s0014`; canonical offsets: `[1574, 1644)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> In addition, p53 signalling pathway was suppressed by KIF23 knockdown.

HunFlair2 suggestions:
- `[13, 16)` 'p53' — Gene (score=1.0000)
- `[54, 59)` 'KIF23' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```

### 137. `targetpilot-568ce27163e9a7fc`

- Paper: `PMID:38569671` (PMID `38569671`, PMCID `None`)
- Split: `test`; section: `abstract / CONCLUSION`
- Sentence: `s0015`; canonical offsets: `[1646, 1765)`
- Sampling: `B` — entity_rich_stable_predictions
- Source text SHA-256: `39058e36f1b50e00fd7a154996f0fef4f82509c3b699d845fefad35742fa49e6`

> Knockdown of KIF23 alleviated the progression of asthma by suppressing pyroptosis and inhibited p53 signalling pathway.

HunFlair2 suggestions:
- `[13, 18)` 'KIF23' — Gene (score=1.0000)
- `[49, 55)` 'asthma' — Disease (score=1.0000)
- `[96, 99)` 'p53' — Gene (score=1.0000)

AIONER suggestions (when available):
- none recorded

Gold annotation to complete by a human reviewer:
```json
{
  "entities": [],
  "annotation_status": "unreviewed",
  "annotation_complete": false
}
```
