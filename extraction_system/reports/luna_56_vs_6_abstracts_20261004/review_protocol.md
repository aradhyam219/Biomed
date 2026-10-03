# Paired eight-abstract Luna comparison

The user authorized a thorough GPT-5.6 Luna `max` versus GPT-6 Luna `max`
comparison. This evaluation does not change production defaults, prompts,
schemas, validation, NER, graphs, or the viewer.

## Frozen experiment

Eight complete title-plus-abstract sources and the corresponding saved HunFlair2
mention packets are verified against the canonical corpus. Each model receives
the same untouched input through the current Responses harness: `max` effort,
standard/default reasoning mode, 128,000 output-token ceiling, two bounded
output repairs, zero provider retries, a 300-second request timeout, and a
920-second external job watchdog. One fresh replicate per model/paper gives
16 jobs, with four papers A-first and four B-first. No previous model output or
response state is supplied. Three consecutive transport, timeout, or worker
failures abort remaining jobs; malformed generated output follows the existing
bounded repair policy. Failed output is never hand-corrected.

## Review

Source-only Luna reviewers inventory representable explicit claims without
reading generated outputs or the model key. These references are machine-made
review aids, not adjudicated biomedical gold. Final outputs are then assessed
under neutral A/B labels. Every emitted relation is checked for endpoint
identity, direction, negation, assertion support, material intervention and
outcomes, appropriate context, and alias/naming-only artifacts. Every source
reference claim is checked for coverage or a justified representability limit.
Different predicate wording and duplicate mention-level formulations are not
automatically counted as semantic disagreements.

Relations receive `supported`, `partially_supported`, `unsupported`, or
`unclear` judgments with source evidence and rationale. Coverage receives
`covered`, `partial`, `missing`, or `not_assessable`. Review disagreements and
uncertainties remain explicit. Review files and their hashes are frozen before
the model key is disclosed. More relations or longer assertions do not establish
higher intelligence. No precision, recall, F1, population accuracy, or causal
quality claim is made from this small, machine-reviewed set.

## Accounting and interpretation

Every attempt retains timing, generated output, validation outcome, provider
usage when returned, and exact errors. Provider metadata and the A/B key stay
in the ignored cache during review. Reported cost distinguishes token-based
estimates from measured provider usage and leaves missing usage unknown.
Transport failures and timeouts establish operational limitations only. A
recommendation requires successful paired outputs and a source-grounded review;
an aborted experiment cannot establish a semantic winner.
