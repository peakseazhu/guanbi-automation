# Publish Stage Detailed Design

> 状态：Approved
> 最近更新：2026-03-21
> 前置阶段：`runtime contract`、`extract runtime policy`、`workbook stage`
> 后续阶段：`publish stage implementation plan`
> 关联文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-21-workbook-detailed-design.md`

## 1. 背景

`workbook stage` 已完成后，当前正式进入 `publish` 阶段细化。

这一阶段的目标不是做一个通用飞书脚本，也不是把结果 workbook 整本无差别上传，而是把 workbook transform 已经产出的稳定结果值，按明确映射，发布到飞书 Sheets 的明确目标子表和范围。

当前设计继续遵守：

1. 新项目实现代码从 0 构建
2. 不回到 legacy `src/`
3. publish 设计必须复用 runtime contract 的 stage gate、error taxonomy 与 manifest 语义
4. publish 必须优先满足“日更报表稳定更新”的业务现实，而不是先追求最自由的上传方式

## 2. 已确认业务事实

本轮澄清后，publish 阶段的关键事实已经收敛为：

- publish 的输入来自 `workbook_transform` 产出的结果 workbook
- 一个结果 workbook 中通常包含：
  - 多个底表
  - 多个计算结果表
- publish 的真实目标通常是：
  - 将多个计算结果表或结果区块
  - 上传到飞书一个或多个 spreadsheet 的多个子表
- 大多数情况下：
  - 多个结果会发布到同一个飞书 spreadsheet 下的多个子表
- 少数情况下：
  - 不同结果会分发到多个 spreadsheet
- 源侧必须同时支持：
  - 整张计算表读取
  - 固定结果区块读取
- 目标侧必须同时支持：
  - 整个子表覆盖
  - 指定范围覆盖
  - 从指定行列开始追加
- 写入飞书的是值，不是公式
- 默认应保留飞书目标中的既有结构，只更新值
- 表头策略默认应为：
  - 不上传表头
  - 仅在 mapping 显式声明时才允许带表头上传

## 3. 历史证据

### 3.1 已被验证的有效链路

legacy 资料已经证明以下链路成立：

- 读取结果 workbook 的结果区
- 查询飞书 spreadsheet 的子表元数据
- 按明确 range 向飞书写二维值
- 大表写入需要分批

这说明：

- “Excel 计算结果 -> 飞书 Sheets” 的业务链路成立
- 飞书发布不是全新未知能力
- 新系统可以继承业务经验，但不能继承旧脚本的耦合组织方式

### 3.2 不应继承的旧实现形态

legacy `src/api/feishu_client.py` 和相关审计记录同时暴露出：

- 客户端是一次性脚本，不是稳定发布层
- token、目标和调用方式存在明显硬编码
- 失败语义不足
- 不能支撑 mapping 级归档、重试和重跑

这意味着 publish v1 的关键不是“再包一层旧调用”，而是先把：

- source contract
- target contract
- chunk write
- manifest

正式建模。

### 3.3 当前证据对方案的限制

结合 workbook 阶段已经锁定的边界，当前证据明确支持：

- publish 应复用 workbook 的“受约束块”思想
- 但 publish 不能直接复制 workbook 的执行器
- workbook 负责结构保留与计算
- publish 负责值读取、目标解析、分批写入和外部副作用归档

## 4. 方案对比

### 4.1 方案 A：直接 workbook 读取后立刻写飞书

做法：

- 每个 mapping 直接从 workbook 读取值
- 读取后立即调用飞书写入

优点：

- 实现最短

缺点：

- 数据读取与外部副作用耦合
- 中断后难以判断“本次到底准备发布什么”
- mapping 级诊断、重试和重跑边界弱

结论：

- 不采用

### 4.2 方案 B：显式 `publish source + publish target` 契约，中间保留标准化 dataset

做法：

- 先按 mapping 从 workbook 读取值
- 生成标准化 `publish dataset`
- 再由 Feishu writer 分批写入目标

优点：

- 同时支持整表源与块源
- 同时支持覆盖与追加目标
- 读值与外部副作用解耦
- 更适合归档、重试、重跑与失败诊断

缺点：

- 比直接上传多一层中间数据结构

结论：

- 当前采用该方案

### 4.3 方案 C：先让 workbook 输出统一 publish outputs，再由 publish 消费

做法：

- 先要求 workbook 阶段显式产出 publish-specific outputs
- publish 只消费这些 outputs

优点：

- 阶段边界最干净

缺点：

- 反向抬高 workbook 复杂度
- 当前会把已稳定的 workbook 边界重新拉回讨论

结论：

- 当前阶段不采用

## 5. 设计结论

### 5.1 阶段角色

`publish` 的职责：

- 消费一个 job 的结果 workbook
- 按显式 mapping 读取一个或多个结果源
- 归一化为标准化 publish dataset
- 分批写入飞书目标
- 记录 mapping 级与 job 级 publish 证据

它不负责：

- 再次触发 Excel 计算
- 写公式到飞书
- 自动创建业务结构
- 在无边界情况下自由猜测源区块或目标范围

### 5.2 v1 边界

publish v1 的正式边界为：

- `1 job -> 1 result workbook -> 多个 publish mappings`
- 一个 mapping 只负责：
  - 一个 workbook source
  - 一个飞书 target
- 源支持：
  - `sheet`
  - `block`
- 目标支持：
  - `replace_sheet`
  - `replace_range`
  - `append_rows`
- 默认写入值，不写公式
- 默认不上传表头
- 默认不自动创建飞书子表
- 默认 mapping 串行执行
- 默认 chunk 串行执行

## 6. Mapping Contract

publish v1 以 `PublishMappingSpec` 作为最小发布单元。

一个 job 可以声明多条 mapping，每条 mapping 只绑定一个源与一个目标，不做多源混写。

### 6.1 `PublishSourceSpec`

最少包含：

- `source_id`
- `sheet_name`
- `read_mode`
- `start_row`
- `start_col`
- 可选 `end_row`
- 可选 `end_col`
- `header_mode`

源模式固定支持：

- `sheet`
- `block`

### 6.2 `PublishTargetSpec`

最少包含：

- `spreadsheet_token`
- `sheet_id` 或稳定 `sheet_name`
- `write_mode`
- `start_row`
- `start_col`
- 可选 `end_row`
- 可选 `end_col`
- 可选 `append_locator_columns`

目标模式固定支持：

- `replace_sheet`
- `replace_range`
- `append_rows`

### 6.3 `PublishMappingSpec`

最少包含：

- `mapping_id`
- `source`
- `target`

### 6.4 默认规则

当前默认规则固定为：

- 默认只更新值，不改飞书目标结构
- 默认 `header_mode=exclude`
- `append_rows` 必须显式声明 `append_locator_columns`
- `replace_range` 必须能由配置边界与源数据形状共同确定唯一目标矩形
- 一个 mapping 不做多源混写

## 7. Source 范围检测规则

source 范围检测的正式规则为：

- `start_row/start_col` 是唯一允许的识别锚点
- 识别只在当前结果 workbook 的当前 source 内进行
- 如果给了 `end_row/end_col`，系统只能在该矩形内识别有效区域
- 如果未给完整结束边界，系统只能在锚点右下做保守识别
- 不允许回扫锚点上方或左侧
- `None` 和空字符串视为空
- 中间空单元格不截断数据区，只裁掉尾部空行与尾部空列

### 7.1 `sheet` 源

语义：

- 从一个计算结果表中读取一整块有效结果区
- 但“整张表”并不代表无边界读取整个 sheet

规则：

- 从锚点向右下识别有效结果区
- 默认裁掉尾部空行和尾部空列
- 表头是否进入最终 dataset 由 `header_mode` 决定

### 7.2 `block` 源

语义：

- 从计算结果表中的固定结果区读取

规则：

- `start_row/start_col` 必填
- `end_row/end_col` 推荐显式给出
- 未给完整边界时仍然只允许保守识别，不允许全表自由猜测

### 7.3 表头策略

`header_mode` 当前固定支持：

- `exclude`
- `include`

默认是 `exclude`。

这意味着：

- 读取范围的识别与表头策略解耦
- `exclude` 只影响 dataset 输出是否跳过首行
- 不改变源区本身的定位逻辑

## 8. Target 范围检测规则

publish 目标解析必须比 workbook 更严格，因为它是外部副作用平面。

### 8.1 目标定位

每个 target 必须显式声明：

- `spreadsheet_token`
- `sheet_id` 或稳定 `sheet_name`

推荐执行顺序：

1. 先通过飞书 metadata 查询目标 spreadsheet
2. 将目标子表解析为稳定对象
3. 再计算实际写入范围

不允许：

- 仅凭模糊名称匹配目标子表
- 在未解析出唯一子表前继续写入

### 8.2 `replace_sheet`

语义：

- 并不是删除整张子表结构
- 而是在该子表内，从声明锚点开始的目标数据区做整块值替换

默认行为：

- 只清值
- 不清结构
- 由锚点控制是否保留表头和说明区

### 8.3 `replace_range`

语义：

- 在目标子表的显式范围内覆盖写入值

规则：

- 必须先得到唯一目标矩形
- 允许两种确定方式：
  - 显式 `end_row/end_col`
  - 由 `start_row/start_col + dataset 形状` 唯一推导
- 如果无法唯一确定，直接 `blocked`

### 8.4 `append_rows`

语义：

- 在显式锚点内定位有效末行，再向下追加

规则：

- 末行判断默认只看 `append_locator_columns`
- 这些列号按飞书目标子表的绝对列号解释
- 如果 locator 列在锚点以下都为空，则从 `start_row` 开始写第一批
- 不允许通过整张子表自由猜测末行

## 9. 数据流与执行顺序

publish v1 的执行顺序固定为：

1. `resolve mappings + preflight`
2. `read workbook values -> publish dataset`
3. `write publish dataset -> feishu target`
4. `publish manifest`

### 9.1 `resolve mappings + preflight`

这一阶段至少要检查：

- 结果 workbook 是否存在
- source 的 sheet / block 是否可读
- 飞书目标是否存在且可唯一解析
- 本次每个 mapping 的预期 `row_count / column_count / cell_count`

### 9.2 `publish dataset`

中间标准化数据层至少保留：

- `mapping_id`
- `source_range`
- `header_mode`
- `rows`
- `row_count`
- `column_count`

设计原因：

- 将 source 读取与 target 写入解耦
- 为 chunk 写入和 manifest 归档提供稳定输入

### 9.3 Feishu 写入

写入阶段固定原则：

- 只写值
- 不写公式
- 不默认修改结构
- 不把 dataset 整块直接压给单次请求
- 必须先按 shape 分 chunk 再写

## 10. 失败语义、重试与重跑边界

### 10.1 Mapping 级状态

publish 的最小执行与诊断单元是 `mapping`，而不是整个 job。

每个 mapping 至少有以下状态：

- `blocked`
- `failed`
- `completed`
- `skipped`

### 10.2 `partial_write`

当前不单独引入 `partial_success` 作为主状态。

更优路径是：

- 主状态仍使用 `failed`
- manifest 中额外记录：
  - `chunk_count`
  - `successful_chunk_count`
  - `failed_chunk_index`
  - `partial_write`

### 10.3 分批写入

publish dataset 必须按 `row_count / column_count / cell_count` 先切 chunk，再写飞书。

v1 固定规则：

- chunk 串行执行
- mapping 串行执行
- 同一 spreadsheet 下的多个子表先不做并发抢写

### 10.4 重试边界

publish retry 只服务“瞬时问题”，不服务“配置错误”。

可重试：

- 显式 rate limit
- 瞬时网络错误
- 短时服务不可用

不应重试：

- 鉴权失败
- 目标子表不存在
- range 非法
- source 配置错误

### 10.5 幂等边界

`replace_sheet` 与 `replace_range` 更接近天然幂等。

`append_rows` 默认不是天然幂等，因此当前正式规则为：

- 同一 batch / 同一 mapping / 同一目标的追加式重跑默认 `blocked`
- manifest 必须记录 append 前后末行与 source 指纹
- 若未来业务需要更强追加重跑能力，再新增显式策略

### 10.6 空数据策略

当前推荐默认：

- `empty_source_policy = skip`

这意味着：

- 空数据不默认视为“清空飞书目标”
- 只有 mapping 显式声明时，才允许用空结果覆盖目标

## 11. Manifest 与归档结构

publish 归档仍挂在：

`runs/.../jobs/<job_run_id>/publish/`

推荐结构：

```text
publish/
  manifest.json
  mappings/
    <mapping_id>.json
  datasets/
    <mapping_id>.json
