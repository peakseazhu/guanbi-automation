# 主线 Publish Runtime Consumer 设计

> 状态：Approved
> 最近更新：2026-03-23
> 前置阶段：`publish foundation + hardening primitives in main`
> 后续阶段：`mainline publish runtime consumer implementation plan`
> 关联文档：
> - `README.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/plans/2026-03-22-mainline-validation-governance-design.md`
> - `docs/archive/decision-log.md`
> - `docs/archive/sessions/2026-03-23-publish-mainline-reconciliation.md`

## 1. 背景

截至 2026-03-23，`main` 已经具备 publish foundation 与 publish hardening primitives：

- workbook value-only publish source reader
- Feishu target planner
- row/column-aware segment planner
- Feishu Sheets client adapter
- concrete publish writer
- mapping-level publish manifest surface
- `PublishStage`

但主线仍缺少一个非测试、可直接运行的 publish runtime consumer。

这意味着：

- `main` 当前可以证明“publish primitives 已稳定存在”
- 但还不能证明“主线已经有真正消费这些 primitives 的运行入口”

验证线 `.worktrees/publish-stage-task1` 已经证明真实宽表样本可以完成写入、读回与 comparison，也已经帮助主线沉淀了 hardening primitives；但 live verification service、本地 spec、真实资源 readback/comparison runtime 仍属于验证推进层，不应直接整体搬回主线。

当前最小且正确的下一步，不是继续扩验证脚手架，而是让 `main` 获得一个最小、清晰、可测试的 publish runtime consumer。

## 2. 目标

本设计的目标是为 `main` 增加一个第一版 publish-only runtime consumer，使主线第一次具备以下能力：

1. 以非测试方式直接执行 `PublishStage`
2. 显式消费现有 publish foundation/primitives，而不是重复实现一套平行逻辑
3. 以稳定的 CLI 输入/输出语义向外暴露 publish 运行结果
4. 在文档和测试中明确区分：
   - “能力已经存在于 stage/foundation”
   - “能力已经被 mainline consumer 接通”
   - “能力仍未被 mainline consumer 接通，但并未丢失”

## 3. 非目标

第一版主线 consumer 明确不做以下事情：

- 不引入 tenant token 自动换取流程
- 不引入真实资源 readback/comparison
- 不引入 live verification local spec
- 不引入 evidence archive
- 不把验证线 service 或 entrypoint 直接复制回主线
- 不在本次切片中支持 `append_rows` runtime path

这些内容不是被删除，而是继续保留在：

- 已存在但尚未被 mainline consumer 接通的 foundation/stage 能力
- 验证线专属的 live verification 运行层

## 4. 功能账本

### 4.1 当前主线已具备的 publish 基础能力

- `replace_sheet` / `replace_range` / `append_rows` contract 已存在
- source reader 已存在
- target planner 已存在
- `append_rows` planner 语义已存在
- concrete publish writer 已存在
- `PublishStage` 已存在
- `append_rows` rerun block 语义已存在

### 4.2 本次切片要让 mainline consumer 正式接通的能力

- 从 YAML run spec 读取 publish 执行输入
- 显式接收 `tenant_access_token`
- 对 `replace_sheet` / `replace_range` 进行真实 runtime wiring
- 通过 `PipelineEngine.run_publish(...)` 执行 `PublishStage`
- 把 manifest 作为稳定 JSON 输出给调用方

### 4.3 本次切片明确不接通但必须保留在账本中的能力

- `append_rows` consumer runtime path
- 目标表现状读取
- append 起始行探测所需的运行前加载
- readback/comparison
- tenant token fetch

文档与测试必须始终把这些功能写成“暂未接通”，而不是“功能不存在”。

## 5. 为什么第一版拒绝 `append_rows`

`append_rows` 与 `replace_sheet` / `replace_range` 的本质区别在于，它不是静态矩形写入，而是状态型写入：

- `replace_*` 只需要源数据形状和声明的写入锚点，就能确定目标矩形
- `append_rows` 必须先知道目标子表当前已经写到哪一行，才能决定新数据的起始行

主线 planner 中 `resolve_append_rows(...)` 需要 `existing_rows` 作为输入，而第一版主线 consumer 当前只计划使用主线已稳定的最小 Feishu 路径：

- `query_sheets`
- `write_values`
- `write_values_batch`

如果把 `append_rows` 一起纳入第一版，就必须同时扩展：

- 目标表读取路径
- append 起点判定运行时加载
- rerun duplicate safety 边界

这会让“最小真实 consumer”重新膨胀成“consumer + target-state read path + append safety runtime”，与当前主线切片目标冲突。

因此第一版 consumer 的固定策略是：

- 继续保留 `append_rows` contract / planner / stage safety tests
- 只要 run spec 中出现任一 `append_rows` mapping，就在 consumer 级预校验阶段整次失败
- 返回稳定、显式、可测试的错误结果

## 6. 运行形态

### 6.1 入口形态

第一版入口为一个主线 `publish-only` CLI。

建议输入包括：

