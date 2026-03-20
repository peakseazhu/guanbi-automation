# 2026-03-19 运行中心与筛选器模型细化会话归档

## 1. 本次会话触发点

用户明确要求后续每一次细化都要持续思考是否存在更优方法，并要求“更优”判断必须经过认真思考与测试支撑。

## 2. 本次新增且已确认的信息

本次会话新增并锁定了以下结论：

1. 运行中心采用五段式生命周期：
   - `RunBatchRequest`
   - `PreflightReport`
   - `RunBatchPlan`
   - `Execution`
   - `RunBatchManifest`
2. `run batch` 的归档必须显式保存：
   - `run-request.json`
   - `preflight-report.json`
   - `run-plan.json`
   - `batch-manifest.json`
3. 筛选器采用混合建模，而不是纯抽象模型或纯原始 payload 模型。
4. `extract_signature` 使用语义化后的标准结构生成，而不是直接对原始请求 JSON 字符串做哈希。

## 3. 本次证据对比

本轮基于已有样本做了覆盖面检查：

- `记录/all_ploy.txt` 共 4 组 payload
- 已出现的 `filterType`：
  - `BT`
  - `IN`
- 已出现的 `fdType`：
  - `STRING`
  - `DATE`
- 已出现的组合：
  - `BT + STRING`
  - `IN + STRING`
  - `IN + DATE`

并结合已验证文档确认：

- `selectorType=TIME_MACRO`
- `selectorType=DS_ELEMENTS`

结论是：

- 当前最优路径必须同时考虑 `filterType` 和 `selectorType`。
- 只按字段名写死或只按图表写死的设计都不成立。

## 4. 本次对主设计的升级

本次已同步进主设计的核心内容包括：

- “重大规划变更必须有证据对比或最小 spike 测试”的治理规则
- 混合式筛选器模型
- `DS_ELEMENTS` 的第一阶段落地策略
- extract signature 的规范化规则
- run center 的五段式生命周期
- 批次重跑保持旧 manifest 不可变

## 5. 当前仍待后续继续收敛的问题

- `TIME_MACRO` 预设与 UI 选择项的最终映射表
- `DS_ELEMENTS` 在线候选值查询接口
- 日期显示值与服务端真实语义是否存在特殊耦合
- workbook 和 publish 阶段的重跑复用策略

## 6. 本次会话输出文件

- `docs/plans/master-system-design.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-19-filter-model-and-run-center-refinement.md`
