# 2026-03-22 会话归档（Mainline Foundation Extraction）

## 当前结论

- `main` 已按“稳定主线优先”的原则，萃取并保留 `publish foundation`。
- `publish live verification` 继续保留在 `publish-stage-task1` worktree 中推进，不直接进入主线。
- 主线与验证线从本次开始显式分层治理。

## 本次萃取到主线的范围

本次进入 `main` 的内容包括：

- `publish contract`
- `publish source reader`
- `publish target planner`
- `feishu sheets client adapter`
- `publish stage`
- `publish gate / preflight / pipeline engine wiring`
- 对应测试
- publish implementation 最终归档

对应来源提交为：

- `0525159`
- `d155c04`
- `f6d718f`
- `e16362a`
- `5fea856`
- `867412a`
- `1b8c5a5`
- `80f5bd6`
- `c47a044`
- `082e487`
- `13259ce`

## 本次明确留在验证线的范围

以下内容仍保留在 `publish-stage-task1`：

- publish live verification 设计
- live verification spec
- Feishu readback support
- publish live verification service
- real sample entry
- 真实写入 / 读回 / comparison 证据归档

## 治理结论

后续阶段统一按以下规则执行：

- `main` 保留稳定、可复验、可作为基线继续开发的内容
- 验证线继续向真实资源边界推进
- 真实验证成功后，再做第二次萃取，而不是把探索过程整体并回主线

## 当前恢复点

- 主线当前状态：`publish foundation` 已在 `main`
- 验证线当前状态：`publish-stage-task1` 继续承担 publish live verification
- 主线下一步：
  - 保持稳定
  - 等待验证线拿到真实样本证据后，再选择性提升
- 验证线下一步：
  - 完成 live verification Task 5
  - 产出真实写入、读回和 comparison evidence

