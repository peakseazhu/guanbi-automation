# 主线稳定与验证推进双轨治理设计

> 状态：Approved
> 最近更新：2026-03-22
> 关联文档：
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-21-publish-stage-implementation-plan.md`

## 1. 背景

`publish-stage-task1` worktree 已经同时承载了两类内容：

1. 可进入主线的 `publish foundation` 正式实现
2. 继续向真实资源推进的 `publish live verification` 验证层

如果继续把两类内容混在一个分支里理解，会出现两个问题：

- `main` 会长期落后于真实稳定实现
- 未完成真实落地验证的探索内容会过早污染主线

当前需要显式区分：

- 什么属于“主线稳定层”
- 什么属于“验证推进层”

## 2. 目标

本设计的目标不是增加新的功能，而是固定一套分阶段治理规则：

- `main` 始终优先保留已经稳定、已通过 fresh verification 的阶段成果
- 验证线允许继续直接推到真实资源边界，回答“能不能做、怎么做、做到什么程度”
- 只有验证成功并且边界收敛后，验证线成果才允许被再次萃取进主线

## 3. 主线与验证线定义

### 3.1 主线稳定层

主线稳定层指可以直接进入 `main` 的实现与文档，至少满足：

- 不依赖未完成的真实资源试跑
- 已通过当前 fresh automated verification
- 已具备清晰的职责边界与最小归档
- 不把实验性现场状态伪装成权威现状

### 3.2 验证推进层

验证推进层指继续在 worktree / feature branch 中向前推进的内容，允许包含：

- 真实样本写入与读回验证
- 真实资源权限、接口边界、速率限制和尺寸上限摸底
- 专用 live verification 入口
- 只服务验证过程的本地 spec 和证据归档

验证推进层的目标不是维持“最干净的主线”，而是尽快逼近真实边界并留下证据。

## 4. 当前对 publish 阶段的应用

当前对 `publish-stage-task1` 的正式划分如下：

### 4.1 进入主线的内容

以下内容属于 `publish foundation`，应萃取到 `main`：

- publish contract
- workbook publish source reader
- feishu target planner
- feishu sheets client adapter
- publish stage
- publish runtime wiring
- 与以上实现直接对应的测试与最终实现归档

### 4.2 留在验证线的内容

以下内容继续留在验证线，不直接进入 `main`：

- publish live verification design
- publish live verification implementation
- 真实 workbook -> Feishu target 的写入/读回验证入口
- 本地 live verification spec
- 真实样本运行证据与 readback comparison

## 5. 提升规则

验证线内容想进入主线时，必须满足以下条件：

1. 已有 fresh automated verification
2. 若涉及真实资源，已有可回看的本地 evidence archive
3. 已明确哪些部分是可沉淀的正式能力，哪些仍是一次性验证脚手架
4. 已更新权威文档与 session archive

不满足以上条件时，只能继续保留在验证线。

## 6. 当前结论

从 2026-03-22 起，项目采用以下治理方式：

- `main`：只保留稳定阶段成果
- `publish-stage-task1`：继续承担 publish 真实落地验证
- 后续其它阶段也默认沿用同一原则：
  - foundation 先进主线
  - live verification 在验证线先跑到底

