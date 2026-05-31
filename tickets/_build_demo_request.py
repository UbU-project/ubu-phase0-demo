"""One-off builder for demo_request.json.

Run during PHASE0-T002. Constructs a PlanningRequest from the frozen schema and
the static dummy issue fixture so the request validates by construction. This
script is NOT part of the package; it is a fixture-generation utility.

The affect preset expansion below mirrors the table that affect.py will own in
T004. It is duplicated here only to bootstrap the golden request fixture.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ubu_phase0.schema import (  # noqa: E402
    AffectDimensionName,
    AffectDimensionSpec,
    AffectDirection,
    AffectProfile,
    AuthoritySource,
    ComputeBudget,
    ConstraintPolicy,
    DependencyEdge,
    ExplanationRequest,
    FixedDuration,
    HorizonPolicy,
    PHASE0_WINDOW_SECONDS,
    PlanningRequest,
    Priority,
    ScoringPolicy,
    TaskGraph,
    TaskSpec,
    TimeWindow,
    UniverseStateSnapshot,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"

# Affect preset table (mirrors affect.py / PHASE0_CONTRACT_PROFILE.md).
ENERGY = {
    "low": (3.0, 1.0, 0.5),
    "medium": (4.0, 1.5, 0.5),
    "high": (6.0, 1.5, 0.3),
}
STRESS = {
    "low": (7.0, 1.5, 0.5),
    "medium": (5.5, 1.2, 0.5),
    "high": (4.0, 1.0, 0.6),
}
MOOD = {
    "calm": (8.0, 1.5, 0.5),
    "engaged": (6.5, 1.2, 0.5),
    "intense": (5.0, 1.0, 0.6),
}

# Skip-calibration / demo defaults: medium energy, low stress, calm mood.
DEFAULT_PRESETS = {"energy": "medium", "stress": "low", "mood_intensity": "calm"}

# Per-task predicted affect demand on the 0-10 scale, keyed by issue number.
# Derived from the ubu:energy/stress/mood labels in the static fixture.
AFFECT_REQUIREMENT = {
    8: {"energy": 5.0, "stress": 3.0, "mood_intensity": 3.0},
    12: {"energy": 5.0, "stress": 5.0, "mood_intensity": 5.0},
    15: {"energy": 5.0, "stress": 3.0, "mood_intensity": 3.0},
    19: {"energy": 8.0, "stress": 8.0, "mood_intensity": 8.0},
    23: {"energy": 3.0, "stress": 2.0, "mood_intensity": 2.0},
}

DURATION = {8: 1800, 12: 1800, 15: 3600, 19: 5400, 23: 900}
PRIORITY = {8: "high", 12: "high", 15: "medium", 19: "medium", 23: "low"}


def build_affect_profile() -> AffectProfile:
    e = ENERGY[DEFAULT_PRESETS["energy"]]
    s = STRESS[DEFAULT_PRESETS["stress"]]
    m = MOOD[DEFAULT_PRESETS["mood_intensity"]]
    return AffectProfile(
        energy=AffectDimensionSpec(
            dimension=AffectDimensionName.energy,
            direction=AffectDirection.higher_is_better,
            location=e[0], scale=e[1], threshold=e[2],
        ),
        stress=AffectDimensionSpec(
            dimension=AffectDimensionName.stress,
            direction=AffectDirection.lower_is_better,
            location=s[0], scale=s[1], threshold=s[2],
        ),
        mood_intensity=AffectDimensionSpec(
            dimension=AffectDimensionName.mood_intensity,
            direction=AffectDirection.lower_is_better,
            location=m[0], scale=m[1], threshold=m[2],
        ),
        preset_labels=dict(DEFAULT_PRESETS),
        needs_review=True,
    )


def build_tasks() -> tuple[list[TaskSpec], list[DependencyEdge]]:
    raw = json.loads((FIXTURES / "static_dummy_issue.json").read_text())
    tasks: list[TaskSpec] = []
    for issue in raw["issues"]:
        if issue.get("pull_request"):
            continue  # PR exclusion
        n = issue["number"]
        ref = f"github:UbU-dummy/ubu-design#{n}"
        tasks.append(
            TaskSpec(
                id=ref,
                title=issue["title"],
                description=issue["body"],
                source_ref=ref,
                external_id=str(n),
                external_url=issue["html_url"],
                authority_source=AuthoritySource.imported_config,
                duration=FixedDuration(seconds=DURATION[n]),
                priority=Priority(PRIORITY[n]),
                affect_requirement=AFFECT_REQUIREMENT[n],
                dependencies=[],
                raw_labels=issue["labels"],
            )
        )
    edges = [
        DependencyEdge(**e) for e in raw["hardcoded_dependency_edges"]
    ]
    # Populate per-task dependency lists from edges.
    by_id = {t.id: t for t in tasks}
    for edge in edges:
        if edge.after_task_id in by_id:
            by_id[edge.after_task_id].dependencies.append(edge.before_task_id)
    return tasks, edges


def main() -> None:
    tasks, edges = build_tasks()
    start = "2026-06-09T09:00:00Z"
    end = "2026-06-09T13:00:00Z"  # +4 hours
    assert PHASE0_WINDOW_SECONDS == 4 * 60 * 60

    request = PlanningRequest(
        planner_version="ubu-phase0/0.1.0",
        request_id="req-phase0-demo-0001",
        effective_time=start,
        generated_at="2026-06-09T08:59:00Z",
        rng_seed=20260609,
        time_window=TimeWindow(start_time=start, end_time=end),
        horizon_policy=HorizonPolicy(),
        compute_budget=ComputeBudget(),
        task_graph=TaskGraph(
            tasks=tasks,
            dependency_edges=edges,
            topological_order=None,
        ),
        universe_state_snapshot=UniverseStateSnapshot(
            snapshot_id="snap-phase0-demo-0001",
            snapshot_effective_time=start,
        ),
        affect_profile=build_affect_profile(),
        scoring_policy=ScoringPolicy(),
        constraint_policy=ConstraintPolicy(),
        explanation_request=ExplanationRequest(),
    )

    out = FIXTURES / "demo_request.json"
    out.write_text(json.dumps(request.model_dump(mode="json"), indent=2) + "\n")
    # Round-trip check.
    reloaded = PlanningRequest.model_validate_json(out.read_text())
    assert reloaded.request_id == request.request_id
    print(f"Wrote and validated {out} ({len(tasks)} tasks, {len(edges)} edges)")


if __name__ == "__main__":
    main()
