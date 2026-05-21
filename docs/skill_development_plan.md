# Skill 开发任务规划

## 📅 创建日期
2026-05-20

## 🎯 目标
将项目中的核心流程转换为 Claude Code Skills，提升自动化程度和用户体验。

---

## 📋 Skill 优先级列表

### 🥇 高优先级 Skills（立即开始）

#### 1. `/analyze-requirements` - 智能需求分析 Skill

**任务 ID**: #41

**优先级**: ⭐⭐⭐⭐⭐ 最高

**为什么需要这个 Skill**：
- 最常用的功能
- 当前流程需要 3 个独立命令（convert-pdf → split-doc → analyze-doc）
- 用户体验差，中间文件管理麻烦
- 多步骤决策流程适合 Skill

**功能描述**：
端到端分析需求文档（PDF/Markdown），自动完成：
1. PDF 转 Markdown（如果需要）
2. 智能拆分文档
3. 提取关键词
4. 搜索相关代码
5. LLM 相关性分析
6. 生成分析报告

**输入**：
- 需求文档路径（PDF 或 Markdown）
- 代码库路径（可选，默认当前目录）
- 配置文件（可选）

**输出**：
- 分析报告（Markdown）
- 关键词列表
- 代码匹配结果（带相关性评分）
- 实现建议

**技术实现**：
```python
# Skill 结构
~/.claude/skills/analyze-requirements/
├── skill.md              # Skill 定义
├── prompts/
│   ├── extract_keywords.md
│   ├── analyze_relevance.md
│   └── generate_report.md
├── utils/
│   └── helpers.py
└── tests/
    ├── test_pdf_analysis.py
    └── test_code_matching.py
```

**使用示例**：
```bash
# 基础用法
/analyze-requirements docs/requirements.pdf

# 指定代码库
/analyze-requirements docs/requirements.pdf --codebase ./spdk

# 指定配置
/analyze-requirements docs/requirements.pdf --config custom_config.yaml
```

**成功标准**：
- [ ] 能够自动完成 PDF → 分析的完整流程
- [ ] 关键词提取准确率 > 80%
- [ ] 代码匹配相关性评分合理
- [ ] 生成的报告清晰易读
- [ ] 处理时间 < 5 分钟（中等大小文档）

**预计工时**: 2-3 天

---

#### 2. `/investigate-jira` - Jira Issue 深度调查 Skill

**任务 ID**: #42

**优先级**: ⭐⭐⭐⭐⭐ 最高

**为什么需要这个 Skill**：
- 核心业务功能
- 需要多轮推理（根因分析 → 相似问题 → 解决方案）
- 可以整合现有的 24 个 Analyzer
- 动态调整调查方向

**功能描述**：
深度分析 Jira Issue，自动完成：
1. 提取问题关键信息
2. 根因分析
3. 搜索相似历史问题
4. 检索相关知识（Wiki + 代码）
5. 生成解决方案建议
6. 提供验证测试建议

**输入**：
- Jira Issue Key（如 TEST-123）
- Wiki 目录（可选）
- 配置文件（可选）

**输出**：
- 调查报告（Markdown）
- 根因分析
- 相似问题列表
- 解决方案建议
- 验证测试建议

**技术实现**：
```python
# Skill 会自动编排这些 Analyzer
analyzers = [
    'root_cause_analyzer',      # 根因分析
    'similar_jira_finder',      # 相似问题
    'knowledge_retriever',      # 知识检索
    'action_recommender',       # 解决方案
]

# 使用新的共享模块
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine
```

**使用示例**：
```bash
# 基础用法
/investigate-jira TEST-123

# 指定 Wiki
/investigate-jira TEST-123 --wiki my-wiki

# 深度调查模式
/investigate-jira TEST-123 --depth thorough
```

**成功标准**：
- [ ] 能够自动完成完整的调查流程
- [ ] 根因分析准确率 > 70%
- [ ] 找到相似问题 > 3 个
- [ ] 解决方案建议可操作
- [ ] 处理时间 < 3 分钟

**预计工时**: 3-4 天

---

### 🥈 中优先级 Skills（1-2周后）

#### 3. `/smart-search` - 智能语义搜索 Skill

**任务 ID**: #43

**优先级**: ⭐⭐⭐⭐ 高

**为什么需要这个 Skill**：
- 统一搜索质量
- 提供更好的用户体验
- 支持自然语言查询
- 多轮细化搜索

**功能描述**：
智能搜索代码和文档：
1. 理解自然语言查询
2. 提取搜索关键词
3. 执行多源搜索（代码 + 文档 + Wiki）
4. LLM 相关性排序
5. 支持交互式细化

**输入**：
- 自然语言查询
- 搜索范围（code/docs/wiki/all）
- 最大结果数

**输出**：
- 搜索结果列表（按相关性排序）
- 每个结果的相关性评分和原因
- 代码片段预览

