# 观远 BI 自动化套件主设计文档

> 状态：Active
> 最近更新：2026-03-23
> 当前权威文档：
> - `docs/plans/master-system-design.md`
> - `docs/plans/master-implementation-roadmap.md`
> - `docs/archive/decision-log.md`
> - `docs/plans/2026-03-22-mainline-validation-governance-design.md`
> - `docs/plans/2026-03-22-repository-state-and-recovery-design.md`

## 1. 文档治理规则

本项目的规划与归档采用固定三层结构，并从本次会话开始强制执行：

1. 主规划文档：保存当前生效版本。
2. 每次对话单独归档：记录本次新增信息、被推翻内容、待确认项。
3. 决策日志：记录关键取舍、原因、影响范围与后果。

同时明确以下原则：

- 除当前列出的权威文档外，其余规划文档默认按历史记录处理；即使是权威文档，也只是记录某一时点的最优判断。
- `master` 文档不是永久真理，只是“当前全局最优的工作版本”。
- 任何新的真实验证结果、实现阻力、边界变化，都必须反向审视当前 `master` 文档是否仍是全局最优。
- 发现更优路径时，必须更新 `master` 文档、追加 `decision-log`，并保留旧判断作为可追溯历史，而不是静默覆盖。
- 任何重大架构取舍在进入 `master` 前，至少要完成一次证据对比（历史抓包、日志、样本、已有验证记录）或一次最小 spike 测试。

### 1.1 当前恢复入口规则

从 2026-03-22 起，文档恢复入口固定为：

1. 先读 `master` 文档与 `decision-log`
2. 再读最新状态对账文档
3. 最后才按需要翻 `sessions` 历史归档

同时明确：

- `sessions` 文档默认是历史现场记录，不自动等于当前现状
- worktree 下的文档只对该验证线直接生效，不能替代主线权威文档
- `README.md` 是恢复导航入口，不单独替代 `master` 文档、`decision-log` 和最新状态对账文档
- 历史归档保持不可变；若当前事实发生变化，应新增对账文档或更新 `master`，而不是改写旧归档

## 2. 不可违背的项目边界

以下边界已经确认，后续不得偏离：

- 新项目的实现代码必须从 0 构建。
- 当前目录中的 legacy `src/`、`logger/`、`记录/`、根目录 `.xlsx` 文件，只是需求、接口、业务规则和失败模式的参考证据库。
- 新项目不得通过“在旧脚本上持续修补”来冒充重构完成。
- 新项目代码不得直接依赖 legacy `src` 模块。
- 允许继承的内容只有：接口知识、真实请求样本、Excel 业务映射经验、已知失败模式、验证清单。

## 3. 产品定位

本项目是一个本地运行的观远 BI 自动化套件，目标用户通过友好的可视化界面完成以下事情：

1. 浏览账号下可访问的页面、面板和筛选器。
2. 点击想要的面板与筛选条件，确认需要下载的文件配置。
3. 将这些下载定义保存为可复用模板。
4. 将多个模板组合成多个任务配置文件。
5. 选择一个或多个任务执行，并获得完整归档。
6. 按需继续进入 Excel 和飞书阶段。

这意味着产品必须同时支持：

- 面向“单个抽取定义”的交互。
- 面向“多个任务配置文件并存”的编排。
- 面向“单次执行中多个任务共享部分抽取结果”的工程能力。

## 4. 用户操作视角

从用户视角，系统应被理解为 5 个工作区：

### 4.1 资源浏览区

用于刷新与浏览观远页面树，展示：

- 文件夹
- 页面
- 自定义查询
- 页面内可导出图表
- 页面筛选器与图表关系

### 4.2 抽取配置区

用于从页面详情中点选图表、选择筛选条件、保存抽取模板。

核心交互是：

- 选中图表
- 选中筛选器
- 配置动态规则
- 保存为 `extract template`

### 4.3 任务编排区

