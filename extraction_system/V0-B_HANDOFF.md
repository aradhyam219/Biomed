# V0-B BioRED Gold-Entity RE Baseline — Completed State

Status: implementation and authorized complete-fit baseline complete

## Result

```text
BioRED development complete-fit baseline
Evaluated: 99 / 100 documents
Excluded: PMID 19880293
Exclusion reason: exceeds current GLiREL checkpoint input limit
Document coverage: 99.00%
Total official-dev gold relations: 1162
Gold relations in evaluated documents: 1156
Gold-relation coverage: 99.48%
Gold relations in excluded document: 6
```

This is not a full or official BioRED development score. PMID `19880293` remains
unevaluated because its exact supplied-entity input is 554 tokens and the fixed
`jackboyla/glirel-large-v0` checkpoint limit is 512. It was not truncated, windowed,
chunked, inferred, or counted as false negatives. The exclusion was determined by
sequence preflight before model loading and independently of prediction outcome.

The threshold calibrated once on the authorized 99 documents is `0.14250895`.

- Pair-only: precision `0.2212`, recall `0.4775`, F1 `0.3023`
  (`TP=552`, `FP=1944`, `FN=604`).
- Typed micro: precision `0.1322`, recall `0.2855`, F1 `0.1807`
  (`TP=330`, `FP=2166`, `FN=826`).

## Completed implementation

- V0-B is fixed to `DEFAULT_RELATION_MODEL` / `jackboyla/glirel-large-v0`; the
  misleading evaluator `--model` option was removed.
- Full-run preflight permits only the authorized sequence-length exclusion and fails
  closed for any unexpected over-limit PMID.
- Reports include document coverage, official and evaluated gold counts,
  gold-relation coverage, and the excluded document's gold count.
- Threshold calibration receives only the 99 complete-fit documents.
- The 74 valid cached predictions were reused; only 25 remaining complete-fit
  documents were inferred. The final cache contains 99 documents and does not
  contain PMID `19880293`.
- `pipeline.py`, `cli.py`, and `demo.py` now meet the repository documentation
  standard without behavior changes. The character-span to inclusive GLiREL input
  span to half-open GLiREL output span to entity-ID flow is documented explicitly.
- `docs/EVALUATION.md` is the authoritative current methodology and result.

## Verification

- Focused BioRED evaluator and production pipeline tests: 22 passed.
- Final real-model run exited successfully using the project-local CPU environment.
- Raw predictions remain ignored at `.cache/v0b_raw.json`.
- The machine-readable final report is tracked at
  `reports/biored_v0b_complete_fit.json` for Talia and other reviewers.
- Cache after completion: 99 documents; excluded PMID absent.

## Scope held

No GLiREL fine-tuning, GLiNER evaluation, end-to-end BioRED evaluation, windowing,
truncation, alternate-model benchmarking, or checkpoint change was performed. The
unrelated parent `C:\Projects\Biomed\.gitignore` remains untouched and untracked.

## Next action

V0-B is complete. Review and commit the scoped `extraction_system` changes when
requested; do not include the unrelated parent `.gitignore` or ignored artifacts.
