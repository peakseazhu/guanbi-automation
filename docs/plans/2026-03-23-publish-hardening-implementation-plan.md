# Publish Hardening Bundle V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add row/column-aware Feishu publish writing so the validation branch can productize wide-table publish hardening without pulling live-verification readback into the main publish runtime.

**Architecture:** Keep live verification readback separate. Reuse the already-proven `write_values_batch` and `plan_range_segments` primitives, add a dedicated publish writer module that chooses between single-range and batch-range writes, and extend `PublishStage` manifests so wide-table writes are visible and promotable as a foundation bundle.

**Tech Stack:** Python 3.12, httpx, pytest, Pydantic, Markdown

---

### Task 1: Add publish hardening settings and manifest surface

**Files:**
- Modify: `guanbi_automation/bootstrap/settings.py`
- Modify: `guanbi_automation/execution/stages/publish.py`
- Test: `tests/bootstrap/test_settings.py`
- Test: `tests/execution/test_publish_stage.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.bootstrap.settings import PublishSettings


def test_publish_settings_include_column_chunk_limit():
    settings = PublishSettings()

    assert settings.chunk_row_limit > 0
    assert settings.chunk_column_limit == 100


def test_publish_stage_manifest_records_segment_summary(tmp_path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[[f"col-{index}" for index in range(127)]]),
        target_loader=lambda *_args, **_kwargs: _target_context(end_col=128),
        target_writer=lambda *_args, **_kwargs: _write_result(
            chunk_count=1,
            written_row_count=1,
            segment_write_mode="batch_ranges",
            write_segments=[
                {
                    "range_string": "子表1!B3:CW3",
                    "row_count": 1,
                    "column_count": 100,
                    "row_offset": 0,
                    "column_offset": 0,
                },
                {
                    "range_string": "子表1!CX3:DX3",
                    "row_count": 1,
                    "column_count": 27,
                    "row_offset": 0,
                    "column_offset": 100,
                },
            ],
        ),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.manifest["mappings"][0]["write_summary"]["segment_count"] == 2
    assert result.manifest["mappings"][0]["write_summary"]["segment_write_mode"] == "batch_ranges"
    assert result.manifest["mappings"][0]["write_segments"][1]["column_offset"] == 100
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/bootstrap/test_settings.py tests/execution/test_publish_stage.py -v -p no:cacheprovider`

Expected: FAIL because `PublishSettings` does not yet expose `chunk_column_limit`, and `PublishStage` manifests do not yet record segment metadata.

**Step 3: Write minimal implementation**

```python
class PublishSettings(BaseModel):
    chunk_row_limit: int = Field(default=500, gt=0)
    chunk_column_limit: int = Field(default=100, gt=0)
    empty_source_policy: Literal["skip", "replace_with_empty"] = "skip"


@dataclass(frozen=True)
class PublishWriteResult:
    chunk_count: int
    successful_chunk_count: int
    written_row_count: int
    partial_write: bool
    segment_write_mode: str = "single_range"
    write_segments: list[dict[str, Any]] | None = None
    final_error: RuntimeErrorInfo | None = None
    events: list[dict[str, Any]] | None = None
```

Also update `_build_mapping_manifest(...)` so `write_summary` includes:

- `segment_count`
- `segment_write_mode`

and add a top-level `write_segments` list on each mapping manifest.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/bootstrap/test_settings.py tests/execution/test_publish_stage.py -v -p no:cacheprovider`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/bootstrap/test_settings.py tests/execution/test_publish_stage.py guanbi_automation/bootstrap/settings.py guanbi_automation/execution/stages/publish.py
git commit -m "feat: add publish hardening manifest surface"
```

### Task 2: Add a concrete Feishu publish writer for row/column-aware writes

**Files:**
- Create: `guanbi_automation/infrastructure/feishu/publish_writer.py`
- Modify: `guanbi_automation/infrastructure/feishu/__init__.py`
- Test: `tests/infrastructure/feishu/test_publish_writer.py`

**Step 1: Write the failing tests**

```python
import httpx

from guanbi_automation.domain.publish_contract import PublishDataset, PublishTargetSpec
from guanbi_automation.execution.stages.publish import PublishTargetContext
from guanbi_automation.infrastructure.feishu.client import FeishuSheetsClient
from guanbi_automation.infrastructure.feishu.publish_writer import write_publish_target
from guanbi_automation.infrastructure.feishu.target_planner import ResolvedPublishTarget


def test_write_publish_target_uses_single_range_for_small_dataset():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"code": 0, "msg": "ok", "data": {"updatedRows": 2}})

    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=[["x", 1], ["y", 2]],
            row_count=2,
            column_count=2,
            source_range="计算表1!A2:B3",
        ),
        target_context=_target_context(),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert requests == [("PUT", "/open-apis/sheets/v2/spreadsheets/sheet-token/values")]
    assert result.segment_write_mode == "single_range"
    assert len(result.write_segments) == 1


def test_write_publish_target_uses_batch_ranges_for_wide_dataset():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": {"responses": [{"updatedRange": "x"}]}},
        )

    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=[[f"col-{index}" for index in range(127)]],
            row_count=1,
            column_count=127,
            source_range="计算表1!A2:DW2",
        ),
        target_context=_target_context(end_col=128),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert requests == [("POST", "/open-apis/sheets/v2/spreadsheets/sheet-token/values_batch_update")]
    assert result.segment_write_mode == "batch_ranges"
    assert [segment["column_count"] for segment in result.write_segments] == [100, 27]
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/infrastructure/feishu/test_publish_writer.py -v -p no:cacheprovider`

