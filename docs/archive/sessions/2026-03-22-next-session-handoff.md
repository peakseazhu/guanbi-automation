# 2026-03-22 会话归档（Next Session Handoff）

## 下次会话直接使用的接续内容

请无缝衔接 `D:\get_bi_data__1` 项目，不要重新发散，也不要回到修改 legacy `src/` 的路径。

先按固定顺序阅读以下文档：

1. `README.md`
2. `docs/plans/master-system-design.md`
3. `docs/plans/master-implementation-roadmap.md`
4. `docs/archive/decision-log.md`
5. `docs/plans/2026-03-22-mainline-validation-governance-design.md`
6. `docs/plans/2026-03-22-repository-state-and-recovery-design.md`
7. `docs/archive/sessions/2026-03-22-full-repository-state-reconciliation.md`
8. 若继续验证线，再读：
   - `.worktrees/publish-stage-task1/README.md`
   - `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-design.md`
   - `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
   - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-design-approval.md`

当前项目真实状态如下：

- `main` 是稳定基线，只保留稳定阶段成果。
- `main` 已完成并保留：
  - runtime contract
  - extract runtime policy
  - workbook foundation
  - publish foundation
- 验证线是 `D:\get_bi_data__1\.worktrees\publish-stage-task1`，职责是继续推进 `publish live verification`。
- 验证线已经具备：
  - live verification spec / local spec
  - Feishu readback / batch write support
  - live verification service
  - real-sample entrypoint
- 验证线本地 real sample spec 已存在：
  - `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.local.yaml`
- 验证线当前还有一个关键未完成点：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260322T054012Z` 已存在，但它是空目录，只能算运行足迹，不能算有效 evidence archive
- 仍缺：
  - 真实写入 / 读回 / comparison evidence
  - `docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
  - 基于真实证据决定哪些内容值得再萃取回 `main`

当前必须记住的判断：

- 不要把验证线状态误写成“还没开始”，因为代码和本地 spec 已经到位。
- 也不要把当前状态误写成“验证已经完成”，因为 evidence archive 还没有形成。
- 空的时间戳目录不等于验证完成。

当前本机环境还存在 fresh verification 阻塞，必须先处理：

- 当前 shell 里 `pytest` 不在 PATH
- 历史 `D:\miniconda3\envs\feishu-broadcast\python.exe` 当前缺少 `pytest`
- `D:\get_bi_data__1\.venv\Scripts\python.exe` 配合 `.packages` 可以启动 `pytest`，但 collection 阶段缺 `openpyxl` 与 `xlwings`

所以下一步严格顺序是：

1. 先恢复可执行验证环境，保证 focused verification 和 full suite 能重新运行
2. 进入验证线 `publish-stage-task1`
3. 运行 live verification focused verification
4. 执行 real sample 写入、读回、comparison
5. 让 `runs/live_verification/publish/<timestamp>/` 真正落下 `request.json`、`write-plan.json`、`readback.json`、`comparison.json` 等证据文件
6. 补写最终 implementation archive
7. 再判断哪些 live verification 成果可以晋升回 `main`

当前不允许做的事：

- 不回 legacy `src/`
- 不把未收口的验证层内容直接并入 `main`
- 不跳过 superpower 技能工作流
- 不降低模型档位；主代理和子代理统一使用 `gpt-5.4 + xhigh`
- 不把“历史通过记录”当成“当前 fresh verification 已通过”

当前 Git 关键信息：

- `main` 最新两条提交：
  - `5150b97 docs: add readme recovery entry`
  - `152986d docs: reconcile repository recovery state`
- `main` 当前状态：
  - 相对 `origin/main` ahead 38
  - 只剩未跟踪 `tools/`
- 验证线 `publish-stage-task1`：
  - 相对 `origin/publish-stage-task1` ahead 7
  - `HEAD = 350b903 feat: add publish live verification entry`
  - 工作区干净

如果新会话开始时只允许先做一件事，那就先做这件事：

- 恢复可执行测试环境，然后在验证线完成 live verification 的真实 evidence archive 收口
