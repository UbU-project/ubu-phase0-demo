"""UbU Phase 0 loop (orchestration).

Orchestrates: mode selection, github_ingest calls, dependency-overlay
validation, PlanningRequest construction, planner dispatch, claim-register
loading and validation, display-ready result assembly.

May import: schema, affect, planner, bootstrap, github_ingest; stdlib.
Forbidden: cli, Rich/Typer formatting; GitHub mutation; persistent cache;
auto-fallback from live to fixture.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ubu_phase0 import github_ingest as _github_ingest
from ubu_phase0 import planner as _planner
from ubu_phase0.bootstrap import default_affect_profile
from ubu_phase0.schema import (
    AffectProfile,
    DependencyEdge,
    LogEntry,
    PlanningRequest,
    PlanningResponse,
    TaskGraph,
    TimeWindow,
    UniverseStateSnapshot,
)

logger = logging.getLogger(__name__)

_PLANNER_VERSION = "ubu-phase0/0.1.0"

_REPO_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_FIXTURE_PATH = _REPO_ROOT / "fixtures" / "static_dummy_issue.json"
_DEFAULT_CLAIM_REGISTER_PATH = _REPO_ROOT / "fixtures" / "claim_register.json"

_ENV_TOKEN = "UBU_PHASE0_GITHUB_TOKEN"
_ENV_OWNER = "UBU_PHASE0_GITHUB_OWNER"
_ENV_REPO = "UBU_PHASE0_GITHUB_REPO"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LoopError(RuntimeError):
    """Hard failure in loop.run(); no fallback. CLI exits non-zero."""


# ---------------------------------------------------------------------------
# Claim-register data objects (structured, not raw string/dict)
# ---------------------------------------------------------------------------


@dataclass
class ClaimEntry:
    id: str
    claim: str
    status: str
    modules: list[str]
    test: str


@dataclass
class ClaimRegister:
    profile: str
    claims: list[ClaimEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Display-ready result
# ---------------------------------------------------------------------------


@dataclass
class LoopResult:
    mode: str  # "live" or "offline"
    source_label: str  # human-readable source description for CLI header
    task_graph: TaskGraph
    planning_request: PlanningRequest
    planning_response: PlanningResponse
    affect_profile: AffectProfile
    claim_register: ClaimRegister
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dependency-overlay validation
# ---------------------------------------------------------------------------


def validate_dependency_edges(
    task_graph: TaskGraph,
) -> tuple[TaskGraph, list[str]]:
    """Drop edges whose before/after task ID is absent from the task set.

    Returns (validated_graph, warning_strings). Missing-target edges are
    logged and collected; the loop surfaces them in LoopResult.warnings.
    """
    task_ids = {t.id for t in task_graph.tasks}
    valid_edges: list[DependencyEdge] = []
    warnings: list[str] = []

    for edge in task_graph.dependency_edges:
        missing = [
            ref
            for ref in (edge.before_task_id, edge.after_task_id)
            if ref not in task_ids
        ]
        if missing:
            msg = (
                f"Dependency edge ({edge.before_task_id!r} -> {edge.after_task_id!r}) "
                f"references unknown task(s) {missing!r}; treating as absent."
            )
            logger.warning(msg)
            warnings.append(msg)
        else:
            valid_edges.append(edge)

    return (
        TaskGraph(
            tasks=task_graph.tasks,
            dependency_edges=valid_edges,
            topological_order=task_graph.topological_order,
        ),
        warnings,
    )


# ---------------------------------------------------------------------------
# Claim-register loader
# ---------------------------------------------------------------------------


def _load_claim_register(path: Path) -> ClaimRegister:
    data: dict = json.loads(path.read_text())
    claims = [
        ClaimEntry(
            id=c["id"],
            claim=c["claim"],
            status=c["status"],
            modules=c["modules"],
            test=c["test"],
        )
        for c in data.get("claims", [])
    ]
    return ClaimRegister(profile=data["profile"], claims=claims)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run(
    offline: bool = False,
    logs: list[LogEntry] | None = None,
    affect_profile: AffectProfile | None = None,
    fixture_path: Path | None = None,
    claim_register_path: Path | None = None,
) -> LoopResult:
    """Run one full plan cycle and return a display-ready LoopResult.

    Hard switch: offline=True reads the fixture; offline=False (default) fetches
    live GitHub issues. There is NO auto-fallback. Live-mode failures raise
    LoopError so the CLI can exit non-zero with a clean message.
    """
    if logs is None:
        logs = []

    loop_warnings: list[str] = []

    # ---- Source selection (hard switch, no fallback) ----------------------
    if offline:
        fp = fixture_path or _DEFAULT_FIXTURE_PATH
        task_graph = _github_ingest.ingest_fixture(fp)
        mode = "offline"
        source_label = f"fixture:{fp.name}"
    else:
        token = os.environ.get(_ENV_TOKEN, "").strip()
        if not token:
            raise LoopError(
                f"Live mode requires {_ENV_TOKEN} to be set. "
                "Run with --offline to use the fixture instead."
            )
        owner = os.environ.get(_ENV_OWNER, "UbU-dummy")
        repo = os.environ.get(_ENV_REPO, "ubu-design")
        try:
            task_graph = _github_ingest.ingest_live(token=token, owner=owner, repo=repo)
        except Exception as exc:
            raise LoopError(
                f"GitHub ingestion failed ({type(exc).__name__}: {exc}). "
                "Check token permissions and network, or use --offline."
            ) from exc
        mode = "live"
        source_label = f"github:{owner}/{repo}"

    # ---- Dependency-overlay validation ------------------------------------
    task_graph, edge_warnings = validate_dependency_edges(task_graph)
    loop_warnings.extend(edge_warnings)

    # ---- Affect profile ---------------------------------------------------
    profile = affect_profile or default_affect_profile()

    # ---- Build PlanningRequest --------------------------------------------
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=4)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    window_end_str = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    request = PlanningRequest(
        planner_version=_PLANNER_VERSION,
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        effective_time=now_str,
        generated_at=now_str,
        rng_seed=int(now.timestamp()),
        time_window=TimeWindow(
            start_time=now_str,
            end_time=window_end_str,
        ),
        task_graph=task_graph,
        universe_state_snapshot=UniverseStateSnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            snapshot_effective_time=now_str,
        ),
        affect_profile=profile,
    )

    # ---- Plan -------------------------------------------------------------
    response = _planner.planner(request, logs)

    # ---- Load claim register (structured object) --------------------------
    cr_path = claim_register_path or _DEFAULT_CLAIM_REGISTER_PATH
    claim_register = _load_claim_register(cr_path)

    return LoopResult(
        mode=mode,
        source_label=source_label,
        task_graph=task_graph,
        planning_request=request,
        planning_response=response,
        affect_profile=profile,
        claim_register=claim_register,
        warnings=loop_warnings,
    )
