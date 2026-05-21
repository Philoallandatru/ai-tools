# 代码检索和文档检索日志说明

## 概述

`analyze-doc` 命令在分析文档时会执行以下检索操作：
1. **关键词提取** - 从文档内容中提取技术关键词
2. **代码检索** - 在代码库中搜索相关代码片段
3. **文档检索** - 在需求文档中搜索相关文档片段

现在所有检索过程都会输出详细的日志，帮助你了解检索的详细过程。

## 📍 日志存储位置

### 当前配置

日志会同时输出到：
1. **控制台** - 实时查看
2. **日志文件** - `logs/analyze.log`（完整路径：`C:\Users\Administrator\Documents\Code\my-code\ai-tools\logs\analyze.log`）

### 修改日志位置

在 `config.yaml` 中修改：

```yaml
logging:
  level: INFO              # 日志级别：DEBUG, INFO, WARNING, ERROR
  format: text             # 格式：text (易读) 或 json (结构化)
  output_file: "logs/analyze.log"   # 日志文件路径（null = 只输出到控制台）
```

### 查看日志文件

```bash
# Windows
type logs\analyze.log

# Linux/Mac
cat logs/analyze.log

# 实时查看（tail）
tail -f logs/analyze.log
```

## 日志输出示例

### 1. 关键词提取日志

```
============================================================
开始提取关键词
文本长度: 156 字符
文本预览: ## NVMe 控制器重置

NVMe 控制器重置是一个关键的错误恢复机制。当控制器遇到严重错误时，需要执行重置操作来恢复正常状态。

重置过程包括以下步骤：
1. 设置 CC.EN 为 0 禁用控制器
2. 等待 CSTS.RDY 变为 0
3. 重新初始化控制器
4. 设置 CC.EN 为 1 启用控制器
...
提取到 9 个关键词: ['NVMe 控制器', 'NVMe Reset', '控制器重置', 'CC.EN', 'CSTS.RDY', '错误恢复', '重置操作', '重新初始化', '控制器状态']
============================================================
```

**说明**：
- 显示文本长度和预览
- 显示提取到的所有关键词
- 这些关键词将用于后续的代码和文档检索

### 2. 代码检索日志

```
================================================================================
开始检索相关上下文
================================================================================

[代码检索] 开始检索代码库
  配置信息:
    - 基础目录: .
    - 文件类型: ['**/*.py', '**/*.js', '**/*.ts']
    - 排除目录: ['.venv', 'node_modules', '__pycache__', '.git']
    - 上下文行数: 3
    - 最大结果数: 5

  将搜索 5 个关键词: ['NVMe 控制器', 'NVMe Reset', '控制器重置', 'CC.EN', 'CSTS.RDY']

  [1/5] 搜索关键词: 'NVMe 控制器'
      原始匹配数: 0
      过滤后代码文件匹配数: 0
      未找到匹配的代码文件

  [2/5] 搜索关键词: 'NVMe Reset'
      原始匹配数: 5
      过滤后代码文件匹配数: 2
      匹配的文件:
        - crawler\llm_client.py:92
          [OK] 已添加代码片段 (行 89-95)
        - crawler\utils\keyword_extractor.py:154
          [OK] 已添加代码片段 (行 151-157)

  [3/5] 搜索关键词: '控制器重置'
      原始匹配数: 0
      过滤后代码文件匹配数: 0
      未找到匹配的代码文件

  [代码检索] 完成，共收集 4 个代码片段
```

**说明**：
- **配置信息**：显示代码检索的配置（目录、文件类型、排除目录等）
- **搜索关键词**：显示将要搜索的关键词列表
- **每个关键词的搜索结果**：
  - 原始匹配数：在所有文件中找到的匹配数
  - 过滤后匹配数：只保留代码文件（.py, .js, .ts 等）的匹配数
  - 匹配的文件：显示具体的文件路径和行号
  - [OK] 标记：表示成功添加该代码片段

### 3. 文档检索日志

