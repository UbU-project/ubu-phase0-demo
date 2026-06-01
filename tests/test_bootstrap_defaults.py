"""Acceptance tests for PHASE0-T006: bootstrap.

Covers:
- skip-calibration defaults (energy=medium, stress=low, mood_intensity=calm)
- default_affect_profile returns a valid AffectProfile with correct preset_labels
- select_affect_profile accepts all valid preset combinations
- qualitative choice lists are exposed (no raw sigmoid parameters)
- import boundaries (bootstrap must not import planner, loop, cli, github_ingest)
"""

from __future__ import annotations

import pathlib

from ubu_phase0.bootstrap import (
    DEFAULT_ENERGY,
    DEFAULT_MOOD_INTENSITY,
    DEFAULT_STRESS,
    ENERGY_CHOICES,
    MOOD_INTENSITY_CHOICES,
    STRESS_CHOICES,
    default_affect_profile,
    select_affect_profile,
)
from ubu_phase0.schema import (
    AffectDirection,
    AffectProfile,
    EnergyPreset,
    MoodPreset,
    StressPreset,
)


# ---------------------------------------------------------------------------
# Skip-calibration defaults
# ---------------------------------------------------------------------------


def test_default_energy_is_medium():
    assert DEFAULT_ENERGY is EnergyPreset.medium


def test_default_stress_is_low():
    assert DEFAULT_STRESS is StressPreset.low


def test_default_mood_intensity_is_calm():
    assert DEFAULT_MOOD_INTENSITY is MoodPreset.calm


# ---------------------------------------------------------------------------
# default_affect_profile
# ---------------------------------------------------------------------------


def test_default_affect_profile_returns_affect_profile():
    profile = default_affect_profile()
    assert isinstance(profile, AffectProfile)


def test_default_affect_profile_preset_labels():
    profile = default_affect_profile()
    assert profile.preset_labels["energy"] == "medium"
    assert profile.preset_labels["stress"] == "low"
    assert profile.preset_labels["mood_intensity"] == "calm"


def test_default_affect_profile_needs_review():
    profile = default_affect_profile()
    assert profile.needs_review is True


def test_default_affect_profile_directions():
    profile = default_affect_profile()
    assert profile.energy.direction is AffectDirection.higher_is_better
    assert profile.stress.direction is AffectDirection.lower_is_better
    assert profile.mood_intensity.direction is AffectDirection.lower_is_better


def test_default_affect_profile_is_deterministic():
    assert default_affect_profile() == default_affect_profile()


# ---------------------------------------------------------------------------
# select_affect_profile
# ---------------------------------------------------------------------------


def test_select_affect_profile_uses_provided_presets():
    profile = select_affect_profile(
        energy=EnergyPreset.high,
        stress=StressPreset.medium,
        mood_intensity=MoodPreset.engaged,
    )
    assert profile.preset_labels["energy"] == "high"
    assert profile.preset_labels["stress"] == "medium"
    assert profile.preset_labels["mood_intensity"] == "engaged"


def test_select_affect_profile_defaults_match_skip_calibration():
    explicit = select_affect_profile(
        energy=EnergyPreset.medium,
        stress=StressPreset.low,
        mood_intensity=MoodPreset.calm,
    )
    assert explicit == default_affect_profile()


def test_select_affect_profile_all_energy_presets():
    for preset in EnergyPreset:
        profile = select_affect_profile(energy=preset)
        assert profile.preset_labels["energy"] == preset.value


def test_select_affect_profile_all_stress_presets():
    for preset in StressPreset:
        profile = select_affect_profile(stress=preset)
        assert profile.preset_labels["stress"] == preset.value


def test_select_affect_profile_all_mood_presets():
    for preset in MoodPreset:
        profile = select_affect_profile(mood_intensity=preset)
        assert profile.preset_labels["mood_intensity"] == preset.value


# ---------------------------------------------------------------------------
# Qualitative choice lists
# ---------------------------------------------------------------------------


def test_energy_choices_are_all_presets():
    assert set(ENERGY_CHOICES) == set(EnergyPreset)


def test_stress_choices_are_all_presets():
    assert set(STRESS_CHOICES) == set(StressPreset)


def test_mood_intensity_choices_are_all_presets():
    assert set(MOOD_INTENSITY_CHOICES) == set(MoodPreset)


# ---------------------------------------------------------------------------
# Import boundary
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
            for alias in node.names:
                imported_names.add(alias.name)

    return imported_names


def test_bootstrap_import_boundaries():
    bootstrap_path = (
        pathlib.Path(__file__).parent.parent / "src" / "ubu_phase0" / "bootstrap.py"
    )
    source = bootstrap_path.read_text()

    forbidden = {"planner", "loop", "cli", "github_ingest"}
    imported_names = _imported_names_from_source(source)

    violations = forbidden & imported_names
    assert not violations, f"bootstrap.py imports forbidden module(s): {violations}"
