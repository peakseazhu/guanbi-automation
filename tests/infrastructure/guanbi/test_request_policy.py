import httpx

from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.guanbi.request_policy import (
    call_with_request_budget,
)


def test_request_budget_retries_transient_network_errors_once():
    calls = 0

    def flaky_call():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectTimeout("timed out")
        return {"ok": True}

    result = call_with_request_budget(
        operation_name="submit",
        action=flaky_call,
        budget={"connect_timeout": 3.0, "read_timeout": 10.0, "max_retries": 1},
    )

    assert result.completed is True
    assert calls == 2


def test_request_budget_returns_stable_error_for_non_retryable_failure():
    result = call_with_request_budget(
        operation_name="download",
        action=lambda: (_ for _ in ()).throw(ValueError("bad payload")),
        budget={"connect_timeout": 5.0, "read_timeout": 30.0, "max_retries": 1},
    )

    assert result.completed is False
    assert result.error.code == RuntimeErrorCode.REQUEST_SUBMIT_ERROR
