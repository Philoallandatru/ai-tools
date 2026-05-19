# 项目结构说明

## 目录组织

```
ai-tools/
├── crawler/                    # 核心爬虫代码
│   ├── __init__.py
│   ├── confluence.py          # Confluence 爬虫实现
│   ├── jira.py               # Jira 爬虫实现
│   ├── storage.py            # 存储管理（Markdown 生成）
│   ├── error_handler.py      # 错误处理和重试逻辑
│   ├── doc_splitter.py       # 文档拆分工具
│   ├── searcher.py           # 全文搜索引擎
│   ├── doc_analyzer.py       # 文档分析器
│   ├── analyzers/            # Jira 分析器
│   │   ├── issue_summary.py  # 问题摘要分析器
│   │   ├── root_cause.py     # 根因分析器
│   │   ├── similar_jira.py   # 类似问题查找器
│   │   ├── closed_loop.py    # 闭环检查器
│   │   ├── comment_analyzer.py # 评论分析器（智能采样）
│   │   ├── metadata_extractor.py # 元数据提取器
│   │   └── action_recommender.py # 行动建议生成器
│   └── filters/              # LLM 响应过滤器
│       └── reasoning_filter.py # 推理过程过滤器
│
├── docs/                      # 项目文档
│   ├── DESIGN.md             # 系统设计文档
│   ├── QUICKSTART.md         # 快速开始指南
│   ├── USAGE.md              # 详细使用说明
│   ├── SCHEDULER.md          # 定时任务配置
│   ├── WIKI_INTEGRATION.md   # Wiki 集成指南
│   ├── WIKI_SETUP_COMPLETE.md # Wiki 集成完成总结
│   └── DOC_ANALYZER_DESIGN.md # 文档分析器设计
│
├── scripts/                   # 工具脚本
│   ├── analyze_prompts.py    # Prompt 分析工具
│   ├── diagnose_confluence.py # Confluence 诊断工具
│   ├── download_modelscope_model.py # ModelScope 模型下载
│   ├── health-check.py       # 健康检查脚本
│   ├── run_e2e_tests.py      # E2E 测试运行器
│   ├── scheduler.py          # 定时任务调度器
│   ├── test_all_commands.bat # 命令测试（Windows）
│   ├── test_all_commands.sh  # 命令测试（Unix/Linux）
│   └── README.md             # 脚本说明文档
│
├── tests/                     # 测试文件
│   ├── integration/          # 集成测试
│   ├── unit/                 # 单元测试
│   ├── manual/               # 手动测试脚本
│   │   ├── test_comment_sampling.py # 评论采样测试
│   │   ├── test_full_analysis.py # 完整分析测试
│   │   ├── test_filter_integration.py # 过滤器集成测试
│   │   ├── test_mock_filter.py # Mock 过滤器测试
│   │   ├── test_prompt_optimization.py # Prompt 优化测试
│   │   ├── test_reasoning_filter.py # 推理过滤器测试
│   │   └── README.md         # 手动测试说明
│   ├── fixtures/             # 测试固件
│   ├── outputs/              # 测试输出文件
│   ├── test-sources/         # 测试用源文件
│   ├── test_reports/         # 测试报告
│   ├── test-config.yaml      # 测试配置
│   └── conftest.py           # pytest 配置
│
├── configs/                   # 配置文件目录
│   └── doc_analysis_config.yaml  # 文档分析配置
│
├── cli.py                     # CLI 命令入口
├── run-sync.ps1              # Windows PowerShell 同步脚本
│
├── config.example.yaml        # Atlassian 配置模板
├── .env.example              # 环境变量配置模板
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
sources/                      # 爬取的源文件（Markdown）
wikis/                        # 编译后的知识库
  ├── concepts/              # 概念页面
  ├── index.md               # 索引
  └── MOC.md                 # 概念地图
reports/                     # 分析报告输出
tests/outputs/               # 测试输出（包含测试结果和报告）
.llmwiki/                    # Wiki 编译缓存和状态
.venv/                       # Python 虚拟环境
__pycache__/                 # Python 缓存
config.yaml                  # 实际配置（包含敏感信息）
.env                         # 环境变量（包含 API 密钥）
.atlassian-sync-state.json   # 同步状态
.sync-state.json             # 同步状态
sync-errors.log              # 错误日志
.claude/                     # Claude Code 工作目录
.cache/                      # 缓存目录
uv.lock                      # UV 锁文件
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

### 爬虫模块

- **crawler/confluence.py**: Confluence 页面爬取逻辑
- **crawler/jira.py**: Jira Issue 爬取逻辑
- **crawler/storage.py**: Markdown 文件生成和存储
- **crawler/error_handler.py**: 统一的错误处理和重试机制

### Jira 分析器

- **crawler/analyzers/issue_summary.py**: 问题摘要分析器
  - 提取客户名称、测试项目、测试平台、根因、修复方案
- **crawler/analyzers/root_cause.py**: 根因分析器
  - 分析直接原因、深层原因、触发条件
- **crawler/analyzers/similar_jira.py**: 类似问题查找器
  - 基于 TF-IDF 相似度查找相关问题
- **crawler/analyzers/closed_loop.py**: 闭环检查器
  - 检查根因识别、修复方案、验证测试是否完成
- **crawler/analyzers/comment_analyzer.py**: 评论分析器
  - **智能采样策略**: 根据评论数量动态调整采样方式
  - ≤10条: 全部分析
  - 11-30条: 首5+后5
  - 31-50条: 首5+关键词5+后5
  - >50条: 首3+关键词10+后3
- **crawler/analyzers/metadata_extractor.py**: 元数据提取器
  - 提取影响范围、时间线、优先级等关键信息
- **crawler/analyzers/action_recommender.py**: 行动建议生成器
  - 生成技术、流程、测试三个维度的行动建议

### LLM 响应过滤器

- **crawler/filters/reasoning_filter.py**: 推理过程过滤器
  - 自动移除 LLM 响应中的思考过程标签
  - 支持多种标签格式: `<thinking>`, `<think>`, `<reflection>` 等

### 工具脚本

- **scripts/scheduler.py**: 定时任务调度器，支持自动同步
- **scripts/health-check.py**: 健康检查脚本，监控系统状态
- **scripts/analyze_prompts.py**: Prompt 分析和优化工具
- **scripts/diagnose_confluence.py**: Confluence 连接诊断工具
- **scripts/download_modelscope_model.py**: ModelScope 模型下载工具
- **scripts/run_e2e_tests.py**: E2E 测试运行器

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
- ✅ 测试框架（tests/）
- ✅ README 和 .gitignore

### 未提交的文件（敏感或生成的）

- ❌ config.yaml（包含 API token）
- ❌ .env（包含 API 密钥）
- ❌ sources/（爬取的数据）
- ❌ wiki/（生成的知识库）
- ❌ reports/（分析报告）
- ❌ .llmwiki/（编译缓存）
- ❌ .claude/（Claude Code 工作目录）
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
