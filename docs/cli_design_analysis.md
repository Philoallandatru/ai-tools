# CLI 设计分析与改进建议

## 当前命令分类

### 1. 数据源管理（Atlassian 相关）
- `init` - 初始化配置文件
- `list-sources` - 列出所有配置的数据源
- `sync` - 执行同步
- `status` - 查看同步状态

### 2. Wiki 知识库管理
- `wiki-init` - 初始化新的 wiki 仓库
- `wiki-list` - 列出所有配置的 wiki
- `wiki-status` - 显示 wiki 状态
- `compile-wiki` - 编译 wiki 知识库
- `query-wiki` - 查询 wiki 知识库
- `watch-wiki` - 监控 wiki 变化
- `migrate-wiki` - 迁移现有 wiki/ 目录到多 wiki 架构

### 3. 文档处理（PDF → Markdown → 分析）
- `convert-pdf` - 将 PDF 转换为 Markdown
- `split-doc` - 分割文档为小块
- `analyze-doc` - 分析文档（需求拆解）

### 4. Jira 相关
- `find-jira` - 查找 Jira issue
- `list-jira` - 列出 Jira issues
- `analyze-jira` - 分析 Jira issue

### 5. 搜索与报告
- `search` - 搜索内容
- `generate-report` - 生成报告
- `export-filtered` - 导出过滤后的文档

---

## 问题分析

### 1. 职责混乱
- **问题**：CLI 同时承担了 3 个完全不同的职责：
  1. Atlassian 数据爬取工具（原始定位）
  2. Wiki 知识库管理系统
  3. 文档分析工具（PDF → 需求拆解）

- **影响**：
  - 用户不清楚这个工具到底是做什么的
  - 命令太多（21个），难以记忆
  - 命令之间缺乏层次结构

### 2. 命名不一致
- `analyze-jira` vs `analyze-doc` - 都是分析，但一个用连字符，一个也用连字符（一致）
- `wiki-init` vs `convert-pdf` - wiki 相关用前缀，PDF 相关不用前缀
- `split-doc` vs `convert-pdf` - 都是文档处理，但命名风格不统一

### 3. 工作流不清晰
- PDF 处理工作流：`convert-pdf` → `split-doc` → `analyze-doc`
  - 用户需要记住 3 个独立的命令
  - 没有一个命令能完成端到端的流程
  - 中间文件管理麻烦

### 4. 缺少命令分组
- Click 支持命令分组（`@cli.group()`），但当前所有命令都是平铺的
- 没有利用子命令来组织相关功能

---

## 改进建议

### 方案 1：按功能域分组（推荐）

```bash
# 数据源管理
cli.py source init
cli.py source list
cli.py source sync [--source NAME] [--type jira|confluence]
cli.py source status

# Wiki 知识库
cli.py wiki init <wiki-name>
cli.py wiki list
cli.py wiki status [wiki-name]
cli.py wiki compile [wiki-name] [--all]
cli.py wiki query <question>
cli.py wiki watch [--interval 60]
cli.py wiki migrate <target-wiki>

# Jira 分析
cli.py jira find <issue-key>
cli.py jira list [--status STATUS] [--priority PRIORITY]
cli.py jira analyze <issue-key> [--wiki WIKI]

# 文档分析（核心工作流）
cli.py doc convert <pdf-file> [--output FILE] [--pages 1-50]
cli.py doc split <markdown-file> [--output-dir DIR] [--max-chars 5000]
cli.py doc analyze <markdown-file> [--config CONFIG]
cli.py doc pipeline <pdf-file>  # 端到端：convert → split → analyze

# 搜索与报告
cli.py search <query> [--type jira|confluence|all]
cli.py report generate [--type TYPE] [--start-date DATE]
cli.py report export [--doc-type TYPE] [--status STATUS]
```

**优点**：
- 清晰的功能域划分
- 命令层次结构明确
- 易于扩展新功能
- 符合现代 CLI 工具的设计模式（如 `git`, `docker`, `kubectl`）

