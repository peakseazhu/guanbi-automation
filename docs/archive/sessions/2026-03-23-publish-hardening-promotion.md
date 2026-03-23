# 2026-03-23 会话归档（Publish Hardening Promotion）

## 当前结论

- `publish-hardening-promotion` 已将验证线中的 `publish hardening bundle v1` 萃取为干净的 mainline selective promotion 载体。
- 本次 promotion 只提升主线 publish runtime 已实际消费的 hardening slice，不混入 live verification scaffold。
- promotion 依据仍回溯到验证线的首个有效 evidence archive：`.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`，其中 `comparison.json` 已确认 `matches = true`，并证明真实样本是 `58 x 127` 宽表。
- 当前远端分支已推送：`origin/publish-hardening-promotion`
- 当前 clean PR 已创建：
  - `https://github.com/peakseazhu/guanbi-automation/pull/2`

## Promotion Scope

本次进入 mainline promotion 的内容为：

- `PublishSettings.chunk_column_limit=100`
- row/column-aware `plan_range_segments(...)`
- single-range fallback inference
- concrete `publish_writer`
- 单 segment `write_values(...)` / 多 segment `values_batch_update(...)`
- batch-aware `PUBLISH_RANGE_INVALID`
- mapping manifest `segment_count / segment_write_mode / write_segments`
- 对应 regression tests

具体代码切片保持在以下运行时代码与测试范围：

- `guanbi_automation/bootstrap/settings.py`
- `guanbi_automation/execution/stages/publish.py`
- `guanbi_automation/infrastructure/feishu/__init__.py`
- `guanbi_automation/infrastructure/feishu/client.py`
- `guanbi_automation/infrastructure/feishu/publish_writer.py`
- `guanbi_automation/infrastructure/feishu/target_planner.py`
- `tests/bootstrap/test_settings.py`
- `tests/execution/test_publish_stage.py`
- `tests/infrastructure/feishu/test_client.py`
- `tests/infrastructure/feishu/test_publish_writer.py`
- `tests/infrastructure/feishu/test_target_planner.py`

## Explicit Exclusions

本次明确不进入主线的内容为：

- `fetch_tenant_access_token`
- `read_values`
- `PUBLISH_READBACK_MISMATCH`
- live verification spec / service / entrypoint
- `config/live_verification/publish/real_sample.local.yaml`
- `runs/live_verification/publish/20260323T022511Z`
- 任何真实 spreadsheet token、target sheet 标识与 readback / comparison runtime

原因是：

- 这些内容仍然服务真实样本写入、读回、comparison 与证据归档
- 当前主线 publish runtime 还没有 readback/comparison 的正式消费者
- promotion 必须保持“foundation runtime”与“verification asset”分层

## Promotion Provenance

本次 promotion 直接回溯到以下验证线证据与归档：

- evidence archive：`.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`
- live verification implementation archive：`.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
- publish hardening implementation archive：`.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-23-publish-hardening-implementation.md`

验证线 `publish hardening bundle v1` 的实现来源为：

- `f268f66 feat: add publish hardening manifest surface`
- `18d37da fix: infer single-range publish segments`
- `b7ceea4 feat: add publish hardening writer`
- `b1bca69 docs: archive publish hardening implementation`

## 自动化验证

### Promotion Branch Focused Verification

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-hardening-promotion;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/bootstrap/test_settings.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

结果：

- `33 passed`

### Promotion Branch Full Suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-hardening-promotion;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `98 passed`

### Validation Branch Full Suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `110 passed`

## 关键边界

- `client.py` 只保留 hardening 所需的 `write_values_batch(...)`、JSON headers 与 batch-aware range error mapping；不整体替换为验证线版本。
- `publish_source_reader` 继续保持主线已有的 streaming-safe 实现，不因本次 promotion 再次改写。
- `partial_write` 的语义仍然只表达 runtime 已确认的请求级部分写入；单次 `values_batch_update(...)` 失败不误报为 `partial_write=True`。

## 当前恢复点

- worktree：`D:\get_bi_data__1\.worktrees\publish-hardening-promotion`
- branch：`publish-hardening-promotion`
- commit：`82374e8 feat: promote publish hardening bundle`
- PR：`https://github.com/peakseazhu/guanbi-automation/pull/2`
- 当前工作应继续保持 selective promotion 边界，避免把验证线 `client.py` / `test_client.py` 整体覆盖进来
- 下一恢复点固定为：
  1. 对 PR #2 做 merge 前代码审查
  2. 若审查通过，则合并到 `main`
  3. 合并后同步本地 `main`、清理 promotion worktree，并更新主线恢复点
