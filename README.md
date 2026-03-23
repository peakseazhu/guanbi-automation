# Guanbi Automation

从 0 构建的观远 BI 自动化套件当前已完成 runtime contract、extract runtime policy、workbook foundation、publish foundation。基于首个有效 publish live verification evidence archive，`main` 已吸收 `publish hardening` 所需的 foundation primitives，包括 `publish_source_reader` 的 streaming-safe 读取修复、concrete Feishu publish writer、row/column-aware segment planning、`values_batch_update` 批量写入路径，以及 segment-aware publish manifest surface；真实资源 readback/comparison、live verification runtime，以及主线尚未具备的 publish runtime consumer 继续在独立验证线推进。

## Recovery Entry

未来任何新会话恢复时，固定按以下顺序进入：

1. `README.md`
2. `docs/plans/master-system-design.md`
3. `docs/plans/master-implementation-roadmap.md`
4. `docs/archive/decision-log.md`
5. `docs/plans/2026-03-22-mainline-validation-governance-design.md`
6. `docs/plans/2026-03-22-repository-state-and-recovery-design.md`
7. 当前工作线的最新 session archive
8. 对应阶段的 design / implementation plan

当前恢复时还必须同时记住：

- `main` 是稳定基线
- `.worktrees/publish-stage-task1` 是 publish live verification 验证线，不替代主线权威文档
- 最新主线状态归档已前进到：
  - `docs/archive/sessions/2026-03-23-publish-mainline-reconciliation.md`
- 验证线同时保留两类运行目录：
  - `runs/live_verification/publish/20260322T054012Z` 仍为空目录，只算历史运行足迹
  - `runs/live_verification/publish/20260323T022511Z` 是首个有效 evidence archive，`comparison.json` 已确认 `matches = true`
- 当前最重要的新边界是：
  - `58 x 127` 真实宽表已经通过验证线 evidence 证明需要 `chunk_column_limit=100`、单 segment `write_values` 与多 segment `values_batch_update`；对应 foundation primitives 已进入 `main`，但主线尚未具备非测试 publish runtime consumer
  - `.worktrees/publish-stage-task1` 仍只保留 live verification spec / service / entrypoint / local spec / evidence / readback comparison，不替代主线 runtime

## Runtime Contract Baseline

- `doctor`：通过 `guanbi_automation.application.doctor_service.run_doctor(...)` 返回结构化 `DoctorReport`
- `extract runtime policy`：由 `guanbi_automation.bootstrap.settings.RuntimePolicySettings` 提供 `fast / standard / heavy` 三档 extract profile，默认档位为 `standard`
- `stage gates`：由 `guanbi_automation.execution.stage_gates` 统一判断 extract / workbook / publish 是否允许进入

## Extract Runtime Profiles

- `standard` 是默认 profile
- `extract template` 保存默认 profile
- `run batch` 可提供 runtime profile override，解析顺序为 `override > template default`
- extract manifest 会记录 `template_runtime_profile`、`effective_runtime_profile` 以及 `submit / poll / download` 分段证据

## Workbook Stage Foundation

当前 workbook foundation 已覆盖：

- `WorkbookBlockSpec` 与 `WorkbookSettings`
- bounded block locator
- `.xlsx / .csv` extract artifact loader
- file-based block writer
- `fill_fixed_value` 与 `fill_down_formula`
- `workbook_ingest` block-level manifest
- `workbook_transform` calculation trigger

其中：

- 默认数据平面走 file-based writer
- Excel / COM 只负责 `workbook_transform` 的 calculation plane
- workbook manifest 会记录 block 写入范围、action evidence 和 calculation 结果

## Publish Stage Foundation

当前 publish foundation 已覆盖：

- `PublishSourceSpec`、`PublishTargetSpec`、`PublishMappingSpec`
- workbook value-only source reader
- Feishu target planner 与 row/column-aware segment planner
- Feishu Sheets client adapter 与 batch-range write path
- concrete publish writer
- mapping-level publish manifest
- `publish` execution stage

其中：

- publish 只消费 result workbook 的值，不上传公式
- target 支持 `replace_sheet`、`replace_range`、`append_rows`
- `chunk_column_limit` 默认值为 `100`
- 单 segment 写入走 `write_values`
- 多 segment 写入走 `values_batch_update`
- mapping manifest 会记录 `segment_count`、`segment_write_mode` 与 `write_segments`
- `append_rows` 重跑默认阻断，不视为天然幂等
- publish gate 会在进入阶段前校验 workbook、mapping 数量与 target readiness
- 当前 `main` 只有 publish foundation/primitives；非测试 `PublishStage` runtime wiring 仍未进入主线

## Current Verification

当前已覆盖：

- runtime contract domain models
- environment doctor
- extract runtime profile resolution
- polling policy and network error mapping
- request budget helper for submit / download
- structured event and manifest helpers
- stage gate evaluation
- extract stage segmented runtime evidence
- workbook contract, locator, loader, writer, ingest, transform foundation
- publish contract, source reader, row/column-aware target planner, batch-capable client adapter, publish writer, and publish stage foundation
