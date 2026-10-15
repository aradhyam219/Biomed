# Provisioning the accepted dual runtime

Run commands from the delivery checkout's `extraction_system` directory on
Windows. Install uv and use Python 3.11.16. No research cache or virtual
environment is required or copied.

```powershell
uv sync --locked --python 3.11.16 --cache-dir .cache/uv-independent
./provisioning/provision_hunflair2.ps1
uv run --locked python -m unittest discover -s tests -v
node --test viewer/tests/adapter.test.mjs
uv run --locked biomedical-ner --text "BRCA1 is associated with breast cancer." --offline
```

The main `uv.lock` keeps baseline versions of retained provider dependencies.
The isolated environment installs the exact accepted package inventory from
`provisioning/hunflair2-requirements.txt` without resolving alternate dependency
versions. This intentionally preserves the existing runtime, including its
legacy SciSpaCy/spaCy dependency combination, rather than upgrading it during
cleanup. `hunflair2-installed.json` records the observed baseline inventory.
This original recipe is Windows-specific. The Linux/CUDA additions and its
separate profile are described below; the original CPU inventory remains intact.

`provision_models.py` downloads HunFlair2 revision
`3af2b8972f7af2910ce8d9ae724da09b3d7a166c`, verifies its SHA-256 against
`baseline.json`, and loads the model and official SciSpaCy splitter to provision
any required tokenizer state inside the delivery cache. Model/runtime caches
are ignored and can be reacquired. HunFlair2 uses a separate environment because
its Pydantic/spaCy/transformers requirements differ from the main provider runtime.

Supply `OPENAI_API_KEY` externally. The application reads environment settings;
`.env.example` documents non-secret relation defaults but is not automatically
loaded. Do not commit secrets or copy the research `.env`. `OPENAI_BASE_URL` and
`OPENAI_API_KEY_ENV` can configure an external provider connection. Default model,
reasoning, background mode, service tier, finite repair budget, poll interval and
generation timeout for current delivery are recorded in the packaged Luna
profiles and `reports/phase2/luna-freeze.json`. `baseline.json` preserves the
original historical CPU/Sol freeze and must not be relabeled as Luna.

```powershell
uv run --locked biomedical-extract-llm --text "BRCA1 is associated with breast cancer." --output-format graph --document-id smoke --hunflair2-offline
```

This live command may invoke both relation and degree-zero role providers. Run it
only after deterministic checks. Provider generation is variable: a live smoke
proves integration, not exact graph equivalence. The saved stage fixtures are the
primary behavior-preservation gate. The graph CLI emits versioned Graph Contract v1 through the export boundary
(see GRAPH_CONTRACT.md); raw GraphResult serialization remains available. The
existing viewer consumes both shapes without a backend change; serve it with Python's HTTP server as described
in the product specification.

## Baseline identities

`baseline.json` records the immutable Git anchor, original lock digest, prompts,
semantic schemas, runtime/model identities and representative fixture digests.
Its source-byte hashes describe the research working files at freeze time;
Git checkout CRLF/LF differences must be normalized when comparing source text.
The baseline tag is the authoritative committed source. No fixture is scientific gold.

## Phase 2 CPU identity evidence

The fresh seven-input CPU capture initially failed because installed PyTorch
release metadata reports `2.14.0`, while the inference module reports `2.14.0+cpu`.
The CPU identity amendment corrects verification, without reinstalling or changing
that runtime: this exact pair requires actual CPU execution, CUDA runtime null
and CUDA unavailable. Live release evidence is read from the same isolated
interpreter selected for inference. Retained evidence uses its captured isolated
inventory. Other builds/releases and missing or contradictory corroboration fail.

The existing retained run now passes corrected revalidation; its original failed
capture event remains unchanged. `reports/phase2/cpu-revalidation.json` records
success separately from historical `cpu-reference.json` and ignored `run.json`.
The original CPU descriptor, canonical identity and protected scientific modules
are unchanged. No NER rerun, model download, dependency reinstall or provider
submission was used for this correction.

Python-source attestations decode UTF-8 with an optional BOM removed, normalize
CRLF and CR to LF, encode UTF-8 without a BOM and then hash with SHA-256. Capture
and revalidation tools each record a separate normalized-source identity and
byte identity. This convention applies only to Python-source attestation:
scientific text/title identities, Graph Contract fingerprints and raw-output
hashes preserve their existing exact-input/byte rules.

## Existing Linux/CUDA host

The AWS host is provisioned and real T4 CUDA execution is proven. Its isolated
Python 3.11.16 inventory matches the complete CPU inventory, plus exactly
`nvidia-cusparselt-cu13==0.8.1` and `nvidia-nvshmem-cu13==3.4.5`. These additions
are recorded in `hunflair2-linux-cuda-requirements.txt`, which includes the
unchanged base requirements. It uses PyTorch distribution 2.14.0, actual module
2.14.0+cu130 and CUDA runtime 13.0. Keep the two environments isolated.

For a fresh Linux environment, create `.cache/hunflair2/runtime` with Python
3.11.16 and install the Linux requirements with `uv pip install --no-deps
--python .cache/hunflair2/runtime/bin/python -r
provisioning/hunflair2-linux-cuda-requirements.txt`. Use the existing artifact
provisioner to acquire/verify the same pinned model. Do not reinstall or repeat
the seven-case NER study on the already provisioned execution host.

Current relation and naturally invoked role requests use Luna/max/Fast background
Responses, two output repairs per task, 128000 output tokens, 3-second polls and
a 900-second deadline; SDK retries remain disabled. Prompt and both schema
identities are verified against the recorded Contract 14R evidence before live
execution. Requested `fast` and observed `priority` remain distinct diagnostics.
The composed Linux/CUDA smoke and profile promotion are gated in
`../reports/phase2/README.md`. Development tooling/evidence stay outside the client
package; no container or new serving infrastructure is introduced.

An existing `.env` can still explicitly override those defaults. The execution
host's old file selects Sol/medium/default; do not mistake that external override
for the current freeze. The composed smoke loads only the existing credentials
from that file, then explicitly binds `BIOMEDICAL_RELATION_MODEL=gpt-5.6-luna`,
`BIOMEDICAL_RELATION_REASONING_EFFORT=max` and
`BIOMEDICAL_RELATION_SERVICE_TIER=fast` in its execution environment. The runner
rejects any remaining frozen-setting mismatch before inference/submission.
