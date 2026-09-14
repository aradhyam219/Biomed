# V0-B BioRED Gold-Entity RE Baseline — Active State

Status: blocked pending a methodological decision

## Goal

Measure the existing zero-shot `jackboyla/glirel-large-v0` relation stage on the
original BioRED development split using gold entity mentions and normalized concept
IDs, without allowing GLiNER errors into the result.

The implementation is ready and partially exercised, but no full-development metric
is valid yet. One official development document exceeds GLiREL's hard token limit,
and the governing contract forbids silently truncating or excluding it.

## Ground situation

- Branch: `extraction_system`
- Latest pushed implementation commit: `56fd7a90fe3c2ff146f21875e5e7f3a1cd098b3c`
  (`Add BioRED gold-entity RE evaluator`)
- Remote: `origin/extraction_system`
- Runtime used: project-local `uv` environment, Python 3.11, CPU-only PyTorch
  (`torch.cuda.is_available() == False` during V0-B work).
- Official local dataset: `.cache/BIORED/BioRED/Dev.BioC.JSON`
- Dataset SHA-256:
  `d5ab4d05673ac46fb5e3b2904d2820462dec2c4c50dfcdd8678635ff1b8ce1f5`
- Generated corpus, raw scores, and summaries are gitignored and are not on GitHub.
- The unrelated untracked parent file `C:\Projects\Biomed\.gitignore` remains
  untouched and must not be included in extraction-system commits.

## Completed

- Added an explicit-path loader for the official original `Dev.BioC.JSON`; train and
  test split requests are rejected for V0-B.
- Reconstructs title plus abstract using BioC passage offsets and validates every
  half-open annotation offset against the exact source text.
- Preserves each gold mention's text, BioRED type, offsets, mention ID, and every
  normalized concept ID.
- Runs GLiREL through the existing supplied-entity relation path. A guard model raises
  if GLiNER is accidentally invoked.
- Uses the exact eight canonical labels through an explicit prompt mapping:
  `Association`, `Positive_Correlation`, `Negative_Correlation`, `Bind`,
  `Conversion`, `Drug_Interaction`, `Comparison`, and `Cotreatment`.
- Enforces BioRED's eight eligible unordered concept-pair families.
- Expands comma-delimited multi-ID mentions by Cartesian product without consulting
  gold relations.
- Converts directed mention predictions into non-directional document/concept pairs,
  then uses maximum mention-level score across repeats, expansions, and directions.
- Retains at most one semantic label per concept pair after aggregation.
- Uses GLiREL `top_k=1` and relation inference threshold `0.0`, preserving reusable
  scores for threshold calibration without rerunning the model.
- Selects the development threshold that maximizes typed micro F1; exact ties prefer
  higher precision and then the higher threshold.
- Computes pair-only TP/FP/FN/P/R/F1, typed micro metrics, per-label metrics, compact
  threshold diagnostics, and representative errors.
- Saves cache progress after each document so smoke, subset, and eventual full runs
  reuse the same inference.
- Added a fail-fast sequence preflight so GLiREL cannot silently produce an invalid
  truncated result.
- Added the `biored-evaluate` command and methodology/documentation updates.

## Task-local findings and decisions

### Official dev corpus facts observed locally

- 100 documents
- 3,533 gold mentions
- 1,162 unique typed concept-level gold relations
- Entity mentions:
  - 1,087 GeneOrGeneProduct
  - 982 DiseaseOrPhenotypicFeature
  - 822 ChemicalEntity
  - 370 OrganismTaxon
  - 250 SequenceVariant
  - 22 CellLine
- Gold relation support:
  - Association: 560
  - Positive_Correlation: 352
  - Negative_Correlation: 216
  - Bind: 19
  - Cotreatment: 10
  - Comparison: 5
  - Conversion: 0
  - Drug_Interaction: 0

Absent Conversion/Drug_Interaction support means their dev recall and F1 can be
undefined; the scorer serializes undefined metrics as JSON `null` and prints `N/A`.

### Candidate constraints

