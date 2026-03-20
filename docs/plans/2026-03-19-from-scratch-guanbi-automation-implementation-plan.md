# From-Scratch Guanyuan Automation Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从 0 构建一个本地运行、可视化、支持多任务批次执行的观远 BI 自动化套件，先完成 extract-only 批次里程碑，再逐步接入 Excel 与飞书阶段。

**Architecture:** 新项目使用独立代码根 `guanbi_automation/`，采用 `bootstrap / domain / application / execution / infrastructure / web` 分层结构，不依赖 legacy `src/`。配置、模板、快照、运行批次和归档全部显式建模；Web 控制台负责浏览、编排和触发，真正的副作用由 execution 与 infrastructure 层执行。

**Tech Stack:** Python 3.12, FastAPI, Jinja2, HTMX, Pydantic v2, httpx, PyYAML, openpyxl, xlwings, lark_oapi, pytest

---

### Task 1: Bootstrap the clean layered project shell

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `guanbi_automation/__init__.py`
- Create: `guanbi_automation/main.py`
- Create: `guanbi_automation/bootstrap/__init__.py`
- Create: `guanbi_automation/domain/__init__.py`
- Create: `guanbi_automation/application/__init__.py`
- Create: `guanbi_automation/execution/__init__.py`
- Create: `guanbi_automation/infrastructure/__init__.py`
- Create: `guanbi_automation/web/__init__.py`
- Create: `tests/test_package_import.py`

**Step 1: Write the failing test**

```python
from importlib import import_module


def test_layered_package_imports():
    assert import_module("guanbi_automation")
    assert import_module("guanbi_automation.main")
    assert import_module("guanbi_automation.bootstrap")
    assert import_module("guanbi_automation.domain")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_package_import.py -v`
Expected: FAIL because the package shell does not exist yet.

**Step 3: Write minimal implementation**

```python
# guanbi_automation/main.py

def create_app() -> dict:
    return {"name": "guanbi-automation"}
```

**Step 4: Add the project manifest**

Create `pyproject.toml` with the project name, Python version, runtime dependencies, and pytest configuration.

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_package_import.py -v`
Expected: PASS.

### Task 2: Build settings, logging, and filesystem roots

**Files:**
- Create: `config/project.example.yaml`
- Create: `guanbi_automation/bootstrap/settings.py`
- Create: `guanbi_automation/bootstrap/logging.py`
- Create: `guanbi_automation/domain/project.py`
- Create: `tests/bootstrap/test_settings.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.domain.project import ProjectConfig


def test_project_config_defaults():
    cfg = ProjectConfig.model_validate({"timezone": "Asia/Shanghai"})
    assert cfg.timezone == "Asia/Shanghai"
    assert cfg.runs_dir == "runs"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/bootstrap/test_settings.py -v`
Expected: FAIL because settings models do not exist yet.

**Step 3: Write minimal implementation**

Implement `ProjectConfig` and a settings loader that can read `config/project.yaml`, apply environment overrides, and normalize paths.

**Step 4: Add logging bootstrap**

Implement UTF-8 logging setup with file and console handlers so future manifests and stage logs share one consistent format.

**Step 5: Run test to verify it passes**

Run: `pytest tests/bootstrap/test_settings.py -v`
Expected: PASS.

### Task 3: Build storage repositories and batch archive layout

**Files:**
- Create: `templates/extracts/.gitkeep`
- Create: `templates/jobs/.gitkeep`
- Create: `snapshots/pages/.gitkeep`
- Create: `runs/.gitkeep`
- Create: `guanbi_automation/infrastructure/storage/template_repository.py`
- Create: `guanbi_automation/infrastructure/storage/snapshot_repository.py`
- Create: `guanbi_automation/infrastructure/storage/run_repository.py`
- Create: `tests/infrastructure/storage/test_run_repository.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from guanbi_automation.infrastructure.storage.run_repository import create_batch_layout


def test_create_batch_layout(tmp_path: Path):
    batch_dir = create_batch_layout(tmp_path, batch_id="batch-001")
    assert (batch_dir / "extracts").exists()
    assert (batch_dir / "jobs").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/infrastructure/storage/test_run_repository.py -v`
Expected: FAIL because the repository helpers do not exist yet.

**Step 3: Write minimal implementation**

Implement repositories that can persist:

- extract templates as YAML
- job templates as YAML
- page snapshots as JSON
- batch/job/extract manifests as JSON

**Step 4: Enforce the batch archive layout**

The run repository must create:

- `batch-manifest.json`
- `logs/`
- `extracts/<extract_run_id>/`
- `jobs/<job_run_id>/`

**Step 5: Run test to verify it passes**

Run: `pytest tests/infrastructure/storage/test_run_repository.py -v`
Expected: PASS.

### Task 4: Build Guanyuan authentication and normalized API client

**Files:**
- Create: `guanbi_automation/infrastructure/guanbi/auth.py`
- Create: `guanbi_automation/infrastructure/guanbi/client.py`
- Create: `guanbi_automation/infrastructure/guanbi/models.py`
- Create: `tests/infrastructure/guanbi/test_auth_client.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.infrastructure.guanbi.models import normalize_payload


