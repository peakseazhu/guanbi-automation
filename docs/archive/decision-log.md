# 决策日志

## ADR-2026-03-19-01：采用三层规划与归档结构

- Status：Accepted
- Context：项目后续会持续迭代，且用户明确要求每次对话都要归档，防止中断后工程不连贯或细节遗漏。
- Decision：采用“主规划文档 + 每次对话单独归档 + 决策日志”的三层结构。
- Consequences：
  - `master` 文档成为当前唯一权威版本。
  - `sessions` 保存每次讨论的完整上下文。
  - `decision-log` 保存关键取舍及理由，避免未来只看到结论看不到原因。

## ADR-2026-03-19-02：新项目实现代码从 0 构建

- Status：Accepted
- Context：当前目录中的 legacy 脚本已经证明业务链路存在，但实现高度写死、耦合重、错误边界差，不适合作为新系统的直接基底。
- Decision：新项目的实现代码从 0 构建；legacy 代码、日志、抓包、Excel 文件仅作为参考证据与需求样本，不作为迁移基线。
- Consequences：
  - 后续实现不得以“继续改旧脚本”作为默认路径。
  - 允许继承的是知识与样本，不是结构与耦合关系。
  - 规划文档、实施计划和目录结构都必须围绕全新代码骨架编排。

## ADR-2026-03-19-03：新代码与 legacy `src/` 物理隔离

- Status：Accepted
- Context：当前工作目录已经存在 legacy `src/`，如果继续沿用该路径，新代码与旧代码会天然混杂，难以执行“从 0 构建”的边界。
- Decision：新项目使用独立代码根 `guanbi_automation/`，不在 legacy `src/` 中继续添加实现代码。
- Consequences：
  - 新旧代码责任边界清晰。
  - 可以在不破坏当前参考资料的前提下启动新实现。
  - 实施阶段必须禁止新代码 `import` legacy `src` 模块。

## ADR-2026-03-19-04：采用 extract + job + run batch 三层执行模型

- Status：Accepted
- Context：用户明确存在多个配置文件任务，旧规划也已经确认“同一个 chart 可在不同筛选条件下重复导出”以及“多个任务在同一次运行中共享部分抽取结果”。
- Decision：采用 `extract template`、`job template`、`run batch` 三层模型。
- Consequences：
  - `extract` 成为最小可复用抽取单元。
  - `job` 成为完整业务任务配置文件。
  - 单次执行允许同时选择多个 jobs。
  - 共享去重在 `run batch` 内进行，而不是跨天默认缓存。

## ADR-2026-03-19-05：采用 Core-first, Web-ready 分层架构

- Status：Accepted
- Context：产品最终形态是本地 Web 工具，但如果先做 UI 再倒逼后端建模，模板模型、运行模型和副作用边界会持续返工。
- Decision：采用 `bootstrap / domain / application / execution / infrastructure / web` 的分层架构，先锁定核心骨架，再让 Web 接到稳定边界上。
- Consequences：
  - Web 不再承担业务核心逻辑。
  - 批次规划、阶段执行、文件归档和外部系统适配都有明确归属。
  - 文档、实施计划和后续代码目录必须统一采用这套分层命名。

## ADR-2026-03-19-06：重大规划变更必须有证据对比或最小测试支撑

- Status：Accepted
- Context：用户明确要求每次都要思考是否存在更优方法或路径，并且更优判断不能只靠主观感受。
- Decision：任何进入 `master` 的重大规划变更，至少要经过一次证据对比（抓包、日志、已有验证结果、历史样本）或一次最小 spike 测试。
- Consequences：
  - 规划演化必须可解释、可追溯。
  - 不能因为“看起来更优”就直接修改主架构。
  - 后续实现阶段需要为关键争议点保留小型验证实验。

## ADR-2026-03-19-07：采用混合式筛选器模型

- Status：Accepted
- Context：历史样本已覆盖 `BT + STRING`、`IN + STRING`、`IN + DATE`，验证文档还确认了 `TIME_MACRO` 与 `DS_ELEMENTS`。如果只做高度抽象模型，容易丢掉观远原始字段；如果只存原始 payload，则动态规则、UI 编辑和签名去重都不稳定。
- Decision：页面快照中保留 selector 原始元数据；extract template 中保存 `selector_ref + template_payload + dynamic_rule/literal_value + display_value_policy` 的混合模型。
- Consequences：
  - 可以同时兼顾保真、可编辑、可测试和可去重。
  - `DS_ELEMENTS` 在线候选值接口未完全锁定前，系统仍可先通过 literal 模式落地。
  - 签名计算可以基于语义化后的标准结构，而不是直接哈希原始 JSON。

