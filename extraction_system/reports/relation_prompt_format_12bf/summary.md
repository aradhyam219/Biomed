# Contract 12B-F — formatting-only salience experiment

**FORMATTING EXPERIMENT FAILED — PRESERVE 12A CONTROL PROMPT**

SFPQ effects population improved, but the variant lost important Cbl, PTEN and
EZH2 findings and weakened 11U rich fields. It is not eligible for promotion.
Stop prompt experiments. No production prompt, model, reasoning, execution
default, schema, validator, entity packet, graph conversion or viewer changed.
Product and architecture documents remain current because this is report-local
experimental evidence only. No promotion was performed.

## Experimental integrity

- Clean primary `extraction_system_v2` checkout and fetched remote both began at
  `78b656011c8a6bf0231c57d121bc7ea4fd465b5a`. No worktree, reset or history rewrite.
- Control comes from `RELATION_EXTRACTION_SYSTEM_PROMPT` at that exact Git SHA,
  extracted from its AST and compared with the live constant and preserved control.
- One variant adds only six XML tag pairs, sparse bold emphasis and whitespace.
  No natural-language wording, order, substantive punctuation or request labels
  changed. No 12B/12B-R amendment was used.
- Deterministic full-sequence equivalence **passed before the first live call**:
  strip only the six approved tags and inserted `**`, normalize whitespace, then
  compare the entire text including substantive punctuation. See
  `prompt_equivalence.json` and `prompt_format_diff.txt`.
- Control SHA-256:
  `13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f`.
- Formatted SHA-256:
  `fc25eef5257d23005a9db8488f7841068690d15d7f17e9c13aa6ecb1bb595e36`.
- Prompt and hashes were frozen before execution and checked before every case.
  Exactly five completed scientific generations; zero adaptive edits, control
  reruns, output repairs, generation resubmissions or operational retries.
- Four 12A Sol-medium paper controls plus original 11U Candidate C control are
  reused. Their original outputs, source/entity/request hashes and exact graph
  replay were verified offline. All inputs are identical to 12B and 12B-R.
- Existing report-local runner is reused with its explicit prompt override.
  `prompt_refined.txt` is a byte-identical harness alias for `prompt_formatted.txt`;
  `graphs/refined/` and `cases/*/refined.json` retain that runner's naming convention.
- Every completion observed `gpt-6.1-sol`, medium, Standard/default,
  background Responses. The existing 128,000-token ceiling, 900-second bound,
  three-second polling and two-repair budget were unchanged; SDK retries are zero.

## Scientific targets

| Target | Result |
|---|---|
| JAK2 overexpression reversal recovered? | **No** |
| STAT4 overexpression reversal recovered? | **No** |
| Runx3 overexpression reversal retained? | **No**, original control finding lost; other Runx3 findings remain |
| Increased PTEN expression after serum deprivation in H9c2 recovered? | **No**, despite valid supplied H9c2/PTEN endpoints |
| Artificial PTEN knockdown self-edge? | None |
| DM-rat/HG-HUVEC expression setting retained? | Rat setting remains for JAK2/Runx3/STAT4; HG-HUVEC setting absent and reduced Cbl expression lost |
| Unsupported glucose/context causal additions? | Zero known glucose-to-gene causal edges or unsupported new rich values |
| 11U original findings/topology? | All ten original endpoint pairs and directions retained; same graph adjacency, no cohort-to-gene substitution or reversal |
| 11U AST/ALT? | ALT comparability and elevated AST retained; ratio findings absent as in Candidate C control |
| SFPQ cognition/memory lost? | No; retained and rich effects improved. AAV hippocampal setup relation lost |
| EZH2 poor prognosis lost? | No; retained as correlation, not causation |
| EZH2 maintenance/other findings lost? | Pathway maintenance effects emptied; final maintenance effect populated; tumor-initiating capacity lost and conditional pathway topology changed |

The supported glucose-to-DM in-vitro model edge remains distinct from the
forbidden glucose-to-gene-expression causal inflation. The Cbl predicate
`alleviates` drops `appears` although its assertion retains the hedge; this match
is excluded from clean matched-finding richness. STAT4-to-Runx3 expression remains
but its explicit histone trimethylation mechanism is lost and excluded likewise.

