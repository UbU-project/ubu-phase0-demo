# UbU Phase 0 — Preparation and Code-Generation Process

**Document type:** Master process specification
**Target milestone:** ETHConf NYC, June 8–10, 2026
**Implementation repository:** `https://github.com/UbU-project/ubu-phase0-demo`
**Design authority:** `https://github.com/UbU-project/ubu-design` at commit `5ab5315` (Phase 1 design frozen at `cc8b339`)
**Profile identifier:** `planning-kernel-contract/phase0-profile/0.1`

---

## 0. How to read this document

This is the single authoritative document for building UbU Phase 0. It contains the full decision set, the complete documentation packet, the code-generation workflow, the ticket structure, the acceptance-test spine, and the reserved v1.5 feature set.

The document is organized so that the eleven `PHASE0_*.md` packet files can be extracted from it section by section. Section numbers map to packet files where indicated. Where this document says "this section is the content of `PHASE0_X.md`," the prose below the heading is intended to be copied into that file with light editing.

The governing discipline is stated once and applies throughout: **Phase 0 is a standalone demo prototype. It is not Phase 1, not production architecture, and its code is not assumed to survive into Phase 1.** What survives Phase 0 is the experience, the fixtures, the schema examples, the claim-register structure, and the demonstrated patterns — not the Python.

Two rules dominate every tradeoff:

1. The schema is frozen after the first ticket. Schema changes after freeze are the most expensive change in this architecture. Only fields needed by v1 or near-certain v1.5 features are given schema slots now. Other Phase 1 optionality is reserved in documentation and ticket IDs, not in the frozen schema.
2. Preserving optionality is cheap when it is documentation-only and expensive when it is retrofit. Filenames, ticket IDs, enum values, and module-boundary shapes for deferred features are reserved now.

---

## 1. Purpose and demo thesis

Phase 0 demonstrates the core UbU loop end to end, in Python, from a terminal:

```
GitHub project state
  → UbU Task objects
  → PlanningRequest
  → dependency-aware, affect-aware planning
  → four-hour Calendar preview
  → honest claim register
```

The minimum successful demo ends when the CLI displays a Calendar preview for today's next four hours, with each scheduled Task showing where it came from, how close it sits to the affect threshold, and an honest footer about what Phase 0 does not model.

The demo thesis, stated for the audience:

> This GitHub issue became a UbU Task. UbU understood enough about the work to place it into a Calendar preview, respecting dependencies and the operator's current affect state. UbU can explain the preview. UbU is explicit about what is live, what is fixture-backed, and what is deferred to Phase 1.

The demo must be impressive because it is **concrete**, not because it is broad. The primary demonstration value is project self-planning / dogfooding: UbU uses public GitHub project state to coordinate its own Phase 0 preparation. This may foreshadow later Association and organizational-introspection work, but Phase 0 does not claim to implement those features.

---

## 2. Consolidated decision set

This section is the canonical decision record. Every later section is downstream of it. If a later section appears to contradict this one, this section wins and the later section is in error.

### 2.1 Scope and milestone

- ETHConf NYC, June 8–10, 2026.
- Standalone Python prototype; code reuse into Phase 1 is not assumed.
- New public repository `ubu-phase0-demo`, separate from the `ubu-design` design repository.
- Package name `ubu_phase0`.
- Profile identifier `planning-kernel-contract/phase0-profile/0.1`.

### 2.2 Stack

- Python 3.12.
- Pydantic v2, Typer, Rich, pytest, ruff, PyGithub.
- mypy is included but **advisory, not blocking**. mypy warnings are reported in ticket summaries; they do not fail a ticket.

### 2.3 UI

- CLI/Rich only. No Streamlit.
- Two commands in v1: `demo` and `refresh`.
- `--offline` is a **hard switch** flag on `demo`. It is mutually exclusive with live fetch. There is no auto-fallback.
- Calendar preview window is today, next four hours.
- Audience-created issues are pulled in by the operator typing `refresh`, which writes a small JSON cache at `.ubu-phase0/live_issues.json`. No polling, no background service.

### 2.4 Data sources

- Live source: `UbU-dummy/ubu-design` GitHub repository, accessed via an environment-variable token.
- Fixture source: a single canonical file `fixtures/static_dummy_issues.json`, which serves simultaneously as the test fixture and the offline corpus.
- Live refresh cache: `.ubu-phase0/live_issues.json`. The `refresh` command fetches live GitHub issues and writes this cache so a later `demo` invocation can use the refreshed live snapshot.
- Mode is selected by the operator: live by default, fixture via `--offline`. `--offline` is mutually exclusive with live fetch. A live-mode error fails visibly and exits non-zero; it does not silently fall back to fixtures.

### 2.5 Schema (frozen after ticket T001)

- Pydantic v2 models.
- Sentinel constants `PHASE0_PROFILE`, `PHASE0_NOT_SUPPORTED`, `PHASE0_NOT_ESTIMATED`.
- No `Omitted` wrapper class. Deferred Phase 1 fields are present as `Optional[...] = None` or literal sentinels.
- Schema fields are classified into three levels: v1 required fields, v1.5 reserved-but-tested-lightly fields, and deferred Phase 1 fields documented only rather than added to the frozen schema.
- The schema includes `LogEntry`, `SkeletonFailureDiagnostic`, and `PlanCandidate.semi_legitimization_summary` as v1.5 reserved fields even though v1 may not exercise them.
- `TaskSpec.authority_source` is present and populated by `github_ingest` (Phase 1 pull-in, adopted into v1).

### 2.6 Planner

- Pure function: `planner(request: PlanningRequest, log_entries: list[LogEntry]) -> PlanningResponse`.
- No file I/O, no environment-variable access, no GitHub access, no mutation of inputs.
- Explanations are generated inside the planner. No separate `explanations` module.
- The planner auto-selects the top (or first-equal) candidate and declares it the default Plan. This is deliberately against the Phase 1 full-legitimization rule and is a documented Phase 0 simplification.
- Semi-legitimization is implemented as a deterministic cheap-check summary. It passes iff the dependency graph is acyclic, fixed durations fit inside the four-hour window, no scheduled task violates affect feasibility, and no dependency is scheduled after its dependent. Full legitimization is stubbed.
- Fixed-duration tasks only.
- Topological ordering over a dependency DAG.

### 2.7 Affect

- Three dimensions: `energy`, `stress`, `mood_intensity`.
- Directions per the frozen contract: `energy` higher-is-better, `stress` lower-is-better, `mood_intensity` lower-is-better.
- Bootstrap exposes qualitative choices only; raw sigmoid parameters stay internal.
- Skip-calibration defaults: `medium` energy, `low` stress, `calm` mood.
- Calibration runs once at demo start, not between replans.

### 2.8 GitHub ingestion

