"""PHASE0-T007: offline mode and token-guard acceptance tests.

Covers:
- run(offline=True) succeeds without UBU_PHASE0_GITHUB_TOKEN
- run(offline=True) returns a valid LoopResult with fixture task count
- run(offline=False) without token raises LoopError (no auto-fallback)
- Claim register is returned as a structured ClaimRegister object
- Source label reflects the active mode
"""

from __future__ import annotations

import pytest

from ubu_phase0.loop import ClaimRegister, LoopError, LoopResult, run
from ubu_phase0.schema import PlanningStatus


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------


def test_offline_run_succeeds_without_token(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert isinstance(result, LoopResult)


def test_offline_run_mode_is_offline(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert result.mode == "offline"


def test_offline_run_source_label_contains_fixture(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert "fixture" in result.source_label


def test_offline_run_task_count_matches_fixture(monkeypatch):
    # Fixture has 6 entries; one carries pull_request metadata and must be excluded.
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert len(result.task_graph.tasks) == 5


def test_offline_run_planning_response_present(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert result.planning_response is not None


def test_offline_run_planning_status_ok_or_partial(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert result.planning_response.status in (PlanningStatus.ok, PlanningStatus.partial)


def test_offline_run_claim_register_is_structured_object(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert isinstance(result.claim_register, ClaimRegister)
    assert isinstance(result.claim_register.claims, list)
    assert len(result.claim_register.claims) > 0


def test_offline_run_claim_register_not_a_string(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert not isinstance(result.claim_register, str)


def test_offline_run_claim_register_profile(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert result.claim_register.profile == "planning-kernel-contract/phase0-profile/0.1"


def test_offline_run_claim_entries_have_required_fields(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    for entry in result.claim_register.claims:
        assert entry.id
        assert entry.claim
        assert entry.status
        assert isinstance(entry.modules, list)
        assert entry.test


def test_offline_run_affect_profile_uses_bootstrap_defaults(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = run(offline=True)
    assert result.affect_profile.preset_labels["energy"] == "medium"
    assert result.affect_profile.preset_labels["stress"] == "low"
    assert result.affect_profile.preset_labels["mood_intensity"] == "calm"


# ---------------------------------------------------------------------------
# Live mode without token → LoopError (no auto-fallback)
# ---------------------------------------------------------------------------


def test_live_mode_without_token_raises_loop_error(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    with pytest.raises(LoopError):
        run(offline=False)


def test_live_mode_without_token_error_mentions_env_var(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    with pytest.raises(LoopError, match="UBU_PHASE0_GITHUB_TOKEN"):
        run(offline=False)


def test_live_mode_without_token_no_silent_fallback(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    raised = False
    try:
        run(offline=False)
    except LoopError:
        raised = True
    assert raised, "Expected LoopError; got silent fallback to fixture instead"
