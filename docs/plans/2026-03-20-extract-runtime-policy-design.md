# 观远 BI 自动化套件 Extract Runtime Policy 设计

> 状态：Approved
> 最近更新：2026-03-20
> 前置阶段：`runtime contract`
> 后续阶段：`extract runtime policy implementation`
> 关联文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-19-runtime-contract-and-stage-gating-design.md`

## 1. 背景

`runtime contract` 已经完成最小落地，但当前 extract 仍只有一套粗粒度 polling 配置。下一步要解决的问题不是 workbook，而是把 extract 主链路的运行策略正式收敛为可配置、可归档、可调优的运行政策。

这里的 extract 主链路明确指：

1. `submit`
2. `poll`
3. `download`

目标不是把所有任务统一设成“尽快失败”，而是让轻量任务不会被重任务拖慢，同时让历史上确实存在的慢任务和大数据量任务有正式的宽松档位，而不是靠到处改魔法数字维持。

## 2. 历史证据

### 2.1 轮询确实存在长耗时样本

旧日志已经证明，部分导出任务的正常等待时间会明显长于几十秒：

- `logger/log_15202603_1005.txt` 出现最长 `99s` 的轮询等待。
- `logger/log_12202603_0850.txt` 出现最长 `72s` 的轮询等待。
- `logger/log_17202601_0818.txt` 出现最长 `71s` 的轮询等待。
- `logger/log_07202603_0850.txt` 出现最长 `54s` 的轮询等待。
- `logger/log_21202601_0818.txt`、`logger/log_21202601_1356.txt` 也分别出现 `37s`、`32s` 的等待。

这意味着统一使用过紧的总等待上限会误杀真实业务任务。

### 2.2 大表场景真实存在

旧日志已经记录了大体量下载与后续处理样本：

- `logger/log_21202601_0818.txt` 出现 `66 x 219336`。
- `logger/log_21202601_1356.txt` 出现 `66 x 219336`。
- `logger/log_10202601_0818.txt` 出现 `66 x 218155`。
- `logger/log_07202603_0850.txt` 出现 `70 x 215501`。

这些样本在旧链路中还表现为明显的读取与写入耗时，因此 download 阶段不能套用 submit 的短请求策略。

### 2.3 瞬时网络错误也是真实失败模式

旧日志中还已出现：

- `logger/log_09202601_0818.txt` 的 `SSLError`
- `logger/log_13202602_0818.txt` 的 `ConnectTimeout`

因此 runtime policy 仍必须保留对瞬时网络错误的有限重试能力。

## 3. 方案对比

### 3.1 方案 A：整条 extract 共用一套预算

优点：

- 配置最少
- 初看实现简单

缺点：

- `submit / poll / download` 三段行为本质不同，却被迫共用同一套 timeout 与 retry 语义。
- 轻量任务和重任务无法分开调优。
- manifest 归因会变模糊，难以看出耗时集中在哪一段。

结论：

- 不采用。

### 3.2 方案 B：三段拆预算，但没有档位

优点：

- 比单预算更专业。
- 可以独立控制 `submit / poll / download`。

缺点：

- 仍然需要针对慢任务手工逐个改数字。
- 缺少模板级可复用的“运行重量”表达。

结论：

- 比方案 A 更好，但还不够工程化。

### 3.3 方案 C：三段拆预算 + 运行档位 + 总时限

优点：

- `submit / poll / download` 能按阶段语义独立控制。
- 轻量任务与重任务可以用不同 profile，不互相拖累。
- 仍保留 `extract_total_deadline` 作为整条链路的总刹车。
- manifest 和调参入口都更清晰。

缺点：

- 配置结构比单预算更复杂。

结论：

- 当前采用该方案。

## 4. 设计结论

### 4.1 Extract 运行边界

一个 extract 运行被正式拆成 4 层：

1. `submit`
2. `poll`
3. `download`
4. `extract_total_deadline`

其中：

- 分段预算负责每个动作自己的 timeout / retry 语义。
- `extract_total_deadline` 负责给整条链路设置最终硬上限。

### 4.2 Runtime Profile

第一版正式引入 3 个 extract runtime profile：

- `fast`
- `standard`
- `heavy`

它们不是 UI 展示标签，而是稳定的运行档位语义。

### 4.3 档位选择规则

当前采用：

- `extract template` 保存 `runtime_profile`
- `run batch` 允许 `runtime_profile_override`
- 实际执行使用：`override > template default`

默认档位为：

- `standard`

当前不采用“系统自动推断档位”作为第一版前置能力，因为历史数据虽足以证明慢任务存在，但还不足以支撑可靠自动分类。

## 5. 预算模型

### 5.1 配置结构

extract runtime policy 在配置层应至少表达：

- `runtime_profile`
- `submit_budget`
- `poll_budget`
- `download_budget`
- `total_deadline_seconds`

`submit_budget` 和 `download_budget` 负责请求型 timeout / retry；`poll_budget` 负责轮询间隔、最长等待和瞬时错误重试；`total_deadline_seconds` 作为整条 extract 的总硬上限。

### 5.2 Profile 默认值

#### `fast`

- `submit`
  - `connect_timeout = 3s`
  - `read_timeout = 8s`
  - `network_retries = 1`
- `poll`
  - `poll_interval = 2s`
  - `max_wait = 45s`
  - `transient_error_retries = 1`
  - `backoff_policy = fixed`
- `download`
  - `connect_timeout = 5s`
  - `read_timeout = 15s`
  - `network_retries = 1`
- `total_deadline = 75s`

#### `standard`

- `submit`
  - `connect_timeout = 3s`
  - `read_timeout = 10s`
  - `network_retries = 1`
- `poll`
  - `poll_interval = 2s`
  - `max_wait = 150s`
  - `transient_error_retries = 2`
  - `backoff_policy = fixed`
- `download`
  - `connect_timeout = 5s`
  - `read_timeout = 30s`
  - `network_retries = 1`
- `total_deadline = 210s`

#### `heavy`

- `submit`
  - `connect_timeout = 5s`
  - `read_timeout = 15s`
  - `network_retries = 2`
- `poll`
  - `poll_interval = 3s`
  - `max_wait = 240s`
  - `transient_error_retries = 3`
  - `backoff_policy = fixed`
- `download`
  - `connect_timeout = 8s`
  - `read_timeout = 60s`
  - `network_retries = 2`
- `total_deadline = 360s`

### 5.3 轮询语义

必须明确区分：

- 正常状态轮询
- 错误重试

`PROCESSING -> PROCESSING -> PROCESSING` 这类正常状态检查，不消耗错误重试预算。只有瞬时网络错误才消耗 `poll` 的 `transient_error_retries`。

## 6. 错误分类与重试边界

### 6.1 submit

允许有限重试：

- `network_connect_timeout`
- `network_ssl_error`

立即失败：

- `authentication_error`
- `configuration_error`
- `payload_parse_error`
- 非网络类请求提交失败，归 `request_submit_error`

### 6.2 poll

正常继续轮询：

- `PROCESSING`
- 其他等价“任务仍在执行中”的状态

允许有限重试：

- `network_connect_timeout`
- `network_ssl_error`

立即失败：

- 任务状态明确失败
- 返回结构不可解析
- 返回内容与预期状态模型不一致

轮询超过等待预算时，稳定归类为：

- `poll_timeout`

### 6.3 download

允许有限重试：

- `network_connect_timeout`
- `network_ssl_error`

立即失败：

- 文件响应结构异常
- 下载响应不可解析
- 本地能力或路径问题

### 6.4 最终归因

extract 最终错误按“最后失败阶段优先”归因：

- `submit` 失败 -> `final_error = submit_final_error`
- `poll` 失败 -> `final_error = poll_final_error`
- `download` 失败 -> `final_error = download_final_error`

不允许只记录模糊的 `extract_failed` 而不保留阶段归因。

## 7. Manifest 与 Event 记录

extract manifest 最小字段扩展为：

- `template_runtime_profile`
- `effective_runtime_profile`
- `submit_attempts`
- `submit_elapsed_seconds`
- `submit_final_error`
- `poll_attempts`
- `poll_total_wait_seconds`
- `poll_elapsed_seconds`
- `poll_final_error`
- `download_attempts`
- `download_elapsed_seconds`
- `download_final_error`
- `extract_total_elapsed_seconds`
- `deadline_exhausted`
- `final_error`
- `completed`

设计原则：

- 分段证据必须可见。
- 既要知道哪里失败，也要知道时间花在哪里。
- profile 必须写入 manifest，便于后续归档比较与调参。

## 8. 与现有 runtime contract 的关系

该设计是 `runtime contract` 的细化阶段，不推翻已锁定顺序：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

它也不改变“新项目从 0 构建”和“不回到 legacy `src/`”的既定边界。

## 9. 当前不做的事情

本阶段明确不做：

- workbook writer engine 设计
- publish runtime policy 细化
- 基于历史 manifest 的自动 profile 推断
- 为每一种观远业务失败立刻扩展完整 taxonomy

这些都不应阻塞 extract runtime policy 第一版落地。

## 10. 实施影响

该设计落地后，会带来以下直接影响：

- bootstrap 中的 runtime settings 需要从单一 `extract_polling` 升级为 profile-aware 结构。
- extract planning 与 stage execution 需要同时感知模板默认 profile 和运行时 override。
- polling / network error policy 需要从“只看轮询”升级到覆盖 `submit / poll / download` 三段。
- extract manifest 需要补齐分段证据字段。
- 测试需要覆盖：
  - profile 选择
  - 长轮询场景
  - 瞬时网络错误重试
  - 最终错误归因

## 11. 后续入口

本设计批准后，下一步不是直接写代码，而是：

1. 写 `extract runtime policy implementation plan`
2. 按 TDD 实施
3. 落地后再进入下一阶段的 workbook 细化
