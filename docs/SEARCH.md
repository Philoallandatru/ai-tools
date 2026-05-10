# 全文搜索功能使用指南

## 概述

全文搜索功能允许你快速在 `sources/` 目录中的所有 Markdown 文件中查找内容。支持普通文本搜索、正则表达式搜索、文件类型过滤和结果高亮显示。

## 基本用法

### 简单搜索

```bash
uv run python cli.py search "NVMe Reset"
```

这将在所有文件中搜索 "NVMe Reset" 并显示匹配结果及上下文。

### 搜索选项

```bash
uv run python cli.py search [关键词] [选项]
```

## 命令选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--type` | 文件类型过滤 (all/jira/confluence) | all |
| `--context` | 显示上下文行数 | 2 |
| `--regex` | 使用正则表达式搜索 | false |
| `--case-sensitive` | 区分大小写 | false |
| `--max-results` | 最大结果数 | 100 |
| `--source-dir` | 源文件目录 | ./sources |
| `--no-highlight` | 不高亮显示匹配内容 | false |
| `--stats-only` | 只显示统计信息 | false |

## 使用示例

### 1. 基本搜索

搜索包含 "NVMe Reset" 的所有文件：

```bash
uv run python cli.py search "NVMe Reset"
```

输出示例：
```
搜索关键词: NVMe Reset
文件类型: all

============================================================
找到 21 个匹配，分布在 9 个文件中
============================================================

📄 deep-analysis-of-nvme-reset-timeout.md:15
────────────────────────────────────────────────────────────
  ## 背景
  
▶ 在 NVMe Reset 过程中，主机需要等待控制器状态寄存器...
  
  ## 问题描述
```

### 2. 按文件类型过滤

只搜索 Jira issues：

```bash
uv run python cli.py search "性能优化" --type jira
```

只搜索 Confluence 页面：

```bash
uv run python cli.py search "测试方法" --type confluence
```

### 3. 正则表达式搜索

使用正则表达式搜索多个关键词：

```bash
uv run python cli.py search "CC\.EN|CSTS\.RDY" --regex
```

搜索以特定模式开头的内容：

```bash
uv run python cli.py search "^##\s+.*测试" --regex
```

### 4. 调整上下文行数

显示更多上下文（前后 5 行）：

```bash
uv run python cli.py search "NVMe" --context 5
```

不显示上下文（只显示匹配行）：

```bash
uv run python cli.py search "NVMe" --context 0
```

### 5. 区分大小写

默认搜索不区分大小写，如需区分：

```bash
uv run python cli.py search "NVMe" --case-sensitive
```

### 6. 限制结果数量

只显示前 10 个匹配：

```bash
uv run python cli.py search "测试" --max-results 10
```

### 7. 统计模式

只显示统计信息，不显示详细匹配内容：

```bash
uv run python cli.py search "NVMe" --stats-only
```

输出示例：
```
============================================================
找到 21 个匹配，分布在 9 个文件中
============================================================

文件匹配统计:
    5 个匹配 - deep-analysis-nvme-reset.md
    3 个匹配 - nvme-spec.md
    2 个匹配 - ssd-testing.md
    ...
```

### 8. 组合使用

搜索 Jira 中的正则表达式，显示 3 行上下文：

```bash
uv run python cli.py search "KAN-\d+" --type jira --regex --context 3
```

## 高级技巧

### 搜索中文内容

直接输入中文关键词即可：

```bash
uv run python cli.py search "性能优化"
uv run python cli.py search "测试用例"
```

### 搜索特殊字符

如果搜索包含特殊字符的内容，使用正则表达式并转义：

```bash
uv run python cli.py search "CC\.EN" --regex
uv run python cli.py search "\[重要\]" --regex
```

### 搜索多个关键词

使用正则表达式的 OR 操作符：

```bash
uv run python cli.py search "NVMe|PCIe|SSD" --regex
```

### 搜索特定格式

搜索 Markdown 标题：

```bash
uv run python cli.py search "^#+\s+" --regex
```

搜索代码块：

```bash
uv run python cli.py search "```" --regex
```

搜索链接：

```bash
uv run python cli.py search "\[.*\]\(.*\)" --regex
```

## 输出格式说明

### 标准输出

```
📄 文件路径:行号
────────────────────────────────────────────────────────────
  上下文行（灰色）
  
▶ 匹配行（高亮显示匹配内容）
  
  上下文行（灰色）
```

- `📄` 表示文件
- `▶` 表示匹配行
- 匹配的关键词会以黄色高亮显示（终端支持颜色时）

### 统计信息

每次搜索都会显示：
- 总匹配数
- 匹配的文件数
- 每个文件的匹配数量（stats-only 模式）

## 性能优化

### 搜索速度

- 搜索速度取决于文件数量和大小
- 使用 `--type` 过滤可以提高搜索速度
- 使用 `--max-results` 限制结果数量可以更快返回

### 大型仓库

如果文件很多，建议：

1. 使用文件类型过滤：
```bash
uv run python cli.py search "关键词" --type jira
```

2. 限制结果数量：
```bash
uv run python cli.py search "关键词" --max-results 20
```

3. 使用统计模式快速了解分布：
```bash
uv run python cli.py search "关键词" --stats-only
```

## 常见问题

### Q: 搜索结果太多怎么办？

A: 使用以下方法缩小范围：
- 使用更具体的关键词
- 添加 `--type` 过滤
- 使用 `--max-results` 限制数量
- 使用正则表达式精确匹配

### Q: 如何搜索包含空格的短语？

A: 使用引号包裹：
```bash
uv run python cli.py search "NVMe Reset Mechanism"
```

### Q: 正则表达式不工作？

A: 确保：
1. 添加了 `--regex` 参数
2. 正确转义了特殊字符（如 `.` 应写为 `\.`）
3. 使用引号包裹正则表达式

### Q: 如何搜索文件名？

A: 当前版本只搜索文件内容，不搜索文件名。可以使用系统的 `find` 或 `dir` 命令搜索文件名。

### Q: 搜索结果没有高亮？

A: 检查：
1. 终端是否支持 ANSI 颜色
2. 是否使用了 `--no-highlight` 参数

## 与其他功能配合

### 搜索后导出

先搜索找到相关文件，然后使用筛选导出：

```bash
# 1. 搜索找到相关主题
uv run python cli.py search "性能测试" --stats-only

# 2. 导出相关文档
uv run python cli.py export-filtered --days 7 --status "进行中"
```

### 搜索后查询 Wiki

先搜索原始文档，然后在 Wiki 中查询概念：

```bash
# 1. 在源文件中搜索
uv run python cli.py search "NVMe Reset"

# 2. 在 Wiki 中查询相关概念
uv run python cli.py query-wiki "NVMe 重置机制是什么？"
```

## 技术实现

搜索功能使用 Python 的 `re` 模块实现：
- 支持完整的正则表达式语法
- 跨平台兼容（Windows/Linux/macOS）
- 高效的文件遍历和内容匹配
- 智能的上下文提取

## 未来改进

计划中的功能：
- [ ] 搜索结果缓存
- [ ] 支持中文分词
- [ ] 搜索历史记录
- [ ] 导出搜索结果为文件
- [ ] 交互式搜索模式
- [ ] 搜索结果排序（按相关性）

## 相关文档

- [使用指南](USAGE.md) - 完整的使用说明
- [快速开始](QUICKSTART.md) - 快速上手
- [开发路线图](DEVELOPMENT_ROADMAP.md) - 功能规划
