# analyze-requirements

智能需求分析 Skill - 端到端分析需求文档（PDF/Markdown），自动完成文档转换、拆分、关键词提取、代码搜索和 LLM 分析。

## 功能描述

自动完成需求文档的完整分析流程：
1. **文档预处理**: 自动识别文件类型（PDF/Markdown）
2. **智能拆分**: 将文档拆分为有意义的小节
3. **关键词提取**: 使用 LLM 或正则表达式提取技术关键词
4. **代码搜索**: 在代码库中搜索相关代码片段
5. **相关性分析**: LLM 评估代码与需求的相关性（0-10 分）
6. **生成报告**: 输出结构化的分析报告

## 使用场景

- 分析新需求文档，了解需要修改哪些代码
- 评估需求的实现复杂度
- 查找相关的历史实现
- 生成技术方案参考

## 输入参数

- `doc_path` (必需): 需求文档路径（支持 .pdf 和 .md）
- `--config` (可选): 配置文件路径，默认 `config.yaml`
- `--llm-base-url` (可选): LLM API 地址
- `--llm-model` (可选): LLM 模型名称

## 输出

- 分析报告保存到 `reports/doc_analysis_<文档名>_<时间戳>.md`
- 报告包含：
  - 文档概览
  - 每个小节的关键词
  - 相关代码片段（带相关性评分）
  - LLM 分析结果
  - 实现建议

## 使用示例

```bash
# 基础用法
/analyze-requirements sources/KAN-1.md

# 分析 PDF 文档
/analyze-requirements docs/requirements.pdf

# 使用自定义配置
/analyze-requirements sources/KAN-1.md --config custom_config.yaml

# 指定 LLM 服务
/analyze-requirements sources/KAN-1.md --llm-base-url http://localhost:8080
```

## 性能指标

- **处理时间**: 
  - 小文档（< 10 节）: ~30 秒
  - 中等文档（10-20 节）: ~2 分钟
  - 大文档（> 20 节）: ~5 分钟
- **LLM 调用**: 每个小节 1-2 次
- **准确率**: 关键词提取 > 80%，代码匹配相关性 > 75%

## 依赖

- Python 3.10+
- 本地 LLM 服务（推荐 llama.cpp + Qwen3.5-9B）
- 项目依赖：`crawler` 模块

## 注意事项

1. **PDF 支持**: 需要先运行 `python cli.py doc-convert-pdf` 转换 PDF
2. **LLM 服务**: 确保 LLM 服务运行正常，否则会降级到正则表达式提取
3. **文档大小**: 超大文档（> 100 页）可能需要较长时间
4. **中文支持**: 完全支持中文文档和关键词提取

## 实现细节

Skill 内部调用以下 CLI 命令：

```python
# 1. 如果是 PDF，先转换
if doc_path.endswith('.pdf'):
    subprocess.run(['python', 'cli.py', 'doc-convert-pdf', doc_path])
    doc_path = doc_path.replace('.pdf', '.md')

# 2. 执行文档分析
subprocess.run([
    'python', 'cli.py', 'analyze-doc', doc_path,
    '--config', config,
    '--llm-base-url', llm_base_url,
    '--llm-model', llm_model
])
```

## 故障排查

### 问题 1: LLM 服务连接失败
**症状**: 提示 "LLM 服务不可用"  
**解决**: 
- 检查 LLM 服务是否运行: `curl http://127.0.0.1:8080/health`
- 检查配置文件中的 `llm.base_url`

### 问题 2: 关键词提取质量差
**症状**: 提取的关键词不相关  
**解决**:
- 使用更强的 LLM 模型
- 调整 `doc_analysis.keyword_extraction.min_score` 阈值

### 问题 3: 报告未生成
**症状**: 命令执行完成但找不到报告  
**解决**:
- 检查 `reports/` 目录是否存在
- 查看命令输出中的错误信息
- 检查文件权限

## 相关 Skills

- `/investigate-jira` - Jira Issue 深度调查
- `/smart-search` - 智能语义搜索

## 版本历史

- **v1.0** (2026-05-21): 初始版本，支持 Markdown 和 PDF 文档分析
