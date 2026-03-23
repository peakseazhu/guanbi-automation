# 仓库状态与恢复入口设计

> 状态：Approved
> 最近更新：2026-03-23
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
- publish hardening primitives

最新一次已确认的 fresh automated verification 结果为：

- `PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider` -> `98 passed`
- `PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-mainline-reconciliation;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider` -> `99 passed`

当前还必须同时记住：

- `pytest` 仍不在当前 shell PATH 中
- `feishu-broadcast` env 本身仍缺 `pytest / pydantic / PyYAML`
- 但该 env 已具备 `openpyxl / xlwings / pywin32`
- 根目录 `.packages` 已补齐 `pytest / pydantic / PyYAML`

因此当前可复现的 fresh verification 路径已经恢复为：

- `feishu-broadcast python + root .packages`

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
- Feishu readback / comparison support
- publish live verification service
- real-sample entrypoint
- 真实样本写入 / 读回 / comparison
- 真实资源边界摸底

同时已存在一条尚未收口的运行足迹：

- `.worktrees/publish-stage-task1/runs/live_verification/publish/20260322T054012Z`

同时已新增一条有效 evidence archive：

- `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`

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
- `publish hardening` primitive slice 已通过 PR #2 合入 `main`
- 主线只保留稳定阶段成果
- 未把 `publish live verification` 的脚手架和未完成证据直接并回
- 主线当前仍未具备非测试 `PublishStage` runtime wiring
- 当前 corrective worktree 已补上 explicit bounded target rectangle padding regression，并通过 focused/full verification

主线已经包含：

- publish contract
- publish source reader（含 streaming-safe 读取修复）
- feishu target planner 与 row/column-aware `plan_range_segments(...)`
- feishu sheets client adapter（含最小 `write_values_batch(...)` 路径）
- concrete publish writer
- publish stage
- explicit bounded target rectangle padding fix
- mapping manifest `segment_count / segment_write_mode / write_segments`

### 3.2 验证线 `publish-stage-task1`

当前验证线已经完成：

- 最近提交：
  - `b1bca69 docs: archive publish hardening implementation`
- publish live verification design
- live verification spec loader
- Feishu readback support
- publish live verification service
- real sample entrypoint
- 本地 real-sample spec：
  - `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.local.yaml`
- 历史运行足迹目录：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260322T054012Z`
- 首个有效 evidence archive：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`
  - 已落下 `request.json`、`source-metadata.json`、`target-metadata.json`、`write-plan.json`、`write-result.json`、`readback.json`、`comparison.json`
  - `comparison.json -> matches = true`
- live verification 最终 implementation archive：
  - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
- publish hardening implementation archive：
  - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-23-publish-hardening-implementation.md`
- validation line fresh full suite：
  - `PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider` -> `110 passed`

这意味着验证线当前状态是：

- 自动化代码与本地验证输入已到位
- 已同时具备历史运行足迹与有效 evidence archive
- 已经可以基于真实证据判断哪些内容值得选择性回灌 `main`

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

主线当前仍不应把 live verification 脚手架整体并入，而应：

- 保持 `publish foundation + publish hardening primitives` 的稳定状态
- 只继续选择性提升已经被真实证据证明、且已被主流程实际消费的 foundation 级能力
- readback / comparison contract 与 runtime-connected hardening claim 只有在主线出现明确消费者后再进入下一轮 selective promotion 判断

### 6.2 验证线下一步

验证线当前下一合理入口是：

- 保留 `20260322T054012Z` 为空足迹目录的历史事实
- 以 `20260323T022511Z` 作为首个有效 evidence archive、以 `2026-03-23-publish-hardening-implementation.md` 作为最新实现归档继续推进后续判断
- 若继续提升内容到 `main`，仍先做真实证据，再区分可被主线消费的通用能力与本地验证资产

## 7. 当前仍需持续跟踪的缺口

当前仍需持续跟踪的缺口如下：

- 已存在一条空的历史运行足迹目录，说明“跑过一次痕迹”和“证据闭环完成”仍不能混写
- 当前 shell 仍不具备直接 PATH 级 `pytest`
- 当前仍需要通过 `feishu-broadcast python + root .packages` 这条组合路径复现 fresh verification
- discovery / page snapshot / template / run planner / web 尚未开始实现
- `pyproject.toml`、`environment.yml`、`requirements.txt` 之间仍存在依赖治理收口空间
- 旧配置与真实资源映射仍主要停留在 legacy 证据层，尚未正式进入新模板系统

## 8. 当前结论

截至 2026-03-23，当前仓库的最准确认知是：

- `main` 仍是稳定基线，且当前状态已前进到 `publish foundation + publish hardening primitives`
- `publish-stage-task1` 仍是继续向真实资源推进的验证线，且现在已具备首个有效 evidence archive 与最终 implementation archive
- 当前 shell 仍没有 PATH 级 `pytest`，但主线与验证线都已经恢复出可复现的 fresh verification 路径
- 历史归档继续保留，但恢复入口必须先走权威文档与最新状态对账
