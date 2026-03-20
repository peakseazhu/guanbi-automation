# 2026-03-19 运行契约优先级确认会话归档

## 1. 本次会话触发点

在完成历史日志审查后，用户继续追问：

- 当前是先做 `Workbook` 细化更合适，还是先做 `doctor + polling` 更合适
- 是否存在更严格、更正确的项目开发顺序

## 2. 本次会话形成的判断

本次没有选择简单的二选一，而是进一步确认了当前全局最优路径：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

结论原因：

- 先做 workbook 只能解决局部问题，无法解决全局入口护栏缺失。
- 只做 `doctor + polling` 又不足以形成正式的阶段护栏与 manifest 契约。
- 先建立 `runtime contract` 才能让 extract 和 workbook 共享同一套运行语义。

## 3. 本次被正式采纳的内容

本次将以下内容正式提升为当前主方向：

- 运行契约作为 workbook 细化前的正式前置阶段
- 运行契约必须覆盖：
  - `doctor`
  - timeout / retry / polling
  - `stage gate`
  - `error taxonomy`
  - `event + manifest`

## 4. 本次新增输出

### 4.1 新设计文档

- `docs/plans/2026-03-19-runtime-contract-and-stage-gating-design.md`

### 4.2 新实施计划

- `docs/plans/2026-03-19-runtime-contract-implementation-plan.md`

### 4.3 主文档同步

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`

## 5. 本次新增 ADR

- `ADR-2026-03-19-11`：先建立 runtime contract，再细化 workbook 设计

## 6. 当前后续顺序

当前后续顺序已经锁定为：

1. 继续收敛 `runtime contract`
2. 明确 extract runtime policy 的实现接口
3. 在此前提下进入 workbook detailed design
