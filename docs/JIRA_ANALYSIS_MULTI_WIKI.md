# Jira Analysis 多 Wiki 适配说明

## 适配状态

✅ **已完全适配** - `analyze-jira` 命令已经完整支持多 wiki 架构

---

## 功能概览

### CLI 命令参数

```bash
python cli.py analyze-jira <issue_key> [OPTIONS]
```

**新增参数:**
- `--wiki-name TEXT` - 指定要使用的 wiki 名称
- `--wiki-mode [specify|auto_match|search_all]` - Wiki 选择模式（默认: auto_match）

**示例:**
```bash
# 自动匹配模式（默认）- 根据 Jira 项目/关键词自动选择 wiki
python cli.py analyze-jira KAN-10

# 指定特定 wiki
python cli.py analyze-jira KAN-10 --wiki-name default

# 搜索所有 wiki
python cli.py analyze-jira KAN-10 --wiki-mode search_all
```

---

## 实现细节

### 1. CLI 层 (cli.py)

**位置:** `cli.py:882-910`

```python
@cli.command()
@click.argument('issue_key')
@click.option('--wiki-name', help='指定 wiki 名称')
@click.option('--wiki-mode', type=click.Choice(['specify', 'auto_match', 'search_all']),
              default='auto_match', help='Wiki 选择模式')
def analyze_jira(issue_key, source_dir, wiki_name, wiki_mode, output_dir, llm_provider, config):
    """分析 Jira issue（支持多 wiki）"""
    # 如果指定了 wiki_name，强制使用 specify 模式
    if wiki_name and wiki_mode != 'specify':
        wiki_mode = 'specify'
    
    service = AnalysisService(config=cfg)
    report_path = service.analyze_jira(
        issue_key=issue_key,
        output_dir=output_dir,
        wiki_mode=wiki_mode,
        wiki_name=wiki_name
    )
```

**关键特性:**
- 新增 `--wiki-name` 和 `--wiki-mode` 参数
- 自动处理参数冲突（指定 wiki_name 时强制 specify 模式）
- 向后兼容：不指定参数时使用默认的 auto_match 模式

---

### 2. 服务层 (AnalysisService)

**位置:** `crawler/services/analysis_service.py:46-81`

```python
def analyze_jira(
    self,
    issue_key: str,
    wiki_mode: str = "auto_match",
    wiki_name: Optional[str] = None,
) -> JiraAnalysisResult:
    """Run Jira deep analysis and persist the markdown report."""
    analyzer = self.create_jira_analyzer(
        source_dir, wiki_dir, llm_client, wiki_mode, wiki_name
    )
    report = analyzer.analyze(issue_key)
    # ... 生成报告
```

**关键特性:**
- 接受 `wiki_mode` 和 `wiki_name` 参数
- 传递给 `create_jira_analyzer` 创建适配的分析器

---

### 3. 分析器创建 (create_jira_analyzer)

**位置:** `crawler/services/analysis_service.py:115-168`

```python
def create_jira_analyzer(
    self,
    source_dir: str,
    wiki_dir: str,
    llm_client: BaseLLMClient,
    wiki_mode: str = "auto_match",
    wiki_name: Optional[str] = None,
) -> JiraDeepAnalyzer:
    """Create and register the standard Jira analysis pipeline."""
    analyzer = JiraDeepAnalyzer(source_dir=source_dir, llm_client=llm_client)
    
    # 检查是否配置了多 wiki
    wikis_config = self.config.get("wikis", {})
    has_multi_wiki = bool(wikis_config.get("repositories", []))
    
    if has_multi_wiki:
        # 使用多 Wiki 知识检索器
        retriever = MultiWikiKnowledgeRetriever(
            wikis_root="./wikis",
            source_dir=source_dir,
            llm_client=llm_client,
            config=self.config,
        )
        
        # 包装成适配器
        class MultiWikiAdapter(BaseAnalyzer):
            def __init__(self, retriever, mode, name):
                self.retriever = retriever
                self.mode = mode
                self.wiki_name = name
            
            def analyze(self, jira_data, context):
                return self.retriever.analyze(
                    jira_data, context, 
                    mode=self.mode, 
                    wiki_name=self.wiki_name
                )
        
        analyzer.register_analyzer(MultiWikiAdapter(retriever, wiki_mode, wiki_name))
    else:
        # 使用单 Wiki 知识检索器（向后兼容）
        analyzer.register_analyzer(
            KnowledgeRetriever(
                source_dir=source_dir,
                wiki_dir=wiki_dir,
                llm_client=llm_client,
                config=self.config,
            )
        )
```

