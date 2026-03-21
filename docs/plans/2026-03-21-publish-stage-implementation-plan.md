# Publish Stage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first `publish` stage that reads value-only results from a workbook, maps them to constrained Feishu Sheet targets, writes them in chunks, and records mapping-level manifests.

**Architecture:** The implementation follows the approved `publish source + publish target + publish dataset` design. It adds a publish contract, a workbook source reader, Feishu target planning and client adapters, then wires them through a dedicated `publish` execution stage with mapping-level manifests and conservative retry/append guardrails.

**Tech Stack:** Python 3.12, Pydantic, openpyxl, httpx, pytest

---

### Task 1: Add Publish Contract Models And Defaults

**Files:**
- Create: `guanbi_automation/domain/publish_contract.py`
- Modify: `guanbi_automation/bootstrap/settings.py`
- Modify: `guanbi_automation/domain/runtime_errors.py`
- Test: `tests/domain/test_publish_contract.py`
- Test: `tests/bootstrap/test_settings.py`

**Step 1: Write the failing tests**

```python
import pytest

from guanbi_automation.bootstrap.settings import PublishSettings
from guanbi_automation.domain.publish_contract import PublishSourceSpec, PublishTargetSpec


def test_publish_source_defaults_to_excluding_headers():
    source = PublishSourceSpec(
        source_id="calc-1",
        sheet_name="计算表1",
        read_mode="sheet",
        start_row=2,
        start_col=1,
    )

    assert source.header_mode == "exclude"


def test_append_rows_target_requires_locator_columns():
    with pytest.raises(ValueError):
        PublishTargetSpec(
            spreadsheet_token="sheet-token",
            sheet_id="sub-sheet-1",
            write_mode="append_rows",
            start_row=2,
            start_col=1,
        )


def test_publish_settings_have_safe_defaults():
    settings = PublishSettings()

    assert settings.chunk_row_limit > 0
    assert settings.empty_source_policy == "skip"
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_publish_contract.py tests/bootstrap/test_settings.py -v -p no:cacheprovider
```

Expected: FAIL because `publish_contract.py` and `PublishSettings` do not exist yet.

**Step 3: Write minimal implementation**

```python
class PublishSourceSpec(BaseModel):
    source_id: str
    sheet_name: str
    read_mode: Literal["sheet", "block"]
    start_row: int = Field(ge=1)
    start_col: int = Field(ge=1)
    end_row: int | None = Field(default=None, ge=1)
    end_col: int | None = Field(default=None, ge=1)
    header_mode: Literal["exclude", "include"] = "exclude"


class PublishTargetSpec(BaseModel):
    spreadsheet_token: str
    sheet_id: str | None = None
    sheet_name: str | None = None
    write_mode: Literal["replace_sheet", "replace_range", "append_rows"]
    start_row: int = Field(ge=1)
    start_col: int = Field(ge=1)
    end_row: int | None = Field(default=None, ge=1)
    end_col: int | None = Field(default=None, ge=1)
    append_locator_columns: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_append_rows(self) -> "PublishTargetSpec":
        if self.write_mode == "append_rows" and not self.append_locator_columns:
            raise ValueError("append_rows targets must declare append_locator_columns")
        return self


class PublishSettings(BaseModel):
    chunk_row_limit: int = Field(default=500, gt=0)
    empty_source_policy: Literal["skip", "replace_with_empty"] = "skip"
```

Also extend `RuntimeErrorCode` with publish-specific stable codes needed by the design:

- `publish_target_missing`
- `publish_range_invalid`
- `publish_source_read_error`
- `publish_write_error`
- `publish_append_rerun_blocked`

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_publish_contract.py tests/bootstrap/test_settings.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/domain/test_publish_contract.py tests/bootstrap/test_settings.py guanbi_automation/domain/publish_contract.py guanbi_automation/bootstrap/settings.py guanbi_automation/domain/runtime_errors.py
git commit -m "feat: add publish contract models"
```

### Task 2: Implement Workbook Publish Source Reader

**Files:**
- Modify: `guanbi_automation/domain/publish_contract.py`
- Create: `guanbi_automation/infrastructure/excel/publish_source_reader.py`
- Test: `tests/infrastructure/excel/test_publish_source_reader.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from openpyxl import Workbook

from guanbi_automation.domain.publish_contract import PublishSourceSpec
from guanbi_automation.infrastructure.excel.publish_source_reader import read_publish_source


