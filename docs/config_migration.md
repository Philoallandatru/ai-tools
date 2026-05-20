# 配置文件整合说明

## 变更概述

将原本独立的 `configs/doc_analysis_config.yaml` 整合到主配置文件 `config.yaml` 中，统一管理所有配置项。

## 主要变更

### 1. LLM 配置统一

**之前**：
- 主配置文件：`config.yaml` 中的 `llm.timeout: 600`
- 文档分析配置：`configs/doc_analysis_config.yaml` 中的 `llm.timeout: 120`

**现在**：
```yaml
llm:
  provider: openai
  base_url: http://127.0.0.1:8080/v1
  model: Qwen3.5-9B-IQ4_XS.gguf
  timeout: 600  # 默认超时时间
  
  # 文档分析专用配置（覆盖默认值）
  doc_analysis:
    provider: llamacpp
    base_url: http://127.0.0.1:8080
    model: Qwen3.5-9B-IQ4_XS.gguf
    timeout: 120  # 文档分析超时时间
    temperature: 0.3
  
  # Vision LLM 配置
  vision:
    enabled: true
    provider: llamacpp
    base_url: http://127.0.0.1:9090
    model: Qwen3-VL-4B-Instruct-Q4_K_M.gguf
    timeout: 120
    temperature: 0.3
    max_tokens: 1000
```

### 2. 代码库路径配置化

**之前**：代码库路径硬编码在 `DocumentAnalyzer` 中
```python
self.code_searcher = ContentSearcher(source_dir='.')  # 硬编码
```

**现在**：从配置文件读取
```yaml
doc_analysis:
  retrieval:
    code:
      enabled: true
      base_dir: .  # 可配置的代码库根目录
      patterns:
        - "**/*.py"
        - "**/*.js"
        - "**/*.ts"
```

### 3. 配置文件结构

主配置文件 `config.yaml` 新增 `doc_analysis` 顶级配置节：

```yaml
doc_analysis:
  # 文档切分配置
  splitting:
    split_level: 2
    max_chars: 5000

  # 检索配置
  retrieval:
    code:
      enabled: true
      base_dir: .
      patterns: [...]
      exclude_dirs: [...]
    docs:
      enabled: true
      path: "sources/"
      patterns: [...]

  # Prompt 模板
  prompts:
    system: |
      ...
    keyword_extraction: |
      ...
    user_template: |
      ...
    image_analysis: |
      ...

  # 报告配置
  report:
    output_dir: "reports/"
    filename_template: "doc_analysis_{source_filename}_{timestamp}.md"
```

## 代码变更

### 1. DocumentAnalyzer 类

**文件**：`crawler/doc_analyzer.py`

**变更**：
- 默认配置路径从 `configs/doc_analysis_config.yaml` 改为 `config.yaml`
- 支持从主配置文件提取 `doc_analysis` 配置节
- 代码库路径从配置读取而非硬编码
- 兼容旧的独立配置文件格式

```python
def __init__(self, config_path: str = "config.yaml"):
    """默认使用主配置文件"""
    ...

def _load_config(self) -> Dict[str, Any]:
    """
    加载配置文件
    - 如果是主配置文件，提取 doc_analysis 部分
    - 如果是旧格式，直接使用
    """
    ...
```

### 2. CLI 命令

**文件**：`cli.py`

**变更**：
```python
@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
def analyze_doc(doc_path, config, output, dry_run):
    ...
```

### 3. 批量分析脚本

**文件**：`batch_analyze.py`

**变更**：
```python
config_path = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
```

### 4. 测试文件

**文件**：
- `tests/test_file_type_validation.py`
- `tests/integration/test_code_search.py`
- `tests/integration/test_llm_keywords.py`

**变更**：所有测试默认使用 `config.yaml`

## 向后兼容性

### 保留旧配置文件

`configs/doc_analysis_config.yaml` 文件保留，但不再是默认配置。

### 兼容性支持

`DocumentAnalyzer._load_config()` 方法支持两种格式：
1. **主配置文件**：自动提取 `doc_analysis` 配置节
2. **独立配置文件**：直接使用整个文件内容

### 迁移路径

用户可以选择：
1. **推荐**：使用新的主配置文件 `config.yaml`
2. **兼容**：继续使用旧配置文件，显式指定路径：
   ```bash
   python cli.py analyze-doc doc.md --config configs/doc_analysis_config.yaml
   ```

## 优势

### 1. 配置集中管理
- 所有配置在一个文件中，便于维护
- 避免配置分散导致的不一致

### 2. 灵活的超时配置
- 不同场景可以使用不同的超时时间
- 文档分析（120秒）vs 报告生成（600秒）

### 3. 路径可配置
- 代码库路径不再硬编码
- 支持多项目、多环境配置

### 4. 更好的可扩展性
- 新增配置项只需修改一个文件
- 配置结构清晰，易于理解

## 验证

### 测试配置加载

```bash
python -c "
from crawler.doc_analyzer import DocumentAnalyzer
analyzer = DocumentAnalyzer('config.yaml')
print(f'Split level: {analyzer.config[\"splitting\"][\"split_level\"]}')
print(f'LLM timeout: {analyzer.config[\"llm\"][\"timeout\"]}')
print(f'Code base: {analyzer.config[\"retrieval\"][\"code\"][\"base_dir\"]}')
"
```

### 测试 CLI 命令

```bash
# 使用默认配置（config.yaml）
python cli.py analyze-doc test.md --dry-run

# 使用旧配置文件（兼容性）
python cli.py analyze-doc test.md --config configs/doc_analysis_config.yaml --dry-run
```

## 注意事项

1. **配置文件位置**：确保 `config.yaml` 在项目根目录
2. **LLM 配置优先级**：`llm.doc_analysis` 会覆盖 `llm` 的默认值
3. **路径配置**：相对路径基于项目根目录
4. **测试更新**：所有测试已更新为使用新配置路径

## 后续工作

1. 考虑废弃 `configs/doc_analysis_config.yaml`（在几个版本后）
2. 添加配置验证和默认值处理
3. 考虑支持环境变量覆盖配置
