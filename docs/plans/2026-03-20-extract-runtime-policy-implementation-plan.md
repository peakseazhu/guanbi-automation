# Extract Runtime Policy Implementation Plan

> 状态：Completed
> 完成日期：2026-03-21
> 验证结果：`pytest tests -v -p no:cacheprovider` -> `34 passed`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有 runtime contract 基线之上，为 extract 主链路落地 profile-aware 的 `submit / poll / download` 分段运行策略、阶段级证据记录与稳定错误归因。

**Architecture:** 保留 `RuntimePolicySettings` 作为单一 bootstrap 入口，但把当前扁平 `extract_polling` 升级为带 `fast / standard / heavy` profile 的嵌套结构。运行时先解析模板默认 profile 与运行时 override，再由 extract stage 调用 `submit -> poll -> download` 三段受控链路；正常 `PROCESSING` 轮询与瞬时网络错误重试在语义上分离，manifest 记录各阶段独立证据。

**Tech Stack:** Python 3.12, Pydantic v2, httpx, pytest

---

### Task 1: Replace flat extract polling settings with profile-aware runtime policy models

**Files:**
- Modify: `guanbi_automation/domain/runtime_contract.py`
- Modify: `guanbi_automation/bootstrap/settings.py`
- Test: `tests/domain/test_runtime_contract.py`
- Test: `tests/bootstrap/test_settings.py`

**Step 1: Write the failing tests**

```python
from guanbi_automation.bootstrap.settings import RuntimePolicySettings


def test_runtime_policy_settings_expose_default_extract_profile():
    settings = RuntimePolicySettings()
    assert settings.extract.default_profile == "standard"
    assert settings.extract.profiles["heavy"].poll.max_wait == 240.0
```

```python
from guanbi_automation.domain.runtime_contract import ExtractRuntimePolicy


def test_extract_runtime_policy_requires_submit_poll_download_and_deadline():
    policy = ExtractRuntimePolicy.model_validate(
        {
            "profile_name": "standard",
            "submit": {"connect_timeout": 3.0, "read_timeout": 10.0, "max_retries": 1},
            "poll": {
                "poll_interval": 2.0,
                "max_wait": 150.0,
                "transient_error_retries": 2,
                "backoff_policy": "fixed",
            },
            "download": {"connect_timeout": 5.0, "read_timeout": 30.0, "max_retries": 1},
            "total_deadline_seconds": 210.0,
        }
    )
    assert policy.profile_name == "standard"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/domain/test_runtime_contract.py tests/bootstrap/test_settings.py -v`
Expected: FAIL because the profile-aware models and settings do not exist yet.

**Step 3: Write the minimal implementation**

Implement profile-aware models for:

- `RequestBudget`
- `PollBudget`
- `ExtractRuntimePolicy`
- `ExtractRuntimeProfileName`
- nested bootstrap settings for:
  - `extract.default_profile`
  - `extract.profiles.fast`
  - `extract.profiles.standard`
  - `extract.profiles.heavy`

Keep `RuntimePolicySettings` as the bootstrap root object; remove the flat `extract_polling` setting once the new tests pass.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/domain/test_runtime_contract.py tests/bootstrap/test_settings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add guanbi_automation/domain/runtime_contract.py guanbi_automation/bootstrap/settings.py tests/domain/test_runtime_contract.py tests/bootstrap/test_settings.py
git commit -m "feat: add profile-aware extract runtime settings"
```

### Task 2: Add runtime profile resolution for template defaults and run overrides

**Files:**
- Create: `guanbi_automation/application/runtime_policy_service.py`
- Test: `tests/application/test_runtime_policy_service.py`

**Step 1: Write the failing test**

```python
from guanbi_automation.application.runtime_policy_service import resolve_extract_runtime_policy
from guanbi_automation.bootstrap.settings import RuntimePolicySettings


