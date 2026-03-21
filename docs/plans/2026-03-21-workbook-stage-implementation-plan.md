# Workbook Stage Implementation Plan

> 状态：Completed
> 完成日期：2026-03-21
> 验证结果：focused verification -> `23 passed`; full suite -> `49 passed`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 workbook 阶段落地受约束 block 写入、写后派生动作、计算触发与 block 级 manifest 证据，同时继续保持 legacy `src/` 只读参考边界。

**Architecture:** 先用独立的 workbook contract 锁定 block 配置、写入模式和 post-write actions；再实现边界受控的 block locator、file-based writer 与 Excel calculation runner；最后把这些能力接入 `workbook_ingest` / `workbook_transform` stage、stage gate 与 manifest。默认数据平面走 file-based writer，Excel / COM 只负责模板计算，不承担默认大块数据写入。

**Tech Stack:** Python 3.12, Pydantic v2, openpyxl, xlwings, pytest

---

### Task 1: Add workbook contract models and bootstrap workbook settings

**Files:**
- Create: `guanbi_automation/domain/workbook_contract.py`
- Modify: `guanbi_automation/domain/runtime_errors.py`
- Modify: `guanbi_automation/bootstrap/settings.py`
- Test: `tests/domain/test_workbook_contract.py`
- Test: `tests/bootstrap/test_settings.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.domain.workbook_contract import WorkbookBlockSpec


def test_append_block_requires_anchor_and_locator_columns():
    block = WorkbookBlockSpec.model_validate(
        {
            "block_id": "sales_append",
            "sheet_name": "底表",
            "source_extract_id": "sales_detail",
            "write_mode": "append_rows",
            "start_row": 2,
            "start_col": 2,
            "append_locator_columns": [2, 3, 4],
            "clear_policy": "none",
        }
    )
    assert block.write_mode == "append_rows"
```

```python
from guanbi_automation.bootstrap.settings import WorkbookSettings


def test_workbook_settings_default_to_file_writer_and_positive_cell_limit():
    settings = WorkbookSettings()
    assert settings.default_writer_engine == "file"
    assert settings.cell_limit > 0
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_workbook_contract.py tests/bootstrap/test_settings.py -v -p no:cacheprovider
```

Expected: FAIL because the workbook contract models and bootstrap settings do not exist yet.

**Step 3: Write the minimal implementation**

Implement:

- workbook enums / literals for:
  - `write_mode`
  - `clear_policy`
  - `post_write_action`
- `WorkbookBlockSpec`
- `WorkbookStageSpec`
- bootstrap-visible workbook settings for:
  - `default_writer_engine`
  - `cell_limit`
  - optional calculation mode defaults
- additional workbook runtime error codes needed by the approved design

Keep the models frozen and validation-focused. Do not mix in file I/O.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_workbook_contract.py tests/bootstrap/test_settings.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/domain/workbook_contract.py guanbi_automation/domain/runtime_errors.py guanbi_automation/bootstrap/settings.py tests/domain/test_workbook_contract.py tests/bootstrap/test_settings.py
git commit -m "feat: add workbook contract models"
```

### Task 2: Implement bounded block range detection and append row resolution

**Files:**
- Create: `guanbi_automation/infrastructure/excel/__init__.py`
- Create: `guanbi_automation/infrastructure/excel/block_locator.py`
- Test: `tests/infrastructure/excel/test_block_locator.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.infrastructure.excel.block_locator import find_append_start_row


def test_append_start_row_uses_locator_columns_within_block_boundary():
    rows = [
        [None, "门店A", 100],
        [None, "门店B", 200],
        [None, None, None],
    ]

    start_row = find_append_start_row(
        rows=rows,
        anchor_row=2,
        locator_columns=[2, 3],
    )

    assert start_row == 4
```

```python
from guanbi_automation.infrastructure.excel.block_locator import trim_trailing_empty_edges


def test_trim_trailing_empty_edges_keeps_internal_gaps():
    trimmed = trim_trailing_empty_edges(
        [
            ["区域", "值", None],
            ["华东", None, None],
            [None, None, None],
        ]
    )

    assert trimmed == [
        ["区域", "值"],
        ["华东", None],
    ]
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_block_locator.py -v -p no:cacheprovider
```

Expected: FAIL because the bounded locator helpers do not exist yet.

**Step 3: Write the minimal implementation**

Implement helpers for:

- trimming tail empty rows / columns without collapsing internal gaps
- resolving append start row from locator columns
- resolving effective write width from source data width and optional block boundaries

Keep the locator pure and deterministic. Do not touch workbook files in this task.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_block_locator.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/infrastructure/excel/__init__.py guanbi_automation/infrastructure/excel/block_locator.py tests/infrastructure/excel/test_block_locator.py
git commit -m "feat: add workbook block locator"
```

