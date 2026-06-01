"""UbU Phase 0 planner.

Implements planner(request, logs) -> PlanningResponse.

May import: schema, affect, stdlib only.
PURE: no file I/O, no env vars, no GitHub, no mutation of request.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from ubu_phase0 import affect as _affect
from ubu_phase0.schema import (
    AffectProfile,
    CandidateRole,
    Diagnostics,
    ExplanationFragment,
    FeasibilitySummary,
    LogEntry,
    LogOutcome,
    PlanCandidate,
    PlanningRequest,
    PlanningResponse,
    PlanningStatus,
    ProbabilityQuality,
    ProbabilitySummary,
    ScoreSummary,
    ScheduledPlacement,
    SemiLegitimizationResult,
    SemiLegitimizationSummary,
    SkeletonFailureDiagnostic,
    SkeletonFailureClass,
    SkeletonSeverity,
    ScoringPolicy,
    TaskSpec,
    TimeWindow,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _topo_sort(
    task_ids: list[str], edges: list[tuple[str, str]]
) -> tuple[list[str], bool]:
    """Kahn's algorithm. Returns (topological_order, has_cycle)."""
    task_set = set(task_ids)
    in_degree: dict[str, int] = {tid: 0 for tid in task_ids}
    adj: dict[str, list[str]] = {tid: [] for tid in task_ids}

    for before, after in edges:
        if before in task_set and after in task_set:
            adj[before].append(after)
            in_degree[after] += 1

    # Stable initial order: preserve input ordering.
    queue: deque[str] = deque(tid for tid in task_ids if in_degree[tid] == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    has_cycle = len(order) != len(task_ids)
    return order, has_cycle


def _find_cycle_participants(
    task_ids: list[str], edges: list[tuple[str, str]]
) -> list[str]:
    """Return task IDs involved in at least one cycle (DFS colouring)."""
    task_set = set(task_ids)
    adj: dict[str, list[str]] = {tid: [] for tid in task_ids}
    for before, after in edges:
        if before in task_set and after in task_set:
            adj[before].append(after)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {tid: WHITE for tid in task_ids}
    in_cycle: set[str] = set()

    def _dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in adj[node]:
            if color[neighbor] == GRAY:
                cycle_start = path.index(neighbor)
                for n in path[cycle_start:]:
                    in_cycle.add(n)
            elif color[neighbor] == WHITE:
                _dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    for tid in task_ids:
        if color[tid] == WHITE:
            _dfs(tid, [])

    return sorted(in_cycle)


def _score_candidate(
    schedule: list[ScheduledPlacement],
    task_map: dict[str, TaskSpec],
    affect_profile: AffectProfile,
    scoring_policy: ScoringPolicy,
) -> ScoreSummary:
    if not schedule:
        return ScoreSummary()

    priority_weights = {"high": 3.0, "medium": 2.0, "low": 1.0}
    utility_score = sum(
        priority_weights.get(task_map[p.task_id].priority.value, 2.0)
        for p in schedule
        if p.task_id in task_map
    ) / (len(schedule) * 3.0)
    utility_score = min(1.0, utility_score)

    affect_scores: list[float] = []
    for placement in schedule:
        task = task_map.get(placement.task_id)
        if task:
            result = _affect.check_task_affect_feasibility(affect_profile, task)
            affect_scores.append(result.minimum_score)
    affect_margin_score = sum(affect_scores) / len(affect_scores) if affect_scores else 1.0

    total_score = (
        scoring_policy.utility_weight * utility_score
        + scoring_policy.affect_margin_weight * affect_margin_score
    )
    return ScoreSummary(
        utility_score=round(utility_score, 4),
        robustness_score=0.0,
        affect_margin_score=round(affect_margin_score, 4),
        schedule_diversity_score=0.0,
        total_score=round(total_score, 4),
    )


def _semi_legitimize(
    schedule: list[ScheduledPlacement],
    task_map: dict[str, TaskSpec],
    affect_profile: AffectProfile,
    time_window: TimeWindow,
) -> SemiLegitimizationSummary:
    """Cheap pre-validation layer (UBU-D0211). Full legitimization is stubbed."""
    if not schedule:
        return SemiLegitimizationSummary(
            result=SemiLegitimizationResult.passes_cheap_checks,
            affect_budget_ok=True,
            slack_preserved=True,
            dependency_fragility_ok=True,
            user_mode_compatible=True,
        )

    affect_ok = all(
        _affect.check_task_affect_feasibility(affect_profile, task_map[p.task_id]).feasible
        for p in schedule
        if p.task_id in task_map
    )
    last_end = _parse_dt(schedule[-1].end_time)
    window_end = _parse_dt(time_window.end_time)
    slack_preserved = last_end <= window_end

    result = (
        SemiLegitimizationResult.passes_cheap_checks
        if (affect_ok and slack_preserved)
        else SemiLegitimizationResult.reject_obvious
    )
    return SemiLegitimizationSummary(
        result=result,
        affect_budget_ok=affect_ok,
        slack_preserved=slack_preserved,
        dependency_fragility_ok=True,
        user_mode_compatible=True,
        local_repair_viable=None,
        legitimacy_delta_estimate=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def planner(request: PlanningRequest, logs: list[LogEntry]) -> PlanningResponse:
    """Phase 0 deterministic dependency-aware, affect-aware planner.

    Pure function: no file I/O, no env vars, no GitHub, no mutation of request.
    """
    now_str = request.generated_at
    all_tasks: dict[str, TaskSpec] = {t.id: t for t in request.task_graph.tasks}

    # Derive effective task set from logs.
    completed_refs: set[str] = set()
    blocked_refs: set[str] = set()
    skipped_refs: set[str] = set()
    for entry in logs:
        if entry.outcome == LogOutcome.completed:
            completed_refs.add(entry.task_ref)
        elif entry.outcome == LogOutcome.blocked:
            blocked_refs.add(entry.task_ref)
        elif entry.outcome == LogOutcome.skipped:
            skipped_refs.add(entry.task_ref)

    excluded_refs = completed_refs | blocked_refs | skipped_refs
    effective_tasks = [t for t in request.task_graph.tasks if t.id not in excluded_refs]
    effective_task_ids = [t.id for t in effective_tasks]
    effective_set = set(effective_task_ids)

    # Build edge list restricted to effective tasks.
    edge_set: set[tuple[str, str]] = set()
    for e in request.task_graph.dependency_edges:
        if e.before_task_id in effective_set and e.after_task_id in effective_set:
            edge_set.add((e.before_task_id, e.after_task_id))
    for task in effective_tasks:
        for dep_id in task.dependencies:
            if dep_id in effective_set:
                edge_set.add((dep_id, task.id))
    edges = list(edge_set)

    # DAG validation.
    topo_order, has_cycle = _topo_sort(effective_task_ids, edges)

    if has_cycle:
        cycle_participants = _find_cycle_participants(effective_task_ids, edges)
        diag = SkeletonFailureDiagnostic(
            diagnostic_id=f"diag-cycle-{request.request_id}",
            severity=SkeletonSeverity.blocking,
            failure_class=SkeletonFailureClass.cyclic_dependency,
            affected_task_refs=cycle_participants,
            prompt_policy="immediate_blocking_prompt",
            user_facing_summary=(
                f"Dependency cycle detected among tasks: "
                f"{', '.join(cycle_participants)}. "
                "Planning cannot proceed until the cycle is resolved."
            ),
        )
        return PlanningResponse(
            schema_version=request.schema_version,
            profile=request.profile,
            planner_version=request.planner_version,
            request_id=request.request_id,
            rng_seed_echo=request.rng_seed,
            generated_at=now_str,
            status=PlanningStatus.rejected,
            plan_candidates=[],
            diagnostics=Diagnostics(
                probability_quality=ProbabilityQuality.not_estimated,
                rejection_counts_by_reason={"cyclic_dependency": 1},
                skeleton_failure_diagnostics=[diag],
            ),
        )

    # Affect gate.
    enforce_affect = request.constraint_policy.affect_constraint_mode == "enforce"
    affect_passed: set[str] = set()
    affect_rejected: list[str] = []
    warnings: list[str] = []

    for tid in topo_order:
        task = all_tasks[tid]
        feasibility = _affect.check_task_affect_feasibility(request.affect_profile, task)
        if not feasibility.feasible and enforce_affect:
            affect_rejected.append(tid)
            warnings.append(
                f"Task {tid!r} excluded by affect gate: "
                f"violated dimensions: {feasibility.violated_dimensions}"
            )
        else:
            affect_passed.add(tid)
            if not feasibility.feasible:
                warnings.append(
                    f"Task {tid!r} fails affect gate (warn_only mode): "
                    f"violated dimensions: {feasibility.violated_dimensions}"
                )

    # Schedule into the planning window in topological order.
    # A task is placed only when all known dependencies are satisfied.
    window_start = _parse_dt(request.time_window.start_time)
    window_end = _parse_dt(request.time_window.end_time)

    current_time = window_start
    schedule: list[ScheduledPlacement] = []
    # Completed and skipped tasks count as satisfied for dependency purposes.
    satisfied_ids: set[str] = completed_refs | skipped_refs

    for tid in topo_order:
        if tid not in affect_passed:
            continue

        task = all_tasks[tid]

        # Collect all dependency refs for this task.
        all_deps: set[str] = set(task.dependencies)
        for e in request.task_graph.dependency_edges:
            if e.after_task_id == tid:
                all_deps.add(e.before_task_id)

        # Deps missing from the task graph are absent; warn and ignore.
        absent_deps = all_deps - set(all_tasks.keys())
        for dep in sorted(absent_deps):
            warnings.append(
                f"Task {tid!r}: dependency {dep!r} not found in task graph; treating as absent."
            )

        known_deps = all_deps & set(all_tasks.keys())
        unsatisfied = known_deps - satisfied_ids
        if unsatisfied:
            warnings.append(
                f"Task {tid!r} skipped: unsatisfied dependencies: {sorted(unsatisfied)}"
            )
            continue

        task_end = current_time + timedelta(seconds=task.duration.seconds)
        if task_end > window_end:
            warnings.append(f"Task {tid!r} does not fit in remaining window; excluded.")
            continue

        schedule.append(
            ScheduledPlacement(
                task_id=tid,
                start_time=_fmt_dt(current_time),
                end_time=_fmt_dt(task_end),
            )
        )
        satisfied_ids.add(tid)
        current_time = task_end

    # Feasibility summary over the schedule.
    violated_dims: list[str] = []
    min_affect_score = 1.0
    for placement in schedule:
        task = all_tasks[placement.task_id]
        result = _affect.check_task_affect_feasibility(request.affect_profile, task)
        for dim in result.violated_dimensions:
            if dim not in violated_dims:
                violated_dims.append(dim)
        min_affect_score = min(min_affect_score, result.minimum_score)

    feasibility_summary = FeasibilitySummary(
        affect_feasible=len(violated_dims) == 0,
        minimum_affect_score=round(min_affect_score, 4),
        violated_affect_dimensions=violated_dims,
    )

    score_summary = _score_candidate(
        schedule, all_tasks, request.affect_profile, request.scoring_policy
    )
    semi_leg = _semi_legitimize(
        schedule, all_tasks, request.affect_profile, request.time_window
    )

    explanations: list[ExplanationFragment] = []
    if schedule:
        explanations.append(
            ExplanationFragment(text=f"Scheduled {len(schedule)} task(s) in the 4-hour window.")
        )
    if affect_rejected:
        explanations.append(
            ExplanationFragment(
                text=f"{len(affect_rejected)} task(s) excluded by affect gate: "
                f"{', '.join(affect_rejected)}."
            )
        )
    if completed_refs:
        explanations.append(
            ExplanationFragment(
                text=f"{len(completed_refs)} task(s) already completed (from logs), not re-scheduled."
            )
        )
    if blocked_refs:
        warnings.append(
            f"{len(blocked_refs)} task(s) blocked (from logs), excluded from schedule."
        )

    candidate = PlanCandidate(
        candidate_id=f"cand-{request.request_id}-0",
        rank=1,
        candidate_role=CandidateRole.highest_utility,
        schedule=schedule,
        score_summary=score_summary,
        feasibility_summary=feasibility_summary,
        semi_legitimization_summary=semi_leg,
        probability_summary=ProbabilitySummary(),
        explanation_fragments=explanations,
    )

    status = PlanningStatus.ok if schedule else PlanningStatus.partial

    diagnostics = Diagnostics(
        candidate_counts_by_stage={
            "effective_tasks": len(effective_tasks),
            "after_affect_filter": len(affect_passed),
            "scheduled": len(schedule),
        },
        n_skeleton_candidates=1,
        n_after_affect_filter=len(affect_passed),
        n_after_value_scoring=1,
        n_finalists_rollout=0,
        rejection_counts_by_reason=(
            {"affect_gate": len(affect_rejected)} if affect_rejected else {}
        ),
        warnings=warnings,
        probability_quality=ProbabilityQuality.not_estimated,
        coverage_scope=None,
        coverage_estimate=None,
        uncovered_mass_estimate=None,
        coverage_threshold_used=None,
        coverage_below_threshold=None,
    )

    return PlanningResponse(
        schema_version=request.schema_version,
        profile=request.profile,
        planner_version=request.planner_version,
        request_id=request.request_id,
        rng_seed_echo=request.rng_seed,
        generated_at=now_str,
        status=status,
        plan_candidates=[candidate],
        diagnostics=diagnostics,
    )
