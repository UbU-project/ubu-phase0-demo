# Agent Instructions — UbU Phase 0

You are implementing UbU Phase 0, a Python-only ETHConf NYC demo prototype.
It is NOT Phase 1 and NOT production architecture. Phase 0 code is not expected
to survive into Phase 1.

## Goal

Build a CLI demo that:

1. reads GitHub issues from `UbU-dummy/ubu-design` in live mode,
2. reads fixtures in `--offline` mode,
3. converts issues into UbU Task objects with `authority_source`,
4. builds a Phase 0 `PlanningRequest`,
5. runs a deterministic dependency-aware, affect-aware planner,
6. shows a four-hour Calendar preview with source and affect-margin columns,
7. prints a claim-register summary.

## How to work

- Implement exactly one ticket at a time. Read the ticket JSON in `tickets/`.
- Read this file and the relevant `PHASE0_*.md` docs before writing code.
- Touch only the ticket's `allowed_files`. Never edit `forbidden_files`.
- Run the ticket's acceptance tests. Stop when they pass.
- Report changed files, test output, and any mypy warnings.

## Hard rules

- Do not implement Phase 1: no repair mode, no stochastic durations, no GPU,
  no Monte Carlo, no correlation matrices, no OAuth, no model-committee integration.
- Do not mutate GitHub in any way (no create/edit/close/comment/assign/label/PR/board).
- Do not auto-fall-back: live-mode errors exit non-zero; `--offline` selects the fixture.
- Do not add a persistent cache. `refresh` replaces in-memory state only.
- Do not edit `src/ubu_phase0/schema.py` after T001; it is FROZEN.
- Do not change fixture shapes without updating schema and tests.
- Do not violate `PHASE0_MODULE_BOUNDARIES.md`.
- Do not move explanation generation out of `planner.py`.
- `planner.py` must not read files, env vars, or GitHub, and must not import
  `github_ingest`, `loop`, or `cli`.
- Do not create a `claims.py` module; the claim-register loader lives in `loop.py`.
- Optimize for the canonical demo path and the documented failure modes.
  Do not add defensive code beyond ticket scope. Do not generalize.

## Checks

```
python -m pytest -m "not live_github"   # blocking
python -m ruff check .                   # blocking
python -m mypy src/ubu_phase0            # advisory; report warnings, do not hide them
```

## Definition of done

A ticket is done only when:

- its acceptance tests pass,
- changed files are within allowed scope and no forbidden imports were added,
- no Phase 1 features were introduced,
- `schema.py` is unchanged (unless this is an explicit schema-change ticket),
- demo behavior remains fixture-safe,
- mypy warnings are reported in the ticket summary.
