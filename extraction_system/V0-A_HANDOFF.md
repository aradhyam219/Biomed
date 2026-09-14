# V0-A Working Biomedical Extractor — Active State

Status: ready-for-review

## Goal

Deliver the smallest working GLiNER-BioMed to GLiREL zero-shot extraction pipeline with normalized, serializable output.

## Completed

- Added the `biomedical_extractor` package with entity-only, relation-with-supplied-entities, and end-to-end extraction paths.
- Added strict character-span to GLiREL token-span conversion and directional relation-to-entity-ID mapping.
- Added configurable finite entity/relation schemas, thresholds, model checkpoints, and device selection.
- Added a runnable CLI demo, project dependency metadata, and a resolved lockfile.
- Added the root-level interactive `demo.py` presentation entry point.
- Declared GLiREL's missing `loguru` and DeBERTa tokenizer `protobuf` runtime dependencies; pinned the compatible released model stack without monkey patching.
- Updated repository navigation, current architecture, and current product wording.
- Kept all implementation work inside `extraction_system`; no BioRED evaluation or excluded subsystem was added.

## Verification already completed

- `uv run python -m unittest discover -s tests -v`: 9 focused tests passed.
- Python compilation, package import, JSON serialization, CLI help, and `uv lock --check` passed.
- Both real checkpoints loaded successfully on CPU.
- Representative end-to-end inference detected `BRCA1` at `[0, 5)` and `breast cancer` at `[57, 70)`, and returned relations whose source/target IDs resolved to those entities.
- `uv run python demo.py` completed successfully with pasted representative input and displayed readable entities, relations, and the normalized JSON result.

## Outstanding

- The working-tree changes have not been committed.
- GPU execution was not exercised; the verified project environment used CPU PyTorch.
- Extraction quality and production thresholds remain intentionally untuned. BioRED evaluation belongs to a later task.

## Next action

Review the V0-A working tree and, if accepted, commit it before starting a separately scoped evaluation task.

## Material files

- `src/biomedical_extractor/pipeline.py`
- `src/biomedical_extractor/cli.py`
- `demo.py`
- `tests/test_pipeline.py`
- `pyproject.toml`
- `uv.lock`

## Authoritative references

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/product/CURRENT_SPEC.md`
- `README.md`
