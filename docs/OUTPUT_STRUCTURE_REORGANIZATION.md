# 测试输出目录重组文档

**日期**: 2026-05-19  
**变更类型**: 目录结构优化

## 变更概述

将 `tests/outputs/` 目录从扁平化结构重组为分类结构，提高文件组织性和可维护性。

## 变更前后对比

### 变更前
```
tests/outputs/
├── KAN-1_analysis.md
├── KAN-2_analysis.md
├── KAN-2_acceptance_20260517_094142.md
├── KAN-2_real_llm_20260517_100529.md
├── KAN-2_smart_mock_20260517_094348.md
├── ... (34 个文件混在一起)
├── ALL_COMMANDS_TEST_REPORT.md
├── ALL_COMMANDS_TEST_REPORT.json
├── SMART_SAMPLING_REPORT.md
└── summary.md
```

### 变更后
```
tests/outputs/
├── jira/                          # Jira 分析结果（最新）
│   ├── KAN-1.md
│   ├── KAN-2.md
│   ├── ... (21 个 issue)
│   └── summary.md
├── reports/                       # 测试报告
│   ├── all-commands.md
│   ├── all-commands.json
│   └── smart-sampling.md
└── archive/                       # 历史文件
    ├── KAN-2_acceptance_20260517_094142.md
    ├── KAN-2_real_llm_20260517_100529.md
    └── ... (9 个历史文件)
```

## 文件命名规范

### Jira 分析文件
- **格式**: `{ISSUE_KEY}.md`
- **示例**: `KAN-1.md`, `KAN-2.md`
- **说明**: 去掉 `_analysis` 后缀，简化命名

### 测试报告文件
- **格式**: `{report-type}.md` 或 `{report-type}.json`
- **示例**: `all-commands.md`, `smart-sampling.md`
- **说明**: 使用小写和连字符，避免大写和下划线

### 历史文件
- **格式**: 保持原有时间戳格式
- **示例**: `KAN-2_real_llm_20260517_100529.md`
- **说明**: 仅用于归档，不影响当前工作

## 代码变更

### 1. test_all_commands.py
```python
# 变更前
report_path = TEST_OUTPUTS_DIR / "ALL_COMMANDS_TEST_REPORT.md"
json_path = TEST_OUTPUTS_DIR / "ALL_COMMANDS_TEST_REPORT.json"

# 变更后
report_path = TEST_OUTPUTS_DIR / "reports" / "all-commands.md"
json_path = TEST_OUTPUTS_DIR / "reports" / "all-commands.json"
```

### 2. test_full_analysis.py
```python
# 变更前
output_file = output_dir / f"{issue_key}_analysis.md"
summary_file = output_dir / "summary.md"

# 变更后
jira_dir = output_dir / "jira"
jira_dir.mkdir(parents=True, exist_ok=True)
output_file = jira_dir / f"{issue_key}.md"
summary_file = jira_dir / "summary.md"
```

### 3. tests/manual/README.md
更新文档说明新的目录结构。

## 统计信息

- **jira/**: 22 个文件（21 个 issue + 1 个 summary）
- **reports/**: 3 个文件（2 个 Markdown + 1 个 JSON）
- **archive/**: 9 个历史文件

## 优势

1. **清晰分类**: 按文件类型分目录，一目了然
2. **简化命名**: 去掉冗余后缀，文件名更简洁
3. **历史归档**: 历史文件单独存放，不干扰当前工作
4. **易于维护**: 新文件自动归类，避免混乱
5. **向后兼容**: 保留历史文件，不丢失数据

## 注意事项

1. 旧的测试脚本需要更新路径配置
2. 文档和 README 需要同步更新
3. CI/CD 流程如果依赖路径需要调整
4. 建议定期清理 `archive/` 目录

## 后续优化建议

1. 考虑为 `archive/` 添加自动清理策略（如保留最近 30 天）
2. 可以按日期进一步组织 `archive/` 子目录
3. 添加 `.gitkeep` 文件确保空目录被 Git 跟踪