- Labels only for directives; issue bodies are not parsed in v1.
- Duration via `ubu:duration:Xm` labels, default 30 minutes.
- Duplicate labels in the same family: take the first alphabetically and warn.
- Dependencies are independent by default, may be supplied by a local dependency overlay, and may also be supplied by optional `ubu:depends-on:#N` labels. Overlay edges have priority over label-derived edges. Fixture dependencies live in `static_dummy_issues.json`.
- Missing dependency target from an overlay or `ubu:depends-on:#N` label: warn, treat the dependency as absent, log the event, do not crash.
- Pull requests excluded via the `pull_request` metadata check.
- Deduplication by `source_ref`.
- Unknown labels preserved for display, never failure-causing.

### 2.9 Persistence

- JSON files only. No SQLite. The reason is transparency: fixtures and outputs are visually inspectable.

### 2.10 Claim register

- A single JSON file at `fixtures/claim_register.json`.
- Demo-claim granularity is primary; `modules` is metadata on each claim.
- Status values: `implemented`, `fixture_backed`, `mocked`, `deferred`.
- Loaded and validated by `loop.py`. There is no `claims.py` module.
- Rendered as a section of `demo` output. There is no standalone `claims` command in v1.
- Completeness rule: every `implemented` claim names an existing, passing test.

### 2.11 Module boundaries

- `schema → affect → planner → bootstrap → loop → cli`.
- `schema → github_ingest → loop`.
- Mechanical enforcement via `tests/test_import_boundaries.py`.
- The bootstrap preset-to-profile mapping is callable from outside the bootstrap CLI flow (so the v1.5 `recalibrate` command can reuse it).
- The loop's claim-register loader returns a structured object, not a rendered string (so a v1.5 standalone `claims` command can reuse it).

### 2.12 Calendar preview rendering

- Rich table, one row per scheduled Task.
- Columns: time, label, source (`authority_source`), affect-margin indicator.
- Affect margin rendered as a three-character visual: `▁▁▁` low, `▃▃▃` medium, `▆▆▆` healthy.
- Footer line shows `probability_quality: not_estimated` and `coverage_estimate: —`, each annotated "(Phase 1 will populate)".
- When v1.5 log-replan fires, a "Completed" section is shown above the new Calendar preview.

### 2.13 Failure handling

- In live mode: missing token, invalid token, network failure, and rate limit each produce a clean message and a non-zero exit. They do not fall back.
- Empty issue list, malformed issue, dependency cycle: handled per `PHASE0_DEMO_FAILURE_MODES.md` (Section 9 of this document).
- v1 avoids deliberately triggering `SkeletonFailureDiagnostic`. The v1.5 stretch deliberately triggers and renders it.

### 2.14 Code-generation workflow

- The documentation packet is human-authored. Agents may produce drafts, but every packet file is human-reviewed and accepted before any implementation ticket begins.
- The schema is frozen after T001 and not edited by any later ticket unless that ticket is explicitly a schema-change ticket.
- Ticket sequence T001–T009 builds v1. Ticket IDs T010–T015 are reserved for v1.5.
- A reviewer-agent step runs between every implementation ticket; its output is captured in `tickets/PHASE0-TXXX-review.md`.
- Acceptance tests are agent-written in Python from human-written specs in `PHASE0_ACCEPTANCE_TESTS.md`. The test specification is human-owned; the test code is agent-owned.
- Phase 0 code optimizes for the canonical demo path and the documented failure modes. It does not add defensive generalization beyond ticket scope.

### 2.15 Auto-generation expectation

- v1 Python code: 88–92% agent-generated and acceptable on first pass; working assumption 90%.
- Residual concentrated in three predictable areas: PyGithub integration against the live repository, Rich visual polish, and bootstrap prompt wording. None of these can be specified away.

---

## 3. Required documentation packet

Before any implementation code is generated, the following eleven files are authored and human-accepted. They are the rails for code generation; the implementation should be almost mechanically derivable from them plus the fixtures, tests, and tickets.

```
PHASE0_PLAN.md
PHASE0_CUTLIST.md
PHASE0_CONTRACT_PROFILE.md
PHASE0_MODULE_BOUNDARIES.md
PHASE0_GITHUB_INGESTION.md
PHASE0_DEMO_FAILURE_MODES.md
PHASE0_CODEGEN_WORKFLOW.md
PHASE0_ACCEPTANCE_TESTS.md
PHASE0_DEMO_SCRIPT.md
PHASE0_CLAIM_REGISTER_SPEC.md
AGENTS.md
```

Sections 4 through 14 below are the content of these files. The reviewer of this document should treat each of those sections as the draft of the corresponding packet file.

---

## 4. `PHASE0_PLAN.md`

### Demo objective

Phase 0 is a Python-only ETHConf NYC demo prototype. It is not the production Phase 1 implementation.

The demo shows that UbU can:

1. ingest project state from GitHub issues,
2. map issues into UbU Task objects with explicit provenance,
3. build a Phase 0 `PlanningRequest`,
4. run a deterministic, dependency-aware, affect-aware planner,
5. produce a four-hour Calendar preview with affect-margin indicators,
6. show an honest claim register.

The required UI is CLI/Rich. Live GitHub ingestion is the default; fixture mode is selected with `--offline`. The canonical live source is `UbU-dummy/ubu-design`.

### Required end state

`ubu-phase0 demo` must:

1. Load environment and configuration.
2. Select data source: live GitHub (default) or fixture (`--offline`).
3. In live mode, use `.ubu-phase0/live_issues.json` if present; otherwise attempt a live fetch and write that cache. On live fetch error, fail cleanly and exit non-zero. Do not silently fall back to fixtures.
4. Convert issues into `TaskSpec` objects with `authority_source` set.
5. Apply safe defaults and any `ubu:` labels.
6. Apply dependency information in priority order: local overlay first, optional `ubu:depends-on:#N` labels second, otherwise independent by default.
7. Build a `PlanningRequest`.
8. Run the planner.
9. Display the Calendar preview for today's next four hours, with source and affect-margin columns and the probability/coverage footer.
10. Print the claim-register summary.

### Stretch end state (v1.5)

11. Operator marks one Task complete (single key).
12. Planner reruns with the same `PlanningRequest` plus the accumulated `LogEntry` list.
13. CLI shows a "Completed" section above a changed Calendar preview.

---

## 5. `PHASE0_CUTLIST.md`

This file exists to prevent scope creep. It has four sections: in scope, reserved for v1.5, out of scope, and cut-order if the schedule slips.

### In scope (v1)

