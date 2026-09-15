# Repository Working Guide

> This file is the repository map and project-specific operating contract. Keep it short.
> Durable product behavior belongs in `docs/product/CURRENT_SPEC.md`; durable structural truth belongs in `docs/ARCHITECTURE.md`.

## Project purpose

This repository contains a biomedical entity-and-relation extraction component intended to turn unstructured biomedical text into clean, machine-consumable structured entities and relationships.

The current system is deliberately narrow. It is one component inside a larger system, not a general biomedical knowledge platform.

## Project map

- **Current product/domain truth:** `docs/product/CURRENT_SPEC.md`
- **Current architecture:** `docs/ARCHITECTURE.md`
- **Production package:** `src/biomedical_extractor/`
- **Focused tests:** `tests/`
- **Tracked machine-readable evaluation reports:** `reports/`
- **Dependency truth:** `pyproject.toml` and `uv.lock`
- **Decision records:** introduce `docs/decisions/` only when a durable, non-obvious architectural decision genuinely needs rationale preserved.
- **Active task state:** introduce a small task-state file only when work spans sessions and the next session cannot cheaply recover the needed delta from repository truth.

Canonical commands:

- install/sync: `uv sync`
- focused tests: `uv run python -m unittest discover -s tests -v`
- human-facing demo: `uv run python demo.py`

## Hard repository invariants

- Production extraction must accept ordinary biomedical text. It must not depend on BioRED-specific input structures.
- BioRED is evaluation infrastructure, not a production dependency.
- Entity extraction and relation extraction remain independently evaluable.
- The production path must produce normalized, machine-consumable structured output.
- Evaluation code must not leak dataset-specific assumptions into the production extraction path.
- Machine-readable final evaluation reports intended for review must be written to
  `reports/` and committed with the evaluation; raw predictions, incremental caches,
  and limited-run diagnostics remain under ignored `.cache/`.
- Do not broaden this component into adjacent platform capabilities unless a later task explicitly changes the product scope.

## Architectural boundaries

The current production responsibility is:

```text
biomedical text
    -> entity extraction
    -> relation extraction
    -> normalized structured result
```

Evaluation is a separate concern and is described in `docs/ARCHITECTURE.md`.

Follow existing repository patterns before introducing new abstractions. Prefer the smallest coherent implementation that satisfies the current specification and task contract.

## Scope discipline

Before expanding production scope, read `docs/product/CURRENT_SPEC.md`.

In particular:

- preserve unrelated behavior and existing user changes;
- do not perform opportunistic refactors during focused extraction work;
- do not introduce infrastructure merely because it may be useful later;
- do not add new production dependencies, public interfaces, persistence layers, or cross-subsystem behavior unless the current task requires them;
- keep the implementation suitable for extension without building speculative architecture for future phases.

If repository reality conflicts with a required behavior or invariant, surface the concrete conflict rather than silently changing product semantics.

## Validation policy

Use risk-proportional validation.

For ordinary extraction changes, prefer:

1. focused static/import checks where useful;
2. targeted tests for the changed behavior;
3. the relevant entity, relation, or end-to-end evaluation path when that behavior is affected;
4. broader tests only when the change or evidence justifies them.

Do not repeatedly run expensive model/evaluation work without a specific uncertainty it is intended to reduce.

## Documentation maintenance

Repository truth should evolve with the code.

For non-trivial code changes, keep documentation close to the behavior: new
non-trivial modules need a responsibility/data-flow module docstring; public or
non-obvious functions/classes need purpose, input/output, and invariant docstrings;
and non-obvious transformations need short comments explaining why. Identify the
authoritative source for external dataset/model assumptions, never narrate obvious
syntax, and update documentation whenever the documented behavior changes.

Codex is explicitly expected to update authoritative documentation as part of implementation when a task changes the truth those documents own:

- **Product/domain behavior changed:** update `docs/product/CURRENT_SPEC.md`.
- **Architecture, component boundaries, data/control flow, stable contracts, or supported extension points changed:** update `docs/ARCHITECTURE.md`.
- **Stable repository navigation or canonical commands changed:** update this `AGENTS.md`.
- **Durable non-obvious rationale is needed to prevent a harmful future reversal:** add a concise ADR rather than turning current-truth documents into history logs.

### Architecture update rule

Do **not** wait for Talia or the user to provide a replacement architecture file for each later phase.

When implementation materially changes the architecture, Codex should update `docs/ARCHITECTURE.md` itself in the same task so that it continues to describe the system **as it exists after the change**.

Architecture maintenance must remain evidence-based:

- update it when structural truth changes;
- do not update it merely because implementation details changed;
- replace obsolete statements instead of accumulating old and new architectures;
- keep historical debate in version control or an ADR when the rationale genuinely matters.

The same current-truth principle applies to `CURRENT_SPEC.md`.

## Completion

A task is complete when:

- its acceptance criteria are satisfied;
- hard invariants remain true;
- justified validation has passed;
- accidental scope growth has been removed; and
- any authoritative documentation made stale by the change has been updated.

Normal Codex completion reports should stay concise: what changed, what was verified, and any material risk or deviation.
