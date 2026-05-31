"""PHASE0-T001/T002 acceptance test: contract round-trip.

Asserts that the golden demo_request.json loads, validates as a PlanningRequest,
serializes back to JSON, and re-validates. The planner ticket (T005) extends
this file to assert the request is consumable by the planner and the response
validates.
"""

import json
from pathlib import Path

from ubu_phase0.schema import PlanningRequest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_demo_request_loads_and_validates():
    raw = (FIXTURES / "demo_request.json").read_text()
    req = PlanningRequest.model_validate_json(raw)
    assert req.profile == "planning-kernel-contract/phase0-profile/0.1"
    assert req.schema_version == "planning-kernel-contract/0.1"
    assert len(req.task_graph.tasks) == 5  # PR #27 excluded
    assert len(req.task_graph.dependency_edges) == 3


def test_demo_request_round_trips():
    raw = (FIXTURES / "demo_request.json").read_text()
    req = PlanningRequest.model_validate_json(raw)
    again = PlanningRequest.model_validate(json.loads(req.model_dump_json()))
    assert again.request_id == req.request_id
    assert [t.id for t in again.task_graph.tasks] == [
        t.id for t in req.task_graph.tasks
    ]


def test_no_pull_requests_in_task_graph():
    raw = (FIXTURES / "demo_request.json").read_text()
    req = PlanningRequest.model_validate_json(raw)
    assert all("#27" not in t.id for t in req.task_graph.tasks)


def test_authority_source_set_on_every_task():
    raw = (FIXTURES / "demo_request.json").read_text()
    req = PlanningRequest.model_validate_json(raw)
    assert all(t.authority_source is not None for t in req.task_graph.tasks)
