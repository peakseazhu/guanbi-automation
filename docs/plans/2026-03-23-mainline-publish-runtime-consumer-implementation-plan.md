# Mainline Publish Runtime Consumer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first non-test mainline publish runtime consumer that reads a YAML publish spec, accepts an explicit `tenant_access_token`, runs `PublishStage` through `PipelineEngine`, emits a stable JSON envelope, and explicitly rejects `append_rows`.

**Architecture:** Keep the first consumer thin and layered. A new spec-loader module will parse a minimal YAML object that directly reuses `PublishMappingSpec`; a new application service will own preflight validation, deterministic IDs, target loading, and stage wiring; a thin CLI module will parse argv, call the service, print a stable envelope JSON, and map status to exit codes. Existing publish primitives stay authoritative for source reads, target planning, writing, and manifests.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, httpx, pytest

---

## File Structure

**Create:**

- `guanbi_automation/application/publish_runtime_spec.py`
  Loads the minimal YAML publish spec and validates it against existing `PublishMappingSpec`.
- `guanbi_automation/application/publish_runtime_service.py`
  Owns preflight validation, deterministic `batch_id` / `job_id`, target loading, `PublishStage` wiring, and result envelope construction.
- `guanbi_automation/publish/__init__.py`
  Marks the new `publish` package for runtime entrypoint code.
- `guanbi_automation/publish/run_publish.py`
  Thin CLI entrypoint. Parses argv, calls the runtime service, prints JSON, and returns the exit code.
- `tests/application/test_publish_runtime_spec.py`
  Covers YAML shape/validation and reuse of existing publish contracts.
- `tests/application/test_publish_runtime_service.py`
  Covers preflight failures, deterministic IDs, target resolution priority, and `PublishStage` wiring.
- `tests/publish/test_run_publish.py`
  Covers CLI parsing, envelope printing, and `0/1/2` exit semantics.
- `docs/archive/sessions/2026-03-23-mainline-publish-runtime-consumer-implementation.md`
  Records what was wired into `main`, what remains intentionally unwired, and fresh verification evidence.

**Modify:**

- `README.md`
  Update mainline state to say `main` now has a non-test publish runtime consumer for `replace_sheet` / `replace_range`.
- `docs/archive/decision-log.md`
  Add an ADR for the first mainline publish consumer slice and the explicit deferral of `append_rows`.

**Keep unchanged but verify against:**

- `guanbi_automation/domain/publish_contract.py`
- `guanbi_automation/domain/runtime_errors.py`
- `guanbi_automation/execution/pipeline_engine.py`
- `guanbi_automation/execution/stages/publish.py`
- `guanbi_automation/infrastructure/excel/publish_source_reader.py`
- `guanbi_automation/infrastructure/feishu/client.py`
- `guanbi_automation/infrastructure/feishu/target_planner.py`
- `guanbi_automation/infrastructure/feishu/publish_writer.py`

### Task 1: Add the YAML Publish Spec Loader

**Files:**

- Create: `guanbi_automation/application/publish_runtime_spec.py`
- Test: `tests/application/test_publish_runtime_spec.py`

- [ ] **Step 1: Write the failing spec-loader tests**

```python
from pathlib import Path

import pytest

from guanbi_automation.application.publish_runtime_spec import (
    PublishRuntimeSpec,
    load_publish_runtime_spec,
)


def test_load_publish_runtime_spec_reuses_publish_mapping_contract(tmp_path: Path):
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: publish-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "      header_mode: exclude\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      write_mode: replace_range\n"
        "      start_row: 3\n"
        "      start_col: 2\n",
        encoding="utf-8",
    )

    spec = load_publish_runtime_spec(spec_path)

    assert isinstance(spec, PublishRuntimeSpec)
    assert spec.mappings[0].target.write_mode == "replace_range"


def test_load_publish_runtime_spec_rejects_non_mapping_payload(tmp_path: Path):
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text("- bad\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_publish_runtime_spec(spec_path)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_runtime_spec.py -v -p no:cacheprovider
```

Expected:

- `ModuleNotFoundError` for `guanbi_automation.application.publish_runtime_spec`

- [ ] **Step 3: Implement the loader and spec model**

```python
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from guanbi_automation.domain.publish_contract import PublishMappingSpec


class PublishRuntimeSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    mappings: list[PublishMappingSpec] = Field(default_factory=list, min_length=1)


def load_publish_runtime_spec(spec_path: Path | str) -> PublishRuntimeSpec:
    payload = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("publish runtime spec must be a mapping")
    return PublishRuntimeSpec.model_validate(payload)
```

