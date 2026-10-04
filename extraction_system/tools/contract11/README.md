# Preserved Contract 11 benchmarks

These are experimental tools, separate from ordinary production RE. Production
continues to use GPT-5.6 Luna through its existing LangChain integration.

`run.py` reuses the preserved 11S-R lifecycle and 11U orchestration. It retains
background ID persistence, polling, bounded transport retries, cancellation,
strict SDK schema conversion, Contract 10 validation, repairs, tier checks,
usage/cost accounting, and randomized review packets. The source/entity fixture
at `reports/luna_56_vs_6_real_probe_11qr/passage_001/manifest.json` is tracked;
NER and provider caches are not required for this experiment.

From `extraction_system`, prepare a new run without network access:

```powershell
.venv/Scripts/python.exe tools/contract11/run.py --candidate 61-medium-standard --output reports/new_sol_probe --prepare
```

For a paid run, use `--run` instead of `--prepare` with a fresh output name and
network-capable execution. Credentials come from the existing environment or
`.env` and are not logged. `--candidate 11u` reproduces the original three
configurations in order; `61-xhigh-standard` runs the supplemental configuration.
The semantic hash and transport hash are checked before inference. The reference
production tree must still match the protected Contract 10 state. Historical
scripts retain their original baseline gates and are archival entry points;
use this launcher for a new run after report-only commits advance HEAD.

Run offline lifecycle/accounting checks:

```powershell
.venv/Scripts/python.exe reports/luna_gpt6_background_probe_11s/scripts/check_adapter.py
.venv/Scripts/python.exe reports/model_selection_11u/scripts/check_trial.py
.venv/Scripts/python.exe tools/contract11/check_preservation.py
```

## Audit records

- Original three-candidate experiment: `reports/model_selection_11u/`.
  Original frozen review: `review/blind_packet.json` and `review/review_freeze.json`.
  The user-created `unblinding package/` retains costs, operations, and the key.
  The byte-identical convenience ZIP is local-only; its JSON contents are tracked.
- Supplemental D: `reports/gpt61_sol_xhigh_supplemental/`. It ran outside the
  original 11U trial, with model identity known before scientific comparison.
- A/B/C/D comparison: `reports/model_selection_11u_with_candidate_d/review/`.
  This is a separate supplemental packet; the original A/B/C freeze is unchanged.
- Scientific decision supplied by Talia via the preservation contract:
  `reports/contract11_preservation_11p/scientific_decision.json`. Candidate C is
  GPT-6.1 Sol medium Standard. The full external frozen scientific review body
  was not supplied in the checkout; the blank original template remains blank.
- Earlier aborted experiments and connectivity/timeout records remain historical
  diagnostics, not successful scientific-quality comparisons.

The preservation manifest records exact source artifact bytes. Git attributes
disable newline conversion for these report trees so freeze hashes survive
commits and checkouts. No production promotion is authorized by preservation.
