# GPT-6 Luna max versus GPT-5.6 Luna max: eight-abstract attempt

**The intelligence comparison remains unresolved.** Three consecutive requests
timed out without returning a model output or token usage. The frozen stop rule
then aborted the remaining 13 jobs. No relation-quality winner, measured cost
advantage, or eight-paper completion is claimed.

The experiment used only Luna models. Production defaults, NER, prompts, schema,
validation, relations, graphs, paper roles, and viewer behavior were unchanged.

## Observed result

| Source | GPT-6 Luna max | GPT-5.6 Luna max |
|---|---|---|
| PMC10770459 | Request timeout, 300.141 s | Request timeout, 300.125 s |
| PMC11824863 | Unattempted after abort | Request timeout, 300.125 s |
| Remaining six abstracts | Unattempted after abort | Unattempted after abort |

All attempted jobs ended with the same production-facing error:

`LLM relation provider invocation failed: Request timed out.`

The retained exception chain includes `OpenAITimeoutError`, `APITimeoutError`,
and `ReadTimeout` (`The read operation timed out`). These were network-enabled,
escalated executions, rather than an automatic approval rejection. The evidence
does not identify whether the delay arose in the provider, an intermediary, or
inference itself. It establishes failure to return a response within this
experiment's five-minute request limit.

There were 16 planned jobs, three attempted jobs, zero returned provider
responses, zero validated outputs, and zero successfully paired papers. Each
attempt made one request. No output repairs or provider retries occurred.
The run lasted 15 minutes 5.868 seconds including worker startup. The second
abstract was attempted only by GPT-5.6 Luna because the balanced execution order
placed that condition first there; this imbalance after abort is not evidence
that either model is more reliable.

## Controlled method

The current repository baseline was
`7f388368a8bd06f35f60eda37eb2ccdce711eed8`. Eight complete title-plus-abstract
texts were verified against the canonical corpus, together with their saved
HunFlair2 mention packets. Their combined input contains 13,562 source
characters and 331 entity mentions. Full papers and the development paper
PMC10444909 were excluded.

The frozen sources were PMC10770459, PMC11824863, PMC8605525, PMID 27172794,
PMID 27370646, PMID 31324362, PMID 33652126, and PMID 38569671.

Both conditions used the unchanged production Responses structured-output
extraction path with `reasoning.effort=max`, default reasoning mode, a 128,000
output-token ceiling, two bounded output repairs, zero provider retries, a
300-second request timeout, and a 920-second external job watchdog. The offline
request payloads were identical except for model identity. Four papers were
A-first and four B-first in the planned order. Three consecutive operational
failures stopped execution. No prompt or configuration was tuned during the run,
and no aborted request was manually retried.

Every request was fresh: no previous response state or prior extracted relation
was supplied. Saved NER mentions were reused deliberately to hold entity
detection constant. This does not establish that the papers were absent from a
model's training data, nor does it guarantee a cold provider prompt cache.

## Source-grounded review preparation

Two GPT-6 Luna max reviewers separately inventoried the sources before reading
generated outputs or the A/B key. They recorded 59 clear claims, 25 ambiguous or
tentative claims, and 21 excluded items. All 105 items passed checks that their
evidence excerpts occur verbatim in the frozen source and that referenced entity
IDs exist in the corresponding packet.

These are machine-generated review aids, not human-adjudicated biomedical gold.
Quote and ID checks do not certify semantic correctness or inventory
completeness. In particular, the references preserve missing/composite NER
endpoints, study aims, naming constructions, the `Cbl`/`Cb1` source spelling
difference, and uncertainty about biological direction or intervention effects.
They are intended to prevent an NER gap, a hypothesis, or an alias from being
misclassified as a relation-model error.

The planned review would assess endpoint identity, direction, negation,
assertion support, intervention, effects, context, grounding, alias-only
relations, and omitted explicit claims. With no outputs, those comparisons are
all **not assessable**. No claims are counted as model omissions, no empty graph
is scored, and no precision, recall, F1, or intelligence ranking is reported.

The source references, neutral terminal outputs, and unassessable review were
hashed and frozen before analysis disclosed the key:
**Model A = GPT-6 Luna; Model B = GPT-5.6 Luna.**

## Cost

Actual token usage and request cost are **unknown**. No usage was returned by
any attempted call, and a timed-out request is not assumed to be free.

The standard short-context unit prices checked for the preflight were:

| USD per million tokens | GPT-5.6 Luna | GPT-6 Luna |
|---|---:|---:|
| Input | 0.20 | 0.10 |
| Cached input | 0.02 | 0.01 |
| Cache write | 0.25 | 0.125 |
| Output, including billed reasoning | 1.20 | 0.50 |

These are published rates, not measured charges or an eight-paper estimate.
At equal token counts GPT-6 Luna has lower unit cost, but the run supplies no
evidence about its reasoning-token consumption or total cost for these papers.
Sources: [GPT-5.6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
and [GPT-6 Luna model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna).

## Verification and decision

Preflight verified all eight input packets and exact half-open mention spans,
source/prompt/schema/code hashes, a clean production/test/viewer scope, and
offline payload equality apart from model identity. The 36 focused relation,
CLI, pipeline, and paper-role tests had passed earlier in this session on the
unchanged production code; they were not rerun. Source-reference provenance
checks passed. Finalization confirmed the three terminal failures, 13 unattempted
jobs, absent responses/usage, and the review freeze before unblinding.

This attempt does **not** justify changing the current GPT-5.6 Luna defaults or
claiming GPT-6 Luna is smarter or weaker at biomedical relations. The next useful
step is to establish why the actual Responses path does not return realistic
requests within the timeout, then freeze a new experiment in a
fresh report root. Preserve this attempt unchanged; any later synthetic
connectivity test would establish connectivity only.

## Artifacts

- `preflight.json`: baseline, configuration, input and code hashes, execution order.
- `inputs/`: exact eight source texts and entity packets.
- `outputs/`: neutral per-job attempts, exact failures, and unattempted records.
- `run_state.json`: terminal abort state and actual execution order.
- `review/`: source-only inventories, provenance verification, and frozen unassessable review.
- `analysis.json`: disclosed mapping and model-specific operational accounting.
- `scripts/`: reproducible freeze/run, reference validation, and no-response finalization.
- `verification.json`: checks recorded before the first provider request.
- `.gitattributes`: preserves exact artifact bytes and their frozen hashes in Git.

Private prompts, provider metadata, and the original model key remain in the
ignored cache. No credentials are included in this report.
