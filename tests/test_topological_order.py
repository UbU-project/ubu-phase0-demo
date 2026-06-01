"""Acceptance tests for PHASE0-T005: topological ordering and cycle detection.

Covers:
- Linear dependency chain produces correct schedule order.
- Cycle detection returns rejected status with cyclic_dependency diagnostic.
- Empty task graph returns ok with empty schedule.
- Completed tasks (from logs) are excluded and their dependents are unblocked.
- Blocked tasks exclude their dependents from the schedule.
- Independent tasks are all scheduled.
- Planner import boundary: planner must not import forbidden modules.
"""

from __future__ import annotations

from ubu_phase0.affect import preset_to_affect_profile
from ubu_phase0.planner import planner
from ubu_phase0.schema import (
    AuthoritySource,
    DependencyEdge,
    FixedDuration,
    LogEntry,
    LogOutcome,
    PlanningStatus,
    SkeletonFailureClass,
    TaskGraph,
    TaskSpec,
    UniverseStateSnapshot,
    TimeWindow,
    PlanningRequest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(task_id: str, deps: list[str] | None = None) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        title=f"Task {task_id}",
        source_ref=task_id,
        external_id=task_id.split("#")[-1] if "#" in task_id else task_id,
        external_url=f"https://example.com/{task_id}",
        authority_source=AuthoritySource.imported_config,
        duration=FixedDuration(seconds=900),
        dependencies=deps or [],
    )


def _request(
    tasks: list[TaskSpec],
    edges: list[DependencyEdge] | None = None,
    request_id: str = "req-topo-test",
) -> PlanningRequest:
    return PlanningRequest(
        planner_version="ubu-phase0/0.1.0",
        request_id=request_id,
        effective_time="2026-06-09T09:00:00Z",
        generated_at="2026-06-09T09:00:00Z",
        rng_seed=42,
        time_window=TimeWindow(
            start_time="2026-06-09T09:00:00Z",
            end_time="2026-06-09T13:00:00Z",
        ),
        task_graph=TaskGraph(tasks=tasks, dependency_edges=edges or []),
        universe_state_snapshot=UniverseStateSnapshot(
            snapshot_id="snap-topo-test",
            snapshot_effective_time="2026-06-09T09:00:00Z",
        ),
        affect_profile=preset_to_affect_profile(),
    )


def _scheduled_ids(response) -> list[str]:
    if not response.plan_candidates:
        return []
    return [p.task_id for p in response.plan_candidates[0].schedule]


# ---------------------------------------------------------------------------
# Empty graph
# ---------------------------------------------------------------------------


def test_empty_task_graph_returns_ok():
    req = _request([])
    resp = planner(req, [])
    assert resp.status == PlanningStatus.ok or resp.status == PlanningStatus.partial
    assert _scheduled_ids(resp) == []


# ---------------------------------------------------------------------------
# Single task
# ---------------------------------------------------------------------------


def test_single_task_is_scheduled():
    req = _request([_task("T1")])
    resp = planner(req, [])
    assert resp.status == PlanningStatus.ok
    assert _scheduled_ids(resp) == ["T1"]


# ---------------------------------------------------------------------------
# Linear chain via task.dependencies
# ---------------------------------------------------------------------------


def test_two_task_chain_deps_field_order():
    """T2 depends on T1 → T1 must be scheduled before T2."""
    tasks = [_task("T1"), _task("T2", deps=["T1"])]
    req = _request(tasks)
    resp = planner(req, [])
    ids = _scheduled_ids(resp)
    assert "T1" in ids and "T2" in ids
    assert ids.index("T1") < ids.index("T2")


def test_three_level_chain_order():
    """T1 → T2 → T3 must appear in that order."""
    tasks = [
        _task("T1"),
        _task("T2", deps=["T1"]),
        _task("T3", deps=["T2"]),
    ]
    req = _request(tasks)
    resp = planner(req, [])
    ids = _scheduled_ids(resp)
    assert ids.index("T1") < ids.index("T2") < ids.index("T3")


# ---------------------------------------------------------------------------
# Linear chain via dependency_edges
# ---------------------------------------------------------------------------


def test_two_task_chain_via_edges():
    """Edge T1→T2 (before/after) must produce T1 before T2 in schedule."""
    tasks = [_task("T1"), _task("T2")]
    edges = [DependencyEdge(before_task_id="T1", after_task_id="T2")]
    req = _request(tasks, edges)
    resp = planner(req, [])
    ids = _scheduled_ids(resp)
    assert ids.index("T1") < ids.index("T2")


