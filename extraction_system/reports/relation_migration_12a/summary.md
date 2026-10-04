# Contract 12A production-path regression

Run status: **complete**

The paper set, title-plus-abstract source, mention packets, baseline relations, prompt, and semantic schema were frozen before the candidate run. Both current-pipeline comparison paths omit paper roles. The archived Contract 10 graph references contain stored role annotations on some unconnected nodes; archive equivalence therefore reports entity/edge equality with roles ignored and lists those annotations separately. This packet reports deterministic differences only; it does not declare a scientific winner.

## Semantic comparison

| Paper | Status | Baseline relations | Candidate relations | Baseline nodes/edges | Candidate nodes/edges | Node IDs preserved | Edge identities match | Baseline-only records | Candidate-only records | Paired rich-field changes | Exact relation match |
|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| PMCID:PMC11824863 | compared | 19 | 13 | 20/19 | 20/13 | True | False | 19 | 13 | 2 | False |
| PMCID:PMC8605525 | compared | 30 | 26 | 20/29 | 20/25 | True | False | 30 | 26 | 5 | False |
| PMID:27172794 | compared | 22 | 20 | 15/19 | 15/18 | True | False | 22 | 20 | 1 | False |
| PMID:33652126 | compared | 12 | 7 | 10/10 | 10/6 | True | False | 11 | 6 | 2 | False |

Full source text, supplied entities, every baseline/candidate relation field, and graph deltas are in `papers/*.json`. Baseline and candidate graph JSON files are under `graphs/baseline/` and `graphs/candidate/`. Edge identity compares directed source, target, predicate, and negation independently of edge IDs and rich evidence. Baseline-only and candidate-only relation counts are exact-record multiset differences; paired rich-field changes identify changed records sharing the same directed endpoints and predicate, so that count can overlap the two exact-record counts.

## Operational telemetry

| Paper | Status | Seconds | Generations | Repairs | Polls | Input tokens | Output tokens | Reasoning tokens | Observed service tier | Response IDs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| PMCID:PMC11824863 | success | 51.141567 | 1 | 0 | 14 | 3571 | 2791 | 1034 | default | resp_0986dbf2dccfd1d9006ac1bc4e621c87d189f85fa1cf36290f |
| PMCID:PMC8605525 | success | 68.509862 | 1 | 0 | 20 | 5109 | 4064 | 1552 | default | resp_003b9adce39336d3006ac1bc7fd1cc87d195695ff82c133925 |
| PMID:27172794 | success | 55.845936 | 1 | 0 | 16 | 3576 | 3594 | 882 | default | resp_06a6da7bd5f62682006ac1bcc45dd087d18bf4b003fb630af4 |
| PMID:33652126 | success | 31.466077 | 1 | 0 | 9 | 3131 | 1489 | 698 | default | resp_0d41b58e9ae977db006ac1bcfc3bd487d198b68855350863f7 |

## Reviewer paths

- `frozen_set_manifest.json` records selection, provenance hashes, and historical equivalence.
- `frozen_inputs.json` contains the self-contained source text, entity packets, and saved baseline relations.
- `papers/*.json` contains the complete per-paper semantic comparison.
- `telemetry.json` contains operational data separately from scientific output.
- `graphs/candidate/*.json` contains graph JSON for the existing viewer compatibility smoke.
- `verification.json`, `compatibility_verification.json`, and `viewer_smoke.json` record the mechanical, preservation, and viewer checks.