用于从多个 `extract template` 中挑选并组合出一个业务任务。

核心交互是：

- 选择要使用的 extracts
- 排列阶段顺序
- 开关 workbook / publish 阶段
- 保存为 `job template`

### 4.4 运行中心

用于选择一个或多个 `job template` 发起执行，并查看本次批次状态。

### 4.5 归档查看区

用于回看某次执行的：

- 批次 manifest
- 实际筛选条件
- 下载文件
- workbook 阶段产物
- publish 摘要
- 失败位置

## 5. 推荐总体架构

采用“Core-first, Web-ready”的方案。

含义如下：

- 产品入口是本地 Web 控制台。
- 先把核心模型、执行引擎、归档结构定稳，再把 Web 接到这些稳定边界上。
- Web 是一体化使用入口，但不是业务逻辑中心。

不推荐的方向：

- 先做脚本，后面再慢慢补 Web。
- 先做大而全界面，再倒逼后端建模。
- 把多个任务配置继续揉在一个扁平配置文件里。

## 6. 目标代码结构

结合“多任务并存”和“从 0 构建”的要求，当前建议将新项目代码根细化为以下结构：

```text
guanbi_automation/
  __init__.py
  main.py
  bootstrap/
    settings.py
    logging.py
    container.py
  domain/
    project.py
    page_snapshot.py
    extract_template.py
    job_template.py
    run_batch.py
    errors.py
  application/
    discovery_service.py
    template_service.py
    run_service.py
    preflight_service.py
  execution/
    run_planner.py
    pipeline_engine.py
    manifest_builder.py
    stages/
      extract.py
      workbook_ingest.py
      workbook_transform.py
      publish.py
  infrastructure/
    guanbi/
    excel/
    feishu/
    storage/
  web/
    routes/
    presenters/
    templates/
    static/
tests/
config/
templates/
  extracts/
  jobs/
snapshots/
  pages/
runs/
references/
```

### 6.1 各层职责

- `bootstrap/`：启动、配置、日志、依赖装配。
- `domain/`：系统中的核心对象与约束，不依赖外部系统。
- `application/`：组织业务用例，协调 domain、execution 与 infrastructure。
- `execution/`：负责运行计划展开、阶段引擎、manifest 生成。
- `infrastructure/`：负责观远、Excel、飞书、文件系统等外部依赖的适配。
- `web/`：负责可视化界面、输入输出展示和路由。

### 6.2 调用边界

必须遵守以下边界：

- `web -> application`
- `application -> domain + execution + infrastructure(通过接口/仓储)`
- `execution -> domain + infrastructure`
- `infrastructure` 只向外部系统发起调用，不反向依赖 `web`
- `domain` 不依赖任何外部实现细节

禁止行为：

- 在 `web` 层直接写 requests、Excel、Feishu 调用。
- 在 `domain` 层读写文件或发 HTTP 请求。
- 在 `application` 层散落具体的 GUI 或模板渲染细节。

## 7. 核心领域模型

### 7.1 项目配置 `project`

保存全局配置，例如：

- 默认时区
- 归档目录
- 观远站点地址
- 模板目录
- UI 默认行为
- 功能开关

### 7.2 页面快照 `page snapshot`

用于保存某次发现到的页面结构，至少包含：

- 页面基础信息
- `cards`
- `filterLayout`
- `tabMap`
- `dsInfos`
- 页面中可导出图表清单

### 7.3 抽取模板 `extract template`

这是系统中最小可复用抽取单元，不直接等价于某个页面，也不直接等价于某个 chart id。

一个 extract 至少包含：

- `extract_id`
- `page_id`
- `chart_id`
- `chart_name`
- `filter_template`
- `dynamic_rules`
- `archive_naming`

这样做的原因是：

- 同一个 `chart_id` 可能需要不同筛选条件导出多次。
- 同一个图表的不同用途应使用不同 extract，而不是在运行时临时拼装。