- Python CLI demo (`demo`, `refresh`).
- Pydantic v2 schema with the Phase 0 contract profile.
- Live GitHub issue ingestion against `UbU-dummy/ubu-design`.
- Fixture mode via `--offline` using `static_dummy_issues.json`.
- GitHub issue to `TaskSpec` conversion with `authority_source`.
- Manual `refresh` that writes `.ubu-phase0/live_issues.json`.
- Safe label mapping (duration, priority, affect hints).
- Dependency handling: local overlay first, optional live labels second, independent by default.
- Fixed-duration tasks only.
- Deterministic CPU planner with topological ordering.
- Affect presets and the sigmoid affect gate.
- Four-hour Calendar preview with source and affect-margin columns and the probability/coverage footer.
- Planner-generated explanations.
- Claim register JSON, loaded by the loop, rendered inside `demo`.
- Acceptance tests.
- Import-boundary tests.

### Reserved for v1.5 (do not implement in v1; do not foreclose)

- Log-replan with a "Completed" section above the new preview.
- Deliberate impossible-graph `SkeletonFailureDiagnostic` demo (`--demo-impossible` flag).
- Standalone `claims` command.
- `recalibrate` mid-demo command.
- Issue-body `ubu:` directive parsing (labels take precedence).
- Minimal `doctor` command.
- Calibration example surfacing (the six neutral frames from UBU-D0200).

### Out of scope (do not implement, do not reserve)

- Streamlit or any web UI.
- OAuth.
- GitHub mutation of any kind (create, edit, close, comment, assign, label, PR, project board).
- GitHub comment, pull-request, CI, milestone, or project-board ingestion.
- LLM-based or free-text dependency inference.
- Persistent on-disk caches other than the explicitly allowed live refresh snapshot `.ubu-phase0/live_issues.json`.
- Production persistence semantics.
- Multi-user behavior; full Identity, Compartment, Relationship, or Association models.
- Repair mode.
- GPU planning, Monte Carlo rollout, stochastic duration modeling, correlation matrices.
- Release Outreach Pipeline.
- `model-committee` integration (it runs independently, offline to the demo).
- Skill, Resource, Technique modeling.
- `pipeline_state` projection metadata.

### Cut order if the schedule slips

Cut in this order; stop as soon as the schedule is recovered:

1. Probability/coverage footer (cosmetic; cheapest to drop).
2. Affect-margin visual indicator (keep the binary feasible/infeasible result).
3. `refresh` command polish (operator can run `demo` live directly, or use `--offline`).
4. Dependency overlay for live issues (fixture edges remain).

Do not cut, under any circumstances: GitHub issue to `TaskSpec` conversion, fixture mode, the frozen schema, the affect preset table, the dependency-aware planner, the Calendar preview, the claim register, the CLI `demo` path.

---

## 6. `PHASE0_CONTRACT_PROFILE.md`

This is the most important specification file. It defines the Phase 0 subset of the frozen `planning-kernel-contract/0.1`.

### 6.1 Profile identifier and constants

```python
PHASE0_PROFILE = "planning-kernel-contract/phase0-profile/0.1"
PHASE0_NOT_SUPPORTED = "not_supported"
PHASE0_NOT_ESTIMATED = "not_estimated"
```

The Phase 1 baseline `schema_version` is `planning-kernel-contract/0.1`. Phase 0 objects carry the Phase 1 `schema_version` for replay compatibility and additionally carry the `profile` field set to `PHASE0_PROFILE`. This makes a Phase 0 artifact unmistakable while keeping it a valid subset of the frozen contract.

### 6.2 Schema-slot levels

The frozen schema distinguishes three levels:

1. **v1 required fields** — implemented and exercised by the required CLI demo and blocking tests.
2. **v1.5 reserved-but-tested-lightly fields** — present because they are near-certain stretch additions and would be expensive to add after the schema freeze. These fields may be populated with `None`, `PHASE0_NOT_SUPPORTED`, or `PHASE0_NOT_ESTIMATED` in v1, but their serialization shape is tested.
3. **Deferred Phase 1 fields** — documented only, not added to the frozen Phase 0 schema. Do not add broad Phase 1 optionality merely to preserve speculative future choices.

Schema additions after T001 require an explicit schema-change ticket.

### 6.3 Supported envelope fields

Carried and populated by Phase 0:

- `schema_version` = `planning-kernel-contract/0.1`
- `profile` = `planning-kernel-contract/phase0-profile/0.1`
- `planner_version`
- `request_id`
- `effective_time` (authoritative planning start; for the demo, the current local time rounded to the next clean boundary)
- `generated_at`
- `rng_seed`

### 6.4 `PlanningRequest` — Phase 0 subset

Supported and meaningful:

- `mode` = `fresh_generation` only. `repair` is not supported in Phase 0.
- `time_window` with `start_time`, `end_time` (start + 4 hours), and `planning_delta_seconds` = 60.
- `task_graph` with `tasks`, `dependency_edges`, and a CPU-supplied `topological_order`. In Phase 0 the planner computes the order itself from the edges; the field is populated for contract fidelity.
- `affect_profile` per §6.7.
- `constraint_policy.affect_constraint_mode` = `enforce` for the demo; `warn_only` permitted in test fixtures.
- `scoring_policy` weights with Phase 0 defaults (utility, robustness, affect-margin, schedule-diversity). Robustness and schedule-diversity may be set to 0 in Phase 0 since no stochastic modeling exists.
- `explanation_request` with `include_user_facing_fragments` = true.

Present but inert (carried as `None` or sentinel, not removed):

- `horizon_policy` — present; `branch_coverage_target` may be carried but is not used because no coverage is estimated.
- `compute_budget` — present with Phase 1 defaults; `n_rollouts` is 0 because there is no rollout.
- `universe_state_snapshot` — present with a minimal snapshot id and effective time; rich state facts are not modeled.
- `scoring_policy.robustness_weight`, `schedule_diversity_weight` — present, may be 0.
- `privacy_and_provenance` — present; `payload_safety_proof` carries `PHASE0_NOT_SUPPORTED`, `payload_verified_safe` is true by construction because Phase 0 uses only public dummy data.

Not supported (absent or sentinel; never invented):

- `repair_context` — absent (no repair mode).
- `external_event_assumptions` — empty list.
- Deferred Phase 1 fields (mobile GPU, cloud GPU, encrypted compute, cross-user, realtime, premium provider) — absent.

### 6.5 `TaskSpec` — Phase 0 subset

Phase 0 `TaskSpec` carries:

- `id` (form `github:UbU-dummy/ubu-design#N`)
- `title`
- `description` (issue body or empty string)
- `source` = `github_issue`
- `source_ref` (same as `id`)
- `external_id` (issue number as string)
- `external_url` (issue `html_url`)
- `authority_source` (Phase 1 pull-in; see §6.6)
- `duration` — fixed model only
- `priority` (label-derived or `medium`)
- affect hints (label-derived or safe defaults)
- `dependencies` (overlay-derived or empty)

Duration uses the fixed model from the frozen contract:

```json
{ "type": "fixed", "seconds": 1800 }
```

