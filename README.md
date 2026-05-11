# AI Tools - Atlassian Knowledge Management System

一个集成了 Atlassian 数据爬取和智能知识库编译的工具集。

## 功能特性

### 1. Atlassian 数据爬取
- ✅ **Confluence 页面爬取**: 自动下载 Confluence 空间的所有页面
- ✅ **Jira Issue 爬取**: 批量导出 Jira 项目的 Issues
- ✅ **Markdown 格式**: 所有数据保存为结构化的 Markdown 文件
- ✅ **增量同步**: 支持增量更新，只爬取变更的内容
- ✅ **附件下载**: 自动下载并保存附件
- ✅ **错误处理**: 完善的错误处理和重试机制
- ✅ **筛选导出**: 根据时间和状态筛选导出 Jira/Confluence 文档
- ✅ **全文搜索**: 快速搜索所有文档内容，支持正则表达式和高亮显示

### 2. 文档拆分工具
- ✅ **智能拆分**: 按 Markdown 标题层级自动拆分长文档
- ✅ **大小控制**: 支持设置单个文档的最大字符数
- ✅ **递归拆分**: 超大章节自动递归拆分或按行切分
- ✅ **元数据保留**: 自动添加源文件和章节信息
- ✅ **预览模式**: dry-run 模式预览拆分结果

### 3. 智能知识库编译 (llm-wiki-compiler)
- ✅ **概念提取**: 使用 LLM 从文档中自动提取技术概念
- ✅ **知识图谱**: 生成互联的概念网络（341 个概念）
- ✅ **中文支持**: 完整支持中文内容处理
- ✅ **智能查询**: 基于 AI 的知识问答系统
- ✅ **实时监控**: 自动监控源文件变化并重新编译

### 4. Jira 深度分析
- ✅ **相关知识检索**: 从 Wiki 和源文件中检索相关技术知识
- ✅ **根因分析**: 使用 LLM 分析问题的直接原因、深层原因和触发条件
- ✅ **类似问题查找**: 基于关键词和根因匹配相似的 Jira Issues
- ✅ **闭环检查**: 检查问题是否完成根因识别、修复和验证
- ✅ **评论分析**: 分析评论的时间线、关键决策和合理性
- ✅ **行动建议**: 生成短期、中期、长期的行动建议
- ✅ **Markdown 报告**: 自动生成结构化的分析报告

### 5. 文档分析 (NEW!)
- ✅ **智能切分**: 按 Markdown 标题层级自动切分文档
- ✅ **关键词提取**: 自动提取技术术语、标识符和中文词汇
- ✅ **上下文检索**: 从代码库和需求文档中检索相关内容
- ✅ **LLM 分析**: 判断内容是否可形成需求或测试用例
- ✅ **批量处理**: 串行处理所有小节，自动生成完整报告
- ✅ **配置灵活**: 通过 YAML 配置文件管理 prompt 和检索规则
- ✅ **预览模式**: dry-run 模式预览处理结果

## 快速开始

### 安装依赖

```bash
# 安装 Python 依赖（使用 uv）
uv sync

# 或使用 pip
pip install -r requirements.txt

# 安装 Node.js 依赖（用于 wiki 编译）
npm install -g llm-wiki-compiler
```

### 配置

1. 复制配置文件模板：
```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

2. 编辑 `config.yaml` 配置 Atlassian 连接信息
3. 编辑 `.env` 配置 LLM API 密钥（用于 wiki 编译）

### 基本使用

```bash
# 1. 爬取 Atlassian 数据
uv run python cli.py sync

# 2. 全文搜索（快速查找内容）
# 基本搜索
uv run python cli.py search "NVMe Reset"

# 只搜索 Jira issues
uv run python cli.py search "性能优化" --type jira

# 使用正则表达式搜索
uv run python cli.py search "CC\.EN|CSTS\.RDY" --regex

# 显示更多上下文（前后 5 行）
uv run python cli.py search "测试" --context 5

# 只显示统计信息
uv run python cli.py search "NVMe" --stats-only

# 根据 issue key 查找 Jira
uv run python cli.py find-jira KAN-10

# 列出所有 Jira issues
uv run python cli.py list-jira

# 按状态过滤
uv run python cli.py list-jira --status "进行中"

# 按优先级过滤
uv run python cli.py list-jira --priority Highest

# 3. Jira 深度分析
# 使用 Mock LLM 分析（测试模式）
uv run python cli.py analyze-jira KAN-2

# 使用真实 LLM 分析（需要配置 llmstudio）
uv run python cli.py analyze-jira KAN-2 --llm-provider llmstudio

# 4. 文档分析（NEW!）
# 分析文档并生成需求/测试用例建议报告
uv run python cli.py analyze-doc sources/KAN-1.md

# 使用自定义配置
uv run python cli.py analyze-doc sources/requirements.md --config custom_config.yaml

# 预览模式（不调用 LLM）
uv run python cli.py analyze-doc sources/spec.md --dry-run

# 指定输出路径
uv run python cli.py analyze-doc sources/doc.md --output reports/my_analysis.md

# 5. 自动报告生成
# 生成本周周报
uv run python cli.py generate-report

