# Guanbi Automation

从 0 构建的观远 BI 自动化套件当前已完成 runtime contract、extract runtime policy、workbook stage、publish stage，并新增 publish live verification 入口用于真实样本写入与读回校验。

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

## Publish Live Verification

当前新增了一个专用真实样本验证入口：

- 入口命令：`python -m guanbi_automation.live_verification.publish_real_sample`
- 默认 spec：`config/live_verification/publish/real_sample.local.yaml`
- 示例 spec：`config/live_verification/publish/real_sample.example.yaml`
- 运行证据目录：`runs/live_verification/publish/<timestamp>/`

这个入口不会回到 legacy `src/` 运行链路，而是复用新实现：

- 从 result workbook 读取值并做 canonical normalization
- 用 Feishu 官方 Sheets API 执行 `values_batch_update`
- 对相同目标范围做 readback
- 输出矩阵级 comparison 与本地 evidence archive

当前首个真实样本固定为：

- workbook：`D:\get_bi_data__1\执行管理字段更新版.xlsx`
- source sheet：`全国执行`
- header mode：`include`
- target sheet：`测试子表 / ySyhcD`
- write mode：`replace_sheet`
- target anchor：`A1`

运行前提：

- `.env` 中必须提供 `FEISHU_APP_ID` 与 `FEISHU_APP_SECRET`
- 若在 `.worktrees/...` 中运行，入口会优先回退到共享仓库根目录 `.env`
- 飞书应用至少需要 `sheets:spreadsheet` 或 `drive:drive` 写权限
- 目标 spreadsheet 还必须给该应用开放文档访问权限

当前真实样本 `全国执行` 为 `80 x 127`，已超过飞书单次 `100` 列上限，因此 live verification 会按列自动拆成多个矩形范围，再统一写入和读回。

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
- publish live verification spec, Feishu readback adapter, column-aware range planning, service archive, and thin real-sample entrypoint
