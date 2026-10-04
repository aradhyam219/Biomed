# Contract 12B-R review package

Read `summary.md`, then `scientific_review.json`, `evidence_locality_review.json`
and each case's `comparison.json`. Mechanical checks passed; scientific prompt
refinement failed. Preserve 12A control behavior; no production promotion.

Folders use the preserved harness conventions: four cases under `papers/`, one
under `contract11u_passage/`, and ten graphs under `graphs/`. Each case contains
the exact input, reused control, saved failed-12B output, one new output and its
attempt events. Nothing in 12A, 12B or 11U was overwritten.

Offline reproduction from the repository directory:

```powershell
.venv\Scripts\python.exe reports/relation_prompt_refinement_12br/scripts/experiment.py verify
$task12brGraphs = Get-ChildItem reports/relation_prompt_refinement_12br/graphs -Recurse -Filter '*.json' | Select-Object -ExpandProperty FullName
node reports/relation_prompt_refinement_12br/scripts/check_viewer.mjs @task12brGraphs
.venv\Scripts\python.exe reports/relation_prompt_refinement_12br/scripts/build_review.py
.venv\Scripts\python.exe reports/relation_prompt_refinement_12br/scripts/inspect_relations.py pmcid_pmc8605525 control failed_12b refined
```

These commands make no provider calls. The review builder checks the preserved
test logs; it does not rerun tests. Freeze/run guards reject another experiment
or duplicate submissions. Do not remove them to resample this trial.

Provider lifecycle reference: [official OpenAI background-mode documentation](https://developers.openai.com/api/docs/guides/background).
