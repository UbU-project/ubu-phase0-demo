"""PHASE0-T003: deduplication and ordering acceptance tests."""

import json
from pathlib import Path
from typing import Any

from ubu_phase0.github_ingest import ingest_fixture

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _make_issue(number: int, pull_request: Any = None) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": "",
        "state": "open",
        "html_url": f"https://github.com/UbU-dummy/ubu-design/issues/{number}",
        "created_at": "2026-05-28T13:00:00Z",
        "updated_at": "2026-05-28T13:00:00Z",
        "labels": [],
        "pull_request": pull_request,
    }


def _write_fixture(tmp_path: Path, issues: list[dict[str, Any]]) -> Path:
    fixture: dict[str, Any] = {
        "source": {"owner": "UbU-dummy", "repo": "ubu-design"},
        "issues": issues,
        "hardcoded_dependency_edges": [],
    }
    p = tmp_path / "fixture.json"
    p.write_text(json.dumps(fixture))
    return p


# ---------------------------------------------------------------------------
# Baseline: canonical fixture has no duplicates
# ---------------------------------------------------------------------------


def test_canonical_fixture_has_no_duplicate_source_refs():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    refs = [t.source_ref for t in graph.tasks]
    assert len(refs) == len(set(refs))


# ---------------------------------------------------------------------------
# Deduplication by source_ref
# ---------------------------------------------------------------------------


def test_duplicate_issue_number_deduplicated(tmp_path: Path):
    p = _write_fixture(tmp_path, [_make_issue(1), _make_issue(1), _make_issue(2)])
    graph = ingest_fixture(p)
    assert len(graph.tasks) == 2
    refs = [t.source_ref for t in graph.tasks]
    assert len(refs) == len(set(refs))


def test_duplicate_keeps_first_occurrence(tmp_path: Path):
    issue_a = _make_issue(1)
    issue_a["title"] = "First"
    issue_b = _make_issue(1)
    issue_b["title"] = "Second"
    p = _write_fixture(tmp_path, [issue_a, issue_b])
    graph = ingest_fixture(p)
    assert len(graph.tasks) == 1
    assert graph.tasks[0].title == "First"


# ---------------------------------------------------------------------------
# Deterministic ordering by issue number
# ---------------------------------------------------------------------------


def test_tasks_ordered_by_issue_number_ascending(tmp_path: Path):
    p = _write_fixture(tmp_path, [_make_issue(5), _make_issue(2), _make_issue(8), _make_issue(1)])
    graph = ingest_fixture(p)
    numbers = [int(t.external_id) for t in graph.tasks]
    assert numbers == sorted(numbers)


def test_ordering_independent_of_input_order(tmp_path: Path):
    issues_fwd = [_make_issue(1), _make_issue(3), _make_issue(2)]
    issues_rev = [_make_issue(2), _make_issue(3), _make_issue(1)]
    p1 = tmp_path / "fwd.json"
    p2 = tmp_path / "rev.json"
    p1.write_text(json.dumps({"source": {"owner": "UbU-dummy", "repo": "ubu-design"}, "issues": issues_fwd, "hardcoded_dependency_edges": []}))
    p2.write_text(json.dumps({"source": {"owner": "UbU-dummy", "repo": "ubu-design"}, "issues": issues_rev, "hardcoded_dependency_edges": []}))

    g1 = ingest_fixture(p1)
    g2 = ingest_fixture(p2)
    assert [t.external_id for t in g1.tasks] == [t.external_id for t in g2.tasks]


def test_two_calls_produce_same_order(tmp_path: Path):
    p = _write_fixture(tmp_path, [_make_issue(3), _make_issue(1), _make_issue(2)])
    g1 = ingest_fixture(p)
    g2 = ingest_fixture(p)
    assert [t.id for t in g1.tasks] == [t.id for t in g2.tasks]


# ---------------------------------------------------------------------------
# PR exclusion interacts correctly with dedup
# ---------------------------------------------------------------------------


def test_pr_excluded_before_dedup(tmp_path: Path):
    pr_item = _make_issue(2, pull_request={"url": "https://api.github.com/repos/UbU-dummy/ubu-design/pulls/2"})
    p = _write_fixture(tmp_path, [_make_issue(1), pr_item])
    graph = ingest_fixture(p)
    assert len(graph.tasks) == 1
    assert graph.tasks[0].external_id == "1"


def test_all_prs_excluded_yields_empty_task_list(tmp_path: Path):
    pr = {"url": "https://api.github.com/repos/UbU-dummy/ubu-design/pulls/1"}
    p = _write_fixture(tmp_path, [_make_issue(1, pull_request=pr)])
    graph = ingest_fixture(p)
    assert graph.tasks == []