- [ ] **Step 4: Re-run the targeted tests**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_runtime_spec.py -v -p no:cacheprovider
```

Expected:

- All tests in `tests/application/test_publish_runtime_spec.py` PASS

- [ ] **Step 5: Commit the spec-loader slice**

```bash
git add guanbi_automation/application/publish_runtime_spec.py tests/application/test_publish_runtime_spec.py
git commit -m "feat: add publish runtime spec loader"
```

### Task 2: Add the Runtime Service Envelope and Preflight Rules

**Files:**

- Create: `guanbi_automation/application/publish_runtime_service.py`
- Test: `tests/application/test_publish_runtime_service.py`

- [ ] **Step 1: Write the failing preflight/service tests**

```python
from pathlib import Path

from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.application.publish_runtime_service import run_publish_runtime


def test_run_publish_runtime_rejects_append_rows_before_stage(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: append-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      write_mode: append_rows\n"
        "      start_row: 3\n"
        "      start_col: 2\n"
        "      append_locator_columns: [1]\n",
        encoding="utf-8",
    )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
    )

    assert result.status == "preflight_failed"
    assert result.final_error.code == RuntimeErrorCode.CONFIGURATION_ERROR


def test_run_publish_runtime_uses_deterministic_default_ids(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: append-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      write_mode: append_rows\n"
        "      start_row: 3\n"
        "      start_col: 2\n"
        "      append_locator_columns: [1]\n",
        encoding="utf-8",
    )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
    )

    assert result.batch_id == "publish-cli"
    assert result.job_id.startswith("publish-")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_runtime_service.py -v -p no:cacheprovider
```

Expected:

- `ModuleNotFoundError` for `guanbi_automation.application.publish_runtime_service`

- [ ] **Step 3: Implement the result envelope and preflight-only service path**

```python
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from guanbi_automation.application.publish_runtime_spec import load_publish_runtime_spec
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode


class PublishRuntimeResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage_name: Literal["publish"] = "publish"
    status: Literal["preflight_failed", "completed", "blocked", "failed"]
    batch_id: str
    job_id: str
    manifest: dict[str, object] | None = None
    final_error: RuntimeErrorInfo | None = None


def _default_job_id(workbook_path: Path, spec_path: Path) -> str:
    digest = sha256(f"{workbook_path.resolve()}|{spec_path.resolve()}".encode("utf-8")).hexdigest()[:12]
    return f"publish-{digest}"


def run_publish_runtime(
    *,
    workbook_path: Path | None,
    spec_path: Path | None,
    tenant_access_token: str | None,
    batch_id: str | None = None,
    job_id: str | None = None,
    client_factory=None,
    source_reader=None,
    target_writer=None,
) -> PublishRuntimeResult:
    resolved_batch_id = batch_id or "publish-cli"
    resolved_job_id = job_id or _default_job_id(
        workbook_path or Path("<missing-workbook>"),
        spec_path or Path("<missing-spec>"),
    )

    if workbook_path is None:
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="workbook_path is required",
            details={"field": "workbook_path"},
        )
    if spec_path is None:
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="spec_path is required",
            details={"field": "spec_path"},
        )
    if not tenant_access_token or not tenant_access_token.strip():
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="tenant_access_token is required",
            details={"field": "tenant_access_token"},
        )

    try:
        spec = load_publish_runtime_spec(spec_path)
    except (OSError, ValueError, TypeError) as exc:
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message=str(exc),
            details={"spec_path": str(spec_path)},
        )

    if any(mapping.target.write_mode == "append_rows" for mapping in spec.mappings):
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="append_rows is not wired into the first mainline publish consumer",
            details={"unsupported_write_mode": "append_rows"},
        )
```

- [ ] **Step 4: Re-run the targeted tests**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_runtime_service.py -v -p no:cacheprovider
```

Expected:

- Preflight-oriented tests PASS

- [ ] **Step 5: Commit the preflight/result slice**

```bash
git add guanbi_automation/application/publish_runtime_service.py tests/application/test_publish_runtime_service.py
git commit -m "feat: add publish runtime preflight service"
```

### Task 3: Wire the Runtime Service to PublishStage

**Files:**

- Modify: `guanbi_automation/application/publish_runtime_service.py`
- Test: `tests/application/test_publish_runtime_service.py`
- Modify: `guanbi_automation/execution/stages/publish.py`
- Test: `tests/execution/test_publish_stage.py`

