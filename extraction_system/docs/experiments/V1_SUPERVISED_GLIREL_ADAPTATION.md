# V1 — Supervised GLiREL Biomedical Adaptation

## Experiment status

| Stage | Status | Evidence |
|---|---|---|
| V1-A — BioRED Training Preparation | **Completed and verified locally** | Deterministic Train conversion, 512-token preflight, native-collator negative-label test, provenance check, and reproducibility checks passed. |
| V1-B — GPU Fine-Tuning & Evaluation | **Pending V1-B1 smoke rerun after diagnostic correction** | The first AWS smoke stopped during optimizer construction; the post-optimizer attempt reached forward/backward but exposed ambiguity in the old one-scalar update check. |

This is the one living report for V1. It records the prepared experiment now and
will be updated with the actual GPU progression, selected checkpoint, Dev metrics,
and conclusion after V1-B. Planned or pending items are not results.

## Objective and research question

V1 tests whether supervised adaptation of the accepted pretrained checkpoint
`jackboyla/glirel-large-v0` can materially improve biomedical relation extraction
when BioRED gold entities are supplied. The direct comparison target is the
accepted zero-shot V0-B relation baseline. The experiment deliberately isolates
relation extraction; it is not an end-to-end NER+RE experiment and does not change
the production extraction contract.

Research question:

> Can supervised BioRED fine-tuning make `jackboyla/glirel-large-v0` materially
> better at biomedical relation extraction?

## Accepted V0-B baseline

The baseline is the tracked **BioRED development complete-fit baseline**, not a
full or official BioRED development score. It evaluates 99 / 100 Dev documents;
PMID `19880293` is the one authorized exclusion because exact supplied-entity
tokenization produces 554 tokens against the checkpoint's 512-token limit. The
baseline uses gold entities, non-directional concept-level aggregation, `top_k=1`,
and a Dev-calibrated threshold of `0.14250895380973816`.

| Metric | Precision | Recall | F1 |
|---|---:|---:|---:|
| Pair-only | 0.2212 | 0.4775 | 0.3023 |
| Typed micro | 0.1322 | 0.2855 | 0.1807 |

At the accepted operating point, pair-only counts are `TP=552, FP=1944,
FN=604`; typed counts are `TP=330, FP=2166, FN=826`.

The baseline per-label results are retained here so V1-B can be compared on the
same units:

| Relation | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Association | 557 | 0.1391 | 0.5404 | 0.2212 |
| Positive_Correlation | 349 | 0.1695 | 0.0287 | 0.0490 |
| Negative_Correlation | 216 | 0.1026 | 0.0556 | 0.0721 |
| Bind | 19 | 0.1111 | 0.1579 | 0.1304 |
| Conversion | 0 | 0.0000 | N/A | N/A |
| Drug_Interaction | 0 | 0.0000 | N/A | N/A |
| Comparison | 5 | 0.0857 | 0.6000 | 0.1500 |
| Cotreatment | 10 | 0.0167 | 0.1000 | 0.0286 |

Authoritative baseline files are `docs/EVALUATION.md` and
`reports/biored_v0b_complete_fit.json`. V0-B behavior and its fixed default
checkpoint remain unchanged by V1-A.

## Dataset source, split policy, and hashes

The local corpus is the official NCBI BioRED release already used by V0-B. Its
metadata is `source=PubTator`, `date=2021-11-30`, and `key=BioC.key`. The local
ignored archive and split files are under `.cache/` and are not repository source.

| Artifact | Documents | Gold relations | SHA-256 |
|---|---:|---:|---|
| Local `BIORED.zip` | — | — | `c3032230bd89d22a0923d0df6ae943bc8ea37fba7e42da7a8dec21bac02d47` |
| `Train.BioC.JSON` | 400 | 4,178 | `53e08e0acff5043937cdd3fdb595639e59bfb0390b64760a3840f6e1a2a69987` |
| `Dev.BioC.JSON` | 100 | 1,162 | `d5ab4d05673ac46fb5e3b2904d2820462dec2c4c50dfcdd8678635ff1b8ce1f5` |
| `Test.BioC.JSON` | 100 | 1,163 | `35ec8aad0c62032689b4a957220c7532eb067dc7e159d70cc42e6d40e6c447c6` |

The Dev digest exactly matches the required verified hash. The code refuses to
prepare V1-A against a sibling Dev file with a different digest.

