from pydantic import ValidationError

from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    EventRecord,
    PollingPolicy,
    RetryBudget,
    RuntimeErrorInfo,
    StageGateDecision,
    TimeoutBudget,
)
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode


def test_timeout_budget_requires_positive_values():
    budget = TimeoutBudget(
        connect_timeout=5.0,
        read_timeout=30.0,
        poll_interval=2.0,
        max_wait=300.0,
        max_retries=4,
    )

    assert budget.max_wait > budget.poll_interval


def test_timeout_budget_rejects_non_positive_values():
    try:
        TimeoutBudget(
            connect_timeout=0.0,
            read_timeout=30.0,
            poll_interval=2.0,
            max_wait=300.0,
            max_retries=4,
        )
    except ValidationError as exc:
        assert "greater than 0" in str(exc)
    else:
        raise AssertionError("Expected TimeoutBudget to reject non-positive timeouts")


def test_stage_gate_decision_only_allows_known_statuses():
    decision = StageGateDecision(status="ready")

    assert decision.status == "ready"

    try:
        StageGateDecision(status="unknown")
    except ValidationError as exc:
        assert "ready" in str(exc)
    else:
        raise AssertionError("Expected StageGateDecision to reject unknown status")


def test_retry_budget_requires_non_negative_retry_count():
    budget = RetryBudget(max_retries=3, backoff_multiplier=2.0)

    assert budget.max_retries == 3

    try:
        RetryBudget(max_retries=-1)
    except ValidationError as exc:
        assert "greater than or equal to 0" in str(exc)
    else:
        raise AssertionError("Expected RetryBudget to reject negative retry counts")


def test_polling_policy_accepts_supported_backoff_modes():
    policy = PollingPolicy(
        timeout_budget=TimeoutBudget(
            connect_timeout=5.0,
            read_timeout=30.0,
            poll_interval=2.0,
            max_wait=300.0,
            max_retries=4,
        ),
        retry_budget=RetryBudget(max_retries=3, backoff_multiplier=2.0),
        backoff_policy="exponential",
    )

    assert policy.backoff_policy == "exponential"


def test_runtime_error_info_uses_stable_error_codes():
    error = RuntimeErrorInfo(
        code=RuntimeErrorCode.NETWORK_SSL_ERROR,
        message="ssl eof",
        retryable=True,
    )

    assert error.code == RuntimeErrorCode.NETWORK_SSL_ERROR
    assert error.retryable is True


def test_event_record_defaults_attempt_and_timestamp():
    event = EventRecord(
        batch_id="batch-001",
        stage_name="extract",
        event_type="poll_retry",
    )

    assert event.attempt == 0
    assert event.timestamp.tzinfo is not None


def test_extract_runtime_policy_requires_submit_poll_download_and_deadline():
    policy = ExtractRuntimePolicy.model_validate(
        {
            "profile_name": "standard",
            "submit": {
                "connect_timeout": 3.0,
                "read_timeout": 10.0,
                "max_retries": 1,
            },
            "poll": {
                "poll_interval": 2.0,
                "max_wait": 150.0,
                "transient_error_retries": 2,
                "backoff_policy": "fixed",
            },
            "download": {
                "connect_timeout": 5.0,
                "read_timeout": 30.0,
                "max_retries": 1,
            },
            "total_deadline_seconds": 210.0,
        }
    )

    assert policy.profile_name == "standard"
