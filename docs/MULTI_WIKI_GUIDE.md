# 多 Wiki 仓库使用指南

## 概述

多 Wiki 仓库架构允许你为不同项目维护独立的知识库，支持批量编译、智能知识检索和自动匹配。

## 核心特性

### 1. 多项目隔离
- 每个项目独立的 wiki 仓库
- 独立的编译状态和配置
- 互不干扰的知识库

### 2. 批量编译
- 分批编译（默认每批 5 个文件）
- 失败时保留进度
- 支持断点续传

### 3. 智能知识检索
- **specify 模式**：指定特定 wiki
- **auto_match 模式**：根据元数据自动匹配
- **search_all 模式**：搜索所有 wiki 并合并结果

### 4. 自动匹配规则
匹配优先级：
1. **Jira 项目键** - `KAN-10` → 匹配 `jira_projects: ["KAN"]`
2. **关键词** - 标题/描述中的关键词
3. **Confluence Space** - Space 键匹配

---

## 快速开始

### 1. 配置 Wiki

在 `config.yaml` 中添加 wikis 配置：

```yaml
wikis:
  default_wiki: "project-a"
  
  repositories:
    - name: "project-a"
      display_name: "Project Alpha"
      description: "NVMe firmware development"
      path: "./wikis/project-a"
      
      auto_match:
        jira_projects: ["KAN", "NVME"]
        confluence_spaces: ["MFS"]
        keywords: ["nvme", "firmware", "ssd"]
      
      compilation:
        batch_size: 5
        auto_compile: true
        compile_timeout: 300
        stop_on_failure: true
```

### 2. 初始化 Wiki

```bash
# 使用 CLI 命令初始化
uv run python cli.py wiki-init project-a \
  --display-name "Project Alpha" \
  --jira-projects "KAN,NVME" \
  --keywords "nvme,firmware,ssd"
```

这将创建以下目录结构：

```
wikis/project-a/
├── temp/                  # 临时暂存区
├── sources/               # Wiki 专用源文件
├── wiki/                  # 编译输出
├── .llmwiki/              # Wiki 状态
├── .batch-state.json      # 批量编译进度
└── .wiki-metadata.json    # Wiki 元数据
```

### 3. 编译 Wiki

```bash
# 编译特定文件
uv run python cli.py compile-wiki --wiki-name project-a --files sources/KAN-*.md

# 编译所有 wiki
uv run python cli.py compile-wiki --all-wikis

# 自定义批次大小
uv run python cli.py compile-wiki --wiki-name project-a --files sources/*.md --batch-size 10

# 续传失败的编译
uv run python cli.py compile-wiki --wiki-name project-a --resume
```

---

## 工作流程

### 集成编译工作流

```
用户执行命令
    ↓
自动复制文件到 temp/
    ↓
批量编译循环
    ├─ Batch 1: 移动 5 个文件到 sources/
    ├─ 运行 npx llm-wiki-compiler compile
    ├─ 检查状态（成功/失败）
    └─ 继续下一批或停止
```

### 批量编译状态跟踪

编译进度保存在 `.batch-state.json`：

```json
{
  "current_batch": 2,
  "total_batches": 4,
  "completed_files": ["KAN-1.md", "KAN-2.md", "KAN-3.md"],
  "pending_files": ["KAN-6.md", "KAN-7.md"],
  "failed_files": [],
  "status": "in_progress"
}
```

---

## 知识检索

### 1. 自动匹配模式（默认）

```bash
# 根据 Jira 项目键自动匹配
uv run python cli.py analyze-jira KAN-10

# 系统会自动：
# 1. 提取项目键 "KAN"
# 2. 匹配到配置了 jira_projects: ["KAN"] 的 wiki
# 3. 使用该 wiki 进行知识检索
```

### 2. 指定 Wiki 模式

```bash
# 明确指定使用哪个 wiki
uv run python cli.py analyze-jira KAN-10 --wiki-name project-a
```

### 3. 搜索所有 Wiki 模式

```bash
# 搜索所有 wiki 并合并结果
uv run python cli.py analyze-jira KAN-10 --wiki-mode search_all

# 结果按相关性评分排序
```

