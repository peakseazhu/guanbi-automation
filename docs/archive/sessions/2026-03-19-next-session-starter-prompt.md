# 2026-03-19 下一次新会话开场提示词

## 1. 推荐完整版

```text
请先完整阅读并遵守当前项目的权威规划文档与归档规则，然后无缝衔接继续推进，不要重新发散，也不要回到修改 legacy 脚本的路径。

项目根目录：`D:\get_bi_data__1`

先阅读以下文档，并以它们为当前唯一权威上下文：

1. `docs/plans/master-system-design.md`
2. `docs/plans/master-implementation-roadmap.md`
3. `docs/archive/decision-log.md`
4. `docs/archive/sessions/2026-03-19-pause-handoff-summary.md`
5. `docs/plans/2026-03-19-runtime-contract-and-stage-gating-design.md`
6. `docs/plans/2026-03-19-runtime-contract-implementation-plan.md`

重要约束：

- 新项目代码必须从 0 构建，不能基于 legacy `src/` 修改。
- `logger/`、`记录/`、legacy `src/`、根目录 Excel 文件都只是参考证据库。
- 规划与归档必须继续遵守“三层结构”：
  - 主规划文档
  - 每次对话单独归档
  - 决策日志
- 每次发现更优方法时，必须先做认真对比和必要测试，再更新主规划文档。
- 现在已经锁定的工程顺序是：
  1. `runtime contract`
  2. `extract runtime policy`
  3. `workbook detailed design`

当前恢复点：

- 不要直接开始 workbook 实现。
- 不要重新讨论是否先做 workbook。
- 直接按 `docs/plans/2026-03-19-runtime-contract-implementation-plan.md` 从 Task 1 开始继续。

本次新会话你的目标是：

1. 先核对上述文档，确认与当前工作区状态一致。
2. 如有新的更优路径，必须基于证据说明，不得主观改动方向。
3. 然后进入 `runtime contract` 的实现推进。
4. 同时把本次新会话继续归档到 `docs/archive/sessions/`，并按需更新 `master` 文档和 `decision-log`。

请先用简洁的话复述你对当前项目状态、当前恢复点、下一步任务的理解，再开始执行。
```

## 2. 推荐精简版

```text
请无缝衔接 `D:\get_bi_data__1` 这个项目，不要重新发散，也不要回到修改 legacy 脚本的路径。

先读：
- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-19-pause-handoff-summary.md`
- `docs/plans/2026-03-19-runtime-contract-and-stage-gating-design.md`
- `docs/plans/2026-03-19-runtime-contract-implementation-plan.md`

当前已锁定顺序：
1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

直接从 `2026-03-19-runtime-contract-implementation-plan.md` 的 Task 1 继续，并继续维护三层归档体系。
先复述理解，再执行。
```

## 3. 使用建议

- 如果你希望新会话尽量稳，不遗漏上下文，优先用“完整版”。
- 如果只是快速恢复推进，可用“精简版”。
- 新会话一开始先让对方复述理解，这样可以快速判断它有没有读对当前恢复点。