EZH2's p21 requirement is redirected from p21-to-EZH2 plus conditional
EZH2-to-Wnt/beta-catenin edges into p21-to-Wnt/beta-catenin edges. Assertions retain
EZH2 dependence, but graph topology changes; these are not credited as equivalent
coverage. In PTEN, PI3K-inhibitor reversal and PI3K/AKT mechanism findings disappear.
In 11U, effects are emptied on hyperglycemia reduction and liver damage, and AST
and Cystatin C lose their plasma/10-week qualifiers. Narrowed evidence remains
adequate for the emitted core claims; absent qualifiers are not imported.

## Rich fields

Population counts describe records, not quality scores. Every populated new or
changed value has a direct evidence/edge-specific semantic judgment in
`rich_field_review.json`. No known unsupported rich additions were identified.

| Set | Intervention control → formatted | Effects control → formatted | Context control → formatted |
|---|---:|---:|---:|
| 56 valid matched findings | 20 → 20 | 11 → 17 | 26 → 26 |
| All emitted records | 28 → 20 | 14 → 17 | 38 → 26 |

Aggregate matched counts hide losses: SFPQ effects improve **2 → 9**, while EZH2
pathway maintenance effects disappear and 11U effects fall **2 → 0**. EZH2's
other effects additions offset its maintenance losses numerically. Lost findings
fall outside matched pairs and remain explicit rejection evidence. Exact pairs,
exclusions, full relation judgments and losses are in `scientific_review.json`
and each case's `comparison.json`.

| Case | Relations control → formatted | Graph edges control → formatted |
|---|---:|---:|
| SFPQ / PMC11824863 | 13 → 14 | 13 → 14 |
| Cbl / PMC8605525 | 26 → 17 | 25 → 16 |
| EZH2 / PMID27172794 | 20 → 17 | 18 → 17 |
| PTEN / PMID33652126 | 7 → 4 | 6 → 4 |
| Original 11U passage_001 | 10 → 10 | 10 → 10 |

## Operational results

All five response statuses are **completed/success**, observed tier **default**,
with **zero repairs, retries, resubmissions or polling failures** per case.
Reasoning tokens are included in output tokens, not additional to them.

| Case | Wall latency (s) | Input tokens | Output tokens | Reasoning tokens | Polls |
|---|---:|---:|---:|---:|---:|
| SFPQ | 62.42 | 3,646 | 3,026 | 682 | 17 |
| Cbl | 46.81 | 5,184 | 2,372 | 765 | 13 |
| EZH2 | 52.22 | 3,651 | 2,554 | 689 | 15 |
| PTEN | 31.81 | 3,206 | 1,167 | 757 | 9 |
| 11U | 55.33 | 5,298 | 2,241 | 868 | 16 |

Full safe generation diagnostics, response IDs and attempt-event histories are
preserved in `telemetry.json` and `cases/*/attempt.json`.

## Validation, reproducibility and limits

- **54 focused Python tests passed:** 25 background lifecycle/configuration and
  prompt override, 16 relation parsing/validation, 13 deterministic graph tests.
- **13 viewer tests passed.** All ten control/formatted graphs pass unchanged
  viewer adapter and Cytoscape conversion, preserving direction, evidence,
  aliases, mentions, rich fields, hidden/revealed nodes and JSON immutability.
- Every output exactly replays through the unchanged graph pipeline. Nodes are
  identical. Endpoint IDs and contiguous verbatim evidence are mechanically
  valid; rich-evidence projection is exact. Zero normalized exact duplicate
  relations/graph identities/evidence records; no semantic duplicate explosion
  identified. Duplicate counts do not expose unknown raw records removed by
  unchanged validation.
- Production code/viewer, defaults and every historical artifact are hash
  guarded. `frozen_set_manifest.json` records initial frozen files and provenance;
  final artifact hashes preserve the completed review package. Runner refuses
  duplicate live submissions. Offline verification/review is reproducible.
- Review is by the primary agent, not independent adjudication or accepted gold.
  One completion per case cannot isolate sampling variability. No browser
  interaction rerun or full Python suite was needed for this report-only change.

Normal scoped commit/push to `origin/extraction_system_v2` is authorized. Final
delivered SHA, remote verification and clean-checkout result are recorded in the
completion response; embedding the containing commit's own SHA is circular.
