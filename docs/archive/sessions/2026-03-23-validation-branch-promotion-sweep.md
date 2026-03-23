# 2026-03-23 会话归档（Validation Branch Promotion Sweep）

## 当前结论

- 已完成 `main..publish-stage-task1` 的下一批候选回灌筛选。
- 本轮没有新的运行时代码回灌到 `main`。
- `main` 继续保持：
  - publish foundation
  - `publish_source_reader` streaming-safe 修复
- 下一批真正值得推进的候选项不再是零散 helper，而是一个完整的 `publish hardening` bundle：
  - row/column-aware write planning
  - `values_batch_update` 写入路径
  - 与主线 publish writer 真正连通后的必要错误语义

## 本轮审查范围

已审查 `publish-stage-task1` 中相对 `main` 仍未进入主线的核心差异：

- live verification spec / domain / service
- real-sample entrypoint
- Feishu client 的：
  - `fetch_tenant_access_token`
  - `read_values`
  - `write_values_batch`
- target planner 的：
  - `plan_range_segments`
- runtime error:
  - `PUBLISH_READBACK_MISMATCH`
- 对应测试与实现归档文档

## 分类结果

### 1. live-verification-only

- 本地 ignored artifact：
  - `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.local.yaml`
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`
- tracked validation-line asset：
  - `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.example.yaml`
  - `.worktrees/publish-stage-task1/guanbi_automation/domain/live_verification.py`
  - `.worktrees/publish-stage-task1/guanbi_automation/application/live_verification_spec.py`
  - `.worktrees/publish-stage-task1/guanbi_automation/application/publish_live_verification_service.py`
  - `.worktrees/publish-stage-task1/guanbi_automation/live_verification/publish_real_sample.py`
  - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`

原因：

- 这些内容直接服务真实样本写入、读回、comparison 与 evidence archive。
- `real_sample.local.yaml` 与 `runs/live_verification/...` 本身还是本地 ignored artifact，不应被误写成主线可跟踪资产。
- 即使其中部分实现不含私有 token，本质上仍属于 live verification runtime，而不是当前 `main` 的稳定 publish 入口。

### 2. potential-foundation

- `.worktrees/publish-stage-task1/guanbi_automation/infrastructure/feishu/client.py`
  - `fetch_tenant_access_token`
  - `read_values`
  - `write_values_batch`
- `.worktrees/publish-stage-task1/guanbi_automation/infrastructure/feishu/target_planner.py`
  - `plan_range_segments`
- `.worktrees/publish-stage-task1/guanbi_automation/domain/runtime_errors.py`
  - `PUBLISH_READBACK_MISMATCH`

原因：

- 它们确实被真实样本证明是通用能力：
  - evidence archive 已证明当前真实样本需要把 `58 x 127` 数据按 `100 + 27` 列切分
  - `comparison.json` 已确认 `matches = true`
- 但当前 `main` 的 publish stage 还没有真正消费这些 helper：
  - 主线没有 row/column-aware writer
  - 主线没有 batch write path
  - 主线也没有 readback comparison contract
- 如果把这些 helper 单独回灌到 `main`，只会引入未被主流程消费的 dormant API，并把主线状态写得比真实进度更靠前。

### 3. docs/history divergence only

- 验证线中的旧 README / roadmap / session archive 反映的是当时工作线现场，不再直接代表当前主线事实。
- 这些差异不构成新的代码 promotion 候选；它们的职责是保留历史演化轨迹。

## 为什么本轮不再继续拆小回灌

本轮之后，最重要的边界已经清楚：

- `publish_source_reader` streaming-safe 修复是可以独立成立的 foundation 修复，所以已经回灌。
- 剩余 Feishu readback / batch write / column segmentation 能力，只有在主线 publish writer 实际接入后，才算主线真正获得了 publish hardening。
- 因此下一次回灌应当是一个连通的 publish hardening bundle，而不是继续拆成零散 helper commit。

## 当前证据依据

- 首个有效 evidence archive：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`
- `write-plan.json` 已记录两段列范围：
  - `ySyhcD!A1:CV58`
  - `ySyhcD!CW1:DW58`
- `comparison.json` 已确认：
  - `matches = true`
  - `row_count = 58`
  - `column_count = 127`

## 下一步固定路线

若继续推进，下一步固定为：

1. 在验证线把 `publish hardening` 做成完整可验证 bundle。
2. 让主线 publish writer 真正消费 row/column-aware range planning 与 batch write path。
3. 只在主线具备 fresh verification 后，再选择性回灌。

## 本轮验证说明

- 本轮是 docs + diff classification sweep，不是新的 runtime implementation。
- 未重新执行 pytest。
- 本轮结论依据为：
  - `main..publish-stage-task1` 差异审查
  - 已存在 evidence archive 内容核对
  - 当前主线与验证线既有 fresh verification 记录