def test_normalize_payload_accepts_wrapped_response():
    payload = {"result": "ok", "response": {"status": "FINISHED"}}
    assert normalize_payload(payload)["status"] == "FINISHED"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/infrastructure/guanbi/test_auth_client.py -v`
Expected: FAIL because the Guanyuan client layer does not exist yet.

**Step 3: Write minimal implementation**

Implement:

- sign-in request wrapper
- token and cookie header builder
- payload normalization
- timeout and retry policy for task polling
- typed task status model

**Step 4: Add error mapping**

Normalize login failure, export submit failure, polling timeout, download failure, and malformed payload into explicit client exceptions.

**Step 5: Run test to verify it passes**

Run: `pytest tests/infrastructure/guanbi/test_auth_client.py -v`
Expected: PASS.

### Task 5: Build discovery services and page snapshots

**Files:**
- Create: `guanbi_automation/domain/page_snapshot.py`
- Create: `guanbi_automation/application/discovery_service.py`
- Create: `tests/application/test_discovery_service.py`
- Create: `tests/fixtures/guanbi/page_tree_sample.json`
- Create: `tests/fixtures/guanbi/page_detail_sample.json`

**Step 1: Write the failing test**

```python
from guanbi_automation.application.discovery_service import flatten_pages


def test_flatten_pages_returns_pages(page_tree_fixture):
    result = flatten_pages(page_tree_fixture)
    assert any(node.resource_type == "PAGE" for node in result)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_discovery_service.py -v`
Expected: FAIL because discovery parsing does not exist yet.

**Step 3: Write minimal implementation**

Implement helpers that can:

- flatten page trees
- extract cards, selectors, tabs, panels, and dataset metadata
- produce a stable `PageSnapshot` object for storage and UI rendering

**Step 4: Save snapshot examples**

Use fixture files derived from verified samples in `记录/` so the tests are driven by real payload shapes.

**Step 5: Run test to verify it passes**

Run: `pytest tests/application/test_discovery_service.py -v`
Expected: PASS.

### Task 6: Build extract, job, and run batch models

**Files:**
- Create: `guanbi_automation/domain/extract_template.py`
- Create: `guanbi_automation/domain/job_template.py`
- Create: `guanbi_automation/domain/run_batch.py`
- Create: `tests/domain/test_templates.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.domain.job_template import JobTemplate


def test_job_template_defaults_to_extract_only():
    job = JobTemplate.model_validate({"job_id": "daily-run", "extract_refs": ["core"]})
    assert job.stages[0].name == "extract"
    assert job.stages[0].enabled is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_templates.py -v`
Expected: FAIL because the template models do not exist yet.

**Step 3: Write minimal implementation**

Implement models for:

- selector rules
- extract template
- job template
- stage config
- run batch
- extract run
- job run

**Step 4: Add validation rules**

At minimum validate:

- extract references are resolvable
- stage dependency ordering is legal
- batch selection contains at least one job
- duplicate extract IDs are rejected at repository level

**Step 5: Run test to verify it passes**

Run: `pytest tests/domain/test_templates.py -v`
Expected: PASS.

### Task 7: Build the run planner and preflight service

**Files:**
- Create: `guanbi_automation/execution/run_planner.py`
- Create: `guanbi_automation/application/preflight_service.py`
- Create: `tests/execution/test_run_planner.py`
- Create: `tests/application/test_preflight_service.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.execution.run_planner import build_extract_signature


def test_extract_signature_changes_when_filters_change():
    left = build_extract_signature(chart_id="c1", normalized_filters={"date": ["2026-03-18"]})
    right = build_extract_signature(chart_id="c1", normalized_filters={"date": ["2026-03-19"]})
    assert left != right
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/execution/test_run_planner.py tests/application/test_preflight_service.py -v`
Expected: FAIL because the planner and preflight services do not exist yet.

**Step 3: Write minimal implementation**

Implement `run planner` so it can:

- load selected jobs
- expand all referenced extracts
- render dynamic rules into real filter values
- compute extract signatures
- dedupe equivalent extracts within a batch
- produce a `RunBatchPlan`

**Step 4: Add preflight validation**

Preflight must at minimum check:

- BI credentials presence
- template references are resolvable
- stage dependency ordering is valid
- workbook targets exist when workbook stages are enabled
- Feishu targets exist when publish is enabled

**Step 5: Run tests to verify they pass**

Run: `pytest tests/execution/test_run_planner.py tests/application/test_preflight_service.py -v`
Expected: PASS.

### Task 8: Build the pipeline engine and extract-only batch execution

**Files:**
- Create: `guanbi_automation/execution/pipeline_engine.py`
- Create: `guanbi_automation/execution/manifest_builder.py`
- Create: `guanbi_automation/execution/stages/__init__.py`
- Create: `guanbi_automation/execution/stages/extract.py`
- Create: `tests/execution/test_pipeline_engine.py`
- Create: `tests/execution/test_extract_stage.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.execution.pipeline_engine import PipelineEngine


