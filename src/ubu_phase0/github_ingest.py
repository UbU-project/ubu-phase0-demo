"""GitHub issue ingestion for UbU Phase 0.

Converts GitHub issues (from live API or static fixture) into TaskSpec objects.
May import schema and PyGithub only (PyGithub is optional; live mode only).
No planning, no affect-gate execution, no GitHub mutation.
"""

from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Any

from ubu_phase0.schema import (
    AuthoritySource,
    DependencyEdge,
    FixedDuration,
    Priority,
    TaskGraph,
    TaskSpec,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Label family prefixes
# ---------------------------------------------------------------------------

_DURATION_PREFIX = "ubu:duration:"
_PRIORITY_PREFIX = "ubu:priority:"
_ENERGY_PREFIX = "ubu:energy:"
_STRESS_PREFIX = "ubu:stress:"
_MOOD_PREFIX = "ubu:mood:"
_DEPENDS_ON_PREFIX = "ubu:depends-on:#"

_KNOWN_PREFIXES = (
    _DURATION_PREFIX,
    _PRIORITY_PREFIX,
    _ENERGY_PREFIX,
    _STRESS_PREFIX,
    _MOOD_PREFIX,
    _DEPENDS_ON_PREFIX,
)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

_DURATION_MAP: dict[str, int] = {
    "15m": 900,
    "30m": 1800,
    "60m": 3600,
    "90m": 5400,
}

_PRIORITY_MAP: dict[str, Priority] = {
    "low": Priority.low,
    "medium": Priority.medium,
    "high": Priority.high,
}

_ENERGY_MAP: dict[str, float] = {
    "low-ok": 2.0,
    "medium": 5.0,
    "high": 8.0,
}

_STRESS_MAP: dict[str, float] = {
    "low": 2.0,
    "medium": 5.0,
    "high-risk": 8.0,
}

_MOOD_MAP: dict[str, float] = {
    "calm": 2.0,
    "engaged": 5.0,
    "intense-risk": 8.0,
}

# Safe defaults
_DEFAULT_DURATION_SECONDS = 1800
_DEFAULT_PRIORITY = Priority.medium
_DEFAULT_ENERGY = 5.0
_DEFAULT_STRESS = 5.0
_DEFAULT_MOOD = 5.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_task_id(owner: str, repo: str, number: int) -> str:
    return f"github:{owner}/{repo}#{number}"


def _resolve_family(
    labels: list[str],
    prefix: str,
    mapping: dict[str, Any],
    field: str,
) -> tuple[Any, list[str]]:
    """Return (resolved_value_or_None, unknown_labels) for one label family.

    On conflict (multiple labels in the same family), picks first alphabetically
    and emits a UserWarning. Unknown suffixes yield None and the label preserved.
    """
    matching = [lbl for lbl in labels if lbl.startswith(prefix)]
    if not matching:
        return None, []

    matching_sorted = sorted(matching)
    if len(matching_sorted) > 1:
        warnings.warn(
            f"Multiple {field} labels {matching_sorted!r}; using {matching_sorted[0]!r}",
            UserWarning,
            stacklevel=2,
        )

    chosen = matching_sorted[0]
    suffix = chosen[len(prefix):]
    if suffix in mapping:
        return mapping[suffix], []
    # Unknown variant: preserve as raw label
    return None, [chosen]


def _parse_labels(
    labels: list[str],
    owner: str,
    repo: str,
    number: int,
) -> tuple[FixedDuration, Priority, dict[str, float], list[str], list[str]]:
    """Parse issue labels into (duration, priority, affect_requirement, dep_ids, raw_labels).

    dep_ids are fully qualified task IDs derived from ubu:depends-on:#N labels.
    raw_labels collects anything not matched by a known family.
    """
    raw_labels: list[str] = []

    # Collect labels that match no known prefix at all
    for lbl in labels:
        if not any(lbl.startswith(p) for p in _KNOWN_PREFIXES):
            raw_labels.append(lbl)

    # Duration
    dur_secs, unknown = _resolve_family(labels, _DURATION_PREFIX, _DURATION_MAP, "duration")
    raw_labels.extend(unknown)
    duration = FixedDuration(seconds=dur_secs if dur_secs is not None else _DEFAULT_DURATION_SECONDS)

    # Priority
    pri_val, unknown = _resolve_family(labels, _PRIORITY_PREFIX, _PRIORITY_MAP, "priority")
    raw_labels.extend(unknown)
    priority: Priority = pri_val if pri_val is not None else _DEFAULT_PRIORITY

    # Energy
    energy_val, unknown = _resolve_family(labels, _ENERGY_PREFIX, _ENERGY_MAP, "energy")
    raw_labels.extend(unknown)

    # Stress
    stress_val, unknown = _resolve_family(labels, _STRESS_PREFIX, _STRESS_MAP, "stress")
    raw_labels.extend(unknown)

    # Mood
    mood_val, unknown = _resolve_family(labels, _MOOD_PREFIX, _MOOD_MAP, "mood")
    raw_labels.extend(unknown)

    affect_requirement: dict[str, float] = {
        "energy": energy_val if energy_val is not None else _DEFAULT_ENERGY,
        "stress": stress_val if stress_val is not None else _DEFAULT_STRESS,
        "mood_intensity": mood_val if mood_val is not None else _DEFAULT_MOOD,
    }

    # Dependency edges from ubu:depends-on:#N labels
    dep_ids: list[str] = []
    for lbl in labels:
        if lbl.startswith(_DEPENDS_ON_PREFIX):
            ref_num_str = lbl[len(_DEPENDS_ON_PREFIX):]
            try:
                dep_ids.append(_make_task_id(owner, repo, int(ref_num_str)))
            except ValueError:
                logger.warning("Malformed depends-on label %r on issue %d; skipping", lbl, number)

    return duration, priority, affect_requirement, dep_ids, raw_labels


def _issue_dict_to_task_spec(
    issue: dict[str, Any],
    owner: str,
    repo: str,
    authority_source: AuthoritySource,
) -> TaskSpec:
    number: int = issue["number"]
    task_id = _make_task_id(owner, repo, number)
    labels: list[str] = issue.get("labels", [])

    duration, priority, affect_requirement, dep_ids, raw_labels = _parse_labels(
        labels, owner, repo, number
    )

    return TaskSpec(
        id=task_id,
        title=issue["title"],
        description=issue.get("body") or "",
        source="github_issue",
        source_ref=task_id,
        external_id=str(number),
        external_url=issue["html_url"],
        authority_source=authority_source,
        duration=duration,
        priority=priority,
        affect_requirement=affect_requirement,
        dependencies=dep_ids,
        raw_labels=raw_labels,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_fixture(fixture_path: Path) -> TaskGraph:
    """Load the static fixture JSON and return a TaskGraph (authority=imported_config).

    Pull-request items are excluded. Deduplication is by source_ref. Tasks are
    ordered deterministically by issue number. Dependency edges are taken from
    hardcoded_dependency_edges in the fixture (not from labels).
    """
    data: dict[str, Any] = json.loads(fixture_path.read_text())
    owner: str = data["source"]["owner"]
    repo: str = data["source"]["repo"]

    seen: dict[str, TaskSpec] = {}
    for issue in data["issues"]:
        if issue.get("pull_request"):
            continue
        task = _issue_dict_to_task_spec(issue, owner, repo, AuthoritySource.imported_config)
        if task.source_ref in seen:
            logger.warning("Duplicate source_ref %r in fixture; skipping", task.source_ref)
            continue
        seen[task.source_ref] = task

    tasks = sorted(seen.values(), key=lambda t: int(t.external_id))

    dep_edges = [
        DependencyEdge(
            before_task_id=e["before_task_id"],
            after_task_id=e["after_task_id"],
        )
        for e in data.get("hardcoded_dependency_edges", [])
    ]

    return TaskGraph(tasks=tasks, dependency_edges=dep_edges)


def ingest_live(
    token: str,
    owner: str = "UbU-dummy",
    repo: str = "ubu-design",
) -> TaskGraph:
    """Fetch open issues from GitHub and return a TaskGraph (authority=github_event).

    Requires PyGithub. Pull-request items are excluded. Deduplication is by
    source_ref. Dependency edges are derived from ubu:depends-on:#N labels;
    targets absent from the imported set emit a warning and are dropped.
    """
    try:
        from github import Github  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "PyGithub is required for live mode. "
            "Install with: pip install -e '.[github]'"
        ) from exc

    g = Github(token)
    gh_repo = g.get_repo(f"{owner}/{repo}")

    seen: dict[str, TaskSpec] = {}
    for issue in gh_repo.get_issues(state="open"):
        if issue.pull_request:
            continue
        labels = [lbl.name for lbl in issue.labels]
        issue_dict: dict[str, Any] = {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "state": issue.state,
            "html_url": issue.html_url,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "labels": labels,
            "pull_request": None,
        }
        task = _issue_dict_to_task_spec(issue_dict, owner, repo, AuthoritySource.github_event)
        if task.source_ref in seen:
            logger.warning("Duplicate source_ref %r from live API; skipping", task.source_ref)
            continue
        seen[task.source_ref] = task

    tasks = sorted(seen.values(), key=lambda t: int(t.external_id))
    all_ids = {t.id for t in tasks}

    dep_edges: list[DependencyEdge] = []
    for task in tasks:
        for dep_id in task.dependencies:
            if dep_id not in all_ids:
                logger.warning(
                    "Dependency %r for task %r not found in imported set; skipping",
                    dep_id,
                    task.id,
                )
                continue
            dep_edges.append(DependencyEdge(before_task_id=dep_id, after_task_id=task.id))

    return TaskGraph(tasks=tasks, dependency_edges=dep_edges)
