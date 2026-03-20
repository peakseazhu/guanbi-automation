import httpx

from guanbi_automation.domain.runtime_contract import PollingPolicy, RetryBudget, TimeoutBudget
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.guanbi.client import poll_with_policy
from guanbi_automation.infrastructure.guanbi.polling import (
    classify_poll_error,
    compute_next_wait_interval,
    should_continue_polling,
    should_retry_poll_error,
)


def test_ssl_error_is_retryable():
    assert should_retry_poll_error("network_ssl_error") is True


def test_classify_connect_timeout_to_stable_error_code():
    error = httpx.ConnectTimeout("timed out")

    assert classify_poll_error(error) == RuntimeErrorCode.NETWORK_CONNECT_TIMEOUT


def test_compute_next_wait_interval_uses_exponential_backoff():
    policy = _build_policy(backoff_policy="exponential")

    assert compute_next_wait_interval(policy, attempt=0, elapsed_seconds=0.0) == 2.0
    assert compute_next_wait_interval(policy, attempt=1, elapsed_seconds=2.0) == 4.0


def test_should_continue_polling_stops_after_budget_is_exhausted():
    policy = _build_policy(max_wait=5.0, max_retries=2)

    assert should_continue_polling(policy, attempt=1, elapsed_seconds=4.0) is True
    assert should_continue_polling(policy, attempt=2, elapsed_seconds=4.0) is False
    assert should_continue_polling(policy, attempt=1, elapsed_seconds=5.0) is False


def test_poll_with_policy_returns_stable_error_after_retries_exhausted():
    attempts = 0

    def fetch_status():
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectTimeout("still waiting")

    result = poll_with_policy(
        fetch_status=fetch_status,
        policy=_build_policy(max_wait=10.0, max_retries=2),
        sleep=lambda _seconds: None,
    )

    assert attempts == 3
    assert result.completed is False
    assert result.attempts == 3
    assert result.error.code == RuntimeErrorCode.NETWORK_CONNECT_TIMEOUT


def _build_policy(
    *,
    backoff_policy: str = "fixed",
    max_wait: float = 30.0,
    max_retries: int = 3,
) -> PollingPolicy:
    return PollingPolicy(
        timeout_budget=TimeoutBudget(
            connect_timeout=5.0,
            read_timeout=30.0,
            poll_interval=2.0,
            max_wait=max_wait,
            max_retries=max_retries,
        ),
        retry_budget=RetryBudget(max_retries=max_retries, backoff_multiplier=2.0),
        backoff_policy=backoff_policy,
    )
