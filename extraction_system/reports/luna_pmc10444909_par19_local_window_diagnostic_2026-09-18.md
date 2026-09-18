# PMC10444909 Par19 Local-Window Diagnostic

Date: 2026-09-18
Branch: `extraction_system_v2`
Base commit before these artifacts: `41cb1a8`
Status: **completed; diagnostic-only**

This report tests the exact previously verified Par19 text with the unchanged two-pass GLiNER -> Luna -> deterministic-validation path. No production code, model, label, threshold, merge rule, prompt, reasoning setting, completion budget, relation contract, retry rule, validator, or graph behavior changed. The companion [JSON report](luna_pmc10444909_par19_local_window_diagnostic_2026-09-18.json) contains every normalized entity and relation.

## Exact source and split

Par19 is the Results paragraph `Sec18/Par19`, SHA-256 `0ae2a28512767a31fba398a935041e55dca2bcc743ded4ad8cfc498abf0e2e98`, with 938 characters and 145 whitespace-delimited words. The exact source is preserved in the JSON report; `\u00A0` below denotes the literal U+00A0 figure-space character in the source.

| Sentence | Source span | Window |
|---:|---:|---|
| 1 | [0, 173) | W1 |
| 2 | [174, 240) | W1 |
| 3 | [241, 367) | W1 |
| 4 | [368, 453) | W1 |
| 5 | [454, 680) | W2 |
| 6 | [681, 787) | W2 |
| 7 | [788, 938) | W2 |

The contiguous split is `[0,454)` / `[454,938)`; concatenation reconstructs the 938-character source exactly. Two windows are the minimum satisfying the contract: one full paragraph would retain the 27-entity context.

### W1 — sentences 1-4, [0,454)

SHA-256: `a61bfc11749f8b08f2a4ea6baa847251ad1fdcd69222698ea7eb13bdb29ba54a`
Characters/words: 454 / 70
Exact text:

```text
To investigate the mechanisms by which KNTC1 affects hepatocellular carcinoma, we performed predictions of proteins that interrelate with KNTC1 by using the STRING database. The results showed that CDK1 has interaction with KNTC1 (Fig.\u00A04A). We showed that knockdown of KNTC1 in SK-Hep-1 and Huh7 cells significantly reduced the protein as well as mRNA levels of CDK1. This indicates that KNTC1 positive correlation with the expression of CDK1 (Fig.\u00A04B).\u0020
```

NER returned 12 entities: 9 biological process, 2 cell line, and 1 RNA. The exact normalized entity array is in JSON. Biological-process detections were: `KNTC1`, `hepatocellular carcinoma`, `KNTC1`, `CDK1`, `KNTC1`, `KNTC1`, `CDK1`, `KNTC1`, `CDK1`, with their exact spans/scores preserved in JSON. The output contains no gene-labeled entity.

Luna completed structured extraction in 21.277 s after 0.384 s NER; successful-call token usage was not exposed and is recorded as unavailable. Six normalized relations were returned:

```json
[
  {
    "source": "E1",
    "target": "E2",
    "predicate": "affects",
    "evidence": "KNTC1 affects hepatocellular carcinoma",
    "negated": false,
    "surface_form": "affects",
    "score": null
  },
  {
    "source": "E4",
    "target": "E5",
    "predicate": "interacts with",
    "evidence": "CDK1 has interaction with KNTC1",
    "negated": false,
    "surface_form": "has interaction with",
    "score": null
  },
  {
    "source": "E6",
    "target": "E7",
    "predicate": "is knocked down in",
    "evidence": "knockdown of KNTC1 in SK-Hep-1",
    "negated": false,
    "surface_form": "knockdown of KNTC1 in",
    "score": null
  },
  {
    "source": "E6",
    "target": "E8",
    "predicate": "is knocked down in",
    "evidence": "knockdown of KNTC1 in SK-Hep-1 and Huh7 cells",
    "negated": false,
    "surface_form": "knockdown of KNTC1 in",
    "score": null
  },
  {
    "source": "E6",
    "target": "E10",
    "predicate": "knockdown reduces levels of",
    "evidence": "knockdown of KNTC1 in SK-Hep-1 and Huh7 cells significantly reduced the protein as well as mRNA levels of CDK1",
    "negated": false,
    "surface_form": "significantly reduced the protein as well as mRNA levels of CDK1",
    "score": null
  },
  {
    "source": "E11",
    "target": "E12",
    "predicate": "positively correlates with expression of",
    "evidence": "KNTC1 positive correlation with the expression of CDK1",
    "negated": false,
    "surface_form": "positive correlation with the expression of",
    "score": null
  }
]
```

Structural validation: entity spans 12/12 PASS; endpoints 6/6 PASS; evidence 6/6 PASS; surface forms 6/6 PASS; existing validator 6/6 PASS.

Semantic assessment is bounded to returned claims: CDK1 -> KNTC1 interaction, KNTC1 knockdown -> cell-line context/CDK1 reduction, and KNTC1 -> CDK1 positive-correlation wording have source-faithful direction/intervention language. The process-labeled endpoints and absent separate protein/mRNA relations limit the assessment; validation does not establish semantic type correctness or completeness.

### W2 — sentences 5-7, [454,938)

SHA-256: `5df0394d6d3889b193121470b80b697bc83a9e993b4cfca0cf00c903a6f4e9f2`
Characters/words: 484 / 75
Exact text:

