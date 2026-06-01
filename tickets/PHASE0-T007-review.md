# PHASE0-T007 Code Review

**Ticket:** Loop (orchestration + claim register)  
**Files reviewed:** `src/ubu_phase0/loop.py`, `tests/test_missing_github_token_uses_fixture.py`, `tests/test_dependency_overlay.py`  
**Reference docs:** `AGENTS.md`, `PHASE0_CUTLIST.md`, `PHASE0_MODULE_BOUNDARIES.md`, `tickets/PHASE0-T007-loop.json`  
**Verdict:** PASS. No blocking violations. Four advisory items noted below.

---

## 1. Scope Creep — CLEAR

Three new files added, all in `allowed_files`:

- `src/ubu_phase0/loop.py` ✓
- `tests/test_missing_github_token_uses_fixture.py` ✓
- `tests/test_dependency_overlay.py` ✓

Forbidden files (`schema.py`, `cli.py`) are untouched.

No Phase 1 features introduced:
- No repair mode, stochastic durations, GPU, Monte Carlo, OAuth, or model-committee calls.
- No persistent cache (in-memory state only; `LoopResult` is returned fresh each call).
- No auto-fallback (missing token raises `LoopError`; see §4 and §8 below).
- `run()` accepts a `logs` parameter but only passes it through to the existing `planner(request, logs)` API, which always accepts logs. The v1.5 log-replan feature (T010) requires additional log-loading and CLI wiring not present here. Carrying the parameter is correct planner-API wiring, not a Phase 1 feature implementation.

---

## 2. Schema Drift — CLEAR

`schema.py` is not in the working-tree diff. Confirmed frozen.

Schema symbols imported by `loop.py`:

| Symbol | Status |
|---|---|
| `AffectProfile` | confirmed in schema.py:198 ✓ |
| `DependencyEdge` | confirmed in schema.py:253 ✓ |
| `LogEntry` | confirmed in schema.py:371 ✓ |
| `PlanningRequest` | confirmed in schema.py:330 ✓ |
| `PlanningResponse` | confirmed in schema.py:525 ✓ |
| `TaskGraph` | confirmed in schema.py:258 ✓ |
| `TimeWindow` | confirmed in schema.py:271 ✓ |
| `UniverseStateSnapshot` | confirmed in schema.py:291 ✓ |

`ClaimEntry` and `ClaimRegister` are new dataclasses defined in `loop.py`, not in `schema.py`. This is correct per `AGENTS.md`: "Do not create a `claims.py` module; the claim-register loader lives in `loop.py`." ✓

---

## 3. Import Boundaries — CLEAR

`loop.py` imports:

| Import | Permitted? |
|---|---|
| `from __future__ import annotations` | stdlib ✓ |
| `import json, logging, os, uuid` | stdlib ✓ |
| `from dataclasses import dataclass, field` | stdlib ✓ |
| `from datetime import datetime, timedelta, timezone` | stdlib ✓ |
| `from pathlib import Path` | stdlib ✓ |
| `from ubu_phase0 import github_ingest as _github_ingest` | permitted ✓ |
| `from ubu_phase0 import planner as _planner` | permitted ✓ |
| `from ubu_phase0.bootstrap import default_affect_profile` | permitted ✓ |
| `from ubu_phase0.schema import (...)` | permitted ✓ |

Forbidden module `cli` is absent. `affect` is not imported directly (bootstrap handles preset expansion; loop does not need it). All imports are within the set defined in `PHASE0_MODULE_BOUNDARIES.md §7.2`.

---

## 4. Hidden Network Dependency — CLEAR

`loop.py` itself contains no HTTP, socket, subprocess, or environment-variable-driven network calls at module level. The live path calls `_github_ingest.ingest_live()`, which is only reachable when `offline=False` and a non-empty token is present — a deliberate operator choice. The offline path is completely network-free. No lazy imports that could introduce network access at call time.

---

## 5. GitHub Mutation — CLEAR

`loop.py` calls `_github_ingest.ingest_live()`, which calls `gh_repo.get_issues(state="open")` — a read-only API call. No create, edit, close, comment, assign, label, PR, or project-board operations. `loop.py` itself contains no GitHub library imports. ✓

---

## 6. Planner Impurity — NOT APPLICABLE

`loop.py` calls `_planner.planner(request, logs)` as a pure function. It does not modify `planner.py`, does not import it at module level in any way that could leak state, and does not expose any file/env/GitHub path to the planner. The planner module itself is unchanged.

---

## 7. Missing Tests — CLEAR

**`tests/test_missing_github_token_uses_fixture.py`** (14 tests):

- Offline run returns a valid `LoopResult` (no token required)
- `result.mode == "offline"`
- `"fixture"` in `source_label`
- Task count equals 5 (6 fixture entries minus 1 PR exclusion)
- `planning_response` is not None
- Planning status is `ok` or `partial`
- Claim register is a `ClaimRegister` instance, not a string
- Claim register has correct `profile` value
- All `ClaimEntry` fields populated
- Default affect profile matches bootstrap skip-calibration presets
- `run(offline=False)` without token raises `LoopError`
- Error message names `UBU_PHASE0_GITHUB_TOKEN`
- No silent fallback (explicit negative assertion)

**`tests/test_dependency_overlay.py`** (9 tests):

