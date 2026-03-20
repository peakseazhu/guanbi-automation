> 2026-03-19 规划治理更新：当前权威文档已切换到 `docs/plans/master-system-design.md` 与 `docs/plans/master-implementation-roadmap.md`；本文保留为更早期的范围草稿。
# 观远 BI 到 Excel 到飞书 Sheets 通用任务工具设计稿

> 状态：Draft
> 更新时间：2026-03-18
> 说明：本文件保留为第一版范围草稿。2026-03-19 起，项目规划已扩展为完整的“观远 BI 自动化套件”设计，请优先阅读：
> - `docs/plans/2026-03-19-guanbi-automation-suite-design.md`
> - `docs/plans/2026-03-19-guanbi-live-verification.md`
> - `docs/plans/2026-03-19-legacy-script-audit.md`
> - `docs/plans/2026-03-19-guanbi-automation-implementation-plan.md`

## 已确认结论

- 目标是一个完全配置驱动的通用任务工具，不再为单一计算表写死流程。
- 系统需要支持同一个观远看板在同一次运行中以不同筛选条件下载多次。
- 共享关系是“部分共享”：
  - 不同计算表任务会复用一部分相同 BI 下载结果。
  - 共享只发生在同一次运行内。
  - 历史下载文件保留为本地存档，不作为次日默认复用来源。
- 飞书第一阶段只支持 `Sheets` 上传，不优先做 `Wiki`。

## 当前推荐的配置组织

采用三层结构：

1. `project` 全局配置
2. `extracts` 共享抽取定义
3. `jobs` 计算表任务定义

示意结构：

```text
config/
  project.json
  extracts/
    *.json
  jobs/
    *.json
```

## 当前推荐的核心抽象

### extract

共享的最小单位不是看板，而是抽取定义。

每个 extract 使用自定义的 `extract_id` 唯一标识，而不是直接使用 `chart_id`。

这样可以支持：

- 同一个 `chart_id`
- 不同筛选条件
- 不同导出命名
- 不同用途

并存于同一个系统中。

### job

每个 job 代表一条完整业务链路，通常对应一个本地计算工作簿：

- 引用多个 extract
- 执行复制/追加/覆盖
- 触发 Excel 计算
- 读取结果区域
- 上传到飞书 Sheets

## 运行时共享原则

- 单次运行内，对解析后的抽取定义做去重。
- 如果多个 job 依赖的 extract 在最终展开后完全相同，则只下载一次。
- 到下一天重新运行时，重新生成当天所需下载，不直接复用昨天产物。

## 已确认执行流水线

1. 读取 `project.json`
2. 解析本次运行上下文
3. 加载本次启用的 `jobs`
4. 汇总这些 job 引用的 `extract_id`
5. 将 extract 的动态筛选规则渲染为本次真实筛选条件
6. 基于真实筛选条件计算签名并做单次运行内去重
7. 从观远 BI 下载文件并归档保存
8. 逐个执行 job，将抽取结果写入对应计算工作簿
9. 触发 Excel 计算并保存结果
10. 读取 job 定义好的输出区域
11. 分批上传到飞书 Sheets
12. 记录本次运行结果、失败点和归档路径

## 已确认日期筛选设计方向

不再使用按字段名写死逻辑的方式更新筛选，而改为：

- `filter_template`
- `dynamic_rules`

### 设计原则

- 尽量保留观远原始请求结构
- 只动态修改 `filterValue`、`displayValue`、必要时的 `macroName`
- 通过 `fdId` 优先定位目标筛选项
- `name` 仅作为辅助定位字段，不作为唯一定位依据

### 推荐支持的规则类型

- `date_range`
- `date_list`
- `month_list`
- `literal`
- `passthrough`

### 推荐支持的日期预设

- `yesterday`
- `days_ago`
- `last_n_days`
- `week_to_yesterday`
- `current_month`
- `previous_month`
- `explicit`

### 当前覆盖目标

需要覆盖以下真实场景：

- `BT` + 两个日期值
- `IN` + 多个日期值
- `STRING` 类型日期字段
- `DATE` 类型日期字段
- 日期筛选与其他固定筛选并存

### displayValue 原则

- 默认由系统根据 `filterValue` 同步生成
- 除非显式配置，不要求手工维护

## 已确认 Excel 写入设计方向

### 关于写入模式的结论

最初讨论的 4 个写入模式：

- `append_rows`
- `replace_range`
- `replace_sheet_data`
- `overlay`

可以覆盖当前大多数高频场景，但如果目标是长期高度自由的通用工具，仅靠这 4 个裸模式并不够。

### 两种方向的比较结论

1. 仅保留 4 个写入模式
   - 优点：简单
   - 缺点：很快会遇到边界问题，例如清尾、保留表头、按哪一列判断追加位置、大表分块写入

2. 一开始就做成完全组合式写入引擎
   - 优点：理论自由度最高
   - 缺点：第一版配置复杂度过高，维护成本大

3. 当前推荐方向
   - 保留 4 个常用写入模式作为用户层预设
   - 同时补充少量关键增强项

当前确认采用第 3 种方向。

### 推荐第一阶段保留的 4 个写入模式

- `append_rows`
- `replace_range`
- `replace_sheet_data`
- `overlay`

### 推荐第一阶段补充的关键增强项

- `anchor`
- `detect_last_row_by_col`
- `clear_policy`
- `preserve_header_rows`
- `chunk_size`
- `writer_engine`

### 当前判断为高优先级且高频的增强项

以下能力比继续增加新模式更重要：

1. `clear_policy`
2. `detect_last_row_by_col`
3. `preserve_header_rows`
4. `chunk_size`
5. `writer_engine`

### 当前不建议第一阶段实现的高级能力

以下能力先预留，不作为第一阶段目标：

- `upsert`
- 横向追加（如 `append_cols`）
- 插入并下移（如 `insert_shift`）

### 当前待继续展开的内容

下次需要继续明确：

- Excel 写入配置 schema
- 各写入模式与增强项的组合规则
- 不同 writer engine 的切换条件
- 大表写入的分块阈值策略

## 待继续确认

- Excel 写入模式设计
- 飞书 Sheets 上传设计
- 错误处理与日志设计
- 测试与验证策略

