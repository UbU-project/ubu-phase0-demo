# PHASE0-T004 Code Review

**Ticket:** Affect gate  
**Files reviewed:** `src/ubu_phase0/affect.py`, `tests/test_affect_gate_rejection.py`  
**Reference docs:** `AGENTS.md`, `PHASE0_CUTLIST.md`, `PHASE0_MODULE_BOUNDARIES.md`, `PHASE0_CONTRACT_PROFILE.md §6.6`, `tickets/PHASE0-T004-affect.json`  
**Verdict:** PASS with one bug in the test AST scanner and two advisory items. No blocking violations in `affect.py` itself.

---

## 1. Scope Creep — CLEAR

Exactly two files created: `src/ubu_phase0/affect.py` and `tests/test_affect_gate_rejection.py`. Both are listed in `allowed_files`. No forbidden files were touched.

`schema.py` MD5 is identical to HEAD (`47064bad7eb917bba57f97c94365a663`). Frozen — confirmed.

No Phase 1 features introduced: no stochastic modeling, no repair mode, no GPU, no Monte Carlo, no correlation matrices, no OAuth.

---

## 2. Schema Drift — CLEAR

`affect.py` constructs `AffectProfile` and `AffectDimensionSpec` objects using only fields present in the frozen schema. The `model_validator` in `AffectProfile._check_directions` is satisfied because the correct `direction` values are hardcoded by `preset_to_affect_profile`. No new schema fields are invented or assumed.

---

## 3. Import Boundaries — CLEAR (affect.py); BUG (test scanner)

**`affect.py` imports (correct):**

| Import | Permitted? |
|---|---|
| `__future__` | stdlib ✓ |
| `math` | explicitly permitted ✓ |
| `typing.NamedTuple` | stdlib ✓ |
| `ubu_phase0.schema` | explicitly permitted ✓ |

No forbidden modules (`planner`, `github_ingest`, `bootstrap`, `loop`, `cli`) are present. No file I/O, no env var reads, no GitHub library imports.

**Ticket note vs spec discrepancy (advisory, not a violation):** The ticket says "May import schema and math only." `PHASE0_MODULE_BOUNDARIES.md §7.2` is the normative spec and says "May import: schema, math, stdlib." `typing` is stdlib; the ticket note is informal shorthand. Not a violation.

**BUG (Mitigated) — `test_affect_import_boundaries` AST scanner has a detection gap:**

The scanner at `tests/test_affect_gate_rejection.py:313–336` cannot detect `from ubu_phase0.planner import some_function` style imports. It splits `node.module` on `.` and takes only the first segment:

```python
imported_names.add(node.module.split(".")[0])  # "ubu_phase0.planner" → "ubu_phase0"
```

`"ubu_phase0"` is not in `forbidden = {"planner", "loop", "cli", "github_ingest", "bootstrap"}`, so the check silently passes. The scanner correctly catches `import planner` (bare) and `from ubu_phase0 import planner` (submodule-as-name), but misses the most natural import form used throughout this codebase:

```python
from ubu_phase0.planner import check_something  # NOT caught by the scanner
```

Verified with a live AST parse: `imported_names` would be `{'some_function', 'ubu_phase0'}` — zero violations flagged.

**Impact:** `affect.py` currently has no forbidden imports, so no live vulnerability exists. The bug is in the test's enforcement, not in the implementation. However, the test overstates the coverage it provides.

**Fix:** Replace the first-segment split with a full submodule check:

```python
# Replace:
imported_names.add(node.module.split(".")[0])
# With:
for part in node.module.split("."):
    imported_names.add(part)
```

This catches `from ubu_phase0.planner import X` (adds both "ubu_phase0" and "planner").

**Note:** `tests/test_import_boundaries.py` — the canonical mechanical enforcement layer described in `PHASE0_MODULE_BOUNDARIES.md §7.3` — does not yet exist. Until that file is created (likely a dedicated ticket), the per-module scanners in each test file are the only import enforcement. The gap above is therefore currently unmitigated at the project level.

**Status:** Fixed/Mitigated, as per recommendation.

---

## 4. Preset Table Values — CORRECT

All nine presets verified bit-for-bit against `PHASE0_CONTRACT_PROFILE.md §6.6`:

| Dimension | Preset | location | scale | threshold |
|---|---|---|---|---|
| energy | low | 3.0 | 1.0 | 0.5 |
| energy | medium | 4.0 | 1.5 | 0.5 |
| energy | high | 6.0 | 1.5 | 0.3 |
| stress | low | 7.0 | 1.5 | 0.5 |
| stress | medium | 5.5 | 1.2 | 0.5 |
| stress | high | 4.0 | 1.0 | 0.6 |
| mood_intensity | calm | 8.0 | 1.5 | 0.5 |
| mood_intensity | engaged | 6.5 | 1.2 | 0.5 |
| mood_intensity | intense | 5.0 | 1.0 | 0.6 |

Default presets (`DEFAULT_ENERGY_PRESET=medium`, `DEFAULT_STRESS_PRESET=low`, `DEFAULT_MOOD_PRESET=calm`) match the spec's "skip-calibration defaults."

---

## 5. Sigmoid Formula — CORRECT

Implementation in `dimension_satisfaction`:

```python
higher_is_better: sigmoid((value - spec.location) / spec.scale)   # matches spec
lower_is_better:  sigmoid((spec.location - value) / spec.scale)   # matches spec
```

`sigmoid` itself is numerically stable (avoids `exp` overflow for large positive inputs by switching form for `x < 0`). Verified `sigmoid(0.0) == 0.5`.

---

## 6. Feasibility Condition — CORRECT

`check_task_affect_feasibility` uses `sat < spec.threshold` for violation (i.e., `satisfaction >= threshold` is feasible). Exactly-at-threshold passes. This matches "Feasible iff every active dimension satisfaction >= threshold" in the spec.

---

## 7. Hidden Network Dependency — CLEAR

No network calls anywhere in `affect.py`. Pure math and data structure operations only.

---

## 8. GitHub Mutation — CLEAR

Not applicable. `affect.py` has no GitHub interaction.

---

## 9. Planner Impurity — CLEAR

`planner.py` was not created or modified. `affect.py` contains no planning logic; it is a pure computation module as required.

---

## 10. Claim-Register Drift — NOT APPLICABLE

`affect.py` contains no claim-register logic. No drift.

---

## 11. Tests — CLEAR

28 tests cover:

- `sigmoid`: zero point, large-positive, large-negative, monotonicity.
- `dimension_satisfaction`: both directions, at-location=0.5 identity, above/below-location ordering.
- `preset_to_affect_profile`: default locations match spec, preset labels stored, all 9 presets expand without error, direction correctness.
- `check_task_affect_feasibility` pass cases: empty requirements, comfortable energy, low-stress task.
- `check_task_affect_feasibility` rejection cases: high stress under low profile, low energy under high profile, intense mood under calm profile, multi-dimension violation.
- Threshold boundary: exactly-at-threshold is feasible, just-below is not.
- Score accounting: `minimum_score` reflects worst dimension; scores dict populated only for evaluated dimensions.
- Import boundary: AST scan of `affect.py` (with the gap noted in §3).

All 28 pass. ruff: clean. mypy: no issues found.

---

## ADVISORY

### A1 — `minimum_score=1.0` sentinel for unconstrained tasks

**Location:** `affect.py:179`

When `task.affect_requirement` is empty, `scores` is empty and `min_score = 1.0`. This sentinel will propagate to `FeasibilitySummary.minimum_affect_score` in the planner and likely surface as the affect-margin column value in the calendar preview. A task with no affect requirements will appear to have a "perfect" 1.0 margin — which is vacuously correct but potentially misleading to a demo observer.

The spec does not define the empty-requirements case. The implementation is reasonable for Phase 0. **Recommendation for T005 (planner):** document that a `minimum_affect_score` of 1.0 with an empty `affect_requirement` means "unconstrained," not "optimal," and consider suppressing the margin display for such tasks.

### A2 — `AffectFeasibilityResult` NamedTuple contains mutable fields

**Location:** `affect.py:145–149`

`violated_dimensions: list[str]` and `satisfaction_scores: dict[str, float]` are mutable despite being fields of a `NamedTuple`. The tuple structure is immutable but the contained list and dict can be mutated by callers. In Phase 0 with a single-threaded planner this is not a practical concern, but a caller modifying `result.violated_dimensions` in place would corrupt state. No caller currently does this; advisory only.