- All 3 fixture hardcoded edges present in `result.task_graph.dependency_edges`
- Fixture edges present in `result.planning_request.task_graph.dependency_edges`
- Fixture edge count is exactly 3
- `validate_dependency_edges` preserves valid edges with no warnings
- `validate_dependency_edges` with empty edge list produces no warnings
- Missing `before_task_id` drops edge and names the ghost ID in warning
- Missing `after_task_id` drops edge and names the ghost ID in warning
- Mixed valid/invalid edges: valid preserved, invalid dropped, one warning
- Loop integration: bad fixture edge dropped, warning in `LoopResult.warnings`

The ticket's definition of done ("Tests pass. No auto-fallback, no cache.") is satisfied by the test set above.

---

## 8. Claim-Register Drift — CLEAR

`loop.py` loads `fixtures/claim_register.json` and returns a `ClaimRegister` dataclass (not a raw string, not a plain dict). Each claim becomes a `ClaimEntry` dataclass. This is the "structured object" required by the ticket and `PHASE0_MODULE_BOUNDARIES.md §7.2`.

The `_load_claim_register()` function performs structural validation (JSON parse, field extraction). Completeness validation — the `test_claim_register_completeness` test that checks every `status=implemented` claim has a non-empty `modules` list and named test — is a separate concern assigned to the test suite, not to the loader. This is consistent with `PHASE0_CLAIM_REGISTER_SPEC.md §13.3`.

`ClaimRegister` and `ClaimEntry` live in `loop.py`, not in a `claims.py` module. ✓

---

## Advisory Items (non-blocking)

### A. `_REPO_ROOT` path resolution is editable-install-only

`loop.py:22`: `_REPO_ROOT = Path(__file__).parent.parent.parent` resolves correctly when the package is installed in editable mode (`pip install -e .`), placing `__file__` at `src/ubu_phase0/loop.py`. If the package is ever installed non-editably (e.g., built into a wheel and installed into site-packages), this path will resolve to a directory three levels above the site-packages location, which will not contain `fixtures/`. Per `AGENTS.md`: "Optimize for the canonical demo path." The canonical path is always editable install from the repo root. No fix required for Phase 0; note for any packaging step.

### B. `test_claim_register_completeness` not yet implemented

`PHASE0_CLAIM_REGISTER_SPEC.md §13.3` names `test_claim_register_completeness` as the test that enforces the completeness rule: every `status=implemented` claim must have a non-empty `modules` list, a named `test`, and a passing acceptance test. This test file does not exist in the working tree and is not in T007's `allowed_files`. It is not a T007 obligation — no ticket through T007 lists it as required — but it will need to land before the claim register is considered verified. Note for T008 or T009 scope planning.

### C. No test for the `affect_profile` override in `run()`

`loop.py:137`: `run(affect_profile=<override>)` lets callers supply a non-default `AffectProfile`. This parameter exists so T008 (CLI) can pass an operator-selected profile. There is no acceptance test exercising this path. For T007 scope, the parameter is correct infrastructure. T008 will exercise the override through CLI tests. No fix required.

### D. `validate_dependency_edges` does not test `topological_order` preservation

`loop.py:94-107`: `validate_dependency_edges` constructs the returned `TaskGraph` passing `topological_order=task_graph.topological_order`. This preserves whatever the ingest layer set (always `None` in Phase 0, as `ingest_fixture` and `ingest_live` do not compute a topo order). No test asserts this preservation. It is a no-op detail in Phase 0; the planner always recomputes topological order from scratch. No fix required.

---

## Correctness Spot-Checks

**Hard switch / no fallback (critical):** `loop.py:127-139`: `if offline:` → fixture path; `else:` → live path with token check. The token check is `if not token: raise LoopError(...)`. There is no `except` block that redirects to the fixture on failure. The only `except` block (`loop.py:154-159`) re-raises as `LoopError`. Confirmed no auto-fallback.

**No persistent cache:** No `open()` for writing, no shelve/sqlite/pickle, no module-level mutable dict that survives between calls. Each `run()` call allocates a fresh `LoopResult`. ✓

**`validate_dependency_edges` task identity check:** Uses `{t.id for t in task_graph.tasks}` as the set of known IDs. Both `edge.before_task_id` and `edge.after_task_id` are checked against this set. Correct — `TaskSpec.id` and `DependencyEdge.{before,after}_task_id` use the same `github:{owner}/{repo}#{number}` format. ✓

**PlanningRequest 4-hour window:** `window_end = now + timedelta(hours=4)`. `TimeWindow.start_time = now_str`, `end_time = window_end_str`. Delta is exactly 4 hours, matching `PHASE0_WINDOW_SECONDS = 4 * 60 * 60 = 14400` in schema. ✓

**Claim register path:** `_DEFAULT_CLAIM_REGISTER_PATH = _REPO_ROOT / "fixtures" / "claim_register.json"`. File confirmed to exist at `fixtures/claim_register.json` with the required v1 claims. ✓

---

## Verdict

**PASS.** All hard rules from `AGENTS.md` and `PHASE0_MODULE_BOUNDARIES.md` are satisfied. No forbidden imports, no schema mutations, no GitHub mutation, no Phase 1 features, no auto-fallback, no persistent cache, no claims.py module. Claim register is returned as a structured object. Acceptance test coverage is complete for the ticket's stated scope. Four advisory items noted; none require a code change before T007 is closed.