### Task 3: Normalize extract artifacts into workbook-ready tabular data

**Files:**
- Create: `guanbi_automation/infrastructure/excel/extract_loader.py`
- Test: `tests/infrastructure/excel/test_extract_loader.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path

from guanbi_automation.infrastructure.excel.extract_loader import load_extract_table


def test_load_extract_table_reads_first_sheet_from_xlsx(tmp_path: Path):
    table = load_extract_table(tmp_path / "sample.xlsx")
    assert table.row_count >= 1
```

```python
from pathlib import Path

from guanbi_automation.infrastructure.excel.extract_loader import load_extract_table


def test_load_extract_table_supports_csv_when_requested(tmp_path: Path):
    table = load_extract_table(tmp_path / "sample.csv")
    assert table.column_count >= 1
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_extract_loader.py -v -p no:cacheprovider
```

Expected: FAIL because the extract loader does not exist yet.

**Step 3: Write the minimal implementation**

Implement a small loader that:

- reads `.xlsx` first-sheet values into normalized rows
- optionally reads `.csv` into the same normalized shape
- trims only trailing empty edges
- returns `row_count`, `column_count`, `cell_count`, and `rows`

Do not mix this with workbook writing yet.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_extract_loader.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/infrastructure/excel/extract_loader.py tests/infrastructure/excel/test_extract_loader.py
git commit -m "feat: add workbook extract loaders"
```

### Task 4: Implement file-based workbook writer for replace and append modes

**Files:**
- Create: `guanbi_automation/infrastructure/excel/workbook_writer.py`
- Test: `tests/infrastructure/excel/test_workbook_writer.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.infrastructure.excel.workbook_writer import write_block


def test_replace_range_clears_values_but_preserves_existing_formula_cells():
    result = write_block(...)
    assert result.written_start_row == 2
    assert result.written_end_row == 4
```

```python
from guanbi_automation.infrastructure.excel.workbook_writer import write_block


def test_append_rows_starts_after_last_locator_row():
    result = write_block(...)
    assert result.written_start_row == 5
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_workbook_writer.py -v -p no:cacheprovider
```

Expected: FAIL because the file-based writer does not exist yet.

**Step 3: Write the minimal implementation**

Implement an `openpyxl`-backed writer that supports:

- template workbook copy to result workbook
- `replace_sheet`
- `replace_range`
- `append_rows`
- `clear_values` and `none`
- block-level write result metadata

Do not add formula fill or fixed-value sidecar logic in this task yet.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_workbook_writer.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/infrastructure/excel/workbook_writer.py tests/infrastructure/excel/test_workbook_writer.py
git commit -m "feat: add file-based workbook block writer"
```

### Task 5: Add post-write actions for fixed values and formula fill coverage

**Files:**
- Modify: `guanbi_automation/infrastructure/excel/workbook_writer.py`
- Test: `tests/infrastructure/excel/test_workbook_writer.py`

**Step 1: Write the failing tests**

```python
def test_fill_fixed_value_only_populates_newly_written_rows():
    result = write_block(...)
    assert result.written_end_row == 6
```

```python
def test_fill_down_formula_extends_formula_to_written_end_row():
    result = write_block(...)
    assert result.actions["fill_down_formula"]["covered_end_row"] == 6
```

```python
import pytest


def test_fill_down_formula_fails_when_seed_formula_is_missing():
    with pytest.raises(ValueError):
        write_block(...)
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_workbook_writer.py -v -p no:cacheprovider
```

Expected: FAIL because post-write actions are not implemented yet.

**Step 3: Write the minimal implementation**

Extend the writer so that:

- `fill_fixed_value` only touches the block's written rows
- `fill_down_formula` copies Excel formulas, not calculated values
- formula extension uses the nearest seed formula row above the write span
- the action validates coverage through `written_end_row`
- missing seed or incomplete coverage returns a stable workbook error

