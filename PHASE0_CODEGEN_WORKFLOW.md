## 10. `PHASE0_CODEGEN_WORKFLOW.md`

### 10.1 Objective and ownership

Maximize agent-generated code while keeping the architecture coherent. The split:

Human owns: scope, the demo story, claim honesty, GitHub token and repository setup, the documentation packet, review and acceptance, demo rehearsal, cut decisions, and the acceptance-test specifications.

Agents own: implementation code, test code (from human-written specs), fixtures, ticket implementation, lint fixes, and small in-scope refactors.

### 10.2 Sequence

```
docs first  →  schema first (freeze)  →  fixtures  →  tests  →  modules one ticket at a time  →  reviewer-agent after each ticket
```

Stage 0 — documentation packet (human-authored, agent drafts permitted): the eleven files in Section 3.

Stage 1 — repo skeleton: `pyproject.toml`, `README.md`, `src/ubu_phase0/__init__.py`, empty `tests/`, `fixtures/`, `tickets/`. No business logic.

Stages 2–10 — implementation tickets T001–T009 (Section 11). Each ticket is implemented by an agent constrained to its allowed files, then checked by the reviewer agent before the next ticket starts.

Stage 11 — optional v1.5 tickets T010–T015, only if the v1 demo path is stable.

### 10.3 The schema freeze rule

After T001 completes and is accepted, `src/ubu_phase0/schema.py` is frozen. No subsequent ticket may edit it unless that ticket is explicitly a schema-change ticket and the freeze is consciously reopened. This is the single most important discipline in the workflow because schema drift propagates to every downstream module.

### 10.4 Ticket format

Each ticket is a JSON file in `tickets/`:

```json
{
  "id": "PHASE0-T005",
  "title": "Implement deterministic planner and four-hour Calendar preview",
  "goal": "Produce a valid PlanningResponse from a PlanningRequest and a LogEntry list.",
  "allowed_files": [
    "src/ubu_phase0/planner.py",
    "tests/test_topological_order.py",
    "tests/test_calendar_preview_next_four_hours.py",
    "tests/test_affect_gate_rejection.py"
  ],
  "forbidden_files": [
    "src/ubu_phase0/schema.py",
    "src/ubu_phase0/github_ingest.py",
    "src/ubu_phase0/cli.py",
    "src/ubu_phase0/loop.py"
  ],
  "acceptance_tests": [
    "python -m pytest tests/test_topological_order.py tests/test_calendar_preview_next_four_hours.py tests/test_affect_gate_rejection.py"
  ],
  "implementation_notes": [
    "Planner is pure; imports schema and affect only.",
    "Planner must not read files, environment variables, or GitHub.",
    "Planner produces explanations internally.",
    "Planner auto-selects the top candidate as default Plan.",
    "Semi-legitimization is implemented; full legitimization is stubbed."
  ],
  "definition_of_done": [
    "Acceptance tests pass.",
    "Import boundaries are not violated.",
    "No Phase 1 features are introduced.",
    "schema.py is unchanged."
  ]
}
```

### 10.5 Implementation-agent rule

Every implementation-agent prompt includes:

```
Implement only this ticket.
Read AGENTS.md first.
Do not edit forbidden files.
Do not add Phase 1 features.
Do not generalize beyond the ticket scope.
Run the ticket acceptance tests.
Stop when they pass.
Report changed files, test output, and any mypy warnings.
```

### 10.6 Reviewer-agent rule (required between every ticket)

After each implementation ticket and before the next begins, a reviewer agent runs against the diff. Its output is written to `tickets/PHASE0-TXXX-review.md`. The reviewer prompt:

```
Review the diff against AGENTS.md, PHASE0_CUTLIST.md, PHASE0_MODULE_BOUNDARIES.md, and the ticket file.
Look for: scope creep, schema drift, import-boundary violations, hidden network dependency,
GitHub mutation, planner impurity, missing tests, claim-register drift.
Do not refactor unless there is a concrete violation.
Report each finding with file and line.
```

If the reviewer flags a violation, the implementation ticket is reopened and the violation fixed before the next ticket starts. A clean review is recorded in the review file and the workflow advances.

### 10.7 Check commands

```
python -m pytest -m "not live_github"     # blocking
python -m ruff check .                     # blocking
python -m mypy src/ubu_phase0              # advisory; warnings reported, not blocking
```

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
