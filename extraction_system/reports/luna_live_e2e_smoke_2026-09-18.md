# LIVE SMOKE — GLiNER-BioMed to GPT-5.6 Luna

Date: 2026-09-18
Branch: `extraction_system_v2`
Source: PMID 27370646
Scope: one live composed smoke run over genuine biomedical prose; this was not an evaluation campaign.

## LIVE SMOKE

- Command: `uv run --env-file .env biomedical-extract-llm --text "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF."`
- Result: PASS, process exit code `0`.
- Path exercised: text -> default GLiNER-BioMed entity schema -> GPT-5.6 Luna relation extraction -> local normalized relation validation.
- Entity schema: the configured default labels were used; no entities were manually supplied.
- Model: `gpt-5.6-luna`.
- Reasoning effort: `high`.
- Configured completion ceiling: `8192` tokens.
- Wall-clock latency: `44.842` seconds for the complete command, including GLiNER model initialization/cache fetch and the Luna call.
- Actual token usage: unavailable. The current LangChain/CLI boundary returns normalized entities and relations but does not expose input, completion, reasoning, or total usage metadata. `8192` is the configured ceiling, not observed completion usage.
- Retry status: the harness has a bounded repair budget, but the current CLI does not expose an attempt counter. No retry indication was emitted, so the exact provider-attempt count is not observable from this run.

The initial sandbox invocation failed before model/provider execution because `uv` could not read its existing user cache. The same command was then run with the required elevated cache access; this was an environment execution retry, not a second provider smoke run.

## ENTITIES

The composed command returned these normalized entities with half-open character spans:

```json
[
  {
    "id": "E1",
    "text": "p53",
    "type": "gene",
    "start": 46,
    "end": 49,
    "score": 0.9987726807594299
  },
  {
    "id": "E2",
    "text": "SSC-4 cells",
    "type": "cell line",
    "start": 121,
    "end": 132,
    "score": 0.9938382506370544
  },
  {
    "id": "E3",
    "text": "VEGF",
    "type": "chemical",
    "start": 224,
    "end": 228,
    "score": 0.8644157648086548
  }
]
```

## RELATIONS

The composed command returned these normalized, directed relations. All four had `negated: false` and `score: null` because the initial LLM schema does not request or fabricate relation confidence.

```json
[
  {
    "source": "E1",
    "target": "E2",
    "predicate": "inhibiting expression of p53 decreased proliferation ability in SSC-4 cells",
    "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells",
    "negated": false,
    "surface_form": "inhibiting the expression of p53 decreased the proliferation ability",
    "score": null
  },
  {
    "source": "E1",
    "target": "E2",
    "predicate": "inhibiting expression of p53 induced apoptosis/autophagy in SSC-4 cells",
    "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells",
    "negated": false,
    "surface_form": "induced apoptosis/autophagy in SSC-4 cells",
    "score": null
  },
  {
    "source": "E1",
    "target": "E2",
    "predicate": "decreased migration in SSC-4 cells",
    "evidence": "this has decreased migration",
    "negated": false,
    "surface_form": "has decreased migration",
    "score": null
  },
  {
    "source": "E1",
    "target": "E3",
    "predicate": "blocked expression of VEGF",
    "evidence": "has blocked the expression of VEGF",
    "negated": false,
    "surface_form": "has blocked the expression of VEGF",
    "score": null
  }
]
```

## VALIDATION

An offline deterministic check was run against the captured result without another provider call:

- Endpoint check: PASS, all `4/4` relations reference returned entity IDs `E1`–`E3`.
- Evidence grounding: PASS, all `4/4` evidence strings occur verbatim in the supplied passage.
- Surface-form grounding: PASS, all `4/4` surface forms occur verbatim in the supplied passage.
- Local validator: PASS, `validate_relations` accepted `4/4` relations.
- Unsupported output: none rejected by the validator. The initial LLM path intentionally has no finite predicate ontology; the check therefore covered the configured structural, endpoint, evidence, negation, surface-form, and score invariants.
- Secret handling: `.env` is Git-ignored and untracked. The live command output was captured through a redaction wrapper; no API key or other secret value appears in this report or the command output.

## MACHINE-READABLE TECHNICAL DETAILS

The same run is available as [luna_live_e2e_smoke_2026-09-18.json](<C:/Projects/Biomed/extraction_system/reports/luna_live_e2e_smoke_2026-09-18.json>) and is reproduced below for consumers that read this Markdown report directly.

