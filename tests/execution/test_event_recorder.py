from guanbi_automation.domain.runtime_contract import PollingPolicy, RetryBudget, RuntimeErrorInfo, TimeoutBudget
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.event_recorder import build_event_record
from guanbi_automation.execution.manifest_builder import (
    build_batch_manifest,
    build_extract_manifest,
)


def test_event_record_contains_runtime_identifiers():
    event = build_event_record(
        batch_id="batch-001",
        stage_name="extract",
        event_type="poll_retry",
        extract_id="extract-001",
        chart_id="chart-123",
        task_id="task-999",
        attempt=2,
    )

    assert event.batch_id == "batch-001"
    assert event.stage_name == "extract"
    assert event.extract_id == "extract-001"
    assert event.chart_id == "chart-123"
    assert event.task_id == "task-999"
    assert event.attempt == 2


def test_batch_manifest_includes_runtime_policy_summary():
    manifest = build_batch_manifest(
        batch_id="batch-001",
        runtime_policy=_build_policy(),
    )

    assert manifest["batch_id"] == "batch-001"
    assert manifest["runtime_policy"]["timeout_budget"]["max_wait"] == 300.0
    assert manifest["runtime_policy"]["retry_budget"]["max_retries"] == 4


def test_extract_manifest_includes_final_error_summary():
    manifest = build_extract_manifest(
        extract_id="extract-001",
        stage_name="extract",
        runtime_policy=_build_policy(),
        final_error=RuntimeErrorInfo(
            code=RuntimeErrorCode.POLL_TIMEOUT,
            message="polling budget exhausted",
            retryable=False,
        ),
    )

    assert manifest["extract_id"] == "extract-001"
    assert manifest["stage_name"] == "extract"
    assert manifest["final_error"]["code"] == RuntimeErrorCode.POLL_TIMEOUT
    assert manifest["runtime_policy"]["timeout_budget"]["poll_interval"] == 2.0


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
        backoff_policy="exponential",
    )