The shifted-log-normal model, `correlation_groups`, and all stochastic duration features are **not supported** in Phase 0. The fixed model must be represented as a delta distribution, never as a tight log-normal.

### 6.6 `authority_source` (UBU-D0185, adopted into v1)

`authority_source` is the closed MVP enum from UBU-D0185. Phase 0 populates it on every Task:

- live GitHub issue → `github_event`
- the static fixture issue → `imported_config`
- a Task created or overridden by the operator → `user_override`

The full enum is carried in the schema for fidelity: `human_admin`, `automation_worker`, `github_event`, `project_policy`, `imported_config`, `llm_advisory`, `user_override`. Phase 0 only emits `github_event`, `imported_config`, and `user_override`. `authority_source` is provenance, not authorization; it does not gate anything in Phase 0.

### 6.7 Affect dimensions and preset table

Phase 0 supports exactly `energy`, `stress`, `mood_intensity`, with the frozen-contract directions: `energy` higher-is-better, `stress` lower-is-better, `mood_intensity` lower-is-better (arousal/volatility, not valence).

The sigmoid satisfaction function from the frozen contract:

```
higher_is_better: satisfaction = sigmoid((x - location) / scale)
lower_is_better:  satisfaction = sigmoid((location - x) / scale)
```

A candidate is affect-feasible only if every active dimension has `satisfaction >= threshold` at the evaluation point.

The Phase 0 bootstrap preset table (copy verbatim; these expand internally to sigmoid parameters and are never shown to the user):

```
ENERGY
  low:    location=3.0, scale=1.0, threshold=0.5
  medium: location=4.0, scale=1.5, threshold=0.5
  high:   location=6.0, scale=1.5, threshold=0.3

STRESS
  low:    location=7.0, scale=1.5, threshold=0.5
  medium: location=5.5, scale=1.2, threshold=0.5
  high:   location=4.0, scale=1.0, threshold=0.6

MOOD_INTENSITY
  calm:     location=8.0, scale=1.5, threshold=0.5
  engaged:  location=6.5, scale=1.2, threshold=0.5
  intense:  location=5.0, scale=1.0, threshold=0.6
```

The `medium` energy, `low` stress, and `calm` mood rows correspond to the frozen-contract conservative bootstrap defaults (`energy` location 4.0, `stress` location 7.0, `mood_intensity` location 8.0). These are the Phase 0 skip-calibration defaults.

Bootstrap exposes only qualitative choices:

```
energy:         low | medium | high
stress:         low | medium | high
mood_intensity: calm | engaged | intense
```

Skip-calibration defaults: `energy = medium`, `stress = low`, `mood_intensity = calm`. These are the most permissive combination that still lets the gate fire on demonstrably stressful tasks, which is what the demo needs.

### 6.8 `PlanningResponse` — Phase 0 subset

Supported:

- `schema_version`, `planner_version`, `request_id`, `rng_seed_echo`, `generated_at`
- `status` — `ok`, `partial`, `rejected`, `engine_error`. Phase 0 normally returns `ok`.
- `plan_candidates` — ranked list; Phase 0 returns at least one and auto-selects the top.
- `diagnostics`:
  - `skeleton_failure_diagnostics` — empty in v1 (no deliberate failure); populated in the v1.5 impossible-graph stretch.
  - `probability_quality` = `not_estimated`.
  - coverage fields (`coverage_scope`, `coverage_estimate`, `uncovered_mass_estimate`, `coverage_threshold_used`, `coverage_below_threshold`) — null.
  - `warnings` — used for ingestion warnings surfaced through the loop.

### 6.9 `PlanCandidate` — Phase 0 subset

Each candidate carries:

- `candidate_id`, `rank`, `candidate_role` (Phase 0 uses `highest_utility`)
- `schedule` — ordered Task placements within the four-hour window
- `score_summary` — `utility_score`, `affect_margin_score` (surfaced in the preview), `total_score`; `robustness_score` and `schedule_diversity_score` may be 0
- `feasibility_summary` — `affect_feasible`, `minimum_affect_score`, `violated_affect_dimensions`; `hard_constraints_assumed_satisfied_by_engine` is advisory
- `semi_legitimization_summary` — implemented in Phase 0: `result` (`passes_cheap_checks` / `reject_obvious` / `needs_full_legitimization`), `affect_budget_ok`, and the other cheap-check booleans where computed. Semi-legitimization passes iff: the dependency graph is acyclic; fixed durations fit inside the four-hour window; no scheduled task violates affect feasibility; and no dependency is scheduled after its dependent.
- `probability_summary` — `provenance_refs` carries `PHASE0_NOT_ESTIMATED`; numeric fields null
- `explanation_fragments` — generated by the planner

### 6.10 Planner purity

```python
planner(request: PlanningRequest, log_entries: list[LogEntry]) -> PlanningResponse
```

The planner does not mutate `request`, does not read files, does not call GitHub, does not read environment variables, and produces explanations internally. It derives effective task state from `request` plus `log_entries`: completed tasks are filtered, blocked tasks are flagged, skipped tasks are ignored for Phase 0.

### 6.11 `LogEntry` (schema present in v1, exercised in v1.5)

`LogEntry` is fully defined in the v1 schema even though v1 constructs only the empty list. Minimum fields: `task_ref`, `outcome` (`completed` / `skipped` / `blocked`), `effective_time`, and an optional `authority_source` (typically `user_override`). Defining it now avoids a post-freeze schema change when log-replan is added.

---

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

## 8. `PHASE0_GITHUB_INGESTION.md`

### 8.1 Source repository and configuration

```
owner: UbU-dummy
repo:  ubu-design
url:   https://github.com/UbU-dummy/ubu-design
```

Environment variables:

```
UBU_PHASE0_GITHUB_TOKEN   (required for live mode; never committed)
UBU_PHASE0_GITHUB_OWNER   (default UbU-dummy)
UBU_PHASE0_GITHUB_REPO    (default ubu-design)
```

The intended token is a fine-grained, read-only token scoped to `UbU-dummy/ubu-design` with Issues and metadata permissions only. The implementation must not require broader permissions.

### 8.2 Mode selection

- Default: live. `demo` fetches open issues from the configured repository.
- `--offline`: fixture mode. `demo` reads `fixtures/static_dummy_issues.json` and never touches the network.
- Live cache: `.ubu-phase0/live_issues.json`. The `refresh` command fetches live GitHub issues and writes this cache. `demo` may read the cache when present; if no cache exists, it may attempt a live fetch and write the cache.
- The two modes are mutually exclusive. There is no auto-fallback from live mode to fixture mode.
- The CLI must report the active source on every run (see `PHASE0_DEMO_SCRIPT.md`).

### 8.3 Data read from issues

Supported: issue number, title, body, labels, state, `html_url`, `created_at`, `updated_at`.

Ignored: comments, pull requests, CI, milestones, assignees, project boards, reactions, linked branches.

