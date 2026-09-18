# Exact-Span Core/Process Cleanup Luna Smoke

Date: 2026-09-18
Branch: `extraction_system_v2`
Base commit: `2b74f34`

## CLEANUP

The existing two-pass path remains unchanged: one GLiNER-BioMed model serves
the core labels (`gene`, `protein`, `disease`, `chemical`, `species`, `cell
line`, `DNA`, `RNA`) and the `biological process` pass. During merge, a
`biological process` returned by the dedicated process pass suppresses a
non-process-pass entity only when `(start, end, source text)` is identical.

Exact `(start, end, type, text)` duplicates are still removed. The retained
process entity keeps its original GLiNER score; scores are not compared. No
arbitrary same-pass core-label ambiguity is resolved. Entities are then sorted
deterministically and assigned `E1`-style IDs.

## VERIFICATION

- Focused entity tests: `8/8` passed.
- Full test suite: `51/51` passed.
- Deterministic live-output validator check: `5/5` relations accepted; `7/7`
  entity IDs supplied; all evidence and surface forms were verbatim substrings.
- `.env` is Git-ignored. No secret value was printed, logged, committed, or
  included in this report.
- The first sandboxed transport attempt failed locally with `WinError 10013`
  before an API response. The same bounded command was then run with approved
  network access and completed once; no provider/output retry was observed.

## LIVE RERUN

Command:

```powershell
uv --cache-dir C:/Projects/Biomed/.uv-cache run --env-file .env biomedical-extract-llm --text "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF."
```

- Status: PASS, exit code `0`.
- Model: `gpt-5.6-luna`.
- Reasoning effort: `high`.
- Completion ceiling: `8192`.
- Wall-clock latency: `26.229 s` (including model initialization/cache activity
  and the Luna call).
- Input, output, reasoning, and total token counts: unavailable at the current
  LangChain/CLI boundary; no usage fields are exposed there.

### ENTITIES

```json
[
  {"id":"E1","text":"p53","type":"gene","start":46,"end":49,"score":0.9957374334335327},
  {"id":"E2","text":"proliferation ability","type":"biological process","start":64,"end":85,"score":0.5634341239929199},
  {"id":"E3","text":"apoptosis","type":"biological process","start":98,"end":107,"score":0.9412609338760376},
  {"id":"E4","text":"autophagy","type":"biological process","start":108,"end":117,"score":0.9079713225364685},
  {"id":"E5","text":"SSC-4 cells","type":"cell line","start":121,"end":132,"score":0.9944570064544678},
  {"id":"E6","text":"migration","type":"biological process","start":180,"end":189,"score":0.8534796237945557},
  {"id":"E7","text":"VEGF","type":"protein","start":224,"end":228,"score":0.986096203327179}
]
```

### RELATIONS

```json
[
  {"source":"E1","target":"E2","predicate":"inhibition of expression decreased proliferation ability","evidence":"inhibiting the expression of p53 decreased the proliferation ability","negated":false,"surface_form":"decreased the proliferation ability","score":null},
  {"source":"E1","target":"E3","predicate":"inhibition of expression induced apoptosis","evidence":"inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells","negated":false,"surface_form":"induced apoptosis","score":null},
  {"source":"E1","target":"E4","predicate":"inhibition of expression induced autophagy","evidence":"inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells","negated":false,"surface_form":"induced apoptosis/autophagy","score":null},
  {"source":"E1","target":"E6","predicate":"inhibition of expression decreased migration","evidence":"this has decreased migration","negated":false,"surface_form":"decreased migration","score":null},
  {"source":"E1","target":"E7","predicate":"inhibition of expression blocked VEGF expression","evidence":"this has decreased migration and has blocked the expression of VEGF","negated":false,"surface_form":"blocked the expression of VEGF","score":null}
]
```

### VALIDATION

- Entity source-span checks: `7/7` pass.
- Relation endpoint checks: `5/5` pass; every endpoint is one of `E1`–`E7`.
- Evidence and surface-form grounding: `5/5` pass; all occur verbatim in the
  supplied passage.
- Local relation validator acceptance: `5/5`.
- Process relation targets: `E2`, `E3`, `E4`, `E6`.
- `SSC-4 cells` target: none.
- Exact-span `apoptosis` count: one, type `biological process`; the disease
  duplicate is absent.

## COMPARISON

The immediately preceding two-pass smoke returned 8 entities and 5 relations,
including both `apoptosis`/`biological process` and `apoptosis`/`disease` at
`[98, 107)`. The cleaned run returns 7 entities and the same 5 semantic
relations; the process node remains and the disease duplicate is removed.

`proliferation ability`, `apoptosis`, `autophagy`, and `migration` remain
biological-process endpoints. None of the five relations targets `SSC-4
cells`. No material regression was observed. `VEGF` remains a core-pass
`protein` detection; no unrelated type-resolution rule was added.

The machine-readable technical record is
[luna_conflict_cleanup_smoke_2026-09-18.json](<C:/Projects/Biomed/extraction_system/reports/luna_conflict_cleanup_smoke_2026-09-18.json>).
