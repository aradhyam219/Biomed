# Contract 11P — Full-Paper Feasibility Probe

- Baseline: `extraction_system_v2@1f12923ce54ab6718a00b8d8e8126536285dc6a8`
- Paper: `PMCID:PMC10770459`; 48,203 source characters; 874 frozen mentions; 6 chunks.
- Production-code diff: none in `src/`, `viewer/`, or `tests/`.

## Execution

- Successful chunks: 0/6 (attempted 1); validation failures 0; timeouts 0; other failures 1.
- Provider attempts: 1; repairs: 0; elapsed: 3.485 seconds.
- Tokens: input unavailable; output unavailable (usage recorded for 0/1 input and 0/1 output attempts).
- Validated relations: 0; unique evidence spans: 0; source coverage by successful chunks: 0.0%.
- Graph: 114 nodes, 0 edges. Viewer smoke: graph loaded; no console errors or warnings; node inspection passed; edge and bundle checks unavailable because the graph has zero edges.
- Stop condition: failed_or_timed_out_fraction_exceeded_25_percent.

## Viewer smoke

- Graph load: passed; 114 nodes and 0 edges; console errors/warnings: 0; node inspection: passed for glucose (doc_e_001); 2 aliases and 64 source mentions displayed.
- Edge inspection: unavailable because there are no edges; relation bundles: unavailable because there are no edges.
- Default-layout screenshot: captured in the CUA viewer and displayed during the smoke check; no local PNG was saved because browser security rejected the data-URL navigation needed to persist it and prohibited workarounds.

## Failed chunks

- `chunk_001` range `0:9153`; attempts 1; repairs 0; elapsed 3.453 seconds.
  Error: `LLM relation provider invocation failed: Connection error.`

## Artifacts

- preflight: `reports/luna_6_fullpaper_pilot_11p/preflight.json`
- chunk_manifest: `reports/luna_6_fullpaper_pilot_11p/chunk_manifest.json`
- chunk_results: `reports/luna_6_fullpaper_pilot_11p/chunks`
- full_paper_relations: `reports/luna_6_fullpaper_pilot_11p/full_paper_relations.json`
- full_paper_graph: `reports/luna_6_fullpaper_pilot_11p/full_paper_graph.json`
- screenshot: not persisted
- summary_markdown: `reports/luna_6_fullpaper_pilot_11p/summary.md`
- summary_json: `reports/luna_6_fullpaper_pilot_11p/summary.json`
- screenshot_status: `captured in the CUA viewer and displayed during the smoke check; no local PNG was saved because browser security rejected the data-URL navigation needed to persist it and prohibited workarounds`

No scientific-quality judgment is included in this feasibility probe.