### 7.4 任务模板 `job template`

一个 job 表示一条完整业务任务，是“多个配置文件任务并存”的正式承载对象。

一个 job 至少包含：

- `job_id`
- `name`
- 引用的 `extracts`
- 阶段顺序
- 各阶段配置
- 默认开关
- 输出与归档规则

### 7.5 运行批次 `run batch`

单次操作员点击执行，不应只对应一个 job。更合理的模型是：

- 一次运行批次可以选择 1 个或多个 job。
- 一个批次中会产生若干 `extract run`。
- 一个批次中会产生若干 `job run`。
- workbook / publish 阶段以 `job run` 为边界。
- 抽取去重以 `extract run` 为边界。

### 7.6 运行清单 `manifest`

manifest 需要分层，而不是只有一个扁平大文件：

- `batch manifest`
- `extract manifest`
- `job manifest`
- 必要时的 `stage result`

### 7.7 筛选器与动态规则模型

当前对比后的最优路径不是“完全抽象化筛选器模型”，也不是“只保存原始 payload 不建模”，而是采用混合模型：

- 页面快照中保留尽可能完整的 selector 原始元数据。
- extract template 中保存执行所需的最小稳定引用和 `template_payload`。
- 动态行为通过独立 `dynamic_rule` 描述，而不是直接在原始 payload 上做临时字符串替换。

这样做的原因是：

- 观远 selector 结构存在真实差异，过度抽象很容易丢失语义。
- 如果只保存原始 payload，则 UI 编辑、动态日期规则、去重签名和校验都会变得脆弱。
- 混合模型既保留原始结构，又允许稳定渲染和测试。

一个 extract 中的单个筛选绑定至少应包含：

- `selector_ref`
- `template_payload`
- `value_mode`
- `dynamic_rule` 或 `literal_value`
- `display_value_policy`
- `required`

其中：

- `selector_ref` 用于稳定定位 selector，优先使用 `fdId + cdId + dsId`。
- `template_payload` 用于保留发送给观远接口所需的原始字段形状。
- `value_mode` 用于区分 `dynamic / literal / passthrough`。
- `display_value_policy` 默认使用 `auto`，只有在观远确实要求时才使用显式值。

### 7.8 当前规则类型范围

基于现有历史样本和验证记录，第一阶段必须稳定支持：

- `date_range`
- `date_list`
- `month_list`
- `literal`
- `passthrough`

当前证据覆盖如下：

- `记录/all_ploy.txt` 已出现：
  - `BT + STRING`
  - `IN + STRING`
  - `IN + DATE`
- `docs/plans/2026-03-19-guanbi-live-verification.md` 已确认：
  - `selectorType=TIME_MACRO`
  - `selectorType=DS_ELEMENTS`

这意味着当前最优建模边界是：

- 执行语义必须同时考虑 `filterType` 和 `selectorType`。
- 第一阶段优先做“值渲染与模板化”。
- `DS_ELEMENTS` 的候选值在线接口先不作为主阻塞项。

### 7.9 `DS_ELEMENTS` 的第一阶段策略

对于 `DS_ELEMENTS`，当前不建议把“在线候选值自动拉取”作为第一阶段前置条件。

当前更优路径是：

1. 先支持识别与保存 `DS_ELEMENTS` selector 元数据。
2. 先支持手工录入 literal 值。
3. 如果页面快照中存在可用候选项缓存，则可展示为只读建议值。
4. 在线候选值接口作为后续增强项，待稳定 endpoint 锁定后再接入。

这样可以避免为了一个尚未完全锁定的接口，阻塞整个模板系统落地。

## 8. 多任务执行与共享策略

这是当前全局框架中最关键的工程点之一。

### 8.1 基本原则

