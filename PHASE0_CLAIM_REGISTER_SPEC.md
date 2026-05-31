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
      "test": "test_missing_github_token_uses_fixture" },
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

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
