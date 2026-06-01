"""PHASE0-T007: dependency overlay acceptance tests.

Covers:
- Fixture hardcoded edges flow through loop into task_graph and planning_request
- validate_dependency_edges drops and warns on missing before/after task IDs
- Valid edges are preserved unchanged
- Loop drops bad edges and records warnings in LoopResult.warnings
"""

from __future__ import annotations

import json

from ubu_phase0.loop import run, validate_dependency_edges
from ubu_phase0.schema import (
    AuthoritySource,
    DependencyEdge,
    FixedDuration,
    TaskGraph,
    TaskSpec,
)

_OWNER = "UbU-dummy"
_REPO = "ubu-design"


def _task(number: int) -> TaskSpec:
    tid = f"github:{_OWNER}/{_REPO}#{number}"
    return TaskSpec(
        id=tid,
        title=f"Task {number}",
        source="github_issue",
        source_ref=tid,
        external_id=str(number),
        external_url=f"https://github.com/{_OWNER}/{_REPO}/issues/{number}",
        authority_source=AuthoritySource.imported_config,
        duration=FixedDuration(seconds=1800),
    )


# ---------------------------------------------------------------------------
# Fixture edges flow through
# ---------------------------------------------------------------------------


def test_fixture_edges_present_in_task_graph(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    edge_pairs = {
        (e.before_task_id, e.after_task_id) for e in result.task_graph.dependency_edges
    }
    assert ("github:UbU-dummy/ubu-design#8", "github:UbU-dummy/ubu-design#12") in edge_pairs


def test_fixture_edges_present_in_planning_request(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    edge_pairs = {
        (e.before_task_id, e.after_task_id)
        for e in result.planning_request.task_graph.dependency_edges
    }
    assert ("github:UbU-dummy/ubu-design#12", "github:UbU-dummy/ubu-design#15") in edge_pairs
    assert ("github:UbU-dummy/ubu-design#12", "github:UbU-dummy/ubu-design#19") in edge_pairs


def test_fixture_edge_count(monkeypatch):
    # static_dummy_issue.json has exactly 3 hardcoded_dependency_edges
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert len(result.task_graph.dependency_edges) == 3


# ---------------------------------------------------------------------------
# validate_dependency_edges — valid edges
# ---------------------------------------------------------------------------


def test_valid_edges_preserved():
    t1, t2 = _task(1), _task(2)
    edge = DependencyEdge(before_task_id=t1.id, after_task_id=t2.id)
    graph = TaskGraph(tasks=[t1, t2], dependency_edges=[edge])
    result_graph, warnings = validate_dependency_edges(graph)
    assert len(result_graph.dependency_edges) == 1
    assert result_graph.dependency_edges[0] == edge
    assert warnings == []


def test_empty_edges_no_warnings():
    graph = TaskGraph(tasks=[_task(1)], dependency_edges=[])
    result_graph, warnings = validate_dependency_edges(graph)
    assert result_graph.dependency_edges == []
    assert warnings == []


# ---------------------------------------------------------------------------
# validate_dependency_edges — missing targets
# ---------------------------------------------------------------------------


def test_missing_before_task_dropped_with_warning():
    t2 = _task(2)
    ghost_id = f"github:{_OWNER}/{_REPO}#99"
    edge = DependencyEdge(before_task_id=ghost_id, after_task_id=t2.id)
    graph = TaskGraph(tasks=[t2], dependency_edges=[edge])
    result_graph, warnings = validate_dependency_edges(graph)
    assert result_graph.dependency_edges == []
    assert len(warnings) == 1
    assert ghost_id in warnings[0]


def test_missing_after_task_dropped_with_warning():
    t1 = _task(1)
    ghost_id = f"github:{_OWNER}/{_REPO}#99"
    edge = DependencyEdge(before_task_id=t1.id, after_task_id=ghost_id)
    graph = TaskGraph(tasks=[t1], dependency_edges=[edge])
    result_graph, warnings = validate_dependency_edges(graph)
    assert result_graph.dependency_edges == []
    assert len(warnings) == 1
    assert ghost_id in warnings[0]


def test_mixed_valid_and_invalid_edges():
    t1, t2 = _task(1), _task(2)
    ghost_id = f"github:{_OWNER}/{_REPO}#99"
    valid_edge = DependencyEdge(before_task_id=t1.id, after_task_id=t2.id)
    bad_edge = DependencyEdge(before_task_id=ghost_id, after_task_id=t2.id)
    graph = TaskGraph(tasks=[t1, t2], dependency_edges=[valid_edge, bad_edge])
    result_graph, warnings = validate_dependency_edges(graph)
    assert result_graph.dependency_edges == [valid_edge]
    assert len(warnings) == 1


# ---------------------------------------------------------------------------
# Loop surfaces bad-edge warnings in LoopResult.warnings
# ---------------------------------------------------------------------------


def test_loop_drops_bad_edge_and_records_warning(monkeypatch, tmp_path):
    """Loop drops a hardcoded edge whose after-task does not exist."""
    fixture_data = {
        "source": {"owner": _OWNER, "repo": _REPO},
        "issues": [
            {
                "number": 1,
                "title": "T1",
                "body": "",
                "state": "open",
                "html_url": f"https://github.com/{_OWNER}/{_REPO}/issues/1",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "labels": [],
                "pull_request": None,
            }
        ],
        "hardcoded_dependency_edges": [
            {
                "before_task_id": f"github:{_OWNER}/{_REPO}#1",
                "after_task_id": f"github:{_OWNER}/{_REPO}#999",
            }
        ],
    }
    fp = tmp_path / "bad_fixture.json"
    fp.write_text(json.dumps(fixture_data))

    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True, fixture_path=fp)

    assert len(result.task_graph.dependency_edges) == 0
    assert any("999" in w for w in result.warnings)
