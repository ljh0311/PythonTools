"""Pytest wrapper for ML evaluation (see tests/ml_evaluation.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.ml_evaluation import run_ml_evaluation


@pytest.fixture(scope="module")
def evaluation_report():
    csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "22 - Sheet1.csv")
    if not os.path.exists(csv):
        pytest.skip("Local CSV not present")
    return run_ml_evaluation(csv)


def test_ml_evaluation_verdict(evaluation_report):
    assert evaluation_report["verdict"] in ("PASS", "WARN"), (
        f"ML evaluation failed: {evaluation_report['checks']}"
    )


def test_all_checks_pass_or_warn(evaluation_report):
    for check in evaluation_report["checks"]:
        assert check["status"] in ("pass", "warn"), (
            f"{check['name']}: {check['message']}"
        )


def test_scenarios_produce_ml(evaluation_report):
    for scenario in evaluation_report["scenarios"]:
        assert scenario.get("ml_top_cost") is not None, scenario["name"]
        assert scenario["ml_top_cost"] > 0


def test_no_scenario_ratio_fail(evaluation_report):
    failed = [s["name"] for s in evaluation_report["scenarios"] if s.get("ratio_status") == "fail"]
    assert not failed, f"ML far from history: {failed}"
