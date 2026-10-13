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
The recipe is Windows-specific; another OS has not been validated.

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
generation timeout are recorded in `baseline.json`; preserve them for the baseline.

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

## Phase 2 prerequisite evidence

The fresh seven-input CPU observation in `reports/phase2/` is blocked: installed
PyTorch distribution metadata reports `2.14.0`, but the actual inference module
reports `2.14.0+cpu`, which the original immutable v1 descriptor rejects. The
original profile and protected implementations are unchanged. No Linux/CUDA
configuration has been provisioned, verified or promoted; an existing target host
and resolution of the CPU identity conflict are required before comparison.
Development fixtures/tooling remain outside the client package. See
`../reports/phase2/README.md` for retained evidence and the explicit resume boundary.