```
[文档检索] 开始检索需求文档
  配置信息:
    - 文档目录: sources/
    - 文件类型: ['*.md']
    - 排除文件: ['README.md']
    - 上下文行数: 5
    - 最大结果数: 5

  将搜索 5 个关键词: ['NVMe 控制器', 'NVMe Reset', '控制器重置', 'CC.EN', 'CSTS.RDY']

  [1/5] 搜索关键词: 'NVMe 控制器'
      原始匹配数: 3
      过滤后文档文件匹配数: 3
      匹配的文件:
        - sources\confluence\MFS\NVMe_Architecture.md:45
          [OK] 已添加文档片段 (行 42-48)
        - sources\confluence\MFS\Error_Handling.md:23
          [OK] 已添加文档片段 (行 20-26)

  [2/5] 搜索关键词: 'NVMe Reset'
      原始匹配数: 2
      过滤后文档文件匹配数: 2
      匹配的文件:
        - sources\confluence\MFS\NVMe_Reset_Flow.md:12
          [OK] 已添加文档片段 (行 9-15)

  [文档检索] 完成，共收集 5 个文档片段
```

**说明**：
- **配置信息**：显示文档检索的配置（目录、文件类型、排除文件等）
- **搜索过程**：与代码检索类似，显示每个关键词的搜索结果
- **匹配的文档**：显示找到的 Markdown 文档及其位置

### 4. 去重和总结日志

```
[去重处理]
  去重前: 代码片段 6 个, 文档片段 7 个
  去重后: 代码片段 4 个, 文档片段 5 个
  代码片段超过限制，截取前 5 个

[检索总结]
  最终返回: 代码片段 4 个, 文档片段 5 个
  代码片段来源文件:
    - crawler\llm_client.py:89-95 (关键词: NVMe Reset)
    - crawler\utils\keyword_extractor.py:151-157 (关键词: NVMe Reset)
    - crawler\utils\keyword_extractor.py:134-140 (关键词: 控制器)
    - crawler\utils\keyword_extractor.py:150-156 (关键词: 控制器)
  文档片段来源文件:
    - sources\confluence\MFS\NVMe_Architecture.md:42-48 (关键词: NVMe 控制器)
    - sources\confluence\MFS\Error_Handling.md:20-26 (关键词: NVMe 控制器)
    - sources\confluence\MFS\NVMe_Reset_Flow.md:9-15 (关键词: NVMe Reset)
    - sources\confluence\MFS\Controller_States.md:15-21 (关键词: CC.EN)
    - sources\confluence\MFS\Status_Register.md:30-36 (关键词: CSTS.RDY)
================================================================================
```

**说明**：
- **去重处理**：移除重复的代码片段（相同文件、相同行号范围）
- **最终结果**：显示最终返回给 LLM 的代码片段和文档片段
- **来源文件**：列出所有片段的来源文件、行号和匹配的关键词

## 如何查看详细日志

### 方法 1：使用 Python 脚本（推荐）

```python
import logging
import sys
from crawler.doc_analyzer import DocumentAnalyzer

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 创建分析器并运行
analyzer = DocumentAnalyzer('config.yaml')
result = analyzer.analyze_document('your_document.md')
print(f'\n报告已生成: {result}')
```

### 方法 2：修改配置文件

在 `config.yaml` 中设置日志级别：

```yaml
logging:
  level: INFO              # 设置为 INFO 显示详细日志
  format: text             # 使用文本格式（更易读）
  output_file: null        # 输出到控制台
```

### 方法 3：使用环境变量

```bash
# Windows
set PYTHONIOENCODING=utf-8
python cli.py analyze-doc your_document.md

# Linux/Mac
PYTHONIOENCODING=utf-8 python cli.py analyze-doc your_document.md
```

## 日志级别说明

- **INFO**：显示所有详细日志（关键词提取、检索过程、匹配结果）
- **WARNING**：只显示警告和错误（检索失败、文件不存在等）
- **ERROR**：只显示错误信息

## 检索过程详解

### 1. 关键词提取

使用 `KeywordExtractor` 从文档内容中提取关键词：
- 优先使用 LLM 提取（更智能，能识别技术术语）
- 如果 LLM 失败，回退到正则表达式提取
- 过滤停用词和无意义词汇
- 限制关键词长度（2-20 字符）

### 2. 代码检索

对每个关键词执行以下操作：
1. 在代码库中搜索包含该关键词的文件
2. 过滤出代码文件（.py, .js, .ts, .java, .c, .cpp, .go, .rs）
3. 提取匹配行及其上下文（默认前后 3 行）
4. 每个关键词最多保留 2 个匹配结果

### 3. 文档检索

对每个关键词执行以下操作：
1. 在文档目录中搜索包含该关键词的 Markdown 文件
2. 提取匹配行及其上下文（默认前后 5 行）
3. 每个关键词最多保留 2 个匹配结果

