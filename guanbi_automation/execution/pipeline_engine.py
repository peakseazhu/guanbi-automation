from __future__ import annotations

from guanbi_automation.execution.stages.extract import ExtractStage, ExtractStageResult, PlannedExtractRun
from guanbi_automation.execution.stages.workbook_transform import (
    PlannedWorkbookTransformRun,
    WorkbookTransformStage,
    WorkbookTransformStageResult,
)


class PipelineEngine:
    """Minimal pipeline wrapper for stage-specific execution."""

    def __init__(
        self,
        *,
        extract_stage: ExtractStage,
        workbook_transform_stage: WorkbookTransformStage | None = None,
    ) -> None:
        self._extract_stage = extract_stage
        self._workbook_transform_stage = workbook_transform_stage

    def run_extract(self, planned_extract_run: PlannedExtractRun) -> ExtractStageResult:
        return self._extract_stage.run(planned_extract_run)

    def run_workbook_transform(
        self,
        planned_workbook_transform_run: PlannedWorkbookTransformRun,
    ) -> WorkbookTransformStageResult:
        if self._workbook_transform_stage is None:
            raise ValueError("Workbook transform stage is not configured")
        return self._workbook_transform_stage.run(planned_workbook_transform_run)
