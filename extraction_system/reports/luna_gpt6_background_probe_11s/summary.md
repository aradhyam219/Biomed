# Contract 11S — stopped at schema integration blocker

## BASELINE

Branch: extraction_system_v2  
HEAD: 7f388368a8bd06f35f60eda37eb2ccdce711eed8  
Production diff: empty before and after. Production model default: gpt-5.6-luna.

All frozen source/entity/prompt/schema hashes matched; 68/68 entity spans were exact.
Runtime: openai 3.14.1, langchain-openai 1.6.2, langchain-core 1.6.3.
Provider call executed using require_escalated / network-capable execution.

## BACKGROUND CONTROL

Status: background_create_failure (HTTP 400, invalid_json_schema).  
Response ID: none. Terminal provider status: unavailable (no job created).  
Initial-create latency: 1.063 seconds. Total elapsed: 1.156 seconds.  
Create attempts: 1. Confirmed background jobs: 0. Repairs: 0. Polls: 0. Poll failures: 0.  
Validated relations: 0. Unique evidence spans: 0. Usage/input/output tokens: unavailable.

Exact error:

```text
Error code: 400 - {'error': {'message': "Invalid schema for response_format 'StructuredRelationPayload': In context=(), 'required' is required to be supplied and to be an array including every key in properties. Missing 'intervention'.", 'type': 'invalid_request_error', 'param': 'text.format.schema', 'code': 'invalid_json_schema'}}
```

Request ID: req_f95dd78a4b0f465db86392acd433671e.
Full redacted cause chain is in synthetic_background.json.

## REAL PASSAGE

Status: not_run — Phase A failed; mandatory contract stop.  
Response ID, initial-create latency, terminal status, elapsed, input/output tokens, validated relations, and unique evidence spans: not applicable.  
Provider generations: 0. Repairs: 0. Polls: 0. Poll failures: 0.

This result establishes a direct-schema integration blocker. Background feasibility for the real passage remains untested. No schema rewrite, second create, or alternate test was performed.

Verification: six offline adapter lifecycle checks passed. Final production diff was empty and HEAD still matched. An unrelated abstracts report became staged externally during execution; this probe left it untouched.

Artifacts: preflight.json, synthetic_background.json, real_passage_background.json, poll_history.json, summary.md, summary.json. Adapter and offline checks are under scripts/.

Production code unchanged: yes
Production model default unchanged: yes
Nothing committed or pushed: yes
