# 2026-03-23 会话归档（Publish Hardening Mainline Merge）

## 当前结论

- `publish hardening bundle v1` 已经通过 PR #2 合入 `main`。
- 当前主线已经从 `publish foundation + streaming-safe source reader fix` 前进到 `publish foundation + publish hardening bundle v1`。
- 本轮合入没有把 live verification scaffold、readback/comparison runtime、本地 real-sample config 或 evidence archive 混入 `main`。

## Merge Provenance

- merged PR：
  - `https://github.com/peakseazhu/guanbi-automation/pull/2`
- merge commit：
  - `5ac9b38 Merge pull request #2 from peakseazhu/publish-hardening-promotion`
- promotion branch head before merge：
  - `aecf810 docs: update publish hardening promotion status`
- selective promotion source：
  - `publish-stage-task1@b1bca69`

## Mainline State After Merge

当前 `main` 已包含：

- `PublishSettings.chunk_column_limit=100`
- row/column-aware `plan_range_segments(...)`
- single-range fallback inference
- concrete `publish_writer`
- 单 segment `write_values(...)`
- 多 segment `values_batch_update(...)`
- batch-aware `PUBLISH_RANGE_INVALID`
- mapping manifest `segment_count / segment_write_mode / write_segments`
- 对应 regression tests

当前仍明确留在验证线的内容为：

- `fetch_tenant_access_token`
- `read_values`
- `PUBLISH_READBACK_MISMATCH`
- live verification spec / service / entrypoint
- local real-sample config
- 真实目标标识
- evidence archive 与 readback/comparison runtime

## 自动化验证

### Merged Main Fresh Full Suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `98 passed`

### Promotion Branch Provenance

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-hardening-promotion;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/bootstrap/test_settings.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

结果：

- `33 passed`

### Validation Branch Provenance

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `110 passed`

## 当前恢复点

- 主线：
  - `main@5ac9b38`
  - 当前权威恢复入口应前移到本归档
- 验证线：
  - 继续以 `.worktrees/publish-stage-task1` 承担 readback/comparison 与后续真实资源验证
- 当前下一步固定为：
  1. 保持 `main` 稳定，不再把验证线 readback/comparison helper 直接抬入主线
  2. 若要继续提升 publish 能力，必须先证明主线存在新的 runtime consumer
  3. promotion worktree 与分支在不再需要时可清理，但不影响当前主线恢复点