```

其中：

- `datasets/` 是否长期持久化，可由后续实现按配置控制
- 但 manifest 必须至少保留数据形状和目标信息

### 11.1 Job 级 manifest

至少包含：

- `batch_id`
- `job_id`
- `stage_name`
- `result_workbook_path`
- `mapping_count`
- `completed_mapping_count`
- `failed_mapping_count`
- `blocked_mapping_count`
- `skipped_mapping_count`
- `final_status`
- `final_error`

### 11.2 Mapping 级 manifest

至少包含：

- `mapping_id`
- `source`
  - `sheet_name`
  - `read_mode`
  - `resolved_range`
  - `header_mode`
- `target`
  - `spreadsheet_token`
  - `sheet_id`
  - `sheet_name`
  - `write_mode`
  - `resolved_target_range`
- `dataset_shape`
  - `row_count`
  - `column_count`
  - `cell_count`
- `write_summary`
  - `chunk_count`
  - `successful_chunk_count`
  - `written_row_count`
  - `partial_write`
- `status`
- `final_error`
- `events`

### 11.3 Append 证据

对于 `append_rows`，manifest 还必须记录：

- `append_anchor`
- `append_locator_columns`
- `previous_last_row`
- `new_last_row`
- `source_fingerprint`

### 11.4 空数据证据

对于空数据源，还必须显式记录：

- `empty_source`
- `empty_source_policy`
- 最终 `status`

## 12. 配置草图

```yaml
publish:
  chunk_row_limit: 500
  empty_source_policy: skip
  mappings:
    - mapping_id: calc_sheet_1_to_b1
      source:
        source_id: calc_sheet_1
        read_mode: sheet
        sheet_name: 计算表1
        start_row: 2
        start_col: 1
        header_mode: exclude
      target:
        spreadsheet_token: sheet_token_b
        sheet_id: sub_sheet_1
        write_mode: replace_sheet
        start_row: 2
        start_col: 1

    - mapping_id: calc_block_3_to_c1
      source:
        source_id: calc_block_3
        read_mode: block
        sheet_name: 计算表3
        start_row: 5
        start_col: 2
        end_row: 18
        end_col: 10
        header_mode: include
      target:
        spreadsheet_token: sheet_token_c
        sheet_id: sub_sheet_1
        write_mode: replace_range
        start_row: 3
        start_col: 2

    - mapping_id: calc_sheet_4_append
      source:
        source_id: calc_sheet_4
        read_mode: sheet
        sheet_name: 计算表4
        start_row: 2
        start_col: 1
        header_mode: exclude
      target:
        spreadsheet_token: sheet_token_b
        sheet_id: sub_sheet_4
        write_mode: append_rows
        start_row: 2
        start_col: 2
        append_locator_columns: [2, 3, 4]
