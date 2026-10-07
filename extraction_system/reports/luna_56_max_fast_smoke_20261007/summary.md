# Luna/max/Fast migration smoke — blocked

The proposed default switch was not promoted. All 71 focused offline tests passed, but the smoke driver failed locally before any OpenAI request. The original code, tests, documentation, and environment template were restored; the ignored local `.env` was never modified.

The smoke driver prepared the frozen UTF-8 packet correctly, then read it using Windows CP1252 during execution. This changed the decoded source and produced 27 span mismatches. The unchanged entity assembly validator rejected the packet. Explicit UTF-8 decoding was verified offline to retain all 41 mentions and assemble 20 nodes. This is a driver setup error, not evidence about the model or provider.

- Provider requests: **0**; role requests: **0**; paid inference resubmissions: **0**.
- Fast-tier verification: **not run**. Requested and observed tiers were never fabricated.
- Scientific review: **not run**. No live relation or role outputs exist.
- No prompt, schema, extraction, role wording, graph, or scientific-coverage tuning occurred.

The task's stop rule was honored. The complete proposed implementation remains reviewable in `candidate.patch`; the original failed driver and frozen preflight are preserved. `driver_setup_fix.patch` records the explicit UTF-8 decoding correction for a separately authorized fresh smoke. It was not used for a second run.

The offline suites cover configuration, Responses lifecycle and tier metadata, relations, both CLIs, pipeline composition, and paper roles. The installed virtual-environment Python ran these checks because uv could not write its interpreter cache inside the sandbox. No dependencies were changed.

Evidence: `preflight.json`, `inputs.json`, `frozen_findings.json`, both providers' semantic/transport schemas, `baseline_graph.json`, `offline_verification.json`, `offline_tests.log`, `execution.json`, `setup_failure.json`, and the two unperformed review records. Raw/incremental cache artifacts remain ignored.
