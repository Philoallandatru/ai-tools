# 代码质量改进 - 快速开始指南

## 🚀 5 分钟快速验证

### 步骤 1: 安装测试依赖

```bash
# 激活虚拟环境（如果还没激活）
source .venv/Scripts/activate  # Windows Git Bash
# 或
.venv\Scripts\activate  # Windows CMD

# 安装 pytest
pip install pytest pytest-cov
```

### 步骤 2: 运行测试

```bash
# 测试关键词提取器
python -m pytest tests/unit/test_keyword_extractor.py -v

# 测试统一搜索引擎
python -m pytest tests/unit/test_unified_search.py -v

# 运行所有新测试
python -m pytest tests/unit/test_keyword_extractor.py tests/unit/test_unified_search.py -v
```

### 步骤 3: 快速体验新功能

创建测试脚本 `test_improvements.py`：

```python
"""快速测试代码质量改进"""

from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine
from crawler.llm_client import MockLLMClient

# 1. 测试关键词提取
print("=" * 50)
print("测试关键词提取器")
print("=" * 50)

extractor = KeywordExtractor()
text = "NVMe Reset功能需要实现spdk_nvme_ctrlr_reset接口"
keywords = extractor.extract_from_text(text)

print(f"输入文本: {text}")
print(f"提取的关键词: {keywords}")
print()

# 2. 测试 Jira 数据提取
jira_data = {
    'title': 'NVMe FFU Download Failure',
    'description': 'The firmware update fails during download. Error in spdk_nvme_ctrlr_update_firmware.'
}

keywords = extractor.extract_from_jira(jira_data)
print(f"Jira 标题: {jira_data['title']}")
print(f"提取的关键词: {keywords}")
print()

# 3. 测试统一搜索（需要真实的源文件目录）
print("=" * 50)
print("测试统一搜索引擎")
print("=" * 50)

# 使用 Mock LLM 进行演示
mock_llm = MockLLMClient()
mock_llm.set_response('{"score": 8, "reason": "高度相关"}')

engine = UnifiedSearchEngine(
    source_dir='./sources',  # 确保这个目录存在
    llm_client=mock_llm
)

try:
    results = engine.search(
        query="NVMe controller reset implementation",
        keywords=["nvme", "reset"],
        max_results=5,
        use_llm_ranking=True
    )
    
    print(f"搜索查询: NVMe controller reset implementation")
    print(f"找到 {len(results)} 个结果:")
    
    for i, result in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"  文件: {result.file_path}")
        print(f"  相关性: {result.relevance_score}/10")
        print(f"  原因: {result.match_reason}")
        print(f"  代码片段: {result.snippet[:80]}...")
        
except Exception as e:
    print(f"搜索失败: {e}")
    print("提示: 确保 ./sources 目录存在并包含一些代码文件")

print("\n" + "=" * 50)
print("测试完成！")
print("=" * 50)
```

运行测试脚本：

```bash
python test_improvements.py
```

---

## 📖 使用示例

### 示例 1: 在 DocumentAnalyzer 中使用

```python
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine

class DocumentAnalyzer:
    def __init__(self, config, llm_client):
        # 使用新的共享模块
        self.keyword_extractor = KeywordExtractor(
            llm_client=llm_client,
            min_length=2,
            max_length=20,
            max_keywords=15
        )
        
        self.search_engine = UnifiedSearchEngine(
            source_dir=config['codebase_path'],
            llm_client=llm_client,
            cache_dir='.cache/search',
            min_relevance_score=3.0
        )
    
    def analyze_section(self, section_text):
        # 1. 提取关键词
        keywords = self.keyword_extractor.extract_from_text(
            section_text,
            context="document"
        )
        
        # 2. 搜索相关代码
        results = self.search_engine.search(
            query=section_text[:200],  # 使用前 200 字符作为查询
            keywords=keywords,
            max_results=10,
            use_llm_ranking=True
        )
        
        return {
            'keywords': keywords,
            'code_matches': results
        }
```

