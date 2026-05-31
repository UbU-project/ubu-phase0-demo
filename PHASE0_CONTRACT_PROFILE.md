## 6. `PHASE0_CONTRACT_PROFILE.md`

This is the most important specification file. It defines the Phase 0 subset of the frozen `planning-kernel-contract/0.1`.

### 6.1 Profile identifier and constants

```python
PHASE0_PROFILE = "planning-kernel-contract/phase0-profile/0.1"
PHASE0_NOT_SUPPORTED = "not_supported"
PHASE0_NOT_ESTIMATED = "not_estimated"
```

The Phase 1 baseline `schema_version` is `planning-kernel-contract/0.1`. Phase 0 objects carry the Phase 1 `schema_version` for replay compatibility and additionally carry the `profile` field set to `PHASE0_PROFILE`. This makes a Phase 0 artifact unmistakable while keeping it a valid subset of the frozen contract.

### 6.2 Supported envelope fields

Carried and populated by Phase 0:

- `schema_version` = `planning-kernel-contract/0.1`
- `profile` = `planning-kernel-contract/phase0-profile/0.1`
- `planner_version`
- `request_id`
- `effective_time` (authoritative planning start; for the demo, the current local time rounded to the next clean boundary)
- `generated_at`
- `rng_seed`

### 6.3 `PlanningRequest` — Phase 0 subset

Supported and meaningful:

- `mode` = `fresh_generation` only. `repair` is not supported in Phase 0.
- `time_window` with `start_time`, `end_time` (start + 4 hours), and `planning_delta_seconds` = 60.
- `task_graph` with `tasks`, `dependency_edges`, and a CPU-supplied `topological_order`. In Phase 0 the planner computes the order itself from the edges; the field is populated for contract fidelity.
- `affect_profile` per §6.6.
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

### 6.4 `TaskSpec` — Phase 0 subset

Phase 0 `TaskSpec` carries:

- `id` (form `github:UbU-dummy/ubu-design#N`)
- `title`
- `description` (issue body or empty string)
- `source` = `github_issue`
- `source_ref` (same as `id`)
- `external_id` (issue number as string)
- `external_url` (issue `html_url`)
- `authority_source` (Phase 1 pull-in; see §6.5)
- `duration` — fixed model only
- `priority` (label-derived or `medium`)
- affect hints (label-derived or safe defaults)
- `dependencies` (overlay-derived or empty)

Duration uses the fixed model from the frozen contract:

```json
{ "type": "fixed", "seconds": 1800 }
```

The shifted-log-normal model, `correlation_groups`, and all stochastic duration features are **not supported** in Phase 0. The fixed model must be represented as a delta distribution, never as a tight log-normal.

### 6.5 `authority_source` (UBU-D0185, adopted into v1)

`authority_source` is the closed MVP enum from UBU-D0185. Phase 0 populates it on every Task:

- live GitHub issue → `github_event`
- the static fixture issue → `imported_config`
- a Task created or overridden by the operator → `user_override`

The full enum is carried in the schema for fidelity: `human_admin`, `automation_worker`, `github_event`, `project_policy`, `imported_config`, `llm_advisory`, `user_override`. Phase 0 only emits `github_event`, `imported_config`, and `user_override`. `authority_source` is provenance, not authorization; it does not gate anything in Phase 0.

### 6.6 Affect dimensions and preset table

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

### 6.7 `PlanningResponse` — Phase 0 subset

Supported:

- `schema_version`, `planner_version`, `request_id`, `rng_seed_echo`, `generated_at`
- `status` — `ok`, `partial`, `rejected`, `engine_error`. Phase 0 normally returns `ok`.
- `plan_candidates` — ranked list; Phase 0 returns at least one and auto-selects the top.
- `diagnostics`:
  - `skeleton_failure_diagnostics` — empty in v1 (no deliberate failure); populated in the v1.5 impossible-graph stretch.
  - `probability_quality` = `not_estimated`.
  - coverage fields (`coverage_scope`, `coverage_estimate`, `uncovered_mass_estimate`, `coverage_threshold_used`, `coverage_below_threshold`) — null.
  - `warnings` — used for ingestion warnings surfaced through the loop.

### 6.8 `PlanCandidate` — Phase 0 subset

Each candidate carries:

- `candidate_id`, `rank`, `candidate_role` (Phase 0 uses `highest_utility`)
- `schedule` — ordered Task placements within the four-hour window
- `score_summary` — `utility_score`, `affect_margin_score` (surfaced in the preview), `total_score`; `robustness_score` and `schedule_diversity_score` may be 0
- `feasibility_summary` — `affect_feasible`, `minimum_affect_score`, `violated_affect_dimensions`; `hard_constraints_assumed_satisfied_by_engine` is advisory
- `semi_legitimization_summary` — implemented in Phase 0: `result` (`passes_cheap_checks` / `reject_obvious` / `needs_full_legitimization`), `affect_budget_ok`, and the other cheap-check booleans where computed
- `probability_summary` — `provenance_refs` carries `PHASE0_NOT_ESTIMATED`; numeric fields null
- `explanation_fragments` — generated by the planner

### 6.9 Planner purity

```python
planner(request: PlanningRequest, log_entries: list[LogEntry]) -> PlanningResponse
```

The planner does not mutate `request`, does not read files, does not call GitHub, does not read environment variables, and produces explanations internally. It derives effective task state from `request` plus `log_entries`: completed tasks are filtered, blocked tasks are flagged, skipped tasks are ignored for Phase 0.

### 6.10 `LogEntry` (schema present in v1, exercised in v1.5)

`LogEntry` is fully defined in the v1 schema even though v1 constructs only the empty list. Minimum fields: `task_ref`, `outcome` (`completed` / `skipped` / `blocked`), `effective_time`, and an optional `authority_source` (typically `user_override`). Defining it now avoids a post-freeze schema change when log-replan is added.

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
