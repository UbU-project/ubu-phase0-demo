"""PHASE0-T003: label mapping rules acceptance tests."""

import warnings

from ubu_phase0.github_ingest import _make_task_id, _parse_labels
from ubu_phase0.schema import FixedDuration, Priority

OWNER = "UbU-dummy"
REPO = "ubu-design"


def _parse(labels: list[str], number: int = 1) -> tuple[FixedDuration, Priority, dict[str, float], list[str], list[str]]:
    return _parse_labels(labels, OWNER, REPO, number)


# ---------------------------------------------------------------------------
# Duration
# ---------------------------------------------------------------------------


def test_duration_15m():
    duration, *_ = _parse(["ubu:duration:15m"])
    assert duration.seconds == 900


def test_duration_30m():
    duration, *_ = _parse(["ubu:duration:30m"])
    assert duration.seconds == 1800


def test_duration_60m():
    duration, *_ = _parse(["ubu:duration:60m"])
    assert duration.seconds == 3600


def test_duration_90m():
    duration, *_ = _parse(["ubu:duration:90m"])
    assert duration.seconds == 5400


def test_duration_default_when_no_label():
    duration, *_ = _parse([])
    assert duration.seconds == 1800


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


def test_priority_low():
    _, priority, *_ = _parse(["ubu:priority:low"])
    assert priority is Priority.low


def test_priority_medium():
    _, priority, *_ = _parse(["ubu:priority:medium"])
    assert priority is Priority.medium


def test_priority_high():
    _, priority, *_ = _parse(["ubu:priority:high"])
    assert priority is Priority.high


def test_priority_default_when_no_label():
    _, priority, *_ = _parse([])
    assert priority is Priority.medium


# ---------------------------------------------------------------------------
# Affect dimensions
# ---------------------------------------------------------------------------


def test_energy_low_ok():
    _, _, affect, *_ = _parse(["ubu:energy:low-ok"])
    assert affect["energy"] == 2.0


def test_energy_medium():
    _, _, affect, *_ = _parse(["ubu:energy:medium"])
    assert affect["energy"] == 5.0


def test_energy_high():
    _, _, affect, *_ = _parse(["ubu:energy:high"])
    assert affect["energy"] == 8.0


def test_stress_low():
    _, _, affect, *_ = _parse(["ubu:stress:low"])
    assert affect["stress"] == 2.0


def test_stress_medium():
    _, _, affect, *_ = _parse(["ubu:stress:medium"])
    assert affect["stress"] == 5.0


def test_stress_high_risk():
    _, _, affect, *_ = _parse(["ubu:stress:high-risk"])
    assert affect["stress"] == 8.0


def test_mood_calm():
    _, _, affect, *_ = _parse(["ubu:mood:calm"])
    assert affect["mood_intensity"] == 2.0


def test_mood_engaged():
    _, _, affect, *_ = _parse(["ubu:mood:engaged"])
    assert affect["mood_intensity"] == 5.0


def test_mood_intense_risk():
    _, _, affect, *_ = _parse(["ubu:mood:intense-risk"])
    assert affect["mood_intensity"] == 8.0


def test_affect_defaults_when_no_labels():
    _, _, affect, *_ = _parse([])
    assert affect["energy"] == 5.0
    assert affect["stress"] == 5.0
    assert affect["mood_intensity"] == 5.0


# ---------------------------------------------------------------------------
# Depends-on labels
# ---------------------------------------------------------------------------


def test_depends_on_label_produces_dep_id():
    _, _, _, deps, _ = _parse(["ubu:depends-on:#8"])
    assert deps == [_make_task_id(OWNER, REPO, 8)]


def test_multiple_depends_on_labels():
    _, _, _, deps, _ = _parse(["ubu:depends-on:#8", "ubu:depends-on:#12"])
    assert _make_task_id(OWNER, REPO, 8) in deps
    assert _make_task_id(OWNER, REPO, 12) in deps
    assert len(deps) == 2


# ---------------------------------------------------------------------------
# Unknown labels
# ---------------------------------------------------------------------------


def test_unknown_label_preserved_in_raw():
    *_, raw = _parse(["some-random-label"])
    assert "some-random-label" in raw


def test_unknown_label_does_not_affect_defaults():
    duration, priority, affect, deps, _ = _parse(["completely:unknown:label"])
    assert duration.seconds == 1800
    assert priority is Priority.medium
    assert affect["energy"] == 5.0
    assert deps == []


def test_unknown_ubu_variant_in_raw():
    *_, raw = _parse(["ubu:duration:2h"])
    assert "ubu:duration:2h" in raw


# ---------------------------------------------------------------------------
# Conflict: duplicate same-family labels — first alphabetical wins, warn
# ---------------------------------------------------------------------------


def test_duplicate_duration_first_alpha_wins_with_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        duration, *_ = _parse(["ubu:duration:60m", "ubu:duration:30m"])
        # "ubu:duration:30m" < "ubu:duration:60m" alphabetically → 30m = 1800s
        assert duration.seconds == 1800
        assert len(w) == 1
        assert "duration" in str(w[0].message).lower()


def test_duplicate_priority_first_alpha_wins_with_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _, priority, *_ = _parse(["ubu:priority:high", "ubu:priority:low"])
        # "ubu:priority:high" < "ubu:priority:low" alphabetically → high wins
        assert priority is Priority.high
        assert len(w) == 1
        assert "priority" in str(w[0].message).lower()


def test_no_warning_for_single_family_label():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _parse(["ubu:duration:30m", "ubu:priority:high"])
        assert len(w) == 0


# ---------------------------------------------------------------------------
# make_task_id helper
# ---------------------------------------------------------------------------


def test_make_task_id_format():
    tid = _make_task_id("UbU-dummy", "ubu-design", 42)
    assert tid == "github:UbU-dummy/ubu-design#42"