**缺点**：
- 需要重构现有代码
- 破坏向后兼容性（需要提供别名或迁移指南）

---

### 方案 2：保持扁平结构，但改进命名

```bash
# 数据源管理（保持原样）
cli.py init
cli.py list-sources
cli.py sync
cli.py status

# Wiki 知识库（统一前缀）
cli.py wiki-init
cli.py wiki-list
cli.py wiki-status
cli.py wiki-compile
cli.py wiki-query
cli.py wiki-watch
cli.py wiki-migrate

# Jira 分析（统一前缀）
cli.py jira-find
cli.py jira-list
cli.py jira-analyze

# 文档分析（统一前缀 + 端到端命令）
cli.py doc-convert
cli.py doc-split
cli.py doc-analyze
cli.py doc-pipeline  # 新增：端到端处理

# 搜索与报告（统一前缀）
cli.py search
cli.py report-generate
cli.py report-export
```

**优点**：
- 改动较小
- 保持扁平结构，学习成本低
- 通过前缀实现逻辑分组

**缺点**：
- 命令仍然很多
- 没有利用 Click 的分组功能
- 命令补全体验不如分组方案

---

### 方案 3：混合方案（渐进式重构）

**第一阶段**：保持现有命令，添加分组别名
```bash
# 旧命令仍然可用（向后兼容）
cli.py convert-pdf input.pdf

# 新的分组命令
cli.py doc convert input.pdf

# 两者等价，逐步引导用户迁移
```

**第二阶段**：添加端到端命令
```bash
# 新增高级命令，简化常见工作流
cli.py doc pipeline input.pdf --output-dir ./analysis
# 等价于：convert-pdf → split-doc → batch-analyze
```

**第三阶段**：废弃旧命令
```bash
# 在旧命令中显示警告
cli.py convert-pdf input.pdf
# Warning: 'convert-pdf' is deprecated, use 'doc convert' instead
```

---

## 具体改进建议

### 1. 立即可做的改进（不破坏兼容性）

#### 1.1 添加端到端命令
```python
@cli.command('doc-pipeline')
@click.argument('pdf_file')
@click.option('--output-dir', default='./analysis', help='输出目录')
@click.option('--pages', help='页码范围，如 1-50')
@click.option('--max-chars', default=5000, help='每个文档最大字符数')
@click.option('--config', default='configs/doc_analysis_config.yaml')
def doc_pipeline(pdf_file, output_dir, pages, max_chars, config):
    """端到端文档分析：PDF → Markdown → 拆分 → 批量分析"""
    output = CLIOutput()
    
    # Step 1: Convert PDF
    output.info("Step 1/3: Converting PDF to Markdown...")
    md_file = convert_pdf_internal(pdf_file, pages)
    
    # Step 2: Split document
    output.info("Step 2/3: Splitting document...")
    split_dir = split_doc_internal(md_file, output_dir, max_chars)
    
    # Step 3: Batch analyze
    output.info("Step 3/3: Analyzing documents...")
    batch_analyze_internal(split_dir, config)
    
    output.success(f"Pipeline complete! Results in {output_dir}")
```

#### 1.2 改进帮助文档
```python
@click.group()
def cli():
    """
    Atlassian 数据爬取与文档分析工具
    
    主要功能：
      1. 数据源管理：从 Jira/Confluence 同步数据
      2. Wiki 知识库：构建和查询知识库
      3. 文档分析：PDF → Markdown → 需求拆解
      4. Jira 分析：分析 issue 并生成报告
    
    快速开始：
      # 初始化配置
      python cli.py init
      
      # 分析 PDF 文档（端到端）
      python cli.py doc-pipeline input.pdf
      
      # 查询 wiki
      python cli.py wiki-query "如何实现 NVMe 初始化？"
    """
    pass
```