**技术实现**：
```python
# 使用统一搜索引擎
from crawler.utils.unified_search import UnifiedSearchEngine

engine = UnifiedSearchEngine(
    source_dir='./sources',
    llm_client=llm_client,
    cache_dir='.cache/search',
    min_relevance_score=3.0
)
```

**使用示例**：
```bash
# 自然语言搜索
/smart-search "How to reset NVMe controller"

# 限制搜索范围
/smart-search "memory leak" --scope code

# 细化搜索
/smart-search "buffer overflow" --refine "in download function"
```

**成功标准**：
- [ ] 理解自然语言查询
- [ ] 搜索结果相关性 > 80%
- [ ] 支持多轮细化
- [ ] 响应时间 < 10 秒

**预计工时**: 2-3 天

---

#### 4. `/build-knowledge-base` - 智能知识库构建 Skill

**任务 ID**: 待创建

**优先级**: ⭐⭐⭐ 中高

**功能描述**：
智能构建和维护 Wiki 知识库：
1. 分析文档内容和关系
2. 自动发现知识缺口
3. 优化知识组织结构
4. 生成知识图谱
5. 建议补充内容

**使用示例**：
```bash
# 构建知识库
/build-knowledge-base --source ./docs

# 发现知识缺口
/build-knowledge-base --analyze-gaps

# 优化结构
/build-knowledge-base --optimize
```

**预计工时**: 3-4 天

---

#### 5. `/generate-insights` - 智能报告生成 Skill

**任务 ID**: 待创建

**优先级**: ⭐⭐⭐ 中

**功能描述**：
自动生成洞察性报告：
1. 分析数据趋势
2. 识别异常和风险
3. 根据受众调整报告风格
4. 生成可操作建议
5. 支持可视化

**使用示例**：
```bash
# 生成周报
/generate-insights --type weekly --audience tech-lead

# 生成项目健康报告
/generate-insights --type health --data jira_data.json
```

**预计工时**: 2-3 天

---

### 🥉 低优先级 Skills（按需开发）

#### 6. `/refactor-code` - 代码重构建议 Skill

**优先级**: ⭐⭐ 中低

**功能描述**：
分析代码质量并提供重构建议：
1. 分析代码复杂度
2. 识别重复代码
3. 对比需求文档和实现
4. 生成重构优先级列表

**预计工时**: 3-4 天

---

#### 7. `/sync-data` - 智能数据同步 Skill

**优先级**: ⭐⭐ 低

**功能描述**：
智能同步 Atlassian 数据：
1. 自动检测变化
2. 优先同步重要数据
3. 智能处理冲突
4. 生成同步报告

**预计工时**: 2 天

---

#### 8. `/diagnose-system` - 系统诊断 Skill

**优先级**: ⭐ 低

**功能描述**：
诊断系统配置和性能问题：
1. 检查配置完整性
2. 分析性能瓶颈
3. 验证 LLM 连接
4. 生成优化建议

**预计工时**: 1-2 天

---

## 🚀 实施计划

### 阶段 1: 核心分析 Skills（第 1-2 周）

**目标**: 实现最常用的两个 Skills

**任务**:
1. ✅ 完成代码质量改进（已完成）
   - 统一关键词提取
   - 统一搜索接口
   - 完整测试套件

2. 🔄 实现 `/analyze-requirements` Skill
   - Week 1, Day 1-3: 开发 Skill
   - Week 1, Day 4-5: 测试和优化

3. 🔄 实现 `/investigate-jira` Skill
   - Week 2, Day 1-4: 开发 Skill
   - Week 2, Day 5: 测试和优化

**交付物**:
- 2 个可用的 Skills
- 完整的测试套件
- 使用文档

---

### 阶段 2: 搜索和知识管理 Skills（第 3-4 周）

**目标**: 提升搜索质量和知识管理能力

**任务**:
1. 实现 `/smart-search` Skill
2. 实现 `/build-knowledge-base` Skill
3. 集成到现有工作流

**交付物**:
- 2 个可用的 Skills
- 性能基准测试报告
- 用户指南

---

### 阶段 3: 报告和优化 Skills（第 5-6 周，按需）

**目标**: 增强报告能力和系统优化

**任务**:
1. 实现 `/generate-insights` Skill
2. 实现其他低优先级 Skills
3. 整体优化和性能调优

**交付物**:
- 剩余 Skills
- 完整的 Skill 生态系统
- 最佳实践文档

---

## 🧪 使用 OpenCode 进行测试

### 测试策略

#### 1. 单元测试
```bash
# 测试 Skill 的各个组件
pytest tests/skills/test_analyze_requirements_unit.py -v
```

#### 2. 集成测试
```bash
# 测试 Skill 的完整流程
pytest tests/skills/test_analyze_requirements_integration.py -v
```

#### 3. OpenCode 无头模式测试
```bash
# 使用 OpenCode 测试 Skill
opencode -p "Use /analyze-requirements skill to analyze sample.pdf" \
  --agent plan \
  --output json \
  --headless
```

