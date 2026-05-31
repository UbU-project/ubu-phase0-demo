# PHASE0_PLAN.md

Phase 0 is a Python-only ETHConf NYC demo prototype. It is not the production Phase 1 implementation.

## Demo objective

The demo shows that UbU can:

1. ingest project state from GitHub issues,
2. map issues into UbU Task objects with explicit provenance,
3. build a Phase 0 `PlanningRequest`,
4. run a deterministic, dependency-aware, affect-aware planner,
5. produce a four-hour Calendar preview with affect-margin indicators,
6. show an honest claim register.

The required UI is CLI/Rich. Live GitHub ingestion is the default; fixture mode is selected with `--offline`. The canonical live source is `UbU-dummy/ubu-design`. The minimum successful demo ends when the CLI displays a Calendar preview for today's next four hours.

## Required end state

`ubu-phase0 demo` must:

1. Load environment and configuration.
2. Select data source: live GitHub (default) or fixture (`--offline`).
3. In live mode, fetch open issues; on any error, fail cleanly and exit non-zero.
4. Convert issues into `TaskSpec` objects with `authority_source` set.
5. Apply safe defaults and any `ubu:` labels.
6. Apply the dependency overlay (live `depends-on:` labels; fixture hardcoded edges).
7. Build a `PlanningRequest`.
8. Run the planner.
9. Display the Calendar preview for today's next four hours, with source and affect-margin columns and the probability/coverage footer.
10. Print the claim-register summary.

## Stretch end state (v1.5)

11. Operator marks one Task complete (single key).
12. Planner reruns with the same `PlanningRequest` plus the accumulated `LogEntry` list.
13. CLI shows a "Completed" section above a changed Calendar preview.

See `docs/PHASE0_PROCESS.md` for the full master specification.
