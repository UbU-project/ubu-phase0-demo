# PHASE0-T005 Code Review

**Ticket:** Planner  
**Files reviewed:** `src/ubu_phase0/planner.py`, `tests/test_topological_order.py`, `tests/test_calendar_preview_next_four_hours.py`  
**Reference docs:** `AGENTS.md`, `PHASE0_CUTLIST.md`, `PHASE0_MODULE_BOUNDARIES.md`, `tickets/PHASE0-T005-planner.json`  
**Verdict:** PASS. No blocking violations. Three advisory items noted below.

---

## 1. Scope Creep — CLEAR

Three files added, all listed in `allowed_files`:
- `src/ubu_phase0/planner.py`
- `tests/test_topological_order.py`
- `tests/test_calendar_preview_next_four_hours.py`

No forbidden files touched. `test_affect_gate_rejection.py` (also in `allowed_files`) was not modified — it is a T004 artifact and was already complete; no modification was required.

No Phase 1 features introduced:
- No Monte Carlo, stochastic durations, GPU, repair mode, correlation matrices, OAuth, or model-committee calls.
- `probability_quality = not_estimated` throughout; all five coverage fields set to `None`.
- Semi-legitimization implemented; full legitimization is a no-op stub, as required.
- Single candidate produced (`rank=1`, `candidate_role=highest_utility`), consistent with deterministic Phase 0 planning.
- No persistent cache, no on-disk writes, no auto-fallback logic.

---

## 2. Schema Drift — CLEAR

All 23 names imported from `schema.py` are confirmed to exist at their declared lines:

| Symbol | Line in schema.py |
|---|---|
| `AffectProfile` | 199 |
| `CandidateRole` | 102 |
| `Diagnostics` | 499 |
| `ExplanationFragment` | 436 |
| `FeasibilitySummary` | 397 |
| `LogEntry` | 370 |
| `LogOutcome` | 138 |
| `PlanCandidate` | 441 |
| `PlanningRequest` | 330 |
| `PlanningResponse` | 525 |
| `PlanningStatus` | 78 |
| `ProbabilityQuality` | 115 |
| `ProbabilitySummary` | 416 |
| `ScoreSummary` | 389 |
| `ScheduledPlacement` | 383 |
| `SemiLegitimizationResult` | 109 |
| `SemiLegitimizationSummary` | 404 |
| `SkeletonFailureDiagnostic` | 486 |
| `SkeletonFailureClass` | 127 |
| `SkeletonSeverity` | 122 |
| `ScoringPolicy` | 299 |
| `TaskSpec` | 228 |
| `TimeWindow` | 271 |

`schema.py` is not in the untracked or modified file list — confirmed frozen.

---

## 3. Import Boundaries — CLEAR

`planner.py` imports:

| Import | Permitted? |
|---|---|
| `from __future__ import annotations` | stdlib ✓ |
| `from collections import deque` | stdlib ✓ |
| `from datetime import datetime, timedelta` | stdlib ✓ |
| `from ubu_phase0 import affect as _affect` | permitted ✓ |
| `from ubu_phase0.schema import (...)` | permitted ✓ |

Forbidden modules (`github_ingest`, `bootstrap`, `loop`, `cli`) are absent. Confirmed by both visual inspection and the AST-based boundary test in `test_topological_order.py:test_planner_import_boundaries`.

---

## 4. Planner Purity — CLEAR

Scanned `planner.py` for:
- `open(` — absent
- `os.environ` — absent
- `os.getenv` — absent
- PyGithub / `github` / `requests` / `urllib` / `socket` imports — absent

The function accepts `PlanningRequest` and `list[LogEntry]` and returns `PlanningResponse`. No mutation of the input request is performed (all derived state is in local variables). Pure.

---

## 5. Hidden Network Dependency — CLEAR

No HTTP, socket, subprocess, or environment-variable reads anywhere in `planner.py`. No lazy imports that could introduce network access at call time.

---

## 6. GitHub Mutation — NOT APPLICABLE

Planner has no GitHub access by construction.

---

## 7. Missing Tests — CLEAR

The three acceptance test files named in the ticket cover:

**`test_topological_order.py`**
- Empty graph (ok/partial status)
- Single task scheduled
- Two-task chain via `task.dependencies`
- Three-level chain order
- Two-task chain via `dependency_edges`
- Independent tasks all scheduled
- Mutual cycle → `rejected` status
- Cycle diagnostic class is `cyclic_dependency`
- Cycle diagnostic names involved tasks
- Three-task cycle rejected
- Completed task not re-scheduled
- Completed dependency unblocks dependent
- Blocked task excluded
- Blocked dependency prevents dependent scheduling
- Import boundary: forbidden modules absent