def test_runtime_profile_override_wins_over_template_default():
    settings = RuntimePolicySettings()
    policy = resolve_extract_runtime_policy(
        settings=settings,
        template_profile="heavy",
        override_profile="fast",
    )
    assert policy.profile_name == "fast"
    assert policy.poll.max_wait == 45.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_runtime_policy_service.py -v`
Expected: FAIL because the resolver does not exist yet.

**Step 3: Write the minimal implementation**

Implement a resolver that:

- accepts `RuntimePolicySettings`
- accepts `template_profile`
- accepts optional `override_profile`
- returns the effective `ExtractRuntimePolicy`
- blocks unknown profile names with a clear error

Prefer a small pure function; do not couple this to I/O or stage execution.

**Step 4: Run test to verify it passes**

Run: `pytest tests/application/test_runtime_policy_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add guanbi_automation/application/runtime_policy_service.py tests/application/test_runtime_policy_service.py
git commit -m "feat: resolve extract runtime profiles"
```

### Task 3: Fix poll semantics so PROCESSING does not count as a retry failure

**Files:**
- Modify: `guanbi_automation/infrastructure/guanbi/polling.py`
- Modify: `guanbi_automation/infrastructure/guanbi/client.py`
- Test: `tests/infrastructure/guanbi/test_polling_policy.py`

**Step 1: Write the failing tests**

```python
def test_processing_status_waits_without_consuming_error_retry_budget():
    payloads = iter(
        [
            {"task_status": "processing"},
            {"task_status": "processing"},
            {"task_status": "done", "download_token": "file-001"},
        ]
    )

    result = poll_with_policy(
        fetch_status=lambda: next(payloads),
        policy=_build_policy(max_wait=30.0, max_retries=1),
        sleep=lambda _seconds: None,
    )

    assert result.completed is True
    assert result.attempts == 3
```

```python
def test_processing_status_times_out_after_poll_budget_is_exhausted():
    result = poll_with_policy(
        fetch_status=lambda: {"task_status": "processing"},
        policy=_build_policy(max_wait=4.0, max_retries=1),
        sleep=lambda _seconds: None,
    )

    assert result.completed is False
    assert result.error.code == RuntimeErrorCode.POLL_TIMEOUT
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/infrastructure/guanbi/test_polling_policy.py -v`
Expected: FAIL because polling currently treats any payload as a completed result.

**Step 3: Write the minimal implementation**

Update polling semantics so that:

- `task_status=processing` keeps polling
- `task_status=done` completes polling
- normal processing loops do not consume transient network retry budget
- only transient network failures use retry logic
- `poll_timeout` is emitted when processing outlives `poll.max_wait`

Keep the implementation small and deterministic; do not introduce real sleeps in tests.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/infrastructure/guanbi/test_polling_policy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add guanbi_automation/infrastructure/guanbi/polling.py guanbi_automation/infrastructure/guanbi/client.py tests/infrastructure/guanbi/test_polling_policy.py
git commit -m "fix: align poll policy with processing semantics"
```

### Task 4: Add request-budget helpers for submit and download stages

**Files:**
- Create: `guanbi_automation/infrastructure/guanbi/request_policy.py`
- Test: `tests/infrastructure/guanbi/test_request_policy.py`

**Step 1: Write the failing tests**

```python
import httpx

from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.guanbi.request_policy import call_with_request_budget


def test_request_budget_retries_transient_network_errors_once():
    calls = 0

    def flaky_call():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectTimeout("timed out")
        return {"ok": True}

    result = call_with_request_budget(
        operation_name="submit",
        action=flaky_call,
        budget={"connect_timeout": 3.0, "read_timeout": 10.0, "max_retries": 1},
    )

    assert result.completed is True
    assert calls == 2
```

```python
def test_request_budget_returns_stable_error_for_non_retryable_failure():
    result = call_with_request_budget(
        operation_name="download",
        action=lambda: (_ for _ in ()).throw(ValueError("bad payload")),
        budget={"connect_timeout": 5.0, "read_timeout": 30.0, "max_retries": 1},
    )

    assert result.completed is False
    assert result.error.code == RuntimeErrorCode.REQUEST_SUBMIT_ERROR
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/infrastructure/guanbi/test_request_policy.py -v`
Expected: FAIL because the request-budget helper does not exist yet.

**Step 3: Write the minimal implementation**

Implement a helper that:

- executes a submit/download style callable under a request budget
- retries only transient network errors
- returns structured attempt counts and final error info
- never sleeps for long in tests

Keep stage-specific naming in the result object so later manifest code can distinguish submit from download evidence without guessing.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/infrastructure/guanbi/test_request_policy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add guanbi_automation/infrastructure/guanbi/request_policy.py tests/infrastructure/guanbi/test_request_policy.py
git commit -m "feat: add request budget helper for extract stages"
```

### Task 5: Refactor extract stage to execute submit -> poll -> download and record stage evidence

**Files:**
- Modify: `guanbi_automation/execution/manifest_builder.py`
- Modify: `guanbi_automation/execution/pipeline_engine.py`
- Modify: `guanbi_automation/execution/stages/extract.py`
- Test: `tests/execution/test_extract_stage.py`
- Test: `tests/execution/test_event_recorder.py`

**Step 1: Write the failing tests**

```python
def test_extract_manifest_records_effective_runtime_profile_and_stage_metrics():
    result = extract_stage.run(
        planned_extract_run(
            template_profile="heavy",
            effective_profile="fast",
        )
    )
    assert result.manifest["template_runtime_profile"] == "heavy"
    assert result.manifest["effective_runtime_profile"] == "fast"
    assert result.manifest["submit_attempts"] >= 1
    assert result.manifest["download_attempts"] >= 1
