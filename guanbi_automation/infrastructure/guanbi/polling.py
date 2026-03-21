from __future__ import annotations

from typing import Literal

import httpx

from guanbi_automation.domain.runtime_contract import PollingPolicy
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode

RetryablePollError = Literal[
    RuntimeErrorCode.NETWORK_CONNECT_TIMEOUT,
    RuntimeErrorCode.NETWORK_SSL_ERROR,
]
PollTaskStatus = Literal["processing", "done"]

_RETRYABLE_ERRORS: frozenset[RuntimeErrorCode] = frozenset(
    {
        RuntimeErrorCode.NETWORK_CONNECT_TIMEOUT,
        RuntimeErrorCode.NETWORK_SSL_ERROR,
    }
)


def classify_poll_error(error: Exception | RuntimeErrorCode | str) -> RuntimeErrorCode:
    if isinstance(error, RuntimeErrorCode):
        return error
    if isinstance(error, str):
        normalized = error.strip().lower()
        for code in RuntimeErrorCode:
            if code.value == normalized:
                return code
        if "ssl" in normalized:
            return RuntimeErrorCode.NETWORK_SSL_ERROR
        return RuntimeErrorCode.REQUEST_SUBMIT_ERROR
    if isinstance(error, httpx.ConnectTimeout):
        return RuntimeErrorCode.NETWORK_CONNECT_TIMEOUT
    if "ssl" in str(error).lower():
        return RuntimeErrorCode.NETWORK_SSL_ERROR
    return RuntimeErrorCode.REQUEST_SUBMIT_ERROR


def should_retry_poll_error(error_code: RuntimeErrorCode | str) -> bool:
    return classify_poll_error(error_code) in _RETRYABLE_ERRORS


def classify_poll_status(payload: object) -> PollTaskStatus:
    if not isinstance(payload, dict):
        raise ValueError("Polling payload must be a dictionary")

    raw_status = payload.get("task_status")
    if not isinstance(raw_status, str):
        raise ValueError("Polling payload is missing task_status")

    normalized = raw_status.strip().lower()
    if normalized in {"processing", "done"}:
        return normalized

    raise ValueError(f"Unsupported task_status: {raw_status}")


def compute_next_wait_interval(
    policy: PollingPolicy,
    *,
    attempt: int,
    elapsed_seconds: float,
) -> float:
    base_interval = policy.timeout_budget.poll_interval
    if policy.backoff_policy == "exponential":
        wait_seconds = base_interval * (policy.retry_budget.backoff_multiplier ** attempt)
    else:
        wait_seconds = base_interval

    if policy.retry_budget.max_backoff is not None:
        wait_seconds = min(wait_seconds, policy.retry_budget.max_backoff)

    remaining = policy.timeout_budget.max_wait - elapsed_seconds
    return max(0.0, min(wait_seconds, remaining))


def compute_processing_wait_interval(
    policy: PollingPolicy,
    *,
    elapsed_seconds: float,
) -> float:
    remaining = policy.timeout_budget.max_wait - elapsed_seconds
    return max(0.0, min(policy.timeout_budget.poll_interval, remaining))


def should_continue_polling(
    policy: PollingPolicy,
    *,
    attempt: int,
    elapsed_seconds: float,
) -> bool:
    return (
        attempt < policy.timeout_budget.max_retries
        and attempt < policy.retry_budget.max_retries
        and elapsed_seconds < policy.timeout_budget.max_wait
    )
