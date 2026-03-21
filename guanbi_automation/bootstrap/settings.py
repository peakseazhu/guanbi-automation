from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    PollBudget,
    RequestBudget,
)


def _build_extract_runtime_profiles() -> dict[str, ExtractRuntimePolicy]:
    return {
        "fast": ExtractRuntimePolicy(
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
        ),
        "standard": ExtractRuntimePolicy(
            profile_name="standard",
            submit=RequestBudget(connect_timeout=3.0, read_timeout=10.0, max_retries=1),
            poll=PollBudget(
                poll_interval=2.0,
                max_wait=150.0,
                transient_error_retries=2,
                backoff_policy="fixed",
            ),
            download=RequestBudget(connect_timeout=5.0, read_timeout=30.0, max_retries=1),
            total_deadline_seconds=210.0,
        ),
        "heavy": ExtractRuntimePolicy(
            profile_name="heavy",
            submit=RequestBudget(connect_timeout=5.0, read_timeout=15.0, max_retries=2),
            poll=PollBudget(
                poll_interval=3.0,
                max_wait=240.0,
                transient_error_retries=3,
                backoff_policy="fixed",
            ),
            download=RequestBudget(connect_timeout=8.0, read_timeout=60.0, max_retries=2),
            total_deadline_seconds=360.0,
        ),
    }


class ExtractRuntimeSettings(BaseModel):
    """Profile-aware runtime settings for extract execution."""

    model_config = ConfigDict(frozen=True)

    default_profile: str = "standard"
    profiles: dict[str, ExtractRuntimePolicy] = Field(default_factory=_build_extract_runtime_profiles)

    @model_validator(mode="after")
    def validate_default_profile(self) -> "ExtractRuntimeSettings":
        if self.default_profile not in self.profiles:
            raise ValueError("default_profile must reference a configured extract runtime profile")
        return self


class RuntimePolicySettings(BaseModel):
    """Bootstrap-visible runtime policy settings."""

    model_config = ConfigDict(frozen=True)

    extract: ExtractRuntimeSettings = Field(default_factory=ExtractRuntimeSettings)
