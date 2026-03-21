# 2026-03-21 会话归档（Extract Runtime Policy Task 1-3）

## 1. 本次范围

本次会话严格沿用既定顺序：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

没有回到 workbook 讨论，没有回到 legacy `src/`，也没有把策略退回单一 `extract_polling`。

本次实际完成 `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md` 的前 3 个任务：

1. Task 1：将扁平 `extract_polling` 升级为 profile-aware runtime policy settings
2. Task 2：新增 template default + run override 的 runtime profile 解析器
3. Task 3：修正 poll 语义，使 `processing` 不消耗错误重试预算

## 2. 代码落地

### 2.1 Task 1

新增/调整：

- `guanbi_automation/domain/runtime_contract.py`
  - 新增 `ExtractRuntimeProfileName`
  - 新增 `RequestBudget`
  - 新增 `PollBudget`
  - 新增 `ExtractRuntimePolicy`
- `guanbi_automation/bootstrap/settings.py`
  - 用 `extract.default_profile + extract.profiles[...]` 取代扁平 `extract_polling`
  - 按设计文档写入 `fast / standard / heavy` 三档默认预算
- `tests/domain/test_runtime_contract.py`
- `tests/bootstrap/test_settings.py`

### 2.2 Task 2

新增：

- `guanbi_automation/application/runtime_policy_service.py`
  - 提供 `resolve_extract_runtime_policy(...)`
  - 解析规则为 `override > template default`
  - 未知 profile 返回稳定错误
- `tests/application/test_runtime_policy_service.py`

### 2.3 Task 3

调整：

- `guanbi_automation/infrastructure/guanbi/polling.py`
  - 新增 `classify_poll_status(...)`
  - 新增 `compute_processing_wait_interval(...)`
- `guanbi_automation/infrastructure/guanbi/client.py`
  - `task_status=processing` 时继续轮询
  - `task_status=done` 时才完成
  - 正常轮询不消耗 transient retry 预算
  - 预算耗尽时稳定落到 `poll_timeout`
- `tests/infrastructure/guanbi/test_polling_policy.py`

## 3. 验证证据

本次会话确认普通 shell 下的 `pytest` 调用会因为环境特性表现异常；恢复沿用上一阶段已验证可用的测试入口：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest ... -p no:cacheprovider
```

本批次最终合并验证命令：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest `
  tests/domain/test_runtime_contract.py `
  tests/bootstrap/test_settings.py `
  tests/application/test_runtime_policy_service.py `
  tests/infrastructure/guanbi/test_polling_policy.py `
  -v -p no:cacheprovider
```

结果：

- `18 passed in 0.41s`

## 4. 本次未改动的权威文档

以下权威文档本次未改动，因为当前实现没有推翻已批准设计：

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/plans/2026-03-20-extract-runtime-policy-design.md`
- `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`

## 5. 当前恢复点

下次继续时，直接从 `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md` 的 Task 4 开始：

1. 新增 `submit / download` 的 request-budget helper
2. 再进入 Task 5 的 extract stage 分段执行与 manifest 证据
3. 然后再做 Task 6 的 preflight / stage gate / README

当前批次代码与本会话归档已提交：

- 提交：`6fdd989`
- 提交信息：`feat: implement extract runtime policy tasks 1-3`

当前 `git status` 仍显示 `tools/` 为未跟踪目录，未纳入本批次实现范围。
