# PHASE0-T003 Code Review

**Ticket:** GitHub Ingestion  
**Files reviewed:** `src/ubu_phase0/github_ingest.py`, `tests/test_github_issue_fixture_to_tasks.py`, `tests/test_github_label_mapping.py`, `tests/test_github_issue_deduplication.py`  
**Reference docs:** `AGENTS.md`, `PHASE0_CUTLIST.md`, `PHASE0_MODULE_BOUNDARIES.md`, `tickets/PHASE0-T003-github-ingest.json`  
**Verdict:** PASS with two warnings. No blocking violations found.

---

## 1. Scope Creep — CLEAR

Exactly four files created: the three test files and `github_ingest.py`. All are in the ticket's `allowed_files` list. No forbidden files (`schema.py`, `planner.py`, `loop.py`, `cli.py`, `affect.py`, `bootstrap.py`) were touched. No Phase 1 features introduced (no repair mode, no stochastic durations, no GPU, no OAuth).

---

## 2. Schema Drift — CLEAR

Every field written to `TaskSpec`, `DependencyEdge`, and `TaskGraph` matches the frozen `schema.py` exactly:

| Field | schema.py type | github_ingest.py value |
|---|---|---|
| `source` | `Literal["github_issue"]` | `"github_issue"` |
| `authority_source` | `AuthoritySource` | `.imported_config` / `.github_event` |
| `duration` | `FixedDuration(seconds=int)` | constructed correctly |
| `priority` | `Priority` enum | uses enum members, not strings |
| `affect_requirement` | `dict[str, float]` | keys: `energy`, `stress`, `mood_intensity` |
| `dependencies` | `list[str]` | task IDs, not raw issue numbers |
| `raw_labels` | `list[str]` | strings only |

`schema.py` is not imported for mutation anywhere; it is read-only here. Schema is frozen and clean.

---

## 3. Import-Boundary Violations — CLEAR

Top-level imports in `github_ingest.py`: `__future__`, `json`, `logging`, `warnings`, `pathlib`, `typing`, `ubu_phase0.schema`. All are stdlib or schema — both permitted.

PyGithub (`from github import Github`) is imported inside `ingest_live()` under a `try/except ImportError`, making it a soft optional dependency. This matches the module rule: "May import: schema, stdlib, PyGithub (live adapter only)."

Forbidden imports (`planner`, `bootstrap`, `loop`, `cli`, `affect`) are absent.

---

## 4. Hidden Network Dependency — CLEAR

`ingest_live` requires network, but it is never called by `ingest_fixture` or any test. All three test files call `ingest_fixture` only, using local fixture files at `fixtures/static_dummy_issue.json` or `tmp_path`-scoped synthetic fixtures. No test requires network access or a GitHub token. CI will not hit GitHub.

---

## 5. GitHub Mutation — CLEAR

`ingest_live` calls only `g.get_repo()` and `gh_repo.get_issues(state="open")`, both read-only PyGithub operations. Label and issue attribute access is read-only. No create/edit/close/comment/assign/label/PR/board operation is present anywhere.

---

## 6. Planner Impurity — CLEAR

`github_ingest.py` does not import `planner`, `affect`, `bootstrap`, `loop`, or `cli`. No affect-gate evaluation is performed; affect values are stored as raw floats on `TaskSpec.affect_requirement` for the planner to consume later. No scheduling logic is present.

---

## 7. Acceptance Tests — CLEAR

All three required test files are present and non-empty:

- `test_github_issue_fixture_to_tasks.py` — 11 tests covering count, PR exclusion, authority source, ID format, source field, dependency edges, deterministic ordering, per-issue label mapping, external URL, external ID.
- `test_github_label_mapping.py` — 28 tests covering all four duration values plus default, all three priority values plus default, all three affect-dimension values plus defaults, depends-on parsing, unknown label preservation, conflict (duplicate same-family) resolution with warning.
- `test_github_issue_deduplication.py` — 8 tests covering baseline no-dup, dup-by-number, first-occurrence retention, deterministic order, order-independence, idempotence, PR exclusion before dedup, all-PR yields empty list.

No live-GitHub tests are present, which is correct; the standard test run excludes the `live_github` marker per `AGENTS.md`.

---

## 8. Claim-Register Drift — NOT APPLICABLE

`github_ingest.py` contains no claim-register logic. The claim register lives in `loop.py` (T009). No drift.

---

## WARNINGS (non-blocking)

### W1 — `TaskSpec.dependencies` populated from labels in fixture mode

**Location:** `github_ingest.py:189–217` (`_issue_dict_to_task_spec`) and `225–256` (`ingest_fixture`)

`_issue_dict_to_task_spec` parses every issue's `ubu:depends-on:#N` labels and stores the resulting task IDs in `TaskSpec.dependencies`. This happens in both fixture and live mode. In fixture mode, however, `ingest_fixture` also builds `TaskGraph.dependency_edges` exclusively from `hardcoded_dependency_edges` (not from `task.dependencies`).

In the canonical fixture, issues 12, 15, and 19 carry `ubu:depends-on` labels. After ingestion:
- `task.dependencies` on those TaskSpecs will contain label-derived dep IDs.
- `graph.dependency_edges` will contain the hardcoded edges (which happen to encode the same relationships).

These two sources are independent and overlap. No test asserts the content of `task.dependencies` in fixture mode. The planner (T005) must treat `TaskGraph.dependency_edges` as the authoritative DAG and not additionally iterate `TaskSpec.dependencies`, or it will double-count edges.

**Recommendation for T005:** Document in the planner which field is authoritative. Do not merge both sources without deduplication.

### W2 — Malformed `ubu:depends-on:#N` labels silently dropped from `raw_labels`

**Location:** `github_ingest.py:176–185`

`_DEPENDS_ON_PREFIX` (`"ubu:depends-on:#"`) is included in `_KNOWN_PREFIXES`, so any label starting with it is excluded from the catch-all `raw_labels` loop at lines 141–145. In the depends-on parsing loop, if `int(ref_num_str)` raises `ValueError` (e.g., label `ubu:depends-on:#abc`), the code logs a warning and skips — it does not append the label to `raw_labels`.

The ticket states: *"Unknown labels preserved in raw_labels, never failure-causing."* A label with a recognised prefix but an unparseable suffix is functionally unknown after the prefix match; the same pattern for duration produces `_resolve_family` returning `(None, [chosen_label])` which extends `raw_labels`. The depends-on path is inconsistent with this convention.

**Recommendation for T003 or T005:** After the `ValueError` catch, append `lbl` to a `raw_labels` accumulator before returning from `_parse_labels`. A test for this edge case should be added.

---

## INFO

- **`ingest_live` is untested.** Expected — a live test requires a GitHub token and is excluded from the standard run. Acceptable per ticket scope. The live path is structurally symmetric with the fixture path and follows the same deduplication and ordering contract.
- **Tests import private symbols** (`_parse_labels`, `_make_task_id`). Acceptable for a demo prototype's acceptance tests, but couples tests to internals. Not a violation.