def test_pipeline_runs_unique_extracts_before_job_stages(planned_batch):
    engine = PipelineEngine()
    result = engine.run(planned_batch)
    assert result.extract_count == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/execution/test_pipeline_engine.py tests/execution/test_extract_stage.py -v`
Expected: FAIL because the execution engine does not exist yet.

**Step 3: Write minimal implementation**

Implement:

- ordered stage execution
- batch/job/extract manifest writing
- extract stage that renders filters, submits export, polls task state, downloads file, and records metadata

**Step 4: Add failure-path assertions**

At least one test must verify that a polling timeout or failed export leaves a failed batch manifest with an explicit stage error.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/execution/test_pipeline_engine.py tests/execution/test_extract_stage.py -v`
Expected: PASS.

### Task 9: Build the local web console for discovery, extract editing, and job composition

**Files:**
- Create: `guanbi_automation/web/app.py`
- Create: `guanbi_automation/web/routes/home.py`
- Create: `guanbi_automation/web/routes/pages.py`
- Create: `guanbi_automation/web/routes/extracts.py`
- Create: `guanbi_automation/web/routes/jobs.py`
- Create: `guanbi_automation/web/routes/runs.py`
- Create: `guanbi_automation/web/templates/base.html`
- Create: `guanbi_automation/web/templates/index.html`
- Create: `guanbi_automation/web/templates/page_detail.html`
- Create: `guanbi_automation/web/templates/extract_editor.html`
- Create: `guanbi_automation/web/templates/job_builder.html`
- Create: `guanbi_automation/web/templates/run_center.html`
- Create: `guanbi_automation/web/templates/archive_view.html`
- Create: `tests/web/test_routes.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from guanbi_automation.web.app import create_web_app


def test_home_page_loads():
    client = TestClient(create_web_app())
    response = client.get("/")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_routes.py -v`
Expected: FAIL because the web application does not exist yet.

**Step 3: Write minimal implementation**

Implement the first working UI with:

- 资源浏览区
- 抽取配置区
- 任务编排区
- 运行中心
- 归档查看区

**Step 4: Wire the services through dependency injection**

The web layer must call application services and execution orchestration, not raw infrastructure clients directly.

**Step 5: Run test to verify it passes**

Run: `pytest tests/web/test_routes.py -v`
Expected: PASS.

### Task 10: Build workbook and publish stages plus end-to-end verification pack

**Files:**
- Create: `guanbi_automation/infrastructure/excel/reader.py`
- Create: `guanbi_automation/infrastructure/excel/writer.py`
- Create: `guanbi_automation/infrastructure/feishu/client.py`
- Create: `guanbi_automation/execution/stages/workbook_ingest.py`
- Create: `guanbi_automation/execution/stages/workbook_transform.py`
- Create: `guanbi_automation/execution/stages/publish.py`
- Create: `tests/infrastructure/excel/test_writer.py`
- Create: `tests/infrastructure/feishu/test_client.py`
- Create: `tests/execution/test_workbook_and_publish_stages.py`
- Create: `tests/e2e/test_manual_verification_checklist.md`

**Step 1: Write the failing tests**

```python
from guanbi_automation.execution.stages.publish import batch_rows


def test_batch_rows_splits_large_payload():
    data = [[i] for i in range(12001)]
    assert len(batch_rows(data, batch_size=5000)) == 3
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/infrastructure/excel/test_writer.py tests/infrastructure/feishu/test_client.py tests/execution/test_workbook_and_publish_stages.py -v`
Expected: FAIL because workbook and publish adapters do not exist yet.

**Step 3: Write minimal implementation**

Implement workbook and publish stages so they can:

- write extract output to target workbook
- trigger recalculation when required
- read configured output ranges
- emit a normalized dataset for publish
- fetch Feishu sheet metadata
- batch-write row payloads and store publish summaries

**Step 4: Build the manual verification checklist**

Record the exact operator checklist for:

- page refresh
- page detail rendering
- extract save
- job save
- extract-only batch run
- workbook run
- publish run
- failed preflight run

**Step 5: Run tests to verify they pass**

Run: `pytest tests/infrastructure/excel/test_writer.py tests/infrastructure/feishu/test_client.py tests/execution/test_workbook_and_publish_stages.py -v`
Expected: PASS.

## Execution Notes

- Implement every task with `@superpowers:test-driven-development`.
- Any unexpected runtime failure must first use `@superpowers:systematic-debugging` before changing code.
- Before claiming any milestone complete, use `@superpowers:verification-before-completion`.
- The legacy `src/` tree is reference-only and must not be imported into the new codebase.
- The first production milestone is extract-only batch execution; workbook and publish work starts only after that milestone is verified.