- 用户可以维护多个 `job template`。
- 每个 job 可以引用多个 extracts。
- 同一次执行可以同时选择多个 jobs。
- 同一次执行内，如果多个 jobs 依赖的 extract 在最终展开后完全相同，则只下载一次。
- 跨天、跨批次默认不复用历史下载结果。

### 8.2 运行计划展开 `run planner`

`run planner` 必须负责：

1. 读取本次选择的 jobs。
2. 展开所有引用的 extracts。
3. 将动态规则渲染为本次真实筛选条件。
4. 基于归一化后的条件生成 `extract_signature`。
5. 对相同 signature 的 extract 执行去重。
6. 生成本次 `run batch plan`。

### 8.3 去重边界

- 同图表但不同筛选条件：不能去重。
- 同图表同筛选条件但被多个 job 复用：可以去重。
- 历史下载文件只用于归档回看，不作为默认缓存。

### 8.4 归一化与签名规则

`extract_signature` 不应直接对原始请求 JSON 做字符串哈希，也不应只用 `chart_id` 粗暴去重。

当前更优路径是：

- 先将筛选条件渲染为标准化结构。
- 再对“语义上影响结果的字段”做 canonical serialization。
- 最终基于规范化结果生成 signature。

当前推荐纳入 signature 的字段：

- `site_key`
- `page_id`
- `chart_id`
- `export_format`
- 每个筛选项的：
  - `fdId`
  - `cdId`
  - `dsId`
  - `filterType`
  - `fdType`
  - 标准化后的 `filterValue`
  - 必要时的 `macroName`

当前不建议默认纳入 signature 的字段：

- `displayValue`
- 人类可读描述
- 纯展示用途的名称字段

原因是当前证据显示 `displayValue` 更像派生展示值，而不是结果语义本身。若后续 spike 证明其影响结果，再调整该规则。

## 9. 持久化与归档策略

当前推荐使用混合方案：

- 人工维护、需要可读可改的配置使用 YAML。
- 机器生成、强调结构稳定和复现实验的数据使用 JSON。
- 大文件与运行产物使用文件系统目录归档。

推荐目录如下：

```text
config/
  project.yaml
templates/
  extracts/
    *.yaml
  jobs/
    *.yaml
snapshots/
  pages/
    *.json
runs/
  YYYY-MM-DD/
    <run_batch_id>/
      run-request.json
      preflight-report.json
      run-plan.json
      batch-manifest.json
      logs/
        events.log
      extracts/
        <extract_run_id>/
          manifest.json
          request.json
          normalized-filters.json
          downloads/
      jobs/
        <job_run_id>/
          manifest.json
          workbook/
          publish/
```

这种结构比旧的扁平 `runs/<run_id>/downloads` 更适合多任务批次，因为它可以同时表达：

- 一个批次下多个共享抽取
- 多个 job 的独立阶段产物
- 共享输入与独立输出之间的层次关系

## 10. 阶段执行模型

所有运行都必须先经过 `preflight`，然后再进入阶段引擎。

运行生命周期应固定为：

1. `RunBatchRequest`
2. `PreflightReport`
3. `RunBatchPlan`
4. `Execution`
5. `RunBatchManifest`

标准阶段顺序如下：

0. `preflight`
1. `extract`
2. `workbook_ingest`
3. `workbook_transform`
4. `publish`

规则如下：

- `preflight` 必须先执行，且不能被模板关闭。
- `extract` 是第一阶段里程碑，必须最先稳定。
- `workbook_ingest`、`workbook_transform`、`publish` 默认关闭，由 job 或运行时覆盖开启。
- `extract` 阶段按去重后的 `extract run` 执行。
- `workbook_ingest`、`workbook_transform`、`publish` 按 `job run` 执行。
- 阶段必须显式声明输入、输出和依赖，不允许共享隐式全局状态。
- v1 默认只允许一个活动 `run batch`，避免 workbook 和 publish 的副作用冲突。
- v1 的 `extract run` 默认串行执行，但在规划与代码结构上预留有限并发能力。