```

```python
def test_extract_manifest_uses_last_failed_stage_for_final_error():
    result = extract_stage.run(
        planned_extract_run_with_download_failure()
    )
    assert result.status == "failed"
    assert result.manifest["download_final_error"]["code"] == RuntimeErrorCode.NETWORK_SSL_ERROR
    assert result.manifest["final_error"]["code"] == RuntimeErrorCode.NETWORK_SSL_ERROR
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/execution/test_extract_stage.py tests/execution/test_event_recorder.py -v`
Expected: FAIL because the extract stage still models only polling and the manifest lacks segmented evidence.

**Step 3: Write the minimal implementation**

Update the extract pipeline so that:

- `PlannedExtractRun` carries:
  - resolved `ExtractRuntimePolicy`
  - `template_runtime_profile`
  - `effective_runtime_profile`
  - `submit_request`
  - `fetch_status`
  - `download_file`
- extract stage runs `submit -> poll -> download`
- manifest records stage-level attempts, elapsed seconds, final errors, total elapsed seconds, and deadline exhaustion
- final extract error is derived from the last failed stage

Keep the stage orchestration testable with pure callables. Do not introduce real HTTP integration in this task.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/execution/test_extract_stage.py tests/execution/test_event_recorder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add guanbi_automation/execution/manifest_builder.py guanbi_automation/execution/pipeline_engine.py guanbi_automation/execution/stages/extract.py tests/execution/test_extract_stage.py tests/execution/test_event_recorder.py
git commit -m "feat: record segmented extract runtime evidence"
```

### Task 6: Validate runtime profile inputs in preflight and refresh operator docs

**Files:**
- Modify: `guanbi_automation/application/preflight_service.py`
- Modify: `guanbi_automation/execution/stage_gates.py`
- Modify: `README.md`
- Test: `tests/execution/test_stage_gates.py`

**Step 1: Write the failing test**

```python
def test_extract_gate_blocks_unknown_runtime_profile():
    decision = evaluate_extract_gate(
        policy=None,
        profile_name="ultra",
        available_profiles={"fast", "standard", "heavy"},
    )
    assert decision.status == "blocked"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/execution/test_stage_gates.py -v`
Expected: FAIL because the extract gate does not validate runtime profiles yet.

**Step 3: Write the minimal implementation**

Update preflight / stage-gate behavior so extract checks:

- profile name is known
- resolved runtime policy is present
- total deadline is positive

Update `README.md` to document:

- the three runtime profiles
- default `standard` behavior
- template default vs run override
- stage-level manifest evidence

**Step 4: Run tests to verify they pass**

Run: `pytest tests/execution/test_stage_gates.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add guanbi_automation/application/preflight_service.py guanbi_automation/execution/stage_gates.py README.md tests/execution/test_stage_gates.py
git commit -m "docs: describe extract runtime profiles and gates"
```

### Task 7: Run focused verification and the full suite

**Files:**
- No code changes expected

**Step 1: Run focused verification for all affected areas**

Run:

```bash
pytest tests/domain/test_runtime_contract.py tests/bootstrap/test_settings.py tests/application/test_runtime_policy_service.py tests/infrastructure/guanbi/test_polling_policy.py tests/infrastructure/guanbi/test_request_policy.py tests/execution/test_extract_stage.py tests/execution/test_event_recorder.py tests/execution/test_stage_gates.py -v
```

Expected: PASS

**Step 2: Run the full suite**

Run:

```bash
pytest tests -v -p no:cacheprovider
```

Expected: PASS

**Step 3: Commit the final verified state**

```bash
git add .
git commit -m "feat: implement extract runtime policy profiles"
```

## Execution Notes

- Implement every task with `@superpowers:test-driven-development`.
- Any unexpected failure in runtime-policy or polling behavior must first use `@superpowers:systematic-debugging`.
- Before claiming the work complete, use `@superpowers:verification-before-completion`.
- Do not begin workbook design or workbook implementation during this plan.
- The legacy `src/` tree remains reference-only.
