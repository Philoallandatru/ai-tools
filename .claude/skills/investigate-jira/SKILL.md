# investigate-jira

Jira Issue 深度调查 Skill - 自动分析 Jira Issue，执行根因分析、相似问题搜索、知识检索，生成完整的调查报告。

## 功能描述

深度分析 Jira Issue，自动完成：
1. **问题信息提取**: 自动提取 Issue 的关键信息
2. **根因分析**: 使用 LLM 分析问题的根本原因
3. **相似问题搜索**: 在历史 Issues 中查找相似问题
4. **知识检索**: 搜索相关的 Wiki 文档和代码
5. **解决方案建议**: 基于历史数据生成解决方案
6. **闭环检查**: 验证问题是否完整解决
7. **代码覆盖分析**: 检查相关代码的测试覆盖率
8. **评论分析**: 分析 Issue 评论中的关键信息
9. **技术债务评估**: 评估问题相关的技术债务

## 使用场景

- 快速了解复杂 Bug 的根因
- 查找类似问题的解决方案
- 评估问题的影响范围
- 生成问题调查报告

## 输入参数

- `issue_key` (必需): Jira Issue Key（如 KAN-10）
- `--wiki` (可选): 指定 Wiki 目录名称
- `--config` (可选): 配置文件路径，默认 `config.yaml`
- `--depth` (可选): 调查深度（quick/normal/thorough），默认 normal

## 输出

- 调查报告保存到 `reports/jira_analysis_<Issue-Key>_<时间戳>.md`
- 报告包含：
  - Issue 摘要
  - 根因分析
  - 相似问题列表（Top 5）
  - 相关知识（Wiki + 代码）
  - 解决方案建议
  - 验证测试建议
  - 技术债务评估

## 使用示例

```bash
# 基础用法
/investigate-jira KAN-10

# 指定 Wiki
/investigate-jira KAN-10 --wiki kan-project

# 深度调查
/investigate-jira KAN-10 --depth thorough

# 快速调查
/investigate-jira KAN-10 --depth quick
```

## 性能指标

- **处理时间**: 
  - quick: ~20 秒
  - normal: ~1 分钟
  - thorough: ~2-3 分钟
- **LLM 调用**: 15-20 次（取决于深度）
- **准确率**: 根因分析 > 70%，相似问题匹配 > 80%

## 分析器列表

Skill 会根据深度自动选择执行的分析器：

| 分析器 | Quick | Normal | Thorough | 说明 |
|--------|-------|--------|----------|------|
| issue_summary | ✅ | ✅ | ✅ | 问题摘要 |
| root_cause | ✅ | ✅ | ✅ | 根因分析 |
| similar_jira | ✅ | ✅ | ✅ | 相似问题 |
| knowledge | ❌ | ✅ | ✅ | 知识检索 |
| actions | ✅ | ✅ | ✅ | 解决方案 |
| closed_loop | ❌ | ✅ | ✅ | 闭环检查 |
| code_coverage | ❌ | ❌ | ✅ | 代码覆盖 |
| comments | ❌ | ✅ | ✅ | 评论分析 |
| tech_debt | ❌ | ❌ | ✅ | 技术债务 |

## 依赖

- Python 3.10+
- Jira API 访问权限
- 本地 LLM 服务
- 已同步的 Jira 数据（`sources/` 目录）

## 注意事项

1. **数据同步**: 首次使用前需运行 `python cli.py sync` 同步 Jira 数据
2. **API 限制**: 频繁调用可能触发 Jira API 限流
3. **Wiki 依赖**: 知识检索需要预先编译 Wiki（`python cli.py wiki-compile`）
4. **LLM 质量**: 分析质量依赖 LLM 模型能力

## 实现细节

```python
# Skill 内部调用 CLI 命令
subprocess.run([
    'python', 'cli.py', 'jira-analyze', issue_key,
    '--wiki', wiki,
    '--config', config
])
```

## 故障排查

### 问题 1: Issue 不存在
**症状**: 提示 "Issue not found"  
**解决**: 
- 检查 Issue Key 是否正确
- 运行 `python cli.py sync` 同步最新数据

### 问题 2: 相似问题搜索无结果
**症状**: 报告中相似问题为空  
**解决**:
- 确保有足够的历史 Issues 数据
- 调整 `jira_analysis.similar_issues.min_score` 阈值

### 问题 3: 知识检索失败
**症状**: 报告中知识检索章节为空  
**解决**:
- 运行 `python cli.py wiki-compile` 编译 Wiki
- 检查 Wiki 目录是否存在

## 相关 Skills

- `/analyze-requirements` - 智能需求分析
- `/smart-search` - 智能语义搜索

## 版本历史

- **v1.0** (2026-05-21): 初始版本，支持 9 个分析器
