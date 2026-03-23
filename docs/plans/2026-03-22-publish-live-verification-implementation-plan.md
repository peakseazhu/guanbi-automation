# Publish Live Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a dedicated publish live-verification path that reuses the existing Feishu app and spreadsheet resources, writes the real `全国执行` workbook sample to the temporary Feishu sub-sheet, reads it back, and archives comparison evidence.

**Architecture:** The implementation keeps production publish contracts intact and adds a thin live-verification layer around them. The new path loads a local verification spec, normalizes workbook values into JSON-safe publish cells, performs row/column-aware write planning against official Feishu limits, executes batch writes plus readback through the Feishu adapter, and stores evidence under `runs/live_verification/`.

**Tech Stack:** Python 3.12, Pydantic, PyYAML, httpx, openpyxl, pytest

---

### Task 1: Add Live Verification Spec And Canonical Value Models

**Files:**
- Create: `guanbi_automation/domain/live_verification.py`
- Create: `guanbi_automation/application/live_verification_spec.py`
- Create: `config/live_verification/publish/real_sample.example.yaml`
- Modify: `.gitignore`
- Test: `tests/domain/test_live_verification.py`
- Test: `tests/application/test_live_verification_spec.py`

**Step 1: Write the failing tests**

```python
from datetime import datetime
from pathlib import Path

from guanbi_automation.application.live_verification_spec import load_publish_live_verification_spec
from guanbi_automation.domain.live_verification import canonicalize_publish_cell


def test_canonicalize_datetime_to_iso_date():
    value = canonicalize_publish_cell(datetime(2026, 3, 9, 0, 0, 0))

    assert value == "2026-03-09"


def test_load_publish_live_verification_spec_from_yaml(tmp_path: Path):
    spec_path = tmp_path / "real_sample.local.yaml"
    spec_path.write_text(
        \"\"\"
workbook_path: D:/get_bi_data__1/执行管理字段更新版.xlsx
source_sheet_name: 全国执行
source_start_row: 1
source_start_col: 1
header_mode: include
spreadsheet_token: sample-token
sheet_id: ySyhcD
target_start_row: 1
target_start_col: 1
write_mode: replace_sheet
\"\"\",
        encoding="utf-8",
    )

    spec = load_publish_live_verification_spec(spec_path)

    assert spec.sheet_id == "ySyhcD"
    assert spec.header_mode == "include"
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_live_verification.py tests/application/test_live_verification_spec.py -v -p no:cacheprovider
```

Expected: FAIL because live verification models and loader do not exist yet.

**Step 3: Write minimal implementation**

```python
class PublishLiveVerificationSpec(BaseModel):
    workbook_path: Path
    source_sheet_name: str
    source_start_row: int = Field(ge=1)
    source_start_col: int = Field(ge=1)
    header_mode: Literal["include", "exclude"] = "include"
    spreadsheet_token: str
    sheet_id: str
    target_start_row: int = Field(ge=1)
    target_start_col: int = Field(ge=1)
    write_mode: Literal["replace_sheet"] = "replace_sheet"
```

Also implement:

- a loader that reads YAML from a local spec path
- a canonical cell normalizer that converts:
  - `None -> ""`
  - `date / datetime -> stable string`
  - `int / float / str -> JSON-safe scalar`
- `.gitignore` entries for:
  - `config/live_verification/**/*.local.yaml`
  - `runs/live_verification/`

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_live_verification.py tests/application/test_live_verification_spec.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/domain/test_live_verification.py tests/application/test_live_verification_spec.py guanbi_automation/domain/live_verification.py guanbi_automation/application/live_verification_spec.py config/live_verification/publish/real_sample.example.yaml .gitignore
git commit -m "feat: add publish live verification spec"
```

### Task 2: Extend Feishu Adapter For Token, Readback, And Column-Aware Batch Writes

**Files:**
- Modify: `guanbi_automation/infrastructure/feishu/client.py`
- Modify: `guanbi_automation/infrastructure/feishu/target_planner.py`
- Test: `tests/infrastructure/feishu/test_client.py`
- Test: `tests/infrastructure/feishu/test_target_planner.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.infrastructure.feishu.target_planner import plan_range_segments


def test_plan_range_segments_splits_wide_dataset_by_column_limit():
    segments = plan_range_segments(
        start_row=1,
        start_col=1,
        row_count=80,
        column_count=127,
        max_rows=5000,
        max_columns=100,
        sheet_id="ySyhcD",
    )

    assert [segment.range_string for segment in segments] == [
        "ySyhcD!A1:CV58",
        "ySyhcD!CW1:DW58",
    ]
```

Also add failing client tests for:

- `fetch_tenant_access_token(...)`
- `read_values(...)`
- `write_values_batch(...)`

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_client.py -v -p no:cacheprovider
```

Expected: FAIL because the adapter only supports sheet query + single-range write today.

