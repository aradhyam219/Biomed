# Repository Working Guide

Current product truth: `docs/product/CURRENT_SPEC.md`.
Current architecture: `docs/ARCHITECTURE.md`.
Graph export/validation contract: `docs/GRAPH_CONTRACT.md`.
Provisioning: `docs/PROVISIONING.md` and `provisioning/`.
Production package: `src/biomedical_extractor/`; focused tests: `tests/`;
fixed regression fixtures: `tests/fixtures/baseline/`; graph consumer: `viewer/`.

The active system composes isolated HunFlair2, document-local assembly, grounded
LLM relations, graph construction and paper roles into Graph JSON. Preserve this
accepted functional baseline and its scientific limitations. Evaluation, model
selection, fine-tuning and historical experiments are outside delivery scope.

Commands (from extraction_system):
- Main environment: `uv sync --locked`.
- Tests: `uv run --locked python -m unittest discover -s tests -v`.
- NER: `uv run --locked biomedical-ner --text "..." --offline`.
- Composed graph: `uv run --locked biomedical-extract-llm --text "..." --output-format graph --document-id paper-1 --paper-title "..."` (v1).
- Consumer tests: `node --test viewer/tests/adapter.test.mjs`.

Production must accept ordinary biomedical text, retain exact source spans and
source evidence, preserve shared domain contracts and keep provider SDK objects
inside provider boundaries. Maintain the dual-runtime isolation and unchanged
viewer/graph semantics. Never commit secrets, environments, caches or generated
outputs. Keep accepted fixtures, lockfiles and provisioning recipes tracked.

Preserve unrelated changes. Use the smallest coherent change, inspect callers
and dependencies before deletion, and validate proportionally. Update CURRENT_SPEC
when product truth changes and ARCHITECTURE when structural truth changes. Keep
current truth concise; history belongs in Git. Each removal commit must remain
importable and testable. Cleanup changes stay under extraction_system/.

Baseline and delivery tags are immutable by policy. Never rewrite history or
force-push. Remote delivery branch/tag publication needs explicit authorization.
