# 文档分析系统设计文档

## 概述

文档分析系统是一个基于 LLM 的批量文档处理工具，用于分析客户需求文档，判断内容是否可以形成功能需求或测试用例，并提供基于代码库和历史文档的上下文建议。

## 需求总结

### 核心功能
- **输入**：客户需求文档（Markdown 格式），已按标题层级切分成小节
- **处理流程**：对每个小节执行以下步骤（串行）：
  1. 使用正则表达式/模式匹配从代码库和需求文档中检索相似内容
  2. 提取匹配代码段及其上下文（前后 N 行）
  3. 将小节内容 + 检索到的上下文 + 自定义 prompt 发送给 LLM
  4. 获取 LLM 的 Markdown 格式分析结果
- **输出**：单个 Markdown 报告文件，包含所有小节的分析结果

### 技术特性
- **Prompt 管理**：通过 YAML 配置文件定义 prompt 模板
- **检索策略**：正则表达式或模式匹配（不使用 embedding）
- **上下文传递**：只传递匹配片段 + 上下文行，不传递完整文件
- **错误处理**：任何 LLM 调用失败立即停止整个流程
- **执行模式**：全自动批量处理，无需人工干预

### 典型使用场景
分析客户需求文档的某个小节，判断"这个内容是否可以形成 requirement 或 testcase 步骤"，并参考代码库和其他需求文档中的相似内容给出建议。

## 假设条件

- **文档切分**：使用现有的 `doc_splitter.py` 工具完成
- **上下文行数**：默认前后各 3-5 行（可配置）
- **检索范围**：代码库指 `*.py` 等源代码文件，需求文档指 `sources/` 目录下的 `.md` 文件
- **LLM 提供商**：复用现有的 llmstudio 配置
- **报告位置**：保存到 `reports/` 目录

---

## 架构设计

### 方案选择：CLI 命令 + 独立模块

**架构**：
- 新增 CLI 命令：`uv run python cli.py analyze-doc <file> --config <config.yaml>`
- 新增模块：`crawler/doc_analyzer.py`（核心分析逻辑）
- 配置文件：`configs/doc_analysis_config.yaml`（prompt 模板 + 检索规则）
- 复用现有：`doc_splitter.py`（文档切分）、`searcher.py`（检索）

**优点**：
- 与现有架构一致（参考 `analyze-jira` 命令）
- 模块职责清晰，易于测试和维护
- 配置与代码分离，灵活性高
- 可以独立使用，也可以集成到其他工作流

### 文件结构

```
ai-tools/
├── crawler/
│   └── doc_analyzer.py          # 新增：文档分析核心模块
├── configs/
│   └── doc_analysis_config.yaml # 新增：分析配置文件
├── cli.py                        # 修改：新增 analyze-doc 命令
└── reports/                      # 已存在：报告输出目录
    └── doc_analysis_*.md         # 生成的分析报告
```

### 核心流程

```
1. 用户执行命令
   ↓
2. 读取并切分 Markdown 文档（复用 doc_splitter）
   ↓
3. 对每个小节：
   3.1 提取关键词/模式
   3.2 检索代码库和需求文档（复用 searcher）
   3.3 构建 prompt（小节内容 + 检索上下文 + 模板）
   3.4 调用 LLM
   3.5 收集结果
   ↓
4. 合并所有小节的分析结果
   ↓
5. 生成 Markdown 报告
```

---

## 配置文件设计

### `configs/doc_analysis_config.yaml`

```yaml
# 文档切分配置
splitting:
  split_level: 2              # 按 H2 标题切分
  max_chars: 5000             # 单个小节最大字符数
  
# 检索配置
retrieval:
  # 代码库检索
  code:
    enabled: true
    patterns:                 # 文件类型
      - "**/*.py"
      - "**/*.js"
      - "**/*.ts"
    exclude_dirs:             # 排除目录
      - ".venv"
      - "node_modules"
      - "__pycache__"
    context_lines: 3          # 匹配行的前后上下文行数
    
  # 需求文档检索
  docs:
    enabled: true
    path: "sources/"          # 需求文档目录
    patterns:
      - "*.md"
    exclude_files:            # 排除文件
      - "README.md"
    context_lines: 5
    
  # 检索策略
  search:
    max_results: 5            # 每个来源最多返回 N 个结果
    min_match_length: 3       # 最小匹配关键词长度
    
# LLM 配置
llm:
  provider: "llmstudio"       # llmstudio 或 mock
  model: "qwen3.5-4b"
  timeout: 120
  temperature: 0.3
  
# Prompt 模板
prompts:
  system: |
    你是一个需求分析专家。你的任务是分析客户需求文档的内容，判断是否可以形成具体的需求或测试用例。
    
  user_template: |
    ## 当前文档小节
    
    {section_content}
    
    ## 相关代码参考
    
    {code_context}
    
    ## 相关需求文档参考
    
    {docs_context}
    
    ## 分析任务
    
    请分析上述文档小节内容，回答以下问题：
    1. 这个内容是否可以形成明确的功能需求（Requirement）？
    2. 这个内容是否可以形成具体的测试用例步骤（Test Case）？
    3. 参考相关代码和文档，给出你的分析建议。
    
    请以 Markdown 格式输出分析结果。

# 报告配置
report:
  output_dir: "reports/"
  filename_template: "doc_analysis_{source_filename}_{timestamp}.md"
  include_toc: true           # 是否包含目录
  include_summary: true       # 是否包含总结
```