### 10.1 失败分层

失败必须区分层级，而不是全部归为一个 `failed`：

- `preflight_failed`
- `extract_failed`
- `job_stage_failed`
- `blocked`
- `skipped`

这样做的原因是：

- preflight 失败时还没有真正执行副作用。
- extract 失败时，其依赖 job 应标记为 `blocked` 或 `skipped`。
- workbook / publish 失败不一定要让所有无关 job 一起终止。

### 10.2 重跑策略

重跑不应覆盖旧批次，也不应“在旧 manifest 上继续写”。

当前更优路径是：

- 任何重跑都生成新的 `RunBatchRequest`。
- 旧批次 manifest 保持不可变。
- 支持以下重跑入口：
  - `rerun_full_batch`
  - `rerun_failed_jobs`
  - `rerun_failed_extracts_and_dependents`

默认策略应为 `fresh`，即重新执行 extract；后续再按显式选项支持从指定 source batch 复用成功 extract 产物。

### 10.3 运行前与阶段前护栏

基于历史失败日志，新系统的 `preflight` 不能只做“配置是否存在”的静态检查，还必须包含可执行的运行护栏。

至少需要覆盖：

- 全局 `doctor`：
  - 解释器版本
  - 单一权威依赖清单的一致性
  - 必需包是否已安装
  - 输出目录是否可写
  - 必需环境变量是否齐全
- extract 阶段：
  - 轮询预算配置是否合法
  - `connect_timeout` / `read_timeout` / `max_wait` / `max_retries` 是否显式给出
- workbook 阶段：
  - 仅在启用 workbook 阶段时检查本地 Excel 能力与模板文件
  - 写入前必须获取源数据的 `row_count`、`column_count`、`cell_count`
  - 超过阈值时必须切换 writer engine 或直接阻断，不允许无护栏地进入批量写入

这部分设计的原因是：

- 历史日志已经出现依赖缺失直接中断。
- 轮询链路已经出现 SSL EOF 和连接超时。
- workbook 链路已经出现超大范围写入导致的 `xlwings` / COM 失败。

### 10.4 全局运行契约 `runtime contract`

当前已确认：在继续细化 workbook 之前，必须先建立一层显式的 `runtime contract`。

它不是某一个 stage 的实现细节，而是一组跨层共享的运行规则，至少包含：

- `doctor contract`
- `runtime policy contract`
- `stage gate contract`
- `error taxonomy contract`
- `event + manifest contract`

其职责边界如下：

- `doctor`：检查系统是否具备启动和执行的最基本条件。
- `runtime policy`：定义 timeout、retry、polling、backoff 等预算。
- `stage gate`：在阶段真正执行前，判断当前上下文下该阶段是否允许进入。
- `error taxonomy`：为高频故障提供稳定错误类型。
- `event + manifest`：定义最小结构化运行记录字段。

这层契约必须优先服务 extract-only 里程碑，同时作为后续 workbook 与 publish 的统一前置，而不是等 workbook 阶段再单独补一套规则。

因此当前推荐顺序固定为：

1. `runtime contract`
2. `extract runtime policy`
3. `workbook detailed design`

### 10.4.1 Extract Runtime Policy

在 `runtime contract` 基线完成后，extract 阶段的运行政策继续细化为：

- `submit / poll / download` 三段分离预算
- extract 级 `total_deadline`
- `fast / standard / heavy` 三档 runtime profile
- `extract template` 默认档位 + `run batch` 运行时 override

当前默认档位为 `standard`，而不是 `fast`。原因是历史日志已经证明部分真实任务会出现接近 `100s` 的正常轮询等待，不能把所有任务都当成轻量查询。

同时明确：

- 正常 `PROCESSING` 轮询不消耗错误重试预算
- 只有瞬时网络错误才消耗有限重试
- extract manifest 必须记录实际生效 profile 以及 `submit / poll / download` 分段运行证据

