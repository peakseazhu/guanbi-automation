from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import xlwings as xw

from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode


@dataclass(frozen=True)
class CalculationRunResult:
    completed: bool
    workbook_path: Path
    error: RuntimeErrorInfo | None = None



def run_workbook_calculation(workbook_path: Path) -> CalculationRunResult:
    app = None
    workbook = None
    path = Path(workbook_path)
    try:
        app = xw.App(visible=False, add_book=False)
        app.display_alerts = False
        app.screen_updating = False
        workbook = app.books.open(str(path), update_links=False, read_only=False)
        workbook.app.calculate()
        workbook.save()
        return CalculationRunResult(completed=True, workbook_path=path)
    except Exception as exc:
        return CalculationRunResult(
            completed=False,
            workbook_path=path,
            error=RuntimeErrorInfo(
                code=RuntimeErrorCode.WORKBOOK_CALCULATION_ERROR,
                message=str(exc),
            ),
        )
    finally:
        if workbook is not None:
            try:
                workbook.close()
            except Exception:
                pass
        if app is not None:
            try:
                app.quit()
            except Exception:
                pass