def test_read_sheet_source_excludes_header_and_trims_tail_blanks(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "计算表1"
    sheet["A1"] = "表头1"
    sheet["B1"] = "表头2"
    sheet["A2"] = "x"
    sheet["B2"] = 1
    sheet["A3"] = "y"
    sheet["B3"] = 2
    workbook.save(workbook_path)

    source = PublishSourceSpec(
        source_id="calc-1",
        sheet_name="计算表1",
        read_mode="sheet",
        start_row=1,
        start_col=1,
        header_mode="exclude",
    )

    dataset = read_publish_source(workbook_path, source)

    assert dataset.rows == [["x", 1], ["y", 2]]
    assert dataset.row_count == 2
    assert dataset.column_count == 2
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_publish_source_reader.py -v -p no:cacheprovider
```

Expected: FAIL because `read_publish_source(...)` does not exist yet.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class PublishDataset:
    rows: list[list[object]]
    row_count: int
    column_count: int
    source_range: str


def read_publish_source(workbook_path: Path, source: PublishSourceSpec) -> PublishDataset:
    workbook = load_workbook(workbook_path, data_only=True)
    sheet = workbook[source.sheet_name]
    rows = _read_bounded_rows(sheet=sheet, source=source)
    if source.header_mode == "exclude" and rows:
        rows = rows[1:]
    trimmed_rows = _trim_trailing_empty_edges(rows)
    return PublishDataset(
        rows=trimmed_rows,
        row_count=len(trimmed_rows),
        column_count=len(trimmed_rows[0]) if trimmed_rows else 0,
        source_range=_format_source_range(source, trimmed_rows),
    )
```

Make sure the helper:

- only scans from the anchor down/right
- trims tail empties only
- supports both `sheet` and `block`
- reads values only via `data_only=True`

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_publish_source_reader.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/infrastructure/excel/test_publish_source_reader.py guanbi_automation/domain/publish_contract.py guanbi_automation/infrastructure/excel/publish_source_reader.py
git commit -m "feat: add publish source reader"
```

### Task 3: Implement Feishu Target Planning And Chunking Helpers

**Files:**
- Create: `guanbi_automation/infrastructure/feishu/__init__.py`
- Create: `guanbi_automation/infrastructure/feishu/target_planner.py`
- Test: `tests/infrastructure/feishu/test_target_planner.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.domain.publish_contract import PublishDataset, PublishTargetSpec
from guanbi_automation.infrastructure.feishu.target_planner import (
    chunk_publish_rows,
    resolve_replace_range,
)


def test_replace_range_uses_dataset_shape_to_build_unique_target_range():
    dataset = PublishDataset(
        rows=[["x", 1], ["y", 2]],
        row_count=2,
        column_count=2,
        source_range="计算表1!A2:B3",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_id="sub-sheet-1",
        write_mode="replace_range",
        start_row=3,
        start_col=2,
    )

    resolved = resolve_replace_range(target=target, dataset=dataset, sheet_title="子表1")

    assert resolved.range_string == "子表1!B3:C4"


def test_chunk_publish_rows_splits_dataset_by_row_limit():
    rows = [["a", 1], ["b", 2], ["c", 3]]

    chunks = chunk_publish_rows(rows=rows, chunk_row_limit=2)

    assert chunks == [
        [["a", 1], ["b", 2]],
        [["c", 3]],
    ]
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/feishu/test_target_planner.py -v -p no:cacheprovider
```

Expected: FAIL because `target_planner.py` does not exist yet.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class ResolvedPublishTarget:
    sheet_id: str
    sheet_title: str
    range_string: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int


def resolve_replace_range(
    *,
    target: PublishTargetSpec,
    dataset: PublishDataset,
    sheet_title: str,
) -> ResolvedPublishTarget:
    end_row = target.end_row or (target.start_row + dataset.row_count - 1)
    end_col = target.end_col or (target.start_col + dataset.column_count - 1)
    return ResolvedPublishTarget(
        sheet_id=target.sheet_id or "",
        sheet_title=sheet_title,
        range_string=_build_a1_range(sheet_title, target.start_row, target.start_col, end_row, end_col),
        start_row=target.start_row,
        start_col=target.start_col,
        end_row=end_row,
        end_col=end_col,
    )


def chunk_publish_rows(*, rows: list[list[object]], chunk_row_limit: int) -> list[list[list[object]]]:
    return [rows[index:index + chunk_row_limit] for index in range(0, len(rows), chunk_row_limit)]
```

Also include planner helpers for:

- `replace_sheet`
- `append_rows`
- A1 range conversion
- append last-row detection from locator-column values

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/feishu/test_target_planner.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/infrastructure/feishu/test_target_planner.py guanbi_automation/infrastructure/feishu/__init__.py guanbi_automation/infrastructure/feishu/target_planner.py
git commit -m "feat: add publish target planner"
```

### Task 4: Implement Feishu Sheets Client Adapter

**Files:**
- Create: `guanbi_automation/infrastructure/feishu/client.py`
- Test: `tests/infrastructure/feishu/test_client.py`

**Step 1: Write the failing test**

```python
import httpx

from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.feishu.client import map_feishu_error


def test_map_feishu_401_to_publish_auth_error():
    response = httpx.Response(401, json={"code": 99991663, "msg": "Auth failed"})

    error = map_feishu_error("query_sheets", response)

    assert error.code == RuntimeErrorCode.PUBLISH_AUTH_ERROR
    assert error.retryable is False


def test_map_feishu_rate_limit_to_retryable_publish_error():
    response = httpx.Response(429, json={"code": 90013, "msg": "rate limit"})

    error = map_feishu_error("write_values", response)

    assert error.code == RuntimeErrorCode.PUBLISH_RATE_LIMIT_ERROR
    assert error.retryable is True
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/feishu/test_client.py -v -p no:cacheprovider
```

Expected: FAIL because `client.py` does not exist yet.

**Step 3: Write minimal implementation**

```python
class FeishuSheetsClient:
    def __init__(self, *, base_url: str = "https://open.feishu.cn", transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=30.0)

    def query_sheets(self, spreadsheet_token: str, tenant_access_token: str) -> list[dict[str, object]]:
        response = self._client.get(
            f"/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query",
            headers=_auth_headers(tenant_access_token),
        )
        if response.is_error:
            raise PublishClientError(map_feishu_error("query_sheets", response))
        return response.json()["data"]["sheets"]

    def write_values(self, spreadsheet_token: str, range_string: str, rows: list[list[object]], tenant_access_token: str) -> dict[str, object]:
        response = self._client.put(
            f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values",
            headers=_auth_headers(tenant_access_token),
            json={"valueRange": {"range": range_string, "values": rows}},
        )
        if response.is_error:
            raise PublishClientError(map_feishu_error("write_values", response))
        return response.json()
```

Implement small, isolated helpers for:

- auth headers
- response parsing
- stable error mapping to `RuntimeErrorInfo`

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/feishu/test_client.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/infrastructure/feishu/test_client.py guanbi_automation/infrastructure/feishu/client.py
git commit -m "feat: add feishu sheets client adapter"
```

### Task 5: Implement Publish Manifest Builders And Stage

**Files:**
- Modify: `guanbi_automation/execution/manifest_builder.py`
- Create: `guanbi_automation/execution/stages/publish.py`
- Test: `tests/execution/test_publish_stage.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from guanbi_automation.execution.stages.publish import PlannedPublishRun, PublishStage


def test_publish_stage_records_mapping_level_results(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["x", 1], ["y", 2]]),
        target_loader=lambda *_args, **_kwargs: _target_context(),
        target_writer=lambda *_args, **_kwargs: _write_result(chunk_count=1, written_row_count=2),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.status == "completed"
    assert result.manifest["completed_mapping_count"] == 1
    assert result.manifest["mappings"][0]["write_summary"]["written_row_count"] == 2
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

Expected: FAIL because `publish.py` and publish manifest helpers do not exist yet.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class PlannedPublishRun:
    batch_id: str
    job_id: str
    workbook_path: Path
    mappings: list[PublishMappingSpec]


class PublishStage:
    def run(self, planned_run: PlannedPublishRun) -> PublishStageResult:
        mapping_manifests: list[dict[str, object]] = []
        for mapping in planned_run.mappings:
            dataset = self._source_reader(planned_run.workbook_path, mapping.source)
            mapping_result = self._publish_mapping(mapping=mapping, dataset=dataset)
            mapping_manifests.append(mapping_result.manifest)
        return PublishStageResult(
            status=_derive_job_status(mapping_manifests),
            manifest=build_publish_manifest(
                batch_id=planned_run.batch_id,
                job_id=planned_run.job_id,
                workbook_path=str(planned_run.workbook_path),
                mappings=mapping_manifests,
            ),
        )
```

Make sure the stage:

- treats `mapping` as the smallest execution unit
- records `chunk_count`, `successful_chunk_count`, `partial_write`, and `written_row_count`
- blocks dangerous append reruns before writing
- honors `empty_source_policy`

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/execution/test_publish_stage.py guanbi_automation/execution/manifest_builder.py guanbi_automation/execution/stages/publish.py
git commit -m "feat: add publish stage"
```

### Task 6: Integrate Publish Stage Into Runtime Wiring

**Files:**
- Modify: `guanbi_automation/execution/stage_gates.py`
- Modify: `guanbi_automation/application/preflight_service.py`
- Modify: `guanbi_automation/execution/pipeline_engine.py`
- Modify: `README.md`
- Test: `tests/execution/test_stage_gates.py`
- Test: `tests/execution/test_publish_stage.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path

from guanbi_automation.execution.pipeline_engine import PipelineEngine
from guanbi_automation.execution.stage_gates import evaluate_publish_gate
from guanbi_automation.execution.stages.publish import PlannedPublishRun, PublishStage


def test_publish_gate_blocks_when_workbook_path_is_missing(tmp_path: Path):
    decision = evaluate_publish_gate(
        target_ready=True,
        workbook_path=tmp_path / "missing.xlsx",
        mapping_count=1,
    )

    assert decision.status == "blocked"


def test_pipeline_engine_delegates_to_publish_stage(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[]),
        target_loader=lambda *_args, **_kwargs: _target_context(),
        target_writer=lambda *_args, **_kwargs: _write_result(chunk_count=0, written_row_count=0),
    )
    engine = PipelineEngine(extract_stage=_extract_stage_stub(), publish_stage=stage)

    result = engine.run_publish(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[],
        )
    )

    assert result.manifest["stage_name"] == "publish"
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_stage_gates.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

