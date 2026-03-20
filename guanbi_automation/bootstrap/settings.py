from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractPollingSettings(BaseModel):
    """Single-source extract polling configuration."""

    model_config = ConfigDict(frozen=True)

    connect_timeout: float = Field(default=5.0, gt=0)
    read_timeout: float = Field(default=30.0, gt=0)
    poll_interval: float = Field(default=2.0, gt=0)
    max_wait: float = Field(default=300.0, gt=0)
    max_retries: int = Field(default=4, ge=0)
    backoff_policy: str = "fixed"
    backoff_multiplier: float = Field(default=2.0, gt=0)
    max_backoff: float | None = Field(default=None, gt=0)


class RuntimePolicySettings(BaseModel):
    """Bootstrap-visible runtime policy settings."""

    model_config = ConfigDict(frozen=True)

    extract_polling: ExtractPollingSettings = Field(default_factory=ExtractPollingSettings)
