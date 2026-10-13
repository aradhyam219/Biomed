# Phase 2 compatibility investigation

Disposition: **BLOCKED**. Stage A ends with incomplete prerequisite evidence;
no Linux/CUDA candidate was established or promoted. This is not completion of
Phase 2's CUDA delivery objective.

## Frozen boundary

Started clean on `delivery/extraction-system-v1` at
`e9a3184b9e76f12370657dab5f2a6457807a57c2`. The original CPU descriptor and
all protected scientific files remain unchanged. CPU identity:
`ees-cfeec6ccd400b9f44abbef35551944aa074ee3d79d3e5ec18dd7d7551c76e0de`.
No candidate CUDA descriptor exists. Baseline/delivery tags remain unchanged.
The research checkout was used only for read-only acquisition of the five
specified corpus entries.

`manifest.json` freezes the seven exact inputs, literal IDs, exact titles,
acquisition provenance, strict UTF-8 identities, Graph Contract fingerprints,
accepted configuration, paid subset and smoke case. All seven contract text
hashes match. Maintained fixtures contain sources only, never historical NER
outputs. `scientific-checklist.json` contains exact source slices and review
questions prepared before any paid calls. These are review assets, not gold.

## Actual CPU observation and blocking conflict

One fresh offline multi-document CPU inference completed on all seven sources.
The model revision and artifact digest match the contract. The actual raw output,
normalized Entity values with full scores/order, source inputs, complete installed
inventories, exact capture-wrapper source/digest and run diagnostics remain under the ignored directory identified in
`cpu-reference.json`. All 2,452 normalized mentions resolve exactly to their
source slices and all provided scores are finite.

The accepted descriptor records `ner.runtime.pytorch = "2.14.0"`. Installed
`importlib.metadata.version("torch")` also reports `2.14.0`, but the actual
inference process reports `torch.__version__ = "2.14.0+cpu"`. The existing
`verify_ner_metadata` check rejects this value. All other checked runtime/model
fields match. Distribution metadata and module build identity are distinct
observations; this investigation does not silently equate them.

The raw inference is **not an accepted CPU comparator**. Runtime comparison
stopped at this prerequisite gate. No inference was repeated to seek a matching
result. Fixing or relaxing protected runtime reporting, or changing the original
profile, would conflict with this contract and needs an explicit revised boundary.

## Missing Linux prerequisite

No Linux/NVIDIA target host or connection was supplied. Local WSL inventory
contains only Docker Desktop's internal distribution, which was not used as a
substitute. No infrastructure was allocated and no drivers were modified.
Provider credentials were absent from this process environment; credentials in
the eventual Linux provider runtime remain unverified. No secrets were read or
copied for this investigation.

## Gates and budget

- Phase 1 grounding and canonical-identity regressions: pass (19 Graph Contract tests).
- Frozen fixture/checklist checks: pass (3 tests), including rejection of actual build drift and invalid spans.
- Both saved baseline graph replays, including source-aware v1 validation: exact (1 test covering both).
- Existing viewer checks: pass (14 tests).
- Protected scientific implementation hashes: unchanged and verified.
- Accepted CPU runtime identity: blocked on actual PyTorch build string.
- Linux dual-runtime provisioning, independent artifact acquisition, CUDA execution proof: not run.
- CPU/CUDA NER and relation/role request comparisons: not run.
- Conditional Linux/CPU diagnostics and controlled live scientific review: not run.
- Raw composed Linux/CUDA smoke and installed public CUDA smoke: not run.
- Profile promotion, release identity changes and clean-wheel CUDA verification: not performed.

Provider generation attempts: **0 / 24**. Repairs: **0 / 4**.
`provider-ledger.json` is an empty ledger, not an implemented budget-enforcement
mechanism. Before any future paid submission, enforcement must be installed at
the submission boundary, covering repairs and uncertain/failed submissions.
Unused slots do not authorize different inputs or additional experiments.

No Green/Yellow/Red NER classification or downstream compatibility conclusion is
possible from this evidence. Existing scientific limitations remain unchanged.
No performance or scientific-quality claim follows from mention counts.

## Resume

Resolve the accepted CPU runtime identity conflict under an explicit contract
amendment, and supply one existing Linux/NVIDIA host and its provider credential
mechanism. Inspect retained CPU observations before authorizing any further
capture; do not reconstruct a comparator from saved baseline predictions.
Then continue the original sequence, budget, source selections and review gate.
Explicit approval of the exact tested candidate/evidence is still required
before promotion. Push authorization permits delivery of this blocked evidence;
it does not authorize promotion, release publication or new tags.

Development commands (from the delivery `extraction_system` directory):

```powershell
.venv/Scripts/python.exe tools/phase2_reference.py freeze --corpus C:/Projects/Biomed/extraction_system/.cache/ner_target_domain/target_corpus.json
.venv/Scripts/python.exe tools/phase2_reference.py capture-cpu
.venv/Scripts/python.exe tools/phase2_reference.py inspect-cpu --run-directory .cache/phase2/20261013T103713Z-6ce48f02
.venv/Scripts/python.exe -m unittest discover -s tests -p test_phase2_fixtures.py -v
```

Acquisition is the only command that reads the research cache. Frozen fixtures
and subsequent inference/inspection do not depend on it. `capture-cpu` refuses a
second attempt when a prior run is present. `inspect-cpu` makes no model/provider
calls and does not turn a rejected observation into an accepted comparator.
The existing wheel target packages only `src/biomedical_extractor`; fixtures,
reports and this development tool are outside it. No release wheel was built.