Expected: FAIL because publish gate and pipeline engine do not support the new behavior yet.

**Step 3: Write minimal implementation**

```python
def evaluate_publish_gate(
    *,
    target_ready: bool,
    workbook_path: Path | str | None = None,
    mapping_count: int = 0,
) -> StageGateDecision:
    if workbook_path is not None and not Path(workbook_path).exists():
        return StageGateDecision(status="blocked", reason="Publish workbook is missing")
    if mapping_count < 1:
        return StageGateDecision(status="blocked", reason="Publish mappings are missing")
    if not target_ready:
        return StageGateDecision(status="blocked", reason="Publish target is not ready")
    return StageGateDecision(status="ready", reason="Publish target is ready")


class PipelineEngine:
    def run_publish(self, planned_publish_run: PlannedPublishRun) -> PublishStageResult:
        if self._publish_stage is None:
            raise ValueError("Publish stage is not configured")
        return self._publish_stage.run(planned_publish_run)
```

Also update `README.md` so current project status explicitly includes publish foundation targets and constraints.

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/execution/test_stage_gates.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/execution/test_stage_gates.py tests/execution/test_publish_stage.py guanbi_automation/execution/stage_gates.py guanbi_automation/application/preflight_service.py guanbi_automation/execution/pipeline_engine.py README.md
git commit -m "feat: wire publish stage into runtime"
```

### Task 7: Run Focused Verification, Full Suite, And Archive Evidence

**Files:**
- Create: `docs/archive/sessions/2026-03-21-publish-stage-implementation.md`

**Step 1: Run focused publish verification**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_publish_contract.py tests/bootstrap/test_settings.py tests/infrastructure/excel/test_publish_source_reader.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_client.py tests/execution/test_publish_stage.py tests/execution/test_stage_gates.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 2: Run full suite**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

Expected: PASS.

**Step 3: Archive verification evidence**

```markdown
# 2026-03-21 会话归档（Publish Stage Implementation）

## 完成内容
- publish contract
- workbook publish source reader
- feishu target planner
- feishu client
- publish stage
- runtime wiring

## 验证证据
- focused verification: PASS
- full suite: PASS

## 当前恢复点
- publish stage implementation complete
- next: post-implementation hardening / publish real-sample validation
```

**Step 4: Commit**

```bash
git add docs/archive/sessions/2026-03-21-publish-stage-implementation.md
git commit -m "docs: archive publish stage implementation results"
```
