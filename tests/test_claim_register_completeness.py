"""PHASE0-T009: Claim register completeness validation.

Rules enforced:
- profile field matches expected value
- All required v1 claims (CR-001..CR-008) are present
- Every claim has a valid status, non-empty modules list, and a test reference
- For status=implemented: the named test file exists and all its tests pass
- deferred/mocked/fixture_backed claims are exempt from the passing-test check
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "fixtures"
TESTS_DIR = REPO_ROOT / "tests"
CLAIM_REGISTER_PATH = FIXTURES / "claim_register.json"

VALID_STATUSES = {"implemented", "fixture_backed", "mocked", "deferred"}

REQUIRED_CLAIM_IDS = {
    "CR-001", "CR-002", "CR-003", "CR-004",
    "CR-005", "CR-006", "CR-007", "CR-008",
}


def _load_claims() -> list[dict]:
    return json.loads(CLAIM_REGISTER_PATH.read_text())["claims"]


def _load_register() -> dict:
    return json.loads(CLAIM_REGISTER_PATH.read_text())


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def test_claim_register_profile():
    data = _load_register()
    assert data["profile"] == "planning-kernel-contract/phase0-profile/0.1"


# ---------------------------------------------------------------------------
# Required claims present
# ---------------------------------------------------------------------------


def test_required_demo_claims_present():
    ids = {c["id"] for c in _load_claims()}
    missing = REQUIRED_CLAIM_IDS - ids
    assert not missing, f"Missing required claim IDs: {sorted(missing)}"


# ---------------------------------------------------------------------------
# Status validity
# ---------------------------------------------------------------------------


def test_all_claim_statuses_are_valid():
    for claim in _load_claims():
        assert claim["status"] in VALID_STATUSES, (
            f"{claim['id']}: invalid status {claim['status']!r}; "
            f"must be one of {sorted(VALID_STATUSES)}"
        )


# ---------------------------------------------------------------------------
# Every claim carries modules + test ref
# ---------------------------------------------------------------------------


def test_all_claims_have_non_empty_modules():
    for claim in _load_claims():
        assert claim.get("modules"), f"{claim['id']}: modules must be a non-empty list"


def test_all_claims_have_test_reference():
    for claim in _load_claims():
        assert claim.get("test"), f"{claim['id']}: test field must be non-empty"


# ---------------------------------------------------------------------------
# Implemented claims: test file must exist
# ---------------------------------------------------------------------------


def test_implemented_claims_have_existing_test_files():
    for claim in _load_claims():
        if claim["status"] != "implemented":
            continue
        test_file = TESTS_DIR / f"{claim['test']}.py"
        assert test_file.exists(), (
            f"{claim['id']}: test file {test_file} not found "
            f"(claim status=implemented)"
        )


# ---------------------------------------------------------------------------
# Implemented claims: named test must pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "claim_id,test_name",
    [
        (c["id"], c["test"])
        for c in json.loads(CLAIM_REGISTER_PATH.read_text())["claims"]
        if c["status"] == "implemented"
    ],
)
def test_implemented_claim_test_passes(claim_id: str, test_name: str):
    test_file = TESTS_DIR / f"{test_name}.py"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-x", "-q", "--tb=short",
         "-m", "not live_github"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{claim_id}: tests in {test_name}.py failed:\n"
        f"{result.stdout}\n{result.stderr}"
    )
