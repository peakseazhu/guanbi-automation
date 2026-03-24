# 2026-03-23 会话归档（Mainline Publish Runtime Consumer Implementation）

## 当前结论

- `main` 已接通首个非测试 publish runtime consumer，不再只停留在 publish foundation / hardening primitives。
- 当前 consumer 形态固定为 thin CLI + application service：
  - YAML publish spec loader
  - explicit `tenant_access_token`
  - CLI token input via `--tenant-access-token` or `FEISHU_TENANT_ACCESS_TOKEN`
  - `PipelineEngine.run_publish(...)` -> `PublishStage`
  - stable JSON runtime envelope
  - exit code `0/1/2`
- 第一版 consumer 只接通 `replace_sheet` / `replace_range`。
- `append_rows` 仍保留在 contract / planner / stage safety 中，但继续在 consumer 预校验阶段显式拒绝。
- validation line 继续承担 live verification、真实资源 readback/comparison 与后续 evidence 收口；本次没有回到 legacy `src/`，也没有把验证线 runtime 混入主线。

## 本轮实现

- `guanbi_automation/application/publish_runtime_spec.py`
  - 读取最小 YAML publish spec，并直接复用既有 `PublishMappingSpec`
- `guanbi_automation/application/publish_runtime_service.py`
  - 执行 preflight
  - 生成稳定默认 `batch_id` / `job_id`
  - 组装 `FeishuSheetsClient`、`PublishSettings`、target loader、default writer、`PublishStage`、`PipelineEngine`
  - 归一化 source-reader、target-loader、planner 与 transport failure，保证 service 不把异常泄漏给 CLI
- `guanbi_automation/execution/stages/publish.py`
  - source-reader failure 与非 `PublishClientError` target-loader failure 会被折叠为 failed mapping manifest
  - manifest target identity 现在优先回显 resolved target identity，而不是只回显请求值
- `guanbi_automation/publish/run_publish.py`
  - 只保留 argv 解析、service 调用、JSON 输出与退出码映射
  - unknown argv 现在也会回到 `preflight_failed` JSON envelope
- `tests/publish/test_run_publish.py`
  - 覆盖 envelope 输出、路径参数传递、`0/1/2` 退出码与模块可执行 guard

## Scope Ledger

- consumer-wired now:
  - `replace_sheet`
  - `replace_range`
  - stable CLI envelope
  - explicit runtime token input
- foundation-only still:
  - `append_rows` consumer runtime path
  - readback/comparison runtime
  - token fetch flow
  - live verification spec / service / entrypoint

## Fresh Verification

### Focused publish consumer + foundation bundle

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/application/test_publish_runtime_spec.py tests/application/test_publish_runtime_service.py tests/publish/test_run_publish.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

结果：

- `60 passed`

### Full suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-consumer;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `130 passed`

## 当前恢复点

- 主线权威叙述现在必须写成：
  - `main` 已包含 runtime contract、extract runtime policy、workbook foundation、publish foundation
  - `main` 已新增首个非测试 publish runtime consumer
  - 第一版 consumer 只接通 `replace_sheet` / `replace_range`
  - `append_rows` 仍存在于 foundation/stage safety，但尚未接入 consumer runtime
  - validation line 继续承担 live verification 与真实证据推进
- 后续若继续推进 publish：
  1. 不回到 legacy `src/`
  2. 先决定当前 consumer 切片如何评审、提交与回灌
  3. 再判断下一主线切片是 `append_rows` consumer wiring，还是继续把 validation 证据收敛为下一批可提升 bundle
