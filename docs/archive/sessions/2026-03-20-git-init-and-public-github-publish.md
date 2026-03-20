# 2026-03-20 Git 初始化与公开 GitHub 仓库发布归档

## 1. 本次目标

将 `D:\get_bi_data__1` 初始化为 Git 仓库，连接 GitHub，创建公开仓库，并把当前从 0 构建的新项目代码与权威规划文档推送到远端。

## 2. 本次执行内容

本次已完成：

- 初始化本地 Git 仓库，默认分支为 `main`
- 配置本仓库为 `safe.directory`
- 补充 `.gitignore`，排除以下不应进入公开仓库的内容：
  - `.env`
  - `.venv/`
  - `.packages/`
  - `.vscode/`
  - `logger/`
  - `记录/`
  - legacy `src/`
  - 根目录 `.xlsx` 文件
- 安装 GitHub CLI
- 通过已登录的浏览器会话创建公开仓库：
  - `https://github.com/peakseazhu/guanbi-automation`
- 设置本地 `origin`
- 推送本地 `main` 到远端

## 3. 公开仓库排除策略

由于仓库目标为公开，以下内容被明确排除，不进入远端：

- 本地环境与凭据
- 业务 Excel 参考文件
- legacy 参考代码
- logger / 记录 证据库

这与主设计文档中“这些目录仅作为本地参考证据库”的边界保持一致。

## 4. 过程中发现的环境问题

推送过程中的真实阻塞并不是 GitHub 仓库本身，而是本机环境里存在以下问题：

### 4.1 Git 全局代理配置

全局 Git 配置存在以下代理：

- `http.proxy = http://127.0.0.1:10808`
- `https.proxy = http://127.0.0.1:10808`

本次已在仓库本地覆盖为空值，避免直接改用户全局配置。

### 4.2 系统 hosts 文件拦截 GitHub

`C:\Windows\System32\drivers\etc\hosts` 中存在活动映射，将多个 GitHub 域名指向 `127.0.0.1`，包括：

- `github.com`
- `api.github.com`
- `gist.github.com`
- `raw.github.com`
- 多个 `githubusercontent.com` 子域

这会导致 Git 在 HTTPS 推送时把 GitHub 解析到本机，从而无法连接。

本次处理方式：

- 先生成本地备份：
  - `docs/archive/sessions/2026-03-20-hosts-backup-before-github-unblock.txt`
- 再通过管理员 PowerShell 子进程执行一次性脚本：
  - `tools/fix_github_hosts.ps1`
- 仅注释掉 GitHub 相关的活动 `127.0.0.1` 映射
- 刷新 DNS 缓存

补充：

- hosts 备份文本和一次性修复脚本只保留在本地，不推送到公开仓库
- 对应忽略规则已写入 `.gitignore`

## 5. 验证结果

关键验证结果如下：

- 本地提交：
  - `2455a9f`
- 远端 `main`：
  - `2455a9f8a8f6d66810da37753842325aca38b2e1`
- 当前远端：
  - `origin https://github.com/peakseazhu/guanbi-automation.git`

说明：

- 当前远端 `main` 已与本地初始化提交对齐
- 仓库创建与首次推送已完成

## 6. 对主规划文档的影响

本次不涉及架构取舍变化，因此未更新：

- `docs/plans/master-system-design.md`
- `docs/plans/master-implementation-roadmap.md`
- `docs/archive/decision-log.md`

原因：

- 本次仅完成仓库治理与公开远端发布
- 未改变 runtime contract / extract runtime policy / workbook detailed design 的既定顺序

## 7. 下一步恢复点

Git 与 GitHub 仓库已经就绪。后续可直接继续：

1. 基于当前远端仓库继续推进 `extract runtime policy`
2. 保持三层文档治理同步
3. 继续避免回到 legacy `src/` 改造路径
