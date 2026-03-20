# 观远 BI 自动化套件运行契约与阶段护栏设计

> 状态：Active
> 最近更新：2026-03-19
> 适用范围：新项目从 0 构建阶段
> 关联主文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`

## 1. 背景

历史日志已经证明，当前项目的主要失败并不集中在某一个业务步骤，而是集中在“系统没有稳定运行契约”：

- 环境依赖会漂移，直到运行时才暴露。
- 导出任务轮询缺少超时预算与错误分类。
- workbook 大表写入缺少尺寸护栏和策略切换。
- 日志缺少统一结构和稳定上下文。

这意味着，如果现在直接细化 workbook 设计，虽然能解决局部大表问题，但仍然会把全局入口护栏、错误分类和 manifest 契约留在后面补，最终导致返工。

## 2. 结论

当前更优路径不是“先细化 workbook”，也不是只零散补 `doctor + polling`，而是先建立一个正式的 `runtime contract`。

它的作用是：

1. 统一定义系统在运行前和运行中的基本约束。
2. 为 extract 阶段提供稳定的超时、重试、日志和 manifest 语义。
3. 为 workbook 阶段提供可继承的护栏结构，而不是再单独补一套。

因此推荐顺序固定为：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

## 3. 为什么这是当前最优顺序

### 3.1 方案对比

#### 方案 A：直接细化 workbook

优点：

- 能最快收敛 Excel 大表写入问题。

缺点：

- 仍然缺少全局运行前检查。
- 仍然缺少统一错误分类。
- 仍然缺少阶段级 manifest 语义。
- workbook 设计会反向依赖尚未锁死的轮询和失败分层规则。

结论：

- 只适合作为局部问题导向，不适合作为当前全局最优顺序。

#### 方案 B：只细化 doctor + polling

优点：

- 能优先解决环境依赖和 extract 阶段的高频不稳定问题。

缺点：

- 仍然没有把阶段护栏、manifest 字段和错误语义统一为正式契约。
- 对 workbook 的前置约束仍然是散的。

结论：

- 比方案 A 更好，但仍然不够完整。

#### 方案 C：先建立 runtime contract，再分阶段细化

优点：

- 先锁定全局入口护栏。
- 先锁定运行时语义和失败语义。
- 先锁定日志与 manifest 的最小稳定字段。
- 后续 extract 和 workbook 都能复用同一套约束模型。

缺点：

- 当前阶段文档工作量更高。

结论：

- 这是当前严格工程顺序下的最优路径。

## 4. Runtime Contract 的定义

`runtime contract` 不是某一个模块名，而是一组跨层共享的运行规则与数据契约。

它应覆盖以下 5 个部分：

1. `doctor contract`
2. `runtime policy contract`
3. `stage gate contract`
4. `error taxonomy contract`
5. `event + manifest contract`

### 4.1 Doctor Contract

负责回答“这个系统现在是否具备启动和执行的最基本条件”。

它只做运行前静态或轻量检查，不负责真正发起业务副作用。

至少包含：

- Python 版本
- 单一权威依赖清单的一致性
- 必需包是否可导入
- 基本目录是否存在且可写
- 必需环境变量是否齐全
- workbook / publish 所需本地能力是否在启用对应阶段时存在

输出应为 `DoctorReport`，而不是一堆控制台打印。

### 4.2 Runtime Policy Contract

负责回答“本次运行允许消耗多少时间和多少重试预算”。

它不是写死在客户端里的魔法数字，而是显式配置的一组预算模型。

至少包含：

- `connect_timeout`
- `read_timeout`
- `poll_interval`
- `max_wait`
- `max_retries`
- `backoff_policy`

该契约首先服务 extract 阶段，但必须设计成未来 workbook / publish 也可继承。

### 4.3 Stage Gate Contract

负责回答“某个阶段在当前上下文下是否允许执行”。

它和 `doctor` 的区别是：

- `doctor` 偏全局、偏静态
- `stage gate` 偏阶段、偏当前批次

例如：

- extract 阶段需要检查轮询预算是否完整。
- workbook 阶段需要检查模板文件是否存在、下载结果是否可解析、数据尺寸是否超阈值。
- publish 阶段需要检查目标表是否存在、数据形状是否可发送。

输出应为 `StageGateDecision`：

- `ready`
- `blocked`
- `degraded`

### 4.4 Error Taxonomy Contract

负责回答“发生错误时，系统如何给出稳定、可追踪、可聚合的错误类型”。

至少需要明确以下层级：

- `configuration_error`
- `doctor_failed`
- `authentication_error`
- `request_submit_error`
- `poll_timeout`
- `network_connect_timeout`
- `network_ssl_error`
- `payload_parse_error`
- `workbook_capability_error`
- `workbook_size_guardrail_triggered`
- `workbook_writer_error`
- `publish_auth_error`
- `publish_rate_limit_error`

这里的目标不是追求一开始就穷尽所有错误，而是先把高频故障做成稳定 taxonomy。

### 4.5 Event + Manifest Contract

负责回答“运行过程中最少必须记录哪些字段，才能确保事后可回溯”。

最小字段集至少应包含：

- `batch_id`
- `job_id`
- `extract_id`
- `stage_name`
- `chart_id`
- `task_id`
- `event_type`
- `error_code`
- `attempt`
- `timestamp`

设计原则：

- 结构化字段优先于纯文本日志。
- manifest 负责稳定归档，日志负责过程细节。
- 两者字段命名应保持可关联。

## 5. 生命周期中的位置

推荐将 `runtime contract` 放在如下链路中理解：

1. 加载项目配置
2. 生成 `DoctorReport`
3. 接收 `RunBatchRequest`
4. 生成 `PreflightReport`
5. 生成 `RunBatchPlan`
6. 为 extract 生成 `RuntimePolicy`
7. extract 执行
8. 为 workbook / publish 生成 `StageGateDecision`
9. 后续阶段执行
10. 汇总 `RunBatchManifest`

这里有一个关键边界：

- `doctor` 在 run request 之前也可以执行
- `stage gate` 必须在阶段真正执行前执行
- workbook 的部分 gate 只能在 extract 产物出现后再判断

因此不应把所有校验都硬塞进一个扁平 `preflight` 函数里。

## 6. 对 Extract 阶段的直接约束

在 `runtime contract` 建立后，extract 阶段必须立即继承以下规则：

- 所有 HTTP 调用必须显式使用 timeout policy。
- 轮询必须使用预算模型，不允许 `while 1`。
- 网络错误必须映射到稳定错误类型。
- manifest 中必须记录：
  - `task_id`
  - 最后状态
  - 尝试次数
  - 总等待时长
  - 最终错误类型

这样做的原因是：

- extract 是第一个生产里程碑。
- 如果 extract 阶段的运行契约不稳，后续 workbook 设计也没有稳定输入可依赖。

## 7. 对 Workbook 阶段的直接约束

在 `runtime contract` 建立后，workbook 设计不应从“怎么写 Excel”开始，而应从“什么情况下允许写 Excel”开始。

这意味着 workbook 设计必须继承：

- `StageGateDecision`
- `ErrorTaxonomy`
- `Event + Manifest`

在此基础上再继续细化：

- writer engine
- anchor
- clear policy
- chunking
- fallback

换句话说：

- `runtime contract` 决定 workbook 是否能安全进入
- `workbook design` 决定进入后如何执行

## 8. 当前建议的数据模型

第一阶段无需一次性把全部类都实现完，但设计上至少需要以下对象：

- `DoctorCheckResult`
- `DoctorReport`
- `TimeoutBudget`
- `RetryBudget`
- `PollingPolicy`
- `StageGateDecision`
- `RuntimeErrorInfo`
- `EventRecord`
- `ManifestRef`

原则如下：

- 先做最小稳定模型，不做过度抽象。
- 先覆盖 extract 的真实失败模式。
- workbook 和 publish 在字段上复用，而不是复制粘贴。

## 9. 当前实现顺序建议

下一轮实施规划应按以下顺序展开：

1. 设计并实现 `doctor` 的输入输出模型
2. 设计并实现 polling / timeout / retry policy
3. 设计并实现最小错误 taxonomy 与事件记录模型
4. 将 extract preflight 接到 runtime contract
5. 在 runtime contract 锁定后细化 workbook 设计

## 10. 当前不应做的事情

在 runtime contract 落地前，当前不建议：

- 直接开始 workbook writer engine 细节实现
- 直接开始 Excel 大表写入策略编码
- 让 workbook 自己定义一套独立错误码
- 在各阶段自己随意打印不结构化日志

这些做法短期看似推进更快，长期一定返工。

## 11. 输出影响

本设计一旦被采纳，会带来以下直接影响：

- `master-system-design` 中新增 `runtime contract` 章节。
- `master-implementation-roadmap` 中明确：extract-only 之前先锁运行契约基线。
- 后续 workbook 设计以该文档为前置条件，而不是独立起草。

## 12. 仍待后续继续收敛的问题

- `DoctorReport` 的最终展示形式是纯 JSON 还是同时提供 UI presenter。
- `backoff_policy` 采用固定分级退避还是指数退避。
- workbook 大表阈值是只看 `cell_count`，还是同时考虑列数和文件体积。
- publish 阶段是否需要与 extract 共享同一个 retry budget 模型。