---

## 核心模块设计

### `crawler/doc_analyzer.py`

#### 主要类和方法

```python
class DocumentAnalyzer:
    """文档分析器"""
    
    def __init__(self, config_path: str):
        """初始化分析器
        
        Args:
            config_path: 配置文件路径
        """
        
    def analyze_document(self, doc_path: str) -> str:
        """分析文档并生成报告
        
        Args:
            doc_path: 文档路径
            
        Returns:
            生成的报告文件路径
        """
        
    def _split_document(self, doc_path: str) -> List[DocumentSection]:
        """切分文档（复用 doc_splitter）"""
        
    def _retrieve_context(self, section: DocumentSection) -> RetrievalContext:
        """检索相关上下文
        
        Returns:
            RetrievalContext(code_snippets, doc_snippets)
        """
        
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词用于检索"""
        
    def _build_prompt(self, section: DocumentSection, context: RetrievalContext) -> str:
        """构建 LLM prompt"""
        
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（复用 jira_analyzer 的逻辑）"""
        
    def _generate_report(self, results: List[AnalysisResult]) -> str:
        """生成最终的 Markdown 报告"""
```

#### 数据结构

```python
@dataclass
class DocumentSection:
    """文档小节"""
    title: str              # 小节标题
    content: str            # 小节内容
    level: int              # 标题层级
    index: int              # 小节序号

@dataclass
class CodeSnippet:
    """代码片段"""
    file_path: str          # 文件路径
    line_start: int         # 起始行号
    line_end: int           # 结束行号
    content: str            # 代码内容
    match_pattern: str      # 匹配的模式

@dataclass
class RetrievalContext:
    """检索上下文"""
    code_snippets: List[CodeSnippet]
    doc_snippets: List[CodeSnippet]  # 复用结构

@dataclass
class AnalysisResult:
    """分析结果"""
    section: DocumentSection
    llm_response: str       # LLM 返回的分析内容
    retrieval_context: RetrievalContext
```

---

## CLI 命令设计

### `cli.py` 新增命令

```python
@cli.command()
@click.argument('doc_path', type=click.Path(exists=True))
@click.option('--config', 
              default='configs/doc_analysis_config.yaml',
              help='配置文件路径')
@click.option('--output', 
              help='输出报告路径（可选，默认使用配置中的规则）')
@click.option('--dry-run', 
              is_flag=True,
              help='预览模式：只显示会处理哪些小节，不实际调用 LLM')
def analyze_doc(doc_path: str, config: str, output: str, dry_run: bool):
    """分析文档并生成需求/测试用例建议报告
    
    示例：
        uv run python cli.py analyze-doc sources/KAN-1.md
        uv run python cli.py analyze-doc sources/requirements.md --config my_config.yaml
        uv run python cli.py analyze-doc sources/spec.md --dry-run
    """
```

### 使用示例

```bash
# 基本使用
uv run python cli.py analyze-doc sources/KAN-1.md

# 使用自定义配置
uv run python cli.py analyze-doc sources/requirements.md --config custom_config.yaml

# 预览模式（不调用 LLM）
uv run python cli.py analyze-doc sources/spec.md --dry-run

# 指定输出路径
uv run python cli.py analyze-doc sources/doc.md --output reports/my_analysis.md
```

---

## 报告格式设计

### 生成的 Markdown 报告结构

```markdown
# 文档分析报告

**源文档**: sources/KAN-1.md  
**分析时间**: 2026-05-11 15:30:45  
**配置文件**: configs/doc_analysis_config.yaml  
**LLM 模型**: qwen3.5-4b

---

## 目录

- [第 1 节：问题描述](#第-1-节问题描述)
- [第 2 节：复现步骤](#第-2-节复现步骤)
- [第 3 节：预期行为](#第-3-节预期行为)
- [总结](#总结)

---

## 第 1 节：问题描述

### 原始内容

> NVMe 设备在执行 CC.EN=0 后，CSTS.RDY 状态位未能在规定时间内变为 0...

### 检索到的相关上下文

#### 代码参考 (2 个匹配)

**文件**: `tests/nvme_reset_test.py:45-52`
```python
def test_nvme_reset_timeout():
    # 设置 CC.EN = 0
    controller.write_register(CC, 0)
    # 等待 CSTS.RDY
    timeout = wait_for_ready(controller, timeout=5000)
