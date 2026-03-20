from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from guanbi_automation.execution.manifest_builder import build_extract_manifest
from guanbi_automation.infrastructure.guanbi.client import poll_with_policy
from guanbi_automation.domain.runtime_contract import PollingPolicy


@dataclass(frozen=True)
class PlannedExtractRun:
    batch_id: str
    extract_id: str
    chart_id: str
    polling_policy: PollingPolicy
    fetch_status: Callable[[], Any]


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
        poll_result = poll_with_policy(
            fetch_status=planned_extract_run.fetch_status,
            policy=planned_extract_run.polling_policy,
            sleep=self._sleep,
        )
        manifest = build_extract_manifest(
            extract_id=planned_extract_run.extract_id,
            stage_name="extract",
            runtime_policy=planned_extract_run.polling_policy,
            final_error=poll_result.error,
        )
        manifest["batch_id"] = planned_extract_run.batch_id
        manifest["chart_id"] = planned_extract_run.chart_id
        manifest["poll_attempts"] = poll_result.attempts
        manifest["total_wait_seconds"] = poll_result.total_wait_seconds

        status = "completed" if poll_result.completed else "failed"
        return ExtractStageResult(
            status=status,
            manifest=manifest,
            payload=poll_result.payload,
        )
