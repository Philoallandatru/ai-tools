# CLI 层重构计划

## 📊 当前状态分析

### 代码统计
- **总行数**: 1057 行
- **目标行数**: ~500 行 (减少 50%)
- **CLI 命令数**: 16 个
- **click.echo/secho 调用**: 184 次
- **错误处理块**: 多处重复的 try/except

### 命令列表
1. `init` - 初始化配置文件
2. `list-sources` - 列出数据源
3. `sync` - 同步数据
4. `status` - 显示同步状态
5. `compile-wiki` - 编译 wiki
6. `query-wiki` - 查询 wiki
7. `wiki-status` - wiki 状态
8. `watch-wiki` - 监控 wiki
9. `split-doc` - 分割文档
10. `search` - 搜索内容
11. `find-jira` - 查找 Jira issue
12. `list-jira` - 列出 Jira issues
13. `generate-report` - 生成报告
14. `export-filtered` - 导出过滤数据
15. `analyze-jira` - 分析 Jira issue
16. `analyze-doc` - 分析文档

## 🎯 重构目标

### 1. 提取输出格式化逻辑 (预计减少 ~200 行)
**问题**: 184 次 click.echo 调用，大量重复的格式化代码

**解决方案**: 创建 `CLIOutput` 类
```python
class CLIOutput:
    """CLI 输出管理器，支持结构化日志和终端输出"""
    
    def success(self, message: str, **context)
    def error(self, message: str, **context)
    def info(self, message: str, **context)
    def warning(self, message: str, **context)
    def table(self, data: List[Dict], headers: List[str])
    def progress(self, current: int, total: int, message: str)
```

### 2. 使用 Service 层 (预计减少 ~150 行)
**问题**: 命令中包含业务逻辑，直接操作文件和数据

**解决方案**: 
- `sync` 命令 → 使用 `SyncService`
- `generate-report` 命令 → 使用 `ReportService`
- `analyze-jira` 命令 → 使用 `AnalysisService`

### 3. 提取辅助函数 (预计减少 ~100 行)
**问题**: 多个辅助函数混在 cli.py 中

**解决方案**: 创建 `crawler/utils/cli_helpers.py`
- `load_config()` → 已有 `ConfigManager`
- `filter_sources()` → 移到 `SyncService`
- `_parse_jira_metadata()` → 移到 `crawler/utils/metadata.py`
- `_parse_confluence_metadata()` → 移到 `crawler/utils/metadata.py`

### 4. 简化错误处理 (预计减少 ~50 行)
**问题**: 重复的 try/except 块

**解决方案**: 创建装饰器
```python
@handle_cli_errors
def command_function():
    ...
```

### 5. 移除未使用的命令 (预计减少 ~50 行)
**问题**: 部分命令可能不常用或已过时

**待评估**: 
- `compile-wiki` - 是否还在使用？
- `query-wiki` - 是否还在使用？
- `wiki-status` - 是否还在使用？
- `watch-wiki` - 是否还在使用？

## 📋 实施步骤

### Step 1: 创建 CLIOutput 类 ✅
- 创建 `crawler/cli/output.py`
- 实现输出方法
- 集成结构化日志

### Step 2: 创建 CLI 辅助工具 ✅
- 创建 `crawler/cli/decorators.py` (错误处理装饰器)
- 创建 `crawler/utils/metadata.py` (元数据解析)

### Step 3: 重构核心命令 ✅
- `sync` - 使用 SyncService
- `generate-report` - 使用 ReportService
- `analyze-jira` - 使用 AnalysisService

### Step 4: 迁移输出到 CLIOutput ✅
- 替换所有 click.echo() 调用
- 使用结构化日志

### Step 5: 清理和验证 ✅
- 移除重复代码
- 运行测试
- 验证行数减少

## 🎯 预期结果

| 指标 | 当前 | 目标 | 减少 |
|------|------|------|------|
| 总行数 | 1057 | ~500 | -557 (-53%) |
| click.echo 调用 | 184 | ~20 | -164 (-89%) |
| 辅助函数 | 4 个 | 0 个 | -4 |
| 重复错误处理 | 多处 | 1 个装饰器 | 大幅减少 |

## ✅ 成功标准

1. cli.py 行数 < 550 行
2. 所有命令功能正常
3. 使用结构化日志
4. 代码可读性提升
5. 测试通过
