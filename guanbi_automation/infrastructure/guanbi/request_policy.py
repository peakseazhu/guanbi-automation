from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from guanbi_automation.domain.runtime_contract import RequestBudget, RuntimeErrorInfo
from guanbi_automation.infrastructure.guanbi.polling import (
    classify_poll_error,
    should_retry_poll_error,
)


@dataclass(frozen=True)
class RequestCallResult:
    operation_name: str
    completed: bool
    attempts: int
    elapsed_seconds: float
    payload: Any | None = None
    error: RuntimeErrorInfo | None = None


def call_with_request_budget(
    *,
    operation_name: str,
    action: Callable[[], Any],
    budget: RequestBudget | dict[str, Any],
) -> RequestCallResult:
    resolved_budget = (
        budget if isinstance(budget, RequestBudget) else RequestBudget.model_validate(budget)
    )
    started_at = perf_counter()
    attempts = 0

    while True:
        attempts += 1
        try:
            payload = action()
        except Exception as exc:
            error_code = classify_poll_error(exc)
            retryable = should_retry_poll_error(error_code)
            result = RequestCallResult(
                operation_name=operation_name,
                completed=False,
                attempts=attempts,
                elapsed_seconds=perf_counter() - started_at,
                error=RuntimeErrorInfo(
                    code=error_code,
                    message=str(exc),
                    retryable=retryable,
                ),
            )
            if retryable and attempts <= resolved_budget.max_retries:
                continue
            return result

        return RequestCallResult(
            operation_name=operation_name,
            completed=True,
            attempts=attempts,
            elapsed_seconds=perf_counter() - started_at,
            payload=payload,
        )