### 8.4 Issue-to-`TaskSpec` mapping

For issue number `N` in `UbU-dummy/ubu-design`:

```
id            = github:UbU-dummy/ubu-design#N
title         = issue title
description   = issue body or ""
source        = github_issue
source_ref    = github:UbU-dummy/ubu-design#N
external_id   = "N"
external_url  = issue html_url
authority_source = github_event   (imported_config for the static fixture issue)
duration      = label-derived, default fixed 30 minutes (1800 seconds)
priority      = label-derived, default medium
affect hints  = label-derived, else safe defaults
dependencies  = overlay edges first, optional depends-on label edges second, else []
```

### 8.5 Pull-request exclusion

The GitHub `/issues` endpoint returns pull requests alongside issues. If an item carries `pull_request` metadata, skip it. This rule is mandatory; agents miss it without explicit instruction.

### 8.6 Deduplication

Deduplicate by `source_ref` (equivalently owner/repo/number). The deduplicated result must be deterministic in ordering.

### 8.7 Label mapping

Supported label families:

```
ubu:duration:15m | ubu:duration:30m | ubu:duration:60m | ubu:duration:90m
ubu:priority:low | ubu:priority:medium | ubu:priority:high
ubu:energy:low-ok | ubu:energy:medium | ubu:energy:high
ubu:stress:low | ubu:stress:medium | ubu:stress:high-risk
ubu:mood:calm | ubu:mood:engaged | ubu:mood:intense-risk
ubu:depends-on:#N   (dependency edge; see 8.9)
```

Conflict rule: when an issue carries more than one label in the same family, take the first one alphabetically and emit a warning. Never silently merge.

Unknown labels: preserve for display, do not fail import, do not affect scheduling.

### 8.8 Safe defaults

```
duration_minutes    = 30
priority            = medium
energy_requirement  = medium
stress_risk         = medium
mood_intensity_risk = engaged
dependencies        = []
```

An unlabeled issue must import successfully under these defaults.

### 8.9 Dependencies

Dependency policy for v1:

- Imported GitHub issues are independent by default.
- A local dependency overlay is the highest-priority dependency source.
- Optional `ubu:depends-on:#N` labels may add dependencies when no overlay edge already controls the same task.
- Issue bodies are not parsed in v1.
- A dependency target that does not exist in the imported set or has been closed: emit a warning, treat the dependency as absent, log the event, continue. Do not crash and do not drop the dependent issue from the plan.
- Cycles are reported clearly by the planner's DAG validation and surfaced by the CLI.

Fixture dependency edges live inside `fixtures/static_dummy_issues.json` so that fixture mode is fully deterministic and self-contained. A separate local overlay file may also be used in tests or live-mode rehearsals.

---

## 9. `PHASE0_DEMO_FAILURE_MODES.md`

The demo fails predictably and never silently. Live-mode credential and network failures are clean non-zero exits; data-shape problems degrade gracefully.

| Condition | Mode | Behavior |
|---|---|---|
| Missing token | live | Clean message naming `UBU_PHASE0_GITHUB_TOKEN`; non-zero exit. No fallback. |
| Invalid token | live | Clean message (note GitHub may surface this as a 404, not 401); non-zero exit. |
| Network failure | live | Clean message; non-zero exit. |
| Rate limit | live | Clean message with reset time if available; non-zero exit. |
| Empty issue list | live | Warn that no open issues were found; exit cleanly. Operator may rerun with `--offline`. |
| Malformed issue | either | Skip the issue, report the skipped count, continue if at least one valid Task remains. |
| Duplicate issue | either | Deduplicate by `source_ref`, report the duplicate count if useful, continue. |
| Missing dependency target | either | Warn, treat as absent, log, continue. |
| Dependency cycle | either | Planner reports an invalid dependency graph; CLI shows a clear error. In fixture mode the bundled edges are known-acyclic, so this only arises from live audience input. |
| No feasible tasks after affect gate | either | Show an empty Calendar preview with an explanation of why nothing was scheduled. Do not crash. |
| Fixture missing | offline | Hard failure naming the missing path. |

The `--offline` switch removes the entire first block of credential/network failure modes by construction, which is its purpose as a demo safety net.

---

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
    "Semi-legitimization is the deterministic cheap-check summary defined in PHASE0_CONTRACT_PROFILE.md; full legitimization is stubbed."
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

## 11. Ticket sequence

### v1 tickets

**PHASE0-T001 — schema (then freeze)**
Allowed: `src/ubu_phase0/schema.py`, `tests/test_schema_contract.py`, `tests/test_contract_roundtrip.py`.
Forbidden: all other modules.
After acceptance, `schema.py` is frozen.

**PHASE0-T002 — fixtures**
Allowed: `fixtures/static_dummy_issues.json`, `fixtures/demo_dependency_overlay.json`, `fixtures/demo_request.json`, `fixtures/demo_log_empty.json`, `fixtures/claim_register.json`, `.ubu-phase0/.gitkeep` if needed, `tests/test_contract_roundtrip.py`.
Also reserve (create as empty/placeholder for v1.5): `fixtures/demo_log_after_task1.json`, `fixtures/demo_response_initial.expected.json`, `fixtures/demo_response_replanned.expected.json`, `fixtures/impossible_dependency_demo.json`.

**PHASE0-T003 — github_ingest**
Allowed: `src/ubu_phase0/github_ingest.py`, `tests/test_github_issue_fixture_to_tasks.py`, `tests/test_github_label_mapping.py`, `tests/test_github_issue_deduplication.py`.
No planner or CLI code.

**PHASE0-T004 — affect**
Allowed: `src/ubu_phase0/affect.py`, `tests/test_affect_gate_rejection.py`.
The preset-to-profile mapping is a standalone pure function.

**PHASE0-T005 — planner**
Allowed: `src/ubu_phase0/planner.py`, `tests/test_topological_order.py`, `tests/test_calendar_preview_next_four_hours.py`, `tests/test_affect_gate_rejection.py`.
Preserve purity; generate explanations internally; auto-select top candidate.

**PHASE0-T006 — bootstrap**
Allowed: `src/ubu_phase0/bootstrap.py`, `tests/test_bootstrap_defaults.py`.

**PHASE0-T007 — loop**
Allowed: `src/ubu_phase0/loop.py`, `tests/test_live_missing_token_fails_cleanly.py`, `tests/test_offline_uses_fixture.py`, `tests/test_dependency_overlay.py`. Token-missing in live mode is a clean non-zero exit, not fallback; `--offline` uses the fixture and never touches the network. The loop also reads/writes `.ubu-phase0/live_issues.json` through the refresh path.
The loop owns claim-register loading and validation, returning a structured object.