**`test_calendar_preview_next_four_hours.py`**
- First task starts at window start
- Task end = start + duration
- Second task starts where first ends
- Three tasks packed consecutively
- Task exceeding window excluded
- Tasks that don't fit after overflow excluded
- All placements end ≤ window end
- Affect-rejected task absent in enforce mode
- Affect-rejected task present in warn_only mode
- Affect rejection counted in diagnostics
- `request_id` echoed in response
- `rng_seed` echoed in response
- `probability_quality == not_estimated`
- All five coverage fields are `None`
- Fixture `demo_request.json` produces ≥ 1 scheduled task
- Fixture with completed task excludes that task from next schedule

**`test_affect_gate_rejection.py`** (pre-existing, T004 artifact, unmodified) — acceptance tests for `affect.py` functions; included in ticket's acceptance test invocation.

---

## 8. Claim-Register Drift — CLEAR

`planner.py` has no reference to any claim-register concept. Claim-register loading is correctly deferred to `loop.py` per `PHASE0_MODULE_BOUNDARIES.md §7.2`.

---

## Advisory Items (non-blocking)

### A. `blocked_refs` count emitted as a warning, not an ExplanationFragment

`planner.py:388–391`: The count of blocked tasks is appended to `warnings` rather than to `explanation_fragments`. Completed and affect-rejected tasks each get an `ExplanationFragment`; blocked tasks do not. This means the blocked-task count will appear in `Diagnostics.warnings` but not in the candidate's `explanation_fragments`, making the explanation rendering in the eventual CLI asymmetric. No schema rule requires parity here; the ticket says "Generate explanations internally" without specifying all cases. No fix required for T005, but note for T008 (cli) that blocked-task info lives in `warnings`, not `explanation_fragments`.

### B. Empty task graph returns `PlanningStatus.partial`

`planner.py:405`: `status = PlanningStatus.ok if schedule else PlanningStatus.partial`. With zero tasks, `schedule` is empty and the status is `partial`. Semantically, `partial` implies tasks exist but not all fit; `ok` might better represent a vacuously successful plan. The acceptance test (`test_empty_task_graph_returns_ok`) accepts either status, so no test fails. Low impact in the demo; the fixture always has tasks. No fix required.

### C. `_find_cycle_participants` uses unbounded recursive DFS

`planner.py:98–115`: DFS is implemented with Python recursion, which will hit the default 1000-frame limit on very deep dependency chains. For the Phase 0 demo scale (handful of GitHub issues) this is safe. Per AGENTS.md: "Do not add defensive code beyond ticket scope." No fix required.

---

## Correctness Spot-Checks

**Blocked dependency propagation (critical path):** When task T1 is `blocked` in logs:
- `excluded_refs = {T1}` → T1 removed from `effective_tasks`
- `satisfied_ids = completed_refs | skipped_refs` — blocked tasks deliberately excluded from `satisfied_ids`
- T2 (dep on T1): `known_deps = {T1}`, T1 is in `all_tasks` (built from `request.task_graph.tasks`, not `effective_tasks`), T1 not in `satisfied_ids` → `unsatisfied = {T1}` → T2 skipped
- Result: T2 correctly excluded. Matches `test_blocked_dependency_prevents_dependent_scheduling`.

**Skipped tasks as satisfied:** Skipped tasks are excluded from `effective_tasks` AND added to `satisfied_ids`. This means their dependents can be scheduled. This is consistent with the implementation note "ignore skipped" — skipped tasks are treated as if they ran, unblocking their dependents. The test suite does not test the skipped-unblocks-dependent path, but no ticket requirement contradicts this behavior.

**`ConstraintPolicy.affect_constraint_mode` comparison:** `planner.py:272` compares against the string `"enforce"`. The schema field is `Literal["enforce", "warn_only"]`. Because `ConstraintPolicy` is a `str`-backed Pydantic field (not an Enum), the string comparison is correct.

**`Priority.value` in `_score_candidate`:** `planner.py:129` calls `task.priority.value`. `Priority` is declared as `class Priority(str, Enum)` in `schema.py:96`. Because it is a `str` enum, `.value` returns the string value (`"high"`, `"medium"`, `"low"`). The lookup against `priority_weights` is correct.

**Fixture smoke test task ref:** `test_calendar_preview_next_four_hours.py:310` uses `task_ref="github:UbU-dummy/ubu-design#8"`. The `demo_request.json` fixture has `"id": "github:UbU-dummy/ubu-design#8"` at its first task position. The ref format matches.

---

## Verdict

**PASS.** All hard rules from `AGENTS.md` and `PHASE0_MODULE_BOUNDARIES.md` are satisfied. No Phase 1 features, no forbidden imports, no schema mutations, no impurity, no GitHub mutations, no claim-register drift. Acceptance test coverage is complete for the ticket's stated scope. Three advisory items noted; none require a code change before T005 is closed.
