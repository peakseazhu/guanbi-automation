# 2026-03-23 会话归档（Publish Hardening Implementation）

## 当前结论

- `publish hardening bundle v1` 已在验证线完成实现收口。
- 本次 hardening 只落在 `guanbi_automation/` 与文档归档目录，没有回到 legacy `src/`。
- 当前 bundle 由以下三段构成：
  - `f268f66 feat: add publish hardening manifest surface`
  - `18d37da fix: infer single-range publish segments`
  - `b7ceea4 feat: add publish hardening writer`
- `publish live verification` 的真实状态仍需单独记住：
  - 有效 evidence archive 是 `runs/live_verification/publish/20260323T022511Z`
  - 旧目录 `runs/live_verification/publish/20260322T054012Z` 仍只是空的历史运行足迹，不是完成证据
- 基于当前 fresh verification，`publish hardening bundle v1` 已具备进入 selective promotion review 的条件，但必须按“整组 foundation bundle”审查，不能再拆成零散 helper promotion。

## 完成内容

- Task 1 已完成并保留在前序提交中：
  - `PublishSettings.chunk_column_limit`
  - `PublishWriteResult.segment_write_mode`
  - `PublishWriteResult.write_segments`
  - publish mapping manifest 的 `segment_count / segment_write_mode / write_segments`
- Task 2 本次完成：
  - 新增 `guanbi_automation/infrastructure/feishu/publish_writer.py`
  - 单 segment 走 `write_values(...)`
  - 多 segment 走 `write_values_batch(...)`
  - writer 返回稳定 `write_segments` 与 `events`
  - `guanbi_automation/infrastructure/feishu/__init__.py` 已补导出
- Task 2 额外补强：
  - writer regression 覆盖了 `520 x 127` tall+wide dataset 的 row-major batch slicing
  - 当前不再只有“列切分 happy path”，而是把行列双维切分也锁住
- Task 3 已确认是 test-only 收口：
  - `plan_range_segments(...)` 原实现已经满足 row-major 的 row/column-aware 分段
  - 新增 `520 x 127` 回归测试，锁定四段范围：
    - `ySyhcD!B5:CW504`
    - `ySyhcD!CX5:DX504`
    - `ySyhcD!B505:CW524`
    - `ySyhcD!CX505:DX524`
- Task 4 无需再改实现：
  - `PublishStage` 现有 manifest tests 已覆盖 `segment_count`
  - 已覆盖 `segment_write_mode`
  - 已覆盖 single-range fallback 与 blocked/failed non-regression
- 计划文档同步修正：
  - 把原实现计划中的 `EU` 示例修正为实际应为的 `DX`
  - 明确 `partial_write` 的实际边界语义

## 关键实现边界

- `chunk_count` 表示适配器请求次数，不表示逻辑 segment 数量。
- `segment_count` 表示逻辑矩形写入段数量。
- `partial_write` 只表达 runtime 已确认的请求级部分写入。
- 当前 `batch_ranges -> values_batch_update` 路径对 runtime 来说是单次适配器调用，因此单次批量请求直接失败时，runtime 不会把未知的服务端部分应用误报为 `partial_write=True`。
- `readback / comparison evidence` 仍然只属于 live verification，不进入本次主线 hardening runtime。

## 自动化验证

### Focused Hardening Verification

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/bootstrap/test_settings.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider
```

结果：

- `34 passed`

### Validation Branch Full Suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `110 passed`

## 对主线的晋升判断

当前已适合进入 selective promotion review 的内容是：

- publish hardening manifest surface
- single-range manifest fallback 修复
- concrete publish writer
- row/column-aware planner regression coverage
- 与之配套的设计 / implementation plan / implementation archive

当前仍应留在验证线、不要回灌 `main` 的内容是：

- `publish_live_verification_service`
- `publish_real_sample` 入口
- `config/live_verification/publish/real_sample.local.yaml`
- `runs/live_verification/publish/20260323T022511Z`
- 任何真实 spreadsheet token / target sheet 绑定内容

原因是：

- 这批内容的职责仍然是“真实样本验证与证据归档”
- 不是主线 publish foundation 的默认运行边界

## 当前恢复点

- worktree：`D:\get_bi_data__1\.worktrees\publish-stage-task1`
- branch：`publish-stage-task1`
- 当前 hardening 实现提交：`b7ceea4 feat: add publish hardening writer`
- 当前分支状态：相对 `origin/publish-stage-task1` 为 `ahead 5`
- 当前未纳入本次工作的遗留项：`uv.lock` 仍保持未跟踪，不参与本次实现与归档
- 下一恢复点固定为：
  1. 将 `publish hardening bundle v1` 作为整组 foundation bundle 做 promotion review
  2. 若 review 通过，再决定如何选择性回灌 `main`
  3. 不把 live verification scaffold 与 evidence archive 混入主线 promotion
