# 2026-03-22 会话归档（Publish Live Verification Design Approval）

## 1. 本次目标

在 `publish stage implementation` 完成后，正式锁定：

- `publish` 真实样本验证边界
- 真实 workbook source
- 真实飞书 target
- 官方约束下的写入与读回校验路径

本次仍未进入 live verification 编码实现。

## 2. 已批准设计结论

### 2.1 真实样本

当前首个真实样本固定为：

- workbook：`D:\get_bi_data__1\执行管理字段更新版.xlsx`
- source sheet：`全国执行`
- source anchor：`A1`
- `header_mode=include`

### 2.2 真实目标

当前继续沿用既有飞书资源：

- app 凭据：根目录 `.env` 中既有 `FEISHU_APP_ID / FEISHU_APP_SECRET`
- spreadsheet：沿用既有旧 spreadsheet
- target 子表：`测试子表`
- `sheet_id = ySyhcD`

当前通过官方接口已确认 `测试子表` 为空白，适合作为临时验证位。

### 2.3 工程落点

已批准的工程落点为：

- 不直接在运行时依赖 legacy `src/config/config.json`
- app 凭据继续从 `.env` 读取
- spreadsheet token 与 target `sheet_id` 落到专用 live-verification spec
- 新实现只落在 `guanbi_automation/`

### 2.4 宽表写入策略

基于真实样本读取结果，`全国执行` 当前形状为 `80 x 127`。

这与飞书官方单次写入 `100` 列限制发生真实碰撞，因此已批准：

- 写入必须做 row/column 双维度分段
- 对当前样本按列拆为 `100 + 27`
- 优先使用 `values_batch_update`
- 不允许通过截断列数或更换样本规避问题

### 2.5 完成标准

live verification 的完成标准固定为：

1. tenant token 获取成功
2. target metadata 解析成功
3. workbook source 规范化成功
4. 写入成功
5. 读回成功
6. canonical matrix comparison 成功
7. evidence archive 落盘

## 3. 文档同步

本次应同步更新：

- `docs/plans/2026-03-22-publish-live-verification-design.md`
- `docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-22-publish-live-verification-design-approval.md`

## 4. 当前恢复点

截至本次设计批准：

- publish live verification design 已完成
- 当前下一恢复点前移为：
  - 执行 `docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
  - 完成真实写入 + 读回 + 归档
  - 再进入 publish hardening
