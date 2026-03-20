# 2026-03-20 Runtime Contract Task 1-7 实施归档

## 1. 本次会话目标

基于以下权威文档继续推进，不重新发散、不回到 legacy `src/` 改造路径：

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-19-pause-handoff-summary.md`
- `docs/plans/2026-03-19-runtime-contract-and-stage-gating-design.md`
- `docs/plans/2026-03-19-runtime-contract-implementation-plan.md`

本次恢复点保持为：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

并直接从 `docs/plans/2026-03-19-runtime-contract-implementation-plan.md` 的 `Task 1` 开始执行。

## 2. 文档与工作区核对结果

本次会话先核对了权威文档与当前工作区，结论如下：

- 当前方向与文档一致，仍然必须从 0 构建新代码，不得修改 legacy `src/`。
- 当前工作区在实现层与规划状态存在两个客观差异：
  - 目录不是 Git 仓库，因此本次无法按 worktree 流程推进。
  - 会话开始时还不存在新的 `guanbi_automation/`、`tests/`、`pyproject.toml` 最小新项目骨架。
- 当前环境还存在一个执行层差异：
  - `python`、`pytest` 不在命令 PATH 中，但 `D:\miniconda3\envs\feishu-broadcast\python.exe` 可用。
  - 为了继续 TDD，本次使用该解释器，并将 `pytest`、`pydantic`、`httpx`、`PyYAML` 安装到项目本地 `.packages`。

这些差异没有改变工程方向，因此没有触发 master 文档或 ADR 更新；仅作为本次实施上下文归档。

## 3. 本次完成的实现

### 3.1 Task 1：runtime contract domain models

新增文件：

- `pyproject.toml`
- `guanbi_automation/domain/runtime_contract.py`
- `guanbi_automation/domain/runtime_errors.py`
- `tests/domain/test_runtime_contract.py`

本次落地的最小模型包括：

- `TimeoutBudget`
- `RetryBudget`
- `PollingPolicy`
- `StageGateDecision`
- `RuntimeErrorInfo`
- `EventRecord`

补充的结构化对象：

- `DoctorCheckResult`
- `DoctorReport`

已验证的最小约束包括：

- timeout 必须为正数
- `max_wait > poll_interval`
- retry 次数非负
- `StageGateDecision.status` 仅允许 `ready / blocked / degraded`
- runtime event 默认带 UTC timestamp

### 3.2 Task 2：environment doctor service

新增文件：

- `guanbi_automation/application/doctor_service.py`
- `guanbi_automation/bootstrap/dependency_manifest.py`
- `tests/application/test_doctor_service.py`

本次 doctor 最小能力包括：

- Python 版本检查
- import 可用性检查
- 必需环境变量检查
- 必需路径存在且可写检查
- 依赖清单存在性检查

当前 `run_doctor(...)` 返回结构化 `DoctorReport`，而不是控制台字符串。

### 3.3 Task 3：polling policy 与 network error mapping

新增文件：

- `guanbi_automation/infrastructure/guanbi/polling.py`
- `guanbi_automation/infrastructure/guanbi/client.py`
- `tests/infrastructure/guanbi/test_polling_policy.py`

本次最小实现包括：

- `classify_poll_error(...)`
- `should_retry_poll_error(...)`
- `compute_next_wait_interval(...)`
- `should_continue_polling(...)`
- `poll_with_policy(...)`

当前已覆盖的最小语义包括：

- `httpx.ConnectTimeout` 映射为 `network_connect_timeout`
- `network_ssl_error` 被视为可重试错误
- exponential backoff 会基于 `poll_interval * backoff_multiplier^attempt` 计算等待
- 达到 `max_wait` 或 `max_retries` 后停止继续轮询
- policy-driven polling 在预算耗尽后返回稳定错误信息，而不是无限循环

### 3.4 Task 4：structured event and manifest helpers

新增文件：

- `guanbi_automation/execution/event_recorder.py`
- `guanbi_automation/execution/manifest_builder.py`
- `tests/execution/test_event_recorder.py`

本次最小实现包括：

- `build_event_record(...)`
- `build_batch_manifest(...)`
- `build_extract_manifest(...)`

当前 manifest 接线已覆盖：

- `batch_id`
- `extract_id`
- `stage_name`
- runtime policy 摘要
- final error 摘要
- events 容器

### 3.5 Task 5：stage gates 与 preflight 接线

新增文件：

- `guanbi_automation/execution/stage_gates.py`
- `guanbi_automation/application/preflight_service.py`
- `tests/execution/test_stage_gates.py`

当前最小 gate 语义包括：

- extract：有 polling policy 才允许进入
- workbook：模板缺失或 `cell_count > cell_limit` 时阻断
- publish：target 未 ready 时阻断
- preflight：按 stage_name 分派到对应 gate

### 3.6 Task 6：extract stage runtime evidence

新增文件：

- `guanbi_automation/execution/pipeline_engine.py`
- `guanbi_automation/execution/stages/extract.py`
- `tests/execution/test_extract_stage.py`

当前 extract stage 已记录的最小运行证据包括：

- `poll_attempts`
- `total_wait_seconds`
- `runtime_policy`
- `final_error`
- `batch_id`
- `extract_id`
- `chart_id`

补充说明：

- polling 终止语义已进一步收敛：
  - 重试次数耗尽时，保留网络类错误码
  - 等待预算耗尽时，上升为 `poll_timeout`

### 3.7 Task 7：bootstrap runtime policy settings

新增文件：

- `guanbi_automation/bootstrap/settings.py`
- `guanbi_automation/bootstrap/container.py`
- `README.md`
- `tests/bootstrap/test_settings.py`

当前 bootstrap 已具备：

- 单一入口 `RuntimePolicySettings`
- 默认 extract polling 配置
- 最小 `RuntimeContractContainer`
- README 中对 doctor / polling / stage gates 的说明入口

## 4. TDD 与调试记录

本次严格按 TDD 推进：

1. 先写 `Task 1` 失败测试，确认 `ModuleNotFoundError`。
2. 写最小实现，验证 `tests/domain/test_runtime_contract.py` 通过。
3. 先写 `Task 2` 失败测试，确认 `doctor_service` 缺失。
4. 写最小实现，验证 `tests/application/test_doctor_service.py` 通过。
5. 先写 `Task 3` 失败测试，确认 `infrastructure/guanbi` 缺失。
6. 写最小实现，验证 `tests/infrastructure/guanbi/test_polling_policy.py` 通过。

过程中遇到一个环境型问题：

- `pytest` 在普通沙箱 shell 下会因为工作区写入权限表现异常，初看像卡在 `collecting`。
- 通过最小调试确认根因后，后续测试均改为在有正常文件访问权限的命令下执行。

该问题属于当前会话运行环境特性，不构成项目架构变更。

## 5. 验证证据

本次批次结束前重新执行了当前 `tests/` 下的完整验证：

命令：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest `
  tests `
  -v -p no:cacheprovider
```

结果：

- `27 passed in 0.73s`

## 6. 本次未更新的文档

以下文档本次未改动：

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`

原因：

- 本次没有新的架构方向变化。
- 没有出现足以推翻既定顺序的证据。
- 当前实现只是按既定 runtime contract 路线落地第一批任务。

## 7. 下一步恢复入口

本次已经完成 `docs/plans/2026-03-19-runtime-contract-implementation-plan.md` 的 `Task 1-7`。

因此下次继续时，恢复入口不再是 runtime contract 内部任务，而是：

1. 对照当前实现补必要的主文档同步
2. 进入既定顺序中的下一阶段：`extract runtime policy`
3. 在 `extract runtime policy` 稳定后，再进入 `workbook detailed design`

继续原则不变：

- 不回到 legacy `src/`
- 不跳去 workbook 实现
- 先在 runtime contract 基线上继续推进 extract-only 链路，再进入后续阶段
