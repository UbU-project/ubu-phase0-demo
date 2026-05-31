"""PHASE0-T001 acceptance test: schema contract invariants.

Asserts that the frozen schema carries the right constants, the profile string,
the Phase 0 sentinels, the required model fields, and that unsupported fields
serialize as None or sentinel rather than disappearing.
"""

from ubu_phase0 import schema as s


def test_profile_and_sentinel_constants_exist():
    assert s.PHASE0_PROFILE == "planning-kernel-contract/phase0-profile/0.1"
    assert s.PHASE1_SCHEMA_VERSION == "planning-kernel-contract/0.1"
    assert s.PHASE0_NOT_SUPPORTED == "not_supported"
    assert s.PHASE0_NOT_ESTIMATED == "not_estimated"
    assert s.PHASE0_DEFAULT_DURATION_SECONDS == 1800
    assert s.PHASE0_WINDOW_SECONDS == 4 * 60 * 60


def test_authority_source_is_the_closed_d0185_enum():
    values = {a.value for a in s.AuthoritySource}
    assert values == {
        "human_admin",
        "automation_worker",
        "github_event",
        "project_policy",
        "imported_config",
        "llm_advisory",
        "user_override",
    }


def test_affect_dimensions_and_directions():
    assert {d.value for d in s.AffectDimensionName} == {
        "energy",
        "stress",
        "mood_intensity",
    }


def test_phase0_supports_fresh_generation_only():
    import pytest

    # A repair-mode request must be rejected by the model validator.
    with pytest.raises(Exception):
        _minimal_request(mode=s.PlanningMode.repair)


def test_probability_summary_provenance_is_sentinel():
    ps = s.ProbabilitySummary()
    assert ps.provenance_refs == s.PHASE0_NOT_ESTIMATED
    assert ps.display_probability is None


def test_diagnostics_default_to_not_estimated_with_null_coverage():
    d = s.Diagnostics()
    assert d.probability_quality is s.ProbabilityQuality.not_estimated
    assert d.coverage_estimate is None
    assert d.coverage_below_threshold is None


def test_deferred_fields_present_not_absent():
    # repair_context and external_event_assumptions are carried, not removed.
    req = _minimal_request()
    dumped = req.model_dump(mode="json")
    assert "repair_context" in dumped
    assert dumped["repair_context"] is None
    assert dumped["external_event_assumptions"] == []
    # privacy payload safety carries the sentinel, not a removed field.
    assert dumped["privacy_and_provenance"]["payload_safety_proof"] == s.PHASE0_NOT_SUPPORTED


def test_logentry_present_in_frozen_schema():
    # LogEntry must exist now so v1.5 log-replan is not a schema change.
    entry = s.LogEntry(
        task_ref="github:UbU-dummy/ubu-design#8",
        outcome=s.LogOutcome.completed,
        effective_time="2026-06-09T09:30:00Z",
    )
    assert entry.authority_source is s.AuthoritySource.user_override


def test_skeleton_failure_diagnostic_present_in_frozen_schema():
    diag = s.SkeletonFailureDiagnostic(
        diagnostic_id="d1",
        severity=s.SkeletonSeverity.blocking,
        failure_class=s.SkeletonFailureClass.cyclic_dependency,
        prompt_policy="immediate_blocking_prompt",
        user_facing_summary="A dependency cycle prevents a valid baseline.",
    )
    assert diag.failure_class is s.SkeletonFailureClass.cyclic_dependency


def test_calibration_frame_hint_reserved():
    # Reserved field shape for v1.5 calibration surfacing must exist.
    frag = s.ExplanationFragment(text="why this task now")
    assert frag.calibration_frame_hint is None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _minimal_request(mode: "s.PlanningMode | None" = None) -> s.PlanningRequest:
    kwargs = dict(
        planner_version="ubu-phase0/0.1.0",
        request_id="req-test",
        effective_time="2026-06-09T09:00:00Z",
        generated_at="2026-06-09T08:59:00Z",
        rng_seed=1,
        time_window=s.TimeWindow(
            start_time="2026-06-09T09:00:00Z", end_time="2026-06-09T13:00:00Z"
        ),
        task_graph=s.TaskGraph(),
        universe_state_snapshot=s.UniverseStateSnapshot(
            snapshot_id="snap", snapshot_effective_time="2026-06-09T09:00:00Z"
        ),
        affect_profile=_minimal_affect(),
    )
    if mode is not None:
        kwargs["mode"] = mode
    return s.PlanningRequest(**kwargs)


def _minimal_affect() -> s.AffectProfile:
    return s.AffectProfile(
        energy=s.AffectDimensionSpec(
            dimension=s.AffectDimensionName.energy,
            direction=s.AffectDirection.higher_is_better,
            location=4.0, scale=1.5, threshold=0.5,
        ),
        stress=s.AffectDimensionSpec(
            dimension=s.AffectDimensionName.stress,
            direction=s.AffectDirection.lower_is_better,
            location=7.0, scale=1.5, threshold=0.5,
        ),
        mood_intensity=s.AffectDimensionSpec(
            dimension=s.AffectDimensionName.mood_intensity,
            direction=s.AffectDirection.lower_is_better,
            location=8.0, scale=1.5, threshold=0.5,
        ),
    )