```

**文件**: `firmware/nvme_controller.c:128-135`
```c
// Wait for CSTS.RDY after CC.EN cleared
while (timeout_ms > 0) {
    if (!(read_csts() & CSTS_RDY)) break;
    delay_ms(10);
    timeout_ms -= 10;
}
```

#### 需求文档参考 (1 个匹配)

**文件**: `sources/NVMe Spec.md:234-240`
> 根据 NVMe 规范 3.5.1 节，控制器必须在 CC.EN 清零后的 CSTS.TO 时间内...

### LLM 分析结果

**1. 是否可形成功能需求？**

是的。这个内容可以形成明确的功能需求：
- **需求 ID**: REQ-NVME-RESET-001
- **需求描述**: NVMe 控制器必须在 CC.EN 清零后的指定超时时间内将 CSTS.RDY 置为 0
- **优先级**: 高（涉及规范合规性）

**2. 是否可形成测试用例？**

是的。可以形成以下测试用例：
- **测试用例 ID**: TC-NVME-RESET-001
- **测试步骤**:
  1. 初始化 NVMe 控制器至就绪状态
  2. 写入 CC.EN = 0
  3. 轮询 CSTS.RDY 状态位
  4. 验证在超时时间内 CSTS.RDY 变为 0
- **预期结果**: CSTS.RDY 在规定时间内变为 0

**3. 参考分析建议**

从检索到的代码来看，现有测试代码 `nvme_reset_test.py` 已经实现了类似的测试逻辑，但超时时间设置为 5000ms。建议：
- 确认超时时间是否符合 NVMe 规范要求
- 参考固件代码中的轮询间隔（10ms），优化测试代码的轮询策略
- 补充边界条件测试（如超时场景的错误处理）

---

## 第 2 节：复现步骤

### 原始内容

> 1. 启动系统并加载 NVMe 驱动
> 2. 执行热重置命令...

### 检索到的相关上下文

...（类似结构）

### LLM 分析结果

...

---

## 总结

### 统计信息

- **总小节数**: 5
- **可形成需求的小节**: 3
- **可形成测试用例的小节**: 4
- **检索到的代码片段**: 12
- **检索到的文档片段**: 8

### 关键发现

1. 文档中 60% 的内容可以直接转化为功能需求
2. 80% 的内容可以形成测试用例步骤
3. 代码库中已有部分相关实现，建议复用现有测试框架

### 建议行动

1. 优先实现 REQ-NVME-RESET-001 等高优先级需求
2. 补充边界条件和异常场景的测试用例
3. 统一超时时间配置，确保与规范一致

---

**报告生成时间**: 2026-05-11 15:35:22  
**处理耗时**: 4 分 37 秒
```

---

## 关键实现细节

### 1. 关键词提取策略

```python
def _extract_keywords(self, text: str) -> List[str]:
    """从文本中提取关键词
    
    策略：
    1. 提取技术术语（大写缩写词，如 NVMe, CSTS, CC.EN）
    2. 提取驼峰命名或下划线命名的标识符
    3. 提取中文技术词汇（2-4 字）
    4. 过滤停用词
    """
    keywords = []
    
    # 正则模式
    patterns = [
        r'\b[A-Z]{2,}\b',                    # 大写缩写：NVMe, CSTS
        r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # 驼峰命名：ReadyState
        r'\b[a-z_]+_[a-z_]+\b',              # 下划线命名：nvme_reset
        r'[一-龥]{2,4}',             # 中文词汇
    ]
    
    for pattern in patterns:
        keywords.extend(re.findall(pattern, text))
    
    return list(set(keywords))  # 去重
```

### 2. 检索实现（复用 searcher.py）

```python
def _retrieve_context(self, section: DocumentSection) -> RetrievalContext:
    """检索相关上下文"""
    keywords = self._extract_keywords(section.content)
    
    code_snippets = []
    doc_snippets = []
    
    # 检索代码库
    if self.config['retrieval']['code']['enabled']:
        for keyword in keywords:
            results = self.searcher.search(
                keyword,
                file_types=self.config['retrieval']['code']['patterns'],
                max_results=self.config['retrieval']['search']['max_results']
            )
            code_snippets.extend(self._format_snippets(results, 'code'))
    
    # 检索需求文档
    if self.config['retrieval']['docs']['enabled']:
        for keyword in keywords:
            results = self.searcher.search(
                keyword,
                path=self.config['retrieval']['docs']['path'],
                max_results=self.config['retrieval']['search']['max_results']
            )
            doc_snippets.extend(self._format_snippets(results, 'docs'))
    
    return RetrievalContext(code_snippets, doc_snippets)
```

