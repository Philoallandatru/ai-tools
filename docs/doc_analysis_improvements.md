# 文档分析改进方案

## 📋 问题描述

当前文档分析的拆分粒度太细，导致：
1. 上下文被割裂，不利于理解
2. 某些小节内容太少，分析价值不高
3. 报告过长，阅读体验差
4. LLM 调用次数过多，成本高

## 🎯 改进目标

1. **智能合并相关小节** - 保持上下文完整性
2. **过滤低价值小节** - 跳过空内容或纯数据小节
3. **生成简洁摘要** - 提供高层次概览
4. **可配置粒度** - 支持不同场景的需求

## 💡 具体改进方案

### 方案 1: 智能小节合并（推荐）

#### 1.1 合并策略

**合并规则**：
```python
# 定义小节组
SECTION_GROUPS = {
    "概览": ["标题", "基本信息", "描述"],
    "协作": ["评论", "关联Issues", "工作日志"],
    "附件": ["附件"],
    "原始数据": ["原始数据", "JSON"]
}

# 合并逻辑
def merge_sections(sections: List[Section]) -> List[SectionGroup]:
    groups = []
    for group_name, keywords in SECTION_GROUPS.items():
        matched_sections = [s for s in sections if any(k in s.title for k in keywords)]
        if matched_sections:
            groups.append(SectionGroup(group_name, matched_sections))
    return groups
```

**效果**：
- 9个小节 → 3-4个小节组
- 上下文更完整
- 分析更深入

---

#### 1.2 最小内容阈值

```python
# 配置
min_section_chars: 100  # 最小字符数
skip_empty_sections: true  # 跳过空小节

# 过滤逻辑
def filter_sections(sections: List[Section]) -> List[Section]:
    return [s for s in sections if len(s.content) >= min_section_chars]
```

**效果**：
- 自动跳过空的"附件"、"工作日志"
- 减少无意义的 LLM 调用

---

#### 1.3 排除特定小节类型

```python
# 配置
exclude_section_patterns: 
  - "原始数据"
  - "JSON"
  - "调试信息"

# 过滤逻辑
def should_analyze_section(section: Section) -> bool:
    for pattern in exclude_patterns:
        if pattern.lower() in section.title.lower():
            return False
    return True
```

**效果**：
- 跳过纯数据小节（JSON、调试信息）
- 专注于有分析价值的内容

---

### 方案 2: 两级分析策略

#### 2.1 第一级：快速概览

```python
# 生成文档摘要
def generate_overview(document: Document) -> str:
    """
    生成文档的高层次摘要
    - 文档类型（需求/设计/测试）
    - 主要内容
    - 关键实体
    - 技术栈
    """
    prompt = f"""
    分析以下文档，生成简洁的概览（200字以内）：
    
    {document.full_content[:2000]}  # 只看前2000字符
    
    请回答：
    1. 文档类型是什么？
    2. 主要讨论什么内容？
    3. 涉及哪些技术或模块？
    """
    return llm_client.generate(prompt)
```

**效果**：
- 1次 LLM 调用获得整体理解
- 用户可以快速判断是否需要详细分析

---

#### 2.2 第二级：详细分析（可选）

```python
# 用户选择后才进行详细分析
def detailed_analysis(document: Document, focus_areas: List[str]) -> Report:
    """
    根据用户指定的关注点进行详细分析
    
    Args:
        focus_areas: ["需求", "测试用例", "架构设计"]
    """
    sections = filter_sections_by_focus(document.sections, focus_areas)
    return analyze_sections(sections)
```

**效果**：
- 按需分析，避免浪费
- 用户控制分析深度

---

### 方案 3: 上下文窗口优化

#### 3.1 保留上下文

```python
# 分析时包含前后小节的上下文
def analyze_with_context(section: Section, prev: Section, next: Section) -> str:
    context = f"""
    前一节: {prev.title}
    {prev.content[:200]}
    
    当前节: {section.title}
    {section.content}
    
    后一节: {next.title}
    {next.content[:200]}
    """
    return llm_client.analyze(context)
```

**效果**：
- 保持上下文连贯性
- 分析更准确

---

#### 3.2 全局上下文注入

```python
# 在每次分析时注入文档全局信息
global_context = {
    "document_type": "Jira Issue",
    "project": "SN5100",
    "issue_key": "KAN-1",
    "priority": "Medium",
    "status": "待办"
}

def analyze_section(section: Section, global_context: Dict) -> str:
    prompt = f"""
    文档背景: {global_context}
    
    当前小节: {section.title}
    {section.content}
    
    请分析...
    """
    return llm_client.generate(prompt)
```

