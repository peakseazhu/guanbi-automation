# 仓库状态与恢复入口设计

> 状态：Approved
> 最近更新：2026-03-22
> 关联文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-22-mainline-validation-governance-design.md`

## 1. 背景

当前仓库已经经历多轮中断与恢复，且 `main` 与 `.worktrees/publish-stage-task1` 分别承担不同职责：

- `main` 承担稳定阶段成果
- `publish-stage-task1` 承担 publish 真实落地验证

如果后续恢复时直接从旧 session archive 或单个 worktree 文档起步，容易把“当时现场状态”误读成“当前全局事实”。

本设计的目标是固定：

- 当前仓库资产的职责边界
- 恢复时的权威阅读顺序
- 哪些文档是现状，哪些只是历史证据

## 2. 当前仓库资产分类

### 2.1 主线实现与测试

以下目录是当前 `main` 的核心实现与验证资产：

- `guanbi_automation/`
- `tests/`
- `README.md`
- `pyproject.toml`

当前 `main` 已包含：

- runtime contract
- extract runtime policy
- workbook foundation
- publish foundation

最近一次已记录的 fresh automated verification 结果为：

- `pytest tests -v -p no:cacheprovider` -> `86 passed`

但本次会话重新尝试验证时，当前可访问环境已经暴露出新的复现阻塞：

- `pytest` 不在当前 shell PATH 中
- 历史 `D:\miniconda3\envs\feishu-broadcast\python.exe` 当前缺少 `pytest`
- `.venv + .packages` 可以启动 `pytest`，但在 collection 阶段缺少 `openpyxl` 与 `xlwings`

因此这里必须区分：

- 最近一次已记录通过的 full suite 结果
- 当前这台机器在本次会话里是否还能立即复现同样的 full suite

### 2.2 权威文档层

当前权威文档固定为：

1. `docs/plans/master-system-design.md`
2. `docs/plans/master-implementation-roadmap.md`
3. `docs/archive/decision-log.md`
4. `docs/plans/2026-03-22-mainline-validation-governance-design.md`
5. `docs/plans/2026-03-22-repository-state-and-recovery-design.md`

它们共同回答：

- 项目是什么
- 为什么这样设计
- 做到哪里了
- 当前应该往哪条线继续推进

### 2.3 历史归档层

以下文档属于历史归档，不是单独的当前权威入口：

- `docs/archive/sessions/*.md`
- `.worktrees/publish-stage-task1/docs/archive/sessions/*.md`

它们必须保留，以保证可以像 Git 历史一样回滚回溯，但使用规则固定为：

- 先读权威文档
- 再读最新状态对账文档
- 最后按需要翻历史归档

### 2.4 legacy 证据层

以下内容继续保留为证据，不进入新实现依赖：

- `src/`
- `logger/`
- `记录/`
- 根目录业务 `.xlsx`

它们的价值是：

- 提供真实接口样本
- 提供历史失败模式
- 提供业务映射经验
- 约束 workbook / publish 的现实边界

### 2.5 验证线资产

当前验证线为：

- `.worktrees/publish-stage-task1`

其职责不是替代 `main`，而是继续推进：

- publish live verification 设计
- live verification spec 与本地 real-sample spec
- Feishu readback / batch write support
- publish live verification service
- real-sample entrypoint
- 真实样本写入 / 读回 / comparison
- 真实资源边界摸底

同时已存在一条尚未收口的运行足迹：

- `.worktrees/publish-stage-task1/runs/live_verification/publish/20260322T054012Z`

### 2.6 本机环境与临时工具层

以下内容属于本机环境、临时工具或编辑器层，不是当前项目方向的权威事实来源：

- `.env`
- `.venv/`
- `.packages/`
- `.vscode/`
- `tools/`

它们的作用是：

- 提供本机运行凭据、虚拟环境与调试脚手架
- 为本地修复、排障、网络绕行等一次性动作提供工具

恢复规则固定为：

- 只有在需要执行、排障或核对本机环境时才读取这些内容
- 它们不能替代权威文档来决定项目方向、阶段状态或晋升判断

### 2.7 当前执行约定

当前恢复和推进时，默认同时遵守以下操作约定：

- 当前协作方式是单人推进
- `main` 负责稳定、可用、可作为下一次恢复点的成果
- 验证线负责把真实资源验证直接推到边界，再把已证实可沉淀的部分回灌主线
- 后续主代理和子代理默认统一使用 `gpt-5.4 + xhigh`
- 新会话继续使用 superpower 技能工作流，至少保证技能检查、计划/实施闭环和完成前验证

## 3. 当前真实状态

### 3.1 主线 `main`

当前 `main` 的真实状态是：

- `publish foundation` 已从验证线萃取进入主线
- 主线只保留稳定阶段成果
- 未把 `publish live verification` 的脚手架和未完成证据直接并回

主线已经包含：

- publish contract
- publish source reader
- feishu target planner
- feishu sheets client adapter
- publish stage
- publish runtime wiring

### 3.2 验证线 `publish-stage-task1`

当前验证线已经完成：

- 最近提交：
  - `350b903 feat: add publish live verification entry`
- publish live verification design
- live verification spec loader
- Feishu readback / batch write support
- publish live verification service
- real sample entrypoint
- 本地 real-sample spec：
  - `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.local.yaml`
- 一次运行足迹目录：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260322T054012Z`

但当前仍未完成：

- 真实样本运行证据归档
  - 当前时间戳目录仍为空，缺少 `request.json`、`write-plan.json`、`comparison.json` 等关键文件
- live verification 最终 implementation archive
- 真实写入 / 读回 / comparison 成功证据的晋升判断

这意味着验证线当前状态是：

- 自动化代码与本地验证输入已到位
- 已经出现一次运行足迹
- 有效 evidence archive 仍未收口

## 4. 当前明确存在的历史/现状混淆点

### 4.1 旧 session archive 中的现场状态

部分归档文档记录的是当时现场，而不是当前全局事实。例如：

- dirty worktree
- 无法提交 Git metadata
- “下一步先补 Task 6/7 提交”

这些内容在其时间点是真实的，但不能再被当成当前恢复入口。

### 4.2 主设计与实现进度的错位

`master-system-design` 描述的是全产品目标全景，但当前实现只完成了后半段执行内核：

- 已完成：runtime contract / extract / workbook / publish foundation
- 未完成：discovery / page snapshot / extract template / job template / run planner / web

因此恢复时必须同时看设计目标和当前实现事实，不能只看其一。

## 5. 恢复阅读顺序

### 5.1 从主线恢复

未来任何新会话若以 `main` 为工作线，固定阅读顺序为：

1. `README.md`
2. `docs/plans/master-system-design.md`
3. `docs/plans/master-implementation-roadmap.md`
4. `docs/archive/decision-log.md`
5. `docs/plans/2026-03-22-mainline-validation-governance-design.md`
6. `docs/plans/2026-03-22-repository-state-and-recovery-design.md`
7. 最新主线 session archive
8. 当前要进入的具体阶段设计与实施计划

### 5.2 从验证线恢复

若继续 `publish-stage-task1`，固定阅读顺序为：

1. 主线恢复顺序 1-6
2. `.worktrees/publish-stage-task1/README.md`
3. `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-design.md`
4. `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
5. `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-design-approval.md`
6. 该验证线的最新 session archive

## 6. 下一步

### 6.1 主线下一步

主线当前不应继续扩展 publish foundation，而应：

- 保持稳定
- 等待验证线拿到真实样本证据后，再决定是否选择性提升

### 6.2 验证线下一步

验证线当前唯一合理入口是：

- 先恢复可执行验证环境，使 focused verification 与 full suite 可以重新运行
- 先跑 live verification focused verification
- 执行 real sample 写入、读回和 comparison
- 让 `runs/live_verification/publish/<timestamp>/` 真正落下 evidence JSON 文件
- 补写 `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
- 再决定哪些内容值得晋升进 `main`

## 7. 当前仍需持续跟踪的缺口

当前仍需持续跟踪的缺口如下：

- publish live verification 尚未形成有效 evidence archive
- 已存在一条空的运行足迹目录，说明“跑过一次痕迹”和“证据闭环完成”不能混写
- 当前可访问测试环境存在漂移：
  - `feishu-broadcast` env 缺 `pytest`
  - `.venv + .packages` 缺 `openpyxl` 与 `xlwings`
- discovery / page snapshot / template / run planner / web 尚未开始实现
- `pyproject.toml`、`environment.yml`、`requirements.txt` 之间仍存在依赖治理收口空间
- 旧配置与真实资源映射仍主要停留在 legacy 证据层，尚未正式进入新模板系统

## 8. 当前结论

截至 2026-03-22，当前仓库的最准确认知是：

- `main` 已是稳定的 publish foundation 基线
- `publish-stage-task1` 是继续向真实资源推进的验证线，且 live verification 代码路径与本地 spec 已经到位
- 验证线已出现一次运行足迹，但有效 evidence archive 和最终 implementation archive 仍未完成
- 当前 shell 可访问的测试环境还不能直接复现历史 full suite，需要先修复依赖漂移
- 历史归档继续保留，但恢复入口必须先走权威文档与最新状态对账
