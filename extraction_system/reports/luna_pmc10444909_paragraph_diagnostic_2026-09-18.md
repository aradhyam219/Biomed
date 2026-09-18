# PMC10444909 Paragraph Diagnostic

Date: 2026-09-18
Branch: `extraction_system_v2`
Base before report artifacts: `85338e663d1785cf4a031dea29ee1931e5cf3bdd`

## Scope

The exact previously evaluated Results paragraphs `Par19`, `Par20`, and
`Par21` were processed independently through the unchanged production path:

```
paragraph -> GLiNER core + biological-process passes -> merge -> Luna -> deterministic validation
```

The companion [JSON report](luna_pmc10444909_paragraph_diagnostic_2026-09-18.json)
contains the exact normalized entity and relation arrays, including scores,
spans, predicates, verbatim evidence, surface forms, and validation records.
No production code, model, prompt, configuration, retry rule, or validation rule
was changed.

## Source identity

| Paragraph | Section | Characters | Words | Exact-input SHA-256 |
|---|---:|---:|---:|---|
| Par19 | Sec18 | 938 | 145 | `0ae2a28512767a31fba398a935041e55dca2bcc743ded4ad8cfc498abf0e2e98` |
| Par20 | Sec19 | 652 | 103 | `538d8855f35d0a026d08248968dbdf7bac9a05ee77db33a93d78970ded893296` |
| Par21 | Sec20 | 527 | 78 | `b8d8690906dcfb9cb33f3a45cb2b239afae223e2c5b58737d6d6edb6fea0c028` |

These are the three LF-separated paragraphs from the prior combined passage,
whose verified SHA-256 was
`aacd57ae2f253a69d01ebfe4269e4c1b3ca8cb21c8d7d585bad370767b2cfca5`.

## Compact comparison

| Input | Entities | Biological-process entities | Luna | Relations | Issue classification |
|---|---:|---:|---|---:|---|
| Previous combined 3-paragraph input | 58 | 0 | Length failure before structured output | 0 | Entity-stage + runtime/provider limitation |
| Par19 | 27 | 0 | Length failure; 8,192 reasoning tokens consumed | 0 | Entity-stage + runtime/provider limitation |
| Par20 | 20 | 3 | Structured extraction completed | 15 | No material issue observed |
| Par21 | 19 | 5 | Structured extraction completed | 11 | No material issue observed |

For the successful runs, entity spans resolved to the exact input text, relation
endpoints referenced supplied entities, relation evidence and supplied surface
forms were verbatim source substrings, and the existing deterministic validator
accepted all returned relations: Par20 `15/15`, Par21 `11/11`.

## Paragraph findings

### Par19 — entity-stage and runtime/provider limitations

- GLiNER returned 27 entities: 14 gene, 3 disease, 7 cell line, 2 RNA, and
  1 species.
- No `biological process` entity was returned.
- Luna received a provider response but raised
  `openai.LengthFinishReasonError` after consuming the configured 8,192
  completion tokens in reasoning. Usage exposed by the failure was
  `prompt_tokens=2248`, `completion_tokens=8192`,
  `reasoning_tokens=8192`, and `total_tokens=10440`.
- No structured relation output existed, so relation semantics, intervention
  language, and validator acceptance of a returned relation set were not
  assessable. Entity source-span validation passed `27/27`.

### Par20 — successful intervention and rescue extraction

Biological-process detections were:

```
E12 cell viability [324,338)  score=0.8416236639022827
E13 proliferative capacity [350,372)  score=0.8578466773033142
E16 cell cycle arrest [469,486)  score=0.8970630764961243
```

Luna returned 15 validated relations. The exact relation array is in the JSON
companion; its coverage is:

- KNTC1 knockdown and CDK1 overexpression in SK-Hep-1/Huh7:
  `E3->E5`, `E3->E6`, `E4->E5`, `E4->E6`.
- CDK1 upregulation of KNTC1, CDK1 protein, and CDK1 mRNA:
  `E7->E8`, `E7->E9`, `E7->E10`.
- Rescue and reversal of KNTC1-knockdown effects:
  `E11->E12`, `E11->E13`, `E15->E16`, `E18->E19`.
- Knockdown-caused effects:
  `E14->E12`, `E14->E13`, `E17->E16`, `E20->E19`.

The predicates and verbatim evidence preserve the knockdown, overexpression,
and rescue/reversal language. No material issue was observed.

### Par21 — successful migration and invasion extraction

Biological-process detections were:

```
E2  CDK1 overexpression   [38,57)   score=0.5162081122398376
E3  cell migration capacity [96,119) score=0.6121155619621277
E8  invasive ability      [245,261) score=0.645431637763977
E12 invasive ability      [324,340) score=0.6441107988357544
E17 metastasis            [465,475) score=0.5536370873451233
```

Luna returned 11 validated relations. The exact relation array is in the JSON
companion; its usable endpoint coverage is:

- Migration: `E2->E3` (increases) and `E4->E3`, `E5->E3` (cell-line
  membership/has relations).
- Invasion: `E7->E8` (KNTC1 inhibits), `E11->E12` (CDK1 increases), and
  cell-line endpoints `E9/E10->E8`, `E13/E14->E12`.
- Metastasis: `E17->E18` and `E19->E17`.

The `with or without KNTC1 inhibition` wording is retained in verbatim
evidence. No additional conditional relation is inferred here. No material
issue was observed; all 11 relations passed endpoint, evidence, surface-form,
and validator checks.

## Run accounting and limits

There were three exact paragraph provider calls, one per requested paragraph.
An initial local selector mistake invoked the already-combined passage instead
of Par19; it reproduced the prior length failure, was not counted as a
paragraph result, and was not retried. The exact Par19 call then failed once;
Par20 and Par21 each completed once. The current runtime did not expose
successful-call token usage or a provider-attempt counter. Approximate complete
command wall-clock observations were Par19 104.3 s, Par20 108.1 s, and Par21
70.0 s, including local GLiNER initialization/cache activity.

## Conclusion

Paragraph-scale processing materially improved the observed result for Par20
and Par21: biological-process entities reappeared, Luna completed, and
contract-valid relations were returned for rescue, migration, and invasion
claims. The improvement was not uniform because Par19 still hit the same
Luna reasoning-length failure and still had no biological-process detections.
This experiment supports the diagnostic comparison only; it does not support
any windowing, aggregation, coreference, prompt, budget, or architecture
change.

No secrets were printed or included. No product or architecture documentation
changed.
