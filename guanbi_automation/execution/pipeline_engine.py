from __future__ import annotations

from guanbi_automation.execution.stages.extract import ExtractStage, ExtractStageResult, PlannedExtractRun


class PipelineEngine:
    """Minimal pipeline wrapper for stage-specific execution."""

    def __init__(self, *, extract_stage: ExtractStage) -> None:
        self._extract_stage = extract_stage

    def run_extract(self, planned_extract_run: PlannedExtractRun) -> ExtractStageResult:
        return self._extract_stage.run(planned_extract_run)
