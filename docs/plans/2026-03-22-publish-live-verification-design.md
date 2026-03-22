# Publish Live Verification Design

> 状态：Approved
> 最近更新：2026-03-22
> 前置阶段：`publish stage implementation`
> 后续阶段：`publish live verification implementation plan`
> 关联文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-21-publish-stage-detailed-design.md`

## 1. 背景

`publish stage implementation` 已完成并通过 focused verification 与 full suite。

当前下一步不是回到 workbook 设计，也不是继续补抽象配置，而是用真实样本把 publish 从“结构正确”推进到“真实资源可写、可读回、可比对”。

本次设计继续遵守以下边界：

1. 新实现只落在 `guanbi_automation/`，不回 legacy `src/`
2. 当前只做 `publish` 真实样本验证，不把生产 job 系统重新展开
3. 飞书行为只以官方文档与实际接口回包为准，不靠猜测
4. 验证必须留下可恢复、可诊断、可复查的运行证据

## 2. 已确认事实

### 2.1 真实样本源

当前首个真实样本固定为：

- workbook：`D:\get_bi_data__1\执行管理字段更新版.xlsx`
- source sheet：`全国执行`
- source anchor：`A1`
- `header_mode=include`

基于本地读取证据，当前样本实际形状为：

- `row_count = 80`
- `column_count = 127`

这不是假设，而是对当前本地样本的实际读取结果。

### 2.2 飞书目标

当前继续沿用既有飞书资源，不重新创建新文档：

- 飞书应用：沿用根目录 `.env` 中既有 `FEISHU_APP_ID / FEISHU_APP_SECRET`
- target spreadsheet：沿用既有旧 spreadsheet
- target sheet：沿用现有临时空白子表 `测试子表`
- target resolution：使用 `sheet_id`

当前通过官方 `query sheets` 接口已确认：

- `测试子表` 的 `sheet_id = ySyhcD`
- 当前 `A1:H8` 读回为空白

### 2.3 配置来源

基于当前本地仓库状态可以确认：

- 根目录 `.env` 当前只包含飞书应用凭据，不包含 spreadsheet token
- legacy `src/config/config.json` 中仍保留旧 spreadsheet token

因此这里有一个必须显式说明的推断：

- “沿用旧 `.env` 与旧 spreadsheet” 在工程上应理解为“沿用既有 app 凭据与既有目标文档”，而不是继续在运行时依赖 legacy config 结构

当前更干净的落点是：

- app 凭据继续来自根目录 `.env`
- spreadsheet token / target `sheet_id` 进入专用 live-verification spec
- runtime 不直接 import 或解析 legacy `src/` 配置

## 3. 官方约束与证据

本次设计使用的飞书官方约束如下：

- `tenant_access_token`：
  - `POST /open-apis/auth/v3/tenant_access_token/internal`
  - 自建应用可用
  - 最大有效期 2 小时
- `query sheets`：
  - `GET /open-apis/sheets/v3/spreadsheets/:spreadsheet_token/sheets/query`
  - 可返回 `sheet_id`、`title`、`hidden`
- `read single range`：
  - `GET /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values/:range`
  - `range` 格式为 `<sheetId>!A1:B2`
  - 单次响应最大 `10 MB`
- `write single range`：
  - `PUT /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values`
  - 单次最多 `5000` 行、`100` 列
- `write multiple ranges`：
  - `POST /open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values_batch_update`
  - 同样受单次 `5000` 行、`100` 列约束，但允许一次提交多个矩形范围
- 文档权限：
  - 既需要应用本身具备云文档 API scope
  - 也需要目标 spreadsheet 对应用开放文档权限

## 4. 方案对比

### 4.1 方案 A：直接复用 legacy config 读取旧 token 并执行 live write

优点：

- 最省事

缺点：

- 运行时重新依赖 legacy 配置结构
- 把“沿用旧资源”错误实现成“继续借用旧脚本组织方式”
- 违反当前从 0 构建与物理隔离边界

结论：

- 不采用

### 4.2 方案 B：沿用既有 app 与 spreadsheet，但建立专用 live-verification spec

做法：

- 根目录 `.env` 提供 app 凭据
- 新增专用 local spec，声明 workbook/source/target 标识
- 用新实现直接调用官方接口完成写入、读回、比对和归档

优点：

- 沿用真实资源，但不回 legacy
- 运行输入与生产 job 配置解耦
- 更适合一次性真实验证与证据归档

缺点：

- 需要新增一个很薄的验证入口

结论：

- 当前采用该方案

### 4.3 方案 C：暂时换窄表样本，规避 127 列问题

优点：

- 可以绕开列限制实现

缺点：

- 偏离已锁定的 `全国执行`
- 把真实问题推迟到后续
- 验证价值明显下降

结论：

- 不采用

## 5. 设计结论

### 5.1 目标边界

本次 live verification 固定为：

- 单 workbook
- 单 source sheet
- 单 target sheet
- 单 mapping 语义
- `write_mode = replace_sheet`
- 从 `A1` 开始
- 首行一起写入
- 必须读回校验

这一步不是生产调度系统，而是 publish 的真实样本验证入口。

### 5.2 专用 spec

当前推荐新增：

- `config/live_verification/publish/real_sample.example.yaml`
- `config/live_verification/publish/real_sample.local.yaml`

其中：

- `example` 文件进入版本库，只保留结构与占位
- `local` 文件保存本机真实标识，不进入版本库

spec 至少包含：

- `workbook_path`
- `source_sheet_name`
- `source_start_row`
- `source_start_col`
- `header_mode`
- `spreadsheet_token`
- `sheet_id`
- `target_start_row`
- `target_start_col`
- `write_mode`

### 5.3 数据规范化

真实样本验证不应把 openpyxl 的原始 Python 值直接塞给飞书接口。

当前正式规则为：

- `str`：原样保留
- `int / float`：原样保留
- `date / datetime`：转成稳定字符串
  - 纯日期优先写成 `YYYY-MM-DD`
  - 含时间部分时写成 `YYYY-MM-DD HH:MM:SS`
- `None`：写成空字符串 `""`

设计原因：

- 飞书 V2 数据接口原生支持字符串和数字
- 日期若走数值序列，需要额外样式设置，超出本次 live verification 范围
- 空单元格若直接保留 Python `None`，JSON 序列化和读回对比语义都不稳定

### 5.4 列感知写入

真实样本 `全国执行` 当前为 `80 x 127`，已经超过飞书单次 `100` 列限制。

因此当前正式策略固定为：

- 先按行判断是否超过 `5000`
- 再按列判断是否超过 `100`
- 任何一维超限，都必须继续切分

对于当前样本：

- 行数 `80` 未超限
- 列数 `127` 超限
- 因此应拆成两个矩形范围：
  - `A1:CV80`
  - `CW1:DW80`

第一版更优路径为：

- 优先使用 `values_batch_update` 一次提交多个矩形范围
- 若后续测试证明拆成多次 `write single range` 更稳，再基于证据调整

当前不再接受：

- 只按行分块
- 先截断到 100 列再验证
- 换样本回避真实限制

### 5.5 读回校验

live verification 的完成标准不是“接口 200”。

必须固定执行：

1. 获取 tenant token
2. 查询 spreadsheet metadata 并确认 `sheet_id`
3. 读取 workbook source，并做规范化
4. 生成列感知写入计划
5. 写入目标范围
6. 读取相同目标范围
7. 做矩阵级对比
8. 落证据归档

比对至少覆盖：

- `row_count`
- `column_count`
- 首行表头
- 全矩阵 canonical equality
- 首若干行 preview

其中 readback comparison 使用 canonical cell normalizer：

- 空值统一归一为 `""`
- 数字统一转换为稳定字符串表达
- 其余值统一转换为稳定文本

### 5.6 归档结构

推荐归档到：

```text
runs/live_verification/
  publish/
    <timestamp>/
      request.json
      source-metadata.json
      target-metadata.json
      write-plan.json
      write-result.json
      readback.json
      comparison.json
```

关键要求：

- 归档是本地运行证据，不作为主文档替代
- 会话结束后仍需回写 `docs/archive/sessions/*.md`

## 6. 失败语义

live verification 至少要稳定区分：

- `publish_auth_error`
- `publish_target_missing`
- `publish_range_invalid`
- `publish_write_error`
- `publish_source_read_error`
- `publish_rate_limit_error`

此外再新增一类验证态失败：

- `publish_readback_mismatch`

它不是飞书接口失败，而是“写成功但读回结果与预期不一致”。

## 7. 测试边界

自动化测试至少覆盖：

- live-verification spec 解析
- 值规范化
- 宽表列分段规划
- `values_batch_update` 请求体构造
- 读回 canonical compare
- evidence archive 结构

手工验证必须覆盖：

- 用真实 workbook `全国执行`
- 用真实 target `测试子表 / ySyhcD`
- 真实写入后读回通过
- 运行证据成功落盘

## 8. 当前恢复点

本设计批准后，下一步固定为：

1. 写 `docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
2. 按 TDD 执行真实样本验证实现
3. 完成一次真实写入 + 读回 + 归档
4. 再进入 publish hardening