---

## 管理命令

### 列出所有 Wiki

```bash
uv run python cli.py wiki-list
```

输出示例：

```
配置的 Wiki (2 个)
默认 wiki: project-a

Project Alpha [默认]
  名称: project-a
  路径: ./wikis/project-a
  描述: NVMe firmware development
  状态: 已初始化
  temp/ 文件: 0
  sources/ 文件: 15
  wiki/concepts/ 文件: 120
  Jira 项目: KAN, NVME
  关键词: nvme, firmware, ssd

Project Beta
  名称: project-b
  路径: ./wikis/project-b
  状态: 未初始化
```

### 初始化新 Wiki

```bash
uv run python cli.py wiki-init project-b \
  --display-name "Project Beta" \
  --description "Cloud infrastructure" \
  --jira-projects "CLOUD" \
  --keywords "kubernetes,docker,aws"
```

### 迁移现有 Wiki

如果你已有旧的 `wiki/` 目录，可以迁移到多 wiki 架构：

```bash
# 预览迁移
uv run python cli.py migrate-wiki --dry-run

# 执行迁移
uv run python cli.py migrate-wiki

# 指定目标 wiki 名称
uv run python cli.py migrate-wiki --target-wiki my-wiki
```

迁移会：
1. 创建 `wikis/default/` 目录结构
2. 移动 `wiki/` → `wikis/default/wiki/`
3. 创建 `.wiki-metadata.json`
4. 更新 `config.yaml`

---

## 高级用法

### 1. 批量编译失败恢复

如果编译在第 2 批失败：

```bash
# 查看状态
cat wikis/project-a/.batch-state.json

# 修复问题后续传
uv run python cli.py compile-wiki --wiki-name project-a --resume
```

### 2. 多项目并行编译

```bash
# 编译所有 wiki
uv run python cli.py compile-wiki --all-wikis
```

### 3. 自定义自动匹配规则

编辑 `config.yaml`：

```yaml
wikis:
  repositories:
    - name: "project-a"
      auto_match:
        jira_projects: ["KAN", "NVME", "SSD"]  # 添加更多项目
        keywords: ["nvme", "firmware", "pcie", "controller"]  # 添加更多关键词
```

### 4. 调整批量编译配置

```yaml
wikis:
  repositories:
    - name: "project-a"
      compilation:
        batch_size: 10              # 增加批次大小
        compile_timeout: 600        # 增加超时时间
        stop_on_failure: false      # 失败后继续编译
```

---

## 目录结构

### 完整目录布局

```
ai-tools/
├── sources/                          # 原始源文件（保持不变）
│   ├── confluence/
│   │   └── sakiko222-confluence/MFS/
│   ├── jira/
│   └── KAN-*.md
│
├── wikis/                            # 多 wiki 根目录
│   ├── project-a/
│   │   ├── temp/                     # 临时暂存区
│   │   ├── sources/                  # Wiki 专用源文件
│   │   │   ├── confluence/
│   │   │   └── jira/
│   │   ├── wiki/                     # 编译输出
│   │   │   ├── concepts/
│   │   │   ├── index.md
│   │   │   └── MOC.md
│   │   ├── .llmwiki/                 # Wiki 状态
│   │   │   ├── state.json
│   │   │   └── schema.json
│   │   ├── .batch-state.json         # 批量编译进度
│   │   └── .wiki-metadata.json       # Wiki 元数据
│   │
│   └── project-b/
│       └── ...
│
├── wiki/                             # 已废弃（迁移后）
└── config.yaml                       # 增强配置
```

### Wiki 元数据格式

`.wiki-metadata.json`：

```json
{
  "name": "project-a",
  "display_name": "Project Alpha Knowledge Base",
  "description": "NVMe firmware development knowledge",
  "created_at": "2026-05-15T10:00:00Z",
  "auto_match_rules": {
    "jira_projects": ["KAN", "NVME"],
    "confluence_spaces": ["MFS"],
    "keywords": ["nvme", "firmware", "ssd"]
  },
  "compilation_config": {
    "batch_size": 5,
    "auto_compile": true
  }
}
```

