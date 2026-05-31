"""UbU Phase 0 schema (FROZEN after ticket PHASE0-T001).

This module is the shared vocabulary for the entire Phase 0 demo. It implements
the Phase 0 subset of the frozen Phase 1 planning-kernel contract
(``planning-kernel-contract/0.1``) under the profile identifier
``planning-kernel-contract/phase0-profile/0.1``.

FREEZE RULE
-----------
After PHASE0-T001 is accepted, this file is frozen. No later ticket may edit it
unless that ticket is explicitly a schema-change ticket and the freeze is
consciously reopened. Schema drift propagates to every downstream module, so
this is the single most important discipline in the workflow.

DESIGN NOTES
------------
* Deferred Phase 1 fields are PRESENT here as ``Optional[...] = None`` or literal
  sentinels. They are never silently removed. A field that exists as ``None`` is
  a clear contract slot; a field that does not exist is a trap for later work.
* There is no ``Omitted`` wrapper model. Sentinels are simple string constants.
* ``authority_source`` (UBU-D0185) is carried on every Task. It is provenance,
  not authorization, and gates nothing in Phase 0.
* The sigmoid affect functions and the qualitative-preset expansion live in
  ``affect.py``; this module only defines the data shapes and the qualitative
  preset enums.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Constants and sentinels
# ---------------------------------------------------------------------------

PHASE1_SCHEMA_VERSION = "planning-kernel-contract/0.1"
PHASE0_PROFILE = "planning-kernel-contract/phase0-profile/0.1"

PHASE0_NOT_SUPPORTED = "not_supported"
PHASE0_NOT_ESTIMATED = "not_estimated"

# Phase 0 fixed-duration default, in seconds (30 minutes).
PHASE0_DEFAULT_DURATION_SECONDS = 1800

# Phase 0 planning window length, in seconds (4 hours).
PHASE0_WINDOW_SECONDS = 4 * 60 * 60


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AuthoritySource(str, Enum):
    """Closed MVP source-path enum (UBU-D0185).

    Phase 0 only ever emits ``github_event``, ``imported_config``, and
    ``user_override``. The remaining values are carried for contract fidelity.
    """

    human_admin = "human_admin"
    automation_worker = "automation_worker"
    github_event = "github_event"
    project_policy = "project_policy"
    imported_config = "imported_config"
    llm_advisory = "llm_advisory"
    user_override = "user_override"


class PlanningMode(str, Enum):
    fresh_generation = "fresh_generation"
    repair = "repair"  # not supported in Phase 0; present for fidelity


class PlanningStatus(str, Enum):
    ok = "ok"
    partial = "partial"
    rejected = "rejected"
    engine_error = "engine_error"


class AffectDimensionName(str, Enum):
    energy = "energy"
    stress = "stress"
    mood_intensity = "mood_intensity"


class AffectDirection(str, Enum):
    higher_is_better = "higher_is_better"
    lower_is_better = "lower_is_better"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class CandidateRole(str, Enum):
    highest_utility = "highest_utility"
    most_robust = "most_robust"
    most_schedule_diverse = "most_schedule_diverse"
    other = "other"


class SemiLegitimizationResult(str, Enum):
    passes_cheap_checks = "passes_cheap_checks"
    reject_obvious = "reject_obvious"
    needs_full_legitimization = "needs_full_legitimization"


class ProbabilityQuality(str, Enum):
    full = "full"
    degraded_numeric_jitter = "degraded_numeric_jitter"
    degraded_independence = "degraded_independence"
    not_estimated = "not_estimated"


class SkeletonSeverity(str, Enum):
    blocking = "blocking"
    warning = "warning"


class SkeletonFailureClass(str, Enum):
    missing_starting_state = "missing_starting_state"
    impossible_dependency = "impossible_dependency"
    cyclic_dependency = "cyclic_dependency"
    static_task_collision = "static_task_collision"
    insufficient_calendar_window = "insufficient_calendar_window"
    unavailable_resource = "unavailable_resource"
    blocked_external_event = "blocked_external_event"
    unknown_precondition = "unknown_precondition"


class LogOutcome(str, Enum):
    completed = "completed"
    skipped = "skipped"
    blocked = "blocked"


# Qualitative bootstrap presets. The expansion to sigmoid parameters lives in
# affect.py; users never see raw location/scale/threshold values.


class EnergyPreset(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class StressPreset(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class MoodPreset(str, Enum):
    calm = "calm"
    engaged = "engaged"
    intense = "intense"


# ---------------------------------------------------------------------------
# Duration model (fixed only in Phase 0)
# ---------------------------------------------------------------------------


class FixedDuration(BaseModel):
    """Fixed duration as a delta distribution.

    The shifted-log-normal model and correlation groups are NOT supported in
    Phase 0 and are intentionally absent.
    """

    type: Literal["fixed"] = "fixed"
    seconds: int = Field(gt=0)


# ---------------------------------------------------------------------------
# Affect
# ---------------------------------------------------------------------------


class AffectDimensionSpec(BaseModel):
    """One sigmoid affect dimension on the user-facing 0-10 scale."""

    dimension: AffectDimensionName
    direction: AffectDirection
    location: float
    scale: float = Field(gt=0)
    threshold: float = Field(ge=0.0, le=1.0)
    freshness_seconds: Optional[int] = None


class AffectProfile(BaseModel):
    """Phase 0 affect profile: exactly energy, stress, mood_intensity.

    ``preset_labels`` records the qualitative choices the operator made (or the
    skip-calibration defaults) so they can be surfaced in explanations and the
    claim register without exposing raw sigmoid parameters.
    """

    energy: AffectDimensionSpec
    stress: AffectDimensionSpec
    mood_intensity: AffectDimensionSpec
    preset_labels: dict[str, str] = Field(default_factory=dict)
    needs_review: bool = True  # bootstrap defaults are temporary priors

    @model_validator(mode="after")
    def _check_directions(self) -> "AffectProfile":
        if self.energy.direction is not AffectDirection.higher_is_better:
            raise ValueError("energy must be higher_is_better in Phase 1/0")
        if self.stress.direction is not AffectDirection.lower_is_better:
            raise ValueError("stress must be lower_is_better in Phase 1/0")
        if self.mood_intensity.direction is not AffectDirection.lower_is_better:
            raise ValueError("mood_intensity must be lower_is_better in Phase 1/0")
        return self


# ---------------------------------------------------------------------------
# TaskSpec and task graph
# ---------------------------------------------------------------------------


class TaskSpec(BaseModel):
    """A single planning Task derived from a GitHub issue.

    ``affect_requirement`` carries the per-dimension predicted affect VALUE for
    this task on the 0-10 scale (label-derived or safe default). The affect gate
    evaluates the operator's AffectProfile against these values.
    """

    id: str
    title: str
    description: str = ""
    source: Literal["github_issue"] = "github_issue"
    source_ref: str
    external_id: str
    external_url: str
    authority_source: AuthoritySource
    duration: FixedDuration
    priority: Priority = Priority.medium
    # Predicted affect demand of this task on the 0-10 scale, by dimension.
    affect_requirement: dict[str, float] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    # Unknown GitHub labels preserved for display; never affect scheduling.
    raw_labels: list[str] = Field(default_factory=list)


class DependencyEdge(BaseModel):
    before_task_id: str
    after_task_id: str


class TaskGraph(BaseModel):
    tasks: list[TaskSpec] = Field(default_factory=list)
    dependency_edges: list[DependencyEdge] = Field(default_factory=list)
    # CPU-supplied topological order. In Phase 0 the planner computes it; the
    # field is carried for contract fidelity.
    topological_order: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# PlanningRequest sub-objects
# ---------------------------------------------------------------------------


class TimeWindow(BaseModel):
    start_time: str  # RFC 3339 / ISO 8601 UTC
    end_time: str
    planning_delta_seconds: int = 60


class HorizonPolicy(BaseModel):
    reactive_horizon_seconds: int = 3600
    # Carried but unused in Phase 0 (no coverage estimation).
    branch_coverage_target: Optional[float] = None


class ComputeBudget(BaseModel):
    max_planning_tasks: int = 256
    n_candidates: int = 1
    n_rollouts: int = 0  # no rollout in Phase 0
    k_candidates: int = 1
    max_wall_clock_ms: Optional[int] = None


class UniverseStateSnapshot(BaseModel):
    snapshot_id: str
    snapshot_effective_time: str
    state_refs: list[str] = Field(default_factory=list)
    # Phase 0 uses only public dummy data; no real compartment policy applies.
    payload_policy_summary: str = PHASE0_NOT_SUPPORTED


class ScoringPolicy(BaseModel):
    utility_weight: float = 1.0
    robustness_weight: float = 0.0  # no stochastic modeling in Phase 0
    affect_margin_weight: float = 1.0
    schedule_diversity_weight: float = 0.0


class ConstraintPolicy(BaseModel):
    hard_constraints_always_required: Literal[True] = True
    affect_constraint_mode: Literal["enforce", "warn_only"] = "enforce"


class PrivacyAndProvenance(BaseModel):
    compartment_ids: list[str] = Field(default_factory=list)
    redaction_level: str = "public_demo"
    # Phase 0 does not enforce payload safety; public dummy data only.
    payload_safety_proof: str = PHASE0_NOT_SUPPORTED
    payload_verified_safe: bool = True


class ExplanationRequest(BaseModel):
    include_rejection_summary: bool = True
    include_score_breakdown: bool = False
    include_user_facing_fragments: bool = True


# ---------------------------------------------------------------------------
# PlanningRequest
# ---------------------------------------------------------------------------


class PlanningRequest(BaseModel):
    schema_version: str = PHASE1_SCHEMA_VERSION
    profile: str = PHASE0_PROFILE
    planner_version: str
    request_id: str
    effective_time: str
    generated_at: str
    mode: PlanningMode = PlanningMode.fresh_generation
    rng_seed: int

    time_window: TimeWindow
    horizon_policy: HorizonPolicy = Field(default_factory=HorizonPolicy)
    compute_budget: ComputeBudget = Field(default_factory=ComputeBudget)
    task_graph: TaskGraph
    universe_state_snapshot: UniverseStateSnapshot
    affect_profile: AffectProfile
    scoring_policy: ScoringPolicy = Field(default_factory=ScoringPolicy)
    constraint_policy: ConstraintPolicy = Field(default_factory=ConstraintPolicy)
    privacy_and_provenance: PrivacyAndProvenance = Field(
        default_factory=PrivacyAndProvenance
    )
    explanation_request: ExplanationRequest = Field(default_factory=ExplanationRequest)

    # Inert / not supported in Phase 0; present for fidelity.
    external_event_assumptions: list[dict] = Field(default_factory=list)
    repair_context: Optional[dict] = None  # absent: no repair mode in Phase 0

    @model_validator(mode="after")
    def _phase0_mode_only(self) -> "PlanningRequest":
        if self.mode is not PlanningMode.fresh_generation:
            raise ValueError("Phase 0 supports mode=fresh_generation only")
        if self.repair_context is not None:
            raise ValueError("Phase 0 does not support repair_context")
        return self


# ---------------------------------------------------------------------------
# LogEntry (schema present in v1; exercised in v1.5 log-replan)
# ---------------------------------------------------------------------------


class LogEntry(BaseModel):
    task_ref: str
    outcome: LogOutcome
    effective_time: str
    authority_source: AuthoritySource = AuthoritySource.user_override


# ---------------------------------------------------------------------------
# PlanningResponse sub-objects
# ---------------------------------------------------------------------------


class ScheduledPlacement(BaseModel):
    task_id: str
    start_time: str
    end_time: str


class ScoreSummary(BaseModel):
    utility_score: float = 0.0
    robustness_score: float = 0.0
    affect_margin_score: float = 0.0
    schedule_diversity_score: float = 0.0
    total_score: float = 0.0


class FeasibilitySummary(BaseModel):
    hard_constraints_assumed_satisfied_by_engine: bool = True  # advisory only
    affect_feasible: bool = True
    minimum_affect_score: float = 0.0
    violated_affect_dimensions: list[str] = Field(default_factory=list)


class SemiLegitimizationSummary(BaseModel):
    """Cheap pre-validation layer (UBU-D0211). Implemented in Phase 0."""

    result: SemiLegitimizationResult
    affect_budget_ok: Optional[bool] = None
    slack_preserved: Optional[bool] = None
    dependency_fragility_ok: Optional[bool] = None
    user_mode_compatible: Optional[bool] = None
    local_repair_viable: Optional[bool] = None
    legitimacy_delta_estimate: Optional[float] = None


class ProbabilitySummary(BaseModel):
    display_probability: Optional[float] = None
    log_probability: Optional[float] = None
    probability_interval: Optional[tuple[float, float]] = None
    # Phase 0 estimates no probability. Do not populate in phase0-profile/0.1.
    provenance_refs: Literal["not_estimated"] = PHASE0_NOT_ESTIMATED  # type: ignore[assignment]


class CalibrationFrameHint(BaseModel):
    """Reserved field shape for the v1.5 calibration-example surfacing (UBU-D0200).

    Present in the frozen schema so v1.5 is a render-and-select change, not a
    schema change. Not populated in v1.
    """

    frame_id: str
    dimension_tags: list[str] = Field(default_factory=list)
    text: str = ""


class ExplanationFragment(BaseModel):
    text: str
    calibration_frame_hint: Optional[CalibrationFrameHint] = None  # reserved v1.5


class PlanCandidate(BaseModel):
    candidate_id: str
    rank: int
    candidate_role: CandidateRole = CandidateRole.highest_utility
    schedule: list[ScheduledPlacement] = Field(default_factory=list)
    score_summary: ScoreSummary = Field(default_factory=ScoreSummary)
    feasibility_summary: FeasibilitySummary = Field(default_factory=FeasibilitySummary)
    semi_legitimization_summary: Optional[SemiLegitimizationSummary] = None
    probability_summary: ProbabilitySummary = Field(default_factory=ProbabilitySummary)
    explanation_fragments: list[ExplanationFragment] = Field(default_factory=list)
    validation_hints: Optional[dict] = None  # not certification


# ---------------------------------------------------------------------------
# Skeleton failure diagnostics (schema present in v1; rendered in v1.5)
# ---------------------------------------------------------------------------


class MissingOrConflictingState(BaseModel):
    target: str
    predicate: str
    expected: Optional[str] = None
    observed: Optional[str] = None
    state_status: Literal[
        "missing", "known_false", "conflicting", "unresolved", "denied_by_policy"
    ]


class SafeAlternative(BaseModel):
    action: Literal[
        "provide_starting_state",
        "mark_state_already_satisfied",
        "add_prerequisite_task",
        "relax_deadline",
        "extend_planning_horizon",
        "remove_or_moot_task",
        "choose_alternate_technique_or_task_path",
        "wait_for_external_event",
        "manual_decision",
    ]
    label: str
    requires_user_input: bool
    resulting_change_summary: str


class SkeletonFailureDiagnostic(BaseModel):
    diagnostic_id: str
    severity: SkeletonSeverity
    failure_class: SkeletonFailureClass
    primary_task_ref: Optional[str] = None
    affected_task_refs: list[str] = Field(default_factory=list)
    missing_or_conflicting_state: Optional[MissingOrConflictingState] = None
    causal_chain: list[dict] = Field(default_factory=list)
    safe_alternatives: list[SafeAlternative] = Field(default_factory=list)
    prompt_policy: Literal["immediate_blocking_prompt", "planning_warning"]
    user_facing_summary: str


class Diagnostics(BaseModel):
    candidate_counts_by_stage: dict[str, int] = Field(default_factory=dict)
    n_skeleton_candidates: int = 0
    n_after_affect_filter: int = 0
    n_after_value_scoring: int = 0
    n_finalists_rollout: int = 0
    rejection_counts_by_reason: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    skeleton_failure_diagnostics: list[SkeletonFailureDiagnostic] = Field(
        default_factory=list
    )
    probability_quality: ProbabilityQuality = ProbabilityQuality.not_estimated
    # Coverage fields: null in Phase 0 (no coverage estimation).
    coverage_scope: Optional[str] = None
    coverage_estimate: Optional[float] = None
    uncovered_mass_estimate: Optional[float] = None
    coverage_threshold_used: Optional[float] = None
    coverage_below_threshold: Optional[bool] = None
    compute_telemetry: Optional[dict] = None


# ---------------------------------------------------------------------------
# PlanningResponse
# ---------------------------------------------------------------------------


class PlanningResponse(BaseModel):
    schema_version: str = PHASE1_SCHEMA_VERSION
    profile: str = PHASE0_PROFILE
    planner_version: str
    request_id: str
    rng_seed_echo: int
    generated_at: str
    status: PlanningStatus = PlanningStatus.ok
    plan_candidates: list[PlanCandidate] = Field(default_factory=list)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
