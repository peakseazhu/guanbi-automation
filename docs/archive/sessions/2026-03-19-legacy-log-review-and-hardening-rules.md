# 2026-03-19 历史日志审查与硬化规则归档

## 1. 本次会话触发点

用户要求回看曾经运行脚本的日志，提炼可以借鉴的经验，以及在新项目中必须规避的错误与 bug 模式。

## 2. 本次审查范围

本次主要对以下证据做了交叉核对：

- `logger/log_01202602_0818.txt`
- `logger/log_01202603_0850.txt`
- `logger/log_06202602_0951.txt`
- `logger/log_07202603_0850.txt`
- `logger/log_08202603_0850.txt`
- `logger/log_09202601_0818.txt`
- `logger/log_10202601_0818.txt`
- `logger/log_10202601_0936.txt`
- `logger/log_13202602_0818.txt`
- `logger/log_13202603_0845.txt`
- legacy 调用链：
  - `src/main.py`
  - `src/api/guanbi_client.py`
  - `src/utils/xlwings_utils.py`
- 依赖清单：
  - `requirements.txt`
  - `environment.yml`

## 3. 本次稳定结论

本次确认的失败模式不是零散 bug，而是以下四类系统性问题：

1. 环境可复现性不足
2. 导出任务轮询缺少超时预算与错误分类
3. Workbook 大表写入缺少尺寸护栏与 writer engine 抽象
4. 日志编码与上下文记录不足

## 4. 关键证据

### 4.1 依赖漂移

- `logger/log_06202602_0951.txt:10`
  - `ModuleNotFoundError: No module named 'dateutil'`
- `requirements.txt`
  - 包含 `python-dateutil`
- `environment.yml`
  - 未包含 `python-dateutil`

结论：

- 旧脚本并没有稳定的单一依赖清单。
- 缺少运行前 `doctor` 检查，导致问题在执行时才暴露。

### 4.2 网络轮询失稳

- `logger/log_09202601_0818.txt:81`
  - `requests.exceptions.SSLError`
- `logger/log_13202602_0818.txt:74`
  - `requests.exceptions.ConnectTimeout`
- [guanbi_client.py](/abs/path/D:/get_bi_data__1/src/api/guanbi_client.py:39)
  - 使用 `while 1` 无限轮询
- [guanbi_client.py](/abs/path/D:/get_bi_data__1/src/api/guanbi_client.py:41)
  - `requests.get(...)` 未显式设置超时预算

结论：

- 旧链路默认假设外部接口总会在有限时间内恢复。
- 一旦遇到 SSL EOF、连接超时或持续处理中，执行链路没有清晰的停止边界。

### 4.3 Workbook 写入链路失稳

- `logger/log_01202602_0818.txt:23`
- `logger/log_01202603_0850.txt:23`
  - `ValueError: The truth value of an array with more than one element is ambiguous`
- [xlwings_utils.py](/abs/path/D:/get_bi_data__1/src/utils/xlwings_utils.py:481)
  - `paste_range.value = data`
- `logger/log_10202601_0818.txt:148`
  - `1 1 70 215501`
- `logger/log_07202603_0850.txt:148`
  - `1 1 66 218155`
- [xlwings_utils.py](/abs/path/D:/get_bi_data__1/src/utils/xlwings_utils.py:478)
  - 先构造超大 `range(...)`

结论：

- 旧脚本把 workbook 写入当作“拿到二维列表就整块贴进去”。
- 这在小表上可以工作，但在真实大表上已经被历史日志证伪。
- 新系统必须在 workbook 阶段前置尺寸判断、写入模式选择和失败分层。

### 4.4 日志可读性不足

- `logger/log_07202603_0850.txt`
- `logger/log_10202601_0818.txt`
  - 多处中文出现乱码

结论：

- 历史日志在编码和字段结构上都不稳定。
- 新项目必须强制 UTF-8，并记录稳定上下文字段。

## 5. 本次进入主文档的规则

本次将以下内容升级为主设计规则：

1. 运行前必须有环境 `doctor`
2. 依赖管理必须有单一权威清单
3. 导出任务轮询必须有超时预算、重试边界和失败分类
4. Workbook 大批量写入必须有 `writer engine + size guardrail`
5. 日志必须统一 UTF-8 并保留结构化上下文

## 6. 本次新增决策日志

新增以下 ADR：

- `ADR-2026-03-19-08`：运行前必须有环境 doctor 与单一依赖清单
- `ADR-2026-03-19-09`：导出任务轮询必须采用有预算的超时与重试策略
- `ADR-2026-03-19-10`：Workbook 大批量写入采用显式 writer engine 与尺寸护栏

## 7. 本次会话输出文件

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`
- `docs/archive/sessions/2026-03-19-legacy-log-review-and-hardening-rules.md`