**关键特性:**
- **自动检测:** 检查 config.yaml 中是否配置了多 wiki
- **智能切换:** 
  - 有多 wiki 配置 → 使用 `MultiWikiKnowledgeRetriever`
  - 无多 wiki 配置 → 使用传统的 `KnowledgeRetriever`
- **适配器模式:** 使用 `MultiWikiAdapter` 将 `MultiWikiKnowledgeRetriever` 适配到 `BaseAnalyzer` 接口
- **向后兼容:** 完全兼容单 wiki 模式

---

## 三种 Wiki 模式详解

### 1. auto_match (自动匹配) - 默认模式

**工作原理:**
1. 提取 Jira issue 的项目键（如 KAN-10 → KAN）
2. 检查标题和描述中的关键词
3. 按优先级匹配：
   - Jira 项目键 > 关键词 > Confluence Space
4. 未匹配到则使用默认 wiki

**适用场景:**
- 日常使用，让系统自动选择最相关的 wiki
- 多个项目使用不同的 wiki

**示例:**
```bash
# KAN-10 会自动匹配到配置了 jira_projects: [KAN] 的 wiki
python cli.py analyze-jira KAN-10
```

**配置示例 (config.yaml):**
```yaml
wikis:
  repositories:
    - name: default
      auto_match:
        jira_projects: [KAN, NVME]
        keywords: [nvme, firmware, ssd]
```

---

### 2. specify (指定模式)

**工作原理:**
- 直接使用 `--wiki-name` 指定的 wiki
- 不进行任何自动匹配

**适用场景:**
- 明确知道要使用哪个 wiki
- 覆盖自动匹配的结果
- 测试特定 wiki 的内容

**示例:**
```bash
# 强制使用 default wiki
python cli.py analyze-jira KAN-10 --wiki-name default

# 或者使用 --wiki-mode specify（效果相同）
python cli.py analyze-jira KAN-10 --wiki-name default --wiki-mode specify
```

---

### 3. search_all (搜索所有)

**工作原理:**
1. 并行搜索所有配置的 wiki
2. 计算每个 wiki 的相关性评分
3. 按相关性排序返回结果
4. 合并所有相关的知识

**适用场景:**
- 跨项目的问题分析
- 不确定知识在哪个 wiki
- 需要全局视角

**示例:**
```bash
# 搜索所有 wiki 并合并结果
python cli.py analyze-jira KAN-10 --wiki-mode search_all
```

**性能考虑:**
- 搜索时间 = 单个 wiki 搜索时间 × wiki 数量
- 建议在 wiki 数量较少（<5个）时使用

---

## 输出示例

### 自动匹配模式输出

```markdown
# Jira Issue Analysis: KAN-10

## 知识库检索结果

**使用的 Wiki:** default (自动匹配)
**匹配原因:** Jira 项目 KAN

### 相关概念

1. **NVMe Protocol** (置信度: 0.95)
   - NVMe (Non-Volatile Memory Express) is a high-performance storage protocol...
   - 来源: test-doc-1.md

2. **PCIe Interface** (置信度: 0.87)
   - PCIe provides direct CPU connection...
   - 来源: test-doc-1.md
```

### 搜索所有模式输出