### 10.4.2 Workbook Detailed Design

在 `extract runtime policy` 完成后，workbook 阶段正式收敛为“受约束块写入”模型，而不是通用 Excel 编辑器。

当前正式边界为：

- `1 job -> 1 template workbook -> 1 result workbook`
- 一个 job 可以消费多个 extract 文件
- 一个结果 workbook 可以包含多个普通 `sheet` block
- workbook 默认目标是更新底表数据区，保留模板结构，供计算表继续计算

当前采用的目标 block 模型至少包含：

- `block_id`
- `sheet_name`
- `source_extract_id`
- `start_row`
- `start_col`
- `write_mode`
- `clear_policy`
- 可选 `end_row / end_col`
- 可选 `append_locator_columns`
- 可选 `post_write_actions`

v1 固定支持的写入模式为：

- `replace_sheet`
- `replace_range`
- `append_rows`

默认语义为：

- 清值，不清结构

这意味着：

- 默认不清公式、格式、合并关系
- 所有智能识别只能发生在 block 显式边界内
- `append_rows` 的末行定位必须受源数据列域或 `append_locator_columns` 约束

第一版固定支持的写后动作为：

- `fill_down_formula`
- `fill_fixed_value`

其中：

- `fill_down_formula` 必须保持单元格仍为公式，而不是写死值
- 公式下拉必须遵守 Excel 相对/绝对引用语义
- 公式覆盖行数必须对齐本次真实写入的最终行段，覆盖不足时稳定失败

writer engine 的正式方向为：

- file-based writer 作为默认数据平面
- Excel / COM 只作为 calculation plane

因此 workbook 大表默认不允许直接压给 COM 做批量写入；写入前仍然必须记录 `row_count / column_count / cell_count`，由 stage gate 决定继续或阻断。

### 10.4.3 Publish Detailed Design

在 workbook stage 完成后，publish 阶段正式收敛为“受约束 workbook-to-Feishu 映射”模型，而不是结果 workbook 整本直传。

当前正式边界为：

- `1 job -> 1 result workbook -> 多个 publish mappings`
- 一个 mapping 只负责一个 source 与一个 target
- source 支持：
  - `sheet`
  - `block`
- target 支持：
  - `replace_sheet`
  - `replace_range`
  - `append_rows`
- publish 写入飞书的是值，不是公式
- 默认 `header_mode=exclude`
- 默认不自动创建飞书子表

当前采用的 publish mapping 模型至少包含：

- `mapping_id`
- `source`
- `target`

其中 source 至少声明：

- `sheet_name`
- `read_mode`
- `start_row`
- `start_col`
- 可选 `end_row / end_col`
- `header_mode`

其中 target 至少声明：

- `spreadsheet_token`
- `sheet_id` 或稳定 `sheet_name`
- `write_mode`
- `start_row`
- `start_col`
- 可选 `end_row / end_col`
- 可选 `append_locator_columns`

publish v1 的执行顺序固定为：

1. `resolve mappings + preflight`
2. `read workbook values -> publish dataset`
3. `write publish dataset -> feishu target`
4. `publish manifest`

其中：

- `publish dataset` 是 source 与 target 之间的标准化数据层
- mapping 是 publish 的最小执行与诊断单元
- chunk 写入默认串行执行
- 真实宽表一旦超过飞书单次写入列上限，必须继续按列或多个矩形范围切分；只按行分块不再视为足够

当前默认风险护栏为：

- `append_rows` 默认不是安全重跑操作
- 同一 batch / 同一 mapping / 同一目标的追加式重跑默认 `blocked`
- `empty_source_policy` 默认 `skip`
- 目标子表必须能被稳定解析，不允许模糊匹配后直接写入
- row/column-aware write planning、batch write path 与相关错误语义，下一次只允许作为可被主线 publish writer 实际消费的 `publish hardening` bundle 进入；不再单独回灌 live verification helper

