# Atlassian Crawler 设计文档

## 项目概述

构建一个 Python CLI 工具，从多个 Atlassian 实例（Jira + Confluence）爬取数据到本地 markdown 文件，作为 [llm-wiki-compiler](https://github.com/atomicmemory/llm-wiki-compiler) 的输入源。

**核心原则：** 最少代码，最多功能，优先使用现有轮子。

---

## 需求总结

### 功能需求

- **数据范围：** Jira 和 Confluence 分开存储
  - **Confluence:** 页面正文 + 附件（图片、文件）
  - **Jira:** issue 基本信息 + 评论 + 附件 + **所有字段**（标准字段 + 自定义字段）
- **多数据源支持：** 支持配置多个 Jira/Confluence 实例
- **过滤范围：** 每个数据源可配置特定 space(s) 和 project(s)
- **更新策略：** 增量更新（只爬取新增或修改的内容）
- **输出格式：** 
  - 简单 markdown（不需要复杂 frontmatter）
  - 基本元数据：标题、作者、日期、原始链接
  - 附件本地存储，相对路径引用
- **运行模式：** 支持多种运行模式（一次性、CLI、定时任务等）

### 非功能需求

- **错误处理：** 跳过失败项并记录，生成错误报告
- **使用频率：** 频繁使用（每天或更频繁）
- **性能：** 暂不考虑并发爬取
- **部署：** 本地 Python 脚本运行

---

## 技术栈

| 组件 | 选择 | 理由 |
|------|------|------|
| API 客户端 | `atlassian-python-api` | 成熟、文档完善、支持 Confluence + Jira |
| HTML → Markdown | `markdownify` | 轻量、可定制、处理 Confluence 的 HTML 存储格式 |
| CLI 框架 | `click` | 简单、流行、支持子命令和参数验证 |
| 配置管理 | `PyYAML` | 标准、易读、支持注释 |
| 增量更新 | 本地 JSON 状态文件 | 简单、无需数据库、易于调试 |

---

## 项目结构

```
atlassian-crawler/
├── config.yaml                 # 配置文件
├── .atlassian-sync-state.json  # 状态文件（自动生成）
├── sync-errors.log             # 错误日志（自动生成）
├── requirements.txt            # Python 依赖
├── README.md                   # 使用文档
├── cli.py                      # CLI 入口
└── crawler/
    ├── __init__.py
    ├── confluence.py           # Confluence 爬取
    ├── jira.py                 # Jira 爬取
    ├── storage.py              # 文件存储
    ├── converter.py            # HTML → Markdown 转换
    └── error_handler.py        # 错误处理
```

---

## 配置文件设计

### config.yaml

```yaml
# 多数据源配置
sources:
  # Confluence 数据源列表
  confluence:
    - name: "company-main"
      url: "https://company.atlassian.net"
      username: "user@company.com"
      api_token: "${CONFLUENCE_COMPANY_TOKEN}"
      spaces:
        - key: "ENG"
          name: "Engineering"
        - key: "PROD"
          name: "Product"
    
    - name: "company-internal"
      url: "https://internal.atlassian.net"
      username: "user@company.com"
      api_token: "${CONFLUENCE_INTERNAL_TOKEN}"
      spaces:
        - key: "HR"
          name: "Human Resources"
  
  # Jira 数据源列表
  jira:
    - name: "company-main"
      url: "https://company.atlassian.net"
      username: "user@company.com"
      api_token: "${JIRA_COMPANY_TOKEN}"
      projects:
        - key: "PROJ"
          name: "Project Alpha"
        - key: "INFRA"
          name: "Infrastructure"
    
    - name: "client-jira"
      url: "https://client.atlassian.net"
      username: "user@client.com"
      api_token: "${JIRA_CLIENT_TOKEN}"
      projects:
        - key: "CLIENT"
          name: "Client Project"

# 输出配置
output:
  base_dir: "./sources"
  
# 增量更新配置
sync:
  state_file: "./.atlassian-sync-state.json"
  
# 错误处理配置
error_handling:
  max_retries: 3
  retry_delay: 5
  error_log: "./sync-errors.log"
```

### 状态文件 (.atlassian-sync-state.json)

```json
{
  "last_sync": "2026-05-06T10:00:00Z",
  "confluence": {
    "company-main": {
      "ENG": {
        "pages": {
          "123456": {
            "title": "Architecture Overview",
            "last_updated": "2026-05-05T15:30:00Z",
            "version": 5
          }
        }
      }
    }
  },
  "jira": {
    "company-main": {
      "PROJ": {
        "issues": {
          "PROJ-123": {
            "summary": "Fix login bug",
            "last_updated": "2026-05-06T09:00:00Z"
          }
        }
      }
    }
  }
}
```

---

## 文件组织结构

```
sources/
├── confluence/
│   ├── company-main/           # 数据源名称
│   │   ├── ENG/                # Space key
│   │   │   ├── Architecture-Overview.md
│   │   │   ├── API-Documentation.md
│   │   │   └── attachments/
│   │   │       ├── diagram1.png
│   │   │       └── spec.pdf
│   │   └── PROD/
│   │       └── ...
│   └── company-internal/       # 另一个数据源
│       └── HR/
│           └── ...
└── jira/
    ├── company-main/           # 数据源名称
    │   ├── PROJ/               # Project key
    │   │   ├── Bug/            # Issue type
    │   │   │   ├── PROJ-123.md
    │   │   │   ├── PROJ-125.md
    │   │   │   └── attachments/
    │   │   ├── Story/          # Issue type
    │   │   │   ├── PROJ-100.md
    │   │   │   └── attachments/
    │   │   ├── Task/           # Issue type
    │   │   │   └── PROJ-200.md
    │   │   └── Epic/           # Issue type
    │   │       └── PROJ-50.md
    │   └── INFRA/
    │       └── ...
    └── client-jira/            # 另一个数据源
        └── CLIENT/
            └── ...
```

---

## Markdown 输出格式

### Confluence 页面

```markdown
# Architecture Overview

> 来源: https://company.atlassian.net/wiki/spaces/ENG/pages/123456
> 作者: John Doe
> 创建时间: 2026-01-15T10:00:00Z
> 更新时间: 2026-05-05T15:30:00Z
> Space: Engineering (ENG)
> 数据源: company-main

[页面正文内容...]

![diagram](./attachments/architecture-diagram.png)
```

### Jira Issue

```markdown
# [PROJ-123] Fix login bug

> 来源: https://company.atlassian.net/browse/PROJ-123
> Project: Project Alpha (PROJ)
> 数据源: company-main
> 创建时间: 2026-04-20T09:00:00Z
> 更新时间: 2026-05-06T09:00:00Z

## 基本信息

- **类型**: Bug
- **状态**: In Progress
- **优先级**: High
- **报告人**: Jane Smith
- **经办人**: John Doe
- **标签**: authentication, security, critical
- **组件**: Frontend, Auth Service
- **影响版本**: 2.1.0
- **修复版本**: 2.1.1
- **Sprint**: Sprint 15
- **Story Points**: 5

## 自定义字段

- **客户影响**: High
- **根本原因**: Configuration error
- **发现阶段**: Production
- **[所有其他自定义字段...]**

## 描述

[Issue 描述内容...]

## 评论

### Jane Smith - 2026-04-21T10:30:00Z
[评论内容...]

### John Doe - 2026-04-22T14:00:00Z
[评论内容...]

## 关联 Issues

- Blocks: PROJ-124
- Related to: PROJ-100, PROJ-101

## 附件

- [screenshot.png](./attachments/screenshot.png)
- [logs.txt](./attachments/logs.txt)

## 工作日志

- 2h - John Doe - 2026-04-22 - Investigation
- 3h - John Doe - 2026-04-23 - Implementation

## 原始数据（JSON）

<details>
<summary>完整字段数据</summary>

```json
{
  "所有字段的完整 JSON..."
}
```

</details>
```

---

## CLI 命令设计

### 命令列表

```bash
# 初始化配置文件
python cli.py init

# 列出所有数据源
python cli.py list-sources

# 同步所有数据源
python cli.py sync

# 只同步所有 Confluence 数据源
python cli.py sync --type confluence

# 只同步所有 Jira 数据源
python cli.py sync --type jira

# 同步指定的数据源（自动识别类型）
python cli.py sync --source company-main

# 同步指定的 Confluence 数据源
python cli.py sync --source company-main --type confluence

# 查看同步状态
python cli.py status

# 使用自定义配置文件
python cli.py sync --config my-config.yaml
```

---

## 核心流程

```
用户执行 `python cli.py sync`
    ↓
加载 config.yaml
    ↓
根据 --source 和 --type 参数过滤数据源
    ↓
初始化 StorageManager（加载状态文件）
    ↓
初始化 ErrorHandler
    ↓
遍历过滤后的 Confluence 数据源
    ↓
    对每个数据源:
        初始化 ConfluenceCrawler
        遍历配置的 spaces
            ↓
            对每个 space:
                获取所有页面 → 检查版本 → 下载新/更新的页面
                → 转换 HTML → Markdown → 下载附件 → 保存文件
                → 更新状态
    ↓
遍历过滤后的 Jira 数据源
    ↓
    对每个数据源:
        初始化 JiraCrawler
        遍历配置的 projects
            ↓
            对每个 project:
                获取所有 issues → 检查更新时间 → 下载新/更新的 issues
                → 构建 Markdown（包含所有字段）→ 下载附件 
                → 按 issue type 保存 → 更新状态
    ↓
保存状态文件
    ↓
生成错误报告
    ↓
完成
```

---

## 模块设计

### 1. cli.py - CLI 入口

**职责：**
- 命令行参数解析
- 配置加载和环境变量替换
- 数据源过滤
- 协调各模块执行

**关键函数：**
- `init()` - 初始化配置文件
- `sync()` - 执行同步
- `list_sources()` - 列出数据源
- `status()` - 查看同步状态
- `filter_sources()` - 过滤数据源

### 2. crawler/confluence.py - Confluence 爬取

**职责：**
- 连接 Confluence API
- 获取 space 页面列表
- 下载页面内容和附件
- 转换 HTML 到 Markdown

**关键类/方法：**
- `ConfluenceCrawler`
  - `crawl_space()` - 爬取整个 space
  - `_process_page()` - 处理单个页面
  - `_build_metadata()` - 构建元数据
  - `_download_attachment()` - 下载附件（带重试）

### 3. crawler/jira.py - Jira 爬取

**职责：**
- 连接 Jira API
- 使用 JQL 查询 issues
- 获取所有字段（标准 + 自定义）
- 获取评论和附件

**关键类/方法：**
- `JiraCrawler`
  - `crawl_project()` - 爬取整个 project
  - `_process_issue()` - 处理单个 issue
  - `_build_complete_issue_markdown()` - 构建完整 markdown（包含所有字段）
  - `_get_comments()` - 获取评论
  - `_download_attachment()` - 下载附件（带重试）

### 4. crawler/storage.py - 文件存储

**职责：**
- 管理文件系统操作
- 增量更新状态管理
- 文件名清理和路径处理
- 附件下载和保存

**关键类/方法：**
- `StorageManager`
  - `_load_state()` - 加载状态文件
  - `save_state()` - 保存状态文件
  - `save_confluence_page()` - 保存 Confluence 页面
  - `save_jira_issue()` - 保存 Jira issue（按 issue type 分类）
  - `_sanitize_filename()` - 清理文件名
  - `_save_attachments()` - 保存附件

### 5. crawler/converter.py - HTML → Markdown 转换

**职责：**
- HTML 到 Markdown 转换
- 处理 Confluence 特殊格式
- 附件链接转换

**关键函数：**
- `convert_html_to_markdown()` - 主转换函数
- `fix_attachment_links()` - 修复附件链接为相对路径

### 6. crawler/error_handler.py - 错误处理

**职责：**
- 错误记录和日志
- 自动重试机制
- 错误报告生成

**关键类/方法：**
- `ErrorHandler`
  - `retry_on_failure()` - 装饰器：自动重试
  - `log_error()` - 记录错误
  - `generate_error_report()` - 生成错误报告

---

## 依赖清单

### requirements.txt

```txt
atlassian-python-api>=3.41.0
markdownify>=0.11.6
click>=8.1.0
PyYAML>=6.0
requests>=2.31.0
```

---

## 决策日志

### 技术栈决策

| 决策 | 选择 | 备选方案 | 理由 |
|------|------|----------|------|
| API 客户端 | `atlassian-python-api` | `mcp-atlassian` | 固定流程不需要 AI agent 交互能力，直接 API 封装更简单 |
| HTML → Markdown | `markdownify` | `html2text`, `pandoc` | 轻量、可定制、专门处理 HTML 转换 |
| CLI 框架 | `click` | `argparse`, `typer` | 简单、流行、文档完善 |
| 配置格式 | YAML | JSON, TOML | 可读性好，支持注释，适合手动编辑 |
| 增量更新 | JSON 状态文件 | SQLite, 文件时间戳 | 无需数据库，简单直接，易于调试 |

### 架构决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 输出格式 | 简单 markdown + 基本元数据 | llm-wiki-compiler 会处理概念提取，无需复杂 frontmatter |
| 配置结构 | 多数据源配置（sources 列表） | 支持多个 Jira/Confluence 实例，灵活管理不同环境 |
| CLI 设计 | 统一入口 + 数据源过滤 | 职责分离，支持选择性同步 |
| 文件组织 | 按数据源/space/project/issue-type 分类 | 保留原始层级，避免数据冲突，便于浏览和管理 |
| 附件处理 | 本地存储 + 相对路径 | 离线可用，符合 llm-wiki-compiler 的 sources 模式 |
| Jira 字段 | 包含所有字段 + 原始 JSON | 确保信息完整，未来可扩展 |
| 错误处理 | 跳过失败项 + 记录日志 | 不阻塞整体流程，便于后续排查 |
| 并发策略 | 暂不实现 | 简化实现，避免过早优化 |

### 非功能性决策

| 方面 | 决策 | 理由 |
|------|------|------|
| 性能 | 串行处理，暂不优化 | 数据量可控，优先保证稳定性 |
| 可维护性 | 模块化设计，清晰职责分离 | 频繁使用，需要易于调试和扩展 |
| 安全性 | API token 通过环境变量 | 避免敏感信息泄露 |
| 可观测性 | 详细日志 + 错误报告 | 便于排查问题和监控同步状态 |

---

## 核心假设

1. **API 访问权限：** 有 Atlassian 实例的 API token 和足够的读取权限
2. **网络稳定性：** 网络基本稳定，偶尔失败可接受（跳过并记录）
3. **存储空间：** 本地有足够空间存储所有附件
4. **Python 环境：** 运行环境有 Python 3.8+
5. **增量更新机制：** 基于 Atlassian API 的 `updated` 时间戳和 `version` 判断内容是否变更
6. **职责分离：** 爬虫只负责获取原始数据，llm-wiki-compiler 负责概念提取和结构化
7. **Markdown 简单性：** 不需要复杂的 frontmatter，基本元数据即可

---

## 明确的非目标

1. ❌ 不需要在爬取阶段做概念提取
2. ❌ 不需要处理页面间的关联关系
3. ❌ 不需要复杂的 frontmatter 结构
4. ❌ 不需要并发爬取优化
5. ❌ 不需要实时同步
6. ❌ 不需要 Web UI 界面

---

## 未来扩展方向

1. **并发爬取：** 当数据量增大时，可以添加多线程/异步支持
2. **增量优化：** 使用 webhook 或 RSS feed 实现更精确的增量更新
3. **过滤增强：** 支持基于标签、日期范围的更细粒度过滤
4. **导出格式：** 支持其他格式（如 JSON、HTML）
5. **监控告警：** 集成监控系统，同步失败时发送通知
6. **Docker 化：** 打包为 Docker 镜像，简化部署

---

## 实现顺序建议

1. **Phase 1 - 基础框架**
   - 项目结构搭建
   - 配置文件加载
   - CLI 基本命令

2. **Phase 2 - Confluence 爬取**
   - Confluence API 集成
   - 页面下载和转换
   - 附件处理

3. **Phase 3 - Jira 爬取**
   - Jira API 集成
   - Issue 下载（包含所有字段）
   - 按 issue type 分类存储

4. **Phase 4 - 增量更新**
   - 状态文件管理
   - 增量检测逻辑

5. **Phase 5 - 错误处理**
   - 重试机制
   - 错误日志和报告

6. **Phase 6 - 多数据源支持**
   - 数据源过滤
   - 独立存储路径

7. **Phase 7 - 测试和文档**
   - 单元测试
   - 使用文档
   - 示例配置

---

## 文档生成时间

2026-05-06
