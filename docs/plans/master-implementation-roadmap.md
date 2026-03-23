# 观远 BI 自动化套件主实施路线图

> 状态：Active
> 最近更新：2026-03-23
> 当前执行明细：
> - `docs/plans/2026-03-19-from-scratch-guanbi-automation-implementation-plan.md`
> - `docs/plans/2026-03-19-runtime-contract-implementation-plan.md`
> - `docs/plans/2026-03-20-extract-runtime-policy-design.md`
> - `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`
> - `docs/plans/2026-03-21-workbook-detailed-design.md`
> - `docs/plans/2026-03-21-workbook-stage-implementation-plan.md`
> - `docs/plans/2026-03-21-publish-stage-detailed-design.md`
> - `docs/plans/2026-03-21-publish-stage-implementation-plan.md`
> - `docs/plans/2026-03-22-mainline-validation-governance-design.md`
> - `docs/plans/2026-03-22-repository-state-and-recovery-design.md`

## 1. 实施总原则

- 实现代码从 0 构建，不在 legacy `src/` 上继续迭代。
- 先稳定领域模型、运行批次模型和 extract-only 主链路，再接 Excel 与飞书。
- 先解决结构正确性，再解决展示完整性。
- 每个里程碑都必须可验证、可归档、可复现。
- 所有阶段都必须围绕“多 job 同批次执行”的目标设计，而不是先写死单任务流程。

## 2. Phase 0：文档治理与框架锁定

**目标**

建立权威文档体系，锁定项目边界、模块分层、批次执行模型和多任务共享策略。

**关键交付物**

- 主设计文档
- 主实施路线图
- 决策日志
- 会话归档机制
- 从 0 构建实施计划

**退出条件**

- 当前会话结论全部已落入文档
- 后续开发可直接按主文档推进
- 文档之间不存在单任务/多任务模型冲突

## 3. Phase 1：新项目骨架与基础设施

**目标**

搭起干净的新代码骨架、依赖管理、配置加载、日志系统和文件存储约定。

**关键交付物**

- `pyproject.toml`
- 单一权威依赖清单与锁定文件
- `guanbi_automation/` 代码骨架
- `bootstrap/`、`domain/`、`application/`、`execution/`、`infrastructure/`、`web/` 分层目录
- 配置加载与校验
- 环境 `doctor` 与运行前检查
- 文件系统仓储基础能力
- 基础测试框架

**退出条件**

- 新项目可独立安装和运行测试
- 目录结构与依赖边界稳定
- 关键依赖缺失会在运行前被阻断，而不是在运行中途报错

## 4. Phase 2：观远发现与页面快照

**目标**

打通登录、页面树、页面详情、快照解析与落盘，建立 UI 可消费的稳定快照层。

**关键交付物**

- 认证模块
- 原始 API client
- 返回结构归一化
- 页面树解析
- 页面详情快照模型
- 页面快照存储

**退出条件**

- 能获取页面树并保存页面快照
- 能稳定解析 `PAGE` 与 `CUSTOM_REPORT`
- 页面详情足以驱动后续 extract 建模

## 5. Phase 3：模板模型与运行批次规划

**目标**

建立 `extract template`、`job template` 和 `run batch` 规划能力，正式支持多任务并存与共享去重。

**关键交付物**

- extract 模型
- job 模型
- run batch 模型
- run planner
- extract signature 去重逻辑
- batch/job/extract manifest 结构

**退出条件**

- 能从多个 job 生成一个稳定的批次执行计划
- 相同 extract 可在同批次内去重

## 6. Phase 4：Preflight 与 Extract-Only 里程碑

**目标**

完成第一条可生产验证链路：模板保存、预检、导出执行、结果归档。

**关键交付物**

- runtime contract 基线
- preflight service
- pipeline engine
- extract stage
- extract runtime profile（`fast / standard / heavy`）
- `submit / poll / download` 分段预算与 extract 总时限
- 超时 / SSL / 连接错误分类与重试策略
- batch 级归档
- 失败态 manifest

**退出条件**

