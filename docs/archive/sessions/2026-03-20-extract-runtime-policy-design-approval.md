# 2026-03-20 Extract Runtime Policy 设计确认归档

## 1. 本次会话目标

在 `runtime contract` 已完成的前提下，继续推进既定顺序中的下一阶段：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

本次会话不进入 workbook，不改 legacy `src/`，只收敛 extract 主链路的运行策略设计。

## 2. 本次核对与补证

本次会话先基于当前工作区和旧日志补充证据，确认以下事实：

- extract 主链路不是单一动作，而是 `submit -> poll -> download`。
- 旧日志存在显著长轮询样本：
  - `logger/log_15202603_1005.txt` 最长 `99s`
  - `logger/log_12202603_0850.txt` 最长 `72s`
  - `logger/log_17202601_0818.txt` 最长 `71s`
- 旧日志存在显著大表样本：
  - `logger/log_21202601_0818.txt` 的 `66 x 219336`
  - `logger/log_21202601_1356.txt` 的 `66 x 219336`
  - `logger/log_07202603_0850.txt` 的 `70 x 215501`
- 旧日志仍包含瞬时网络错误：
  - `logger/log_09202601_0818.txt` 的 `SSLError`
  - `logger/log_13202602_0818.txt` 的 `ConnectTimeout`

这些证据直接推翻了“统一偏紧默认预算”的主观方案。

## 3. 本次确认的设计结论

用户逐段确认了以下 extract runtime policy 设计：

1. extract 主链路正式拆为：
   - `submit`
   - `poll`
   - `download`
   - `extract_total_deadline`
2. 采用三段分离预算，而不是整条 extract 共用一套预算。
3. 引入三档 runtime profile：
   - `fast`
   - `standard`
   - `heavy`
4. profile 选择采用：
   - `extract template` 默认值
   - `run batch` 运行时 override
5. 默认档位为：
   - `standard`
6. `PROCESSING` 等正常轮询状态不消耗错误重试预算。
7. 只有瞬时网络错误进入有限重试：
   - `network_connect_timeout`
   - `network_ssl_error`
8. extract 最终错误按最后失败阶段归因，不再允许只写模糊的 `extract_failed`。

## 4. 本次文档同步

本次会话新增或更新了以下文档：

- 新增：
  - `docs/plans/2026-03-20-extract-runtime-policy-design.md`
  - `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md`
  - `docs/archive/sessions/2026-03-20-extract-runtime-policy-design-approval.md`
- 更新：
  - `docs/plans/master-system-design.md`
  - `docs/plans/master-implementation-roadmap.md`
  - `docs/archive/decision-log.md`

## 5. 当前恢复点

本次设计确认完成后，下一步恢复入口为：

1. 按 `docs/plans/2026-03-20-extract-runtime-policy-implementation-plan.md` 执行
2. 逐任务按 TDD 实施
3. workbook 仍然保持在此阶段之后

当前仍不应做：

- workbook 实现
- 回到 legacy `src/` 改脚本
- 跳过实施计划直接编码
