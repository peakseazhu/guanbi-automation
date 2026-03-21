from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    PollingPolicy,
    RetryBudget,
    TimeoutBudget,
)
from guanbi_automation.execution.manifest_builder import build_extract_manifest
from guanbi_automation.infrastructure.guanbi.request_policy import call_with_request_budget
from guanbi_automation.infrastructure.guanbi.client import poll_with_policy


@dataclass(frozen=True)
class PlannedExtractRun:
    batch_id: str
    extract_id: str
    chart_id: str
    runtime_policy: ExtractRuntimePolicy
    template_runtime_profile: str
    effective_runtime_profile: str
    submit_request: Callable[[], Any]
    fetch_status: Callable[[], Any]
    download_file: Callable[[Any], Any]


@dataclass(frozen=True)
class ExtractStageResult:
    status: str
    manifest: dict[str, Any]
    payload: Any | None = None


class ExtractStage:
    """Runs the extract polling loop and records runtime evidence."""

    def __init__(self, *, sleep: Callable[[float], None]) -> None:
        self._sleep = sleep

    def run(self, planned_extract_run: PlannedExtractRun) -> ExtractStageResult:
        submit_result = call_with_request_budget(
            operation_name="submit",
            action=planned_extract_run.submit_request,
            budget=planned_extract_run.runtime_policy.submit,
        )
        if not submit_result.completed:
            return ExtractStageResult(
                status="failed",
                manifest=self._build_manifest(
                    planned_extract_run=planned_extract_run,
                    submit_attempts=submit_result.attempts,
                    submit_elapsed_seconds=submit_result.elapsed_seconds,
                    submit_final_error=submit_result.error,
                    final_error=submit_result.error,
                ),
            )

        poll_result = poll_with_policy(
            fetch_status=planned_extract_run.fetch_status,
            policy=_build_polling_policy(planned_extract_run.runtime_policy),
            sleep=self._sleep,
        )
        if not poll_result.completed:
            return ExtractStageResult(
                status="failed",
                manifest=self._build_manifest(
                    planned_extract_run=planned_extract_run,
                    submit_attempts=submit_result.attempts,
                    submit_elapsed_seconds=submit_result.elapsed_seconds,
                    poll_attempts=poll_result.attempts,
                    poll_total_wait_seconds=poll_result.total_wait_seconds,
                    poll_elapsed_seconds=poll_result.elapsed_seconds,
                    poll_final_error=poll_result.error,
                    final_error=poll_result.error,
                ),
            )

        download_result = call_with_request_budget(
            operation_name="download",
            action=lambda: planned_extract_run.download_file(poll_result.payload),
            budget=planned_extract_run.runtime_policy.download,
        )

        final_error = None if download_result.completed else download_result.error
        status = "completed" if download_result.completed else "failed"
        return ExtractStageResult(
            status=status,
            manifest=self._build_manifest(
                planned_extract_run=planned_extract_run,
                submit_attempts=submit_result.attempts,
                submit_elapsed_seconds=submit_result.elapsed_seconds,
                poll_attempts=poll_result.attempts,
                poll_total_wait_seconds=poll_result.total_wait_seconds,
                poll_elapsed_seconds=poll_result.elapsed_seconds,
                download_attempts=download_result.attempts,
                download_elapsed_seconds=download_result.elapsed_seconds,
                download_final_error=download_result.error,
                final_error=final_error,
            ),
            payload=download_result.payload,
        )

    def _build_manifest(
        self,
        *,
        planned_extract_run: PlannedExtractRun,
        submit_attempts: int = 0,
        submit_elapsed_seconds: float = 0.0,
        submit_final_error: Any | None = None,
        poll_attempts: int = 0,
        poll_total_wait_seconds: float = 0.0,
        poll_elapsed_seconds: float = 0.0,
        poll_final_error: Any | None = None,
        download_attempts: int = 0,
        download_elapsed_seconds: float = 0.0,
        download_final_error: Any | None = None,
        final_error: Any | None = None,
    ) -> dict[str, Any]:
        total_elapsed_seconds = (
            submit_elapsed_seconds + poll_elapsed_seconds + download_elapsed_seconds
        )
        manifest = build_extract_manifest(
            extract_id=planned_extract_run.extract_id,
            stage_name="extract",
            runtime_policy=planned_extract_run.runtime_policy,
            template_runtime_profile=planned_extract_run.template_runtime_profile,
            effective_runtime_profile=planned_extract_run.effective_runtime_profile,
            submit_attempts=submit_attempts,
            submit_elapsed_seconds=submit_elapsed_seconds,
            submit_final_error=submit_final_error,
            poll_attempts=poll_attempts,
            poll_total_wait_seconds=poll_total_wait_seconds,
            poll_elapsed_seconds=poll_elapsed_seconds,
            poll_final_error=poll_final_error,
            download_attempts=download_attempts,
            download_elapsed_seconds=download_elapsed_seconds,
            download_final_error=download_final_error,
            extract_total_elapsed_seconds=total_elapsed_seconds,
            deadline_exhausted=(
                total_elapsed_seconds > planned_extract_run.runtime_policy.total_deadline_seconds
            ),
            final_error=final_error,
        )
        manifest["batch_id"] = planned_extract_run.batch_id
        manifest["chart_id"] = planned_extract_run.chart_id
        manifest["completed"] = final_error is None
        return manifest


def _build_polling_policy(runtime_policy: ExtractRuntimePolicy) -> PollingPolicy:
    return PollingPolicy(
        timeout_budget=TimeoutBudget(
            connect_timeout=runtime_policy.submit.connect_timeout,
            read_timeout=runtime_policy.submit.read_timeout,
            poll_interval=runtime_policy.poll.poll_interval,
            max_wait=runtime_policy.poll.max_wait,
            max_retries=runtime_policy.poll.transient_error_retries,
        ),
        retry_budget=RetryBudget(
            max_retries=runtime_policy.poll.transient_error_retries,
            backoff_multiplier=2.0,
        ),
        backoff_policy=runtime_policy.poll.backoff_policy,
    )
