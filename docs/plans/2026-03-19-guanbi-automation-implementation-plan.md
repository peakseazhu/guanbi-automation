> 2026-03-19 规划治理更新：`docs/plans/master-implementation-roadmap.md` 与 `docs/plans/2026-03-19-from-scratch-guanbi-automation-implementation-plan.md` 已成为当前实施标准；本文保留为旧阶段性计划快照。
> 2026-03-19 项目边界更新：后续实现代码按“从 0 构建，legacy 仅作参考证据”执行。
# Guanyuan BI Automation Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local, stage-driven Guanyuan BI automation suite that can discover accessible pages, model filters, save reusable templates, download exports, and optionally process Excel and publish to Feishu.

**Architecture:** The system is a local web application backed by a Python service layer. Guanyuan discovery, template management, pipeline execution, Excel processing, and Feishu publishing are separated into explicit modules and standard stages so they can be enabled, disabled, reordered, and extended without rewriting the whole workflow.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, HTMX, Pydantic, requests/httpx, xlwings, openpyxl, lark_oapi, pytest

---

### Task 1: Establish the new application skeleton

**Files:**
- Create: `src/app/__init__.py`
- Create: `src/app/main.py`
- Create: `src/app/settings.py`
- Create: `src/app/routes/__init__.py`
- Create: `src/app/templates/.gitkeep`
- Create: `tests/test_app_imports.py`
- Modify: `requirements.txt`
- Modify: `environment.yml`

**Step 1: Write the failing test**

Create `tests/test_app_imports.py` with import checks for:

- `src.app.main`
- `src.app.settings`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_imports.py -v`
Expected: FAIL because the new modules do not exist yet.

**Step 3: Write minimal implementation**

Create the application package and a minimal FastAPI app factory in `src/app/main.py`.

**Step 4: Add runtime dependencies**

Update dependency files so the environment explicitly includes:

- `fastapi`
- `uvicorn`
- `jinja2`
- `httpx`
- `pydantic`
- `pytest`
- `numpy`
- `python-dateutil`

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_app_imports.py -v`
Expected: PASS.

### Task 2: Build Guanyuan authentication and raw API client

**Files:**
- Create: `src/app/guanbi/__init__.py`
- Create: `src/app/guanbi/auth.py`
- Create: `src/app/guanbi/client.py`
- Create: `src/app/guanbi/models.py`
- Test: `tests/guanbi/test_auth_models.py`

**Step 1: Write the failing test**

Create tests for:

- loading credentials from environment
- building authenticated headers from `uIdToken`
- parsing both wrapped and unwrapped API payloads

**Step 2: Run test to verify it fails**

Run: `pytest tests/guanbi/test_auth_models.py -v`
Expected: FAIL because the client and models do not exist yet.

**Step 3: Write minimal implementation**

Implement:

- login request wrapper
- authenticated session/header builder
- response normalization helper
- typed models for page tree and task status payloads

**Step 4: Run test to verify it passes**

Run: `pytest tests/guanbi/test_auth_models.py -v`
Expected: PASS.

### Task 3: Build discovery and page snapshot extraction

**Files:**
- Create: `src/app/guanbi/discovery.py`
- Create: `src/app/guanbi/snapshot.py`
- Create: `tests/guanbi/test_discovery_snapshot.py`
- Create: `tests/fixtures/guanbi/page_v3_wrapped.json`
- Create: `tests/fixtures/guanbi/page_v3_unwrapped.json`
- Create: `tests/fixtures/guanbi/page_detail_execution_review.json`

**Step 1: Write the failing test**

Cover:

- page tree parsing
- folder/page flattening
- PAGE and CUSTOM_REPORT support
- selector extraction
- chart extraction
- tab/panel mapping extraction

**Step 2: Run test to verify it fails**

Run: `pytest tests/guanbi/test_discovery_snapshot.py -v`
Expected: FAIL because the discovery layer does not exist yet.

**Step 3: Write minimal implementation**

Implement helpers that:

- fetch page tree
- fetch page detail
- normalize cards, selectors, charts, tabs, panels
- produce a stable page snapshot object for storage and UI rendering

**Step 4: Run test to verify it passes**

Run: `pytest tests/guanbi/test_discovery_snapshot.py -v`
Expected: PASS.

### Task 4: Build template, stage, and run models

**Files:**
- Create: `src/app/domain/__init__.py`
- Create: `src/app/domain/models.py`
- Create: `src/app/domain/template_store.py`
- Create: `tests/domain/test_template_models.py`

**Step 1: Write the failing test**

Cover:

- extract template model
- job model
- stage order validation
- default stage flags
- runtime override merge

**Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_template_models.py -v`
Expected: FAIL because the domain models do not exist yet.

**Step 3: Write minimal implementation**

Implement models for:

- page snapshot references
- selectors
- extracts
- jobs
- stages
- run context
- saved template persistence to local JSON files

**Step 4: Run test to verify it passes**

Run: `pytest tests/domain/test_template_models.py -v`
Expected: PASS.

### Task 5: Build the pipeline engine and stage registry

**Files:**
- Create: `src/app/pipeline/__init__.py`
- Create: `src/app/pipeline/engine.py`
- Create: `src/app/pipeline/registry.py`
- Create: `src/app/pipeline/models.py`
- Create: `tests/pipeline/test_engine.py`

**Step 1: Write the failing test**

Cover:

- stage ordering
- stage enable/disable logic
- runtime override behavior
- dependency validation
- stage result propagation

**Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_engine.py -v`
Expected: FAIL because the pipeline engine does not exist yet.

**Step 3: Write minimal implementation**

Implement:

- stage registry
- ordered stage execution
- per-stage result contract
- preflight validation entry point
- run manifest skeleton

**Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_engine.py -v`
Expected: PASS.

### Task 6: Implement built-in stages

**Files:**
- Create: `src/app/pipeline/stages/__init__.py`
- Create: `src/app/pipeline/stages/extract.py`
- Create: `src/app/pipeline/stages/workbook_ingest.py`
- Create: `src/app/pipeline/stages/workbook_transform.py`
- Create: `src/app/pipeline/stages/publish_feishu.py`
- Create: `tests/pipeline/test_built_in_stages.py`

**Step 1: Write the failing test**

Cover:

- extract stage output contract
- workbook ingest stage input validation
- workbook transform stage result shaping
- publish stage batch splitting

**Step 2: Run test to verify it fails**

Run: `pytest tests/pipeline/test_built_in_stages.py -v`
Expected: FAIL because the built-in stage implementations do not exist yet.

**Step 3: Write minimal implementation**

Implement first-pass built-in stages by:

- reusing the validated Guanyuan export flow
- wrapping existing Excel operations behind a new stage API
- wrapping Feishu upload/write behavior behind a new stage API
- avoiding direct calls from the web layer into legacy modules

**Step 4: Run test to verify it passes**

Run: `pytest tests/pipeline/test_built_in_stages.py -v`
Expected: PASS.

### Task 7: Build the local web interface

**Files:**
- Create: `src/app/routes/pages.py`
- Create: `src/app/routes/templates.py`
- Create: `src/app/routes/runs.py`
- Create: `src/app/templates/base.html`
- Create: `src/app/templates/index.html`
- Create: `src/app/templates/page_detail.html`
- Create: `src/app/templates/template_editor.html`
- Create: `src/app/templates/run_result.html`
- Create: `tests/web/test_routes.py`

**Step 1: Write the failing test**

Cover:

- home page loads
- page tree renders
- page detail route renders snapshot data
- template save route accepts valid payload
- run start route triggers pipeline engine

**Step 2: Run test to verify it fails**

Run: `pytest tests/web/test_routes.py -v`
Expected: FAIL because the routes and templates do not exist yet.

**Step 3: Write minimal implementation**

Implement the first version of the UI with:

- left resource tree
- center page detail
- right template/stage editor
- stage toggle UI
- run trigger UI

**Step 4: Run test to verify it passes**

Run: `pytest tests/web/test_routes.py -v`
Expected: PASS.

### Task 8: Add run archive, observability, and migration helpers

**Files:**
- Create: `src/app/runtime/__init__.py`
- Create: `src/app/runtime/archive.py`
- Create: `src/app/runtime/logging.py`
- Create: `src/app/migration/__init__.py`
- Create: `src/app/migration/legacy_import.py`
- Create: `tests/runtime/test_archive.py`

**Step 1: Write the failing test**

Cover:

- run manifest creation
- download/archive directory generation
- failure summary persistence
- import of legacy config samples into new template format

**Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_archive.py -v`
Expected: FAIL because archive and migration helpers do not exist yet.

**Step 3: Write minimal implementation**

Implement:

- stable run directory layout
- manifest writer
- stage log writer
- legacy config bootstrap importer for known chart/filter samples

**Step 4: Run test to verify it passes**

Run: `pytest tests/runtime/test_archive.py -v`
Expected: PASS.

### Task 9: End-to-end validation against the current BI environment

**Files:**
- Create: `tests/e2e/README.md`
- Create: `tests/e2e/test_manual_verification_checklist.md`
- Modify: `docs/plans/2026-03-19-guanbi-live-verification.md`

**Step 1: Write the manual validation checklist**

Include:

- login
- page tree refresh
- page detail rendering
- selector display
- extract-only run
- full pipeline run
- failed preflight run

**Step 2: Execute the checklist manually**

Run the local app and validate the checklist against the current Guanyuan environment.

**Step 3: Record outcomes**

Update the live verification doc with:

- what passed
- what failed
- what remains unresolved

**Step 4: Re-run targeted automated tests**

Run: `pytest tests -v`
Expected: all implemented test suites PASS.

## Execution Notes

- This workspace currently is not a git repository. Before execution, either initialize git or adopt an equivalent checkpoint strategy for safe iteration.
- The existing legacy modules should be treated as reference material, not as the target architecture.
- The first production milestone is:
  - page discovery
  - page detail rendering
  - template save
  - extract-only run
- Excel ingest, transform, and Feishu publish should follow once the first milestone is stable.

