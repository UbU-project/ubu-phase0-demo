## 12. `PHASE0_ACCEPTANCE_TESTS.md`

The test specifications below are human-owned. Agents translate each spec into pytest code; agents do not invent the criteria. This prevents the circularity where agent-derived tests merely confirm the agent's own reading of the design.

### 12.1 Default suite (blocking)

- **test_schema_contract** — schema constants exist; `profile` string is correct; Phase 0 sentinels exist; required model fields exist; unsupported fields serialize as `None` or sentinel rather than disappearing.
- **test_contract_roundtrip** — `demo_request.json` loads, validates as `PlanningRequest`, serializes back, is consumed by the planner, and the resulting `PlanningResponse` validates.
- **test_github_issue_fixture_to_tasks** — `static_dummy_issue.json` loads; issues convert to `TaskSpec`; `source_ref` is correct; `external_url` preserved; `authority_source` set to `imported_config` for the fixture; PR-like items skipped.
- **test_github_label_mapping** — duration, priority, and affect labels map correctly; duplicate-family labels resolve to first-alphabetical with a warning; unknown labels do not fail; unlabeled issue gets safe defaults.
- **test_github_issue_deduplication** — duplicates dedupe by `source_ref`; result ordering is deterministic.
- **test_missing_github_token_uses_fixture** — (revised) in live mode with no token, the loop fails cleanly with a non-zero exit and a message naming the env var; with `--offline`, the loop uses the fixture and does not touch the network; the reported data source is correct in both cases.
- **test_dependency_overlay** — overlay edges apply to matching task refs; unknown refs warn and are treated as absent; valid edges change scheduling order.
- **test_topological_order** — a known dependency chain schedules prerequisites before dependents; cycles are rejected with a clear diagnostic; unknown dependencies are reported.
- **test_affect_gate_rejection** — a low-energy profile rejects or deprioritizes high-energy tasks; a high-stress profile rejects high-stress-risk tasks; an intense-mood profile rejects mood-intense-risk tasks.
- **test_calendar_preview_next_four_hours** — the preview starts at `effective_time`; spans no more than four hours; fixed durations fit; no overlaps.
- **test_claim_register_completeness** — `claim_register.json` loads; every `implemented` claim names an existing test; every required demo claim appears; statuses are valid.
- **test_cli_demo_smoke** — `ubu-phase0 demo --offline` exits 0; output includes the data source, the Calendar preview, and the claim summary.
- **test_cli_refresh_smoke** — `ubu-phase0 refresh` with no token fails cleanly and reports the absence; does not crash.
- **test_import_boundaries** — the module graph in Section 7 is not violated; planner purity is enforced by source scan.

### 12.2 Opt-in and v1.5 tests (excluded from the default run)

- **test_live_github_ingestion_smoke** — marked `@pytest.mark.live_github`; excluded from the default suite via `addopts = "-m 'not live_github'"`; run manually before rehearsal with `UBU_PHASE0_GITHUB_TOKEN=... pytest -m live_github`. Does not block any ticket.
- **test_log_replan**, **test_claims_command**, **test_recalibrate**, **test_doctor_command** — added with their respective v1.5 tickets.

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
