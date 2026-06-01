"""UbU Phase 0 affect gate.

Owns: preset table, preset-to-sigmoid-parameter expansion, sigmoid evaluation,
and per-task affect-feasibility checks.

May import: schema, math, stdlib only.
Forbidden: planner, github_ingest, bootstrap, loop, cli; file I/O; env vars; GitHub.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from ubu_phase0.schema import (
    AffectDimensionName,
    AffectDimensionSpec,
    AffectDirection,
    AffectProfile,
    EnergyPreset,
    MoodPreset,
    StressPreset,
    TaskSpec,
)

# ---------------------------------------------------------------------------
# Internal parameter tuple
# ---------------------------------------------------------------------------


class _SigmoidParams(NamedTuple):
    location: float
    scale: float
    threshold: float


# ---------------------------------------------------------------------------
# Preset tables (verbatim from PHASE0_CONTRACT_PROFILE.md §6.6)
# ---------------------------------------------------------------------------

_ENERGY_PRESETS: dict[EnergyPreset, _SigmoidParams] = {
    EnergyPreset.low: _SigmoidParams(location=3.0, scale=1.0, threshold=0.5),
    EnergyPreset.medium: _SigmoidParams(location=4.0, scale=1.5, threshold=0.5),
    EnergyPreset.high: _SigmoidParams(location=6.0, scale=1.5, threshold=0.3),
}

_STRESS_PRESETS: dict[StressPreset, _SigmoidParams] = {
    StressPreset.low: _SigmoidParams(location=7.0, scale=1.5, threshold=0.5),
    StressPreset.medium: _SigmoidParams(location=5.5, scale=1.2, threshold=0.5),
    StressPreset.high: _SigmoidParams(location=4.0, scale=1.0, threshold=0.6),
}

_MOOD_PRESETS: dict[MoodPreset, _SigmoidParams] = {
    MoodPreset.calm: _SigmoidParams(location=8.0, scale=1.5, threshold=0.5),
    MoodPreset.engaged: _SigmoidParams(location=6.5, scale=1.2, threshold=0.5),
    MoodPreset.intense: _SigmoidParams(location=5.0, scale=1.0, threshold=0.6),
}

# Skip-calibration defaults (most permissive that still lets the gate fire on
# demonstrably stressful tasks).
DEFAULT_ENERGY_PRESET = EnergyPreset.medium
DEFAULT_STRESS_PRESET = StressPreset.low
DEFAULT_MOOD_PRESET = MoodPreset.calm


# ---------------------------------------------------------------------------
# Preset-to-profile expansion (pure function; reused by bootstrap and v1.5)
# ---------------------------------------------------------------------------


def preset_to_affect_profile(
    energy: EnergyPreset = DEFAULT_ENERGY_PRESET,
    stress: StressPreset = DEFAULT_STRESS_PRESET,
    mood_intensity: MoodPreset = DEFAULT_MOOD_PRESET,
) -> AffectProfile:
    """Expand qualitative preset choices into a full AffectProfile.

    This is the only place that translates preset labels to sigmoid parameters.
    Raw parameters are never shown to users; only the preset labels are surfaced.
    """
    ep = _ENERGY_PRESETS[energy]
    sp = _STRESS_PRESETS[stress]
    mp = _MOOD_PRESETS[mood_intensity]

    return AffectProfile(
        energy=AffectDimensionSpec(
            dimension=AffectDimensionName.energy,
            direction=AffectDirection.higher_is_better,
            location=ep.location,
            scale=ep.scale,
            threshold=ep.threshold,
        ),
        stress=AffectDimensionSpec(
            dimension=AffectDimensionName.stress,
            direction=AffectDirection.lower_is_better,
            location=sp.location,
            scale=sp.scale,
            threshold=sp.threshold,
        ),
        mood_intensity=AffectDimensionSpec(
            dimension=AffectDimensionName.mood_intensity,
            direction=AffectDirection.lower_is_better,
            location=mp.location,
            scale=mp.scale,
            threshold=mp.threshold,
        ),
        preset_labels={
            "energy": energy.value,
            "stress": stress.value,
            "mood_intensity": mood_intensity.value,
        },
        needs_review=True,
    )


# ---------------------------------------------------------------------------
# Sigmoid evaluation
# ---------------------------------------------------------------------------


def sigmoid(x: float) -> float:
    """Standard logistic sigmoid, numerically stable."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


def dimension_satisfaction(spec: AffectDimensionSpec, value: float) -> float:
    """Compute satisfaction score in [0, 1] for one affect dimension.

    higher_is_better: satisfaction = sigmoid((value - location) / scale)
    lower_is_better:  satisfaction = sigmoid((location - value) / scale)
    """
    if spec.direction is AffectDirection.higher_is_better:
        return sigmoid((value - spec.location) / spec.scale)
    return sigmoid((spec.location - value) / spec.scale)


# ---------------------------------------------------------------------------
# Per-task affect-feasibility check
# ---------------------------------------------------------------------------


class AffectFeasibilityResult(NamedTuple):
    feasible: bool
    satisfaction_scores: dict[str, float]
    violated_dimensions: list[str]
    minimum_score: float


def check_task_affect_feasibility(
    profile: AffectProfile,
    task: TaskSpec,
) -> AffectFeasibilityResult:
    """Check whether a task's affect requirements are feasible under the profile.

    A task is feasible iff every active dimension has satisfaction >= threshold.
    Dimensions absent from task.affect_requirement are skipped (not constrained).
    """
    dim_specs: dict[str, AffectDimensionSpec] = {
        AffectDimensionName.energy.value: profile.energy,
        AffectDimensionName.stress.value: profile.stress,
        AffectDimensionName.mood_intensity.value: profile.mood_intensity,
    }

    scores: dict[str, float] = {}
    violated: list[str] = []

    for dim_name, spec in dim_specs.items():
        if dim_name not in task.affect_requirement:
            continue
        value = task.affect_requirement[dim_name]
        sat = dimension_satisfaction(spec, value)
        scores[dim_name] = sat
        if sat < spec.threshold:
            violated.append(dim_name)

    min_score = min(scores.values()) if scores else 1.0
    return AffectFeasibilityResult(
        feasible=len(violated) == 0,
        satisfaction_scores=scores,
        violated_dimensions=violated,
        minimum_score=min_score,
    )