# 生成今日日报
uv run python cli.py generate-report --type daily

# 生成月报
uv run python cli.py generate-report --type monthly

# 生成指定时间范围的报告
uv run python cli.py generate-report --start 2026-05-01 --end 2026-05-07

# 输出为 JSON 格式
uv run python cli.py generate-report --format json

# 5. 筛选导出文档（可选）
# 导出今天更新的进行中的 Jira issues
uv run python cli.py export-filtered --today --status "进行中"

# 导出最近 7 天更新的待办和进行中的 issues
uv run python cli.py export-filtered --days 7 --status "待办" --status "进行中"

# 导出昨天更新的所有 Confluence 页面
uv run python cli.py export-filtered --type confluence --yesterday

# 6. 拆分长文档（可选）
uv run python cli.py split-doc test-sources/nvme.md --split-level 2 --max-chars 15000

# 7. 编译知识库
uv run python cli.py compile-wiki

# 8. 查询知识库
uv run python cli.py query-wiki "什么是 NVMe 重置机制？"

# 9. 查看 wiki 状态
uv run python cli.py wiki-status

# 10. 监控模式（自动重新编译）
uv run python cli.py watch-wiki
```

## 项目结构

```
ai-tools/
├── crawler/              # 爬虫核心代码
│   ├── __init__.py
│   ├── confluence.py     # Confluence 爬虫
│   ├── jira.py          # Jira 爬虫
│   ├── storage.py       # 存储管理
│   ├── error_handler.py # 错误处理
│   ├── doc_splitter.py  # 文档拆分工具
│   ├── searcher.py      # 全文搜索引擎
│   └── doc_analyzer.py  # 文档分析器（NEW!）
├── configs/             # 配置文件目录（NEW!）
│   └── doc_analysis_config.yaml  # 文档分析配置
├── sources/             # 爬取的源文件（57 个 Markdown）
├── wiki/                # 编译后的知识库
│   ├── concepts/        # 341 个概念页面
│   ├── index.md         # 索引页面
│   └── MOC.md          # 概念地图
├── reports/             # 分析报告输出目录
├── .llmwiki/           # Wiki 编译缓存
├── docs/               # 文档
│   ├── DESIGN.md       # 设计文档
│   ├── QUICKSTART.md   # 快速开始
│   ├── USAGE.md        # 使用指南
│   ├── SCHEDULER.md    # 定时任务配置
│   ├── WIKI_INTEGRATION.md      # Wiki 集成文档
│   ├── WIKI_SETUP_COMPLETE.md   # Wiki 完成总结
│   └── DOC_ANALYZER_DESIGN.md   # 文档分析器设计（NEW!）
├── cli.py              # CLI 命令入口
├── scheduler.py        # 定时任务调度器
├── health-check.py     # 健康检查脚本
├── config.yaml         # Atlassian 配置
├── .env               # LLM API 配置
└── pyproject.toml     # Python 项目配置
```

## 数据统计

- **源文件**: 57 个 Markdown 文件
- **生成概念**: 341 个中文概念页面
- **数据来源**: Confluence (36 页) + Jira (21 issues)
- **知识领域**: NVMe、SSD 固件、测试、PCIe 等

## 技术栈

- **Python 3.12+**: 核心爬虫逻辑
- **atlassian-python-api**: Atlassian API 客户端
- **llm-wiki-compiler**: 知识库编译器（Node.js）
- **MiniMax API**: 中文 LLM 服务（MiniMax-M2.7）
- **Click**: CLI 框架
- **APScheduler**: 定时任务调度

## 详细文档

- [设计文档](docs/DESIGN.md) - 系统架构和设计决策
- [快速开始](docs/QUICKSTART.md) - 5 分钟上手指南
- [使用指南](docs/USAGE.md) - 详细的使用说明
- [全文搜索](docs/SEARCH.md) - 搜索功能完整指南
- [文档拆分](docs/DOC_SPLITTING.md) - 长文档拆分工具使用指南
- [定时任务](docs/SCHEDULER.md) - 配置自动同步
- [Wiki 集成](docs/WIKI_INTEGRATION.md) - Wiki 编译器集成指南
- [Wiki 完成总结](docs/WIKI_SETUP_COMPLETE.md) - Wiki 集成成果

## 常见问题

### Windows 兼容性

项目已针对 Windows 进行优化：
- UTF-8 编码支持
- 使用 `npx` 调用 Node.js 工具
- 正确的 subprocess 配置

### 模型配置

确保 `.env` 中的模型名称格式正确：
```env
LLMWIKI_MODEL=MiniMax-M2.7  # 正确
# LLMWIKI_MODEL=minimax-2.7  # 错误
```

### 文件组织

源文件必须放在 `sources/` 根目录，而非子目录：
```
✓ sources/file.md
✗ sources/confluence/file.md
```

## 获取 API Token

### Atlassian Cloud

1. 访问 https://id.atlassian.com/manage-profile/security/api-tokens
2. 点击 "Create API token"
3. 复制生成的 token

### MiniMax API

1. 访问 https://www.minimaxi.com/
2. 注册并获取 API Key
3. 配置到 `.env` 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
