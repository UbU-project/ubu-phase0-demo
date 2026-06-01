"""UbU Phase 0 bootstrap.

Provides skip-calibration default affect profile and qualitative preset
selection helpers. Delegates sigmoid-parameter expansion to affect.py.

May import: schema, affect, stdlib only.
Forbidden: planner, github_ingest, loop, cli; file I/O; env vars; GitHub.
"""

from __future__ import annotations

from ubu_phase0.affect import (
    DEFAULT_ENERGY_PRESET,
    DEFAULT_MOOD_PRESET,
    DEFAULT_STRESS_PRESET,
    preset_to_affect_profile,
)
from ubu_phase0.schema import AffectProfile, EnergyPreset, MoodPreset, StressPreset

# Skip-calibration defaults: energy=medium, stress=low, mood_intensity=calm.
DEFAULT_ENERGY: EnergyPreset = DEFAULT_ENERGY_PRESET
DEFAULT_STRESS: StressPreset = DEFAULT_STRESS_PRESET
DEFAULT_MOOD_INTENSITY: MoodPreset = DEFAULT_MOOD_PRESET

# Qualitative choices available to the operator (no raw sigmoid parameters).
ENERGY_CHOICES: list[EnergyPreset] = list(EnergyPreset)
STRESS_CHOICES: list[StressPreset] = list(StressPreset)
MOOD_INTENSITY_CHOICES: list[MoodPreset] = list(MoodPreset)


def default_affect_profile() -> AffectProfile:
    """Return the skip-calibration default AffectProfile (energy=medium, stress=low, mood_intensity=calm)."""
    return preset_to_affect_profile(
        energy=DEFAULT_ENERGY,
        stress=DEFAULT_STRESS,
        mood_intensity=DEFAULT_MOOD_INTENSITY,
    )


def select_affect_profile(
    energy: EnergyPreset = DEFAULT_ENERGY,
    stress: StressPreset = DEFAULT_STRESS,
    mood_intensity: MoodPreset = DEFAULT_MOOD_INTENSITY,
) -> AffectProfile:
    """Expand qualitative preset choices into an AffectProfile.

    Raw sigmoid parameters are never surfaced; only preset labels are visible.
    Delegates to affect.preset_to_affect_profile.
    """
    return preset_to_affect_profile(
        energy=energy,
        stress=stress,
        mood_intensity=mood_intensity,
    )