## 11. 错误处理与可观测性

新系统必须把 legacy 日志里暴露出的真实失败模式显式工程化：

- 依赖管理必须有单一权威清单；运行前 `doctor` 必须阻断缺包、版本漂移和解释器不匹配，避免 `requirements` 与环境文件分叉后才在运行时触发 `ModuleNotFoundError`。
- 登录失败、认证失效、接口超时、SSL 异常要分类记录。
- 导出任务轮询必须有 `connect timeout`、`read timeout`、指数退避或分级退避、最大等待时长和最终失败态；manifest 中要记录 `task_id`、尝试次数、最后一次错误类型与最后一次响应上下文。
- Excel 读写必须区分：文件不存在、sheet 不存在、writer engine 不可用、COM 异常、数据形状异常、数据量超阈值。
- workbook 大批量数据传输不得默认依赖 Excel COM 直写；必须显式记录 writer engine、数据尺寸和触发的护栏策略。
- 飞书发布必须区分：鉴权失败、sheet 不存在、范围无效、源读取失败、限流重试耗尽、批量写入失败。
- 日志必须统一编码为 UTF-8，并在结构化字段中保留 `batch_id`、`job_id`、`extract_id`、`chart_id`、`task_id`，避免历史日志中的乱码和上下文丢失问题。
- 失败必须落到 manifest，而不是只打印到控制台。

## 12. 测试策略

必须采用分层验证，而不是只靠人工点点看：

1. 单元测试：
   - 配置模型
   - 动态筛选渲染
   - 返回结构归一化
   - 阶段依赖校验
   - extract signature 生成与去重
   - workbook block locator
   - workbook 公式下拉与固定值填充
   - publish mapping contract
   - publish source / target 范围识别
   - publish chunk 切分与 append 护栏
2. 集成测试：
   - 观远客户端请求构造
   - 页面快照解析
   - 运行归档写入
   - run planner 展开结果
   - workbook block 写入与结果 workbook 归档
   - publish dataset 生成与 mapping 级 manifest
3. 手工验收：
   - 登录
   - 页面树刷新
   - 页面详情浏览
   - extract-only 执行
   - 多 job 同批次运行
   - 失败 preflight
4. 后续再补：
   - Excel 阶段大样本验证
   - 飞书阶段限流与重试验证

## 13. 当前里程碑定义

### Milestone A：Extract-Only

完成以下能力即视为第一生产里程碑：

- 页面树刷新
- 页面详情查看
- extract template 保存
- job template 保存
- 预检
- extract-only 批次执行
- 批次级归档落盘

### Milestone B：Workbook Processing

在 Milestone A 稳定后接入：

- workbook ingest
- workbook transform
- 受约束 block 写入
- 辅助列公式下拉与固定列补值
- 标准输出数据生成

### Milestone C：Publish

在 workbook 阶段稳定后接入：

- 飞书 Sheets 发布
- workbook source -> publish mapping contract
- value-only publish dataset
- 批次写入摘要
- mapping 级 publish manifest
- 失败重试与限流处理

## 14. 当前已知未决项

以下问题已知但尚未完全锁死，需要在后续会话持续收敛：

- `DS_ELEMENTS` 类型筛选器的候选值接口。
- Workbook 大表写入时 file-based 安全阈值与回退策略。
- 飞书写入 row/column chunk 默认值与 retry budget 的精确默认值。
- `append_rows` 的后续业务键去重增强策略。

## 15. 参考证据清单

当前设计基于以下证据整理，不代表要在这些代码上继续修改：

- `docs/plans/2026-03-19-guanbi-live-verification.md`
- `docs/plans/2026-03-19-legacy-script-audit.md`
- `docs/plans/2026-03-18-guanbi-feishu-pipeline-design.md`
- `记录/*`
- `logger/*`
- 根目录业务 Excel 文件与 sheet 元数据
- legacy `src/` 目录中的接口与处理样本
