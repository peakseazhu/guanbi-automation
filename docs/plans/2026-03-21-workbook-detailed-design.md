# Workbook Detailed Design

> 状态：Approved
> 最近更新：2026-03-21
> 前置阶段：`runtime contract`、`extract runtime policy`
> 后续阶段：`workbook stage implementation plan`
> 关联文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-20-extract-runtime-policy-design.md`

## 1. 背景

`runtime contract` 与 `extract runtime policy` 已完成后，当前正式进入 workbook 阶段细化。

这一阶段的目标不是做一个通用 Excel 编辑器，而是把每日从观远导出的源数据，稳定写回业务模板中的底表数据区，保留模板结构，触发计算，再为后续 publish 阶段提供稳定产物。

当前设计继续遵守：

1. 新项目实现代码从 0 构建
2. 不回到 legacy `src/`
3. workbook 设计必须复用 runtime contract 的 stage gate、error taxonomy 与 manifest 语义

## 2. 已确认业务事实

本轮澄清后，workbook 阶段的关键事实已经收敛为：

- 观远导出的源文件通常是 `.xlsx`，在少数场景下也可能是 `.csv`
- 业务模板本身也是 `.xlsx`
- 不是只有一个 workbook，而是多个 job 各自对应自己的结果 workbook
- 目标区域大多数不是 `Excel Table` 或 `Named Range`，而是普通 `sheet` 区块
- workbook 写入的主要目的，是把底表数据区更新为新的源数据，供计算表继续计算
- 默认应保留模板中的公式、格式、合并关系等结构
- 业务已确认的写入模式至少包括：
  - 清空整张目标 sheet 的数据值后重写
  - 清空指定行列范围的数据值后重写
  - 从指定起点开始追加行
- 写入后还存在两类真实的受约束派生动作：
  - 辅助列公式下拉
  - 在指定列补固定文本值

## 3. 历史证据

### 3.1 旧链路的有效经验

legacy `src/utils/xlwings_utils.py` 已证明以下思路是有效的：

- 范围识别必须基于用户给定的起始行列
- 识别逻辑应当在用户声明边界内收缩，而不是全表自由猜测
- 追加定位可以参考目标区块内的有效末行，而不是只看 `used_range`

这些经验可以继承为新系统的设计原则，但不继承旧实现本身。

### 3.2 旧链路的失败证据

历史日志已经证明，Workbook 大表写入不能默认压给 Excel COM：

- `logger/log_01202602_0818.txt`
- `logger/log_01202603_0850.txt`
- `logger/log_07202603_0850.txt`
- `logger/log_10202601_0818.txt`

这些证据与 legacy `src/utils/xlwings_utils.py` 一起说明：

- 大块二维数据直接经由 `xlwings` / COM 粘贴，在真实大表上已经失稳
- workbook v1 必须把“数据写入平面”和“Excel 计算平面”拆开
- 范围识别和写入模式必须显式建模，而不是继续靠临时脚本逻辑拼接

## 4. 方案对比

### 4.1 方案 A：自由智能识别

做法：

- 用户只给起点
- 系统尽量自动猜测数据区、清理范围、追加终点、公式列与辅助列

优点：

- 前期配置少

缺点：

- 普通 `sheet` 区块容易混有空行、说明文字、临时手填内容
- 一旦猜错，风险直接落到业务底表
- 缺少可验证边界

结论：

- 不采用

### 4.2 方案 B：强结构标记

做法：

- 强制将目标区域统一改造成 `Excel Table` 或 `Named Range`
- 所有写入都围绕结构化对象进行

优点：

- 语义最稳定

缺点：

- 与当前模板现实不匹配
- 会把 workbook v1 的前置条件变成“先重构所有模板”

结论：

- 当前阶段不采用

### 4.3 方案 C：受约束块写入

做法：

- 每个目标区块显式声明 `sheet + 起点 + 模式 + 清理策略 + 追加定位规则 + 写后动作`
- 系统只在该区块内做有限的范围识别

优点：

- 最贴合当前“普通 sheet 区块 + 底表数据源”的现实
- 智能识别仍有边界，便于测试和归档
- 与历史证据“锚点内识别”一致

缺点：

- 前期配置比“全自动猜测”多一些

结论：

- 当前采用该方案

## 5. 设计结论

### 5.1 阶段角色

`workbook_ingest` 的职责：

- 消费一个 job 依赖的多个 extract 文件
- 将 extract 文件归一化为标准表格数据
- 把这些数据写入结果 workbook 中已声明的普通 `sheet` 区块
- 在 block 级完成必要的写后派生动作

`workbook_transform` 的职责：

- 在 ingest 完成后打开结果 workbook
- 触发模板既有计算
- 保存计算后的结果 workbook
- 为后续 publish 阶段保留稳定产物

### 5.2 v1 边界

workbook v1 的正式边界为：

- `1 job -> 1 template workbook -> 1 result workbook`
- 一个 job 可以消费多个 extract 文件
- 一个结果 workbook 可以声明多个目标 block
- 目标 block 以普通 `sheet` 区块为主
- 默认语义是“清值不清结构”
- 所有智能识别都只能发生在 block 自身边界内

当前不做：

- 全工作簿无边界智能识别
- 强制把模板改造成 `Excel Table` / `Named Range`
- 默认清公式、清样式、清合并关系
- 把大表直接交给 COM 做默认数据平面

## 6. Block 模型

workbook v1 以 `WorkbookBlockSpec` 作为最小写入单元。

每个 block 至少包含：

- `block_id`
- `sheet_name`
- `source_extract_id`
- `start_row`
- `start_col`
- `write_mode`
- `clear_policy`
- 可选 `end_row`
- 可选 `end_col`
- 可选 `append_locator_columns`
- 可选 `post_write_actions`

一个结果 workbook 可以声明多个 block，但每个 block 只绑定一个 extract 数据源，不做多源混写。

## 7. 写入模式

### 7.1 `replace_sheet`

语义：

- 仅适用于“整张 sheet 本来就是数据底表”的场景
- 清空目标 sheet 中的数据值，再从 block 的声明起点写入新数据

默认行为：

- 只清值
- 不清公式、格式、合并关系

### 7.2 `replace_range`

语义：

- 只在声明区块内清值并重写
- 适用于指定行列范围覆盖

规则：

- `start_row/start_col` 必填
- `end_row/end_col` 至少要能与源数据宽度共同确定一个稳定目标矩形

### 7.3 `append_rows`

语义：

- 在 block 的声明锚点内定位有效末行，再向下追加新行

规则：

- 末行判断默认只看“本次源数据将写入的那些列”
- 如果业务需要，可以显式声明 `append_locator_columns`
- 没有现有数据时，从 `start_row` 开始写第一批

## 8. 范围识别规则

范围识别的正式规则为：

- `start_row/start_col` 是唯一允许的识别锚点
- 识别只在当前 `sheet` 的当前 block 内进行
- 如果给了 `end_row/end_col`，系统只能在这个矩形内识别有效区域
- 如果未给完整结束边界，系统只能结合“源数据尺寸 + 右下方向保守识别”确定写入窗口
- 不允许回扫锚点上方或左侧
- `None` 和空字符串视为空
- 中间空单元格不截断 block，只裁掉尾部空行和尾部空列
- block 外的零散脏数据一律忽略

这意味着 workbook v1 的“智能”，只体现在显式边界内的保守识别，而不是无边界猜测。

## 9. 写后派生动作

### 9.1 `fill_down_formula`

用途：

- 把底表辅助列公式向下延展到本次真实写入行段

正式语义：

- 下拉结果必须仍然是 Excel 公式，而不是把计算值写死
- 必须遵守 Excel 的相对/绝对引用规则，例如 `=$B2 -> =$B3`
- 下拉行数以本次真实写入后的 `written_start_row` 到 `written_end_row` 为准
- 少覆盖一行也视为失败

推荐策略：

- 优先使用目标列在写入起点上方最近一行的现有公式作为 seed
- 同时允许后续实现增加显式 `formula_seed_row`
- 只作用于声明列
- 只覆盖本次写入影响到的行段

### 9.2 `fill_fixed_value`

用途：

- 在指定列为本次新写入行补固定文本

语义：

- 显式声明目标列和值
- 只填本次写入影响到的行段
- 不回写旧数据行

### 9.3 执行顺序

每个 block 的建议顺序固定为：

1. 范围识别
2. 清理目标值
3. 写入源数据
4. 执行 `post_write_actions`
5. 记录 block 级 manifest 证据

## 10. Writer Engine 与计算平面

### 10.1 默认数据平面

workbook v1 默认采用 `file-based writer` 作为数据写入平面。

它负责：

- 清值
- `replace_sheet`
- `replace_range`
- `append_rows`
- 固定值填充
- 公式下拉

### 10.2 Excel 计算平面

Excel / COM 只在需要模板实际计算时介入。

它负责：

- 打开结果 workbook
- 触发计算
- 保存计算结果

它不负责：

- 作为默认大块数据写入平面

### 10.3 尺寸护栏

每次 block 写入前，必须先显式记录：

- `row_count`
- `column_count`
- `cell_count`

当 block 超过安全阈值时：

- 默认 `blocked`
- 将尺寸信息与 block 信息写入 manifest
- 不自动回退为 COM 批量直写

阈值的精确数值与替代大表写法，仍保留为后续实现期需要验证的点。

## 11. 配置草图

```yaml
workbook:
  template_path: templates/workbooks/daily-report-template.xlsx
  result_naming: "{job_id}-{run_date}.xlsx"
  blocks:
    - block_id: sales_detail_append
      sheet_name: 底表
      source_extract_id: sales_detail
      write_mode: append_rows
      start_row: 2
      start_col: 2
      append_locator_columns: [2, 3, 4]
      clear_policy: none
      post_write_actions:
        - action: fill_fixed_value
          column: 1
          value: 华东区
        - action: fill_down_formula
          columns: [6, 7, 8]

    - block_id: inventory_replace
      sheet_name: 底表
      source_extract_id: inventory_daily
      write_mode: replace_range
      start_row: 2
      start_col: 10
      end_col: 18
      clear_policy: clear_values
      post_write_actions:
        - action: fill_down_formula
          columns: [19]