Only the eight published pair families are enforced. A stricter label/type matrix
was deliberately rejected because the official development truth contradicts the
guideline examples in three cases:

- one chemical-chemical `Bind` gold relation;
- two chemical-gene `Cotreatment` gold relations.

Excluding those cases would make valid gold relations impossible to predict. This is
documented in `docs/EVALUATION.md`.

### Exact gold span handoff

The original V0-A tokenizer rejected 200 eligible dev mentions because BioRED can
annotate a substring of GLiREL's compound token. Splitting hyphens/underscores alone
still left six nested prefixes, including `H3` in `H3K36me3` and `AR` in `ARKO`.

The production relation handoff now splits GLiREL input tokens at exact supplied
entity start/end boundaries. It does not widen, remap, or discard gold spans. Inputs
that already aligned under V0-A retain the same tokenization. This was the only
production-path change needed for V0-B.

### Cache state

- Cache: `.cache/v0b_raw.json`
- Valid cached documents: 74
- Cache identity records dataset SHA, split, checkpoint, prompt mapping, and top-k.
- The over-limit document's truncated prediction was removed from the cache.
- Cache is useful only if the same dataset, checkpoint, prompts, tokenization, and
  aggregation policy are retained.
- Talia reviewing from GitHub will not have this cache; it exists only in the current
  local workspace.

## Verification already completed

- `uv run python -m unittest discover -s tests -v`: 19 tests passed.
- Tests cover BioC parsing, exact schema mapping, multi-ID expansion,
  non-directional canonicalization, repeated-mention/opposite-direction collapse,
  candidate families, pair-vs-typed scoring, threshold selection, supplied-entity
  compound-span tokenization, and existing V0-A behavior.
- All 100 official dev documents parsed successfully.
- Every dev gold relation endpoint resolved to supplied concept IDs.
- Every gold relation fits the selected eight-family candidate policy.
- All exact gold mentions can be transformed to GLiREL spans after entity-boundary
  token splitting; no duplicate supplied spans were found.
- Python compilation passed.
- `uv lock --check` passed; no new dependency was introduced.
- CLI help and machine-readable serialization passed.
- `git diff --check` passed before commit.
- One-document real GLiREL smoke test passed without loading GLiNER.
- Five-document cached subset passed and reused the first document rather than
  inferring it again.
- The full command now exits with code 2 before model loading when it detects the
  oversized document.

## Real-model evidence so far

These numbers are diagnostics, not the V0-B baseline. Threshold selection and metric
calculation are performed on the same tiny subset, so neither estimate is unbiased.

### One-document smoke test

- Document: PMID `14510914`
- Gold relations: 12
- Selected threshold: `0.11492930`
- Pair-only: TP 2, FP 2, FN 10; precision 0.5000, recall 0.1667, F1 0.2500
- Typed: TP 2, FP 2, FN 10; precision 0.5000, recall 0.1667, F1 0.2500

Purpose: verify end-to-end mechanics with the real checkpoint. Do not interpret this
single-document number as model quality.

### Five-document subset

The subset includes the smoke document; it did not rerun that document.

- Documents: 5
- Gold mentions: 139 total; 119 relation-eligible mentions supplied
- Gold relations: 33
- Raw GLiREL mention predictions: 3,270
- Concept-label scores after aggregation: 135
- Concept pairs before threshold: 117
- Predictions after threshold: 71
- Selected threshold: `0.029507499188184738`
- Pair-only: TP 27, FP 44, FN 6
  - precision 0.3803
  - recall 0.8182
  - F1 0.5192
- Typed micro: TP 17, FP 54, FN 16
  - precision 0.2394
  - recall 0.5152
  - F1 0.3269

Per-label subset evidence:

| Label | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Association | 18 | 0.3148 | 0.9444 | 0.4722 |
| Positive_Correlation | 10 | N/A | 0.0000 | N/A |
| Negative_Correlation | 5 | 0.0000 | 0.0000 | 0.0000 |
| Bind | 0 | N/A | N/A | N/A |
| Conversion | 0 | N/A | N/A | N/A |
| Drug_Interaction | 0 | 0.0000 | N/A | N/A |
| Comparison | 0 | N/A | N/A | N/A |
| Cotreatment | 0 | N/A | N/A | N/A |