```markdown
# Jira Issue Analysis: KAN-10

## 知识库检索结果

**搜索模式:** 搜索所有 wiki
**搜索的 Wiki:** default, test-wiki, project-b

### 来自 default wiki (相关性: 0.92)

1. **NVMe Protocol** (置信度: 0.95)
   - ...

### 来自 test-wiki wiki (相关性: 0.45)

1. **Kubernetes Pods** (置信度: 0.50)
   - ...
```

---

## 向后兼容性

### 单 Wiki 模式（无 wikis 配置）

如果 config.yaml 中没有配置 `wikis` 节点，系统会自动回退到传统的单 wiki 模式：

```yaml
# 传统配置（仍然支持）
output:
  base_dir: ./sources

# 没有 wikis 配置
```

**行为:**
- 使用传统的 `KnowledgeRetriever`
- 从 `./wiki` 目录读取知识库
- `--wiki-name` 和 `--wiki-mode` 参数被忽略

---

## 测试状态

### 已测试 ✅
- ✅ CLI 参数解析
- ✅ 多 wiki 自动检测
- ✅ MultiWikiAdapter 适配器
- ✅ 向后兼容（单 wiki 模式）

### 需要实际数据测试 ⊘
- ⊘ auto_match 模式的实际匹配效果
- ⊘ specify 模式的知识检索
- ⊘ search_all 模式的并行搜索和结果合并
- ⊘ 生成的分析报告格式

### 手动测试方法

```bash
# 1. 确保有实际的 Jira issue 数据
python cli.py sync  # 同步 Jira 数据

# 2. 测试自动匹配
python cli.py analyze-jira KAN-10

# 3. 测试指定 wiki
python cli.py analyze-jira KAN-10 --wiki-name default

# 4. 测试搜索所有
python cli.py analyze-jira KAN-10 --wiki-mode search_all

# 5. 查看生成的报告
ls -la reports/jira_analysis_KAN-10_*.md
```

---

## 配置示例

### 完整的多 Wiki 配置

```yaml
# config.yaml

sources:
  jira:
    - name: sakiko222-jira
      url: https://sakiko222.atlassian.net
      projects:
        - key: KAN

wikis:
  default_wiki: default
  
  repositories:
    - name: default
      display_name: Default Wiki
      description: NVMe firmware knowledge base
      path: ./wikis/default
      auto_match:
        jira_projects: [KAN, NVME]
        confluence_spaces: [MFS]
        keywords: [nvme, firmware, ssd, pcie]
      compilation:
        batch_size: 5
        auto_compile: true
    
    - name: cloud-infra
      display_name: Cloud Infrastructure
      description: Kubernetes and Docker knowledge
      path: ./wikis/cloud-infra
      auto_match:
        jira_projects: [CLOUD, INFRA]
        keywords: [kubernetes, docker, aws, cloud]
      compilation:
        batch_size: 5
        auto_compile: true

jira_analysis:
  issue_summary:
    enabled: true
    use_llm: true
```

---

## 总结

### ✅ 已完成的适配

1. **CLI 层:** 新增 `--wiki-name` 和 `--wiki-mode` 参数
2. **服务层:** `analyze_jira()` 方法支持多 wiki 参数
3. **分析器层:** `create_jira_analyzer()` 自动检测并使用多 wiki
4. **适配器:** `MultiWikiAdapter` 桥接新旧接口
5. **向后兼容:** 无 wikis 配置时自动回退到单 wiki 模式

### 🎯 核心优势

- **零配置升级:** 添加 wikis 配置后自动启用多 wiki
- **智能匹配:** 自动根据 Jira 项目和关键词选择最相关的 wiki
- **灵活控制:** 支持手动指定或全局搜索
- **完全兼容:** 不影响现有的单 wiki 用户

### 📋 使用建议

1. **日常使用:** 使用默认的 auto_match 模式
2. **特定场景:** 使用 --wiki-name 指定 wiki
3. **跨项目分析:** 使用 --wiki-mode search_all
4. **性能优化:** 合理配置 auto_match 规则，减少 search_all 使用

---

**文档版本:** 1.0  
**最后更新:** 2026-05-15  
**适配状态:** ✅ 完全适配
