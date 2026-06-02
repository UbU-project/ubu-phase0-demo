# PHASE0-T009 Code Review (final)

**Ticket:** Claim register validation
**Staged files:** `fixtures/claim_register.json` (modified), `tests/test_claim_register_completeness.py` (new), `tests/test_import_boundaries.py` (new), `tickets/PHASE0-T009-claim-register.json` (modified), `tickets/PHASE0-T009-review.md` (new). Cumulative diff also covers T008 committed files.
**Reference docs:** `AGENTS.md`, `PHASE0_CUTLIST.md`, `PHASE0_MODULE_BOUNDARIES.md`, `tickets/PHASE0-T009-claim-register.json`
**Verdict:** PASS. All staged files are correct. 30 tests pass. No scope creep, no schema drift, no Phase 1 features, no GitHub mutation, no planner impurity.

---

## Scope — CLEAR

`tickets/PHASE0-T009-claim-register.json` was amended to add `tests/test_import_boundaries.py` to `allowed_files`. The staged diff touches exactly the three files listed in `allowed_files`:

```text
fixtures/claim_register.json              modified (CR-009 added)
tests/test_claim_register_completeness.py new
tests/test_import_boundaries.py           new
```

The ticket JSON and this review file are also staged as bookkeeping. Forbidden files (`schema.py`, `claims.py`) are absent from the diff. No project-module source files outside `allowed_files` were touched. ✓

---

## Schema Drift — CLEAR

`schema.py` is not in the diff. Confirmed frozen. ✓

---

## Claim-Register Drift — CLEAR

CR-009 was added to `fixtures/claim_register.json`:

```json
{
  "id": "CR-009",
  "claim": "UbU enforces module import boundaries so planning logic cannot be contaminated by I/O or higher-layer modules",
  "status": "implemented",
  "modules": ["schema", "affect", "planner", "github_ingest"],
  "test": "test_import_boundaries"
}
```

- `claim`: accurate — describes the §7.3 rules enforced by the test. ✓
- `status: implemented` — all 16 tests pass. ✓
- `modules`: the four source modules whose import boundaries are mechanically checked. ✓
- `test`: matches `tests/test_import_boundaries.py`. ✓

All CR-001..CR-008 are unchanged. All seven implemented-claim test files exist on disk. The completeness test generates a `CR-009-test_import_boundaries` parametrize case and it passes. ✓

---

## Import Boundaries — ONE CARRY-FORWARD

`src/ubu_phase0/cli.py` line 20 imports `affect`, which is absent from `PHASE0_MODULE_BOUNDARIES.md §7.2`'s explicit "May import" list for `cli` (`loop; schema; Rich; Typer; stdlib`). This was flagged in the T008 review and is unchanged. `test_import_boundaries.py` correctly does not check `cli`-as-subject — §7.3 defines no such rule.

---

## Findings

### F1 — RESOLVED: schema self-import fix staged

`test_import_boundaries.py` line 162 previously read `imports & (_PROJECT_MODULES - {"schema"})` in the staged version, which would have let a `schema.py` self-import pass silently. The fix — `imports & (_PROJECT_MODULES)` — is now staged. ✓

### F2 — RESOLVED: all unstaged files now staged

`fixtures/claim_register.json` (CR-009) and `tickets/PHASE0-T009-claim-register.json` (allowed-files amendment) are both staged. ✓

### F3 (prior, PRESENT) — Parametrize reads fixture at collection time

**File:** `tests/test_claim_register_completeness.py`, lines 113–117

The `@pytest.mark.parametrize` list comprehension calls `CLAIM_REGISTER_PATH.read_text()` at module-import (collection) time. A missing or malformed `claim_register.json` raises `FileNotFoundError` during collection, crashing the entire test session rather than producing a targeted test failure. No current breakage — the fixture is committed and valid.

**Severity:** Low. Not resolved.

---

### F4 (prior, PRESENT) — Deferred/mocked test file existence never verified

**File:** `tests/test_claim_register_completeness.py`, lines 85–87 and 95–103

`test_all_claims_have_test_reference` checks only that the `test` field is non-empty. `test_implemented_claims_have_existing_test_files` skips all non-`implemented` claims. A future deferred or mocked claim with a typo in its `test` field would pass all completeness checks. CR-008 (`deferred`, `test: test_contract_roundtrip`) — file exists, no active breakage.

**Severity:** Low. Not resolved.

---

### F5 (prior, PRESENT) — `fixture_backed` exempt from all checks with no spec basis

**File:** `tests/test_claim_register_completeness.py`, lines 25, 97

`VALID_STATUSES` includes `fixture_backed`. It receives the full exemption (no existence check, no subprocess run) that `PHASE0_CLAIM_REGISTER_SPEC.md §13.3` grants only to `deferred` and `mocked`. No current claim uses `fixture_backed`.

**Severity:** Low. Not resolved.

---

### F6 (prior, PRESENT) — `subprocess.run` has no `cwd=` or `timeout=`; `addopts` applied twice

**File:** `tests/test_claim_register_completeness.py`, lines 121–126

No `cwd=REPO_ROOT` (subprocess inherits caller's working directory). No `timeout=` (a hung subprocess blocks indefinitely). `pyproject.toml` `addopts = "-m 'not live_github'"` is re-applied inside each subprocess on top of the explicit `-m` flag — currently idempotent, fragile if `addopts` grows `--cov` or `--timeout`.

**Severity:** Low. Not resolved.

---

## Checks

```shell
python -m pytest tests/test_claim_register_completeness.py  # 14 passed
python -m pytest tests/test_import_boundaries.py            # 16 passed
python -m pytest -m "not live_github" -q                    # 240 passed
python -m mypy src/ubu_phase0                               # no issues
```

---

## Summary Table

| ID | File | Line | Category | Severity | Status |
| --- | --- | --- | --- | --- | --- |
| F1 | `tests/test_import_boundaries.py` | 162 | Schema self-import fix | — | **Resolved** |
| F2 | `fixtures/claim_register.json`, ticket JSON | — | CR-009 and scope amendment | — | **Resolved** |
| — | `src/ubu_phase0/cli.py` | 20 | `affect` import violates §7.2 | Medium | T008 carry-forward |
| F3 | `test_claim_register_completeness.py` | 113–117 | Parametrize reads fixture at collection time | Low | Prior, unresolved |
| F4 | `test_claim_register_completeness.py` | 95–103 | Deferred/mocked test file existence unchecked | Low | Prior, unresolved |
| F5 | `test_claim_register_completeness.py` | 25, 97 | `fixture_backed` exempt with no spec basis | Low | Prior, unresolved |
| F6 | `test_claim_register_completeness.py` | 121–126 | No `cwd=` or `timeout=`; `addopts` double-applied | Low | Prior, unresolved |