**效果**：
- LLM 始终知道文档的整体背景
- 分析更有针对性

---

### 方案 4: 报告格式优化

#### 4.1 简洁模式

```markdown
# 文档分析报告（简洁版）

## 📋 文档概览
- **类型**: Jira Issue
- **项目**: SN5100 (KAN-1)
- **状态**: 待办
- **优先级**: Medium

## 🎯 核心内容
[200字摘要]

## 🔍 关键发现
1. [发现1]
2. [发现2]
3. [发现3]

## 💡 建议
1. [建议1]
2. [建议2]

## 📎 相关资源
- 代码: [链接]
- 文档: [链接]
```

**效果**：
- 1页纸就能看完
- 快速抓住重点

---

#### 4.2 详细模式（可展开）

```markdown
# 文档分析报告（详细版）

## 📋 文档概览
[同简洁版]

<details>
<summary>📖 详细分析（点击展开）</summary>

### 第 1 组：概览
[合并后的分析]

### 第 2 组：协作
[合并后的分析]

</details>

<details>
<summary>🔍 检索结果（点击展开）</summary>

[代码和文档匹配]

</details>
```

**效果**：
- 默认显示摘要
- 需要时可以展开详情

---

## 🔧 配置示例

```yaml
# config.yaml
doc_analysis:
  # 拆分策略
  splitting:
    strategy: "smart"  # smart | fixed | adaptive
    min_section_chars: 100
    max_section_chars: 2000
    merge_related: true
    
  # 小节过滤
  filtering:
    skip_empty: true
    exclude_patterns:
      - "原始数据"
      - "JSON"
      - "调试信息"
    
  # 分析模式
  analysis:
    mode: "two_level"  # two_level | detailed | summary_only
    include_context: true
    context_window: 200  # 前后各200字符
    
  # 报告格式
  reporting:
    format: "concise"  # concise | detailed | both
    max_sections: 5
    include_toc: true
    collapsible_details: true
```

---

## 📊 效果对比

### 改进前
- **小节数**: 9个
- **LLM 调用**: 18次
- **报告大小**: 54KB
- **阅读时间**: 15-20分钟
- **上下文**: 割裂

### 改进后（方案1）
- **小节数**: 3-4个小节组
- **LLM 调用**: 6-8次
- **报告大小**: 20-30KB
- **阅读时间**: 5-10分钟
- **上下文**: 完整

### 改进后（方案2）
- **第一级**: 1次 LLM 调用，1分钟阅读
- **第二级**: 按需分析
- **灵活性**: 高

---

## 🚀 实施建议

### 短期（1周）
1. **实现方案1**: 智能小节合并
   - 定义小节组
   - 实现合并逻辑
   - 添加过滤规则

2. **优化报告格式**: 简洁模式
   - 生成摘要
   - 突出关键发现
   - 减少冗余信息

### 中期（2-4周）
1. **实现方案2**: 两级分析
   - 快速概览
   - 详细分析（可选）
   - 交互式选择

2. **实现方案3**: 上下文优化
   - 保留前后文
   - 全局上下文注入

### 长期（1-2月）
1. **自适应策略**: 根据文档类型自动调整
2. **用户偏好**: 记住用户的分析偏好
3. **可视化**: 添加图表和关系图

---

## ✅ 验证标准

改进后应该达到：
- [ ] 报告长度减少 50%+
- [ ] LLM 调用减少 50%+
- [ ] 阅读时间减少 60%+
- [ ] 上下文完整性提升
- [ ] 用户满意度提升

---

## 📝 示例对比

### 改进前的报告结构
```
第 1 节：标题 (200字)
第 2 节：基本信息 (300字)
第 3 节：自定义字段 (100字)
第 4 节：描述 (空)
第 5 节：评论 (空)
第 6 节：关联Issues (空)
第 7 节：附件 (空)
第 8 节：工作日志 (空)
第 9 节：JSON (5000字)
```

### 改进后的报告结构
```
📋 文档概览 (200字摘要)

第 1 组：问题概览 (合并1+2+3+4)
  - 标题、基本信息、描述
  - 关键词提取
  - 相关代码/文档

第 2 组：协作信息 (合并5+6+8，跳过空内容)
  - 评论、关联Issues、工作日志
  - 仅在有内容时显示

💡 关键发现和建议
```

---

## 🎯 推荐方案

**优先实施**: 方案1（智能小节合并）+ 方案4（报告格式优化）

**原因**：
1. 实施成本低
2. 效果立竿见影
3. 不破坏现有功能
4. 用户体验提升明显

**下一步**: 根据用户反馈，逐步实施方案2和方案3
