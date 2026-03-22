from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    PollBudget,
    PollingPolicy,
    RequestBudget,
    RetryBudget,
    RuntimeErrorInfo,
    TimeoutBudget,
)
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
        runtime_policy=_build_polling_policy(),
    )

    assert manifest["batch_id"] == "batch-001"
    assert manifest["runtime_policy"]["timeout_budget"]["max_wait"] == 300.0
    assert manifest["runtime_policy"]["retry_budget"]["max_retries"] == 4


def test_extract_manifest_includes_segmented_runtime_evidence():
    manifest = build_extract_manifest(
        extract_id="extract-001",
        stage_name="extract",
        runtime_policy=_build_extract_runtime_policy(),
        template_runtime_profile="heavy",
        effective_runtime_profile="fast",
        submit_attempts=1,
        submit_elapsed_seconds=0.1,
        submit_final_error=None,
        poll_attempts=3,
        poll_total_wait_seconds=2.0,
        poll_elapsed_seconds=2.0,
        poll_final_error=None,
        download_attempts=1,
        download_elapsed_seconds=0.2,
        download_final_error=RuntimeErrorInfo(
            code=RuntimeErrorCode.NETWORK_SSL_ERROR,
            message="ssl eof",
            retryable=True,
        ),
        extract_total_elapsed_seconds=2.3,
        deadline_exhausted=False,
        final_error=RuntimeErrorInfo(
            code=RuntimeErrorCode.NETWORK_SSL_ERROR,
            message="ssl eof",
            retryable=True,
        ),
    )

    assert manifest["extract_id"] == "extract-001"
    assert manifest["template_runtime_profile"] == "heavy"
    assert manifest["effective_runtime_profile"] == "fast"
    assert manifest["submit_attempts"] == 1
    assert manifest["download_final_error"]["code"] == RuntimeErrorCode.NETWORK_SSL_ERROR
    assert manifest["final_error"]["code"] == RuntimeErrorCode.NETWORK_SSL_ERROR


def _build_polling_policy() -> PollingPolicy:
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


def _build_extract_runtime_policy() -> ExtractRuntimePolicy:
    return ExtractRuntimePolicy(
        profile_name="fast",
        submit=RequestBudget(connect_timeout=3.0, read_timeout=8.0, max_retries=1),
        poll=PollBudget(
            poll_interval=2.0,
            max_wait=45.0,
            transient_error_retries=1,
            backoff_policy="fixed",
        ),
        download=RequestBudget(connect_timeout=5.0, read_timeout=15.0, max_retries=1),
        total_deadline_seconds=75.0,
    )