Keep this logic bounded to explicit columns declared by the block spec.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_workbook_writer.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/infrastructure/excel/workbook_writer.py tests/infrastructure/excel/test_workbook_writer.py
git commit -m "feat: add workbook post-write actions"
```

### Task 6: Integrate workbook_ingest stage with gates, preflight, and block-level manifest evidence

**Files:**
- Modify: `guanbi_automation/application/preflight_service.py`
- Modify: `guanbi_automation/execution/stage_gates.py`
- Modify: `guanbi_automation/execution/manifest_builder.py`
- Create: `guanbi_automation/execution/stages/workbook_ingest.py`
- Test: `tests/execution/test_workbook_ingest_stage.py`
- Test: `tests/execution/test_stage_gates.py`

**Step 1: Write the failing tests**

```python
def test_workbook_ingest_manifest_records_written_rows_and_actions():
    result = workbook_ingest_stage.run(...)
    assert result.manifest["blocks"][0]["written_end_row"] == 6
```

```python
def test_workbook_gate_blocks_when_block_cell_count_exceeds_limit():
    decision = evaluate_workbook_gate(
        row_count=70000,
        column_count=220,
        cell_limit=5_000_000,
    )
    assert decision.status == "blocked"
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_workbook_ingest_stage.py tests/execution/test_stage_gates.py -v -p no:cacheprovider
```

Expected: FAIL because the stage and manifest fields do not exist yet.

**Step 3: Write the minimal implementation**

Wire the workbook ingest stage so that it:

- loads extract artifacts into normalized tables
- computes `row_count`, `column_count`, `cell_count`
- runs the workbook gate before each block write
- writes blocks via the file-based writer
- records per-block evidence in the manifest

Do not trigger Excel recalculation in this task.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_workbook_ingest_stage.py tests/execution/test_stage_gates.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/application/preflight_service.py guanbi_automation/execution/stage_gates.py guanbi_automation/execution/manifest_builder.py guanbi_automation/execution/stages/workbook_ingest.py tests/execution/test_workbook_ingest_stage.py tests/execution/test_stage_gates.py
git commit -m "feat: add workbook ingest stage"
```

### Task 7: Add workbook_transform calculation runner and persist calculated result workbooks

**Files:**
- Create: `guanbi_automation/infrastructure/excel/calculation_runner.py`
- Create: `guanbi_automation/execution/stages/workbook_transform.py`
- Modify: `guanbi_automation/execution/pipeline_engine.py`
- Modify: `README.md`
- Test: `tests/execution/test_workbook_transform_stage.py`

**Step 1: Write the failing tests**

```python
def test_workbook_transform_runs_calculation_and_records_result_path():
    result = workbook_transform_stage.run(...)
    assert result.manifest["calculation_completed"] is True
```

```python
def test_workbook_transform_returns_stable_error_when_calculation_fails():
    result = workbook_transform_stage.run(...)
    assert result.status == "failed"
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_workbook_transform_stage.py -v -p no:cacheprovider
```

Expected: FAIL because the transform stage and calculation runner do not exist yet.

**Step 3: Write the minimal implementation**

Implement a thin calculation runner that:

- opens the result workbook in Excel only when calculation is requested
- triggers workbook calculation
- saves and closes cleanly
- returns stable success / failure details

Then wire `workbook_transform` to record:

- result workbook path
- calculation completed flag
- final workbook error when applicable

Keep publish-specific output extraction out of this task.

**Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_workbook_transform_stage.py -v -p no:cacheprovider
```

Expected: PASS

**Step 5: Commit**

```powershell
git add guanbi_automation/infrastructure/excel/calculation_runner.py guanbi_automation/execution/stages/workbook_transform.py guanbi_automation/execution/pipeline_engine.py README.md tests/execution/test_workbook_transform_stage.py
git commit -m "feat: add workbook transform stage"
```

### Task 8: Run focused verification and full-suite regression

**Files:**
- No code changes expected

**Step 1: Run focused verification**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_workbook_contract.py tests/bootstrap/test_settings.py tests/infrastructure/excel/test_block_locator.py tests/infrastructure/excel/test_extract_loader.py tests/infrastructure/excel/test_workbook_writer.py tests/execution/test_workbook_ingest_stage.py tests/execution/test_workbook_transform_stage.py tests/execution/test_stage_gates.py -v -p no:cacheprovider
```

Expected: PASS

**Step 2: Run the full suite**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

Expected: PASS

**Step 3: Commit the final verified state**

```powershell
git add .
git commit -m "feat: implement workbook stage foundation"
```

## Execution Notes

- 本计划必须按 `@superpowers:test-driven-development` 逐 task 执行。
- 任何 workbook 行为与预期不符时，先使用 `@superpowers:systematic-debugging`，再改实现。
- 在宣称 workbook 阶段完成之前，必须使用 `@superpowers:verification-before-completion`。
- 仍然禁止回到 legacy `src/` 编写实现代码。
- `tools/` 当前是未跟踪目录，不属于本计划默认提交范围。