### 4. 去重和限制

1. 去除重复的代码片段（相同文件、相同行号范围）
2. 去除重复的文档片段
3. 限制最终结果数量（默认最多 5 个代码片段 + 5 个文档片段）

## 配置检索行为

在 `config.yaml` 中可以调整检索配置：

```yaml
doc_analysis:
  retrieval:
    # 代码库检索
    code:
      enabled: true              # 是否启用代码检索
      base_dir: .                # 代码库根目录
      patterns:                  # 搜索的文件类型
        - "**/*.py"
        - "**/*.js"
        - "**/*.ts"
      exclude_dirs:              # 排除的目录
        - ".venv"
        - "node_modules"
        - "__pycache__"
        - ".git"
      context_lines: 3           # 匹配行的前后上下文行数

    # 需求文档检索
    docs:
      enabled: true              # 是否启用文档检索
      path: "sources/"           # 需求文档目录
      patterns:
        - "*.md"
      exclude_files:             # 排除的文件
        - "README.md"
      context_lines: 5           # 匹配行的前后上下文行数

    # 检索策略
    search:
      max_results: 5             # 每个来源最多返回 N 个结果
      min_match_length: 3        # 最小匹配关键词长度
```

## 常见问题

### Q1: 为什么有些关键词没有找到匹配？

**原因**：
- 关键词可能是中文，但代码库主要是英文
- 关键词太通用（如"系统"、"功能"），被过滤掉了
- 代码库中确实没有相关代码

**解决方法**：
- 检查关键词提取是否准确
- 调整 `min_match_length` 参数
- 手动添加更具体的关键词

### Q2: 为什么检索到的代码片段不相关？

**原因**：
- 关键词匹配是基于文本搜索，不是语义搜索
- 可能匹配到注释或文档字符串中的关键词

**解决方法**：
- 使用更具体的技术术语作为关键词
- 增加 `context_lines` 查看更多上下文
- 在报告中人工筛选相关片段

### Q3: 检索速度太慢怎么办？

**原因**：
- 代码库太大
- 关键词太多
- 每个关键词匹配结果太多

**解决方法**：
- 减少 `max_results` 参数
- 添加更多 `exclude_dirs` 排除无关目录
- 使用更精确的 `patterns` 限制文件类型

### Q4: 日志输出乱码怎么办？

**原因**：
- Windows 控制台默认使用 GBK 编码
- 日志中包含 UTF-8 字符

**解决方法**：
- 设置环境变量：`set PYTHONIOENCODING=utf-8`
- 使用 PowerShell 而不是 CMD
- 将日志输出到文件：`python cli.py analyze-doc doc.md > log.txt`

## 调试技巧

### 1. 查看原始搜索结果

在 `_retrieve_context` 方法中添加断点，查看 `matches` 变量：

```python
matches = self.code_searcher.search(
    query=keyword,
    file_type='all',
    context_lines=code_context_lines,
    use_regex=False,
    max_results=max_results
)
print(f"DEBUG: matches = {matches}")  # 添加调试输出
```

### 2. 测试关键词提取

单独测试关键词提取功能：

```python
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.llm_client import LLMClientFactory

llm_client = LLMClientFactory.create_from_config({
    'provider': 'openai',
    'base_url': 'http://127.0.0.1:8080/v1',
    'model': 'Qwen3.5-9B-IQ4_XS.gguf'
})

extractor = KeywordExtractor(llm_client=llm_client)
keywords = extractor.extract_from_text(
    text="你的文档内容",
    context="document"
)
print(f"提取的关键词: {keywords}")
```

### 3. 测试代码搜索

单独测试代码搜索功能：

```python
from crawler.searcher import ContentSearcher

searcher = ContentSearcher(source_dir='.')
matches = searcher.search(
    query='NVMe',
    file_type='all',
    context_lines=3,
    max_results=10
)

for match in matches:
    print(f"{match.file_path}:{match.line_number}")
    print(f"  {match.line_content}")
```

## 总结

通过详细的日志输出，你可以：
1. **了解检索过程**：看到每个关键词的搜索结果
2. **调试问题**：发现为什么某些内容没有被检索到
3. **优化配置**：根据日志调整检索参数
4. **验证结果**：确认检索到的代码和文档是否相关

如果遇到问题，请查看日志输出，通常能找到问题的根源。