- 运行前 `doctor`、runtime policy、stage gate 已有最小稳定模型
- extract-only 任务可独立完成一次成功运行
- 多 job 同批次 extract-only 可运行
- 失败运行也能留下可诊断归档
- 轮询不会因无限等待或无分类异常而卡死
- 慢任务可通过更重的 runtime profile 放宽预算，而不必放宽全部 extract

## 7. Phase 5：本地 Web 控制台

**目标**

提供最小可用的本地管理界面，支撑浏览、建模、编排、执行和查看归档。

**关键交付物**

- 资源浏览区
- 抽取配置区
- 任务编排区
- 运行中心
- 归档查看区

**退出条件**

- 操作者无需改代码即可完成 extract 和 job 的建模与执行

## 8. Phase 6：Workbook 阶段

**目标**

在 extract-only 稳定后，接入 Excel ingest 与 transform 阶段，并把副作用边界单独控制。

**关键交付物**

- workbook ingest stage
- workbook transform stage
- 受约束 block 写入模型
- file-based writer + calculation runner 双平面
- 行数 / 列数 / 单元格总量护栏
- 辅助列公式下拉与固定列补值
- workbook 归档结构
- COM 异常和大表写入错误分类

**退出条件**

- 能在明确模板下完成导出到本地底板的写入、计算和读取
- 超大数据集要么被安全阻断，要么被切换到可验证的替代路径，而不是直接压给 COM

## 9. Phase 7：Feishu Publish 阶段

**目标**

接入飞书 Sheets 发布能力，并补齐批次写入、限流和失败摘要。

**关键交付物**

- Feishu adapter
- publish mapping contract
- publish dataset 标准层
- publish stage
- 批量写入器
- mapping 级 manifest
- 发布摘要归档

**退出条件**

- 能在 workbook 阶段输出标准数据后稳定发布到目标 Sheets

## 10. Phase 8：硬化与验收

**目标**

把系统从“能跑”提升到“可交付、可维护、可定位问题”。

**关键交付物**

- 手工验收清单
- 定向集成测试
- 日志规范与错误分类表
- 运行手册
- 回归验证清单

**退出条件**

- 首轮业务可由文档驱动完成完整运行
- 已知高频故障有明确排障入口

## 11. 当前执行优先级

当前优先级必须严格按以下顺序执行：

1. 文档治理与框架锁定
2. 新项目骨架与基础设施
3. 观远发现与快照
4. 模板模型与运行批次规划
5. runtime contract 与 extract runtime policy
6. preflight 与 extract-only
7. 本地 Web 控制台
8. Workbook 阶段
9. Feishu Publish 阶段
10. 硬化与验收

## 12. 风险前置提醒

当前最值得提前防守的风险如下：

- 把 legacy 代码“借一点、改一点”后重新耦回主流程。
- 先写死单任务运行，再在后面硬补多任务与共享去重。
- 模板模型没锁定就先写界面，导致前后端一起返工。
- 只验证成功路径，不验证失败路径与归档可读性。
- 没有先把 batch/job/extract 三层 manifest 结构做稳，导致后续日志和归档越来越乱。
- 把任务轮询继续写成无限循环，缺少超时预算、错误分类和重试边界。
- 把 workbook 大表直接交给 Excel COM 批量写入，没有尺寸护栏和回退策略。
- 在 runtime contract 未锁定前就提前展开 workbook 细节设计，导致阶段护栏、日志字段和错误语义后续返工。
- 把追加式 publish 当成天然幂等操作，导致日更报表重复追加。

## 13. 文档更新规则

后续每次会话都必须至少做以下事情：

- 生成新的 `docs/archive/sessions/*.md`
- 如有设计变更，更新 `docs/plans/master-system-design.md`
- 如有实施顺序变更，更新 `docs/plans/master-implementation-roadmap.md`
- 如有关键取舍，更新 `docs/archive/decision-log.md`

## 14. 当前恢复点

截至 2026-03-23，当前执行状态已经更新为：

