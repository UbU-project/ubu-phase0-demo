"""PHASE0-T008: smoke tests for the refresh command.

Covers:
- refresh --offline exits 0
- Output contains the refreshed indicator
- Output contains the same key sections as demo
- refresh (live mode) without token exits non-zero
"""

from __future__ import annotations

from typer.testing import CliRunner

from ubu_phase0.cli import app

runner = CliRunner()


def _refresh_offline(extra_args: list[str] | None = None) -> object:
    args = ["refresh", "--offline"] + (extra_args or [])
    return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# Exit code
# ---------------------------------------------------------------------------


def test_refresh_offline_exits_zero():
    result = _refresh_offline()
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Refresh indicator
# ---------------------------------------------------------------------------


def test_refresh_output_contains_refreshed_indicator():
    result = _refresh_offline()
    assert "refreshed" in result.output


# ---------------------------------------------------------------------------
# Full demo sections also present after refresh
# ---------------------------------------------------------------------------


def test_refresh_output_contains_title():
    result = _refresh_offline()
    assert "UbU Phase 0 Demo" in result.output


def test_refresh_output_contains_calendar_preview():
    result = _refresh_offline()
    assert "Calendar Preview" in result.output


def test_refresh_output_contains_claim_register():
    result = _refresh_offline()
    assert "Claim Register" in result.output


def test_refresh_output_contains_not_estimated():
    result = _refresh_offline()
    assert "not_estimated" in result.output


def test_refresh_output_contains_task_title():
    result = _refresh_offline()
    assert "Write Phase 0 contract profile" in result.output


def test_refresh_output_shows_offline_source():
    result = _refresh_offline()
    assert "offline" in result.output


# ---------------------------------------------------------------------------
# Live mode without token → non-zero exit
# ---------------------------------------------------------------------------


def test_refresh_live_no_token_exits_nonzero(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = runner.invoke(app, ["refresh"])
    assert result.exit_code != 0
