# Wiki 集成指南

## 概述

本项目集成了 [llm-wiki-compiler](https://github.com/atomicmemory/llm-wiki-compiler)，可以将爬取的 Atlassian 数据自动编译成互联的知识 wiki。

**工作流程：**
```
Atlassian (Jira/Confluence) 
  → 爬取 (cli.py sync) 
  → sources/ (markdown 文件)
  → 编译 (llmwiki compile)
  → wiki/ (概念页面)
  → 查询 (llmwiki query)
```

## 安装

### 1. 安装 llm-wiki-compiler

```bash
npm install -g llm-wiki-compiler
```

### 2. 配置 MiniMax API

复制示例配置并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 MiniMax API 配置：

```env
# MiniMax API configuration (OpenAI-compatible mode)
LLMWIKI_PROVIDER=openai
OPENAI_API_KEY=your-minimax-api-key
OPENAI_BASE_URL=https://api.minimax.chat/v1
LLMWIKI_MODEL=minimax-2.7

# Output in Chinese
LLMWIKI_OUTPUT_LANG=zh-CN

# Adjust timeouts for API
LLMWIKI_REQUEST_TIMEOUT_MS=600000
```

## 使用方式

### 方式 1: 手动编译（推荐用于测试）

```bash
# 步骤 1: 爬取 Atlassian 数据
uv run python cli.py sync

# 步骤 2: 编译 wiki
uv run python cli.py compile-wiki

# 步骤 3: 查看 wiki 状态
uv run python cli.py wiki-status

# 步骤 4: 查询 wiki
uv run python cli.py query-wiki "什么是 NVMe Reset Timeout?"

# 步骤 5: 保存查询结果为 wiki 页面
uv run python cli.py query-wiki "NVMe 安全命令" --save
```

### 方式 2: Watch 模式（推荐用于生产）

Watch 模式会自动监控 `sources/` 目录的变化并重新编译：

```bash
# 在一个终端窗口中启动 watch 模式
uv run python cli.py watch-wiki

# 在另一个终端窗口中运行同步
uv run python cli.py sync

# watch 会自动检测变化并重新编译
```

**优势：**
- 自动化：sources 变化时自动重新编译
- 增量更新：只处理变更的文件
- 实时反馈：立即看到编译结果

### 方式 3: 定时任务 + Watch

结合定时同步和 watch 模式：

```bash
# 1. 启动 watch 模式（作为后台服务）
nohup uv run python cli.py watch-wiki > wiki-watch.log 2>&1 &

# 2. 设置定时同步（使用 scheduler 或 cron）
# watch 会自动检测同步后的变化并编译
```

## 输出结构

```
wiki/
├── concepts/          # 编译后的概念页面
│   ├── nvme-reset.md
│   ├── ssd-testing.md
│   └── ...
├── queries/           # 保存的查询结果
│   └── ...
└── index.md           # 自动生成的目录

.llmwiki/
├── schema.json        # 可选的页面类型定义
└── candidates/        # 待审核的候选页面（如果使用 --review 模式）
```

## Wiki 页面格式

编译后的 wiki 页面包含：

```markdown
---
title: NVMe Reset Timeout
summary: NVMe 设备复位超时机制的详细说明
kind: concept
sources:
  - confluence/sakiko222-confluence/MFS/Deep-Analysis-of-NVMe-Reset-Timeout.md
  - jira/sakiko222-jira/KAN/Bug/KAN-15.md
confidence: 0.85
provenanceState: merged
---

# NVMe Reset Timeout

[概念内容...]

## 相关概念

- [[NVMe 安全命令]]
- [[SSD 性能测试]]

## 来源

^[Deep-Analysis-of-NVMe-Reset-Timeout.md]
^[KAN-15.md:42-58]
```

## 高级功能

### 1. 导出 Wiki

```bash
# 导出为 llms.txt（用于 LLM 上下文）
llmwiki export --target llms.txt

# 导出为 JSON
llmwiki export --target json

# 导出为 GraphML（知识图谱）
llmwiki export --target graphml

# 导出为 Marp 幻灯片
llmwiki export --target marp
```

### 2. 质量检查

```bash
# 运行 lint 检查
llmwiki lint

# 检查内容：
# - 断开的链接
# - 孤立的页面
# - 矛盾的概念
```

### 3. Schema 定义

创建自定义页面类型：

```bash
# 初始化 schema
llmwiki schema init

# 查看 schema
llmwiki schema show
```

编辑 `.llmwiki/schema.json` 定义页面类型：

```json
{
  "kinds": {
    "concept": {
      "description": "独立的概念或模式",
      "minWikilinks": 2
    },
    "entity": {
      "description": "人物、产品、组织或工件",
      "minWikilinks": 1
    },
    "comparison": {
      "description": "并排分析",
      "minWikilinks": 2
    },
    "overview": {
      "description": "连接多个概念的领域地图",
      "minWikilinks": 5
    }
  }
}
```

### 4. MCP Server 集成

启动 MCP 服务器供 AI agent 使用：

```bash
llmwiki serve --root /path/to/ai-tools
```

在 Claude Desktop 或 Cursor 中配置：

```json
{
  "mcpServers": {
    "atlassian-wiki": {
      "command": "npx",
      "args": ["llm-wiki-compiler", "serve", "--root", "C:\\Users\\10259\\Documents\\code\\codex\\ai-tools"],
      "env": {
        "OPENAI_API_KEY": "your-minimax-api-key",
        "OPENAI_BASE_URL": "https://api.minimax.chat/v1",
        "LLMWIKI_MODEL": "minimax-2.7",
        "LLMWIKI_OUTPUT_LANG": "zh-CN"
      }
    }
  }
}
```

## 故障排查

### 问题 1: llmwiki 命令找不到

```bash
# 检查安装
npm list -g llm-wiki-compiler

# 重新安装
npm install -g llm-wiki-compiler
```

### 问题 2: MiniMax API 连接失败

```bash
# 测试 API 连接
curl -X POST https://api.minimax.chat/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"minimax-2.7","messages":[{"role":"user","content":"test"}]}'

# 检查 .env 配置
cat .env

# 确保环境变量已加载
source .env  # Linux/macOS
# 或在 Windows PowerShell 中手动设置
```

### 问题 3: 编译速度慢

```bash
# 首次编译会处理所有文件（慢）
# 后续编译只处理变更文件（快）

# 调整 prompt budget（减少每个概念的字符限制）
export LLMWIKI_PROMPT_BUDGET_CHARS=100000

# 使用 --verbose 查看详细进度
llmwiki compile --verbose
```

### 问题 4: 中文概念提取不准确

```bash
# 确保输出语言设置正确
echo $LLMWIKI_OUTPUT_LANG  # 应该是 zh-CN

# 检查 wiki 页面的语言
cat wiki/concepts/*.md | head -50

# 如果需要，重新编译
rm -rf wiki/ .llmwiki/
llmwiki compile
```

### 问题 5: Watch 模式不工作

```bash
# 检查 watch 进程
ps aux | grep llmwiki

# 查看 watch 日志
tail -f wiki-watch.log

# 手动触发编译测试
llmwiki compile
```

## 性能优化

### 1. 增量编译

llm-wiki-compiler 使用 SHA-256 哈希跟踪文件变化：

- 只有变更的源文件会重新处理
- 未变更的文件跳过 LLM 调用
- 大幅减少 API 调用和编译时间

### 2. Prompt Budget

控制每个概念的处理字符数：

```env
# 默认: 200,000 字符
LLMWIKI_PROMPT_BUDGET_CHARS=200000

# 对于大型知识库，可以减少
LLMWIKI_PROMPT_BUDGET_CHARS=100000
```

### 3. 超时设置

根据网络情况调整：

```env
# 默认: 600,000 ms (10 分钟)
LLMWIKI_REQUEST_TIMEOUT_MS=600000

# 如果 API 响应慢，增加超时
LLMWIKI_REQUEST_TIMEOUT_MS=1200000
```

## 最佳实践

1. **首次编译**
   - 使用小数据集测试（几个文件）
   - 验证 API 连接和输出质量
   - 然后处理完整数据集

2. **日常使用**
   - 使用 watch 模式自动编译
   - 定期运行 `llmwiki lint` 检查质量
   - 使用 query 功能验证知识提取

3. **监控**
   - 定期检查 wiki 状态：`python cli.py wiki-status`
   - 查看健康检查：`python health-check.py`
   - 监控 API 使用量和成本

4. **备份**
   - wiki/ 目录可以重新生成，不需要备份
   - sources/ 目录是原始数据，应该备份
   - .llmwiki/ 包含状态，建议备份以加速重新编译

## 参考资源

- [llm-wiki-compiler GitHub](https://github.com/atomicmemory/llm-wiki-compiler)
- [MiniMax API 文档](https://api.minimax.chat/document)
- [Obsidian](https://obsidian.md/) - 可用于浏览生成的 wiki
