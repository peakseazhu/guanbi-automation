# 2026-03-19 多任务架构细化会话归档

## 1. 本次会话触发点

用户确认整体方向基本符合预期，并额外强调两个关键要求：

1. 需要通过友好的可视化界面点击面板和筛选条件来确认下载配置。
2. 存在多个配置文件任务，规划时必须参考旧文档中的共享与去重结论，并收敛出更好的工程化实践路径。

## 2. 本次新增且已确认的信息

本次会话新增并锁定了以下架构结论：

1. 产品入口仍是本地 Web 控制台，但工程落地顺序采用 `Core-first, Web-ready`。
2. 系统正式采用 `extract template + job template + run batch` 三层执行模型。
3. 多 job 同批次执行与 extract 去重共享是核心能力，不是附加能力。
4. 新项目代码结构从原先较粗的 `integrations/runtime` 进一步细化为：
   - `bootstrap`
   - `domain`
   - `application`
   - `execution`
   - `infrastructure`
   - `web`
5. 当前所有规划文档都被视作历史记录；`master` 文档只是当前全局最优版本，后续必须持续复盘和修正。

## 3. 对旧规划的吸收结果

本次重新吸收了旧规划中最有价值的一部分结论，即：

- 配置组织应采用 `project + extracts + jobs` 的三层模型。
- 同一个图表在不同筛选条件下应保存为不同 extract，而不是运行时临时变形。
- 多个任务间的共享只发生在同一运行批次内。
- 历史下载文件保留归档，但不作为次日默认复用缓存。

## 4. 本次对主设计的关键升级

本次已将以下内容同步进主设计：

- 五个用户工作区：资源浏览、抽取配置、任务编排、运行中心、归档查看。
- 模块级分层和严格调用边界。
- `run batch / extract run / job run` 模型。
- `run planner` 作为批次计划展开与去重核心组件。
- 多层 manifest 结构和批次归档目录。

## 5. 本次对主实施路线的关键升级

本次已将实施路线调整为：

1. 文档治理与框架锁定
2. 新项目骨架与基础设施
3. 观远发现与页面快照
4. 模板模型与运行批次规划
5. preflight 与 extract-only
6. 本地 Web 控制台
7. Workbook 阶段
8. Feishu Publish 阶段
9. 硬化与验收

## 6. 当前最重要的工程结论

当前最重要的工程结论不是“怎么画 UI”，而是：

- 先把抽取模型、任务模型和批次运行模型定稳。
- 再让 UI 去消费这些稳定模型。
- 否则多任务编排、共享去重、运行归档会在后续持续返工。

## 7. 仍待后续继续收敛的问题

- Web 页面级信息架构与页面间切换逻辑。
- `DS_ELEMENTS` 候选值接口能力边界。
- Excel 写入规则模型最终 schema。
- Feishu Sheets 的限流、重试和幂等策略。

## 8. 本次会话输出文件

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/plans/2026-03-19-from-scratch-guanbi-automation-implementation-plan.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-19-multi-task-architecture-refinement.md`

## 9. 后续细化补记：运行中心与筛选器建模

在后续同日细化中，又新增并验证了两类关键结论：

1. 运行中心采用五段式生命周期：
   - `RunBatchRequest`
   - `PreflightReport`
   - `RunBatchPlan`
   - `Execution`
   - `RunBatchManifest`
2. 筛选器采用混合建模：
   - 页面快照保留 selector 原始元数据
   - extract template 保存 `selector_ref + template_payload + dynamic_rule/literal_value + display_value_policy`

本轮证据对比如下：

- `记录/all_ploy.txt` 的 4 组 payload 已覆盖：
  - `BT + STRING`
  - `IN + STRING`
  - `IN + DATE`
- `docs/plans/2026-03-19-guanbi-live-verification.md` 已确认：
  - `selectorType=TIME_MACRO`
  - `selectorType=DS_ELEMENTS`

因此本轮将以下原则提升为主设计规则：

- 更优规划路径进入 `master` 前，必须有证据对比或最小测试支撑。
- `displayValue` 默认不进入 extract signature，先按派生展示值处理；如后续 spike 证明其影响结果，再回调规则。
- `DS_ELEMENTS` 在线候选值接口不作为第一阶段阻塞项，先以 literal 模式落地。
