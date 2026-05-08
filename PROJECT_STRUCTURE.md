# 项目结构说明

## 目录组织

```
ai-tools/
├── crawler/                    # 核心爬虫代码
│   ├── __init__.py
│   ├── confluence.py          # Confluence 爬虫实现
│   ├── jira.py               # Jira 爬虫实现
│   ├── storage.py            # 存储管理（Markdown 生成）
│   └── error_handler.py      # 错误处理和重试逻辑
│
├── docs/                      # 项目文档
│   ├── DESIGN.md             # 系统设计文档
│   ├── QUICKSTART.md         # 快速开始指南
│   ├── USAGE.md              # 详细使用说明
│   ├── SCHEDULER.md          # 定时任务配置
│   ├── WIKI_INTEGRATION.md   # Wiki 集成指南
│   └── WIKI_SETUP_COMPLETE.md # Wiki 集成完成总结
│
├── test-sources/              # 测试用的示例文件
│   └── nvme.md
│
├── cli.py                     # CLI 命令入口
├── scheduler.py               # 定时任务调度器
├── health-check.py            # 健康检查脚本
├── run-sync.ps1              # Windows PowerShell 同步脚本
│
├── config.example.yaml        # Atlassian 配置模板
├── .env.example              # 环境变量配置模板
├── test-config.yaml          # 测试配置
│
├── pyproject.toml            # Python 项目配置（uv）
├── requirements.txt          # Python 依赖列表
│
├── .gitignore                # Git 忽略规则
└── README.md                 # 项目主文档
```

## 被 .gitignore 排除的目录

以下目录包含生成的文件或敏感信息，不会提交到 Git：

```
sources/                      # 爬取的源文件（57 个 Markdown）
wiki/                         # 编译后的知识库（341 个概念页面）
  ├── concepts/              # 概念页面
  ├── index.md               # 索引
  └── MOC.md                 # 概念地图
.llmwiki/                    # Wiki 编译缓存和状态
.venv/                       # Python 虚拟环境
__pycache__/                 # Python 缓存
config.yaml                  # 实际配置（包含敏感信息）
.env                         # 环境变量（包含 API 密钥）
.atlassian-sync-state.json   # 同步状态
sync-errors.log              # 错误日志
```

## 文件说明

### 核心代码

- **cli.py**: 主命令行接口，包含所有 CLI 命令
  - `sync`: 同步 Atlassian 数据
  - `compile-wiki`: 编译知识库
  - `query-wiki`: 查询知识库
  - `wiki-status`: 查看 wiki 状态
  - `watch-wiki`: 监控模式
  - `list-sources`: 列出数据源
  - `status`: 查看同步状态

- **scheduler.py**: 定时任务调度器，支持自动同步

- **health-check.py**: 健康检查脚本，监控系统状态

### 爬虫模块

- **crawler/confluence.py**: Confluence 页面爬取逻辑
- **crawler/jira.py**: Jira Issue 爬取逻辑
- **crawler/storage.py**: Markdown 文件生成和存储
- **crawler/error_handler.py**: 统一的错误处理和重试机制

### 配置文件

- **config.example.yaml**: Atlassian 配置模板
  - 配置 Confluence 和 Jira 数据源
  - 指定要爬取的 Space 和 Project

- **.env.example**: 环境变量模板
  - LLM API 配置（MiniMax）
  - Wiki 编译器配置

### 文档

- **README.md**: 项目主文档，包含快速开始和使用说明
- **docs/DESIGN.md**: 详细的系统设计和架构说明
- **docs/QUICKSTART.md**: 5 分钟快速上手指南
- **docs/USAGE.md**: 完整的使用说明
- **docs/SCHEDULER.md**: 定时任务配置指南
- **docs/WIKI_INTEGRATION.md**: Wiki 编译器集成文档
- **docs/WIKI_SETUP_COMPLETE.md**: Wiki 集成完成总结和验证

## Git 仓库状态

### 已提交的文件

- ✅ 所有核心代码（crawler/, cli.py, scheduler.py, health-check.py）
- ✅ 所有文档（docs/）
- ✅ 配置模板（config.example.yaml, .env.example）
- ✅ 项目配置（pyproject.toml, requirements.txt）
- ✅ 测试文件（test-sources/, test-config.yaml）
- ✅ README 和 .gitignore

### 未提交的文件（敏感或生成的）

- ❌ config.yaml（包含 API token）
- ❌ .env（包含 API 密钥）
- ❌ sources/（爬取的数据）
- ❌ wiki/（生成的知识库）
- ❌ .llmwiki/（编译缓存）
- ❌ 日志文件和状态文件

## 下一步操作

### 推送到 GitHub

```bash
git push -u origin main
```

### 在新环境中使用

```bash
# 1. 克隆仓库
git clone https://github.com/Philoallandatru/ai-tools.git
cd ai-tools

# 2. 安装依赖
uv sync
npm install -g llm-wiki-compiler

# 3. 配置
cp config.example.yaml config.yaml
cp .env.example .env
# 编辑 config.yaml 和 .env

# 4. 开始使用
uv run python cli.py sync
uv run python cli.py compile-wiki
```

## 项目统计

- **代码文件**: 23 个
- **代码行数**: 3509 行
- **文档页面**: 6 个
- **支持的命令**: 8 个
- **生成的概念**: 341 个（从 57 个源文件）

## 技术栈

- Python 3.12+
- atlassian-python-api
- llm-wiki-compiler (Node.js)
- MiniMax-M2.7 LLM
- Click CLI
- APScheduler
- YAML/JSON 配置

## 维护说明

### 添加新功能

1. 在 `crawler/` 中添加新的爬虫模块
2. 在 `cli.py` 中添加新的命令
3. 更新 `docs/USAGE.md` 文档
4. 提交代码并推送

### 更新文档

1. 编辑 `docs/` 中的相应文档
2. 更新 `README.md` 如果有重大变更
3. 提交并推送

### 发布新版本

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`（如果有）
3. 创建 Git tag
4. 推送到 GitHub