Split isolation is fixed:

- BioRED Train supplies supervised training examples only.
- BioRED Dev is reserved for checkpoint selection, threshold calibration, and the
  V0-B-compatible comparison.
- BioRED Test is untouched by V1-A and remains reserved for a later explicitly
  authorized final evaluation.

## BioRED-to-GLiREL supervision methodology

The implementation reuses the existing BioRED parser, concept-ID normalization,
entity-type normalization, relation-label schema, allowed relation-bearing entity
families, and exact supplied-entity tokenization from V0-B. The only supervised
adaptation is the document-level-to-mention-level projection required by GLiREL:

1. Keep only `Gene`, `Disease`, `Chemical`, and `Variant` mentions.
2. For each gold concept relation `Concept A --R-- Concept B`, collect every
   eligible mention containing A and every eligible mention containing B.
3. Emit the complete A-mention × B-mention cross-product with relation label R.
4. Emit both ordered directions because BioRED scoring is non-directional while
   GLiREL represents ordered mention pairs.
5. Deduplicate identical `(head token span, tail token span, relation label)`
   records deterministically.

BioRED's canonical labels remain authoritative for provenance, statistics, and
reporting. The GLiREL-facing `relation_text` values and fixed example `label`
lists use the exact human-readable prompts in `CANONICAL_TO_PROMPT`, the same
prompt text passed by V0-B/V1 evaluation. Each generated positive also carries
the canonical relation type and a `source_gold_relation` diagnostic record. The
native GLiREL collator ignores those extra provenance fields, while the
preparation validator checks that every positive's document, concept pair, and
canonical label occur in parsed BioRED gold truth and that its prompt is the
corresponding mapped label. No evidence-sentence selection, mention ranking,
multiple-instance learning, or hard-negative mining is used.

Because GLiREL 1.2.1 sorts `example["label"]` inside its native supervised
collator, the in-memory loader boundary supplies `str`-compatible prompt values
whose native sort follows the inference order. The serialized JSONL remains plain
prompt text; the actual collated `classes_to_id` order is tested directly.

### Token and span conventions

The converter calls the same token pattern and exact character-boundary splitting
used by V0-B (`\w+(?:[-_]\w+)*|\S`). Entity spans in generated JSONL are GLiREL's
inclusive token indices, for example `[7, 7]` for a one-token mention. BioRED
character spans remain half-open during parsing. No mention is widened or silently
remapped. Documents over 512 converted tokens are excluded before generation;
there is no truncation or chunking.

### Native negative supervision

The installed `glirel==1.2.1` implementation was inspected directly. Its native
`InstructBase.collate_fn` generates ordered non-self entity pairs, and
`get_rel_labels` assigns label `0` when a pair is absent from the supplied gold
relation map. `GLiREL.forward` converts those zeros to negative one-hot targets and
includes them in `binary_cross_entropy_loss`. V1 exposes all eight fixed
human-readable prompt labels in every example, so absent labels/pairs are explicit
negative supervision.