- [ ] **Step 1: Extend the service tests with real wiring coverage**

```python
from pathlib import Path

import httpx

from guanbi_automation.application.publish_runtime_service import run_publish_runtime
from guanbi_automation.domain.publish_contract import PublishDataset
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.stages.publish import PublishWriteResult
from guanbi_automation.infrastructure.feishu.client import FeishuSheetsClient


def test_run_publish_runtime_executes_replace_range_mapping(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: publish-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      sheet_name: 子表1\n"
        "      write_mode: replace_range\n"
        "      start_row: 3\n"
        "      start_col: 2\n",
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sheets/query")
        return httpx.Response(
            200,
            json={"code": 0, "data": {"sheets": [{"sheet_id": "ySyhcD", "title": "子表1"}]}},
        )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        source_reader=lambda *_args, **_kwargs: PublishDataset(
            rows=[["x", 1]],
            row_count=1,
            column_count=2,
            source_range="计算表1!A2:B2",
        ),
        target_writer=lambda **_kwargs: PublishWriteResult(
            chunk_count=1,
            successful_chunk_count=1,
            written_row_count=1,
            partial_write=False,
        ),
    )

    assert result.status == "completed"
    assert result.manifest["stage_name"] == "publish"


def test_run_publish_runtime_prefers_sheet_id_over_sheet_name(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: publish-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      sheet_name: 错误别名\n"
        "      write_mode: replace_range\n"
        "      start_row: 3\n"
        "      start_col: 2\n",
        encoding="utf-8",
    )
    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: FeishuSheetsClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "sheets": [
                                {"sheet_id": "ySyhcD", "title": "真实子表"},
                                {"sheet_id": "other", "title": "错误别名"},
                            ]
                        },
                    },
                )
            )
        ),
        source_reader=lambda *_args, **_kwargs: PublishDataset(
            rows=[["x", 1]],
            row_count=1,
            column_count=2,
            source_range="计算表1!A2:B2",
        ),
        target_writer=lambda **_kwargs: PublishWriteResult(
            chunk_count=1,
            successful_chunk_count=1,
            written_row_count=1,
            partial_write=False,
        ),
    )
    assert result.status == "completed"
    assert result.manifest["mappings"][0]["target"]["sheet_id"] == "ySyhcD"


def test_run_publish_runtime_propagates_blocked_or_failed_status(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: publish-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      write_mode: replace_range\n"
        "      start_row: 3\n"
        "      start_col: 2\n",
        encoding="utf-8",
    )
    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: FeishuSheetsClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"code": 0, "data": {"sheets": [{"sheet_id": "ySyhcD", "title": "子表1"}]}},
                )
            )
        ),
        source_reader=lambda *_args, **_kwargs: PublishDataset(
            rows=[["x", 1]],
            row_count=1,
            column_count=2,
            source_range="计算表1!A2:B2",
        ),
        target_writer=lambda **_kwargs: PublishWriteResult(
            chunk_count=1,
            successful_chunk_count=0,
            written_row_count=0,
            partial_write=True,
            final_error=RuntimeErrorInfo(
                code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
                message="Write failed",
                retryable=False,
            ),
        ),
    )

    assert result.status == "failed"
    assert result.final_error is not None


def test_run_publish_runtime_uses_default_writer_binding(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: publish-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        "      sheet_id: ySyhcD\n"
        "      write_mode: replace_range\n"
        "      start_row: 3\n"
        "      start_col: 2\n",
        encoding="utf-8",
    )
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path.endswith("/sheets/query"):
            return httpx.Response(
                200,
                json={"code": 0, "data": {"sheets": [{"sheet_id": "ySyhcD", "title": "子表1"}]}},
            )
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": {"updatedRange": "ySyhcD!B3:C3"}},
        )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        source_reader=lambda *_args, **_kwargs: PublishDataset(
            rows=[["x", 1]],
            row_count=1,
            column_count=2,
            source_range="计算表1!A2:B2",
        ),
    )

    assert result.status == "completed"
    assert any(path.endswith("/values") for _, path in requests)
```