---

## 故障排查

### 问题 1: 编译失败

**症状**：批量编译在某个批次失败

**解决方案**：
```bash
# 1. 查看失败的批次
cat wikis/project-a/.batch-state.json

# 2. 检查 temp/ 中剩余的文件
ls wikis/project-a/temp/

# 3. 修复问题后续传
uv run python cli.py compile-wiki --wiki-name project-a --resume
```

### 问题 2: 自动匹配不准确

**症状**：Jira 分析使用了错误的 wiki

**解决方案**：
```bash
# 方案 1: 手动指定 wiki
uv run python cli.py analyze-jira KAN-10 --wiki-name project-a

# 方案 2: 调整自动匹配规则
# 编辑 config.yaml，添加更多匹配规则
```

### 问题 3: Wiki 不存在

**症状**：`Wiki not found: project-a`

**解决方案**：
```bash
# 1. 列出所有 wiki
uv run python cli.py wiki-list

# 2. 初始化缺失的 wiki
uv run python cli.py wiki-init project-a
```

### 问题 4: temp/ 目录为空

**症状**：`temp/ 目录为空，跳过编译`

**解决方案**：
```bash
# 使用 --files 参数指定要编译的文件
uv run python cli.py compile-wiki --wiki-name project-a --files sources/KAN-*.md
```

---

## 最佳实践

### 1. Wiki 组织

- **按项目分类**：每个项目一个 wiki
- **按版本分类**：同一项目的不同版本可以有独立 wiki
- **按团队分类**：不同团队维护各自的 wiki

### 2. 自动匹配规则

- **Jira 项目**：使用项目键前缀（如 `KAN`, `NVME`）
- **关键词**：使用核心技术术语（如 `nvme`, `firmware`）
- **避免重叠**：确保不同 wiki 的匹配规则不重叠

### 3. 批量编译

- **小批次**：使用较小的批次大小（5-10 个文件）
- **及时续传**：失败后及时修复并续传
- **监控进度**：定期检查 `.batch-state.json`

### 4. 知识检索

- **优先自动匹配**：让系统自动选择合适的 wiki
- **必要时指定**：对于特殊情况手动指定 wiki
- **使用 search_all**：当不确定时搜索所有 wiki

---

## 性能优化

### 1. 批量编译优化

```yaml
compilation:
  batch_size: 10              # 增加批次大小（如果 API 稳定）
  compile_timeout: 600        # 增加超时（如果网络慢）
```

### 2. 并发控制

```yaml
performance:
  knowledge_retrieval:
    max_thread_workers: 5     # 增加并发数（search_all 模式）
```

### 3. 缓存利用

```yaml
cache:
  enabled: true
  ttl: 86400                  # 24 小时缓存
```

---

## 常见场景

### 场景 1: 新项目启动

```bash
# 1. 初始化 wiki
uv run python cli.py wiki-init new-project \
  --display-name "New Project" \
  --jira-projects "NEW" \
  --keywords "keyword1,keyword2"

# 2. 编译初始文档
uv run python cli.py compile-wiki --wiki-name new-project --files sources/NEW-*.md

# 3. 测试知识检索
uv run python cli.py analyze-jira NEW-1
```

### 场景 2: 迁移现有项目

```bash
# 1. 迁移旧 wiki
uv run python cli.py migrate-wiki

# 2. 验证迁移
uv run python cli.py wiki-list

# 3. 测试编译
uv run python cli.py compile-wiki --wiki-name default --resume
```

### 场景 3: 多项目维护

```bash
# 1. 列出所有项目
uv run python cli.py wiki-list

# 2. 批量编译所有项目
uv run python cli.py compile-wiki --all-wikis

# 3. 针对性分析
uv run python cli.py analyze-jira PROJECT-A-10 --wiki-name project-a
uv run python cli.py analyze-jira PROJECT-B-20 --wiki-name project-b
```

---

## 参考

- [README.md](../README.md) - 项目总览
- [WIKI_INTEGRATION.md](WIKI_INTEGRATION.md) - Wiki 集成指南
- [config.yaml](../config.yaml) - 配置示例
