# Contract 11S-R

## SEMANTIC SCHEMA

Unchanged Contract 10 semantic schema SHA-256:
`023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945`

## TRANSPORT SCHEMA

SDK strict transport SHA-256:
`b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510`

Derived using public SDK responses.parse with an offline MockTransport; live requests used responses.create so the response ID was persisted before parsing. No private SDK helpers or custom schema transformer.

Offline equivalence checks passed: only object requiredness and removal of null defaults changed; field descriptions, types, references and nullability preserved; all objects closed; collection keys required. Empty relations and the representative null/empty qualifiers passed the unchanged Contract 10 parser and validator with identical normal Contract 10 relation semantics. Frozen passage/source/entity/prompt/schema hashes matched; 68 entity spans were exact.

## SYNTHETIC CONTROL

Create: successful, initial status queued.  
Response ID: `resp_0a11cf7f032301b1006ac16659284087d195150b3cc9374033`  
Create latency: 1.609 s. Background duration: 3.578 s. Total phase elapsed: 5.297 s.  
Terminal status: completed. Polls: 1. Poll failures: 0.  
Validated relations: 1. Unique evidence spans: 1. Repairs: 0. Contract 10 validation: passed.  
Tokens: 1029 input, 137 output, including 64 reasoning tokens (metadata only).

## REAL PASSAGE

Frozen PMCID:PMC10770459 passage_001: 1981 characters, 68 entities.  
Create: successful, initial status queued.  
Response ID: `resp_061ba37b3ed116e2006ac1665dc4f087d18406d79290020103`  
Create latency: 0.906 s. Deadline: 480 s from ID receipt.  
Last status at deadline: in_progress. Same-ID cancellation requested at 2026-10-03T20:40:27.356612+00:00; result: cancelled.  
Background elapsed including cancellation: 481.0 s. Total phase elapsed: 482.0 s.  
Polls: 138. Poll failures: 0. Primary generations: 1. Repairs: 0.  
Structured output received: no. Validated relations: 0. Unique evidence spans: 0. Tokens/usage: unavailable.

Outcome: background_timeout_cancelled. The transport schema correction succeeded. The real passage failed at the background inference deadline; it did not produce output for parsing or validation. No model-quality conclusion is drawn. No further provider requests were made.

## INTEGRITY

Current authorized HEAD: fd66f9bb6d1a5c41ae147abfb5a7994c5bddae6c. Production diff against 7f388368a8bd06f35f60eda37eb2ccdce711eed8 and local production diff: empty. Production default: gpt-5.6-luna. Existing reports and report commit preserved.

Production code unchanged: yes  
Production model default unchanged: yes  
Nothing committed or pushed: yes