- [ ] **Step 2: Run the targeted service tests and verify they fail for missing wiring**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_runtime_service.py -v -p no:cacheprovider
```

Expected:

- FAIL because the service is not yet building the real target loader / `PublishStage` path

- [ ] **Step 3: Implement stage wiring, target loading, and status propagation**

```python
from guanbi_automation.execution.pipeline_engine import PipelineEngine
from guanbi_automation.bootstrap.settings import PublishSettings
from guanbi_automation.execution.stages.publish import (
    PlannedPublishRun,
    PublishStage,
    PublishTargetContext,
    PublishWriteResult,
)
from guanbi_automation.infrastructure.feishu.client import FeishuSheetsClient, PublishClientError
from guanbi_automation.infrastructure.excel.publish_source_reader import read_publish_source
from guanbi_automation.infrastructure.feishu import (
    resolve_replace_range,
    resolve_replace_sheet,
    write_publish_target,
)

class _NullExtractStage:
    def run(self, planned_run):  # pragma: no cover - never used by this consumer
        return planned_run


client = client_factory() if client_factory else FeishuSheetsClient()
publish_settings = PublishSettings()


def _write_target(
    *,
    workbook_path: Path,
    mapping,
    dataset,
    target_context,
) -> PublishWriteResult:
    return (target_writer or write_publish_target)(
        mapping=mapping,
        dataset=dataset,
        target_context=target_context,
        client=client,
        tenant_access_token=tenant_access_token,
        chunk_row_limit=publish_settings.chunk_row_limit,
        chunk_column_limit=publish_settings.chunk_column_limit,
    )


def _load_target_context(
    *,
    workbook_path: Path,
    mapping,
    dataset,
) -> PublishTargetContext:
    sheets = client.query_sheets(mapping.target.spreadsheet_token, tenant_access_token)
    resolved_sheet = _resolve_sheet_metadata(
        sheets=sheets,
        sheet_id=mapping.target.sheet_id,
        sheet_name=mapping.target.sheet_name,
    )
    resolved_target = (
        resolve_replace_sheet(
            target=mapping.target,
            dataset=dataset,
            sheet_title=resolved_sheet["title"],
        )
        if mapping.target.write_mode == "replace_sheet"
        else resolve_replace_range(
            target=mapping.target,
            dataset=dataset,
            sheet_title=resolved_sheet["title"],
        )
    )
    return PublishTargetContext(resolved_target=resolved_target)


stage = PublishStage(
    source_reader=source_reader or read_publish_source,
    target_loader=_load_target_context,
    target_writer=_write_target,
)
engine = PipelineEngine(extract_stage=_NullExtractStage(), publish_stage=stage)
stage_result = engine.run_publish(
    PlannedPublishRun(
        batch_id=resolved_batch_id,
        job_id=resolved_job_id,
        workbook_path=workbook_path,
        mappings=spec.mappings,
    )
)
return PublishRuntimeResult(
    status=stage_result.status,
    batch_id=resolved_batch_id,
    job_id=resolved_job_id,
    manifest=stage_result.manifest,
    final_error=_extract_final_error(stage_result.manifest),
)

# In the same task, modify PublishStage so target-loader PublishClientError
# becomes a failed mapping manifest instead of escaping as an uncaught exception.
```

- [ ] **Step 3a: Add a failing stage-level regression test for target-loader failures**

```python
def test_publish_stage_marks_target_loader_publish_client_error_as_failed(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100]]),
        target_loader=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PublishClientError(
                "query_sheets",
                RuntimeErrorInfo(
                    code=RuntimeErrorCode.PUBLISH_TARGET_MISSING,
                    message="Sheet missing",
                    retryable=False,
                ),
            )
        ),
        target_writer=lambda *_args, **_kwargs: _write_result(chunk_count=1, written_row_count=1),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.status == "failed"
    assert result.manifest["mappings"][0]["final_error"]["code"] == RuntimeErrorCode.PUBLISH_TARGET_MISSING
```

- [ ] **Step 4: Re-run the targeted service tests**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest `
  tests/application/test_publish_runtime_service.py `
  tests/execution/test_publish_stage.py `
  -v -p no:cacheprovider
```

Expected:

- All tests in `tests/application/test_publish_runtime_service.py` and `tests/execution/test_publish_stage.py` PASS

- [ ] **Step 5: Commit the runtime wiring slice**

```bash
git add guanbi_automation/application/publish_runtime_service.py guanbi_automation/execution/stages/publish.py tests/application/test_publish_runtime_service.py tests/execution/test_publish_stage.py
git commit -m "feat: wire publish runtime service to stage"
```

### Task 4: Add the Thin CLI Entrypoint

**Files:**

- Create: `guanbi_automation/publish/__init__.py`
- Create: `guanbi_automation/publish/run_publish.py`
- Test: `tests/publish/test_run_publish.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
from pathlib import Path

import json

from guanbi_automation.application.publish_runtime_service import PublishRuntimeResult
from guanbi_automation.publish.run_publish import main


