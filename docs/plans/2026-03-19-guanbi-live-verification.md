# 观远 BI 实测复现记录

> 状态：Draft
> 更新时间：2026-03-19
> 关联主文档：`docs/plans/2026-03-19-guanbi-automation-suite-design.md`

## 目标

验证以下问题是否在当前线上环境中真实可行：

1. 是否能直接通过 `.env` 中的账号密码登录观远
2. 是否能拉到全部可访问页面
3. 是否能获取页面详情、图表与筛选器定义
4. 是否能发起真实导出并拿到 `.xlsx`
5. 是否能通过浏览器真实进入观远首页

## 本次测试环境

- 工作目录：`D:\get_bi_data__1`
- 当前日期：`2026-03-19`
- 本地 Python 解释器：
  - `D:\miniconda3\envs\feishu-broadcast\python.exe`
- 凭据来源：
  - 当前目录 `.env`
- 浏览器验证方式：
  - Chrome DevTools
  - 先通过接口获取 `uIdToken`
  - 再把 `uIdToken` 注入浏览器 cookie
  - 再访问 `https://bi.biaoguoworks.com/home`

说明：

- 本文档不记录账号明文
- 不记录完整 token
- 只记录可复现方法、接口、结论与边界

## 测试方法

### 方法 1：直接调用观远接口

使用 `requests` 结合 `.env` 中的：

- `BI_USERNAME`
- `BI_PASSWORD`

先登录，再调用页面树、页面详情和导出接口。

### 方法 2：浏览器注入登录态

先通过接口拿到 `uIdToken`，再写入浏览器 cookie，访问首页，验证页面能否真正打开。

## 已测试接口与结论

| 接口 | 方法 | 用途 | 结果 |
| --- | --- | --- | --- |
| `/api/user/sign-in` | `POST` | 账号密码登录 | 成功，返回 `uIdToken` |
| `/api/page-v3` | `GET` | 获取全量页面树 | 成功 |
| `/api/favorite/list` | `GET` | 获取收藏页面 | 成功 |
| `/api/bookmarks/{pgId}/list` | `GET` | 获取页面书签 | 成功 |
| `/api/page/{pgId}` | `GET` | 获取页面详情 | 成功 |
| `/api/write/file/{chartId}?typeOp=EXCEL` | `POST` | 发起 Excel 导出 | 成功 |
| `/api/task/{taskId}` | `GET` | 查询导出任务状态 | 成功 |
| `/api/export/file/excel/{fileName}` | `POST` | 下载 Excel 导出文件 | 成功 |
| `/api/export/file/common/{taskId}` | `POST` | 下载通用导出文件 | 成功 |
| `/api/portal/info?isRelease=true` | `GET` | 获取门户页面列表 | 成功 |

## 页面树验证结果

`GET /api/page-v3` 实测结果：

- 当前账号可访问页面总数：`312`
- 其中 `PAGE`：`299`
- 其中 `CUSTOM_REPORT`：`13`

这说明：

- 当前账号并不是只能访问少数固定看板
- 后续本地工具可以基于账号真实能力生成页面树
- 普通页面和自定义查询页面都需要纳入统一发现逻辑

## 页面详情验证结果

测试页面：

- `ob483e8c95e0d496c9e6f7f3`
- 页面名：`执行管理日复盘`

`GET /api/page/{pgId}` 返回中已拿到：

- 页面基础信息
- `meta.layout`
- `meta.filterLayout`
- `meta.tabMap`
- `cards`
- `dsInfos`

对该页面的实测摘要：

- `cards` 数量：`36`
- `dsInfos` 数量：`8`
- 页面中既有 `SELECTOR` 也有 `CHART`
- `filterLayout` 直接给出筛选器在页面中的排列顺序
- `tabMap` 给出 tab、panel、chart 的组织关系

这说明：

- 本地工具不需要靠猜测页面结构来生成界面
- 页面内的图表和筛选器关系已经可以从服务端元数据直接还原

## 筛选器验证结果

在 `执行管理日复盘` 页中，实测拿到了以下典型筛选器：

- `日期`
  - `cdType=SELECTOR`
  - `selectorType=TIME_MACRO`
  - 内含 `昨天`、`最近7天`、`最近30天`、`本周到昨天` 等预设
  - `settings.asFilter.targetCdIds` 给出它影响的目标图表
  - `columnMappings` 给出源字段到各图表目标字段的映射关系

- `商城名称`
  - `cdType=SELECTOR`
  - `selectorType=DS_ELEMENTS`
  - 带 `dsId` 和 `fdId`
  - 说明后续有机会进一步定位候选值查询接口

