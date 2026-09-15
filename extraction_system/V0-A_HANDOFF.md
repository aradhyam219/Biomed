# V0-A Working Biomedical Extractor — Active State

Status: superseded by `V0-B_HANDOFF.md`

V0-A remains the production baseline. Continue current work from
`V0-B_HANDOFF.md`; this file is retained only as the completed V0-A state.

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
- Committed the V0-A implementation on branch `extraction_system` as `0ef9473` (`Implement V0-A biomedical extractor`).

## Verification already completed

- `uv run python -m unittest discover -s tests -v`: 9 focused tests passed.
- Python compilation, package import, JSON serialization, CLI help, and `uv lock --check` passed.
- Both real checkpoints loaded successfully on CPU.
- Representative end-to-end inference detected `BRCA1` at `[0, 5)` and `breast cancer` at `[57, 70)`, and returned relations whose source/target IDs resolved to those entities.
- `uv run python demo.py` completed successfully with pasted representative input and displayed readable entities, relations, and the normalized JSON result.

## Outstanding

- GPU execution was not exercised; the verified project environment used CPU PyTorch.
- Extraction quality and production thresholds remain intentionally untuned. BioRED evaluation belongs to a later task.
- The repository root has an unrelated untracked `C:\Projects\Biomed\.gitignore`; it is outside the `extraction_system` project boundary and must remain untouched unless explicitly brought into scope.

## Next action

Begin only the next explicitly assigned extraction-system task. Read `AGENTS.md` first, then load the linked current-truth documents as needed; do not start BioRED evaluation or remove retained environments/caches without an explicit request.

## Material files

- `src/biomedical_extractor/pipeline.py`
- `src/biomedical_extractor/cli.py`
- `demo.py`
- `tests/test_pipeline.py`
- `pyproject.toml`
- `uv.lock`
- `TALIA_V0-A_COMPREHENSIVE_REPORT.md`

## Authoritative references

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/product/CURRENT_SPEC.md`
- `README.md`
