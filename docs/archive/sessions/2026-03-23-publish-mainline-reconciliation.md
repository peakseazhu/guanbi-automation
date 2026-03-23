# 2026-03-23 会话归档（Publish Mainline Reconciliation）

## 当前结论

- PR #2 合入后的主线审计已确认：`main` 当前并不存在非测试 `PublishStage` runtime wiring，`publish_writer` 仍未被主流程 builder / bootstrap / entrypoint 实际消费。
- 因此主线状态已从“`publish foundation + publish hardening bundle v1`”纠偏为“`publish foundation + publish hardening primitives`”。
- 同时已修复 `write_publish_target(...)` 的显式矩形边界语义：当 resolved target 比 dataset 更大时，writer 会按完整显式矩形写入，并用空串补齐剩余单元格，避免旧值残留。

## Root-Cause Evidence

- `PublishStage(` 在 `guanbi_automation/` 中没有非测试构造点；`PipelineEngine` 也只接受注入式 `publish_stage`。
- `write_publish_target(...)` 没有主线 builder 负责绑定 `FeishuSheetsClient`、`tenant_access_token` 与 `PublishSettings`，因此当前仍属于 dormant foundation primitive。
- 回归测试已复现并锁定原缺陷：
  - resolved target 为 `子表1!B3:E5`
  - dataset 为 `2 x 2`
  - 原实现只会写到 `B3:C4`，无法清空显式矩形其余单元格

## 本轮修复

- `guanbi_automation/infrastructure/feishu/publish_writer.py`
  - 分段规划改为在 dataset 非空时按 resolved target 的完整矩形推导 planned shape
  - 保留空 dataset 时的 no-op 语义，不把空源意外升级成 `1 x 1` 清理写入
- `tests/infrastructure/feishu/test_publish_writer.py`
  - 新增显式矩形边界回归测试
  - 修正原宽表测试中被旧实现掩盖的 resolved target 夹具不一致

## Fresh Verification

### Focused publish suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-reconciliation;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/bootstrap/test_settings.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

结果：

- `34 passed`

### Full suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-reconciliation;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `99 passed`

## 当前恢复点

- 主线权威叙述以后必须写为：
  - `main` 已包含 publish foundation 与 hardening primitives
  - 验证线已形成首个有效 live verification evidence archive
  - 主线当前仍未具备非测试 publish runtime consumer
- 下一步若继续提升 publish：
  1. 不回到 legacy `src/`
  2. 继续以 `.worktrees/publish-stage-task1` 为 live verification 验证线
  3. 只有在主线出现明确 consumer 后，才重新判断 runtime-connected hardening 是否回灌 `main`
