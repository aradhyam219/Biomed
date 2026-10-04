# Contract 11Q-R blinded real biomedical RE probe

Status: aborted_stop_condition
Quality judgment: deferred to Talia; Codex assigns no winner or quality score.
Model mapping remains separately preserved and undisclosed.

## Baseline

- HEAD: 7f388368a8bd06f35f60eda37eb2ccdce711eed8
- Branch: extraction_system_v2
- Production-code diff under src/viewer/tests: clean

## Descriptive run table

| Passage | Model | Chars | Entities | Status | Relations | Attempts | Repairs | Latency ms | Input tokens | Output tokens |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| passage_001 | Model A | 1981 | 68 | provider_failure | — | 1 | 0 | 104.321 | — | — |
| passage_001 | Model B | 1981 | 68 | provider_failure | — | 1 | 0 | 84.215 | — | — |
| passage_002 | Model A | 1864 | 56 | not_run_aborted | — | 0 | 0 | — | — | — |
| passage_002 | Model B | 1864 | 56 | provider_failure | — | 1 | 0 | 83.018 | — | — |
| passage_003 | Model A | 1976 | 71 | not_run_aborted | — | 0 | 0 | — | — | — |
| passage_003 | Model B | 1976 | 71 | not_run_aborted | — | 0 | 0 | — | — | — |
| passage_004 | Model A | 1949 | 63 | not_run_aborted | — | 0 | 0 | — | — | — |
| passage_004 | Model B | 1949 | 63 | not_run_aborted | — | 0 | 0 | — | — | — |
| passage_005 | Model A | 1908 | 50 | not_run_aborted | — | 0 | 0 | — | — | — |
| passage_005 | Model B | 1908 | 50 | not_run_aborted | — | 0 | 0 | — | — | — |

## Totals

| Model | Successes | Validation failures | Timeouts/provider failures | Not run after abort | Total relations | Total tokens | Mean latency ms | Median latency ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Model A | 0 | 0 | 1 | 4 | 0 | — | 104.321 | 104.321 |
| Model B | 0 | 0 | 2 | 3 | 0 | — | 83.617 | 83.617 |

- Passages: 5
- Scheduled jobs: 10
- Completed jobs: 3
- Failures/timeouts: 3
- Validation failures: 0
- Repair attempts: 0
- Total elapsed wall time (seconds): 8.574
- No quality interpretation is included.

## Frozen configuration

- Provider: OpenAI Responses API
- Reasoning effort: max
- Max output tokens: 128000
- Contract 10 repair budget: 2
- Provider retries: 0
- Contract 10 prompt SHA-256: 13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f
- Contract 10 schema SHA-256: 023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945

## Review packets

- [disagreements.md](disagreements.md)
- [shared.md](shared.md)
- [preflight.json](preflight.json)
- Per-passage manifests and blinded results are under `passage_001/` through `passage_005/`.
