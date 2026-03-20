from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from guanbi_automation.domain.runtime_errors import RuntimeErrorCode

BackoffPolicy = Literal["fixed", "exponential"]
DoctorCheckStatus = Literal["passed", "failed"]
StageGateStatus = Literal["ready", "blocked", "degraded"]


class TimeoutBudget(BaseModel):
    """Runtime timeout and polling limits for a single execution context."""

    model_config = ConfigDict(frozen=True)

    connect_timeout: float = Field(gt=0)
    read_timeout: float = Field(gt=0)
    poll_interval: float = Field(gt=0)
    max_wait: float = Field(gt=0)
    max_retries: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_poll_window(self) -> "TimeoutBudget":
        if self.max_wait <= self.poll_interval:
            raise ValueError("max_wait must be greater than poll_interval")
        return self


class RetryBudget(BaseModel):
    """Retry limits shared by network-facing runtime components."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=0, ge=0)
    backoff_multiplier: float = Field(default=1.0, gt=0)
    max_backoff: float | None = Field(default=None, gt=0)


class PollingPolicy(BaseModel):
    """Composes timeout and retry budgets with a supported backoff mode."""

    model_config = ConfigDict(frozen=True)

    timeout_budget: TimeoutBudget
    retry_budget: RetryBudget
    backoff_policy: BackoffPolicy = "fixed"


class StageGateDecision(BaseModel):
    """Explicit readiness decision emitted before entering a stage."""

    model_config = ConfigDict(frozen=True)

    status: StageGateStatus
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RuntimeErrorInfo(BaseModel):
    """Minimal structured runtime error payload for manifests and events."""

    model_config = ConfigDict(frozen=True)

    code: RuntimeErrorCode
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class EventRecord(BaseModel):
    """Structured runtime event payload with stable correlation fields."""

    model_config = ConfigDict(frozen=True)

    batch_id: str
    stage_name: str
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    job_id: str | None = None
    extract_id: str | None = None
    chart_id: str | None = None
    task_id: str | None = None
    error_code: RuntimeErrorCode | None = None
    attempt: int = Field(default=0, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class DoctorCheckResult(BaseModel):
    """Structured result for a single doctor check."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: DoctorCheckStatus
    detail: str | None = None


class DoctorReport(BaseModel):
    """Aggregated environment doctor status."""

    model_config = ConfigDict(frozen=True)

    overall_status: Literal["passed", "failed"]
    checks: list[DoctorCheckResult]
    failing_item_count: int = Field(ge=0)
