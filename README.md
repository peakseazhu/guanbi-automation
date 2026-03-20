# Guanbi Automation

从 0 构建的观远 BI 自动化套件当前先落 runtime contract 基线，再继续 extract-only 链路。

## Runtime Contract Baseline

- `doctor`：通过 `guanbi_automation.application.doctor_service.run_doctor(...)` 返回结构化 `DoctorReport`
- `polling policy`：由 `guanbi_automation.bootstrap.settings.RuntimePolicySettings` 提供默认 extract polling 配置
- `stage gates`：由 `guanbi_automation.execution.stage_gates` 统一判断 extract / workbook / publish 是否允许进入

## Current Verification

当前已覆盖：

- runtime contract domain models
- environment doctor
- polling policy and network error mapping
- structured event and manifest helpers
- stage gate evaluation
- extract stage runtime evidence
