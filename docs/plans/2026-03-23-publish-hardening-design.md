# Publish Hardening Design

> 状态：Approved
> 最近更新：2026-03-23
> 前置阶段：`publish live verification`
> 后续阶段：`publish hardening implementation plan`
> 关联文档：
> - `README.md`
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-22-publish-live-verification-design.md`
> - `docs/archive/sessions/2026-03-23-validation-branch-promotion-sweep.md`

## 1. 背景

`publish live verification` 已证明两件关键事实：

1. 当前真实样本 `全国执行` 的 canonical shape 为 `58 x 127`
2. 飞书单次写入存在 `5000 x 100` 约束，当前样本必须按 `100 + 27` 列切分后才能稳定写入

这说明：

- `publish_source_reader` 的 streaming-safe 修复只是第一层 foundation 修复
- 主线 publish 若仍停留在“单范围写入”或“只按行切分”的抽象，就还没有真正具备宽表 publish 能力

因此下一步不再继续提升 live verification scaffold，而是把验证线中的“宽表可写”部分收敛成一个完整的 `publish hardening` bundle。

## 2. 目标与非目标

### 2.1 本次目标

本次 hardening 只做以下事情：

1. 为 publish stage 增加可实际运行的 Feishu target writer 路径
2. 写入前基于 `row_count / column_count` 生成 row/column-aware segment plan
3. 当数据超过飞书单次范围限制时，优先走 `values_batch_update`
4. mapping manifest 记录真实 segment plan 与批量写入摘要
5. 保持这批能力可以作为下一次 selective promotion 的完整 foundation bundle

### 2.2 明确不做

本次不做：

- 不把 readback comparison 产品化进主线 publish
- 不把 `publish_live_verification_service` 并入 publish stage
- 不把 local spec、real-sample entrypoint、evidence archive 回灌主线
- 不回 legacy `src/`

原因：

- 本轮要解决的是“主线 publish 能不能正确写宽表”
- 不是“主线每次写完后都默认做一轮验证线级别的证明”

## 3. 方案对比

### 3.1 方案 A：只把 helper 回灌到 publish foundation

做法：

- 保留主线 publish writer 抽象不变
- 只提升 `plan_range_segments`、`write_values_batch` 等 helper

优点：

- 改动看起来小

缺点：

- helper 不被主流程消费
- 主线会出现 dormant API
- 无法证明主线 publish 真正获得宽表能力

结论：

- 不采用

### 3.2 方案 B：把 row/column-aware writer 做成 publish hardening bundle

做法：

- 在验证线补齐真实 Feishu target writer
- target writer 统一消费 `ResolvedPublishTarget + PublishDataset`
- 当写入范围超过官方限制时，生成多个矩形 segment
- 优先走 `values_batch_update`
- 把 segment 与写入摘要落到 publish manifest

优点：

- 能真正增强 publish stage
- 和 live verification 的真实证据直接对齐
- 很适合作为下一批 selective promotion 单元

缺点：

- 改动不再只是 helper，需要补 writer runtime 与 manifest 字段

结论：

- 当前采用该方案

### 3.3 方案 C：把 readback comparison 一起产品化

优点：

- 正确性保证更强

缺点：

- 每次 publish 都新增读回成本
- 主线错误语义和运行成本都会扩大
- 当前证据只证明它适合作为 live verification，不足以证明它应成为主线默认行为

结论：

- 本轮不采用

## 4. 设计结论

### 4.1 主线 publish writer 的职责

本次补齐后的 publish writer 固定职责为：

1. 接收 `PublishDataset`
2. 根据 `ResolvedPublishTarget` 与 dataset shape 计算真实 segment plan
3. 按 segment plan 构造飞书写入 payload
4. 调用 Feishu Sheets API 完成写入
5. 返回稳定 `PublishWriteResult`

其中 readback 不属于本 writer 的默认职责。

### 4.2 segment planning 规则

segment planning 固定遵守：

- 最大 `5000` 行
- 最大 `100` 列
- 先按行分段，再按列分段
- segment 必须是连续矩形范围

对于当前真实样本：

- `58 x 127`
- 应拆为：
  - `A1:CV58`
  - `CW1:DW58`

这一规划逻辑从 live verification 路径提升为 publish hardening foundation。

### 4.3 API 选择

本次 writer 采用以下规则：

- 只有一个 segment 时：
  - 允许继续走单范围写入
- 多个 segment 时：
  - 优先走 `values_batch_update`

原因：

- 与 live verification 已验证路径一致
- 能把一次 publish 的多个矩形范围作为一个写入步骤处理
- 比多次离散单范围调用更接近当前真实需求

### 4.4 manifest 扩展

mapping manifest 中现有 `write_summary` 只覆盖：

- `chunk_count`
- `successful_chunk_count`
- `written_row_count`
- `partial_write`

这不足以表达宽表列分段。

因此本次新增：

- `write_summary.segment_count`
- `write_summary.segment_write_mode`
  - `single_range`
  - `batch_ranges`
- `write_segments`
  - 每段 `range_string`
  - `row_count`
  - `column_count`
  - `row_offset`
  - `column_offset`

这样主线 manifest 才能真实表达“宽表是如何被写入的”。

### 4.5 错误语义

本次继续沿用现有 publish 错误语义，不新增 readback failure：

- `publish_auth_error`
- `publish_target_missing`
- `publish_range_invalid`
- `publish_rate_limit_error`
- `publish_write_error`

`publish_readback_mismatch` 继续留在 live verification，不进入本轮主线 hardening bundle。

## 5. 代码边界

本次预计涉及：

- `guanbi_automation/infrastructure/feishu/client.py`
- `guanbi_automation/infrastructure/feishu/target_planner.py`
- `guanbi_automation/infrastructure/feishu/__init__.py`
- `guanbi_automation/execution/stages/publish.py`
- `guanbi_automation/bootstrap/settings.py`
- 必要时新增独立 publish writer 模块
- `tests/infrastructure/feishu/*`
- `tests/execution/test_publish_stage.py`

本次不动：

- `application/publish_live_verification_service.py`
- `application/live_verification_spec.py`
- `domain/live_verification.py`
- `live_verification/publish_real_sample.py`
- `config/live_verification/**/*.local.yaml`
- `runs/live_verification/**`

## 6. 验证策略

自动化测试至少覆盖：

1. 宽表 segment 规划
2. 单 segment 与多 segment 的 API 选择
3. `values_batch_update` payload 构造
4. stage manifest 中的 `write_segments` 与 `segment_count`
5. 写入失败时的 `partial_write / final_error` 语义

阶段验证顺序固定为：

1. focused infrastructure tests
2. focused publish stage tests
3. 验证线 full suite

## 7. 下一步

本设计批准后，下一步固定为：

1. 写 `docs/plans/2026-03-23-publish-hardening-implementation-plan.md`
2. 按 TDD 在验证线实现 publish hardening bundle
3. 完成 focused verification 与 validation-branch fresh full suite
4. 再判断哪些内容值得 selective promotion 到 `main`