**Step 3: Write minimal implementation**

Implement:

- `fetch_tenant_access_token(app_id, app_secret)`
- `read_values(spreadsheet_token, range_string, tenant_access_token, ...)`
- `write_values_batch(spreadsheet_token, value_ranges, tenant_access_token)`
- `plan_range_segments(...)`

Rules:

- enforce official `5000 x 100` per segment
- generate contiguous row/column rectangles
- prefer one `values_batch_update` call when multiple column segments belong to the same write step

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_client.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_client.py guanbi_automation/infrastructure/feishu/client.py guanbi_automation/infrastructure/feishu/target_planner.py
git commit -m "feat: add feishu live verification readback support"
```

### Task 3: Build Comparison And Evidence Archive Service

**Files:**
- Create: `guanbi_automation/application/publish_live_verification_service.py`
- Test: `tests/application/test_publish_live_verification_service.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from guanbi_automation.application.publish_live_verification_service import PublishLiveVerificationService


def test_service_archives_write_and_readback_evidence(tmp_path: Path):
    service = PublishLiveVerificationService(
        workbook_reader=lambda *_args, **_kwargs: _normalized_matrix(),
        feishu_runtime=lambda *_args, **_kwargs: _successful_runtime(),
        evidence_root=tmp_path,
    )

    result = service.run(_spec())

    assert result.status == "completed"
    assert (result.evidence_dir / "comparison.json").exists()
    assert result.comparison["matches"] is True
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_live_verification_service.py -v -p no:cacheprovider
```

Expected: FAIL because the service does not exist yet.

**Step 3: Write minimal implementation**

The service should:

1. load + normalize workbook source
2. fetch tenant token
3. query sheet metadata and confirm `sheet_id`
4. build row/column-aware write plan
5. write all segments
6. read back all written ranges
7. canonicalize readback
8. compare expected vs actual
9. write evidence JSON files under `runs/live_verification/publish/<timestamp>/`

Also define a stable result model:

```python
class PublishLiveVerificationResult(BaseModel):
    status: Literal["completed", "failed"]
    evidence_dir: Path
    comparison: dict[str, object]
```

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_live_verification_service.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/application/test_publish_live_verification_service.py guanbi_automation/application/publish_live_verification_service.py
git commit -m "feat: add publish live verification service"
```

### Task 4: Add Thin Entry Point And README Guidance

**Files:**
- Create: `guanbi_automation/live_verification/publish_real_sample.py`
- Modify: `README.md`
- Test: `tests/application/test_live_verification_spec.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from guanbi_automation.live_verification.publish_real_sample import resolve_default_spec_path


def test_default_spec_path_points_to_local_publish_live_verification_file():
    path = resolve_default_spec_path(Path("D:/get_bi_data__1"))

    assert path.as_posix().endswith("config/live_verification/publish/real_sample.local.yaml")
```

**Step 2: Run test to verify it fails**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_live_verification_spec.py -v -p no:cacheprovider
```

Expected: FAIL because the thin entry module does not exist yet.

**Step 3: Write minimal implementation**

Add a small `python -m` entry that:

- resolves the default local spec path
- calls `PublishLiveVerificationService`
- prints the evidence directory and comparison result

Update `README.md` with:

- the purpose of publish live verification
- where the local spec lives
- which Feishu app permissions and document permissions are required
- that the first real sample uses:
  - workbook sheet `全国执行`
  - temporary sheet `测试子表 / ySyhcD`
  - `replace_sheet` from `A1`
  - readback comparison

**Step 4: Run test to verify it passes**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_live_verification_spec.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/application/test_live_verification_spec.py guanbi_automation/live_verification/publish_real_sample.py README.md
git commit -m "feat: add publish live verification entry"
```

### Task 5: Run Focused Verification, Execute The Real Sample, And Archive Results

**Files:**
- Create: `docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`

**Step 1: Run focused automated verification**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_live_verification.py tests/application/test_live_verification_spec.py tests/application/test_publish_live_verification_service.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_client.py -v -p no:cacheprovider
```

Expected: PASS.

**Step 2: Run the real sample verification**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m guanbi_automation.live_verification.publish_real_sample
```

Expected:

- tenant token fetch succeeds
- target sheet metadata resolves to `ySyhcD`
- write plan contains two column segments for the canonical `58 x 127` sample
- readback comparison reports `matches = true`
- evidence directory is printed

**Step 3: Re-run the relevant regression slice**

```powershell
$env:PYTHONPATH="$PWD;D:\get_bi_data__1\.packages"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

Expected: PASS.

**Step 4: Archive the session**

Record:

- focused test command and result
- real sample run evidence directory
- target workbook/source sheet and target `sheet_id`
- whether full matrix comparison passed
- any remaining hardening follow-ups

**Step 5: Commit**

```bash
git add docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md
git commit -m "docs: archive publish live verification results"
```
