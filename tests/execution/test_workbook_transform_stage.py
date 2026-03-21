from pathlib import Path

from openpyxl import Workbook

from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.stages.workbook_transform import (
    PlannedWorkbookTransformRun,
    WorkbookTransformStage,
)
from guanbi_automation.infrastructure.excel.calculation_runner import CalculationRunResult



def test_workbook_transform_runs_calculation_and_records_result_path(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    Workbook().save(workbook_path)

    calls: list[Path] = []

    def fake_runner(path: Path) -> CalculationRunResult:
        calls.append(path)
        return CalculationRunResult(completed=True, workbook_path=path)

    stage = WorkbookTransformStage(calculation_runner=fake_runner)
    result = stage.run(
        PlannedWorkbookTransformRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
        )
    )

    assert result.status == "completed"
    assert result.manifest["calculation_completed"] is True
    assert result.manifest["result_path"] == str(workbook_path)
    assert calls == [workbook_path]



def test_workbook_transform_returns_stable_error_when_calculation_fails(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    Workbook().save(workbook_path)

    def failing_runner(path: Path) -> CalculationRunResult:
        return CalculationRunResult(
            completed=False,
            workbook_path=path,
            error=RuntimeErrorInfo(
                code=RuntimeErrorCode.WORKBOOK_CALCULATION_ERROR,
                message="Excel calculation failed",
            ),
        )

    stage = WorkbookTransformStage(calculation_runner=failing_runner)
    result = stage.run(
        PlannedWorkbookTransformRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
        )
    )

    assert result.status == "failed"
    assert result.manifest["final_error"]["code"] == RuntimeErrorCode.WORKBOOK_CALCULATION_ERROR
