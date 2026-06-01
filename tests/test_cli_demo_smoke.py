"""PHASE0-T008: smoke tests for the demo command.

Covers:
- demo --offline exits 0
- Output contains all required sections: header, tasks, affect profile,
  planning window, calendar preview, claim register summary, footer
- Calendar rows contain task titles and source
- Affect margin indicator present in output
- Footer shows probability_quality: not_estimated and coverage_estimate: —
- demo (live mode) without token exits non-zero (no fallback)
"""

from __future__ import annotations

from typer.testing import CliRunner

from ubu_phase0.cli import app

runner = CliRunner()


def _offline(extra_args: list[str] | None = None) -> object:
    args = ["demo", "--offline"] + (extra_args or [])
    return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# Exit code
# ---------------------------------------------------------------------------


def test_demo_offline_exits_zero():
    result = _offline()
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Header section
# ---------------------------------------------------------------------------


def test_demo_output_contains_title():
    result = _offline()
    assert "UbU Phase 0 Demo" in result.output


def test_demo_output_contains_data_source():
    result = _offline()
    assert "Data source" in result.output


def test_demo_output_shows_offline_mode():
    result = _offline()
    assert "offline" in result.output


def test_demo_output_shows_fixture_source():
    result = _offline()
    assert "fixture" in result.output


# ---------------------------------------------------------------------------
# Imported tasks section
# ---------------------------------------------------------------------------


def test_demo_output_contains_imported_tasks_header():
    result = _offline()
    assert "Imported Tasks" in result.output


def test_demo_output_contains_fixture_task_title():
    result = _offline()
    assert "Write Phase 0 contract profile" in result.output


def test_demo_output_contains_authority_source():
    result = _offline()
    assert "imported_config" in result.output


def test_demo_output_contains_source_ref():
    result = _offline()
    assert "github:UbU-dummy/ubu-design#8" in result.output


# ---------------------------------------------------------------------------
# Affect profile section
# ---------------------------------------------------------------------------


def test_demo_output_contains_affect_profile_header():
    result = _offline()
    assert "Affect Profile" in result.output


def test_demo_output_contains_energy_preset():
    result = _offline()
    assert "medium" in result.output


def test_demo_output_contains_stress_preset():
    result = _offline()
    assert "low" in result.output


# ---------------------------------------------------------------------------
# Planning window section
# ---------------------------------------------------------------------------


def test_demo_output_contains_planning_window_header():
    result = _offline()
    assert "Planning Window" in result.output


# ---------------------------------------------------------------------------
# Calendar preview section
# ---------------------------------------------------------------------------


def test_demo_output_contains_calendar_preview_header():
    result = _offline()
    assert "Calendar Preview" in result.output


def test_demo_calendar_contains_time_column():
    result = _offline()
    # Time format is HH:MM–HH:MM
    assert "–" in result.output or "-" in result.output


def test_demo_calendar_contains_scheduled_task():
    # Task 8 has no dependencies and passes the affect gate — must appear
    result = _offline()
    assert "Write Phase 0 contract profile" in result.output


def test_demo_calendar_contains_affect_indicator():
    result = _offline()
    # At least one of the three margin symbols should appear
    has_indicator = any(sym in result.output for sym in ("▆▆▆", "▃▃▃", "░░░"))
    assert has_indicator, f"No affect margin indicator found in output:\n{result.output}"


# ---------------------------------------------------------------------------
# Claim register summary section
# ---------------------------------------------------------------------------


def test_demo_output_contains_claim_register_header():
    result = _offline()
    assert "Claim Register" in result.output


def test_demo_output_contains_claim_status():
    result = _offline()
    # At least "implemented" or "deferred" should appear
    has_status = "implemented" in result.output or "deferred" in result.output
    assert has_status, result.output


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------


def test_demo_footer_contains_probability_quality():
    result = _offline()
    assert "not_estimated" in result.output


def test_demo_footer_contains_coverage_estimate_placeholder():
    result = _offline()
    assert "coverage_estimate" in result.output
    assert "—" in result.output


def test_demo_footer_mentions_phase1():
    result = _offline()
    assert "Phase 1" in result.output


# ---------------------------------------------------------------------------
# Live mode without token → non-zero exit (no fallback)
# ---------------------------------------------------------------------------


def test_demo_live_no_token_exits_nonzero(monkeypatch):
    monkeypatch.delenv("UBU_PHASE0_GITHUB_TOKEN", raising=False)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code != 0