Compact threshold behavior:

| Threshold | Predictions | Typed precision | Typed recall | Typed F1 |
|---:|---:|---:|---:|---:|
| 0.0000 | 117 | 0.1538 | 0.5455 | 0.2400 |
| 0.0295 | 71 | 0.2394 | 0.5152 | 0.3269 |
| 0.1000 | 32 | 0.3125 | 0.3030 | 0.3077 |
| 0.3000 | 9 | 0.6667 | 0.1818 | 0.2857 |
| 0.5000 | 0 | N/A | 0.0000 | N/A |

The subset suggests GLiREL finds many correct concept pairs but produces too many
false pairs and frequently assigns the wrong semantic type. It strongly favors
`Association`; representative missed Positive/Negative correlations were instead
predicted as `Association` at weak scores around 0.06-0.09. Scores do not show a
clean operating separation: the F1-optimal subset threshold is only about 0.03, and
raising it rapidly trades away recall.

Representative examples from the subset:

- True positive: PMID `16152606`, concepts `4683` / `D008228`, Association,
  score `0.3881`.
- False positive: PMID `16152606`, concepts `4683` / `D049932`, Association,
  score `0.3704`.
- Wrong-type false negative: PMID `14510914`, concepts `6528` / `C564766`, gold
  Negative_Correlation, predicted Association at `0.0901`.
- Wrong-type false negative: PMID `14510914`, concepts `C564766` /
  `p|DEL|439_443|`, gold Positive_Correlation, predicted Association at `0.0640`.

This is early evidence only. It does not yet justify fine-tuning, prompt/schema
refinement, or replacing GLiREL because the full development baseline is blocked.

## Full-run blocker and incident details

The full run started only after parser/scorer tests, the real smoke test, and the
five-document subset succeeded. It reused the same cache.

At PMID `19880293`, GLiREL emitted:

```text
Token length 554 is longer than max length 512. Truncating.
```

Why this matters:

- BioRED relations are document-level.
- Truncation can remove gold mentions and evidence while the scorer still treats the
  document as completely evaluated.
- The task contract explicitly prohibits silent truncation or exclusion.
- The initial static check counted 550 ordinary regex tokens; exact gold-boundary
  splitting adds four tokens, producing the actual GLiREL input length of 554.

Response taken:

1. Stopped the full run instead of publishing its metrics.
2. Removed PMID `19880293` from the raw-score cache.
3. Kept 74 other completed document entries whose lengths are within the limit.
4. Added a preflight using the exact supplied-entity tokenization.
5. Confirmed the full command now exits before loading the model and reports the
   offending PMID and length.
6. Did not generate a full-development summary.
7. Did not silently report the 74-document or a 99-document score as the baseline.

## Decision Talia needs to make

The current contract cannot simultaneously require the existing GLiREL checkpoint,
complete full-document scoring over all 100 dev documents, one inference pass per
document, and no truncation/chunking decision. Talia should recommend an explicit
methodological amendment before more inference.

### Option A — Report a 99-document complete-fit baseline

- Smallest code and compute change.
- Keep PMID `19880293` explicitly unevaluated and report coverage as 99/100.
- Reuse the 74 cached valid documents and infer only the remaining fitting documents.
- Does not satisfy the current full-split acceptance criterion.
- May introduce small selection bias and cannot be described as the official full
  development result.

### Option B — Authorize deterministic windowing for only the oversized document

- Preserves nominal 100-document coverage and the existing checkpoint.
- Requires a defined window size, overlap, mention inclusion rule, concept-score
  aggregation rule, and treatment of concept pairs whose mentions never co-occur in
  one window.
- A document-level relation can depend on mentions/evidence across windows, so naive
  chunking is not semantically equivalent to full-document inference.
