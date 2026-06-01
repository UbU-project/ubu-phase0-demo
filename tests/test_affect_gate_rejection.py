"""Acceptance tests for PHASE0-T004: affect gate.

Covers:
- preset-to-profile expansion produces correct sigmoid parameters
- sigmoid satisfaction math for both directions
- feasibility pass and rejection cases
- per-dimension threshold boundary
- tasks without affect_requirement are unconstrained (always feasible)
"""

from __future__ import annotations

import pytest

from ubu_phase0.affect import (
    check_task_affect_feasibility,
    dimension_satisfaction,
    preset_to_affect_profile,
    sigmoid,
)
from ubu_phase0.schema import (
    AffectDimensionName,
    AffectDimensionSpec,
    AffectDirection,
    AuthoritySource,
    EnergyPreset,
    FixedDuration,
    MoodPreset,
    StressPreset,
    TaskSpec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(affect_requirement: dict[str, float]) -> TaskSpec:
    return TaskSpec(
        id="github:UbU-dummy/ubu-design#1",
        title="Test task",
        source_ref="github:UbU-dummy/ubu-design#1",
        external_id="1",
        external_url="https://github.com/UbU-dummy/ubu-design/issues/1",
        authority_source=AuthoritySource.github_event,
        duration=FixedDuration(seconds=1800),
        affect_requirement=affect_requirement,
    )


# ---------------------------------------------------------------------------
# sigmoid
# ---------------------------------------------------------------------------


def test_sigmoid_at_zero():
    assert sigmoid(0.0) == pytest.approx(0.5)


def test_sigmoid_large_positive():
    assert sigmoid(100.0) == pytest.approx(1.0, abs=1e-6)


def test_sigmoid_large_negative():
    assert sigmoid(-100.0) == pytest.approx(0.0, abs=1e-6)


def test_sigmoid_monotone():
    values = [-5.0, -2.0, 0.0, 2.0, 5.0]
    sigs = [sigmoid(v) for v in values]
    assert sigs == sorted(sigs)


# ---------------------------------------------------------------------------
# dimension_satisfaction
# ---------------------------------------------------------------------------


def _energy_spec(location: float = 4.0, scale: float = 1.5, threshold: float = 0.5) -> AffectDimensionSpec:
    return AffectDimensionSpec(
        dimension=AffectDimensionName.energy,
        direction=AffectDirection.higher_is_better,
        location=location,
        scale=scale,
        threshold=threshold,
    )


def _stress_spec(location: float = 7.0, scale: float = 1.5, threshold: float = 0.5) -> AffectDimensionSpec:
    return AffectDimensionSpec(
        dimension=AffectDimensionName.stress,
        direction=AffectDirection.lower_is_better,
        location=location,
        scale=scale,
        threshold=threshold,
    )


def test_higher_is_better_at_location_is_half():
    spec = _energy_spec(location=4.0, scale=1.5)
    assert dimension_satisfaction(spec, 4.0) == pytest.approx(0.5)


def test_higher_is_better_above_location_is_above_half():
    spec = _energy_spec(location=4.0, scale=1.5)
    assert dimension_satisfaction(spec, 6.0) > 0.5


def test_higher_is_better_below_location_is_below_half():
    spec = _energy_spec(location=4.0, scale=1.5)
    assert dimension_satisfaction(spec, 2.0) < 0.5


def test_lower_is_better_at_location_is_half():
    spec = _stress_spec(location=7.0, scale=1.5)
    assert dimension_satisfaction(spec, 7.0) == pytest.approx(0.5)


def test_lower_is_better_below_location_is_above_half():
    # stress=4 when location=7 means low stress -> high satisfaction
    spec = _stress_spec(location=7.0, scale=1.5)
    assert dimension_satisfaction(spec, 4.0) > 0.5


def test_lower_is_better_above_location_is_below_half():
    spec = _stress_spec(location=7.0, scale=1.5)
    assert dimension_satisfaction(spec, 9.0) < 0.5


# ---------------------------------------------------------------------------
# preset_to_affect_profile
# ---------------------------------------------------------------------------


def test_default_preset_produces_valid_profile():
    profile = preset_to_affect_profile()
    assert profile.energy.location == pytest.approx(4.0)
    assert profile.stress.location == pytest.approx(7.0)
    assert profile.mood_intensity.location == pytest.approx(8.0)


def test_preset_labels_are_recorded():
    profile = preset_to_affect_profile(
        energy=EnergyPreset.high,
        stress=StressPreset.medium,
        mood_intensity=MoodPreset.engaged,
    )
    assert profile.preset_labels["energy"] == "high"
    assert profile.preset_labels["stress"] == "medium"
    assert profile.preset_labels["mood_intensity"] == "engaged"


def test_all_energy_presets_expand():
    for preset in EnergyPreset:
        profile = preset_to_affect_profile(energy=preset)
        assert profile.energy.location > 0


def test_all_stress_presets_expand():
    for preset in StressPreset:
        profile = preset_to_affect_profile(stress=preset)
        assert profile.stress.location > 0


def test_all_mood_presets_expand():
    for preset in MoodPreset:
        profile = preset_to_affect_profile(mood_intensity=preset)
        assert profile.mood_intensity.location > 0


def test_directions_are_correct():
    profile = preset_to_affect_profile()
    assert profile.energy.direction == AffectDirection.higher_is_better
    assert profile.stress.direction == AffectDirection.lower_is_better
    assert profile.mood_intensity.direction == AffectDirection.lower_is_better


# ---------------------------------------------------------------------------
# check_task_affect_feasibility — pass cases
# ---------------------------------------------------------------------------


def test_no_affect_requirement_is_always_feasible():
    profile = preset_to_affect_profile()
    task = _make_task({})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is True
    assert result.violated_dimensions == []
    assert result.minimum_score == pytest.approx(1.0)


def test_comfortable_energy_is_feasible():
    # energy=medium (loc=4, scale=1.5, threshold=0.5); task energy demand=6 -> satisfied
    profile = preset_to_affect_profile(energy=EnergyPreset.medium)
    task = _make_task({"energy": 6.0})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is True
    assert "energy" not in result.violated_dimensions


def test_low_stress_task_is_feasible_under_low_stress_profile():
    # stress=low (loc=7, scale=1.5, threshold=0.5); task stress=3 -> low stress, high satisfaction
    profile = preset_to_affect_profile(stress=StressPreset.low)
    task = _make_task({"stress": 3.0})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is True


# ---------------------------------------------------------------------------
# check_task_affect_feasibility — rejection cases
# ---------------------------------------------------------------------------


def test_high_stress_task_rejected_under_low_profile():
    # stress=low (loc=7, scale=1.5, threshold=0.5); task stress=9 (very stressful)
    # satisfaction = sigmoid((7-9)/1.5) = sigmoid(-1.33) ≈ 0.21 < 0.5 -> rejected
    profile = preset_to_affect_profile(stress=StressPreset.low)
    task = _make_task({"stress": 9.0})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is False
    assert "stress" in result.violated_dimensions


def test_low_energy_task_rejected_under_high_energy_profile():
    # energy=high (loc=6, scale=1.5, threshold=0.3); task energy=1 (very low demand)
    # direction=higher_is_better: satisfaction = sigmoid((1-6)/1.5) = sigmoid(-3.33) ≈ 0.035 < 0.3 -> rejected
    profile = preset_to_affect_profile(energy=EnergyPreset.high)
    task = _make_task({"energy": 1.0})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is False
    assert "energy" in result.violated_dimensions


def test_intense_mood_task_rejected_under_calm_profile():
    # mood=calm (loc=8, scale=1.5, threshold=0.5); task mood_intensity=9 (very intense)
    # lower_is_better: satisfaction = sigmoid((8-9)/1.5) = sigmoid(-0.67) ≈ 0.34 < 0.5 -> rejected
    profile = preset_to_affect_profile(mood_intensity=MoodPreset.calm)
    task = _make_task({"mood_intensity": 9.0})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is False
    assert "mood_intensity" in result.violated_dimensions


def test_multiple_violations_reported():
    profile = preset_to_affect_profile(
        stress=StressPreset.low,
        mood_intensity=MoodPreset.calm,
    )
    task = _make_task({"stress": 9.5, "mood_intensity": 9.5})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is False
    assert "stress" in result.violated_dimensions
    assert "mood_intensity" in result.violated_dimensions


def test_minimum_score_reflects_worst_dimension():
    profile = preset_to_affect_profile(
        energy=EnergyPreset.medium,
        stress=StressPreset.low,
    )
    task = _make_task({"energy": 7.0, "stress": 3.0})
    result = check_task_affect_feasibility(profile, task)
    expected_energy = dimension_satisfaction(profile.energy, 7.0)
    expected_stress = dimension_satisfaction(profile.stress, 3.0)
    assert result.minimum_score == pytest.approx(min(expected_energy, expected_stress))


# ---------------------------------------------------------------------------
# Threshold boundary
# ---------------------------------------------------------------------------


def test_satisfaction_exactly_at_threshold_is_feasible():
    # Construct a dimension spec where a known value lands exactly at threshold.
    # energy higher_is_better: satisfaction = sigmoid((x-location)/scale) = threshold
    # sigmoid(0)=0.5, so if threshold=0.5 and x=location the sat=0.5 -> feasible
    profile = preset_to_affect_profile(energy=EnergyPreset.medium)  # threshold=0.5
    assert profile.energy.threshold == 0.5
    task = _make_task({"energy": profile.energy.location})  # sat == 0.5 == threshold
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is True  # >= threshold, not strictly greater


def test_satisfaction_just_below_threshold_is_infeasible():
    # energy=medium: loc=4.0, scale=1.5, threshold=0.5
    # Need value slightly below location so sat < 0.5
    profile = preset_to_affect_profile(energy=EnergyPreset.medium)
    task = _make_task({"energy": 3.9})
    result = check_task_affect_feasibility(profile, task)
    assert result.feasible is False


# ---------------------------------------------------------------------------
# Scores are returned for all evaluated dimensions
# ---------------------------------------------------------------------------


def test_scores_returned_for_evaluated_dimensions():
    profile = preset_to_affect_profile()
    task = _make_task({"energy": 5.0, "stress": 4.0})
    result = check_task_affect_feasibility(profile, task)
    assert "energy" in result.satisfaction_scores
    assert "stress" in result.satisfaction_scores
    assert "mood_intensity" not in result.satisfaction_scores


# ---------------------------------------------------------------------------
# Import boundary: affect must not import planner, loop, cli, github_ingest
# ---------------------------------------------------------------------------


def _imported_names_from_source(source: str) -> set[str]:
    import ast

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
            # also capture relative imports resolved to ubu_phase0.*
            for alias in node.names:
                imported_names.add(alias.name)

    return imported_names


def test_import_scanner_detects_dotted_forbidden_submodule_import():
    imported_names = _imported_names_from_source("from ubu_phase0.planner import plan\n")
    assert "planner" in imported_names


def test_affect_import_boundaries():
    import pathlib

    affect_path = pathlib.Path(__file__).parent.parent / "src" / "ubu_phase0" / "affect.py"
    source = affect_path.read_text()

    forbidden = {"planner", "loop", "cli", "github_ingest", "bootstrap"}
    imported_names = _imported_names_from_source(source)

    violations = forbidden & imported_names
    assert not violations, f"affect.py imports forbidden module(s): {violations}"