#### 1.3 添加命令别名和分组提示
```python
# 在每个命令的帮助文档中添加"相关命令"
@cli.command()
def convert_pdf(...):
    """
    将 PDF 转换为 Markdown
    
    相关命令：
      split-doc    - 拆分 Markdown 文档
      analyze-doc  - 分析文档内容
      doc-pipeline - 端到端处理（推荐）
    """
```

### 2. 中期改进（需要重构）

#### 2.1 引入命令分组
```python
@click.group()
def cli():
    """主 CLI 入口"""
    pass

@cli.group()
def doc():
    """文档处理命令组"""
    pass

@doc.command('convert')
def doc_convert(...):
    """转换 PDF 为 Markdown"""
    pass

@doc.command('split')
def doc_split(...):
    """拆分文档"""
    pass

@doc.command('analyze')
def doc_analyze(...):
    """分析文档"""
    pass

@doc.command('pipeline')
def doc_pipeline(...):
    """端到端处理"""
    pass
```

#### 2.2 统一配置管理
```python
# 当前问题：每个命令都有 --config 参数
# 改进：使用全局配置

@click.group()
@click.option('--config', default='config.yaml', envvar='CLI_CONFIG')
@click.pass_context
def cli(ctx, config):
    """主 CLI 入口"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = config

# 子命令自动继承配置
@cli.command()
@click.pass_context
def sync(ctx):
    config = ctx.obj['config']
    # ...
```

### 3. 长期改进（架构级）

#### 3.1 插件化架构
```python
# 允许用户自定义命令
# ~/.cli/plugins/my_plugin.py
@cli.command()
def my_custom_command():
    """用户自定义命令"""
    pass
```

#### 3.2 交互式模式
```python
@cli.command()
def interactive():
    """进入交互式模式"""
    while True:
        cmd = input("cli> ")
        # 解析并执行命令
```

---

## 推荐实施路径

### 阶段 1：立即改进（1-2 天）
1. ✅ 添加 `doc-pipeline` 端到端命令
2. ✅ 改进帮助文档，添加"相关命令"提示
3. ✅ 统一命名风格（所有文档相关命令用 `doc-` 前缀）
4. ✅ 添加命令别名（保持向后兼容）

### 阶段 2：中期重构（1 周）
1. 引入命令分组（`doc`, `wiki`, `jira`, `source`）
2. 保留旧命令作为别名，显示废弃警告
3. 统一配置管理（全局 `--config` 参数）
4. 改进错误提示和工作流指引

### 阶段 3：长期优化（按需）
1. 插件化架构
2. 交互式模式
3. 命令补全脚本（bash/zsh）
4. 配置向导（`cli.py init --wizard`）

---

## 示例：改进后的用户体验

### 当前体验
```bash
# 用户需要记住 3 个命令和中间文件路径
python cli.py convert-pdf input.pdf -o output.md
python cli.py split-doc output.md -o output_split/
python cli.py analyze-doc output_split/section_01.md

# 如果出错，用户不知道下一步该做什么
```

### 改进后体验
```bash
# 方式 1：端到端命令（推荐）
python cli.py doc pipeline input.pdf

# 方式 2：分步执行（高级用户）
python cli.py doc convert input.pdf
python cli.py doc split output.md
python cli.py doc analyze output_split/

# 方式 3：交互式（新手友好）
python cli.py interactive
cli> doc pipeline input.pdf
cli> wiki query "NVMe 初始化流程"
```

---

## 总结

**核心问题**：
1. 职责混乱：3 个不同的功能域混在一起
2. 命名不一致：缺乏统一的命名规范
3. 工作流不清晰：缺少端到端命令
4. 缺少分组：21 个平铺命令难以管理

**推荐方案**：
- **短期**：添加 `doc-pipeline` 端到端命令，改进帮助文档
- **中期**：引入命令分组，保持向后兼容
- **长期**：插件化架构，交互式模式

**优先级**：
1. 🔴 高优先级：添加 `doc-pipeline` 命令（立即解决用户痛点）
2. 🟡 中优先级：引入命令分组（改善长期可维护性）
3. 🟢 低优先级：插件化、交互式（锦上添花）