**PHASE0-T008 — cli**
Allowed: `src/ubu_phase0/cli.py`, `tests/test_cli_demo_smoke.py`, `tests/test_cli_refresh_smoke.py`.
Owns the `--offline` flag, the Rich table (time, label, source, affect-margin), and the probability/coverage footer.

**PHASE0-T009 — claim register validation**
Allowed: `fixtures/claim_register.json`, `tests/test_claim_register_completeness.py`.
No `claims.py` module; the loader lives in `loop.py` from T007.

### Reserved v1.5 tickets (do not implement in v1)

**PHASE0-T010 — log-replan** (`planner.py`, `loop.py`, `cli.py`, `tests/test_log_replan.py`): completed-task filtering, single-key `log`, auto-replan, "Completed" section render.

**PHASE0-T011 — impossible-graph diagnostic** (`cli.py`, fixture loader): `--demo-impossible` flag loads `impossible_dependency_demo.json`; renders `SkeletonFailureDiagnostic`.

**PHASE0-T012 — standalone claims command** (`cli.py`, `tests/test_claims_command.py`): reuses the loop's structured claim-register object.

**PHASE0-T013 — recalibrate command** (`cli.py`, `tests/test_recalibrate.py`): reuses the bootstrap preset-to-profile mapping.

**PHASE0-T014 — issue-body directive parsing** (`github_ingest.py`, tests): single-line `ubu:` directives in bodies; labels take precedence; explicit malformed-input tests.

**PHASE0-T015 — doctor command** (`cli.py`, `tests/test_doctor_command.py`): checks token presence, token validity, fixture presence, claim-register validity.

---

## 12. `PHASE0_ACCEPTANCE_TESTS.md`

The test specifications below are human-owned. Agents translate each spec into pytest code; agents do not invent the criteria. This prevents the circularity where agent-derived tests merely confirm the agent's own reading of the design.

### 12.1 Default suite (blocking)

- **test_schema_contract** — schema constants exist; `profile` string is correct; Phase 0 sentinels exist; required model fields exist; unsupported fields serialize as `None` or sentinel rather than disappearing.
- **test_contract_roundtrip** — `demo_request.json` loads, validates as `PlanningRequest`, serializes back, is consumed by the planner, and the resulting `PlanningResponse` validates.
- **test_github_issue_fixture_to_tasks** — `static_dummy_issues.json` loads; issues convert to `TaskSpec`; `source_ref` is correct; `external_url` preserved; `authority_source` set to `imported_config` for the fixture; PR-like items skipped.
- **test_github_label_mapping** — duration, priority, and affect labels map correctly; duplicate-family labels resolve to first-alphabetical with a warning; unknown labels do not fail; unlabeled issue gets safe defaults.
- **test_github_issue_deduplication** — duplicates dedupe by `source_ref`; result ordering is deterministic.
- **test_live_missing_token_fails_cleanly** — in live mode with no token and no usable live cache, the loop fails cleanly with a non-zero exit and a message naming the env var; it does not silently fall back to fixtures.
- **test_offline_uses_fixture** — with `--offline`, the loop uses `fixtures/static_dummy_issues.json`, does not touch the network, and reports the fixture data source correctly.
- **test_dependency_overlay** — overlay edges apply to matching task refs; unknown refs warn and are treated as absent; valid edges change scheduling order.
- **test_topological_order** — a known dependency chain schedules prerequisites before dependents; cycles are rejected with a clear diagnostic; unknown dependencies are reported.
- **test_affect_gate_rejection** — a low-energy profile rejects or deprioritizes high-energy tasks; a high-stress profile rejects high-stress-risk tasks; an intense-mood profile rejects mood-intense-risk tasks.
- **test_calendar_preview_next_four_hours** — the preview starts at `effective_time`; spans no more than four hours; fixed durations fit; no overlaps.
- **test_claim_register_completeness** — `claim_register.json` loads; every `implemented` claim names an existing test; every required demo claim appears; statuses are valid.
- **test_cli_demo_smoke** — `ubu-phase0 demo --offline` exits 0; output includes the data source, the Calendar preview, and the claim summary.
- **test_cli_refresh_smoke** — `ubu-phase0 refresh` with no token fails cleanly and reports the absence; with a mocked live fetch, it writes `.ubu-phase0/live_issues.json`; it does not crash.
- **test_import_boundaries** — the module graph in Section 7 is not violated; planner purity is enforced by source scan.

### 12.2 Opt-in and v1.5 tests (excluded from the default run)

- **test_live_github_ingestion_smoke** — marked `@pytest.mark.live_github`; excluded from the default suite via `addopts = "-m 'not live_github'"`; run manually before rehearsal with `UBU_PHASE0_GITHUB_TOKEN=... pytest -m live_github`. Does not block any ticket.
- **test_log_replan**, **test_claims_command**, **test_recalibrate**, **test_doctor_command** — added with their respective v1.5 tickets.

---

## 13. `PHASE0_CLAIM_REGISTER_SPEC.md`

### 13.1 File and schema

`fixtures/claim_register.json`:

```json
{
  "profile": "planning-kernel-contract/phase0-profile/0.1",
  "claims": [
    {
      "id": "CR-001",
      "claim": "UbU imports GitHub issues as Task objects",
      "status": "implemented",
      "modules": ["github_ingest", "loop", "cli"],
      "test": "test_github_issue_fixture_to_tasks"
    }
  ]
}
```

Status values: `implemented`, `fixture_backed`, `mocked`, `deferred`.

### 13.2 Required v1 claims

```json
{
  "profile": "planning-kernel-contract/phase0-profile/0.1",
  "claims": [
    { "id": "CR-001", "claim": "UbU imports GitHub issues as Task objects",
      "status": "implemented", "modules": ["github_ingest", "loop", "cli"],
      "test": "test_github_issue_fixture_to_tasks" },
    { "id": "CR-002", "claim": "UbU runs live against UbU-dummy/ubu-design or offline against a fixture by operator choice",
      "status": "implemented", "modules": ["github_ingest", "loop", "cli"],
      "test": "test_offline_uses_fixture" },
    { "id": "CR-003", "claim": "UbU maps GitHub labels to duration, priority, and affect hints with safe defaults",
      "status": "implemented", "modules": ["github_ingest"],
      "test": "test_github_label_mapping" },
    { "id": "CR-004", "claim": "UbU records the provenance of every Task via authority_source",
      "status": "implemented", "modules": ["github_ingest", "schema"],
      "test": "test_github_issue_fixture_to_tasks" },
    { "id": "CR-005", "claim": "UbU respects explicit task dependencies",
      "status": "implemented", "modules": ["planner"],
      "test": "test_topological_order" },
    { "id": "CR-006", "claim": "UbU rejects or deprioritizes affect-infeasible tasks",
      "status": "implemented", "modules": ["affect", "planner"],
      "test": "test_affect_gate_rejection" },
    { "id": "CR-007", "claim": "UbU produces a four-hour Calendar preview with affect-margin indicators",
      "status": "implemented", "modules": ["planner", "loop", "cli"],
      "test": "test_calendar_preview_next_four_hours" },
    { "id": "CR-008", "claim": "UbU does not estimate plan probability or coverage in Phase 0",
      "status": "deferred", "modules": ["planner"],
      "test": "test_contract_roundtrip" }
  ]
}
```

