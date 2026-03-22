# 2026-03-21 会话归档（Extract Runtime Policy Task 4-6）

## 1. 本次范围

本次会话继续严格执行：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

未回到 workbook 讨论，未回到 legacy `src/`，也未改回单一 `extract_polling`。

本次完成 `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md` 的 Task 4-6：

1. Task 4：新增 `submit / download` 的 request-budget helper
2. Task 5：让 extract stage 真正执行 `submit -> poll -> download`，并记录分段 manifest 证据
3. Task 6：为 extract gate 增加 runtime profile 校验，并同步 README

## 2. 代码落地

### 2.1 Task 4

新增：

- `guanbi_automation/infrastructure/guanbi/request_policy.py`
  - 提供 `call_with_request_budget(...)`
  - 只对瞬时网络错误做有限重试
  - 返回稳定的请求阶段结果对象
- `tests/infrastructure/guanbi/test_request_policy.py`

### 2.2 Task 5

调整：

- `guanbi_automation/infrastructure/guanbi/client.py`
  - `PollResult` 新增 `elapsed_seconds`
- `guanbi_automation/execution/manifest_builder.py`
  - extract manifest 支持 `template/effective profile`
  - 支持 `submit_* / poll_* / download_*`
  - 支持 `extract_total_elapsed_seconds`、`deadline_exhausted`
- `guanbi_automation/execution/stages/extract.py`
  - `PlannedExtractRun` 升级为携带 resolved `ExtractRuntimePolicy`
  - extract stage 改为执行 `submit -> poll -> download`
  - final error 由最后失败阶段归因
- `tests/execution/test_extract_stage.py`
- `tests/execution/test_event_recorder.py`

### 2.3 Task 6

调整：

- `guanbi_automation/execution/stage_gates.py`
  - extract gate 校验 profile 是否存在
  - 校验 resolved policy 是否存在
  - 校验 `total_deadline_seconds` 为正值
- `guanbi_automation/application/preflight_service.py`
  - 透传 `profile_name` 与 `available_profiles`
- `README.md`
  - 说明 `fast / standard / heavy`
  - 说明默认 `standard`
  - 说明 `override > template default`
  - 说明 extract manifest 的分段证据
- `tests/execution/test_stage_gates.py`

## 3. 验证证据

本批次继续沿用已验证可用的测试入口：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest ... -p no:cacheprovider
```

本批次最终聚焦验证命令：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest `
  tests/domain/test_runtime_contract.py `
  tests/bootstrap/test_settings.py `
  tests/application/test_runtime_policy_service.py `
  tests/infrastructure/guanbi/test_polling_policy.py `
  tests/infrastructure/guanbi/test_request_policy.py `
  tests/execution/test_extract_stage.py `
  tests/execution/test_event_recorder.py `
  tests/execution/test_stage_gates.py `
  -v -p no:cacheprovider
```

结果：

- `32 passed in 0.52s`

## 4. 本次未更新的权威文档

以下权威文档本次未改动，因为当前实现没有推翻既定设计与顺序：

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/plans/2026-03-20-extract-runtime-policy-design.md`
- `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`

## 5. 当前恢复点

下次继续时，直接进入：

1. `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`
2. 从 Task 7 开始
3. 先跑 focused verification
4. 再跑 full suite

当前仍未进入 workbook 设计或 workbook 实现。
