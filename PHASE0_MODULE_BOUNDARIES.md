## 7. `PHASE0_MODULE_BOUNDARIES.md`

### 7.1 Module graph

```
schema
  ├──────────────► affect
  │                  │
  ├──────────────► github_ingest
  │                  │
  └── affect ──────► planner
                       │
   schema + affect ► bootstrap
                       │
schema + affect + planner + bootstrap + github_ingest
                       │
                       ▼
                     loop
                       │
                       ▼
                      cli
```

Layering rule: a module may import only from modules strictly below it in the dependency order. The two roots are `schema` (imported by everything) and the leaf is `cli` (imported by nothing in the project).

### 7.2 Module responsibilities and import rules

**`schema.py`**
- Owns: Pydantic models, constants, literal enums, sentinel values, serialization/deserialization helpers.
- May import: stdlib, pydantic, typing_extensions.
- Forbidden: every other project module; GitHub libraries; environment variables; runtime file I/O.

**`affect.py`**
- Owns: affect preset definitions, the preset-to-sigmoid-parameter expansion, sigmoid evaluation, affect-feasibility checks.
- The preset-to-profile mapping must be a pure function callable independently of any CLI flow (so the v1.5 `recalibrate` command can reuse it).
- May import: schema, math, stdlib.
- Forbidden: planner, github_ingest, bootstrap, loop, cli; file I/O; environment variables; GitHub.

**`github_ingest.py`**
- Owns: GitHub issue normalization, issue-to-`TaskSpec` conversion, label mapping, safe defaults, `authority_source` assignment, PR exclusion, deduplication, fixture-shaped issue conversion, and the optional live-fetch helper.
- May import: schema, stdlib, PyGithub (live adapter only).
- Forbidden: planner, bootstrap, loop, cli. May reference affect-related schema constants for label-to-hint mapping but must not execute the affect gate or perform any planning.

**`planner.py`**
- Owns: the pure `planner(request, logs)` function; DAG validation; topological ordering; fixed-duration scheduling into the four-hour window; affect-feasibility integration; semi-legitimization; candidate construction and ranking; explanation generation; diagnostics.
- May import: schema, affect, stdlib.
- Forbidden: github_ingest, bootstrap, loop, cli; file I/O; environment variables; GitHub.

**`bootstrap.py`**
- Owns: the minimal default affect profile, qualitative preset selection helpers, and the call into the affect preset-to-profile mapping.
- May import: schema, affect.
- Forbidden: planner, github_ingest, loop, cli; file I/O; GitHub.

**`loop.py`**
- Owns: orchestration. Loads config; selects live or fixture source by mode; calls github_ingest; applies the dependency overlay; builds the `PlanningRequest`; calls the planner; loads and validates the claim register (returning a structured object, not a string); assembles a display-ready result.
- May import: schema, affect, planner, bootstrap, github_ingest; the fixture loader; claim-register helpers.
- Forbidden: Rich console output and CLI formatting where avoidable (rendering belongs to cli).

**`cli.py`**
- Owns: Typer command definitions (`demo`, `refresh`); Rich rendering; the `--offline` flag; all human-facing messages.
- May import: loop; schema (for display types); Rich; Typer; stdlib.
- Forbidden: direct planning logic; direct issue-to-task mapping; schema mutation.

### 7.3 Mechanical enforcement

`tests/test_import_boundaries.py` parses the import graph and fails if any of these hold:

- `affect` imports `planner`, `loop`, or `cli`
- `planner` imports `github_ingest`, `bootstrap`, `loop`, or `cli`
- `planner` reads files, environment variables, or GitHub (checked by scanning for `open(`, `os.environ`, `os.getenv`, and GitHub-library imports inside `planner.py`)
- `github_ingest` imports `planner`, `bootstrap`, `loop`, or `cli`
- `schema` imports any project module

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
