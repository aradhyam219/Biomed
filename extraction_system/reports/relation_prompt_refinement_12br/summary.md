# Contract 12B-R — final grounding-constrained prompt experiment

**PROMPT REFINEMENT FAILED — PRESERVE 12A CONTROL BEHAVIOR**

Grounding improved, but required PTEN-expression recall and overall rich-field
preservation failed. Important SFPQ, Cbl and EZH2 findings were omitted. Stop
prompt refinement: no 12B-R2 and no production promotion. Production defaults,
semantic relation contract, graph behavior, viewer and historical artifacts are
unchanged. Talia/user retains the strategic decision.

## Experimental integrity

- Primary branch: `extraction_system_v2`; starting local and fetched remote SHA:
  `f92ce7e91b62ed069c4479f75a0820ae24d0848f`. No worktree or reset.
- The contract's replacement amendment was frozen before inference, SHA-256
  `efee8ddf2c8f72ee05fc174b86ed704103f62777dd83419a32217b530fe02acf`.
- Refined prompt is the unchanged protected Contract 10/control prompt plus one
  newline and that amendment. Failed 12B amendment is not stacked.
- Five exact 12B inputs, supplied entities, schema and graph pipeline preserved.
  Existing 12A and 11U Candidate C controls were proven equivalent offline;
  no paid control reruns.
- Exactly five successful scientific generations, zero repairs, zero operational
  retries, zero completed scientific reruns, zero adaptive prompt edits.
- Every completion observed `gpt-6.1-sol`, medium, Standard/default tier and
  `background=true`. Existing 900-second bounded lifecycle, three-second polling,
  128,000 output-token ceiling and finite repair budget were unchanged.

## Target findings and scientific gate

| Gate | Result |
|---|---|
| JAK2 and STAT4 | Recovered, Cbl [16,17]; assertions explicitly preserve joint overexpression, not independent interventions |
| Runx3 | Retained, Cbl [18] |
| Increased PTEN expression after serum deprivation in H9c2 | **Missing** |
| Artificial PTEN self-edge | None in relations or graph |
| Unsupported glucose-to-gene causal edges | Zero known |
| Other setting-to-causality inflation | Zero known after direct review |
| Metadata outside saved evidence | Zero known after direct review |
| Dual DM-rat/HG-HUVEC setting | **Not preserved**; all four expression observations omitted |
| Original ten 11U findings | Preserved with identical supplied endpoint IDs and directions |
| 11U AST/ALT | Two explicit cohort-specific ratios; one additional aggregated graph edge |
| 11U topology | No gene-to-gene cohort substitution, measurement-to-subject reversal, unsupported context edges or duplicate explosion |
| EZH2 maintenance outcomes | Preserved in effects on [10,11], correcting the 12B loss |
| Overall richness | **Failed**; explicit effects preservation regressed |

Indices are zero-based in each saved normalized relation array.

## Rich-field diagnostics

For **60 conservatively matched findings across all three outputs**, the number
of relations with each populated field is:

| Output | Intervention | Effects | Context |
|---|---:|---:|---:|
| 12A / 11U control | 24 | 12 | 29 |
| Failed 12B | 23 | 26 | 34 |
| 12B-R | 23 | 7 | 30 |

Two otherwise-matched 12B relations with known evidence-locality violations are
excluded, as are unsupported causal additions, unpaired findings, changed
topologies and narrowed findings. Exact three-way indices are in each case's
`comparison.json`. Equivalence is reviewer judgment, not accepted gold.

Across all emitted records, including known failed-12B edges/values, the same
intervention/effects/context counts are control **28/14/38**, 12B **35/38/58**,
and 12B-R **26/11/36**. These are diagnostics, not quality scores.

| Case | Control relations | Failed 12B | 12B-R | Control → refined graph edges |
|---|---:|---:|---:|---:|
| SFPQ / PMC11824863 | 13 | 13 | 11 | 13 → 11 |
| Cbl / PMC8605525 | 26 | 33 | 23 | 25 → 20 |
| EZH2 / PMID27172794 | 20 | 20 | 19 | 18 → 17 |
| PTEN / PMID33652126 | 7 | 11 | 6 | 6 → 5 |
| 11U passage_001 | 10 | 12 | 12 | 10 → 11 |

## Material findings, losses and grounding

- **SFPQ:** APP/Tau reduction, GST/HO-1 upregulation, Bcl-2/Bax and PI3K/AKT
  phosphorylation ratios remain in assertions, but all seven outcome `effects`
  fields are empty. The explicit recognition/memory improvement is omitted,
  along with AAV hippocampal overexpression setup. No near-duplicate title edge.
- **Cbl:** JAK2/STAT4 recovery is faithful to the joint intervention; Runx3
  remains. The four expression observations in DM rat tissues and HG-induced
  HUVECs are omitted, so avoiding glucose causal inflation does not establish
  successful recall/context preservation. Runx3 effects now include abrogation
  of Cb1's endothelial-function effect. One predicate loses `appears` while its
  assertion preserves that qualification; see the review flag.
- **EZH2:** CCS expansion, advanced-stage high expression, knockdown results,
  initiating capacity, pathway activation, maintenance and EPZ-6438 prevention
  remain represented. The tumor-tissue high-expression and poor-prognosis
  relations are omitted. Maintenance effects are retained and title pathway
  expansion is enriched, but several knockdown/progression effects fields and
  the EPZ-6438 intervention are emptied. Patient-to-EZH2 high expression and
  p21cip1 requirement topology differ from control; assertions retain the
  source's qualifications. No patient-to-CRC co-occurrence edge.
- **PTEN:** Required increased-expression finding is absent. The broader PTEN
  cytotoxicity and PI3K/AKT mechanism remain, without a self-edge. PI3K inhibitor
  reversal narrows to ROS; apoptosis/DNA-damage/proliferation reversal outcomes
  are no longer represented in its assertion/metadata.
- **11U:** All ten original findings preserve endpoints and direction. Cohort,
  plasma and timing fields are evidence-local. Liver/hyperglycemic setting is
  omitted from the droplet/infiltration relations instead of imported from the
  absent preceding sentence. The Cystatin C evidence includes the timing and
  result sentences contiguously. Both AST/ALT ratio findings are defensible.

No known 12B-R unsupported field values or evidence-locality violations were
identified. The failed 12B controls retain four unsupported glucose causal
edges and two relations whose assertion/context depend on text outside evidence;
these are explicitly flagged, not credited as improvement.

## Verification and limits

170 Python tests passed, including all 25 background lifecycle/configuration,
polling/cancellation and transport cases. Thirteen viewer adapter tests passed.
All ten control/refined graphs pass the unchanged adapter/Cytoscape conversion,
including direction, evidence, rich fields, hidden/revealed nodes and JSON
immutability. Graph replay and rich-evidence propagation are exact; normalized
exact duplicates are zero. Logs and hashes are preserved in `validation/` and
`verification.json`. No new browser interaction test was performed.

Every refined relation was directly reviewed against its saved evidence.
`evidence_locality_review.json` records exact contiguous offsets, all populated
field values, literal diagnostics and semantic judgments. Substring checks do
not prove entailment. Review is by the primary agent, not independent
adjudication; one completion per case cannot isolate sampling variability.
Duplicate counts describe normalized outputs, not unknown raw records removed
by validation.

The package preserves all prompts, five inputs, saved controls and failed-12B
outputs, new outputs and attempt events, telemetry, graphs, comparisons and
scientific review. Harness behavior is reused from the preserved 12B runner;
the replacement remains report-local. No architecture/product change was made.
Normal commit/push delivery and its final SHA are verified in the completion
response; no history is rewritten.
