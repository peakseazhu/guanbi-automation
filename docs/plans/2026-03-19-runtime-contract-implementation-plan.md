# Runtime Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为新项目建立运行前检查、轮询预算、阶段护栏、错误分类和结构化运行记录的统一运行契约基线，作为 extract-only 与后续 workbook 阶段的共同前置。

**Architecture:** 运行契约位于 `domain / application / execution / infrastructure` 的共享边界层，不属于单一 stage 实现。先用最小模型覆盖环境 doctor、extract polling 和 manifest 记录，再让 workbook/publish 继承相同契约，而不是各阶段各写一套规则。

**Tech Stack:** Python 3.12, Pydantic v2, httpx, pytest, PyYAML

---

### Task 1: Add runtime contract domain models

**Files:**
- Create: `guanbi_automation/domain/runtime_contract.py`
- Create: `guanbi_automation/domain/runtime_errors.py`
- Test: `tests/domain/test_runtime_contract.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.domain.runtime_contract import TimeoutBudget


def test_timeout_budget_requires_positive_values():
    budget = TimeoutBudget(
        connect_timeout=5.0,
        read_timeout=30.0,
        poll_interval=2.0,
        max_wait=300.0,
        max_retries=4,
    )
    assert budget.max_wait > budget.poll_interval
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_runtime_contract.py -v`
Expected: FAIL because the runtime contract models do not exist yet.

**Step 3: Write minimal implementation**

Implement minimal models for:

- `TimeoutBudget`
- `RetryBudget`
- `PollingPolicy`
- `StageGateDecision`
- `RuntimeErrorInfo`
- `EventRecord`

**Step 4: Add validation rules**

At minimum validate:

- all timeouts are positive
- `max_wait` is greater than `poll_interval`
- retry counts are non-negative
- `StageGateDecision` only allows `ready / blocked / degraded`

**Step 5: Run test to verify it passes**

Run: `pytest tests/domain/test_runtime_contract.py -v`
Expected: PASS.

### Task 2: Build the environment doctor service

**Files:**
- Create: `guanbi_automation/application/doctor_service.py`
- Create: `guanbi_automation/bootstrap/dependency_manifest.py`
- Test: `tests/application/test_doctor_service.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.application.doctor_service import run_doctor


def test_doctor_reports_missing_env_var(tmp_path):
    report = run_doctor(
        required_env_vars=["GUANBI_USERNAME"],
        required_paths=[tmp_path],
        import_checks=["json"],
    )
    assert any(item.status == "failed" for item in report.checks)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_doctor_service.py -v`
Expected: FAIL because the doctor service does not exist yet.

**Step 3: Write minimal implementation**

Implement a doctor service that checks:

- Python version
- required imports
- required environment variables
- required writable paths
- dependency manifest availability

**Step 4: Return structured results**

Return a `DoctorReport` object instead of console strings, with:

- overall status
- check list
- failing item count

**Step 5: Run test to verify it passes**

Run: `pytest tests/application/test_doctor_service.py -v`
Expected: PASS.

### Task 3: Build polling policy and network error mapping

**Files:**
- Modify: `guanbi_automation/infrastructure/guanbi/client.py`
- Create: `guanbi_automation/infrastructure/guanbi/polling.py`
- Test: `tests/infrastructure/guanbi/test_polling_policy.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.infrastructure.guanbi.polling import should_retry_poll_error


def test_ssl_error_is_retryable():
    assert should_retry_poll_error("network_ssl_error") is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/infrastructure/guanbi/test_polling_policy.py -v`
Expected: FAIL because the polling policy helpers do not exist yet.

**Step 3: Write minimal implementation**

Implement helpers that:

- classify poll errors
- decide retryability
- compute next wait interval
- stop when `max_wait` or `max_retries` is exhausted

**Step 4: Integrate policy into the Guanyuan client**

Replace any open-ended polling loop with explicit policy-driven polling.

**Step 5: Run test to verify it passes**

Run: `pytest tests/infrastructure/guanbi/test_polling_policy.py -v`
Expected: PASS.

### Task 4: Build structured event and manifest recording helpers