### 3. 错误处理

```python
def analyze_document(self, doc_path: str) -> str:
    """分析文档"""
    try:
        # 切分文档
        sections = self._split_document(doc_path)
        
        results = []
        for i, section in enumerate(sections):
            try:
                # 检索上下文
                context = self._retrieve_context(section)
                
                # 构建 prompt
                prompt = self._build_prompt(section, context)
                
                # 调用 LLM（失败时立即抛出异常）
                llm_response = self._call_llm(prompt)
                
                results.append(AnalysisResult(section, llm_response, context))
                
            except Exception as e:
                # LLM 调用失败，立即停止
                raise RuntimeError(
                    f"处理第 {i+1} 节 '{section.title}' 时失败: {str(e)}"
                ) from e
        
        # 生成报告
        return self._generate_report(results)
        
    except Exception as e:
        logger.error(f"文档分析失败: {str(e)}")
        raise
```

### 4. LLM 调用（复用 jira_analyzer）

```python
def _call_llm(self, prompt: str) -> str:
    """调用 LLM
    
    复用 jira_analyzer.py 中的 LLMClient 类
    """
    from crawler.jira_analyzer import LLMClient
    
    client = LLMClient(
        provider=self.config['llm']['provider'],
        model=self.config['llm']['model'],
        timeout=self.config['llm']['timeout']
    )
    
    response = client.chat(
        system_prompt=self.config['prompts']['system'],
        user_prompt=prompt,
        temperature=self.config['llm']['temperature']
    )
    
    return response
```

---

## 决策日志

| 决策点 | 选择 | 替代方案 | 理由 |
|--------|------|----------|------|
| 架构模式 | CLI 命令 + 独立模块 | 扩展 Jira 分析器 / 独立脚本 | 与现有架构一致，职责清晰 |
| 配置管理 | YAML 配置文件 | 硬编码 / 外部文件 | 灵活性高，易于维护 |
| 检索策略 | 正则表达式 + 关键词 | Embedding 语义搜索 | 用户明确要求，且实现简单 |
| 上下文传递 | 匹配片段 + 上下文行 | 完整文件 / 仅摘要 | 平衡信息量和 token 消耗 |
| 错误处理 | 立即停止 | 跳过失败 / 重试 | 用户明确要求 |
| 执行模式 | 串行处理 | 并行处理 | 用户明确要求，且实现简单 |
| 报告格式 | 单个 Markdown | 多文件 / 分层 | 用户明确要求 |
| LLM 客户端 | 复用 jira_analyzer | 新实现 | 避免重复代码 |

---

## 实施计划

### 阶段 1：基础设施（预计 1-2 小时）
1. 创建 `configs/` 目录
2. 创建 `configs/doc_analysis_config.yaml` 配置文件
3. 创建 `crawler/doc_analyzer.py` 模块骨架

### 阶段 2：核心功能（预计 3-4 小时）
1. 实现 `DocumentAnalyzer` 类
2. 实现关键词提取 `_extract_keywords()`
3. 实现检索逻辑 `_retrieve_context()`（复用 searcher）
4. 实现 prompt 构建 `_build_prompt()`
5. 实现 LLM 调用 `_call_llm()`（复用 jira_analyzer）

### 阶段 3：报告生成（预计 1-2 小时）
1. 实现报告生成 `_generate_report()`
2. 实现目录生成
3. 实现总结统计

### 阶段 4：CLI 集成（预计 1 小时）
1. 在 `cli.py` 中添加 `analyze-doc` 命令
2. 实现命令行参数处理
3. 实现 dry-run 模式

### 阶段 5：测试和文档（预计 1-2 小时）
1. 使用真实文档测试
2. 调整 prompt 模板
3. 更新 README.md
4. 编写使用示例

**总预计时间**: 7-11 小时

---

## 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 调用超时 | 处理中断 | 配置合理的超时时间，提供重试选项 |
| 关键词提取不准确 | 检索结果不相关 | 提供配置选项，允许手动指定关键词 |
| 报告过长 | 可读性差 | 限制每个小节的检索结果数量 |
| 配置文件复杂 | 使用门槛高 | 提供默认配置和使用示例 |

---

## 后续优化方向

1. **增量分析**：只分析变更的小节
2. **并行处理**：支持多线程/多进程加速
3. **缓存机制**：缓存 LLM 响应，避免重复调用
4. **交互模式**：支持人工确认和调整
5. **语义检索**：引入 embedding 提升检索质量
6. **多模型支持**：支持不同 LLM 提供商

---

**文档版本**: 1.0  
**创建时间**: 2026-05-11  
**最后更新**: 2026-05-11
