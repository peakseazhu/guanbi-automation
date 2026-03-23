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

## ADR-2026-03-20-12：Extract Runtime Policy 采用分段预算与三档运行配置

- Status：Accepted
- Context：runtime contract 已完成最小实现，但旧日志继续证明 extract 运行时间分布差异很大。`logger/log_15202603_1005.txt` 出现最长 `99s` 轮询等待，`logger/log_12202603_0850.txt` 和 `logger/log_17202601_0818.txt` 也分别出现 `72s`、`71s`；同时 `logger/log_21202601_0818.txt`、`logger/log_21202601_1356.txt`、`logger/log_07202603_0850.txt` 还出现 `66 x 219336`、`70 x 215501` 等大表样本。若继续使用单一 extract polling 预算，要么误杀重任务，要么把轻任务全部放宽。
- Decision：extract runtime policy 采用 `submit / poll / download` 三段分离预算，并在外层增加 extract 总时限；同时引入 `fast / standard / heavy` 三档 runtime profile。profile 由 `extract template` 提供默认值，`run batch` 可做运行时 override，默认档位为 `standard`。
- Consequences：
  - bootstrap settings 必须从单一 `extract_polling` 升级为 profile-aware 结构。
  - manifest 必须记录模板默认 profile、实际生效 profile 与三段运行证据。
  - `PROCESSING` 等正常轮询状态不消耗错误重试预算；只有瞬时网络错误才进入有限重试。
  - 后续调参优先围绕 profile，而不是在各处散落修改 timeout 数字。

## ADR-2026-03-21-13：Workbook v1 采用受约束块写入与双平面执行

- Status：Accepted
- Context：用户确认 workbook 的真实目标是“把每日 extract 数据写回模板底表，保留结构，触发计算”，而当前目标区域大多数是普通 `sheet` 区块，不是 `Excel Table / Named Range`。同时 legacy 证据继续表明：锚点内范围识别是有效经验，但大表默认经由 `xlwings` / COM 批量写入已经在真实日志中失稳。
- Decision：workbook v1 采用 `受约束块写入` 模型。每个目标区块显式声明 `sheet_name + start_row/start_col + write_mode + clear_policy + post_write_actions`，支持 `replace_sheet / replace_range / append_rows` 三种写入模式；默认语义为“清值不清结构”。默认数据平面采用 file-based writer，Excel / COM 只承担 calculation plane，不作为默认大块数据写入平面。
- Consequences：
  - workbook v1 边界固定为 `1 job -> 1 template workbook -> 1 result workbook`。
  - 智能识别只允许发生在 block 显式边界内，不允许全表自由猜测。
- 写后派生动作第一版固定支持 `fill_down_formula` 与 `fill_fixed_value`。
- 公式下拉必须以最终真实写入行段为准，且覆盖不足时稳定失败。
- 尺寸护栏继续保留，超阈值默认阻断，不自动把大表切回 COM 批量直写。

## ADR-2026-03-21-14：Publish v1 采用受约束 workbook-to-Feishu 映射与 value-only 发布

- Status：Accepted
- Context：workbook stage 已完成后，用户明确 publish 的真实业务不是“把结果 workbook 整本上传”，而是将一个结果 workbook 中的多个计算表或结果区块，映射到飞书一个或多个 spreadsheet 下的多个子表。用户同时确认：publish 源侧需要同时支持整张计算表与固定区块，目标侧需要同时支持整表覆盖、指定范围覆盖和追加；飞书侧写入的是值，不是公式；大多数日报场景应保留飞书目标结构，只更新值。
- Decision：publish v1 采用“显式 `publish source + publish target` 契约，中间保留标准化 `publish dataset`”的模型。source 支持 `sheet / block` 两种读取方式，target 支持 `replace_sheet / replace_range / append_rows` 三种写入方式。默认 `header_mode=exclude`，默认只写值不写公式，默认不自动创建飞书子表。publish 的最小执行与诊断单元是 `mapping`，而不是整个 job。
- Consequences：
  - publish 需要新增独立的 contract、source reader、target resolver、chunk writer 与 mapping 级 manifest。
  - publish 不会回头要求 workbook 先产出 publish-specific outputs，而是在 publish 阶段自行从结果 workbook 读取值并标准化。
  - `append_rows` 默认不视为安全重跑操作；同一 batch / 同一 mapping / 同一目标的追加式重跑默认阻断。
  - 空数据默认采用 `empty_source_policy=skip`，不默认把空结果解释成“清空飞书目标”。

## ADR-2026-03-22-15：采用“稳定主线 + 验证推进线”双轨治理