#### 4. 性能基准测试
```python
# tests/benchmarks/test_skill_performance.py
class SkillBenchmark:
    def benchmark_against_opencode(self, skill_name, test_cases):
        """对比 Skill 和 OpenCode 原生功能的性能"""
        # 实现基准测试逻辑
```

---

## 📊 成功指标

### 质量指标

| 指标 | 目标 | 测量方法 |
|------|------|----------|
| 准确率 | > 80% | 人工评估 + 自动测试 |
| 响应时间 | < 5 分钟 | 性能测试 |
| 用户满意度 | > 4/5 | 用户反馈 |
| 测试覆盖率 | > 80% | pytest-cov |

### 性能指标

| Skill | 目标响应时间 | 目标准确率 |
|-------|-------------|-----------|
| `/analyze-requirements` | < 5 分钟 | > 80% |
| `/investigate-jira` | < 3 分钟 | > 70% |
| `/smart-search` | < 10 秒 | > 80% |
| `/build-knowledge-base` | < 10 分钟 | > 75% |

---

## 🛠️ 技术栈

### 核心依赖
- **Claude Code SDK**: Skill 框架
- **统一关键词提取器**: `crawler.utils.keyword_extractor`
- **统一搜索引擎**: `crawler.utils.unified_search`
- **LLM 客户端**: `crawler.llm_client`

### 测试工具
- **pytest**: 单元测试和集成测试
- **OpenCode**: 无头模式测试和基准测试
- **pytest-cov**: 测试覆盖率

### 开发工具
- **Claude Code**: Skill 开发环境
- **/write-a-skill**: Skill 脚手架生成
- **/tdd**: 测试驱动开发

---

## 📝 开发规范

### Skill 结构规范

```
~/.claude/skills/<skill-name>/
├── skill.md              # Skill 定义（必需）
├── README.md            # 使用文档
├── prompts/             # LLM 提示词模板
│   ├── main.md
│   └── sub_task.md
├── utils/               # 辅助函数
│   └── helpers.py
├── tests/               # 测试文件
│   ├── test_unit.py
│   └── test_integration.py
└── examples/            # 使用示例
    └── example.md
```

### 命名规范
- Skill 名称：小写，连字符分隔（如 `analyze-requirements`）
- 函数名称：小写，下划线分隔（如 `extract_keywords`）
- 类名称：驼峰命名（如 `KeywordExtractor`）

### 文档规范
- 每个 Skill 必须有 README.md
- 每个函数必须有文档字符串
- 提供使用示例
- 说明输入输出格式

### 测试规范
- 每个 Skill 必须有单元测试
- 关键流程必须有集成测试
- 测试覆盖率 > 80%
- 使用 OpenCode 进行基准测试

---

## 🔗 相关文档

- `docs/code_quality_improvements.md` - 代码质量改进总结
- `docs/quick_start_improvements.md` - 快速开始指南
- `docs/cli_design_analysis.md` - CLI 设计分析
- `crawler/utils/keyword_extractor.py` - 关键词提取器
- `crawler/utils/unified_search.py` - 统一搜索引擎

---

## 💡 最佳实践

### 1. 使用共享模块
```python
# ✅ 好的做法
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine

# ❌ 不好的做法
# 重新实现关键词提取逻辑
```

### 2. 优雅降级
```python
# ✅ 好的做法
try:
    keywords = extractor.extract_with_llm(text)
except Exception:
    keywords = extractor.extract_with_regex(text)  # 回退

# ❌ 不好的做法
keywords = extractor.extract_with_llm(text)  # 可能失败
```

### 3. 使用缓存
```python
# ✅ 好的做法
engine = UnifiedSearchEngine(
    source_dir='./sources',
    cache_dir='.cache/search'  # 启用缓存
)

# ❌ 不好的做法
# 每次都重新搜索，浪费 LLM 调用
```

### 4. 测试驱动开发
```bash
# ✅ 好的做法
# 1. 先写测试
/tdd "实现关键词提取功能"

# 2. 运行测试（红）
pytest tests/test_keyword_extractor.py

# 3. 实现功能（绿）
# 4. 重构（重构）
```

---

## 🎯 下一步行动

### 立即开始（今天）
1. [ ] 安装 OpenCode：`npm install -g @anthropic-ai/opencode`
2. [ ] 创建第一个 Skill：`/write-a-skill analyze-requirements`
3. [ ] 设置测试环境：`pip install pytest pytest-cov`

### 本周完成
1. [ ] 实现 `/analyze-requirements` Skill
2. [ ] 编写完整测试套件
3. [ ] 使用 OpenCode 进行基准测试

### 下周完成
1. [ ] 实现 `/investigate-jira` Skill
2. [ ] 集成到现有工作流
3. [ ] 收集用户反馈

---

**总结**: 通过将核心流程转换为 Skills，我们可以显著提升自动化程度和用户体验。优先实现最常用的 `/analyze-requirements` 和 `/investigate-jira` Skills，然后逐步扩展到其他功能。
