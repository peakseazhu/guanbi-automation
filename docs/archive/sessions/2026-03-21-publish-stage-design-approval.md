# 2026-03-21 会话归档（Publish Stage Design Approval）

## 1. 本次目标

在 workbook stage 已完成后，正式完成：

- `publish stage detailed design`
- 先锁定 `workbook output -> publish mapping contract`
- 再收敛 publish 的数据流、失败语义、归档与恢复边界

本次仍未进入 publish 编码实现。

## 2. 已批准设计结论

### 2.1 主模型

publish v1 采用：

- 显式 `publish source + publish target` 契约
- 中间保留标准化 `publish dataset`
- 再由 Feishu writer 分批写入目标

而不是：

- workbook 读取后直接立刻写飞书
- 或反向要求 workbook 先产出 publish-specific outputs

### 2.2 publish source

source 同时支持：

- 整张计算表读取
- 固定结果区块读取

范围识别规则为：

- 以 `start_row/start_col` 为锚点
- 只在右下方向保守识别
- 可结合 `end_row/end_col` 收紧边界
- `header_mode` 默认 `exclude`

### 2.3 publish target

target 同时支持：

- `replace_sheet`
- `replace_range`
- `append_rows`

目标解析规则为：

- 必须显式给出 `spreadsheet_token`
- 使用稳定 `sheet_id` 优先定位目标子表
- 写入飞书的是值，不是公式
- 默认只更新值，不改结构

### 2.4 数据流

publish v1 的执行顺序固定为：

1. `resolve mappings + preflight`
2. `read workbook values -> publish dataset`
3. `write publish dataset -> feishu target`
4. `publish manifest`

### 2.5 风险护栏

当前已批准的关键护栏为：

- mapping 是最小执行与诊断单元
- chunk 串行执行
- mapping 串行执行
- `append_rows` 默认不是安全重跑操作
- 同一 batch / 同一 mapping / 同一目标的追加式重跑默认 `blocked`
- `empty_source_policy` 默认 `skip`

## 3. 文档同步

本次应同步更新：

- `docs/plans/2026-03-21-publish-stage-detailed-design.md`
- `docs/plans/master-system-design.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-21-publish-stage-design-approval.md`

设计批准后，下一步入口为：

- `docs/plans/2026-03-21-publish-stage-implementation-plan.md`

## 4. 当前恢复点

截至本次设计批准：

- publish detailed design 已完成
- 当前下一恢复点前移为：
  - 写 publish implementation plan
  - 按 TDD 从 Task 1 开始执行