Expected: FAIL because `publish_writer.py` does not exist yet.

**Step 3: Write minimal implementation**

```python
def write_publish_target(
    *,
    mapping: PublishMappingSpec,
    dataset: PublishDataset,
    target_context: PublishTargetContext,
    client: FeishuSheetsClient,
    tenant_access_token: str,
    chunk_row_limit: int,
    chunk_column_limit: int,
) -> PublishWriteResult:
    segments = plan_range_segments(
        start_row=target_context.resolved_target.start_row,
        start_col=target_context.resolved_target.start_col,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        max_rows=chunk_row_limit,
        max_columns=chunk_column_limit,
        sheet_id=target_context.resolved_target.sheet_id or target_context.resolved_target.sheet_title,
    )
    ...
```

Implementation requirements:

- build segment payload values from `dataset.rows`
- one segment -> call `client.write_values(...)`
- multiple segments -> call `client.write_values_batch(...)`
- set `segment_write_mode` to `single_range` or `batch_ranges`
- return `write_segments` and stable `events`
- on adapter failure, return `partial_write=True` only when there is confirmed prior request success; a single failed `values_batch_update` call remains `partial_write=False` because segment-level partial apply is not observable from the adapter boundary

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/infrastructure/feishu/test_publish_writer.py -v -p no:cacheprovider`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/infrastructure/feishu/test_publish_writer.py guanbi_automation/infrastructure/feishu/publish_writer.py guanbi_automation/infrastructure/feishu/__init__.py
git commit -m "feat: add publish hardening writer"
```

### Task 3: Extend target planner coverage for two-dimensional segment planning

**Files:**
- Modify: `tests/infrastructure/feishu/test_target_planner.py`
- Modify: `guanbi_automation/infrastructure/feishu/target_planner.py`

**Step 1: Write the failing test**

```python
def test_plan_range_segments_splits_large_dataset_by_rows_and_columns():
    segments = plan_range_segments(
        start_row=5,
        start_col=2,
        row_count=520,
        column_count=127,
        max_rows=500,
        max_columns=100,
        sheet_id="ySyhcD",
    )

    assert [segment.range_string for segment in segments] == [
        "ySyhcD!B5:CW504",
        "ySyhcD!CX5:DX504",
        "ySyhcD!B505:CW524",
        "ySyhcD!CX505:DX524",
    ]
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/infrastructure/feishu/test_target_planner.py -v -p no:cacheprovider`

Expected: FAIL if the current assertions or planner semantics do not yet cover the row+column case.

**Step 3: Write minimal implementation**

Adjust `plan_range_segments(...)` only if needed so it remains:

- deterministic
- row-major in ordering
- safe for both small and large shapes

If the current planner already passes, keep code minimal and only retain the stronger regression test.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/infrastructure/feishu/test_target_planner.py -v -p no:cacheprovider`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/infrastructure/feishu/test_target_planner.py guanbi_automation/infrastructure/feishu/target_planner.py
git commit -m "test: lock publish hardening segment planning"
```

### Task 4: Wire stage tests to the concrete publish writer behavior

**Files:**
- Modify: `tests/execution/test_publish_stage.py`
- Modify: `guanbi_automation/execution/stages/publish.py`

**Step 1: Write the failing test**

```python
def test_publish_stage_records_batch_range_write_segments(tmp_path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[[f"col-{index}" for index in range(127)]]),
        target_loader=lambda *_args, **_kwargs: _target_context(end_col=128),
        target_writer=lambda *_args, **_kwargs: _write_result(
            chunk_count=1,
            written_row_count=1,
            segment_write_mode="batch_ranges",
            write_segments=[
                {"range_string": "子表1!B3:CW3", "row_count": 1, "column_count": 100, "row_offset": 0, "column_offset": 0},
                {"range_string": "子表1!CX3:EU3", "row_count": 1, "column_count": 27, "row_offset": 0, "column_offset": 100},
            ],
        ),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.manifest["mappings"][0]["write_summary"]["segment_write_mode"] == "batch_ranges"
    assert result.manifest["mappings"][0]["write_segments"][0]["column_count"] == 100
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/execution/test_publish_stage.py -v -p no:cacheprovider`

Expected: FAIL because `PublishStage` manifest output does not yet expose the hardening metadata cleanly enough.

**Step 3: Write minimal implementation**

Keep `PublishStage` dependency injection intact, but ensure stage-level manifest building:

- preserves `write_segments`
- preserves `segment_write_mode`
- does not regress existing blocked/failed semantics

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/execution/test_publish_stage.py -v -p no:cacheprovider`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/execution/test_publish_stage.py guanbi_automation/execution/stages/publish.py
git commit -m "feat: expose publish hardening manifest details"
```

### Task 5: Run focused verification, full suite, and archive the hardening result

**Files:**
- Create: `docs/archive/sessions/2026-03-23-publish-hardening-implementation.md`

**Step 1: Run focused verification**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/bootstrap/test_settings.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider`

Expected: PASS.

**Step 2: Run validation-branch full suite**

Run: `PYTHONPATH="$PWD;D:\get_bi_data__1\.packages" + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider`

Expected: PASS.

**Step 3: Archive the implementation result**

Archive must record:

- hardening scope
- focused verification command and result
- full suite command and result
- whether the bundle is ready for selective promotion review

**Step 4: Commit**

```bash
git add docs/archive/sessions/2026-03-23-publish-hardening-implementation.md
git commit -m "docs: archive publish hardening implementation"
```
