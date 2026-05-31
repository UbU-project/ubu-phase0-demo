"""PHASE0-T003: fixture -> TaskSpec conversion acceptance tests."""

from pathlib import Path

from ubu_phase0.github_ingest import ingest_fixture
from ubu_phase0.schema import AuthoritySource, Priority

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_fixture_produces_five_tasks():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    assert len(graph.tasks) == 5


def test_pull_request_excluded():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    assert all("#27" not in t.id for t in graph.tasks)


def test_authority_source_is_imported_config():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    for task in graph.tasks:
        assert task.authority_source is AuthoritySource.imported_config


def test_task_ids_use_correct_format():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    for task in graph.tasks:
        assert task.id.startswith("github:UbU-dummy/ubu-design#")
        assert task.source_ref == task.id


def test_source_field_is_github_issue():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    for task in graph.tasks:
        assert task.source == "github_issue"


def test_dependency_edges_match_fixture():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    edge_pairs = {(e.before_task_id, e.after_task_id) for e in graph.dependency_edges}
    assert ("github:UbU-dummy/ubu-design#8", "github:UbU-dummy/ubu-design#12") in edge_pairs
    assert ("github:UbU-dummy/ubu-design#12", "github:UbU-dummy/ubu-design#15") in edge_pairs
    assert ("github:UbU-dummy/ubu-design#12", "github:UbU-dummy/ubu-design#19") in edge_pairs
    assert len(graph.dependency_edges) == 3


def test_task_ordering_is_by_issue_number():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    numbers = [int(t.external_id) for t in graph.tasks]
    assert numbers == sorted(numbers)


def test_issue_8_label_mapping():
    """Issue 8: 30m, high priority, medium energy, low stress, calm mood."""
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    task = next(t for t in graph.tasks if t.external_id == "8")
    assert task.duration.seconds == 1800
    assert task.priority is Priority.high
    assert task.affect_requirement["energy"] == 5.0
    assert task.affect_requirement["stress"] == 2.0
    assert task.affect_requirement["mood_intensity"] == 2.0


def test_issue_15_duration_60m():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    task = next(t for t in graph.tasks if t.external_id == "15")
    assert task.duration.seconds == 3600


def test_issue_19_label_mapping():
    """Issue 19: 90m, high energy, high-risk stress, intense mood."""
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    task = next(t for t in graph.tasks if t.external_id == "19")
    assert task.duration.seconds == 5400
    assert task.affect_requirement["energy"] == 8.0
    assert task.affect_requirement["stress"] == 8.0
    assert task.affect_requirement["mood_intensity"] == 8.0


def test_issue_23_label_mapping():
    """Issue 23: 15m, low priority, low-ok energy."""
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    task = next(t for t in graph.tasks if t.external_id == "23")
    assert task.duration.seconds == 900
    assert task.priority is Priority.low
    assert task.affect_requirement["energy"] == 2.0


def test_external_url_set_on_all_tasks():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    for task in graph.tasks:
        assert task.external_url.startswith("https://github.com/")


def test_external_id_matches_issue_number():
    graph = ingest_fixture(FIXTURES / "static_dummy_issue.json")
    for task in graph.tasks:
        assert task.id.endswith(f"#{task.external_id}")
