# 2026-03-23 会话归档（Publish Live Verification Promotion To Mainline）

## 当前结论

- 验证线 `publish-stage-task1` 已形成首个有效 publish live verification evidence archive：
  - `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`
- 基于该证据，本次选择性回灌 `main` 的内容只有：
  - `publish_source_reader` 的 streaming-safe 读取修复
  - 对应回归测试
- live verification 的真实资源脚手架仍留在验证线，不直接进入 `main`：
  - local spec
  - real-sample entrypoint
  - evidence archive
  - 真实 spreadsheet / sheet 标识

## 根因与选择性回灌判断

验证线真实样本第一次执行时，出现：

- 新时间戳目录被创建但为空
- Python 进程长时间高 CPU
- 无活跃网络连接

结合验证线实现与真实 workbook 元信息核对后，根因锁定为：

- `D:\get_bi_data__1\执行管理字段更新版.xlsx` 约 `215MB`
- `publish_source_reader` 仍在做 `load_workbook(..., data_only=True)` 全量加载
- 在真实大 workbook 上，这会卡在 publish source 读取阶段

验证线已证明的最小通用修复是：

- `load_workbook(..., data_only=True, read_only=True)`
- `iter_rows(..., values_only=True)`

这个修复是 foundation 级的 publish source 行为修复，不依赖本机私有资源，因此本次回灌到 `main`。

## TDD 回灌过程

### RED

先在主线新增回归测试：

- `tests/infrastructure/excel/test_publish_source_reader.py::test_read_publish_source_opens_large_workbook_in_read_only_mode`

验证命令：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_publish_source_reader.py -v -p no:cacheprovider
```

结果：

- `1 failed, 2 passed`
- 失败原因明确为：
  - `read_only` 实际为 `None`
  - 与新增测试预期 `True` 一致

### GREEN

随后在主线最小修复：

- `guanbi_automation/infrastructure/excel/publish_source_reader.py`

修改内容：

- workbook 读取切换为 `read_only=True`
- 单元格读取改为 `iter_rows(values_only=True)`
- 保留原有 trim 与 source range 语义

回归验证结果：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests/infrastructure/excel/test_publish_source_reader.py -v -p no:cacheprovider
```

- `3 passed`

## 主线 Fresh Verification

本次主线 fresh full suite 使用的可复现路径为：

```powershell
$env:PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'D:\miniconda3\envs\feishu-broadcast\python.exe' -m pytest tests -v -p no:cacheprovider
```

结果：

- `87 passed`

这同时修正了旧文档里“当前 shell 无法直接复现 main full suite”的过时表述。当前事实应改写为：

- shell PATH 中仍没有 `pytest`
- `feishu-broadcast` env 本身仍缺 `pytest / pydantic / PyYAML`
- 但 `feishu-broadcast python + root .packages` 已是可复现的主线 fresh verification 路径

## 与验证线的边界

当前仍留在验证线的内容：

- `.worktrees/publish-stage-task1/config/live_verification/publish/real_sample.local.yaml`
- `.worktrees/publish-stage-task1/guanbi_automation/live_verification/publish_real_sample.py`
- `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
- `.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`

这样做的原因是：

- 它们仍直接绑定真实资源、临时目标表和本机验证输入
- 它们承担的是“证明 publish live verification 已真实跑通”的职责
- 不是主线 foundation 的通用运行入口

## 当前恢复点

截至 2026-03-23：

- `main` 已回灌 publish source reader 的 streaming-safe 修复，并通过 fresh `87 passed`
- 验证线已具备首个有效 evidence archive 与最终 implementation archive
- 后续若要继续提升更多内容到 `main`，必须继续沿用：
  - 真实证据先形成
  - 只提升 foundation 级通用能力
  - 本地 spec / real-sample 入口 / evidence archive 仍留验证线
