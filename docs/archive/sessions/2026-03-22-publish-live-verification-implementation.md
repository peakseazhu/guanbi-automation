# 2026-03-22 会话归档（Publish Live Verification Implementation）

## 当前结论

- `publish live verification` 已形成首个有效 evidence archive：
  - `runs/live_verification/publish/20260323T022511Z`
- 旧目录 `runs/live_verification/publish/20260322T054012Z` 仍为空，只能继续视为历史运行足迹，不能视为完成证据。
- 本次真实样本写入、读回、comparison 全部成功：
  - `comparison.json -> matches = true`
  - canonical source shape = `58 x 127`
  - canonical readback shape = `58 x 127`
- 当前验证线已不再停留在“代码与本地 spec 已到位但无证据”的状态，而是进入“代码到位 + 真实 evidence archive 已落盘”的状态。

## 环境恢复

本次先按 `docs/plans/2026-03-22-repository-state-and-recovery-design.md` 的顺序恢复，再处理当前 shell 中的验证环境漂移。

重新核对后的当前事实为：

- shell PATH 中仍没有 `pytest`
- `D:\miniconda3\envs\feishu-broadcast\python.exe` 当前仍缺：
  - `pytest`
  - `pydantic`
  - `PyYAML`
- 但该 conda env 已具备：
  - `httpx`
  - `openpyxl`
  - `xlwings`
  - `pywin32`
- 根目录 `.packages` 已具备：
  - `pytest`
  - `pydantic`
  - `PyYAML`
  - `httpx`

因此本次恢复出的可执行验证路径固定为：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest ...
```

这条路径的含义是：

- 解释器使用 `feishu-broadcast`
- 本地项目依赖缺口由根目录 `.packages` 补齐
- 不再依赖当前 shell PATH 中是否存在 `pytest`

## 根因排查与最小修复

真实样本第一次执行 `python -m guanbi_automation.live_verification.publish_real_sample` 时出现以下现象：

- 新目录 `runs/live_verification/publish/20260323T021149Z` 被创建，但仍为空
- Python 进程持续运行数分钟
- 进程 CPU 持续升高
- 进程没有任何活跃网络连接

随后进一步核对到：

- 真实样本 workbook `D:\get_bi_data__1\执行管理字段更新版.xlsx` 文件大小为 `215,910,168` 字节
- `guanbi_automation.infrastructure.excel.publish_source_reader.read_publish_source(...)` 仍在使用：
  - `load_workbook(workbook_path, data_only=True)`
- 但同一文件用：
  - `load_workbook(path, read_only=True, data_only=True)`
  可在约 `8.41s` 内读取到 `全国执行`

因此根因被锁定为：

- live verification 在真实大 workbook 上卡在 publish source 读取阶段
- 原因不是飞书接口、不是写入计划、也不是 readback
- 根因是 `publish_source_reader` 仍对 `215MB` workbook 执行全量加载，而不是 streaming-safe 读取

本次修复只落在验证线，不触碰 legacy `src/`，也不直接改 `main`：

- `guanbi_automation/infrastructure/excel/publish_source_reader.py`
  - `load_workbook(..., data_only=True)` 改为 `load_workbook(..., data_only=True, read_only=True)`
  - 单元格读取改为 `iter_rows(..., values_only=True)`
- `tests/infrastructure/excel/test_publish_source_reader.py`
  - 新增回归测试，明确要求 publish source 读取必须以 `read_only=True` 打开 workbook

本次修复按 red-green 执行：

1. 先新增回归测试
2. 在旧实现下运行，得到预期失败：
   - `read_only` 为 `None`
3. 再补最小实现
4. 回归测试转绿

## 自动化验证

### 1. 回归测试

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_publish_source_reader.py -v -p no:cacheprovider
```

结果：

- `3 passed`

### 2. Live Verification Focused Verification

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/domain/test_live_verification.py tests/application/test_live_verification_spec.py tests/application/test_publish_live_verification_service.py tests/infrastructure/excel/test_publish_source_reader.py tests/infrastructure/feishu/test_target_planner.py tests/infrastructure/feishu/test_client.py -v -p no:cacheprovider
```

结果：

- `31 passed`

### 3. 验证线 Full Suite

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `102 passed`

## 真实样本执行结果

执行命令：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1\.worktrees\publish-stage-task1;D:\get_bi_data__1\.packages'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m guanbi_automation.live_verification.publish_real_sample
```

运行结果：

- Evidence directory：
  - `D:\get_bi_data__1\.worktrees\publish-stage-task1\runs\live_verification\publish\20260323T022511Z`
- target metadata：
  - `spreadsheet_token = Z3zksQfnehAV0ut1Jq8c2lKin6e`
  - `sheet_id = ySyhcD`
  - `title = 测试子表`
- source metadata：
  - workbook = `D:\get_bi_data__1\执行管理字段更新版.xlsx`
  - source sheet = `全国执行`
  - `header_mode = include`
  - canonical row count = `58`
  - canonical column count = `127`

这里必须显式记录一个新事实：

- 之前设计文档中提到的 `80 x 127`，对应的是当前 sheet 的最大行列边界
- 本次真实运行进入 publish source trim 后，最终 canonical dataset 为 `58 x 127`
- 因此真正被写入并参与 comparison 的矩阵规模是 `58 x 127`

写入计划与回写结果如下：

- `write-plan.json` 生成了两段列切分：
  - `ySyhcD!A1:CV58`
  - `ySyhcD!CW1:DW58`
- `write-result.json` 返回：
  - 第一段 `updatedCells = 5800`
  - 第二段 `updatedCells = 1566`
  - 总 revision = `1170`
- `comparison.json` 返回：
  - `matches = true`
  - `mismatch_count = 0`

## Evidence Archive 完整性

`runs/live_verification/publish/20260323T022511Z` 当前已包含：

- `request.json`
- `source-metadata.json`
- `target-metadata.json`
- `write-plan.json`
- `write-result.json`
- `readback.json`
- `comparison.json`

这意味着当前时间戳目录已经满足“可回看、可比对、可复查”的 evidence archive 要求，不再是空目录运行足迹。

## 对主线的晋升判断

基于本次真实证据，当前可分成两类：

### 可以回灌 `main` 的内容

- `publish_source_reader` 的 streaming-safe 修复：
  - `read_only=True`
  - `iter_rows(values_only=True)`
- 对应回归测试：
  - `test_read_publish_source_opens_large_workbook_in_read_only_mode`

原因：

- 这是 foundation 层通用修复，不依赖本机私有 token 或本地 spec
- 已通过验证线 full suite
- 已被真实 `215MB` workbook 样本证明是必要修复，而不是一次性脚手架

### 继续留在验证线的内容

- `config/live_verification/publish/real_sample.local.yaml`
- `publish_real_sample` 入口
- 真实 spreadsheet token / target `sheet_id`
- `runs/live_verification/publish/20260323T022511Z` evidence archive
- 面向真实资源的写入/读回验证脚手架与本地证据

原因：

- 这些内容仍然直接绑定本机真实资源、临时目标表和本地验证输入
- 它们的职责是“证明 publish live verification 已跑通”，不是主线 foundation 的通用运行入口

## 当前恢复点

截至 2026-03-23，本验证线的下一恢复点更新为：

1. 保留 `20260322T054012Z` 为历史空足迹，不再误写为已完成验证
2. 以 `20260323T022511Z` 作为首个有效 publish live verification evidence archive
3. 后续若需要回灌 `main`，优先萃取：
   - `publish_source_reader` 的 read-only 修复
   - 对应回归测试
4. live verification 本地 spec、真实目标标识和 evidence archive 继续留在验证线
