from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from guanbi_automation.domain.runtime_contract import PollingPolicy, RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.guanbi.polling import (
    classify_poll_status,
    classify_poll_error,
    compute_processing_wait_interval,
    compute_next_wait_interval,
    should_continue_polling,
    should_retry_poll_error,
)


@dataclass(frozen=True)
class PollResult:
    completed: bool
    attempts: int
    total_wait_seconds: float
    elapsed_seconds: float
    payload: Any | None = None
    error: RuntimeErrorInfo | None = None


def poll_with_policy(
    *,
    fetch_status: Callable[[], Any],
    policy: PollingPolicy,
    sleep: Callable[[float], None],
) -> PollResult:
    attempts = 0
    elapsed_seconds = 0.0

    while True:
        try:
            payload = fetch_status()
        except Exception as exc:
            attempts += 1
            error_code = classify_poll_error(exc)
            retryable = should_retry_poll_error(error_code)
            error = RuntimeErrorInfo(
                code=error_code,
                message=str(exc),
                retryable=retryable,
            )
            retry_attempt = attempts - 1
            if not retryable:
                return PollResult(
                    completed=False,
                    attempts=attempts,
                    total_wait_seconds=elapsed_seconds,
                    elapsed_seconds=elapsed_seconds,
                    error=error,
                )
            if elapsed_seconds >= policy.timeout_budget.max_wait:
                return PollResult(
                    completed=False,
                    attempts=attempts,
                    total_wait_seconds=elapsed_seconds,
                    elapsed_seconds=elapsed_seconds,
                    error=RuntimeErrorInfo(
                        code=RuntimeErrorCode.POLL_TIMEOUT,
                        message="Polling budget exhausted",
                        retryable=False,
                    ),
                )
            if not should_continue_polling(
                policy,
                attempt=retry_attempt,
                elapsed_seconds=elapsed_seconds,
            ):
                return PollResult(
                    completed=False,
                    attempts=attempts,
                    total_wait_seconds=elapsed_seconds,
                    elapsed_seconds=elapsed_seconds,
                    error=error,
                )

            wait_seconds = compute_next_wait_interval(
                policy,
                attempt=retry_attempt,
                elapsed_seconds=elapsed_seconds,
            )
            if wait_seconds <= 0:
                return PollResult(
                    completed=False,
                    attempts=attempts,
                    total_wait_seconds=elapsed_seconds,
                    elapsed_seconds=elapsed_seconds,
                    error=RuntimeErrorInfo(
                        code=RuntimeErrorCode.POLL_TIMEOUT,
                        message="Polling budget exhausted before next retry",
                        retryable=False,
                    ),
                )
            sleep(wait_seconds)
            elapsed_seconds += wait_seconds
            continue

        attempts += 1
        try:
            task_status = classify_poll_status(payload)
        except ValueError as exc:
            return PollResult(
                completed=False,
                attempts=attempts,
                total_wait_seconds=elapsed_seconds,
                elapsed_seconds=elapsed_seconds,
                error=RuntimeErrorInfo(
                    code=RuntimeErrorCode.PAYLOAD_PARSE_ERROR,
                    message=str(exc),
                    retryable=False,
                ),
            )

        if task_status == "done":
            return PollResult(
                completed=True,
                attempts=attempts,
                total_wait_seconds=elapsed_seconds,
                elapsed_seconds=elapsed_seconds,
                payload=payload,
            )

        if elapsed_seconds >= policy.timeout_budget.max_wait:
            return PollResult(
                completed=False,
                attempts=attempts,
                total_wait_seconds=elapsed_seconds,
                elapsed_seconds=elapsed_seconds,
                error=RuntimeErrorInfo(
                    code=RuntimeErrorCode.POLL_TIMEOUT,
                    message="Polling budget exhausted",
                    retryable=False,
                ),
            )

        wait_seconds = compute_processing_wait_interval(
            policy,
            elapsed_seconds=elapsed_seconds,
        )
        if wait_seconds <= 0:
            return PollResult(
                completed=False,
                attempts=attempts,
                total_wait_seconds=elapsed_seconds,
                elapsed_seconds=elapsed_seconds,
                error=RuntimeErrorInfo(
                    code=RuntimeErrorCode.POLL_TIMEOUT,
                    message="Polling budget exhausted before next status check",
                    retryable=False,
                ),
            )

        sleep(wait_seconds)
        elapsed_seconds += wait_seconds
