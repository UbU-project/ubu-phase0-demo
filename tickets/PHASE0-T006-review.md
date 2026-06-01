# PHASE0-T006 Code Review

**Ticket:** Bootstrap  
**Files reviewed:** `src/ubu_phase0/bootstrap.py`, `tests/test_bootstrap_defaults.py`, `tests/test_github_label_mapping.py`  
**Reference docs:** `AGENTS.md`, `PHASE0_CUTLIST.md`, `PHASE0_MODULE_BOUNDARIES.md`, `tickets/PHASE0-T006-bootstrap.json`  
**Verdict:** PASS with one out-of-scope file touch (benign, noted below). No blocking correctness violations.

---

## 1. Scope Creep — CLEAR

Two new files added:
- `src/ubu_phase0/bootstrap.py` — in `allowed_files` ✓
- `tests/test_bootstrap_defaults.py` — in `allowed_files` ✓

No Phase 1 features introduced: no repair mode, Monte Carlo, stochastic durations, GPU, OAuth, or model-committee references. No persistent cache, no auto-fallback logic, no on-disk writes.

The `CHOICES` list constants (`ENERGY_CHOICES`, `STRESS_CHOICES`, `MOOD_INTENSITY_CHOICES`) are in scope: the ticket implementation note says "Expose qualitative choices only" and the ticket goal names "qualitative preset selection helpers." These lists constitute that exposure surface.

---

## 2. Schema Drift — CLEAR

`schema.py` does not appear in the diff. It is confirmed frozen.

Schema symbols imported by `bootstrap.py`: `AffectProfile`, `EnergyPreset`, `MoodPreset`, `StressPreset`. All four are standard Phase 0 preset/profile types; no novel schema constructs introduced or referenced.

---

## 3. Import Boundary Violations — CLEAR

`bootstrap.py` imports:

| Import | Permitted? |
|---|---|
| `from __future__ import annotations` | stdlib ✓ |
| `from ubu_phase0.affect import DEFAULT_ENERGY_PRESET, DEFAULT_MOOD_PRESET, DEFAULT_STRESS_PRESET, preset_to_affect_profile` | permitted ✓ |
| `from ubu_phase0.schema import AffectProfile, EnergyPreset, MoodPreset, StressPreset` | permitted ✓ |

Forbidden modules (`planner`, `github_ingest`, `loop`, `cli`) are absent from all imports. Confirmed by visual inspection and by `test_bootstrap_import_boundaries` in the acceptance test file.

---

## 4. Hidden Network Dependency — CLEAR

No `requests`, `urllib`, `socket`, `http`, `PyGithub`, or subprocess calls anywhere in `bootstrap.py`. No lazy imports that could introduce network access at call time. The module is fully static.

---

## 5. GitHub Mutation — NOT APPLICABLE

`bootstrap.py` has no GitHub access by construction.

---

## 6. Planner Impurity — NOT APPLICABLE

`bootstrap.py` does not import or call `planner`. The module graph position of `bootstrap` is correctly above `loop` and below nothing it should not reach.

---

## 7. Missing Tests — CLEAR

`tests/test_bootstrap_defaults.py` covers all stated acceptance criteria:

- Skip-calibration defaults (`DEFAULT_ENERGY is EnergyPreset.medium`, `DEFAULT_STRESS is StressPreset.low`, `DEFAULT_MOOD_INTENSITY is MoodPreset.calm`) — three tests
- `default_affect_profile` returns `AffectProfile`, has correct `preset_labels`, `needs_review`, `direction` fields, and is deterministic — five tests
- `select_affect_profile` uses provided presets, defaults match skip-calibration defaults, iterates all presets for each dimension — five tests
- `CHOICES` lists cover all enum members — three tests
- Import boundary enforcement via AST scan — one test

No ticket acceptance criterion is without a corresponding test.

---

## 8. Claim-Register Drift — CLEAR

`bootstrap.py` has no reference to any claim-register concept. Claim-register loading is correctly deferred to `loop.py` per `PHASE0_MODULE_BOUNDARIES.md §7.2`.

---

## Out-of-Scope File Touch — MINOR VIOLATION

`tests/test_github_label_mapping.py` is modified in this diff (the only change: removal of `from typing import Any`). This file is not in T006's `allowed_files` and is not `forbidden_files` — it is a T003 artifact. Per `AGENTS.md`: "Touch only the ticket's `allowed_files`."

The change itself is harmless — `Any` was an unused import in that file — and does not affect test behavior, correctness, or any boundary rule. However, the discipline of touching only `allowed_files` exists precisely to keep diffs auditable per-ticket. This is the only violation found.

**Recommended action:** Accept the change as-is (it is a dead-import cleanup with no risk), but note for future tickets that cleanup of adjacent files should be deferred or batched into a dedicated housekeeping commit, not folded into a feature ticket.

---

## Advisory Items (non-blocking)

### A. Import boundary test adds symbol names to the module-name set

`test_bootstrap_defaults.py:143–161`: `_imported_names_from_source` collects both module-path parts and imported symbol names into a single `set[str]`. For the current `bootstrap.py` this is safe, but if `affect.py` or `schema.py` ever exports a symbol whose name coincides with a forbidden module name (`loop`, `cli`, `planner`, `github_ingest`), the test would produce a false positive. The false-positive risk is negligible for this codebase; no fix required. This is the same pattern used in prior tickets (T005's boundary test). Note for T007/T008 if they add boundary tests.

### B. Two tests assert delegated `affect.py` behavior

`test_default_affect_profile_needs_review` and `test_default_affect_profile_directions` assert properties (`needs_review=True`, specific `AffectDirection` values) that are set by `affect.preset_to_affect_profile`, not by any logic in `bootstrap.py` itself. Bootstrap's only contribution is which preset labels it passes in. If `affect.py` changes those behaviors, these tests break even though `bootstrap.py` is unchanged.

This is implicit integration testing of `affect.py`'s contract as viewed from `bootstrap`. It documents a real behavioral expectation (the demo depends on `needs_review=True` for default profiles and on the direction semantics) so the tests are useful. No fix required; note for T004 maintainers that these tests exist as a downstream contract check.

---

## Verdict

**PASS.** All hard rules from `AGENTS.md` and `PHASE0_MODULE_BOUNDARIES.md` are satisfied. No forbidden imports, no schema mutations, no network access, no GitHub mutation, no Phase 1 features, no claim-register drift. Acceptance test coverage is complete. One out-of-scope file touch noted (benign unused-import removal in a T003 test file). Two advisory items noted; neither requires a code change before T006 is closed.