- `--workbook-path`
- `--spec-path`
- `--tenant-access-token`
- 可选 `--batch-id`
- 可选 `--job-id`

若 `batch_id` / `job_id` 未显式传入，consumer 需要生成稳定默认值，避免调用方为了最小试跑还要额外准备无关元数据。

### 6.2 输出形态

CLI 输出固定为结构化结果，而不是人类导向日志堆叠：

- stdout 输出 publish stage manifest JSON
- 退出码语义固定：
  - `0`：`completed`
  - 非 `0`：`blocked` 或 `failed`

这样后续 shell、调度器或外层脚本都可以直接消费结果，而不需要先解析不稳定文本。

## 7. 架构分解

### 7.1 `publish_runtime_spec`

新增一个最小 YAML loader 与 run spec model，只承载 mainline consumer 所需字段：

- workbook 路径
- publish mappings
- spreadsheet / target 信息

它不应混入 live verification 字段，也不依赖验证线 domain model。

### 7.2 `publish_runtime_service`

新增一个 service 负责：

1. 解析 run spec
2. 执行 consumer 级预校验
3. 构建 `FeishuSheetsClient`
4. 构建 target loader
5. 构建 writer
6. 构建 `PublishStage`
7. 构建 `PipelineEngine`
8. 执行 `run_publish(...)`
9. 返回稳定结果 envelope

这样 CLI 只保留参数解析与进程退出语义，主要业务逻辑全部留在 service 中，以便测试。

### 7.3 `run_publish` CLI

CLI 本身保持很薄，只做：

- argv 解析
- 调 service
- 打印 JSON
- 返回退出码

它的风格可以参考验证线的 thin entrypoint，但不能把 live verification 逻辑带进来。

## 8. 目标加载与写入 wiring

第一版 consumer 的 target loader 应只覆盖 `replace_sheet` 与 `replace_range`：

1. 用 `query_sheets(...)` 解析目标 sheet 元数据
2. 按 mapping 的 `write_mode` 选择：
   - `resolve_replace_sheet(...)`
   - `resolve_replace_range(...)`
3. 组装 `PublishTargetContext`
4. 交给现有 `write_publish_target(...)`

这一层必须坚持复用主线现有 primitives，而不是重新写一套“consumer 专属 planner/writer”。

## 9. 失败语义

consumer 需要把失败分成三类：

### 9.1 预校验失败

例如：

- spec 不合法
- workbook 路径缺失
- `tenant_access_token` 为空
- mapping 中出现 `append_rows`

这类失败在进入 `PublishStage` 之前就应终止，避免制造半成功运行。

### 9.2 Stage blocked

对第一版 consumer 来说，blocked 主要保留为 stage-level 语义出口，而不是常规路径。

CLI 不应吞掉 blocked，而应原样通过：

- 非 `0` 退出码
- manifest 原样输出

### 9.3 Stage failed

写入失败、鉴权失败、目标缺失等 runtime 失败同样以：

- 非 `0` 退出码
- manifest JSON

暴露给调用方。

## 10. 测试策略

本次实现必须采用“分层补齐，而不是只测 happy path”的策略。

### 10.1 spec loader tests

验证：

- YAML 解析成功
- 非 mapping payload 报错
- 缺失字段报错

### 10.2 service tests

验证：

- `append_rows` 出现时整次失败
- `replace_sheet` / `replace_range` 能正确 wiring 到 `PublishStage`
- `completed` / `blocked` / `failed` 语义稳定
- manifest 与退出状态一致

### 10.3 CLI tests

验证：

- 参数解析
- stdout JSON 输出
- 非零退出码语义
- 稳定错误消息

### 10.4 既有 publish tests 持续保留

以下测试不能因为第一版 consumer 不支持 `append_rows` 而被弱化：

- `tests/execution/test_publish_stage.py`
- `tests/infrastructure/feishu/test_target_planner.py`
- `tests/infrastructure/feishu/test_publish_writer.py`

这保证项目的“功能存在层”与“consumer 接通层”不会被混为一谈。

## 11. 文档更新要求

实现完成后，主线权威文档必须同时更新：

- `README.md`
- `docs/archive/decision-log.md`
- 当前会话 archive

更新时必须明确写出：

- `main` 已新增非测试 publish runtime consumer
- 第一版 consumer 当前只接通 `replace_sheet` / `replace_range`
- `append_rows` 等能力仍存在于 foundation/stage，但尚未被第一版 consumer 接通

不能把主线状态写成“publish 全功能已端到端接通”。

## 12. 当前结论

当前最合适的主线推进方式是：

1. 新增一个最小 `publish-only` CLI
2. 用最小 service/wiring 把 `PublishStage` 真正接上主线运行入口
3. 显式支持 `replace_sheet` / `replace_range`
4. 显式拒绝 `append_rows`
5. 通过分层测试和主线文档账本，保证“未接通”不会被误写成“已丢失”或“已完成”

这条路线能以最小代价把 `main` 从“只有 publish primitives”推进到“已有真实 publish runtime consumer”，同时保持主线与验证线的治理边界清晰。