- It also changes “one inference pass per document” into multiple model calls for the
  exceptional document unless the contract defines those calls as one cached
  document-level inference job.
- This is the main option if keeping both the checkpoint and all 100 documents is
  more important than preserving the original inference unit.

### Option C — Use a relation model/checkpoint with a sufficient context limit

- Preserves complete documents and avoids chunk aggregation ambiguity.
- Changes the primary model under evaluation, so it no longer answers exactly how
  the V0-A GLiREL checkpoint performs.
- Existing 74 cached scores cannot be reused for a different checkpoint; the whole
  dev inference must restart.
- Model selection could become a new benchmarking task and must not silently expand
  V0-B into a sweep.

### Option D — Accept explicit truncation

- Cheapest computationally.
- Methodologically invalid under the current contract because one document is scored
  as if complete after model-side truncation.
- Not recommended unless the contract is deliberately weakened and the result is
  prominently labeled.

## Questions for Talia's brainstorming

1. Is the required scientific claim “performance of this exact V0-A checkpoint on
   all official dev documents,” or is a clearly labeled 99/100 complete-fit estimate
   acceptable?
2. If all 100 are mandatory, what windowing rule preserves document-level relation
   semantics well enough to defend the result?
3. How should pairs with no co-window mention evidence be treated—automatic false
   negatives, special handling, or an explicit coverage metric?
4. Does “one inference pass per document” permit several cached model windows that
   are aggregated once, or must it mean exactly one model call?
5. If changing the checkpoint is preferred, should that replace V0-B's primary
   question or become a separate follow-up comparison?
6. Should the 74 cached complete-document predictions be used for interim error
   analysis, or should interpretation wait until the protocol is amended and the
   final calibrated threshold is available?

## Outstanding

- Obtain Talia/user approval for one explicit oversized-document policy.
- Amend `docs/EVALUATION.md` and evaluator behavior to that policy.
- Complete only the missing inference justified by the chosen policy.
- Calibrate the threshold once over the final authorized evaluation set.
- Produce the contract-format full report and evidence-based recommendation.
- Do not start GLiREL fine-tuning, GLiNER evaluation, end-to-end BioRED evaluation,
  or model benchmarking until the V0-B methodology is resolved.

## Next action

Talia should review the blocker and recommend one of Options A-C (Option D is not
recommended), including exact scoring/coverage semantics. Do not run more model
inference until that decision is recorded. After approval, implement only the
smallest required protocol change and reuse the 74 valid cached documents whenever
the selected checkpoint and tokenization remain unchanged.

## Material files

- `src/biomedical_extractor/biored.py`
- `src/biomedical_extractor/biored_cli.py`
- `src/biomedical_extractor/pipeline.py`
- `tests/test_biored.py`
- `tests/test_pipeline.py`
- `docs/EVALUATION.md`
- `.cache/v0b_raw.json` — local ignored cache, 74 valid documents
- `.cache/v0b_smoke_summary.json` — local ignored smoke result
- `.cache/v0b_subset_summary.json` — local ignored five-document result

## Authoritative references

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/product/CURRENT_SPEC.md`
- `docs/EVALUATION.md`
- `README.md`
- Original task contract supplied as
  `V0-B_BioRED_Gold_Entity_RE_Baseline_Contract.md` outside the repository
- NCBI BioRED: <https://github.com/ncbi/BioRED>
- Original BioRED paper: <https://pmc.ncbi.nlm.nih.gov/articles/PMC9487702/>
- BioRED/BioCreative VIII corpus description:
  <https://academic.oup.com/database/article/doi/10.1093/database/baae071/7731176>
- GLiREL repository: <https://github.com/jackboyla/GLiREL>
- GLiREL paper: <https://aclanthology.org/2025.naacl-long.418/>

## Fresh-session continuation prompt

```text
Read the applicable AGENTS.md instructions.
Continue C:\Projects\Biomed\extraction_system\V0-B_HANDOFF.md.
Load linked authoritative sources only as needed.
Proceed with the stated next action after the oversized-document policy is approved.
```