# ---------------------------------------------------------------------------
# Independent tasks
# ---------------------------------------------------------------------------


def test_independent_tasks_all_scheduled():
    tasks = [_task("A"), _task("B"), _task("C")]
    req = _request(tasks)
    resp = planner(req, [])
    ids = set(_scheduled_ids(resp))
    assert {"A", "B", "C"} == ids


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_mutual_cycle_produces_rejected_status():
    """A→B→A is a cycle; planner must reject."""
    tasks = [_task("A", deps=["B"]), _task("B", deps=["A"])]
    req = _request(tasks)
    resp = planner(req, [])
    assert resp.status == PlanningStatus.rejected
    assert resp.plan_candidates == []


def test_cycle_diagnostic_is_cyclic_dependency_class():
    tasks = [_task("A", deps=["B"]), _task("B", deps=["A"])]
    req = _request(tasks)
    resp = planner(req, [])
    diags = resp.diagnostics.skeleton_failure_diagnostics
    assert len(diags) >= 1
    assert any(d.failure_class == SkeletonFailureClass.cyclic_dependency for d in diags)


def test_cycle_diagnostic_names_involved_tasks():
    tasks = [_task("X", deps=["Y"]), _task("Y", deps=["X"])]
    req = _request(tasks)
    resp = planner(req, [])
    diag = resp.diagnostics.skeleton_failure_diagnostics[0]
    assert "X" in diag.affected_task_refs or "X" in diag.user_facing_summary
    assert "Y" in diag.affected_task_refs or "Y" in diag.user_facing_summary


def test_three_task_cycle_rejected():
    tasks = [_task("A", deps=["C"]), _task("B", deps=["A"]), _task("C", deps=["B"])]
    req = _request(tasks)
    resp = planner(req, [])
    assert resp.status == PlanningStatus.rejected


# ---------------------------------------------------------------------------
# Log integration: completed tasks
# ---------------------------------------------------------------------------


def test_completed_task_not_rescheduled():
    tasks = [_task("T1"), _task("T2")]
    req = _request(tasks)
    log = [LogEntry(task_ref="T1", outcome=LogOutcome.completed, effective_time="2026-06-09T09:30:00Z")]
    resp = planner(req, log)
    ids = _scheduled_ids(resp)
    assert "T1" not in ids
    assert "T2" in ids


def test_completed_dependency_unblocks_dependent():
    """If T1 is completed and T2 depends on T1, T2 should be scheduled."""
    tasks = [_task("T1"), _task("T2", deps=["T1"])]
    req = _request(tasks)
    log = [LogEntry(task_ref="T1", outcome=LogOutcome.completed, effective_time="2026-06-09T09:30:00Z")]
    resp = planner(req, log)
    ids = _scheduled_ids(resp)
    assert "T2" in ids
    assert "T1" not in ids


# ---------------------------------------------------------------------------
# Log integration: blocked tasks
# ---------------------------------------------------------------------------


def test_blocked_task_excluded_from_schedule():
    tasks = [_task("T1"), _task("T2")]
    req = _request(tasks)
    log = [LogEntry(task_ref="T1", outcome=LogOutcome.blocked, effective_time="2026-06-09T09:00:00Z")]
    resp = planner(req, log)
    ids = _scheduled_ids(resp)
    assert "T1" not in ids


def test_blocked_dependency_prevents_dependent_scheduling():
    """If T1 is blocked, T2 (which depends on T1) cannot be scheduled."""
    tasks = [_task("T1"), _task("T2", deps=["T1"])]
    req = _request(tasks)
    log = [LogEntry(task_ref="T1", outcome=LogOutcome.blocked, effective_time="2026-06-09T09:00:00Z")]
    resp = planner(req, log)
    ids = _scheduled_ids(resp)
    assert "T1" not in ids
    assert "T2" not in ids


# ---------------------------------------------------------------------------
# Import boundary: planner must not import forbidden modules
# ---------------------------------------------------------------------------


def test_planner_import_boundaries():
    import pathlib
    import ast

    planner_path = (
        pathlib.Path(__file__).parent.parent / "src" / "ubu_phase0" / "planner.py"
    )
    source = planner_path.read_text()

    tree = ast.parse(source)
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for part in node.module.split("."):
                    imported_names.add(part)
            for alias in node.names:
                imported_names.add(alias.name)

    forbidden = {"github_ingest", "loop", "cli", "bootstrap"}
    violations = forbidden & imported_names
    assert not violations, f"planner.py imports forbidden module(s): {violations}"
