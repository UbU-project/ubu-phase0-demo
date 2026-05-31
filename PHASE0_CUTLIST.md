## 5. `PHASE0_CUTLIST.md`

This file exists to prevent scope creep. It has four sections: in scope, reserved for v1.5, out of scope, and cut-order if the schedule slips.

### In scope (v1)

- Python CLI demo (`demo`, `refresh`).
- Pydantic v2 schema with the Phase 0 contract profile.
- Live GitHub issue ingestion against `UbU-dummy/ubu-design`.
- Fixture mode via `--offline` using `static_dummy_issue.json`.
- GitHub issue to `TaskSpec` conversion with `authority_source`.
- Manual `refresh`.
- Safe label mapping (duration, priority, affect hints).
- Dependency overlay (live labels and fixture hardcoded edges).
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
- Persistent on-disk cache.
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
3. `refresh` command (operator restarts `demo` instead).
4. Dependency overlay for live issues (fixture edges remain).

Do not cut, under any circumstances: GitHub issue to `TaskSpec` conversion, fixture mode, the frozen schema, the affect preset table, the dependency-aware planner, the Calendar preview, the claim register, the CLI `demo` path.

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
