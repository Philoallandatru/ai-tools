# 在 OpenCode 中使用 Skills 指南

## 📌 概述

本项目提供了 3 个 Claude Code Skills，可以在 OpenCode（Claude Code）环境中直接使用。

## 🎯 可用的 Skills

### 1. `/analyze-requirements` - 智能需求分析
端到端分析需求文档（PDF/Markdown），自动完成文档转换、拆分、关键词提取、代码搜索和 LLM 分析。

**使用示例**:
```bash
/analyze-requirements sources/KAN-1.md
/analyze-requirements docs/requirements.pdf --config custom_config.yaml
```

### 2. `/investigate-jira` - Jira Issue 深度调查
自动分析 Jira Issue，执行根因分析、相似问题搜索、知识检索，生成完整的调查报告。

**使用示例**:
```bash
/investigate-jira KAN-10
/investigate-jira KAN-10 --wiki kan-project --depth thorough
```

### 3. `/smart-search` - 智能语义搜索
使用自然语言查询代码库和文档，自动提取关键词、执行多源搜索、LLM 相关性排序。

**使用示例**:
```bash
/smart-search "如何实现 NVMe 控制器重置？"
/smart-search "错误处理" --scope code --min-score 8.0
```

## 🚀 快速开始

### 步骤 1: 确认 Skills 已安装

Skills 已经创建在 `.claude/skills/` 目录下：

```
.claude/skills/
├── analyze-requirements/
│   ├── SKILL.md
│   └── skill.py
├── investigate-jira/
│   ├── SKILL.md
│   └── skill.py
└── smart-search/
    ├── SKILL.md
    └── skill.py
```

### 步骤 2: 在 OpenCode 中使用

打开 OpenCode（Claude Code），在对话中直接输入 Skill 命令：

```
/analyze-requirements sources/KAN-1.md
```

OpenCode 会自动：
1. 识别 Skill 命令
2. 加载 Skill 定义（SKILL.md）
3. 执行 Skill 脚本（skill.py）
4. 返回执行结果

### 步骤 3: 查看结果

执行完成后，结果会保存在 `reports/` 目录：

- 文档分析: `reports/doc_analysis_<文档名>_<时间戳>.md`
- Jira 调查: `reports/jira_analysis_<Issue-Key>_<时间戳>.md`
- 搜索结果: 直接显示在对话中

## 📋 使用前准备

### 1. 环境配置

确保已安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置文件

确保 `config.yaml` 配置正确：
```yaml
llm:
  base_url: "http://127.0.0.1:8080/v1"
  model: "qwen3.5-9b"
  
jira:
  url: "https://your-domain.atlassian.net"
  username: "your-email@example.com"
  api_token: "${JIRA_API_TOKEN}"
```

### 3. 数据同步

首次使用前，同步 Jira 和 Confluence 数据：
```bash
python cli.py sync
```

### 4. LLM 服务

启动本地 LLM 服务（推荐 llama.cpp + Qwen3.5-9B）：
```bash
# 示例：使用 llama.cpp
./llama-server -m models/Qwen3.5-9B-IQ4_XS.gguf -c 4096 --port 8080
```

## 💡 使用技巧

### 技巧 1: 组合使用 Skills

```bash
# 1. 先搜索相关代码
/smart-search "NVMe 控制器重置"

# 2. 分析需求文档
/analyze-requirements sources/nvme-requirements.md

# 3. 调查相关 Issue
/investigate-jira KAN-10
```

### 技巧 2: 调整参数优化结果

```bash
# 提高搜索精度
/smart-search "错误处理" --min-score 8.0 --scope code

# 深度调查 Issue
/investigate-jira KAN-10 --depth thorough

# 使用自定义配置
/analyze-requirements docs/spec.md --config custom.yaml
```

### 技巧 3: 在 OpenCode 对话中请求帮助

如果不确定如何使用，可以直接问 Claude：

```
请帮我分析 sources/KAN-1.md 文档
```

Claude 会自动选择合适的 Skill 并执行。

## 🔧 故障排查

### 问题 1: Skill 命令无法识别

**症状**: 输入 `/analyze-requirements` 后没有反应

**解决**:
1. 确认 `.claude/skills/` 目录存在
2. 确认 SKILL.md 和 skill.py 文件存在
3. 重启 OpenCode

### 问题 2: 执行失败

**症状**: Skill 执行报错

**解决**:
1. 检查 Python 环境和依赖
2. 检查配置文件是否正确
3. 查看错误日志
4. 尝试直接运行 CLI 命令测试：
   ```bash
   python cli.py analyze-doc sources/KAN-1.md
   ```

### 问题 3: LLM 服务不可用

**症状**: 提示 "LLM 服务不可用"

**解决**:
1. 检查 LLM 服务是否运行：
   ```bash
   curl http://127.0.0.1:8080/health
   ```
2. 检查 config.yaml 中的 `llm.base_url`
3. 系统会自动降级到正则表达式提取（功能受限）

### 问题 4: 数据未同步

**症状**: 搜索无结果或 Issue 不存在

**解决**:
```bash
# 同步所有数据
python cli.py sync

# 查看同步状态
python cli.py status
```

## 📚 进阶用法

### 自定义 Skill

你可以基于现有 Skills 创建自定义版本：

1. 复制 Skill 目录：
   ```bash
   cp -r .claude/skills/analyze-requirements .claude/skills/my-custom-skill
   ```

2. 修改 `SKILL.md` 和 `skill.py`

3. 在 OpenCode 中使用：
   ```bash
   /my-custom-skill <参数>
   ```

### 集成到工作流

在 OpenCode 中，你可以创建自动化工作流：

```
请帮我完成以下任务：
1. 搜索 NVMe 相关代码
2. 分析 sources/nvme-spec.md 文档
3. 调查 KAN-10 Issue
4. 生成技术方案
```

Claude 会自动调用相应的 Skills 并整合结果。

## 📊 性能参考

| Skill | 平均耗时 | LLM 调用 | 输出大小 |
|-------|---------|---------|---------|
| analyze-requirements | 30秒-2分钟 | 4-18次 | 6-50KB |
| investigate-jira | 20秒-2分钟 | 15-20次 | 30-100KB |
| smart-search | 2-5秒 | 1-3次 | 实时显示 |

## 🔗 相关文档

- [Skills 测试计划](./skills_testing_plan.md)
- [Skill 开发计划](./skill_development_plan.md)
- [项目 README](../README.md)
- [代码质量改进](./code_quality_improvements.md)

## ✅ 检查清单

使用 Skills 前，确保：

- [ ] Python 3.10+ 已安装
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] config.yaml 配置正确
- [ ] LLM 服务运行正常
- [ ] 数据已同步（`python cli.py sync`）
- [ ] Skills 目录结构完整

## 🆘 获取帮助

如果遇到问题：

1. **查看文档**: 阅读 SKILL.md 中的故障排查章节
2. **测试 CLI**: 先用 CLI 命令测试功能是否正常
3. **检查日志**: 查看错误日志获取详细信息
4. **询问 Claude**: 在 OpenCode 中直接描述问题

---

**最后更新**: 2026-05-21  
**版本**: v1.0
