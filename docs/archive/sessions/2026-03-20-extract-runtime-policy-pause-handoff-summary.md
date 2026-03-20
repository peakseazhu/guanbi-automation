# 2026-03-20 会话暂停交接摘要（Extract Runtime Policy）

## 1. 当前全局状态

截至本次会话暂停前，项目方向继续保持为：

- 新项目实现代码必须从 0 构建。
- legacy `src/`、`logger/`、`记录/`、根目录 Excel 文件仅作为参考证据库。
- 三层文档治理继续有效：
  - 主规划文档
  - 每次对话单独归档
  - 决策日志
- 当前工程顺序仍锁定为：
  1. `runtime contract`
  2. `extract runtime policy`
  3. `workbook detailed design`

## 2. 本次会话完成的关键工作

### 2.1 补充证据并修正 extract runtime policy 方向

本次没有重新发散，也没有回到 workbook 或 legacy 路线，而是继续推进 `extract runtime policy`。

在讨论过程中，先用旧日志补证，确认：

- 旧链路确实存在长轮询样本：
  - `logger/log_15202603_1005.txt` 最长 `99s`
  - `logger/log_12202603_0850.txt` 最长 `72s`
  - `logger/log_17202601_0818.txt` 最长 `71s`
- 旧链路确实存在大表样本：
  - `logger/log_21202601_0818.txt` 的 `66 x 219336`
  - `logger/log_21202601_1356.txt` 的 `66 x 219336`
  - `logger/log_07202603_0850.txt` 的 `70 x 215501`
- 旧链路仍存在瞬时网络错误：
  - `logger/log_09202601_0818.txt` 的 `SSLError`
  - `logger/log_13202602_0818.txt` 的 `ConnectTimeout`

因此推翻了“统一偏紧默认预算”的主观方案，转而正式锁定更符合证据的方向。

### 2.2 已锁定的 Extract Runtime Policy 设计结论

本次会话中，用户已逐段确认以下设计：

1. extract 主链路拆成：
   - `submit`
   - `poll`
   - `download`
   - `extract_total_deadline`
2. 采用三段分离预算，而不是整条 extract 共用一套预算。
3. 正式引入三档 runtime profile：
   - `fast`
   - `standard`
   - `heavy`
4. profile 选择规则：
   - `extract template` 保存默认 `runtime_profile`
   - `run batch` 允许 `runtime_profile_override`
   - 实际执行使用 `override > template default`
5. 默认 profile 固定为：
   - `standard`
6. `PROCESSING` 等正常轮询状态不消耗错误重试预算。
7. 只有瞬时网络错误进入有限重试：
   - `network_connect_timeout`
   - `network_ssl_error`
8. extract 最终错误按最后失败阶段归因，不允许只记录模糊的 `extract_failed`。

### 2.3 已落地的文档同步

本次会话已新增或更新：

- 新增设计文档：
  - `docs/plans/2026-03-20-extract-runtime-policy-design.md`
- 新增实施计划：
  - `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`
- 新增本次设计归档：
  - `docs/archive/sessions/2026-03-20-extract-runtime-policy-design-approval.md`
- 更新主文档：
  - `docs/plans/master-system-design.md`
  - `docs/plans/master-implementation-roadmap.md`
- 更新决策日志：
  - `docs/archive/decision-log.md`

### 2.4 Git 状态

- 文档已提交
- 当前最新提交：
  - `ed0e767`
- 提交信息：
  - `docs: add extract runtime policy design and plan`

暂停前工作区是干净的。

## 3. 当前唯一正确恢复点

下次恢复时，不要重新讨论以下内容：

- 不要重新讨论是否先做 workbook
- 不要重新讨论是否回到 legacy `src/`
- 不要重新把 extract runtime policy 做回单一 `extract_polling`
- 不要重新把默认策略设成统一偏紧快失败

当前唯一正确恢复点是：

1. 先阅读：
   - `docs/plans/master-system-design.md`
   - `docs/plans/master-implementation-roadmap.md`
   - `docs/archive/decision-log.md`
   - `docs/plans/2026-03-20-extract-runtime-policy-design.md`
   - `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`
2. 然后直接按实施计划执行：
   - 从 `Task 1` 开始
3. 当前阶段仍然是：
   - `extract runtime policy implementation`
4. workbook 仍然必须排在后面

## 4. 下次要做的内容

下次继续时，应该直接进入：

- `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`

并从 `Task 1` 开始按 TDD 实施，核心工作包括：

1. 把当前扁平 `extract_polling` 升级为 profile-aware 配置结构
2. 增加 `template default + run override` 的 runtime profile 解析
3. 修正当前过于简化的 polling 语义
   - 现状问题：`poll_with_policy(...)` 看到任意 payload 就直接完成
   - 目标语义：`PROCESSING -> continue`, `DONE -> success`, `budget exhausted -> poll_timeout`
4. 增加 `submit` 与 `download` 的 request budget helper
5. 让 extract stage 真正执行：
   - `submit -> poll -> download`
6. 让 manifest 记录：
   - `template_runtime_profile`
   - `effective_runtime_profile`
   - `submit_* / poll_* / download_*`
   - `extract_total_elapsed_seconds`
   - `deadline_exhausted`
   - `final_error`
7. 再更新 preflight / stage gate / README

## 5. 当前最值得提醒的技术点

下次实现时最容易走错的地方有 4 个：

1. 不要把 `PROCESSING` 当成错误重试。
2. 不要把 `poll max_wait` 和 `extract total_deadline` 混为一层。
3. 不要只做 `poll`，而漏掉 `submit / download` 两段预算。
4. 不要只改 settings，不改 extract stage 和 manifest 语义。

## 6. 推荐新会话提示词

下面这段提示词可直接用于下次新会话开场：

```text
请无缝衔接 D:\get_bi_data__1 项目，不要重新发散，也不要回到修改 legacy src 的路径。

先阅读并以以下文档作为当前唯一权威上下文：
- docs/plans/master-system-design.md
- docs/plans/master-implementation-roadmap.md
- docs/archive/decision-log.md
- docs/plans/2026-03-20-extract-runtime-policy-design.md
- docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md
- docs/archive/sessions/2026-03-20-extract-runtime-policy-pause-handoff-summary.md

当前已锁定顺序仍然是：
1. runtime contract
2. extract runtime policy
3. workbook detailed design

当前状态：
- runtime contract 已完成
- extract runtime policy 设计已完成并已写入主文档、decision-log 与实施计划
- 最新文档提交为 ed0e767

当前恢复点：
- 不要重新讨论 workbook
- 不要重新讨论是否回到 legacy
- 不要把 extract runtime policy 做回单一 extract_polling
- 直接按 docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md 从 Task 1 开始执行

实现时必须遵守：
- 新代码从 0 构建，不改 legacy src
- 继续遵守三层文档治理
- 如发现更优路径，必须基于证据对比，不得主观改方向
- 先按 TDD 执行实施计划，再谈后续阶段
```