If the v1.5 log-replan ticket lands, add:

```json
{ "id": "CR-009", "claim": "UbU replans after a task outcome is logged",
  "status": "implemented", "modules": ["planner", "loop", "cli"],
  "test": "test_log_replan" }
```

### 13.3 Completeness rule

For every claim with `status = implemented`, there must be a named test, a non-empty `modules` list, and a passing acceptance test. `test_claim_register_completeness` enforces this. `deferred` and `mocked` claims are exempt from the passing-test requirement but must still carry a `modules` list and a representative test reference.

---

## 14. `PHASE0_DEMO_SCRIPT.md`

### 14.1 Story

UbU is preparing its own Phase 0 release. The project's work lives as GitHub issues. UbU imports those issues as Tasks, builds a planning request, applies dependency and affect constraints, and shows what fits into the next four hours — honestly labeling what it does and does not model.

### 14.2 Setup

```
export UBU_PHASE0_GITHUB_TOKEN=...
export UBU_PHASE0_GITHUB_OWNER=UbU-dummy
export UBU_PHASE0_GITHUB_REPO=ubu-design
```

Pre-flight (operator): run `ubu-phase0 demo --offline` once to confirm the fixture path is healthy before going live.

### 14.3 Live run

```
ubu-phase0 demo
```

Expected output sections, in order:

```
UbU Phase 0 Demo
Data source: live GitHub          Repository: UbU-dummy/ubu-design
Imported Tasks                    (number, with source_ref and authority_source)
Affect Profile                    (qualitative presets chosen at bootstrap)
Planning Window                   (today, next 4 hours)
Calendar Preview                  (Rich table)
Claim Register Summary            (status counts and notable deferrals)
Footer                            probability_quality / coverage_estimate
```

Calendar table columns and a representative row:

```
Time          Task                                   Source         Affect
09:00–09:30   Write Phase 0 contract profile         github_event   ▆▆▆
09:30–10:00   Freeze schema module                   github_event   ▃▃▃
10:00–10:30   Generate acceptance fixtures           github_event   ▆▆▆

probability_quality: not_estimated  (Phase 1 will populate)
coverage_estimate:   —              (Phase 1 will populate)
```

### 14.4 Audience-created issue flow

An audience member opens an issue in `UbU-dummy/ubu-design` (optionally tagging `ubu:duration:60m`, `ubu:priority:high`, `ubu:depends-on:#N`). The operator then:

```
ubu-phase0 refresh
ubu-phase0 demo
```

The `refresh` command writes `.ubu-phase0/live_issues.json`; the new issue appears as a Task in the next preview.

### 14.5 Required visible proof

The demo must visibly show, for at least one Task: the issue number, the issue title, the `source_ref`, the `authority_source`, the Calendar placement, the affect-margin indicator, the active data source, and the claim summary.

### 14.6 Offline safety

If the network or token fails at any point, live mode fails visibly and the operator reruns with `--offline`. The fixture run reproduces the full loop deterministically from `static_dummy_issues.json` with known dependency edges, so the demo always has a working path.

### 14.7 v1.5 stretch (only if implemented)

Mark the first Task complete with a single key; the planner reruns with the accumulated `LogEntry` list; the CLI shows a "Completed" section above a changed Calendar preview. Optionally, `--demo-impossible` loads a cyclic fixture to show UbU rendering a `SkeletonFailureDiagnostic` instead of crashing.

---

## 15. `AGENTS.md`

```markdown
# Agent Instructions — UbU Phase 0

You are implementing UbU Phase 0, a Python-only ETHConf NYC demo prototype.
It is NOT Phase 1 and NOT production architecture. Phase 0 code is not expected
to survive into Phase 1.

## Goal
Build a CLI demo that:
1. reads GitHub issues from UbU-dummy/ubu-design in live mode,
2. reads fixtures in --offline mode,
3. converts issues into UbU Task objects with authority_source,
4. builds a Phase 0 PlanningRequest,
5. runs a deterministic dependency-aware, affect-aware planner,
6. shows a four-hour Calendar preview with source and affect-margin columns,
7. prints a claim-register summary.

## Hard rules
- Do not implement Phase 1: no repair mode, no stochastic durations, no GPU,
  no Monte Carlo, no correlation matrices, no OAuth, no model-committee integration.
- Do not mutate GitHub in any way.
- Do not auto-fall-back: live-mode errors exit non-zero; --offline selects the fixture.
- Do not add any persistent cache except the explicitly allowed live refresh snapshot at `.ubu-phase0/live_issues.json`.
- Do not edit schema.py after it is frozen unless the ticket explicitly allows it.
- Do not change fixture shapes without updating schema and tests.
- Do not violate PHASE0_MODULE_BOUNDARIES.md.
- Do not move explanation generation out of planner.py.
- planner.py must not read files, env vars, or GitHub, and must not import
  github_ingest, loop, or cli.
- Optimize for the canonical demo path and the documented failure modes.
  Do not add defensive code beyond ticket scope. Do not generalize.

## Checks
python -m pytest -m "not live_github"   # blocking
python -m ruff check .                   # blocking
python -m mypy src/ubu_phase0            # advisory; report warnings, do not hide them

## Definition of done
- Acceptance tests pass.
- Changed files within allowed scope; no forbidden imports.
- No Phase 1 features added.
- Demo behavior remains fixture-safe.
- mypy warnings reported in the ticket summary.
```

---

## 16. Repository file tree