**Files:**
- Modify: `guanbi_automation/execution/manifest_builder.py`
- Create: `guanbi_automation/execution/event_recorder.py`
- Test: `tests/execution/test_event_recorder.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.execution.event_recorder import build_event_record


def test_event_record_contains_runtime_identifiers():
    event = build_event_record(
        batch_id="batch-001",
        stage_name="extract",
        event_type="poll_retry",
    )
    assert event.batch_id == "batch-001"
    assert event.stage_name == "extract"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/execution/test_event_recorder.py -v`
Expected: FAIL because the event recording helpers do not exist yet.

**Step 3: Write minimal implementation**

Implement helpers that persist structured runtime fields for:

- batch
- job
- extract
- stage
- chart
- task
- error code
- attempt

**Step 4: Wire the manifest builder**

Ensure batch and extract manifests can include runtime policy and final error summaries.

**Step 5: Run test to verify it passes**

Run: `pytest tests/execution/test_event_recorder.py -v`
Expected: PASS.

### Task 5: Add stage gate evaluation for extract and workbook prerequisites

**Files:**
- Modify: `guanbi_automation/application/preflight_service.py`
- Create: `guanbi_automation/execution/stage_gates.py`
- Test: `tests/execution/test_stage_gates.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.execution.stage_gates import evaluate_workbook_gate


def test_workbook_gate_blocks_when_cell_count_exceeds_limit():
    decision = evaluate_workbook_gate(
        row_count=70000,
        column_count=220,
        cell_limit=5000000,
    )
    assert decision.status == "blocked"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/execution/test_stage_gates.py -v`
Expected: FAIL because stage gate evaluation does not exist yet.

**Step 3: Write minimal implementation**

Implement stage gates for:

- extract policy completeness
- workbook template existence
- workbook size guardrails
- publish target readiness

**Step 4: Integrate preflight and runtime evaluation**

Static checks stay in preflight; data-dependent checks run immediately before the target stage.

**Step 5: Run test to verify it passes**

Run: `pytest tests/execution/test_stage_gates.py -v`
Expected: PASS.

### Task 6: Update the extract stage to emit policy-aware runtime evidence

**Files:**
- Modify: `guanbi_automation/execution/stages/extract.py`
- Modify: `guanbi_automation/execution/pipeline_engine.py`
- Test: `tests/execution/test_extract_stage.py`

**Step 1: Write the failing test**

```python
def test_extract_manifest_records_poll_attempts(extract_stage, planned_extract_run):
    result = extract_stage.run(planned_extract_run)
    assert result.manifest.poll_attempts >= 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/execution/test_extract_stage.py -v`
Expected: FAIL because the extract stage does not yet emit runtime policy evidence.

**Step 3: Write minimal implementation**

Update the extract stage so it records:

- timeout budget
- retry count
- total wait seconds
- final network or polling error

**Step 4: Add a failure-path assertion**

At least one test must assert that a polling timeout produces a stable error code and a failed manifest entry.

**Step 5: Run test to verify it passes**

Run: `pytest tests/execution/test_extract_stage.py -v`
Expected: PASS.

### Task 7: Document and wire the runtime contract into the project bootstrap

**Files:**
- Modify: `guanbi_automation/bootstrap/container.py`
- Modify: `guanbi_automation/bootstrap/settings.py`
- Modify: `README.md`
- Test: `tests/bootstrap/test_settings.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.bootstrap.settings import RuntimePolicySettings


def test_runtime_policy_settings_have_defaults():
    settings = RuntimePolicySettings()
    assert settings.extract_polling.max_retries >= 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/bootstrap/test_settings.py -v`
Expected: FAIL because runtime policy settings are not defined yet.

**Step 3: Write minimal implementation**

Expose runtime policy settings through bootstrap configuration so application and execution layers read from one source.

**Step 4: Update documentation**

Document:

- required doctor checks
- polling policy settings
- stage gate responsibilities

**Step 5: Run test to verify it passes**

Run: `pytest tests/bootstrap/test_settings.py -v`
Expected: PASS.

## Execution Notes

- Implement every task with `@superpowers:test-driven-development`.
- Any unexpected runtime failure must first use `@superpowers:systematic-debugging` before changing code.
- Before claiming any task complete, use `@superpowers:verification-before-completion`.
- Do not begin workbook writer-engine implementation until this runtime contract baseline is merged into the new project shell.
- The legacy `src/` tree remains reference-only.
