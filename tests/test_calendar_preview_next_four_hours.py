"""Acceptance tests for PHASE0-T005: 4-hour calendar preview scheduling.

Covers:
- First task starts at window start_time.
- Each task's end_time = start_time + duration_seconds.
- Consecutive tasks are packed without gaps.
- A task that does not fit in the remaining window is excluded.
- Affect-rejected tasks are absent from the schedule when enforce mode is active.
- The fixture demo_request schedules at least one task.
- PlanningResponse fields are populated correctly (request_id echo, rng_seed echo,
  probability_quality=not_estimated, coverage fields null).
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime

from ubu_phase0.affect import preset_to_affect_profile
from ubu_phase0.planner import planner
from ubu_phase0.schema import (
    AffectDimensionName,
    AffectDimensionSpec,
    AffectDirection,
    AffectProfile,
    AuthoritySource,
    ConstraintPolicy,
    DependencyEdge,
    FixedDuration,
    LogEntry,
    LogOutcome,
    PlanningRequest,
    PlanningStatus,
    ProbabilityQuality,
    TaskGraph,
    TaskSpec,
    TimeWindow,
    UniverseStateSnapshot,
)

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(
    task_id: str,
    duration_seconds: int = 900,
    deps: list[str] | None = None,
    affect_requirement: dict[str, float] | None = None,
) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        title=f"Task {task_id}",
        source_ref=task_id,
        external_id=task_id.split("#")[-1] if "#" in task_id else task_id,
        external_url=f"https://example.com/{task_id}",
        authority_source=AuthoritySource.imported_config,
        duration=FixedDuration(seconds=duration_seconds),
        dependencies=deps or [],
        affect_requirement=affect_requirement or {},
    )


def _request(
    tasks: list[TaskSpec],
    edges: list[DependencyEdge] | None = None,
    affect_profile: AffectProfile | None = None,
    affect_mode: str = "enforce",
    start: str = "2026-06-09T09:00:00Z",
    end: str = "2026-06-09T13:00:00Z",
    request_id: str = "req-cal-test",
) -> PlanningRequest:
    return PlanningRequest(
        planner_version="ubu-phase0/0.1.0",
        request_id=request_id,
        effective_time=start,
        generated_at=start,
        rng_seed=99,
        time_window=TimeWindow(start_time=start, end_time=end),
        task_graph=TaskGraph(tasks=tasks, dependency_edges=edges or []),
        universe_state_snapshot=UniverseStateSnapshot(
            snapshot_id="snap-cal-test",
            snapshot_effective_time=start,
        ),
        affect_profile=affect_profile or preset_to_affect_profile(),
        constraint_policy=ConstraintPolicy(affect_constraint_mode=affect_mode),
    )


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _schedule(response):
    if not response.plan_candidates:
        return []
    return response.plan_candidates[0].schedule


# ---------------------------------------------------------------------------
# Window timing
# ---------------------------------------------------------------------------


def test_first_task_starts_at_window_start():
    req = _request([_task("T1", 1800)])
    resp = planner(req, [])
    sched = _schedule(resp)
    assert sched[0].start_time == "2026-06-09T09:00:00Z"


def test_task_end_time_equals_start_plus_duration():
    req = _request([_task("T1", 1800)])
    resp = planner(req, [])
    sched = _schedule(resp)
    start = _parse_dt(sched[0].start_time)
    end = _parse_dt(sched[0].end_time)
    assert (end - start).total_seconds() == 1800


def test_second_task_starts_where_first_ends():
    tasks = [_task("T1", 1800), _task("T2", 900)]
    req = _request(tasks)
    resp = planner(req, [])
    sched = _schedule(resp)
    assert len(sched) == 2
    assert sched[1].start_time == sched[0].end_time


def test_three_tasks_are_packed_consecutively():
    tasks = [_task("T1", 600), _task("T2", 600), _task("T3", 600)]
    req = _request(tasks)
    resp = planner(req, [])
    sched = _schedule(resp)
    assert len(sched) == 3
    assert sched[1].start_time == sched[0].end_time
    assert sched[2].start_time == sched[1].end_time


# ---------------------------------------------------------------------------
# Window overflow
# ---------------------------------------------------------------------------


def test_task_exceeding_window_is_excluded():
    """A single task longer than the 4h window must not be scheduled."""
    four_hours_plus_one = 4 * 3600 + 1
    req = _request([_task("BIG", four_hours_plus_one)])
    resp = planner(req, [])
    sched = _schedule(resp)
    assert all(p.task_id != "BIG" for p in sched)


def test_tasks_that_fit_after_overflow_are_excluded():
    """If the first task eats most of the window, a second that doesn't fit is excluded."""
    near_full = 4 * 3600 - 60  # 3h59m
    tasks = [_task("T1", near_full), _task("T2", 120)]  # T2 needs 2min, only 1min left
    req = _request(tasks)
    resp = planner(req, [])
    ids = [p.task_id for p in _schedule(resp)]
    assert "T1" in ids
    assert "T2" not in ids


def test_all_tasks_end_before_or_at_window_end():
    tasks = [_task(f"T{i}", 1200) for i in range(10)]
    req = _request(tasks)
    resp = planner(req, [])
    window_end = _parse_dt("2026-06-09T13:00:00Z")
    for placement in _schedule(resp):
        assert _parse_dt(placement.end_time) <= window_end


