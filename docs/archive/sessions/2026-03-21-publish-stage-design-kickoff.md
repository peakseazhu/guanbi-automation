# 2026-03-21 会话归档（Publish Stage Design Kickoff）

## 1. 本次目标

在 `workbook stage` 已完成并合并到 `main` 后，正式进入下一恢复点：

- `publish stage detailed design`
- 当前先收敛 `workbook output -> publish mapping contract`

本次仍不进入 publish 编码实现。

## 2. 已核对上下文

本次继续以以下文档作为当前权威上下文：

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/plans/2026-03-21-workbook-detailed-design.md`
- `docs/archive/sessions/2026-03-21-workbook-stage-completion.md`

当前仓库状态确认如下：

- 当前分支：`main`
- 最近合并提交：`7224171` `Merge branch 'workbook-stage-task1-3'`
- workbook 全量验证状态：`49 passed`
- 工作区中仅保留未跟踪 `tools/`，本次不处理

## 3. 当前已确认事实

结合 master 文档与 workbook 已实现状态，当前进入 publish 设计前已确认：

- `runtime contract` 已完成
- `extract runtime policy` 已完成
- `workbook detailed design` 已完成
- `workbook stage implementation` 已完成
- workbook 当前已能产出稳定的结果 workbook，并在 manifest 中记录 ingest / transform 证据
- `publish` 阶段仍未设计，当前唯一合理入口是先锁定 `workbook output -> publish mapping contract`

## 4. 当前待收敛问题

为了避免 publish 设计发散，首个待确认问题固定为：

- workbook transform 产出的最终发布内容，通常是“整张结果 sheet 直接发布”，还是“从 workbook 中一个或多个固定结果区块发布到飞书的多个目标 range”

当前该问题已经收敛，结论如下：

- publish 不收窄为“整张 sheet 直传”
- publish 与 workbook 一样采用受约束目标块思路，但执行器不同
- publish 源侧同时支持：
  - 整张计算表读取
  - 固定结果区块读取
- publish 目标侧同时支持：
  - 整个子表覆盖
  - 指定 range 覆盖
  - 从指定行列开始追加
- 写入飞书的是值，不是公式
- 表头策略默认：
  - `header_mode=exclude`
  - 仅在 mapping 显式声明时才允许带表头上传
- 常见业务形态为：
  - `1 job -> 1 result workbook -> 多个 publish source -> 同一个飞书大表下的多个子表`
  - 少数场景会分发到多个飞书大表

基于以上约束，当前推荐的 publish mapping 主路径为：

- 显式 `publish source + publish target` 契约
- 中间保留一层标准化 `publish dataset`
- 再由 Feishu writer 分批写入目标

当前已批准的 `publish mapping contract` 进一步收敛为：

- 核心对象为 `PublishMappingSpec`
- 一个 `job` 下可以声明多条 mapping
- 每条 mapping 只负责：
  - 从结果 workbook 的一个源位置读值
  - 整理成标准化 publish dataset
  - 写到一个飞书目标位置
- contract 分为三层：
  - `PublishSourceSpec`
  - `PublishTargetSpec`
  - `PublishMappingSpec`

`PublishSourceSpec` 当前边界：

- 源类型支持：
  - `sheet`
  - `block`
- 最少字段包含：
  - `source_id`
  - `sheet_name`
  - `read_mode`
  - `start_row`
  - `start_col`
  - 可选 `end_row`
  - 可选 `end_col`
  - `header_mode`

`PublishTargetSpec` 当前边界：

- 目标写入模式支持：
  - `replace_sheet`
  - `replace_range`
  - `append_rows`
- 最少字段包含：
  - `spreadsheet_token`
  - `sheet_id` 或稳定 `sheet_name`
  - `write_mode`
  - `start_row`
  - `start_col`
  - 可选 `end_row`
  - 可选 `end_col`
  - 可选 `append_locator_columns`

`PublishMappingSpec` 当前边界：

- 最少字段包含：
  - `mapping_id`
  - `source`
  - `target`

当前默认规则：

- 默认只更新值，不改飞书目标结构
- 默认不带表头上传
- `append_rows` 必须显式声明 `append_locator_columns`
- `replace_range` 必须能由配置边界与源数据尺寸共同确定唯一目标矩形
- 一个 mapping 不做多源混写

当前已批准的 `publish` 数据流固定为：

1. `resolve mappings + preflight`
2. `read workbook values -> publish dataset`
3. `write publish dataset -> feishu target`
4. `publish manifest`

其中：

- preflight 先校验结果 workbook、源区块和飞书目标是否可用
- 读取 workbook 时只取值，不取公式
- 中间 `publish dataset` 至少保留：
  - `mapping_id`
  - `source_range`
  - `header_mode`
  - `rows`
  - `row_count`
  - `column_count`
- publish manifest 至少保留：
  - `mapping_id`
  - `source_sheet/source_range`
  - `target_spreadsheet/target_sheet/target_range`
  - `write_mode`
  - `row_count`
  - `column_count`
  - `chunk_count`
  - `written_row_count`
  - `status`
  - `final_error`

## 5. 当前恢复点

如果会话再次中断，下一步应继续：

1. 输出 `publish stage detailed design` 的下一节：
   - 失败语义、分批写入、限流与幂等边界
2. 继续收敛 publish stage 的 source/target range 检测细则
3. 完成 publish 设计文档初稿
4. 设计批准后，写 implementation plan
