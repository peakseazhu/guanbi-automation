# 2026-03-19 项目重置与文档治理会话归档

## 1. 本次会话触发点

用户要求我完整阅读当前工作目录，先找规划文档，再结合源码、记录、日志和业务文件进行系统性梳理，并且要求后续每次对话都必须归档与更新规划文档。

## 2. 本次新增且已确认的信息

本次会话新增并锁定了两条高优先级边界：

1. 项目文档治理采用“主规划文档 + 每次对话单独归档 + 决策日志”的三层结构。
2. 新项目实现代码必须从 0 构建，当前 legacy 脚本只作为参考样本，不作为后续实现基础。

## 3. 本次检查范围

本次已阅读和核对的内容包括：

- `docs/plans/*.md`
- `记录/*`
- `src/*`
- `requirements.txt`
- `environment.yml`
- `.env` 的键名结构
- `logger/*`
- 根目录业务 Excel 文件的 sheet 元数据

## 4. 本次确认的事实

- 旧脚本已经证明“观远导出 -> Excel 底板 -> 飞书回写”链路成立。
- 旧脚本高度硬编码，不适合作为新系统直接扩展。
- 旧环境声明与代码依赖存在真实不一致。
- 历史日志中存在网络异常、依赖缺失、Excel COM 异常、`xlwings` 数据形状异常、编码混乱等真实失败模式。
- 现有日期型设计稿和实施计划可以保留为历史快照，但不应继续承担唯一权威职责。

## 5. 本次形成的文档动作

本次会话已决定并落地以下文档体系：

- 新建 `docs/plans/master-system-design.md`
- 新建 `docs/plans/master-implementation-roadmap.md`
- 新建 `docs/archive/decision-log.md`
- 新建本会话归档文件
- 新建新的从 0 构建实施计划
- 给旧的阶段性设计稿和实施计划增加“当前权威文档已切换”的提示

## 6. 对后续实施的约束

后续开始写代码时必须遵守：

- 不在 legacy `src/` 基础上修补。
- 不让 legacy 模块进入新项目运行主链路。
- 先完成 extract-only 里程碑，再接 Excel 与飞书阶段。
- 每次会话都要同步更新归档和主规划文档。

## 7. 当前仍需后续继续收敛的问题

- `DS_ELEMENTS` 候选值接口的稳定能力边界。
- Excel 写入规则模型的最终组合约束。
- 飞书 Sheets 批量写入的限流、重试和幂等策略。

## 8. 本次会话输出文件

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-19-project-reset-and-document-governance.md`
- `docs/plans/2026-03-19-from-scratch-guanbi-automation-implementation-plan.md`