def test_main_prints_result_envelope(monkeypatch, capsys):
    monkeypatch.setattr(
        "guanbi_automation.publish.run_publish.run_publish_runtime",
        lambda **_kwargs: PublishRuntimeResult(
            status="completed",
            batch_id="publish-cli",
            job_id="publish-123456789abc",
            manifest={"stage_name": "publish"},
            final_error=None,
        ),
    )

    exit_code = main(
        [
            "--workbook-path",
            "result.xlsx",
            "--spec-path",
            "publish.yaml",
            "--tenant-access-token",
            "tenant-token",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "completed"


def test_main_returns_preflight_envelope_for_missing_args(capsys):
    exit_code = main(["--spec-path", "publish.yaml"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "preflight_failed"


def test_module_is_executable():
    source = Path("guanbi_automation/publish/run_publish.py").read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in source
```

- [ ] **Step 2: Run the targeted CLI tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/publish/test_run_publish.py -v -p no:cacheprovider
```

Expected:

- `ModuleNotFoundError` for `guanbi_automation.publish.run_publish`

- [ ] **Step 3: Implement the CLI**

```python
import argparse
import json
import sys
from pathlib import Path

from guanbi_automation.application.publish_runtime_service import run_publish_runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook-path")
    parser.add_argument("--spec-path")
    parser.add_argument("--tenant-access-token")
    parser.add_argument("--batch-id")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)

    result = run_publish_runtime(
        workbook_path=Path(args.workbook_path) if args.workbook_path else None,
        spec_path=Path(args.spec_path) if args.spec_path else None,
        tenant_access_token=args.tenant_access_token,
        batch_id=args.batch_id,
        job_id=args.job_id,
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if result.status == "completed" else 2 if result.status == "preflight_failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Re-run the targeted CLI tests**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/publish/test_run_publish.py -v -p no:cacheprovider
```

Expected:

- All tests in `tests/publish/test_run_publish.py` PASS

- [ ] **Step 5: Commit the CLI slice**

```bash
git add guanbi_automation/publish/__init__.py guanbi_automation/publish/run_publish.py tests/publish/test_run_publish.py
git commit -m "feat: add publish runtime cli"
```

### Task 5: Update Mainline Docs and Run Fresh Verification

**Files:**

- Modify: `README.md`
- Modify: `docs/archive/decision-log.md`
- Create: `docs/archive/sessions/2026-03-23-mainline-publish-runtime-consumer-implementation.md`
- Verify: `tests/application/test_publish_runtime_spec.py`
- Verify: `tests/application/test_publish_runtime_service.py`
- Verify: `tests/publish/test_run_publish.py`
- Verify: `tests/infrastructure/feishu/test_client.py`
- Verify: `tests/infrastructure/feishu/test_target_planner.py`
- Verify: `tests/infrastructure/feishu/test_publish_writer.py`
- Verify: `tests/execution/test_publish_stage.py`

- [ ] **Step 1: Update mainline docs to match the new consumer reality**

```markdown
- `main` now has a non-test publish runtime consumer
- first consumer scope is `replace_sheet` / `replace_range`
- `append_rows` remains present in contract/planner/stage safety, but is not yet wired into the consumer
```

- [ ] **Step 2: Add the implementation session archive with verification evidence and capability ledger**

```markdown
## Fresh Verification
- targeted runtime consumer suite: PASS
- publish foundation regression suite: PASS

## Scope Ledger
- consumer-wired now: replace_sheet, replace_range
- foundation-only still: append_rows, target-state read path, token fetch, readback/comparison
```

- [ ] **Step 3: Run the focused verification bundle**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest `
  tests/application/test_publish_runtime_spec.py `
  tests/application/test_publish_runtime_service.py `
  tests/publish/test_run_publish.py `
  tests/infrastructure/feishu/test_client.py `
  tests/infrastructure/feishu/test_target_planner.py `
  tests/infrastructure/feishu/test_publish_writer.py `
  tests/execution/test_publish_stage.py `
  -v -p no:cacheprovider
```

Expected:

- All selected tests PASS

- [ ] **Step 4: Run the full suite in the worktree**

Run:

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

Expected:

- Full suite PASS with zero failures

- [ ] **Step 5: Commit the docs + verification bundle**

```bash
git add README.md docs/archive/decision-log.md docs/archive/sessions/2026-03-23-mainline-publish-runtime-consumer-implementation.md
git commit -m "docs: record mainline publish runtime consumer"
```
