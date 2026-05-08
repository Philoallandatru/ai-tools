# 文档拆分工具

## 概述

文档拆分工具用于将长文档按照 Markdown 标题层级智能拆分为多个小文档，便于 LLM 处理和概念提取。

## 为什么需要拆分？

1. **LLM Token 限制**: 大多数 LLM 有输入 token 限制，长文档可能超出限制
2. **概念提取质量**: 较小的文档更容易被 LLM 准确提取概念
3. **处理效率**: 小文档处理速度更快，支持并行处理
4. **增量更新**: 小文档变更时只需重新处理变更部分

## 使用方法

### 基本用法

```bash
# 拆分文档（使用默认参数）
uv run python cli.py split-doc <input_file>

# 示例：拆分 NVMe 规范文档
uv run python cli.py split-doc test-sources/nvme.md
```

### 高级选项

```bash
uv run python cli.py split-doc <input_file> [options]

Options:
  --output-dir PATH       输出目录 [default: sources/]
  --max-chars INTEGER     单个文档最大字符数 [default: 10000]
  --split-level INTEGER   拆分的标题层级 (1-6) [default: 1]
  --dry-run              只显示拆分结果，不实际写入文件
```

### 参数说明

- **input_file**: 要拆分的源文件路径
- **--output-dir**: 拆分后文件的输出目录（默认 `sources/`）
- **--max-chars**: 单个文档的最大字符数限制（默认 10000）
- **--split-level**: 按哪一级标题拆分（1=`#`, 2=`##`, 3=`###`，以此类推）
- **--dry-run**: 预览模式，只显示拆分结果不实际写入文件

## 拆分策略

### 1. 按标题层级拆分

工具会识别 Markdown 标题（`#`, `##`, `###` 等），按指定层级拆分文档：

```markdown
# 第一章          ← level 1
## 1.1 节         ← level 2
### 1.1.1 小节   ← level 3
```

- `--split-level 1`: 按一级标题拆分（每个 `#` 一个文件）
- `--split-level 2`: 按二级标题拆分（每个 `##` 一个文件）
- 以此类推

### 2. 大小限制

如果某个章节超过 `--max-chars` 限制：

1. **优先递归拆分**: 尝试按下一级标题继续拆分
2. **按行切分**: 如果没有更多子标题，按固定大小切分内容

### 3. 元数据保留

每个拆分后的文档会自动添加 YAML frontmatter：

```yaml
---
source_file: nvme.md
part: 18/790
section: Table of Figures
---
```

或者对于按大小切分的文档：

```yaml
---
source_file: nvme.md
part: 18/790
chunk: 1/4
section: Table of Figures
---
```

## 使用示例

### 示例 1: 预览拆分结果

```bash
uv run python cli.py split-doc test-sources/nvme.md --dry-run
```

输出：
```
📄 拆分文档: nvme.md
   原文档大小: 2,024,699 字符
   拆分为: 768 个文档
   拆分层级: # (level 1)
   最大字符数: 10,000

🔍 预览拆分结果 (dry-run):
   - nvme-01-NVM-Express.md: 79 字符
   - nvme-02-Base-Specification.md: 1,149 字符
   ...
```

### 示例 2: 按二级标题拆分

```bash
uv run python cli.py split-doc test-sources/nvme.md \
  --split-level 2 \
  --max-chars 15000 \
  --output-dir sources/nvme-split
```

结果：
- 原文档 2,024,699 字符
- 拆分为 790 个文档
- 每个文档不超过 15,000 字符
- 输出到 `sources/nvme-split/` 目录

### 示例 3: 拆分后编译 Wiki

```bash
# 1. 拆分文档
uv run python cli.py split-doc test-sources/nvme.md \
  --output-dir sources/nvme-split

# 2. 编译 wiki
uv run python cli.py compile-wiki

# 3. 查询 wiki
uv run python cli.py query-wiki "什么是 NVMe Reset?"
```

## 文件命名规则

拆分后的文件按以下规则命名：

### 标准拆分（按标题）

```
{原文件名}-{序号}-{标题}.md
```