```text
Next, we examined CDK1 expression in the hepatoma cell lines of SK-Hep-1, Huh7, HepG2 and SNU449 and found that both protein levels and mRNA levels of CDK1 were significantly increased compared to normal hepatocytes (Fig.\u00A04C). Meanwhile, we found that KNTC1 was regulating CDK1 levels in HCC through TCGA database analysis (Fig.\u00A04D). These results suggest that KNTC1 may positively regulate the levels of CDK1 in hepatocellular carcinoma cells, and both proteins are highly expressed.
```

NER returned 17 entities: 3 gene, 5 biological process, 5 cell line, 1 RNA, 1 species, and 2 disease. The biological-process detections were `CDK1 expression`, `CDK1`, `KNTC1`, `TCGA database analysis`, and `KNTC1`, with exact spans/scores preserved in JSON.

Luna completed structured extraction in 59.751 s after 0.234 s NER; successful-call token usage was not exposed and is recorded as unavailable. Eight normalized relations were returned:

```json
[
  {
    "source": "E2",
    "target": "E3",
    "predicate": "was examined in",
    "evidence": "we examined CDK1 expression in the hepatoma cell lines",
    "negated": false,
    "surface_form": "examined CDK1 expression in",
    "score": null
  },
  {
    "source": "E2",
    "target": "E4",
    "predicate": "was examined in",
    "evidence": "we examined CDK1 expression in the hepatoma cell lines of SK-Hep-1, Huh7, HepG2 and SNU449",
    "negated": false,
    "surface_form": "examined CDK1 expression in",
    "score": null
  },
  {
    "source": "E2",
    "target": "E5",
    "predicate": "was examined in",
    "evidence": "we examined CDK1 expression in the hepatoma cell lines of SK-Hep-1, Huh7, HepG2 and SNU449",
    "negated": false,
    "surface_form": "examined CDK1 expression in",
    "score": null
  },
  {
    "source": "E2",
    "target": "E6",
    "predicate": "was examined in",
    "evidence": "we examined CDK1 expression in the hepatoma cell lines of SK-Hep-1, Huh7, HepG2 and SNU449",
    "negated": false,
    "surface_form": "examined CDK1 expression in",
    "score": null
  },
  {
    "source": "E2",
    "target": "E7",
    "predicate": "was examined in",
    "evidence": "we examined CDK1 expression in the hepatoma cell lines of SK-Hep-1, Huh7, HepG2 and SNU449",
    "negated": false,
    "surface_form": "examined CDK1 expression in",
    "score": null
  },
  {
    "source": "E9",
    "target": "E10",
    "predicate": "had significantly increased levels compared to",
    "evidence": "both protein levels and mRNA levels of CDK1 were significantly increased compared to normal hepatocytes",
    "negated": false,
    "surface_form": "were significantly increased compared to",
    "score": null
  },
  {
    "source": "E11",
    "target": "E12",
    "predicate": "regulates CDK1 levels",
    "evidence": "KNTC1 was regulating CDK1 levels in HCC",
    "negated": false,
    "surface_form": "was regulating",
    "score": null
  },
  {
    "source": "E15",
    "target": "E16",
    "predicate": "may positively regulate CDK1 levels",
    "evidence": "KNTC1 may positively regulate the levels of CDK1 in hepatocellular carcinoma cells",
    "negated": false,
    "surface_form": "may positively regulate",
    "score": null
  }
]
```

Structural validation: entity spans 17/17 PASS; endpoints 8/8 PASS; evidence 8/8 PASS; surface forms 8/8 PASS; existing validator 8/8 PASS.

Semantic assessment is bounded to returned claims: CDK1-expression examination in the listed cell lines, increased CDK1 levels versus normal hepatocytes, KNTC1 regulation of CDK1 levels, and `may positively regulate` direction/language were preserved. The returned process labels include exact gene/database strings and were not corrected; relation completeness is not claimed.

## Comparison with the prior exact full-Par19 run

| Input | Entities | Biological-process detections | Luna | Relations |
|---|---:|---:|---|---:|
| Full Par19 | 27 | 0 | LengthFinishReasonError at 8,192 reasoning tokens | 0 |
| W1 | 12 | 9 | Structured output completed | 6 |
| W2 | 17 | 5 | Structured output completed | 8 |

The prior full run exposed failure usage `prompt_tokens=2248`, `completion_tokens=8192`, `reasoning_tokens=8192`, `total_tokens=10440`; both successful local calls exposed no provider usage metadata. No local retry or provider retry was observed. The harness retained its repair budget of 2 while provider retries remained configured at 0.

## Interpretation and conclusion

Luna completed for both exact local windows, so the prior Par19 length failure did not recur after the entity context was reduced to 12 and 17 entities. Returned relations preserve the direction and intervention/modal language of the emitted KNTC1/CDK1 interaction, knockdown/reduction, expression, and regulation claims.

The full-paragraph zero-process result did not persist: smaller windows returned 9 and 5 process detections. That is an observed GLiNER label change, not proof of semantically correct process recognition; W1 in particular contains process labels on gene/disease strings. Because the full run had no structured relation output, this experiment cannot establish whether the absence of process nodes caused that failure. It establishes only that the unchanged pipeline can complete and return grounded, validator-accepted local relations for this exact two-window split. No production window policy is proposed or implemented.