```

## 13. 失败语义

publish v1 至少需要稳定区分：

- `publish_auth_error`
- `publish_rate_limit_error`
- `publish_target_missing`
- `publish_range_invalid`
- `publish_source_read_error`
- `publish_write_error`
- `publish_append_rerun_blocked`

关键要求：

- source 无法稳定识别时，不允许猜测性发布
- target 无法唯一解析时，不允许继续写入
- chunk 部分写入时，必须显式记录 `partial_write`
- `append_rows` 的危险重跑必须在进入写入前显式阻断

## 14. 测试边界

单元测试至少覆盖：

- `PublishMappingSpec` 的最小结构校验
- source `sheet / block` 范围读取
- `header_mode=exclude/include`
- target `replace_range` 的唯一矩形解析
- `append_rows` 的末行定位
- chunk 切分
- 空数据 `skip`
- append 重跑阻断

集成测试至少覆盖：

- 一个 job 从同一结果 workbook 读取多个 source
- 多个 mapping 发布到同一个 spreadsheet 的多个子表
- `replace_sheet / replace_range / append_rows` 三种目标模式
- publish manifest 记录 mapping 级证据与 chunk 摘要

后续验证至少补：

- 飞书阶段限流与重试验证
- append 模式在真实业务表上的重跑保护验证
- publish chunk 阈值与默认值验证

## 15. 当前仍保留的未决项

本次设计已锁定 publish v1 主模型，但以下问题仍需在实施期基于测试继续收敛：

- chunk 大小与单次请求的安全默认值
- publish retry budget 的精确数值
- `datasets/` 是否默认长期持久化
- `append_rows` 是否需要业务键去重增强策略

## 16. 后续入口

本设计批准后，下一步不是直接写 publish 代码，而是：

1. 写 publish implementation plan
2. 按 TDD 从 Task 1 开始执行
3. 在实施过程中继续把验证证据回写三层文档
