# Contract 12B review package

Start with `summary.md`, then inspect `scientific_review.json` and the case
`comparison.json` files. `verification.json` is mechanical verification, not a
scientific promotion verdict. Ordinary model/execution/prompt defaults are
unchanged.

The initial runner completed SFPQ and Cbl; three subsequent submissions failed
before response IDs were received. After DNS diagnosis and recovery, the three
remaining cases each completed once. Initial failures remain in `refined.json`;
the final outputs for those cases are `refined_retry_01.json`. Final telemetry
and comparisons explicitly select the latter. Both `run_state.json` and
`recovery_state.json` are preserved. There were no control generations, no
repairs, no completed-case reruns, and no adaptive prompt edits.

From the repository directory, reproduce offline checks without provider calls:

```powershell
.venv\Scripts\python.exe reports/relation_prompt_refinement_12b/scripts/experiment.py verify
$taskGraphs = Get-ChildItem reports/relation_prompt_refinement_12b/graphs -Recurse -Filter '*.json' | Select-Object -ExpandProperty FullName
node reports/relation_prompt_refinement_12b/scripts/check_viewer.mjs @taskGraphs
.venv\Scripts\python.exe reports/relation_prompt_refinement_12b/scripts/build_review.py
```

The last two commands regenerate review artifacts; their timestamps and review
freeze change. The `freeze`, `run` and recovery entry points refuse to overwrite
an existing freeze/run. Do not delete those guards to launch another trial; a
later experiment needs separate authorization and a separate artifact root.

All source/entity/prompt/schema/request hashes were frozen before inference.
Control 12A graphs were exactly reproduced through the current production
pipeline. The 11U control request hash and semantic/strict schemas matched the
original Candidate C records. Both control and refined passage graphs were
built through that same unchanged pipeline; neither graph invokes NER or roles.

Provider lifecycle reference: [official OpenAI background-mode documentation](https://developers.openai.com/api/docs/guides/background).
