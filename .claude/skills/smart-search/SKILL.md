# smart-search

智能语义搜索 Skill - 使用自然语言查询代码库和文档，自动提取关键词、执行多源搜索、LLM 相关性排序。

## 功能描述

智能搜索系统，支持：
1. **自然语言理解**: 自动理解查询意图
2. **关键词提取**: 使用 LLM 提取技术关键词
3. **多源搜索**: 同时搜索代码、文档、Wiki
4. **相关性排序**: LLM 评估结果相关性（0-10 分）
5. **结果聚合**: 合并和去重搜索结果
6. **智能过滤**: 根据阈值过滤低相关性结果

## 使用场景

- 快速查找相关代码实现
- 搜索技术文档和 Wiki
- 了解某个功能的实现位置
- 查找 API 使用示例

## 输入参数

- `query` (必需): 搜索查询（自然语言或关键词）
- `--scope` (可选): 搜索范围（code/docs/wiki/all），默认 all
- `--min-score` (可选): 最低相关性分数（0-10），默认 6.0
- `--limit` (可选): 返回结果数量，默认 10
- `--config` (可选): 配置文件路径

## 输出

- 搜索结果列表（按相关性排序）
- 每个结果包含：
  - 文件路径
  - 相关性评分（0-10）
  - 匹配原因
  - 代码片段或文档摘要

## 使用示例

```bash
# 基础用法
/smart-search "如何实现 NVMe 控制器重置？"

# 仅搜索代码
/smart-search "错误处理" --scope code

# 仅搜索文档
/smart-search "架构设计" --scope docs

# 调整相关性阈值
/smart-search "NVMe" --min-score 8.0

# 限制结果数量
/smart-search "测试用例" --limit 5
```

## 性能指标

- **搜索时间**: 
  - 简单查询: < 2 秒
  - 复杂查询: < 5 秒
- **LLM 调用**: 1-3 次
- **准确率**: Top-1 > 80%, Top-5 > 95%

## 搜索范围

| 范围 | 说明 | 搜索内容 |
|------|------|----------|
| code | 代码搜索 | sources/ 目录下的源代码文件 |
| docs | 文档搜索 | sources/ 目录下的 Markdown 文档 |
| wiki | Wiki 搜索 | wikis/ 目录下的编译后 Wiki |
| all | 全部搜索 | 以上所有内容 |

## 关键词提取策略

Skill 会自动选择最佳的关键词提取策略：

1. **LLM 提取** (优先)
   - 使用 LLM 理解查询意图
   - 提取技术术语和标识符
   - 生成同义词和相关词

2. **正则表达式提取** (降级)
   - 当 LLM 不可用时自动降级
   - 基于规则提取关键词
   - 过滤停用词

## 相关性评分

LLM 会根据以下因素评估相关性：
- 关键词匹配度
- 语义相似度
- 上下文相关性
- 代码/文档质量

评分标准：
- **9-10 分**: 高度相关，直接解决问题
- **7-8 分**: 相关，提供有用信息
- **5-6 分**: 部分相关，可能有帮助
- **3-4 分**: 弱相关，参考价值有限
- **0-2 分**: 不相关

## 依赖

- Python 3.10+
- 本地 LLM 服务（可选，用于提升搜索质量）
- 已同步的代码和文档数据

## 注意事项

1. **数据准备**: 首次使用前需同步数据（`python cli.py sync`）
2. **LLM 可选**: 没有 LLM 时会降级到基础搜索
3. **搜索范围**: 仅搜索 `sources/` 和 `wikis/` 目录
4. **性能**: 大型代码库可能需要更长时间

## 实现细节

```python
# Skill 内部调用 CLI 命令
subprocess.run([
    'python', 'cli.py', 'search', query,
    '--scope', scope,
    '--min-score', str(min_score),
    '--limit', str(limit)
])
```

## 高级用法

### 组合查询
```bash
# 查找特定功能的实现和文档
/smart-search "NVMe 初始化流程" --scope all

# 查找错误处理相关代码
/smart-search "error handling exception" --scope code --min-score 7.0
```

### 精确搜索
```bash
# 查找特定函数
/smart-search "nvme_reset_controller" --scope code

# 查找特定配置
/smart-search "timeout configuration" --scope docs
```

## 故障排查

### 问题 1: 搜索无结果
**症状**: 提示 "No results found"  
**解决**: 
- 尝试更通用的查询词
- 降低 `--min-score` 阈值
- 检查数据是否已同步

### 问题 2: 结果不相关
**症状**: 返回的结果与查询无关  
**解决**:
- 提高 `--min-score` 阈值
- 使用更具体的查询词
- 限制搜索范围（--scope）

### 问题 3: 搜索速度慢
**症状**: 搜索时间超过 10 秒  
**解决**:
- 减少搜索范围
- 降低 `--limit` 数量
- 检查 LLM 服务响应速度

## 相关 Skills

- `/analyze-requirements` - 智能需求分析
- `/investigate-jira` - Jira Issue 深度调查

## 版本历史

- **v1.0** (2026-05-21): 初始版本，支持多源搜索和 LLM 排序