```json
{
  "report_type": "live_e2e_smoke",
  "report_date": "2026-09-18",
  "branch": "extraction_system_v2",
  "source": {
    "pmid": "27370646",
    "text": "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF."
  },
  "command": {
    "argv": [
      "uv",
      "run",
      "--env-file",
      ".env",
      "biomedical-extract-llm",
      "--text",
      "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF."
    ],
    "status": "PASS",
    "exit_code": 0,
    "path": [
      "text",
      "GLiNER-BioMed",
      "GPT-5.6 Luna",
      "validated relations"
    ]
  },
  "configuration": {
    "model": "gpt-5.6-luna",
    "reasoning_effort": "high",
    "max_completion_tokens": 8192,
    "max_retries": 2,
    "entity_model": "Ihor/gliner-biomed-base-v1.0",
    "entity_labels": [
      "gene",
      "disease",
      "chemical",
      "species",
      "cell line",
      "DNA",
      "RNA"
    ],
    "entity_threshold": 0.5,
    "device": "auto",
    "entities_manually_supplied": false,
    "finite_predicate_ontology": false
  },
  "latency": {
    "wall_clock_seconds": 44.842,
    "scope": "complete command including GLiNER initialization/cache fetch and Luna call"
  },
  "token_usage": {
    "input_tokens": null,
    "output_tokens": null,
    "completion_tokens": null,
    "reasoning_tokens": null,
    "total_tokens": null,
    "available": false,
    "reason": "The current LangChain/CLI boundary does not expose provider usage metadata."
  },
  "retry_observability": {
    "harness_retry_budget": 2,
    "provider_attempt_count": null,
    "provider_retry_observed": null,
    "reason": "The harness does not expose an attempt counter and emitted no retry indication.",
    "environment_execution_retry": true,
    "environment_retry_reason": "Initial sandbox execution could not read uv's existing user cache; elevated execution was required before model/provider execution.",
    "user_initiated_second_paid_run": false
  },
  "entities": [
    {
      "id": "E1",
      "text": "p53",
      "type": "gene",
      "start": 46,
      "end": 49,
      "score": 0.9987726807594299
    },
    {
      "id": "E2",
      "text": "SSC-4 cells",
      "type": "cell line",
      "start": 121,
      "end": 132,
      "score": 0.9938382506370544
    },
    {
      "id": "E3",
      "text": "VEGF",
      "type": "chemical",
      "start": 224,
      "end": 228,
      "score": 0.8644157648086548
    }
  ],
  "relations": [
    {
      "source": "E1",
      "target": "E2",
      "predicate": "inhibiting expression of p53 decreased proliferation ability in SSC-4 cells",
      "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells",
      "negated": false,
      "surface_form": "inhibiting the expression of p53 decreased the proliferation ability",
      "score": null
    },
    {
      "source": "E1",
      "target": "E2",
      "predicate": "inhibiting expression of p53 induced apoptosis/autophagy in SSC-4 cells",
      "evidence": "inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells",
      "negated": false,
      "surface_form": "induced apoptosis/autophagy in SSC-4 cells",
      "score": null
    },
    {
      "source": "E1",
      "target": "E2",
      "predicate": "decreased migration in SSC-4 cells",
      "evidence": "this has decreased migration",
      "negated": false,
      "surface_form": "has decreased migration",
      "score": null
    },
    {
      "source": "E1",
      "target": "E3",
      "predicate": "blocked expression of VEGF",
      "evidence": "has blocked the expression of VEGF",
      "negated": false,
      "surface_form": "has blocked the expression of VEGF",
      "score": null
    }
  ],
  "validation": {
    "endpoint_check": {"status": "PASS", "checked": 4, "total": 4},
    "evidence_grounding_check": {"status": "PASS", "checked": 4, "total": 4},
    "surface_form_grounding_check": {"status": "PASS", "checked": 4, "total": 4},
    "validator_acceptance": {"status": "PASS", "accepted": 4, "total": 4},
    "unsupported_relations_rejected": 0
  },
  "secret_safety": {
    "env_file": ".env",
    "env_git_ignored": true,
    "env_git_tracked": false,
    "secret_value_printed": false,
    "secret_value_logged": false,
    "secret_value_committed": false,
    "secret_value_in_report": false
  },
  "repository_changes": {
    "production_code_changed": false,
    "prompt_changed": false,
    "dependency_changed": false,
    "architecture_changed": false,
    "report_only": true
  },
  "issues": {
    "material_extraction_issues": [],
    "operational_notes": [
      "Initial uv cache permission failure was resolved with elevated execution before the live path ran."
    ]
  }
}
```

## ISSUES

No extraction issue was observed. The only operational issue was the initial `uv` cache permission failure described above; it was resolved with elevated execution and caused no repository change.

No prompts, production code, dependencies, or architecture were changed for this smoke. This report is the only repository change.
