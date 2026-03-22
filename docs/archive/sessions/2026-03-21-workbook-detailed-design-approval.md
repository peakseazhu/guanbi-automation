# 2026-03-21 会话归档（Workbook Detailed Design Approval）

## 1. 本次范围

本次会话严格沿用既定顺序：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

本次没有回到 legacy `src/`，也没有把 workbook 重新发散成“全自动智能猜测”。讨论和收口都围绕 workbook detailed design 展开。

## 2. 本次新增事实

用户进一步确认了 workbook 阶段的真实业务边界：

- 观远导出的源文件通常是 `.xlsx`
- workbook 模板也是 `.xlsx`
- 一个业务任务对应自己的结果 workbook，不是只有一个总 workbook
- 当前目标区域大多数是普通 `sheet` 区块，而不是 `Excel Table / Named Range`
- workbook 写入的主要目的是更新底表数据源，再驱动计算表得出业务结果
- 默认应保留模板结构，不做“清结构重建”
- 已确认的写入模式包括：
  - 清整张 sheet 的数据值后重写
  - 清指定行列范围的数据值后重写
  - 从指定起点追加行
- 已确认的写后动作包括：
  - 辅助列公式下拉
  - 在指定列补固定文本

## 3. 本次关键澄清

### 3.1 Workbook 的角色

本次正式确认 workbook v1 的定位不是“通用 Excel 编辑器”，而是：

- 把每日 extract 源数据写入业务模板底表
- 保留模板结构
- 触发模板既有计算
- 为后续 publish 阶段保留稳定结果产物

### 3.2 公式下拉的正式语义

用户明确强调：

- 公式下拉后的目标单元格必须仍然是公式
- 必须遵守 Excel 相对引用延展语义
- 公式覆盖行数必须与最终写入的真实数据行数对齐
- 不能出现“最后几行数据已写入，但辅助列公式没跟上”的情况

因此本次已把 `fill_down_formula` 正式收敛为：

- 先写数据，得到真实 `written_start_row / written_end_row`
- 再把声明列中的 seed formula 向下延展到 `written_end_row`
- 覆盖不足时稳定失败

## 4. 方案对比与最终选择

本次明确对比了 3 条 workbook 路线：

1. 自由智能识别
2. 强结构标记（`Excel Table / Named Range`）
3. 受约束块写入

最终结论：

- 采用方案 3：`受约束块写入`

原因：

- 最贴合当前模板现实
- 与历史证据“必须在锚点和边界内识别”一致
- 可测试、可归档、可阻断风险

## 5. 本次进入权威文档的设计结论

本次已确认并准备写入权威文档的核心结论如下：

- workbook v1 边界固定为：
  - `1 job -> 1 template workbook -> 1 result workbook`
- 目标区块模型采用 `WorkbookBlockSpec`
- v1 支持的写入模式固定为：
  - `replace_sheet`
  - `replace_range`
  - `append_rows`
- 默认清理语义为：
  - `清值，不清结构`
- 所有智能识别只能发生在 block 边界内
- 写后动作固定先支持：
  - `fill_down_formula`
  - `fill_fixed_value`
- writer engine 方向固定为：
  - file-based writer 作为默认数据平面
  - Excel / COM 只负责计算平面

## 6. 本次文档输出

本次会话结束时，应该同步以下文档：

- 新增：
  - `docs/plans/2026-03-21-workbook-detailed-design.md`
  - `docs/plans/2026-03-21-workbook-stage-implementation-plan.md`
  - `docs/archive/sessions/2026-03-21-workbook-detailed-design-approval.md`
- 更新：
  - `docs/plans/master-system-design.md`
  - `docs/plans/master-implementation-roadmap.md`
  - `docs/archive/decision-log.md`

## 7. 当前恢复点

本次 design 收口后，下一恢复点前移为：

1. `docs/plans/2026-03-21-workbook-stage-implementation-plan.md`
2. 从 `Task 1` 开始按 TDD 执行
3. 继续遵守三层文档治理
4. 仍然不允许回到 legacy `src/`

## 8. 本次未做的事

本次没有开始 workbook 编码。

原因：

- 当前任务是先完成 workbook detailed design 和 workbook implementation plan
- 下一步实现必须按已批准的实施计划进入，而不是边想边写