# ---------------------------------------------------------------------------
# Affect gate integration
# ---------------------------------------------------------------------------


def _reject_all_profile() -> AffectProfile:
    """An affect profile with a threshold of 1.0 that no task can meet."""
    spec = AffectDimensionSpec(
        dimension=AffectDimensionName.energy,
        direction=AffectDirection.higher_is_better,
        location=10.0,
        scale=0.1,
        threshold=1.0,  # impossible: sigmoid can never reach 1.0
    )
    return AffectProfile(
        energy=spec,
        stress=AffectDimensionSpec(
            dimension=AffectDimensionName.stress,
            direction=AffectDirection.lower_is_better,
            location=0.0,
            scale=0.1,
            threshold=0.0,
        ),
        mood_intensity=AffectDimensionSpec(
            dimension=AffectDimensionName.mood_intensity,
            direction=AffectDirection.lower_is_better,
            location=0.0,
            scale=0.1,
            threshold=0.0,
        ),
        preset_labels={"energy": "high", "stress": "low", "mood_intensity": "calm"},
    )


def test_affect_rejected_task_absent_from_schedule():
    """A task that fails the affect gate is not in the schedule (enforce mode)."""
    # energy demand=1.0 against high-energy profile (loc=6, threshold=0.3):
    # sat = sigmoid((1-6)/1.5) ≈ 0.035 < 0.3 → rejected.
    from ubu_phase0.affect import preset_to_affect_profile as _pap
    from ubu_phase0.schema import EnergyPreset

    profile = _pap(energy=EnergyPreset.high)
    task = _task("BAD", 900, affect_requirement={"energy": 1.0})
    req = _request([task], affect_profile=profile, affect_mode="enforce")
    resp = planner(req, [])
    ids = [p.task_id for p in _schedule(resp)]
    assert "BAD" not in ids


def test_affect_rejected_task_in_schedule_in_warn_only_mode():
    """In warn_only mode, a failing task is still scheduled."""
    from ubu_phase0.affect import preset_to_affect_profile as _pap
    from ubu_phase0.schema import EnergyPreset

    profile = _pap(energy=EnergyPreset.high)
    task = _task("BAD", 900, affect_requirement={"energy": 1.0})
    req = _request([task], affect_profile=profile, affect_mode="warn_only")
    resp = planner(req, [])
    ids = [p.task_id for p in _schedule(resp)]
    assert "BAD" in ids


def test_affect_rejection_counted_in_diagnostics():
    from ubu_phase0.affect import preset_to_affect_profile as _pap
    from ubu_phase0.schema import EnergyPreset

    profile = _pap(energy=EnergyPreset.high)
    task = _task("BAD", 900, affect_requirement={"energy": 1.0})
    req = _request([task], affect_profile=profile, affect_mode="enforce")
    resp = planner(req, [])
    assert resp.diagnostics.rejection_counts_by_reason.get("affect_gate", 0) == 1


# ---------------------------------------------------------------------------
# Response contract fields
# ---------------------------------------------------------------------------


def test_request_id_echoed_in_response():
    req = _request([_task("T1")], request_id="req-echo-test")
    resp = planner(req, [])
    assert resp.request_id == "req-echo-test"


def test_rng_seed_echoed_in_response():
    req = _request([_task("T1")])
    resp = planner(req, [])
    assert resp.rng_seed_echo == req.rng_seed


def test_probability_quality_is_not_estimated():
    req = _request([_task("T1")])
    resp = planner(req, [])
    assert resp.diagnostics.probability_quality == ProbabilityQuality.not_estimated


def test_coverage_fields_are_null():
    req = _request([_task("T1")])
    resp = planner(req, [])
    d = resp.diagnostics
    assert d.coverage_scope is None
    assert d.coverage_estimate is None
    assert d.uncovered_mass_estimate is None
    assert d.coverage_threshold_used is None
    assert d.coverage_below_threshold is None


# ---------------------------------------------------------------------------
# Fixture-based smoke test
# ---------------------------------------------------------------------------


def test_demo_request_fixture_schedules_tasks():
    """The demo_request.json fixture must produce a non-empty schedule."""
    demo_req_path = FIXTURE_DIR / "demo_request.json"
    raw = json.loads(demo_req_path.read_text())
    req = PlanningRequest(**raw)
    resp = planner(req, [])
    assert resp.status in (PlanningStatus.ok, PlanningStatus.partial)
    # At least one task must be scheduled.
    assert len(_schedule(resp)) >= 1


def test_demo_request_with_log_excludes_completed():
    """After task #8 is completed, it must not appear in the next schedule."""
    demo_req_path = FIXTURE_DIR / "demo_request.json"
    raw = json.loads(demo_req_path.read_text())
    req = PlanningRequest(**raw)
    log = [
        LogEntry(
            task_ref="github:UbU-dummy/ubu-design#8",
            outcome=LogOutcome.completed,
            effective_time="2026-06-09T09:30:00Z",
        )
    ]
    resp = planner(req, log)
    scheduled_ids = [p.task_id for p in _schedule(resp)]
    assert "github:UbU-dummy/ubu-design#8" not in scheduled_ids