### 示例 2: 在 KnowledgeRetriever 中使用

```python
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine

class KnowledgeRetriever:
    def __init__(self, source_dir, wiki_dir, llm_client, config):
        # 使用新的共享模块
        self.keyword_extractor = KeywordExtractor(
            llm_client=llm_client,
            min_length=config.get('min_keyword_length', 2),
            max_length=config.get('max_keyword_length', 20),
            max_keywords=config.get('max_keywords', 15)
        )
        
        self.search_engine = UnifiedSearchEngine(
            source_dir=source_dir,
            llm_client=llm_client,
            cache_dir=config.get('cache_dir'),
            min_relevance_score=config.get('min_relevance_score', 3.0)
        )
    
    def analyze(self, jira_data):
        # 1. 提取关键词
        keywords = self.keyword_extractor.extract_from_jira(jira_data)
        
        # 2. 搜索相关源文件
        source_results = self.search_engine.search(
            query=f"{jira_data['title']} {jira_data['description'][:200]}",
            keywords=keywords,
            max_results=10,
            use_llm_ranking=True
        )
        
        return {
            'keywords': keywords,
            'related_sources': source_results
        }
```

---

## 🔧 配置建议

### config.yaml 配置示例

```yaml
# 关键词提取配置
keyword_extraction:
  min_length: 2
  max_length: 20
  max_keywords: 15

# 搜索配置
search:
  min_relevance_score: 3.0
  max_results: 10
  cache_enabled: true
  cache_dir: .cache/search
  context_lines: 3

# LLM 配置
llm:
  provider: openai
  model: gpt-4
  timeout: 120
```

---

## 🐛 常见问题

### Q1: 测试失败 - "No module named pytest"

**解决方案**：
```bash
pip install pytest pytest-cov
```

### Q2: 搜索失败 - "Source directory not found"

**解决方案**：
确保源文件目录存在：
```bash
mkdir -p sources
# 或者在配置中指定正确的路径
```

### Q3: LLM 调用失败

**解决方案**：
系统会自动回退到正则表达式提取和简单排序：
```python
# 不使用 LLM
extractor = KeywordExtractor()  # llm_client=None
engine = UnifiedSearchEngine(source_dir='./sources')  # llm_client=None
```

### Q4: 缓存问题

**解决方案**：
清除缓存：
```bash
rm -rf .cache/search
```

或禁用缓存：
```python
engine = UnifiedSearchEngine(
    source_dir='./sources',
    cache_dir=None  # 禁用缓存
)
```

---

## 📊 性能对比

### 关键词提取

| 方法 | 速度 | 质量 | 适用场景 |
|------|------|------|----------|
| 正则表达式 | 快 (< 1ms) | 中等 | 无 LLM 时 |
| LLM 提取 | 慢 (1-3s) | 高 | 有 LLM 时 |

### 搜索排序

| 方法 | 速度 | 质量 | 适用场景 |
|------|------|------|----------|
| 简单排序 | 快 (< 10ms) | 中等 | 快速搜索 |
| LLM 排序 | 慢 (每结果 1-2s) | 高 | 精确搜索 |
| LLM + 缓存 | 快 (< 10ms) | 高 | 重复查询 |

---

## ✅ 验证清单

完成以下检查确保改进正常工作：

- [ ] pytest 安装成功
- [ ] 关键词提取器测试通过
- [ ] 统一搜索引擎测试通过
- [ ] 测试脚本运行成功
- [ ] 能够提取关键词
- [ ] 能够搜索代码
- [ ] LLM 相关性分析工作正常
- [ ] 缓存机制工作正常

---

## 🎯 下一步

完成验证后，继续：

1. **集成到现有代码** - 修改 `DocumentAnalyzer` 和 `KnowledgeRetriever`
2. **运行完整测试** - 确保没有破坏现有功能
3. **性能基准测试** - 对比改进前后的效果
4. **开始 Skill 开发** - 使用新模块开发 Skills

---

**需要帮助？** 查看 `docs/code_quality_improvements.md` 获取详细信息。
