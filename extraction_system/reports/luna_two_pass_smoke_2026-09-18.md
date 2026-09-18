# Two-Pass GLiNER-BioMed Luna Smoke

Date: 2026-09-18
Branch: `extraction_system_v2`
Base implementation: `f502399`
Scope: one production-code change, full test verification, and exactly one live Luna rerun. No perturbation pass, prompt change, alternate model, threshold change, or additional paid run was used.

## IMPLEMENTATION

- The normal composed GLiNER-to-Luna path now loads `Ihor/gliner-biomed-base-v1.0` once and runs two sequential passes:
  1. core: `gene`, `protein`, `disease`, `chemical`, `species`, `cell line`, `DNA`, `RNA`;
  2. process: `biological process`.
- Pass outputs are normalized through the existing `Entity` contract.
- Duplicates are removed by exact `(start, end, type, text)` identity. The first deterministic pass occurrence retains its GLiNER score; no score is synthesized.
- Remaining entities are sorted by `(start, end, type, text)` and receive fresh deterministic `E1`-style IDs after merging.
- Explicit label callers remain single-pass. `perturbation` is not included in the production passes.
- The Luna relation extractor and prompt are unchanged.

## VERIFICATION

- Focused adapter/CLI/composition tests: included in the full suite and passing.
- Full test suite: `50/50` passed.
- Compile check: `uv --cache-dir C:/Projects/Biomed/.uv-cache run python -m compileall -q src tests` passed.
- `git diff --check`: passed before the live call.
- No paid API was called before tests passed.

## LIVE RERUN

Command:

```powershell
uv --cache-dir C:/Projects/Biomed/.uv-cache run --env-file .env biomedical-extract-llm --text "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF."
```

- Status: PASS, exit code `0`.
- Model: `gpt-5.6-luna`.
- Reasoning effort: `high`.
- Configured completion ceiling: `8192`.
- Wall-clock latency: `21.265 s`, including model initialization/cache fetch and the Luna call.
- Actual input/output/reasoning/total token usage: unavailable at the current LangChain/CLI boundary.
- Provider retry count: not exposed; no retry indication was emitted. No additional provider run was initiated.
- Secret handling: `.env` was used locally; its value was never printed, logged, or included in this report.

## ENTITIES

Exact merged output:

```json
[
  {
    "id": "E1",
    "text": "p53",
    "type": "gene",
    "start": 46,
    "end": 49,
    "score": 0.9957374334335327
  },
  {
    "id": "E2",
    "text": "proliferation ability",
    "type": "biological process",
    "start": 64,
    "end": 85,
    "score": 0.5634341239929199
  },
  {
    "id": "E3",
    "text": "apoptosis",
    "type": "biological process",
    "start": 98,
    "end": 107,
    "score": 0.9412609338760376
  },
  {
    "id": "E4",
    "text": "apoptosis",
    "type": "disease",
    "start": 98,
    "end": 107,
    "score": 0.5024200081825256
  },
  {
    "id": "E5",
    "text": "autophagy",
    "type": "biological process",
    "start": 108,
    "end": 117,
    "score": 0.9079713225364685
  },
  {
    "id": "E6",
    "text": "SSC-4 cells",
    "type": "cell line",
    "start": 121,
    "end": 132,
    "score": 0.9944570064544678
  },
  {
    "id": "E7",
    "text": "migration",
    "type": "biological process",
    "start": 180,
    "end": 189,
    "score": 0.8534796237945557
  },
  {
    "id": "E8",
    "text": "VEGF",
    "type": "protein",
    "start": 224,
    "end": 228,
    "score": 0.986096203327179
  }
]
```

The exact span/type duplicate `apoptosis` was retained twice because the two returned types differ (`biological process` and `disease`); no type-resolution rule was added.

## RELATIONS

Exact Luna output:

```json
[
  {
    "source": "E1",
    "target": "E2",
    "predicate": "inhibition of expression decreases proliferation ability",
    "evidence": "inhibiting the expression of p53 decreased the proliferation ability",
    "negated": false,
    "surface_form": "inhibiting the expression of p53 decreased the proliferation ability",
    "score": null
  },
  {
    "source": "E1",
    "target": "E3",
    "predicate": "inhibition of expression induces apoptosis",
    "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis",
    "negated": false,
    "surface_form": "induced apoptosis",
    "score": null
  },
  {
    "source": "E1",
    "target": "E5",
    "predicate": "inhibition of expression induces autophagy",
    "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy",
    "negated": false,
    "surface_form": "induced apoptosis/autophagy",
    "score": null
  },
  {
    "source": "E1",
    "target": "E7",
    "predicate": "inhibition of expression decreases migration",
    "evidence": "this has decreased migration",
    "negated": false,
    "surface_form": "has decreased migration",
    "score": null
  },
  {
    "source": "E1",
    "target": "E8",
    "predicate": "inhibition of expression blocks VEGF expression",
    "evidence": "has blocked the expression of VEGF",
    "negated": false,
    "surface_form": "has blocked the expression of VEGF",
    "score": null
  }
]
```

Offline checks accepted all `5/5` relations. Every relation endpoint references a returned entity, and every evidence/surface-form string occurs verbatim in the supplied passage. The process effects target `E2`, `E3`, `E5`, and `E7`; none target `SSC-4 cells` (`E6`).

## COMPARISON

- Previous smoke: `3` entities and `4` relations. It returned `p53` as gene, `SSC-4 cells` as cell line, and `VEGF` as chemical; the effects were directed to `SSC-4 cells` or `VEGF`.
- New smoke: `8` entities and `5` relations. It recovered `proliferation ability` as a biological process and added `apoptosis`, `autophagy`, and `migration` as process endpoints.
- Process endpoint fidelity improved: Luna now uses the biological-process IDs for proliferation, apoptosis, autophagy, and migration instead of using `SSC-4 cells` for those effects.
- Proliferation was recovered with exact span `proliferation ability`, `[64, 85)`, score `0.5634341239929199`.
- Remaining material issue: the core pass also returned `apoptosis` as `disease`, and `VEGF` was returned as `protein`; no ambiguity-resolution rule was added, as required.