这说明：

- “像观远一样知道每个看板有哪些筛选条件”是可做的
- 日期型筛选器已经具备很强的模板化能力
- 枚举型筛选器当前已经能被识别和建模，只差在线候选值接口完全锁定

## 图表与导出验证结果

测试图表：

- `r29b8748abc9a44e88365b63`
- 图表名：`执行管理日复盘-中心仓`

在页面详情中，该图表具备：

- `cdType=CHART`
- `displayType=MAXCOMPUTE`
- `content.chartType=PIVOT_TABLE`
- `settings.exportConfig.exportConditions.exportType=exportExcel`

这说明：

- 页面详情足够让系统识别“哪些卡片可导出”
- 后续模板编辑界面可以只展示真正可导出的图表

## 导出链路验证结果

本次实测完整打通了以下导出链路：

1. `POST /api/write/file/{chartId}?typeOp=EXCEL`
2. `GET /api/task/{taskId}`
3. `POST /api/export/file/excel/{fileName}`

以及另一条导出下载链路：

1. `POST /api/write/file/{chartId}?typeOp=EXCEL`
2. `GET /api/task/{taskId}`
3. `POST /api/export/file/common/{taskId}`

结果：

- 两条下载链路都返回 `200`
- `Content-Type=application/octet-stream`
- 返回二进制文件头为 ZIP / XLSX 格式特征

这说明：

- 当前线上环境中，旧脚本依赖的导出核心链路仍然成立
- 新工具可以继续复用这条服务端导出模式

## 浏览器验证结果

通过接口登录获取 `uIdToken` 后，将其注入浏览器 cookie，再访问：

- `https://bi.biaoguoworks.com/home`

实测结果：

- 首页成功进入
- 标题显示为“标果BI系统”
- 后续网络请求中能看到门户信息接口返回页面列表

并进一步验证到：

- `/api/portal/info?isRelease=true` 返回门户中的可访问页面
- 其中能看到 `执行管理日复盘`、`新版薪酬运营-BD&门店`、`绩效运营`、`【非实时】每日每店每SKU查询` 等页面

这说明：

- 当前登录机制不仅能走接口，也能落到真实前端页面
- 后续如需辅助抓取前端行为，浏览器注入登录态是可复现方法

## 返回结构差异注意点

历史记录与当前实测相比，存在一个需要兼容的小差异：

- 部分历史 JSON 是 `{ "result": "ok", "response": ... }`
- 当前线上某些接口实测会直接返回列表或对象本体

因此解析器必须统一兼容：

- `obj["response"]`
- `obj`

两种返回包装，避免上线后因为结构差异报错。

## 当前已确认能力边界

已确认：

- 账号密码登录可用
- 页面树发现可用
- 页面详情发现可用
- 普通页面和 `CUSTOM_REPORT` 都可统一读取
- 图表和筛选器关系可被建模
- Excel 导出可用
- 浏览器登录态验证可用

未完全确认：

- `DS_ELEMENTS` 类型筛选器的在线候选值接口名称

但已确认页面详情里能拿到：

- `selectorType`
- `dsId`
- `fdId`

所以这块并非无解，只是还没有在本轮里完全锁定最终 endpoint。

## 复现步骤

1. 确保 `.env` 中存在：
   - `BI_USERNAME`
   - `BI_PASSWORD`
2. 使用：
   - `D:\miniconda3\envs\feishu-broadcast\python.exe`
3. 先调用：
   - `POST https://bi.biaoguoworks.com/api/user/sign-in`
4. 从返回中提取 `uIdToken`
5. 带上：
   - `Cookie: uIdToken=<token>`
   - `token: <token>`
6. 调用：
   - `GET /api/page-v3`
   - `GET /api/page/{pgId}`
7. 选一个可导出的 `chartId` 调用：
   - `POST /api/write/file/{chartId}?typeOp=EXCEL`
8. 轮询：
   - `GET /api/task/{taskId}`
9. 下载：
   - `POST /api/export/file/excel/{fileName}`
10. 如需浏览器验证：
    - 将 `uIdToken` 注入 cookie
    - 访问 `https://bi.biaoguoworks.com/home`

## 当前结论

从当前线上观远实际状态看，项目目标不是“理论上可能”，而是“工程化改造后可以落地”。

真正的工作重点不再是“能不能连上观远”，而是：

- 如何把页面、图表、筛选器建成稳定模型
- 如何把执行链路拆成可开关、可插入、可复用的阶段
- 如何替换旧脚本中的硬编码与副作用耦合
