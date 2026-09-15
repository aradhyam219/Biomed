# V0-A Biomedical Extractor — Comprehensive Report for Talia

Status: V0-A implemented and ready for review; the broader `extraction_system` project remains active and incomplete.

Requested and authorized by: **Ren Kaizel / Aradhya Majumder**.

This implementation and environment-management work was performed at their explicit request. During the environment follow-up, Ren Kaizel / Aradhya Majumder clarified that `extraction_system` is still under active development and that no working project assets should be removed. That instruction was followed.

## Delivered implementation

- Added the production package under `src/biomedical_extractor/`.
- Implemented the real zero-shot pipeline:
  - ordinary biomedical text;
  - GLiNER-BioMed entity extraction;
  - validated character-span to GLiREL token-span handoff;
  - GLiREL relation extraction;
  - directional relation mapping back to normalized entity IDs;
  - serializable normalized entities and relations.
- Preserved entity text, type, character offsets, and confidence.
- Preserved relation source, target, type, direction, and confidence.
- Added finite configurable entity/relation schemas and confidence thresholds.
- Kept entity-only and relation-with-supplied-entities paths independently usable.
- Added the package CLI and a root-level human-facing `demo.py`.
- Added focused boundary/configuration tests.
- Updated `AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`, and `docs/product/CURRENT_SPEC.md` to match repository truth.
- Did not add BioRED evaluation, fine-tuning, an API, a frontend, or any other excluded subsystem.

## Dependency and reproducibility state

The project contains and retains:

- `pyproject.toml` as direct dependency and package metadata;
- `uv.lock` as the resolved reproducible dependency lock;
- `extraction_system/.venv` as the current active project environment.

The locked compatibility solution uses released GLiNER/GLiREL packages, pins Transformers to the tested compatible version, and explicitly declares GLiREL's undeclared `loguru` dependency plus the DeBERTa tokenizer's `protobuf` requirement. No runtime monkey patch is used.

`uv lock --check` and `uv sync --locked` both succeed against the current files.

## Shared tooling configured

- Installed `uv 0.12.13` at `C:\Users\Aincrad Empirium 3\.local\bin\uv.exe`.
- Added `C:\Users\Aincrad Empirium 3\.local\bin` to the user PATH. A newly opened terminal can use `uv` directly.
- Installed a shared uv-managed Python 3.11.16 runtime at `C:\Users\Aincrad Empirium 3\AppData\Roaming\uv\python\cpython-3.11.16-windows-x86_64-none\python.exe`.
- Confirmed that global uv discovers that managed Python directly.
- Confirmed that commands run from `extraction_system` still select `C:\Projects\Biomed\extraction_system\.venv\Scripts\python.exe`.
- Confirmed normal demo execution can use the shared user Hugging Face model cache.

An optional Python launcher and minor-version junction created during shared-runtime setup were unusable on this Windows installation. Only those newly created broken aliases were removed. The working shared Python runtime was retained and is discoverable by uv.

## Assets deliberately retained

No active or potentially useful project environment/cache was deleted after the project-status clarification.

- `C:\Projects\Biomed\extraction_system\.venv` remains intact and working (approximately 0.93 GiB).
- `C:\Projects\Biomed\extraction_system\.cache\uv` remains intact (approximately 0.91 GiB).
- `C:\Projects\Biomed\extraction_system\.cache\huggingface` remains intact (approximately 1.63 GiB).
- `C:\Projects\Biomed\extraction_system\.python` remains intact (approximately 0.07 GiB).
- `C:\Projects\Biomed\extraction_system\.tools` remains intact (approximately 0.04 GiB).
- The older `C:\Projects\Biomed\.venv` remains present (approximately 3.53 GiB), although it is currently nonfunctional because its original base Python executable no longer exists.

The retained local tooling/caches can be reconsidered only after the project is no longer active or Ren Kaizel / Aradhya Majumder explicitly requests cleanup.

## Verification completed

### V0-A implementation verification

- Nine focused tests passed for normalized serialization, source offsets, entity-to-GLiREL span conversion, relation direction, schema enforcement, invalid relation references, duplicate entity IDs, empty input, and relation extraction with supplied entities.
- Python compilation, package import, CLI help, and lockfile consistency passed.
- Both real model checkpoints loaded successfully on CPU.
- Representative end-to-end inference detected `BRCA1` at `[0, 5)` and `breast cancer` at `[57, 70)` and produced directional relations referencing valid normalized entity IDs.

### Human-facing demo verification

The exact documented command was run successfully:

```powershell
uv run python demo.py
```

Representative text was entered and terminated with `END`. The demo displayed the original input, readable entity rows, readable directional relation rows, and the exact normalized JSON produced by the existing pipeline.

### Environment verification

- Global `uv --version`: passed (`0.12.13`).
- `uv lock --check`: passed.
- `uv sync --locked`: passed; 60 installed packages were checked without replacing the active environment.
- `uv run python` resolved to the project-local `extraction_system/.venv` interpreter.
- Shared uv-managed Python 3.11.16 executes and is discoverable by global uv.
- Both `extraction_system/.venv` and the older `Biomed/.venv` remain present.

## Current commands

From `C:\Projects\Biomed\extraction_system` in a newly opened terminal:

```powershell
uv sync
uv run python demo.py
uv run python -m unittest discover -s tests -v
```

For the interactive demo, paste or type biomedical text and enter `END` on a new line.

## Remaining risks and follow-up boundaries

- The repository changes are still uncommitted.
- The broader extraction project is not complete; this report covers the V0-A milestone and environment follow-up only.
- GPU execution has not been validated; the real pipeline was verified on CPU.
- Extraction quality and production thresholds remain intentionally untuned.
- BioRED evaluation was explicitly excluded and has not started.
- The older `Biomed/.venv` is retained but broken. It should be removed only after an explicit cleanup decision confirms it is no longer needed.
- Project-local caches currently duplicate some shared-cache content, but were retained because the project is active.

## Material files

- `demo.py`
- `pyproject.toml`
- `uv.lock`
- `src/biomedical_extractor/pipeline.py`
- `src/biomedical_extractor/cli.py`
- `tests/test_pipeline.py`
- `AGENTS.md`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/product/CURRENT_SPEC.md`

## Recommended next action

Talia should review the V0-A working tree and this report. If the milestone is accepted, commit the current changes before starting any separately scoped BioRED/evaluation work. Storage cleanup should remain deferred while `extraction_system` is actively being developed.