- Status：Accepted
- Context：`publish-stage-task1` worktree 已经同时包含 `publish foundation` 的正式实现和 `publish live verification` 的真实落地验证层。如果整条验证线直接并回主线，会把尚未完成真实样本证据收口的探索内容一起带入 `main`；如果完全不萃取，又会让主线长期落后于已经稳定的阶段实现。
- Decision：采用“稳定主线 + 验证推进线”双轨治理。`main` 只接收已通过 fresh automated verification、且不依赖未完成真实资源试跑的阶段 foundation；worktree / feature branch 继续承担 live verification、真实资源边界摸底和证据归档。验证线成果只有在真实证据与边界收敛后，才允许再次萃取进主线。
- Consequences：
  - 阶段实现从此区分为 `foundation` 和 `live verification` 两层，而不是把所有内容混为一个“完成/未完成”状态。
  - 当前 `publish foundation` 已萃取进 `main`，而 `publish live verification` 继续留在 `publish-stage-task1`。
  - 后续其它阶段也默认优先把稳定 foundation 进入主线，再由验证线继续向真实资源推进。

## ADR-2026-03-22-16：中断恢复优先从权威文档和最新状态对账入口进入

- Status：Accepted
- Context：仓库已经历多轮中断与恢复，且 `main` 与验证线分别承担不同职责。部分 `session archive` 记录的是当时现场状态，例如 dirty worktree、待补提交、当时下一步等；如果后续恢复直接从这些历史归档起步，容易把历史现场误读成当前现状。
- Decision：中断恢复时固定采用“权威文档 -> 最新状态对账文档 -> 历史归档”的阅读顺序。历史归档保持不可变，不回写修正；当当前事实发生变化时，通过更新 `master`、`decision-log` 和新增状态对账文档来表达最新现状。
- Consequences：
  - 后续恢复入口不再依赖单个旧 `session archive`。
  - 主线与验证线的当前状态都会优先写入权威文档和最新对账文档。
  - 历史归档继续保留完整演化轨迹，满足回滚和回溯需要。

## ADR-2026-03-22-17：验证线状态必须区分代码到位、运行足迹与有效证据归档

- Status：Accepted
- Context：`publish live verification` 当前已经具备 spec、readback support、service、entrypoint 与本地 real-sample spec，且 `runs/live_verification/publish/20260322T054012Z` 已出现时间戳目录。但该目录仍为空，也没有最终 `implementation archive`。如果后续文档把这种状态写成“尚未开始”，会低估已完成工作；如果写成“已完成验证”，又会把空目录误判成有效证据归档。
- Decision：从 2026-03-22 起，所有验证线状态说明都必须显式区分三层事实：
  1. 代码/本地 spec 是否已经到位
  2. 是否已经出现运行足迹
  3. 是否已经形成可复查的 evidence archive 与最终 session archive
  空目录或缺关键 JSON 文件的时间戳目录，只能算运行足迹，不能算验证闭环完成。
- Consequences：
- 后续主线文档不再使用“没有任何运行痕迹”来描述这类状态。
- 验证线是否可晋升到 `main`，必须同时看真实写入/读回/comparison 结果和归档是否完整。
- 状态对账文档需要同时记录“已经实现到哪里”和“证据收口到哪里”。

## ADR-2026-03-23-18：首个有效 publish live verification 证据形成后，只将通用 source-reader 修复回灌主线

- Status：Accepted
- Context：`publish-stage-task1` 已形成首个有效 evidence archive：`.worktrees/publish-stage-task1/runs/live_verification/publish/20260323T022511Z`，其中 `comparison.json` 已确认 `matches = true`。真实样本验证同时暴露出一个 foundation 级问题：`publish_source_reader` 在约 `215MB` workbook 上仍执行全量 `load_workbook(..., data_only=True)`，会导致 publish source 读取阶段卡死。此问题已在验证线通过回归测试、focused verification、full suite 和真实样本运行得到证实。
- Decision：只将与真实资源无关、已被证据证明的通用修复回灌 `main`，即：
  - `publish_source_reader` 改为 `read_only=True`
  - 行读取改为 `iter_rows(values_only=True)`
  - 对应回归测试进入主线
  而本地 `real_sample.local.yaml`、real-sample entrypoint、真实目标标识与 evidence archive 继续留在验证线。
- Consequences：
  - `main` 获得了被真实证据证明必要的 foundation 级稳定性修复。
  - 主线不会因为一次成功的真实样本验证，就把所有 live verification 脚手架一起并入。
  - 后续若要继续从验证线提升内容，仍必须先形成真实证据，再区分“通用正式能力”和“一次性验证资产”。