## ADR-2026-03-19-08：运行前必须有环境 doctor 与单一依赖清单

- Status：Accepted
- Context：历史日志 `logger/log_06202602_0951.txt:10` 出现 `ModuleNotFoundError: No module named 'dateutil'`，同时仓库中 `requirements.txt` 含 `python-dateutil`，但 `environment.yml` 未包含该依赖，说明旧链路存在依赖清单漂移和运行前无校验问题。
- Decision：新项目必须以单一权威依赖清单为准，并在运行前执行环境 `doctor`，显式检查解释器版本、关键依赖、环境变量和输出目录可用性。
- Consequences：
  - 依赖缺失将被前置阻断，而不是在中途运行失败。
  - `requirements` 与环境文件双写漂移的风险被消除。
  - Phase 1 必须优先建设依赖锁定与 `doctor` 能力。

## ADR-2026-03-19-09：导出任务轮询必须采用有预算的超时与重试策略

- Status：Accepted
- Context：历史日志 `logger/log_09202601_0818.txt:81` 出现 `requests.exceptions.SSLError`，`logger/log_13202602_0818.txt:74` 出现 `requests.exceptions.ConnectTimeout`；对应 legacy 代码 [guanbi_client.py](/abs/path/D:/get_bi_data__1/src/api/guanbi_client.py:39) 使用 `while 1` 轮询，未显式设置连接/读取超时和总等待预算。
- Decision：新项目的任务轮询必须显式配置 `connect_timeout`、`read_timeout`、`max_wait`、`max_retries` 和退避策略，并将最终失败态写入 manifest。
- Consequences：
  - 轮询异常将被分类处理，而不是被无限等待或模糊吞没。
  - 执行批次可准确区分网络瞬时故障、持续不可达和业务任务超时。
  - Phase 4 必须把轮询预算模型纳入核心交付物。

## ADR-2026-03-19-10：Workbook 大批量写入采用显式 writer engine 与尺寸护栏

- Status：Accepted
- Context：历史日志 `logger/log_01202602_0818.txt:23` 和 `logger/log_01202603_0850.txt:23` 显示 `paste_range.value = data` 触发 `ValueError: The truth value of an array with more than one element is ambiguous`；`logger/log_07202603_0850.txt:148`、`logger/log_10202601_0818.txt:148` 还显示 `门店详情_日维度` 存在 `70 x 215501`、`66 x 218155` 的真实大表，并最终在 [xlwings_utils.py](/abs/path/D:/get_bi_data__1/src/utils/xlwings_utils.py:478) 附近触发 `pywintypes.com_error`。
- Decision：新项目的 workbook 阶段必须先抽象 `writer engine`，写入前强制记录 `row_count`、`column_count`、`cell_count`，超过阈值时切换策略或阻断执行；禁止默认把大表批量写入直接压给 Excel COM。
- Consequences：
  - Workbook 阶段不再把 Excel COM 当作默认数据平面。
  - 大表处理会成为显式建模和预检的一部分，而不是运行时偶发崩溃。
  - Phase 6 需要优先解决 writer engine、尺寸阈值和回退策略。

## ADR-2026-03-19-11：先建立 runtime contract，再细化 workbook 设计

- Status：Accepted
- Context：用户要求以更严格、更正确的项目开发顺序推进；现有日志已证明问题不仅在 workbook 本身，还涉及环境依赖、任务轮询、错误分类和运行归档。若先细化 workbook，后续仍会因全局运行语义未锁死而返工。
- Decision：当前顺序固定为 `runtime contract -> extract runtime policy -> workbook detailed design`。先定义 doctor、timeout/retry、stage gate、error taxonomy、event/manifest 最小字段，再继续 workbook 细化。
- Consequences：
  - extract-only 里程碑在真正实现前，必须先有最小稳定运行契约。
  - workbook 设计以后不再独立定义自己的错误语义和日志字段。
  - 当前规划与后续实施计划都要把 runtime contract 作为 workbook 之前的正式前置阶段。
