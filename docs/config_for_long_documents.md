# 长文档分析配置指南

## 问题场景

当你的文档有 **300+ 个小节**，且每个小节内容都很重要时，默认的过滤配置可能会跳过大量小节，导致分析不完整。

## 解决方案

修改 `config.yaml` 中的 `doc_analysis` 配置，**完全禁用过滤功能**：

```yaml
doc_analysis:
  # 文档切分配置
  splitting:
    split_level: 2              # 按 H2 标题切分
    max_chars: 5000             # 单个小节最大字符数
    strategy: "fixed"           # 固定拆分，每个小节独立处理
    min_section_chars: 0        # 0 = 不过滤任何小节
    merge_related: false        # 不合并小节

  # 小节过滤配置
  filtering:
    skip_empty: false           # 不跳过空小节
    exclude_patterns: []        # 不排除任何模式
    min_content_ratio: 0.0      # 不检查内容比例
```

## 配置说明

### 关键参数

- **`min_section_chars: 0`** - 设为 0 表示不过滤任何小节，即使内容很短
- **`skip_empty: false`** - 不跳过空小节
- **`exclude_patterns: []`** - 清空排除模式列表
- **`strategy: "fixed"`** - 使用固定拆分，每个小节独立成组
- **`merge_related: false`** - 不合并相关小节

### 效果

- ✅ 所有小节都会被分析，无论内容长短
- ✅ 每个小节独立处理，不会被合并
- ✅ 适合内容密集、每个小节都重要的文档

### 性能考虑

对于 375 个小节的文档：
- **LLM 调用次数**: 375 次（每个小节 1 次）
- **预估时间**: 约 30-60 分钟（取决于 LLM 速度）
- **成本**: 较高（建议使用本地 LLM）

## 其他配置场景

### 场景 1: 短文档（< 50 小节），需要智能合并

```yaml
doc_analysis:
  splitting:
    strategy: "smart"           # 智能合并
    min_section_chars: 100      # 过滤短小节
    merge_related: true         # 合并相关小节
  filtering:
    skip_empty: true
    exclude_patterns:
      - "原始数据（JSON）"
      - "Debug Info"
    min_content_ratio: 0.01     # 过滤低价值内容
```

### 场景 2: 中等文档（50-200 小节），平衡模式

```yaml
doc_analysis:
  splitting:
    strategy: "fixed"
    min_section_chars: 20       # 只过滤极短小节
    merge_related: false
  filtering:
    skip_empty: true
    exclude_patterns:
      - "原始数据（JSON）"
    min_content_ratio: 0.0
```

## 故障排查

### 问题：375 个小节被分成 1 组

**原因**: 过滤器过于激进，把所有小节都过滤掉了

**解决**: 使用上述"长文档配置"，禁用所有过滤

### 问题：分析只处理第一组就退出

**原因**: 第一个小节组处理失败（LLM 错误），导致整个分析停止

**解决**: 
1. 检查 LLM 配置是否正确
2. 使用 `--dry-run` 模式预览小节组
3. 查看日志中的错误信息

### 问题：处理时间太长

**原因**: 小节太多，每个都要调用 LLM

**解决**:
1. 使用本地 LLM（如 Qwen）降低成本
2. 考虑使用 `strategy: "smart"` 合并相关小节
3. 调整 `max_chars` 限制单个小节大小