示例：
- `nvme-01-NVM-Express.md`
- `nvme-07-1-INTRODUCTION-.md`
- `nvme-35-Numerical-Descriptions.md`

### 递归拆分（多层级）

```
{原文件名}-part{父序号}-{子序号}.md
```

示例：
- `nvme-part18-01.md`
- `nvme-part18-02.md`

### 按大小切分

```
{原文件名}-part{序号}-chunk{块号}.md
```

示例：
- `nvme-part18-chunk01.md`
- `nvme-part18-chunk02.md`

## 最佳实践

### 1. 选择合适的拆分层级

- **技术规范文档**: 使用 `--split-level 2`（按章节拆分）
- **博客文章**: 使用 `--split-level 1`（按主标题拆分）
- **API 文档**: 使用 `--split-level 3`（按具体 API 拆分）

### 2. 设置合理的大小限制

- **MiniMax-M2.7**: 建议 `--max-chars 15000`（约 7500 tokens）
- **GPT-4**: 建议 `--max-chars 20000`（约 5000 tokens）
- **Claude**: 建议 `--max-chars 30000`（约 10000 tokens）

### 3. 使用 dry-run 预览

在实际拆分前，先用 `--dry-run` 预览结果：

```bash
uv run python cli.py split-doc <file> --dry-run
```

检查：
- 拆分后的文档数量是否合理
- 每个文档的大小是否符合预期
- 文件命名是否清晰

### 4. 组织输出目录

为不同的源文档使用不同的输出目录：

```bash
# NVMe 规范
uv run python cli.py split-doc specs/nvme.md \
  --output-dir sources/nvme-spec

# PCIe 规范
uv run python cli.py split-doc specs/pcie.md \
  --output-dir sources/pcie-spec

# 内部文档
uv run python cli.py split-doc docs/internal.md \
  --output-dir sources/internal-docs
```

## 技术细节

### 标题识别

工具使用正则表达式识别 Markdown 标题：

```python
r'^(#{1,6})\s+(.+)$'
```

支持：
- `# Title` (level 1)
- `## Title` (level 2)
- `### Title` (level 3)
- 等等

### 拆分算法

1. **解析文档**: 识别所有标题及其层级
2. **按层级分组**: 将相邻的章节分组
3. **检查大小**: 如果组超过限制，递归拆分或按行切分
4. **生成文件**: 添加元数据并保存

### 字符编码

- 所有文件使用 UTF-8 编码
- 支持中文、日文、韩文等多字节字符
- Windows 兼容性已测试

## 故障排除

### 问题 1: 拆分后文档过多

**原因**: 拆分层级太细或文档结构复杂

**解决方案**:
- 降低拆分层级（如从 3 改为 2）
- 增加 `--max-chars` 限制

### 问题 2: 某些文档仍然很大

**原因**: 该章节没有子标题，无法继续拆分

**解决方案**:
- 工具会自动按行切分
- 检查输出中的 `chunk` 文件

### 问题 3: 文件名包含特殊字符

**原因**: 标题中包含特殊字符

**解决方案**:
- 工具会自动清理特殊字符
- 只保留字母、数字、连字符和下划线

## 与 Wiki 编译器集成

拆分后的文档可以直接用于 wiki 编译：

```bash
# 完整流程
uv run python cli.py split-doc test-sources/nvme.md \
  --output-dir sources/nvme-split \
  --split-level 2 \
  --max-chars 15000

uv run python cli.py compile-wiki
uv run python cli.py query-wiki "NVMe 重置机制"
```

## 性能考虑

- **拆分速度**: 约 2MB/秒（取决于文档复杂度）
- **内存使用**: 约为源文件大小的 2-3 倍
- **磁盘空间**: 拆分后文件总大小略大于原文件（因为添加了元数据）

## 未来改进

- [ ] 支持按段落语义拆分（使用 NLP）
- [ ] 支持 PDF、DOCX 等格式
- [ ] 支持批量拆分多个文件
- [ ] 支持自定义元数据模板
- [ ] 支持拆分结果的可视化预览

## 相关文档

- [Wiki 集成指南](WIKI_INTEGRATION.md)
- [使用指南](USAGE.md)
- [快速开始](QUICKSTART.md)
