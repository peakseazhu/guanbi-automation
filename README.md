# Guanbi Automation

从 0 构建的观远 BI 自动化套件当前已完成 runtime contract、extract runtime policy、workbook foundation 与 publish foundation。主线 `main` 只保留稳定阶段成果；真实资源落地验证继续在独立验证线推进。

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
- Feishu target planner 与 chunk helpers
- Feishu Sheets client adapter
- mapping-level publish manifest
- `publish` execution stage

其中：

- publish 只消费 result workbook 的值，不上传公式
- target 支持 `replace_sheet`、`replace_range`、`append_rows`
- `append_rows` 重跑默认阻断，不视为天然幂等
- publish gate 会在进入阶段前校验 workbook、mapping 数量与 target readiness

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
- publish contract, source reader, target planner, client adapter, stage, and runtime wiring foundation