The focused test `test_native_collator_assigns_zero_to_unlabeled_pairs` verifies
this behavior without loading the large checkpoint. Prompt-label alignment is
covered separately for the converter, native training loader, and inference
configuration. The upstream GLiREL training loop and cosine-warmup configuration
were also inspected in the official [GLiREL `train.py`](https://github.com/jackboyla/GLiREL/blob/main/train.py);
V1 uses the package's native collator and a repository-owned AdamW builder that
matches the upstream named-parameter grouping.

## V1-A measured Train preparation

The measured statistics below were generated from the verified local Train file by
`biored-v1 prepare`.

### Corpus and exclusion coverage

| Quantity | Measured value |
|---|---:|
| Train documents in source | 400 |
| Fitting documents | 394 |
| Excluded documents | 6 |
| Document coverage | 98.5000% |
| Gold relations in source | 4,178 |
| Gold relations in fitting documents | 4,123 |
| Gold relations in excluded documents | 55 |
| Gold-relation coverage | 98.6836% |
| All parsed mentions | 13,351 |
| Eligible relation-bearing mentions | 11,819 |
| Fitting-document mentions | 12,994 |
| Fitting eligible mentions | 11,511 |
| Token length minimum / mean / maximum | 47 / 292.805 / 641 |

The exact deterministic over-limit exclusions are:

| PMID | Tokens | Gold relations |
|---|---:|---:|
| `11773892` | 513 | 6 |
| `17595233` | 553 | 7 |
| `24623966` | 587 | 12 |
| `15630069` | 637 | 17 |
| `17379047` | 641 | 7 |
| `19923525` | 622 | 6 |

The exclusion is a V1 training-preparation policy for this 512-token checkpoint.
The documents are not truncated, chunked, or counted as false-negative model
predictions.

### Gold relation counts by label

| Relation | Source | Included | Excluded |
|---|---:|---:|---:|
| Association | 2,192 | 2,178 | 14 |
| Positive_Correlation | 1,089 | 1,070 | 19 |
| Negative_Correlation | 763 | 745 | 18 |
| Bind | 61 | 61 | 0 |
| Conversion | 3 | 3 | 0 |
| Drug_Interaction | 11 | 11 | 0 |
| Comparison | 28 | 24 | 4 |
| Cotreatment | 31 | 31 | 0 |
| **Total** | **4,178** | **4,123** | **55** |

### Generated positive mention relations

The counts below are ordered mention-span positives after cross-product expansion,
bidirectional expansion, and deterministic span-pair/label deduplication. They are
not counts of distinct BioRED concept relations.

| Relation | Generated positives |
|---|---:|
| Association | 74,202 |
| Positive_Correlation | 39,820 |
| Negative_Correlation | 30,238 |
| Bind | 2,854 |
| Conversion | 10 |
| Drug_Interaction | 656 |
| Comparison | 1,584 |
| Cotreatment | 1,498 |
| **Total** | **150,862** |

There are 394 generated document examples; five contain no positive relation and
therefore contribute only native negative pair supervision. The provenance audit
checked all 150,862 serialized positives: `150,862 valid`, `0 invalid`.

The converter recorded 101 same-mention/same-span cross-product cases that GLiREL
1.2.1 cannot represent because its native pair generator excludes self-pairs or
cannot distinguish duplicate spans. They are surfaced in `biored_train_stats.json`
and omitted from the representable positive list; no blanket self-pair filter is
applied to evaluation. No fitting gold relation had an unresolved eligible mention
endpoint.

## Pretrained checkpoint and training configuration

The exact starting checkpoint is:

```text
jackboyla/glirel-large-v0
```

The package is pinned to `glirel==1.2.1`. The first supervised configuration is:

| Setting | Value |
|---|---|
| `lr_encoder` | `1e-5` |
| `lr_others` | `1e-4` |
| `weight_decay_encoder` | `0.01` |
| `weight_decay_other` | `0.01` |
| `warmup_ratio` | `0.1` |
| `scheduler` | `cosine_with_warmup` |
| `loss_func` | `binary_cross_entropy_loss` |
| `fine_tune` | `true` |
| `refine_prompt` | `false` |
| `refine_relation` | `false` |
| `max_len` | `512` |
| `top_k` | `1` |
| `fixed_relation_types` | `true` |
| `random_drop` | `false` |
| `num_unseen_rel_types` | `0` |
| `train_batch_size` | `1` |
| `gradient_accumulation` | `8` |
| mixed precision | FP16 |
| initial `num_steps` | `4,000` microsteps |
| checkpoint save interval | `1,000` microsteps; final save is separate |
| seed | `0` |

The `4,000`-microstep setting is intentionally the first evidence-gathering
viability run, not a sweep or an asserted optimum. With gradient accumulation of
8, the scheduler has 500 optimizer-update steps and 50 warmup steps; `scheduler.step()`
runs once per optimizer update. Periodic checkpoints are saved at microsteps
1,000, 2,000, and 3,000; the 4,000-step boundary is represented by the single
`final` save rather than a duplicate `step_4000` directory. Entity markers are
disabled in the runner so the measured 512-token preflight remains the model input
length.
No GPU training was run locally.

The later target hardware is one Tesla T4 with 15,360 MiB VRAM. The batch size,
gradient accumulation, and FP16 settings are starting defaults for that hardware,
not a general hardware-tuning framework.

The GPU smoke path selects the fitting example with the largest estimated ordered
non-self entity-pair workload, breaking ties by token length and document ID. It
resets CUDA peak counters, performs a finite forward/loss check, uses the enabled
FP16 scaler for backward and optimizer update, explicitly unscales once, validates
the complete gradient set and global norm, and verifies execution through optimizer
state reaching step 1. It records scaler scales, synchronized stage timings, and
peak allocated/reserved CUDA memory before post-step validation. It does not clone a
full trainable parameter or infer update execution from one floating-point element.
These are implementation checks for the AWS smoke gate; the measured attempts are
recorded below.

## Implementation and reproducibility

### Files changed for V1-A

- `src/biomedical_extractor/biored.py` — reuse the existing parser while allowing
  isolated Train/Dev/Test file resolution.
- `src/biomedical_extractor/biored_training.py` — deterministic converter,
  preflight/statistics/provenance checks, V1 config, native GLiREL smoke/training
  runner, and generated-artifact CLI.
- `src/biomedical_extractor/biored_cli.py` — optional local-checkpoint evaluation
  using the unchanged V0-B concept-level aggregation and metrics; default behavior
  remains V0-B.
- `tests/test_biored_training.py` — converter, exclusion, split, provenance,
  prompt-label alignment, native negative-label, smoke-selection, scheduler,
  gradient/update/timing diagnostics, training-schedule, and runner-construction
  tests.
- `tests/test_biored_cli.py` — custom-checkpoint cache/report isolation coverage.
- `pyproject.toml` — `biored-v1` command entry point.
- `docs/ARCHITECTURE.md` — current structural boundary for supervised adaptation.
- `docs/EVALUATION.md` — V0-B default and V1 local-checkpoint evaluation boundary.
- `docs/experiments/V1_SUPERVISED_GLIREL_ADAPTATION.md` — this living report.

Generated Train JSONL, statistics, caches, and future checkpoints remain under
ignored `.cache/`; no generated dataset or model artifact is intended for Git.

### Commands

From the repository root, local deterministic preparation is:

```powershell
uv run biored-v1 prepare `
  --dataset .cache/BIORED `
  --output-dir .cache/v1/biored_train
```

The preparation command verifies the sibling Dev SHA-256 before reading Train and
writes `biored_train_glirel.jsonl`, `biored_train_stats.json`, and
`v1_training_config.json` under the ignored output directory.

The exact later AWS commands use Ubuntu/bash syntax:

```bash
# GPU smoke test: one native GLiREL forward/backward pass; no long training.
uv run biored-v1 smoke \
  --training-jsonl .cache/v1/biored_train/biored_train_glirel.jsonl \
  --checkpoint jackboyla/glirel-large-v0 \
  --device cuda \
  --mixed-precision fp16

# First viability run: save step_1000, step_2000, step_3000, and final.
uv run biored-v1 train \
  --training-jsonl .cache/v1/biored_train/biored_train_glirel.jsonl \
  --checkpoint jackboyla/glirel-large-v0 \
  --output-dir .cache/v1/checkpoints \
  --device cuda \
  --steps 4000 \
  --save-every 1000 \
  --mixed-precision fp16 \
  --seed 0

# Evaluate a selected local fine-tuned checkpoint on the complete-fit Dev split.
uv run biored-evaluate \
  --dataset .cache/BIORED \
  --split dev \
  --checkpoint .cache/v1/checkpoints/final \
  --cache .cache/v1/biored_dev_raw.json \
  --output .cache/v1/biored_dev_summary.json \
  --device cuda \
  --offline
```

If the AWS machine has not prepared the ignored JSONL yet, run the preparation
command first. The evaluation command reports pair precision/recall/F1, typed
precision/recall/F1, all eight per-label metrics, the selected Dev threshold, and
the same coverage/exclusion diagnostics used by V0-B.

## Validation completed for V1-A

Completed locally without loading the large checkpoint or starting GPU work:

- verified the required Dev SHA-256 and recorded Train/Dev/Test/archive hashes;
- parsed all 400 Train documents and completed deterministic 512-token preflight;
- generated all fitting JSONL examples and exact label statistics;
- verified every generated positive against parsed BioRED gold truth;
- regenerated the corrected corpus twice and confirmed identical JSONL and
  statistics SHA-256 values (`E1ECF8985114CCC756A87CECE699F76123AB6489D42B8308FFA71AE750B91C51`
  for JSONL and `AE91907822E47D94E1C2179AB4DCFAFC73B6BF0E2C953B907090ADAD3B2FBA0F`
  for statistics);
- passed the full test suite: 35 tests, including the BioRED/CLI/training-focused
  tests and the native negative-supervision check;
- passed Python compilation and `git diff --check`;
- constructed a training plan without checkpoint loading;
- added and tested local-checkpoint evaluation plumbing without running inference;
- did not modify the accepted V0-B report or run V0-B inference.
- did not run the GPU smoke path or any GPU training locally.

## Material problems and resolutions

The installed GLiREL package provides the model, collator, and low-level training
primitives but no repository-ready high-level trainer. The runner uses those native
mechanisms and the upstream cosine-warmup loop shape, with repository-owned
configuration and optimizer construction kept limited to the experiment.

The V1-B cross-machine preflight exposed path-dependent metadata in the statistics
artifact. It now records stable filenames/logical identity and SHA-256 values
instead of resolved absolute paths; the training corpus, counts, and behavior are
unchanged.

The Train corpus contains same-mention cross-product cases, including self-concept
and multi-concept annotations. GLiREL's native relation-pair generator excludes
self-pairs, so the converter records 101 such cases and keeps every other
representable direction. This is a documented data limitation, not a new global
candidate constraint. BioRED's legitimate self-concept truth remains available to
the existing non-directional evaluator.

The first measured AWS GPU smoke attempt loaded the checkpoint successfully but
stopped before forward execution because GLiREL 1.2.1's `GLiREL.get_optimizer()`
accessed missing `_rel_filtering`. Exact v1.2.1 source inspection confirmed that
`GLiREL.__init__` does not create `_rel_filtering`, while the official `train.py`
builds AdamW from `model.named_parameters()`, separating `token_rep_layer` from
all other trainable parameters. Repository training now follows that supported
optimizer path. The later post-optimizer attempt is recorded below.

## V1-B1 resume reproducibility gate — **CONFIRMED / PASS** (2026-09-16)

Cross-machine preparation reproducibility is **CONFIRMED / PASS**. The initial
absolute-path issue was corrected; the remaining CRLF/LF serialization issue
was isolated and corrected. At Windows commit
`91ee9149428e39e5eb01b16ff8daaf762a9ad52b`, regeneration produced byte hashes
matching the AWS/Linux regenerated artifacts:

- Training JSONL: `E1ECF8985114CCC756A87CECE699F76123AB6489D42B8308FFA71AE750B91C51`
- Statistics: `AE91907822E47D94E1C2179AB4DCFAFC73B6BF0E2C953B907090ADAD3B2FBA0F`

The 4,000-microstep fine-tuning run and Dev evaluation remain **NOT RUN**.

## V1-B1 GPU smoke — measured blocker; correction pending rerun (2026-09-16)

The AWS runtime preflight passed, but the prescribed smoke command did not reach
the forward pass. The repository was at exact HEAD
`c781085b96c6f9412a0c5f7587531e9bbf1ebe80`. The existing prepared artifacts were
present and matched the confirmed cross-machine hashes without regeneration:

- Training JSONL:
  `e1ecf8985114ccc756a87cece699f76123ab6489d42b8308ffa71ae750b91c51`
- Statistics:
  `ae91907822e47d94e1c2179ab4dcfafc73b6bf0e2c953b907090adad3b2fba0f`

### AWS preflight and smoke evidence

| Field | Result |
|---|---|
| GPU | NVIDIA Tesla T4 |
| Total VRAM | 15,360 MiB (`nvidia-smi`); PyTorch reported 14,912 MiB device capacity |
| Driver | `595.91.07` |
| PyTorch | `2.14.0+cu130` |
| PyTorch CUDA build | `13.0` |
| CUDA available | `true`; one CUDA device visible |
| GPU occupancy before smoke | 0 MiB / 0% utilization; no compute process listed |
| Root disk before smoke | 22 GB free of 78 GB (73% used) |
| Root disk after checkpoint download | 18 GB free of 78 GB (77% used); no disk blocker |
| Checkpoint | `jackboyla/glirel-large-v0` loaded successfully before the failure |
| Smoke FP16 setting | Requested `fp16`; AMP execution not reached |
| Intended smoke document | `30442153` (selected deterministically; not executed) |
| Intended workload | 446 tokens, 71 entities, 4,970 candidate pairs, 1,436 positive relations (not executed) |
| Loss | Not reached |
| Backward | Not reached |
| Optimizer step | Not reached; optimizer construction failed |
| Parameter change | Not reached |
| Peak allocated VRAM | Not measured; the smoke path failed before peak counters were reset/read |
| Peak reserved VRAM | Not measured; the smoke path failed before peak counters were reset/read |
| Attempt wall time | 72.00 seconds, including checkpoint download and startup |

The exact command ran with the required checkpoint, device, FP16 mode, and
prepared JSONL. It failed at `model.get_optimizer(...)` with:

```text
AttributeError: 'GLiREL' object has no attribute '_rel_filtering'
```

The installed `glirel==1.2.1` `GLiREL.get_optimizer` unconditionally calls
`self._rel_filtering.parameters()`, while the loaded model instance has no such
attribute. This is the immediate root cause. No speculative fix was attempted,
and the run stopped before full training.

The compatibility correction enabled the later attempt below. V1-B1 smoke remains
**PENDING RERUN after diagnostic correction**. The 4,000-microstep fine-tuning run
and Dev evaluation remain **NOT RUN**.

## V1-B1 post-optimizer GPU smoke — diagnostic ambiguity; correction pending rerun (2026-09-16)

The second measured AWS attempt ran at exact HEAD
`c2586c40d27aa60a699eb9f01897f3e825c5dfd0`. The exact deterministic worst-workload
selection reached the model execution path:

| Field | Result |
|---|---|
| Smoke document | `30442153` — 446 tokens, 71 entities, 4,970 candidate pairs, 1,436 positive relations |
| Forward execution | Reached |
| Finite-loss validation | Passed |
| Backward | Completed |
| Gradient evidence | A finite, non-zero scaled gradient was found |
| `scaler.step()` | Returned |
| `scaler.update()` | Returned |
| CUDA OOM | None |
| Failure | One sampled parameter scalar was unchanged |
| Attempt wall time | `23m14.897s` |
| Stage timings | Not available in this pre-correction run |
| Peak CUDA memory | Not retained because the old post-step validation raised before the memory read |

This was not a demonstrated training failure. The old smoke could not distinguish
GradScaler skipping the optimizer update because another gradient was non-finite
from the optimizer step executing while the single sampled scalar remained
unchanged. The smoke verification is being corrected to validate all unscaled
gradients, record scaler scale changes, and use AdamW state reaching step 1 as the
execution invariant. V1-B1 remains **PENDING RERUN after diagnostic correction**;
the 4,000-microstep training run and Dev evaluation remain **NOT RUN**.

## V1-B results and checkpoint selection — pending

No successful GPU result exists yet. The following fields must be filled from
actual AWS artifacts after the smoke blocker is resolved and the training run is
authorized:

- hardware/runtime, CUDA/PyTorch versions, wall time, and peak VRAM;
- loss/checkpoint progression at the saved steps;
- selected checkpoint and the Dev selection criterion;
- whether the selected checkpoint was evaluated with a fresh checkpoint-specific
  raw-score cache;
- complete-fit Dev coverage and selected threshold;
- pair-only and typed micro P/R/F1;
- per-label P/R/F1, including Association, Positive_Correlation, and
  Negative_Correlation;
- any relation-label confusion matrix or representative errors retained by the
  evaluation summary.

### Direct V0-B versus V1 comparison — pending

| Metric | V0-B zero-shot | V1 supervised | Delta |
|---|---:|---:|---:|
| Pair-only precision | 0.2212 | pending | pending |
| Pair-only recall | 0.4775 | pending | pending |
| Pair-only F1 | 0.3023 | pending | pending |
| Typed micro precision | 0.1322 | pending | pending |
| Typed micro recall | 0.2855 | pending | pending |
| Typed micro F1 | 0.1807 | pending | pending |
| Association F1 | 0.2212 | pending | pending |
| Positive_Correlation F1 | 0.0490 | pending | pending |
| Negative_Correlation F1 | 0.0721 | pending | pending |

## Remaining failure modes and conclusion — pending V1-B

Known limitations entering V1-B are the 512-token exclusion policy, mention-level
projection of document-level truth, same-span unrepresentable cases, Dev-threshold
selection on the same split used for reporting, and the absence of Test evaluation.
The generated supervision is intentionally simple and may duplicate contextual
mentions; this is part of the research question rather than a hidden optimization.

V1 cannot yet conclude whether GLiREL is viable for this biomedical relation task.
That conclusion must wait for the measured V1-B Dev comparison and must distinguish
material improvement from per-label trade-offs and coverage limitations.