```
ubu-phase0-demo/
  AGENTS.md
  README.md
  pyproject.toml
  PHASE0_PLAN.md
  PHASE0_CUTLIST.md
  PHASE0_CONTRACT_PROFILE.md
  PHASE0_MODULE_BOUNDARIES.md
  PHASE0_GITHUB_INGESTION.md
  PHASE0_DEMO_FAILURE_MODES.md
  PHASE0_CODEGEN_WORKFLOW.md
  PHASE0_ACCEPTANCE_TESTS.md
  PHASE0_DEMO_SCRIPT.md
  PHASE0_CLAIM_REGISTER_SPEC.md

  src/
    ubu_phase0/
      __init__.py
      schema.py          # frozen after T001
      affect.py
      github_ingest.py
      planner.py
      bootstrap.py
      loop.py
      cli.py

  .ubu-phase0/
    live_issues.json                    # generated by refresh; not committed

  fixtures/
    static_dummy_issues.json              # canonical: test fixture + offline corpus
    demo_dependency_overlay.json          # optional dependency overlay; higher priority than labels
    demo_request.json
    demo_log_empty.json                  # []
    claim_register.json
    # reserved for v1.5 (created as placeholders in T002):
    demo_log_after_task1.json
    demo_response_initial.expected.json
    demo_response_replanned.expected.json
    impossible_dependency_demo.json

  tests/
    test_schema_contract.py
    test_contract_roundtrip.py
    test_github_issue_fixture_to_tasks.py
    test_github_label_mapping.py
    test_github_issue_deduplication.py
    test_live_missing_token_fails_cleanly.py
    test_offline_uses_fixture.py
    test_dependency_overlay.py
    test_topological_order.py
    test_affect_gate_rejection.py
    test_calendar_preview_next_four_hours.py
    test_claim_register_completeness.py
    test_cli_demo_smoke.py
    test_cli_refresh_smoke.py
    test_bootstrap_defaults.py
    test_import_boundaries.py
    # opt-in / v1.5:
    test_live_github_ingestion_smoke.py   # @pytest.mark.live_github
    test_log_replan.py
    test_claims_command.py
    test_recalibrate.py
    test_doctor_command.py

  tickets/
    PHASE0-T001-schema.json
    PHASE0-T002-fixtures.json
    PHASE0-T003-github-ingest.json
    PHASE0-T004-affect.json
    PHASE0-T005-planner.json
    PHASE0-T006-bootstrap.json
    PHASE0-T007-loop.json
    PHASE0-T008-cli.json
    PHASE0-T009-claim-register.json
    # reserved:
    PHASE0-T010-log-replan.json
    PHASE0-T011-impossible-graph.json
    PHASE0-T012-claims-command.json
    PHASE0-T013-recalibrate.json
    PHASE0-T014-body-directives.json
    PHASE0-T015-doctor.json
    # reviewer outputs, one per implemented ticket:
    PHASE0-TXXX-review.md
```

---

## 17. Reserved v1.5 features and the optionality discipline

If time remains after the v1 demo path is stable, re-add features in this priority order. The preparation work below is documentation-only and is done during the packet authoring, so each feature collapses from "design and implement" to "implement against an existing slot."

### 17.1 Priority order (impact per unit of effort)

1. **Log-replan (T010).** Highest impact: it is what proves UbU is a planning system rather than a sorter. Prepared by: `LogEntry` in the frozen schema; `demo_log_*` fixtures reserved; "Completed" render format pre-specified in the demo script.
2. **Impossible-graph diagnostic (T011).** Shows UbU explaining failure rather than crashing. Prepared by: `SkeletonFailureDiagnostic` in the frozen schema; `impossible_dependency_demo.json` reserved; `--demo-impossible` flag and render budget pre-specified.
3. **Standalone `claims` command (T012).** A demo-honesty proof point. Prepared by: the loop's claim loader returns a structured object, not a string.
4. **Recalibrate mid-demo (T013).** Shows the affect gate doing live work. Prepared by: the preset-to-profile mapping is a standalone pure function callable outside the bootstrap flow.
5. **Issue-body directive parsing (T014).** Forgiving of audience input. Prepared by: the label parser is specified as a directive extractor with labels-take-precedence. Caution: restrict to single-line directives and add explicit malformed-input tests; bodies are arbitrary markdown.
6. **Minimal `doctor` (T015).** Operator pre-flight convenience. Prepared by: command name and test filename reserved.

### 17.2 Calibration example surfacing (UBU-D0200)

Prepared for adoption after v1. The six neutral frames from UBU-D0200 (`urgent_value`, `emotional_cost`, `social_pressure`, `recovery_value`, `long_term_importance`, `ambiguity_value`) attach as a `calibration_frame_hint` in `explanation_fragments`. The planner selects the most relevant frame for a borderline task placement from a small mapping table. Reserve the `calibration_frame_hint` field shape in the frozen schema so this is a render-and-select change later, not a schema change.

### 17.3 The optionality principle

The cheap way to keep options open is to keep the data model and the module boundaries open; the expensive way is to retrofit them. Schema additions after freeze are the most expensive change in this architecture; filename and ticket-ID reservations are the cheapest. Every v1.5 preparation above is documentation-only and leaves v1 unaffected whether or not the feature is ever built.

---

## 18. Development order (end to end)

```
1.  Create the ubu-phase0-demo repository.
2.  Author and human-accept the documentation packet (Sections 4–15).
3.  Add AGENTS.md.
4.  Generate the repo skeleton (Stage 1).
5.  T001: generate schema.py and its two contract tests. Accept. FREEZE schema.py.
6.  T002: generate fixtures (v1 plus reserved v1.5 placeholders).
7.  Author the acceptance-test specs (already in Section 12); agents write the test code alongside their modules.
8.  T003–T009: implement one module per ticket, in dependency order, with a reviewer-agent pass after each.
9.  Run the full default suite; confirm green.
10. Rehearse the live GitHub demo against UbU-dummy/ubu-design.
11. Rehearse the --offline fixture demo.
12. If time remains: implement v1.5 tickets T010–T015 in the Section 17.1 priority order, each with a reviewer pass.
13. If the schedule slips: cut in the Section 5 cut order.
```

---

## 19. Auto-generation expectation

| Area | Expected agent-generation |
|---|---|
| Repo skeleton | ~100% |
| Documentation packet | Human-authored; agent drafts permitted as a starting point |
| Pydantic schema | 95–100% |
| Fixtures | 90–98% |
| GitHub ingestion (logic) | 90–98% |
| Live GitHub adapter (PyGithub) | 75–90% |
| Label mapping | 90–98% |
| Affect gate | 95–100% |
| DAG validation and planner | 90–98% |
| Calendar preview (logic) | 90–98% |
| Calendar preview (Rich visual polish) | hands-on |
| Planner explanations | 85–95% |
| CLI commands and flags | 90–98% |
| Claim-register validation | 95–100% |
| Acceptance tests (from human specs) | 90–98% |
| Bootstrap prompt wording | hands-on |

Overall v1 expectation: **88–92% agent-generated and acceptable on first pass; working assumption 90%.** A 95% ceiling is reachable with tight ticket discipline and the reviewer-agent loop; 100% is not a realistic or useful target.

The residual 10% is concentrated and predictable: PyGithub integration against the live repository, Rich Calendar visual polish, and bootstrap prompt wording. These are where a human eye on the output is the final arbiter, and no amount of upstream specification removes that. Budget rehearsal time specifically for those three.

---

## 20. The one discipline that matters most

Phase 0 succeeds because it is concrete, not because it is broad. The demo lands if an ETHConf attendee can see a real GitHub issue become a UbU Task, watch UbU place it into a Calendar preview that respects dependencies and the operator's affect state, and read an honest account of what is live, what is fixture-backed, and what is deferred to Phase 1. Everything in this document serves that single outcome.
