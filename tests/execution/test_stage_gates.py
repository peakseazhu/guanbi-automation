from pathlib import Path

import pytest

from guanbi_automation.application.preflight_service import run_stage_preflight
from guanbi_automation.domain.runtime_contract import PollingPolicy, RetryBudget, TimeoutBudget
from guanbi_automation.execution.stage_gates import (
    evaluate_extract_gate,
    evaluate_publish_gate,
    evaluate_workbook_gate,
)


def test_workbook_gate_blocks_when_cell_count_exceeds_limit():
    decision = evaluate_workbook_gate(
        row_count=70000,
        column_count=220,
        cell_limit=5_000_000,
    )

    assert decision.status == "blocked"


def test_extract_gate_is_ready_when_policy_is_present():
    decision = evaluate_extract_gate(policy=_build_policy())

    assert decision.status == "ready"


def test_extract_gate_blocks_unknown_runtime_profile():
    decision = evaluate_extract_gate(
        policy=None,
        profile_name="ultra",
        available_profiles={"fast", "standard", "heavy"},
    )

    assert decision.status == "blocked"


def test_publish_gate_blocks_when_target_is_missing():
    decision = evaluate_publish_gate(target_ready=False)

    assert decision.status == "blocked"


def test_publish_gate_blocks_when_workbook_path_is_missing(tmp_path):
    decision = evaluate_publish_gate(
        target_ready=True,
        workbook_path=tmp_path / "missing.xlsx",
        mapping_count=1,
    )

    assert decision.status == "blocked"


@pytest.mark.parametrize("workbook_path", [None, ""])
def test_publish_gate_blocks_when_workbook_input_is_missing(workbook_path):
    decision = evaluate_publish_gate(
        target_ready=True,
        workbook_path=workbook_path,
        mapping_count=1,
    )

    assert decision.status == "blocked"


def test_publish_gate_blocks_when_mapping_count_is_zero(tmp_path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    decision = evaluate_publish_gate(
        target_ready=True,
        workbook_path=workbook_path,
        mapping_count=0,
    )

    assert decision.status == "blocked"


def test_preflight_delegates_to_publish_gate_with_runtime_inputs(tmp_path):
    report = run_stage_preflight(
        stage_name="publish",
        target_ready=True,
        workbook_path=tmp_path / "missing.xlsx",
        mapping_count=1,
    )

    assert report.status == "blocked"


def test_preflight_blocks_publish_when_workbook_input_is_blank():
    report = run_stage_preflight(
        stage_name="publish",
        target_ready=True,
        workbook_path="",
        mapping_count=1,
    )

    assert report.status == "blocked"


def test_preflight_blocks_publish_when_mapping_count_is_zero(tmp_path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    report = run_stage_preflight(
        stage_name="publish",
        target_ready=True,
        workbook_path=workbook_path,
        mapping_count=0,
    )

    assert report.status == "blocked"


def test_preflight_delegates_to_extract_gate():
    report = run_stage_preflight(
        stage_name="extract",
        policy=_build_policy(),
    )

    assert report.status == "ready"


def test_workbook_gate_blocks_when_template_file_is_missing(tmp_path):
    decision = evaluate_workbook_gate(
        row_count=100,
        column_count=10,
        cell_limit=5_000_000,
        template_path=tmp_path / "missing.xlsx",
    )

    assert decision.status == "blocked"


def _build_policy() -> PollingPolicy:
    return PollingPolicy(
        timeout_budget=TimeoutBudget(
            connect_timeout=5.0,
            read_timeout=30.0,
            poll_interval=2.0,
            max_wait=300.0,
            max_retries=4,
        ),
        retry_budget=RetryBudget(max_retries=4, backoff_multiplier=2.0),
        backoff_policy="fixed",
    )
