from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from guanbi_automation.execution.manifest_builder import build_workbook_manifest
from guanbi_automation.infrastructure.excel.calculation_runner import (
    CalculationRunResult,
    run_workbook_calculation,
)


@dataclass(frozen=True)
class PlannedWorkbookTransformRun:
    batch_id: str
    job_id: str
    workbook_path: Path


@dataclass(frozen=True)
class WorkbookTransformStageResult:
    status: str
    manifest: dict[str, Any]
    workbook_path: Path | None = None


class WorkbookTransformStage:
    """Triggers workbook calculation and records transform evidence."""

    def __init__(
        self,
        *,
        calculation_runner: Callable[[Path], CalculationRunResult] = run_workbook_calculation,
    ) -> None:
        self._calculation_runner = calculation_runner

    def run(self, planned_run: PlannedWorkbookTransformRun) -> WorkbookTransformStageResult:
        calculation_result = self._calculation_runner(planned_run.workbook_path)
        manifest = build_workbook_manifest(
            batch_id=planned_run.batch_id,
            job_id=planned_run.job_id,
            stage_name="workbook_transform",
            template_path="",
            result_path=str(calculation_result.workbook_path),
            blocks=[],
            completed=calculation_result.completed,
            calculation_completed=calculation_result.completed,
            final_error=calculation_result.error,
        )
        return WorkbookTransformStageResult(
            status="completed" if calculation_result.completed else "failed",
            manifest=manifest,
            workbook_path=calculation_result.workbook_path,
        )