The machine-readable technical record is [luna_two_pass_smoke_2026-09-18.json](<C:/Projects/Biomed/extraction_system/reports/luna_two_pass_smoke_2026-09-18.json>). No further architectural change was made in response to the live result.

## MACHINE-READABLE TECHNICAL DETAILS

```json
{
  "report_type": "two_pass_luna_smoke",
  "report_date": "2026-09-18",
  "branch": "extraction_system_v2",
  "base_commit": "f502399",
  "scope": {
    "paid_api_calls": 1,
    "luna_called": true,
    "relation_prompt_changed": false,
    "perturbation_included": false,
    "alternate_model_tested": false,
    "threshold_changed": false,
    "manual_entities_added": false
  },
  "implementation": {
    "entity_model": "Ihor/gliner-biomed-base-v1.0",
    "model_loads_per_extraction": 1,
    "passes": [
      {
        "name": "core",
        "labels": ["gene", "protein", "disease", "chemical", "species", "cell line", "DNA", "RNA"]
      },
      {
        "name": "process",
        "labels": ["biological process"]
      }
    ],
    "merge_key": ["start", "end", "type", "text"],
    "duplicate_policy": "first deterministic occurrence retains its GLiNER score",
    "ordering_key": ["start", "end", "type", "text"],
    "id_policy": "assign E1-style IDs after deduplication and ordering",
    "explicit_labels": "single-pass behavior retained"
  },
  "verification": {
    "full_test_suite": {"passed": 50, "total": 50},
    "compileall": "PASS",
    "git_diff_check_before_live": "PASS"
  },
  "live_rerun": {
    "command": "uv --cache-dir C:/Projects/Biomed/.uv-cache run --env-file .env biomedical-extract-llm --text <supplied passage>",
    "status": "PASS",
    "exit_code": 0,
    "model": "gpt-5.6-luna",
    "reasoning_effort": "high",
    "max_completion_tokens": 8192,
    "wall_clock_seconds": 21.265,
    "provider_attempt_count": null,
    "provider_retry_observed": null,
    "token_usage": {
      "input_tokens": null,
      "output_tokens": null,
      "reasoning_tokens": null,
      "total_tokens": null,
      "available": false,
      "reason": "Usage metadata is not exposed at the current LangChain/CLI boundary."
    }
  },
  "entities": [
    {"id": "E1", "text": "p53", "type": "gene", "start": 46, "end": 49, "score": 0.9957374334335327},
    {"id": "E2", "text": "proliferation ability", "type": "biological process", "start": 64, "end": 85, "score": 0.5634341239929199},
    {"id": "E3", "text": "apoptosis", "type": "biological process", "start": 98, "end": 107, "score": 0.9412609338760376},
    {"id": "E4", "text": "apoptosis", "type": "disease", "start": 98, "end": 107, "score": 0.5024200081825256},
    {"id": "E5", "text": "autophagy", "type": "biological process", "start": 108, "end": 117, "score": 0.9079713225364685},
    {"id": "E6", "text": "SSC-4 cells", "type": "cell line", "start": 121, "end": 132, "score": 0.9944570064544678},
    {"id": "E7", "text": "migration", "type": "biological process", "start": 180, "end": 189, "score": 0.8534796237945557},
    {"id": "E8", "text": "VEGF", "type": "protein", "start": 224, "end": 228, "score": 0.986096203327179}
  ],
  "relations": [
    {"source": "E1", "target": "E2", "predicate": "inhibition of expression decreases proliferation ability", "evidence": "inhibiting the expression of p53 decreased the proliferation ability", "negated": false, "surface_form": "inhibiting the expression of p53 decreased the proliferation ability", "score": null},
    {"source": "E1", "target": "E3", "predicate": "inhibition of expression induces apoptosis", "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis", "negated": false, "surface_form": "induced apoptosis", "score": null},
    {"source": "E1", "target": "E5", "predicate": "inhibition of expression induces autophagy", "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy", "negated": false, "surface_form": "induced apoptosis/autophagy", "score": null},
    {"source": "E1", "target": "E7", "predicate": "inhibition of expression decreases migration", "evidence": "this has decreased migration", "negated": false, "surface_form": "has decreased migration", "score": null},
    {"source": "E1", "target": "E8", "predicate": "inhibition of expression blocks VEGF expression", "evidence": "has blocked the expression of VEGF", "negated": false, "surface_form": "has blocked the expression of VEGF", "score": null}
  ],
  "validation": {
    "entity_span_check": {"status": "PASS", "checked": 8, "total": 8},
    "relation_endpoint_check": {"status": "PASS", "checked": 5, "total": 5},
    "relation_evidence_check": {"status": "PASS", "checked": 5, "total": 5},
    "relation_validator_acceptance": {"status": "PASS", "accepted": 5, "total": 5},
    "process_relation_targets": ["E2", "E3", "E5", "E7"],
    "ssc4_relation_targets": [],
    "secret_value_printed": false,
    "secret_value_in_report": false
  },
  "comparison": {
    "previous_entity_count": 3,
    "previous_relation_count": 4,
    "new_entity_count": 8,
    "new_relation_count": 5,
    "proliferation_recovered": true,
    "process_endpoints_improved": true,
    "remaining_issue": "apoptosis also received a disease label; VEGF is protein in the new output. No ambiguity-resolution logic was added."
  }
}
```
