# 2026-03-23 会话归档（Next Session Handoff）

## 下次会话直接使用的接续内容

请无缝衔接 `D:\get_bi_data__1` 项目，不要重新发散，也不要回到修改 legacy `src/` 的路径。

先按固定顺序阅读以下文档：

1. `README.md`
2. `docs/plans/master-system-design.md`
3. `docs/plans/master-implementation-roadmap.md`
4. `docs/archive/decision-log.md`
5. `docs/plans/2026-03-22-mainline-validation-governance-design.md`
6. `docs/plans/2026-03-22-repository-state-and-recovery-design.md`
7. `docs/archive/sessions/2026-03-23-publish-live-verification-promotion.md`
8. 本文档 `docs/archive/sessions/2026-03-23-next-session-handoff.md`
9. 若继续验证线，再读：
   - `.worktrees/publish-stage-task1/README.md`
   - `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-design.md`
   - `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
   - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`

## 当前项目真实状态

- `main` 是稳定基线，只保留稳定阶段成果。
- `main` 已包含：
  - runtime contract
  - extract runtime policy
  - workbook foundation
  - publish foundation
  - 基于真实证据回灌的 `publish_source_reader` streaming-safe 修复
- 验证线是 `D:\get_bi_data__1\.worktrees\publish-stage-task1`，职责是继续承担 `publish live verification` 与后续候选提升判断。

## 当前最关键的新增事实

- 首个有效 publish live verification evidence archive 已形成：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`
- 该 evidence archive 已确认：
  - `comparison.json -> matches = true`
  - canonical source / readback shape = `58 x 127`
  - 写入按列切分为：
    - `ySyhcD!A1:CV58`
    - `ySyhcD!CW1:DW58`
- 旧目录 `.worktrees/publish-stage-task1/runs/live_verification/publish/20260322T054012Z` 仍为空目录，只能继续视为历史运行足迹，不能视为完成证据。

## 当前 Git 状态

- `main`
  - 最近一次功能性主线提交：`5db6b07 fix: promote streaming publish source reads`
  - 当前 handoff 会以 docs-only 方式补入 `origin/main`，恢复时应先看最新 session archive，再回看该功能基线
- `publish-stage-task1`
  - 当前验证线提交：`56c8641 fix: archive publish live verification results`
  - 已推送到：`origin/publish-stage-task1`
- 当前工作区状态：
  - 主线只剩未跟踪本地目录 `tools/`
  - 验证线工作区干净

## 当前可复现验证路径

### 主线

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

最近 fresh 结果：

- `87 passed`

### 验证线

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

最近 fresh 结果：

- `102 passed`

当前必须记住：

- shell PATH 里仍没有 `pytest`
- 但不需要再回到“先恢复环境”的旧路线，因为主线和验证线都已经恢复出可复现的 fresh verification 路径
- 当前默认验证解释器仍是：
  - `D:\miniconda3\envs\feishu-broadcast\python.exe`
  - 配合根目录 `.packages`

## 当前不应该再做的事

- 不回 legacy `src/`
- 不把验证线状态误写成“还没开始”
- 不把验证线状态误写成“所有 live verification 资产都应该并回 main”
- 不把空目录 `20260322T054012Z` 和有效 evidence archive `20260323T022511Z` 混写
- 不把本地 `real_sample.local.yaml`、真实 spreadsheet 标识、evidence archive 整体并入 `main`

## 当前最推荐的下一步

如果新会话只做一件事，就先做这件事：

- 梳理验证线里下一批“可能值得选择性回灌 `main` 的 foundation 候选项”

判断标准固定为：

1. 已被真实证据证明必要
2. 不依赖本机私有资源
3. 属于通用 foundation 能力，而不是一次性验证脚手架
4. 能在主线通过 fresh verification

## 当前已明确留在验证线的内容

- `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.local.yaml`
- `.worktrees/publish-stage-task1/guanbi_automation/live_verification/publish_real_sample.py`
- `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
- `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`

## 当前执行约定

- 继续使用 superpower 技能工作流
- 主代理和子代理继续统一使用 `gpt-5.4 + xhigh`
- 每次完成阶段性推进后，优先补权威文档与 handoff，再决定是否继续实现
