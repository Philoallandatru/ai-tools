# 开发路线图

> 更新时间: 2026-05-10
> 当前版本: v1.0 (已完成 Atlassian 爬取 + Wiki 编译 + 筛选导出)

## 已完成功能 ✅

### 核心功能
- ✅ Confluence 页面爬取（增量同步）
- ✅ Jira Issue 爬取（增量同步）
- ✅ 文档拆分工具（智能按标题层级拆分）
- ✅ Wiki 编译（llm-wiki-compiler + MiniMax API）
- ✅ 智能查询（基于 AI 的知识问答）
- ✅ 筛选导出（时间 + 状态过滤）

### 数据统计
- 源文件: 57 个 Markdown
- Wiki 概念: 341 个
- Confluence 页面: 36 个
- Jira Issues: 21 个

---

## 下一步开发建议

### 🎯 高优先级（立即可做）

#### 1. 全文搜索功能
**价值**: 提升日常使用效率，快速定位信息

**功能点**:
- 在 `sources/` 目录中实现快速全文搜索
- 支持正则表达式和模糊匹配
- 高亮显示搜索结果上下文
- 支持按文件类型过滤（Jira/Confluence）

**技术方案**:
```bash
# 命令示例
uv run python cli.py search "NVMe Reset" --type jira
uv run python cli.py search "性能优化" --context 3  # 显示前后3行
```

**实现要点**:
- 使用 `ripgrep` 或 Python `re` 模块
- 支持中文分词搜索
- 缓存搜索索引提升性能

---

#### 2. 自动周报生成
**价值**: 减少手动整理工作，自动汇总项目进展

**功能点**:
- 统计本周新增/更新的 issues
- 按状态分组（进行中/已完成/待办）
- 生成 Markdown 格式周报
- 支持自定义时间范围

**技术方案**:
```bash
# 命令示例
uv run python cli.py generate-report --type weekly
uv run python cli.py generate-report --start 2026-05-01 --end 2026-05-07
```

**报告内容**:
- 本周新增 issues 数量
- 状态变更统计
- 高优先级问题列表
- 活跃度最高的文档
- 关键词云图

---

#### 3. Slack/钉钉通知集成
**价值**: 及时获取重要更新，提升团队协作效率

**功能点**:
- 同步完成后自动推送通知
- 新增高优先级 issue 提醒
- Wiki 编译完成通知
- 支持自定义通知规则

**技术方案**:
```yaml
# config.yaml 配置示例
notifications:
  slack:
    webhook_url: "https://hooks.slack.com/..."
    channels:
      - "#knowledge-base"
    rules:
      - event: "sync_completed"
        message: "✅ Atlassian 同步完成: {stats}"
      - event: "high_priority_issue"
        message: "🚨 新增高优先级 Issue: {issue_key}"
```

**实现要点**:
- 使用 Slack Webhook API
- 支持钉钉机器人
- 可配置通知频率（避免打扰）

---

### 🔧 中优先级（1-2周内）

#### 4. 数据分析仪表板
**价值**: 了解项目整体状况，发现趋势和问题

**功能点**:
- Issue 状态分布饼图
- 时间线趋势图（新增/关闭）
- 优先级分布统计
- 活跃贡献者排名
- 知识库增长曲线

**技术方案**:
- 使用 `matplotlib` 或 `plotly` 生成图表
- 输出 HTML 仪表板
- 支持导出 PNG/PDF

**命令示例**:
```bash
uv run python cli.py dashboard --output ./reports/dashboard.html
```

---

#### 5. 自动摘要生成
**价值**: 快速理解长文档，节省阅读时间

**功能点**:
- 为长文档生成执行摘要（200-300字）
- 提取关键要点（bullet points）
- 识别核心技术术语
- 生成 TL;DR（Too Long; Didn't Read）

**技术方案**:
- 使用 MiniMax API 生成摘要
- 缓存已生成的摘要
- 支持批量处理

**命令示例**:
```bash
uv run python cli.py summarize sources/KAN-1.md
uv run python cli.py summarize --batch --output ./summaries/
```

---

### 🚀 低优先级（长期规划）

#### 6. 语义搜索
**价值**: 基于语义相似度查找相关文档

**功能点**:
- 使用 embedding 模型生成文档向量
- 相似文档推荐
- 语义查询（"类似 NVMe 重置的问题"）
- 概念关联分析

**技术方案**:
- 使用 `sentence-transformers` 或 OpenAI Embeddings
- 向量数据库（Chroma/Qdrant）
- 增量更新向量索引

**前置条件**:
- 需要更多数据积累（建议 100+ 文档）
- 需要评估 embedding 模型效果

---

#### 7. 知识图谱可视化
**价值**: 直观展示概念之间的关系

**功能点**:
- 将 wiki 概念导出为图谱
- 交互式可视化（D3.js/Cytoscape.js）
- 概念聚类分析
- 路径查询（概念 A → 概念 B）

**技术方案**:
- 解析 wiki 中的 wikilinks
- 使用 NetworkX 构建图
- 导出为 GraphML/JSON
- 前端可视化展示

**命令示例**:
```bash
uv run python cli.py export-graph --format graphml
uv run python cli.py visualize-graph --output ./graph.html
```

---

## 其他潜在方向

### 数据质量管理
- 重复检测（识别相似 issues）
- 链接检查（验证文档中的链接）
- 元数据验证（检查必填字段）
- 内容审核（标记过时内容）

### 协作增强
- 评论提醒（监控 Jira 评论）
- 变更追踪（追踪关键文档修改）
- 团队协作分析（贡献度统计）

### AI 增强
- 问题分类（自动打标签）
- 相似问题推荐（创建 issue 时）
- 知识问答机器人（Slack bot）

---

## 技术债务

### 需要优化的地方
1. **错误处理**: 增强网络请求的重试机制
2. **性能优化**: 大量文件时的爬取速度
3. **测试覆盖**: 添加单元测试和集成测试
4. **文档完善**: API 文档和使用示例
5. **配置验证**: 启动时验证配置文件格式

### 代码质量
- 添加类型注解（Type Hints）
- 统一错误处理模式
- 提取可复用的工具函数
- 添加日志级别控制

---

## 决策记录

### 为什么选择这些优先级？

**高优先级的理由**:
1. **全文搜索** - 最常用的功能，立即提升体验
2. **自动周报** - 减少重复劳动，ROI 高
3. **通知集成** - 提升团队协作，实施简单

**中优先级的理由**:
4. **数据分析** - 需要一定数据积累才有价值
5. **自动摘要** - 依赖 LLM API，成本需要考虑

**低优先级的理由**:
6. **语义搜索** - 技术复杂度高，需要更多数据
7. **图谱可视化** - 前端开发工作量大，非核心功能

---

## 下一步行动

### 本周计划
1. [ ] 实现全文搜索功能
2. [ ] 设计周报模板
3. [ ] 调研 Slack Webhook API

### 本月计划
1. [ ] 完成自动周报生成
2. [ ] 集成 Slack 通知
3. [ ] 开发数据分析仪表板原型

### 长期目标
- 建立完整的知识管理工作流
- 支持多团队使用
- 开源社区版本

---

## 反馈与建议

如果你有其他想法或建议，欢迎补充到这个文档中。

**联系方式**:
- 项目 Issue: [GitHub Issues](https://github.com/your-repo/issues)
- 讨论区: [GitHub Discussions](https://github.com/your-repo/discussions)