1. `runtime contract` 已完成并通过全量测试验证。
2. `extract runtime policy` 已按 `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md` 完成 Task 1-7，并通过全量测试验证。
3. `workbook detailed design` 与 `docs/plans/2026-03-21-workbook-stage-implementation-plan.md` 已完成，并通过 focused verification 与 full suite 验证。
4. `publish stage detailed design` 与 `docs/plans/2026-03-21-publish-stage-implementation-plan.md` 已完成设计收敛。
5. `publish foundation` 已从 `publish-stage-task1` worktree 萃取并进入 `main`，当前主线已包含：
   - publish contract
   - publish source reader（含 streaming-safe 读取修复）
   - feishu target planner 与 row/column-aware `plan_range_segments(...)`
   - feishu sheets client adapter（含最小 `write_values_batch(...)` 路径）
   - concrete publish writer
   - publish stage
   - publish runtime wiring
   - mapping manifest `segment_count / segment_write_mode / write_segments`
6. `publish hardening bundle v1` 已通过 clean PR 合入 `main`：
   - promotion 载体：`publish-hardening-promotion`
   - 来源：`publish-stage-task1@b1bca69`
   - merge commit：`5ac9b38 Merge pull request #2 from peakseazhu/publish-hardening-promotion`
   - merged PR：`#2 feat: promote publish hardening bundle`
7. 本轮 mainline promotion focused verification 已确认：
   - `PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-hardening-promotion;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests/bootstrap/test_settings.py tests/infrastructure/feishu/test_client.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_publish_writer.py tests/execution/test_publish_stage.py -v -p no:cacheprovider` -> `33 passed`
8. 合并后主线 fresh full suite 已确认：
   - `PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider` -> `98 passed`
9. 主线当前治理规则固定为：
   - `main` 只保留稳定阶段成果
   - 真实资源落地验证留在独立验证线推进
10. 当前验证线为：
   - `publish-stage-task1`
   - 继续承担 `publish live verification` 与 post-hardening validation
   - 当前验证线提交：`b1bca69 docs: archive publish hardening implementation`
   - 当前已完成 live verification 设计与代码路径：
      - spec / local spec
      - Feishu readback support
      - live verification service
      - real-sample entrypoint
   - 当前本地 spec 已锁定真实 workbook/source/target
   - 历史运行足迹目录：
      - `runs/live_verification/publish/20260322T054012Z`
   - 首个有效 evidence archive：
      - `runs/live_verification/publish/20260323T022511Z`
      - `comparison.json` 已确认 `matches = true`
   - live verification implementation archive：
      - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
   - publish hardening implementation archive：
      - `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-23-publish-hardening-implementation.md`
   - 验证线 fresh full suite 已恢复并更新为：
      - `PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider` -> `110 passed`
11. 当前 selective promotion 已确认进入主线的 hardening slice 为：
   - `PublishSettings.chunk_column_limit=100`
   - row/column-aware range segmentation 与 single-range fallback inference
   - concrete publish writer
   - 单 segment `write_values(...)` / 多 segment `values_batch_update(...)`
   - batch-aware `PUBLISH_RANGE_INVALID`
   - mapping manifest `segment_count / segment_write_mode / write_segments`
   - 对应 regression coverage
12. 当前仍继续留在验证线的内容为：
   - `fetch_tenant_access_token`
   - `read_values`
   - `PUBLISH_READBACK_MISMATCH`
   - live verification spec / service / entrypoint
   - local real-sample config / 真实目标标识 / evidence archive / readback comparison
13. 当前主线下一恢复点为：
   - 保持 `main` 在 `publish foundation + publish hardening bundle v1` 的稳定状态
   - 后续仍只选择性吸收已被真实证据证明必要、且已被主流程实际消费的 foundation 能力
   - readback / comparison contract 只有在主线出现明确消费者后才进入下一轮 selective promotion 判断
14. 在进入下一阶段时，仍然不允许：
   - 回到 legacy `src/`
   - 把 extract runtime policy 退回单一 `extract_polling`
   - 把本地 spec、真实目标标识与 evidence archive 整体并入 `main`

## 15. 恢复阅读顺序

未来任何新会话在真正动手前，固定阅读顺序为：

1. `README.md`
2. `docs/plans/master-system-design.md`
3. `docs/plans/master-implementation-roadmap.md`
4. `docs/archive/decision-log.md`
5. `docs/plans/2026-03-22-mainline-validation-governance-design.md`
6. `docs/plans/2026-03-22-repository-state-and-recovery-design.md`
7. 当前工作线的最新 session archive
8. 对应阶段的 design / implementation plan