```

## 12. 失败语义

workbook v1 至少需要稳定区分：

- `workbook_template_missing`
- `workbook_sheet_missing`
- `workbook_block_invalid`
- `workbook_range_detection_failed`
- `workbook_size_guardrail_triggered`
- `workbook_formula_seed_missing`
- `workbook_formula_fill_incomplete`
- `workbook_writer_error`
- `workbook_calculation_error`
- `workbook_output_read_error`

关键要求：

- 范围识别失败时，不允许猜测性写入
- 公式种子不存在时，不允许假装下拉成功
- 公式未覆盖到最终写入行时，必须显式失败

## 13. 测试边界

单元测试至少覆盖：

- `replace_range` 的清值与写入边界
- `append_rows` 基于 locator columns 的末行定位
- `fill_down_formula` 按最终写入行数准确覆盖
- `fill_fixed_value` 只填本次影响行
- 公式覆盖不足时稳定失败
- 尺寸护栏触发时稳定 blocked

集成测试至少覆盖：

- 一个 job 消费多个 extract，写入同一 workbook 的多个 block
- 从模板副本生成结果 workbook
- 触发计算并保存结果 workbook
- manifest 记录 block 输入、写入范围、写后动作与失败点

## 14. 当前仍保留的未决项

本次设计已锁定 workbook v1 的写入模型，但以下问题仍需在实施期基于测试继续收敛：

- `file-based writer` 的大表安全阈值精确数值
- 超阈值后的替代写法是否需要单独 spike
- workbook 结果输出区与 publish 映射契约
- `.csv` 输入在 workbook ingest 中的最终支持边界

## 15. 后续入口

本设计批准后，下一步不是直接写代码，而是：

1. 写 workbook 实施计划
2. 按 TDD 从 Task 1 开始执行
3. 在实施过程中继续把验证证据回写三层文档
