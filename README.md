# Guanbi Automation

从 0 构建的观远 BI 自动化套件当前先落 runtime contract 基线，再继续 extract-only 与 workbook foundation。

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
