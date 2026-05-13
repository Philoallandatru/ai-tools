# CLI 命令测试指南

本文档说明如何在每次修改后测试所有 CLI 命令，确保功能正常工作。

## 测试脚本

项目提供了两个测试脚本，覆盖 README.md 中的所有命令：

- **Linux/Mac**: `test_all_commands.sh`
- **Windows**: `test_all_commands.bat`

## 快速开始

### Linux/Mac

```bash
# 添加执行权限
chmod +x test_all_commands.sh

# 运行测试
./test_all_commands.sh
```

### Windows

```cmd
# 直接运行
test_all_commands.bat
```

## 测试覆盖范围

测试脚本覆盖以下 9 个功能模块：

### 1. 搜索功能 (5 个测试)
- ✅ 基本搜索
- ✅ 搜索 Jira issues
- ✅ 正则表达式搜索
- ✅ 带上下文搜索
- ✅ 只显示统计信息

### 2. Jira 查询功能 (4 个测试)
- ✅ 查找特定 Jira issue
- ✅ 列出所有 Jira issues
- ✅ 按状态过滤 Jira
- ✅ 按优先级过滤 Jira

### 3. Jira 分析功能 (2 个测试)
- ✅ 使用 Mock LLM 分析 Jira
- ⏭️ 使用真实 LLM 分析 Jira（需要 LLM 服务运行）

### 4. 文档分析功能 (3 个测试)
- ✅ 分析文档（dry-run 模式）
- ⏭️ 分析文档（真实 LLM）
- ✅ 分析文档（指定输出路径）

### 5. 报告生成功能 (5 个测试)
- ✅ 生成周报
- ✅ 生成日报
- ✅ 生成月报
- ✅ 生成指定时间范围报告
- ✅ 生成 JSON 格式报告

### 6. 筛选导出功能 (3 个测试)
- ✅ 导出今天更新的进行中 issues
- ✅ 导出最近 7 天更新的 issues
- ✅ 导出昨天更新的 Confluence 页面

### 7. 文档拆分功能 (1 个测试)
- ✅ 拆分长文档（如果测试文件存在）

### 8. Wiki 功能 (3 个测试)
- ✅ 查看 Wiki 状态
- ⏭️ 编译知识库（耗时较长）
- ⏭️ 查询知识库（需要先编译）

### 9. 同步功能 (1 个测试)
- ⏭️ 同步 Atlassian 数据（避免实际调用 API）

**图例**:
- ✅ 默认运行的测试
- ⏭️ 默认跳过的测试（需要外部服务或耗时较长）

## 测试输出

测试脚本会显示每个测试的结果：

```
==========================================
1. 搜索功能测试
==========================================

[TEST 1] 基本搜索
命令: uv run python cli.py search NVMe
✓ PASSED

[TEST 2] 搜索 Jira issues
命令: uv run python cli.py search 测试 --type jira
✓ PASSED

...

==========================================
测试总结
==========================================
总测试数: 27
通过: 20
失败: 0
跳过: 7

✓ 所有测试通过！
```

## 修改后的测试流程

每次修改代码后，建议按以下流程测试：

### 1. 运行单元测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块的测试
pytest tests/unit/test_llm_client.py -v
```

### 2. 运行集成测试

```bash
# 运行所有集成测试
pytest tests/integration/ -v
```

### 3. 运行 CLI 命令测试

```bash
# Linux/Mac
./test_all_commands.sh

# Windows
test_all_commands.bat
```

### 4. 运行 E2E 测试（可选）

```bash
# 运行端到端测试
python run_e2e_tests.py
```

## 自定义测试

如果需要测试特定命令，可以直接运行：

```bash
# 测试搜索功能
uv run python cli.py search "测试关键词"

# 测试 Jira 查询
uv run python cli.py find-jira KAN-1

# 测试报告生成
uv run python cli.py generate-report
```

## 跳过的测试

某些测试默认跳过，原因如下：

1. **真实 LLM 测试**: 需要 LLM 服务运行（LM Studio、Ollama 等）
2. **Wiki 编译**: 耗时较长（几分钟）
3. **同步功能**: 避免实际调用 Atlassian API

如需运行这些测试，可以手动执行相应命令。

## 启用跳过的测试

要运行所有测试（包括跳过的），需要：

1. **启动 LLM 服务**:
   ```bash
   # LM Studio: 启动本地服务器（默认 http://127.0.0.1:1234）
   # Ollama: ollama serve
   ```

2. **修改测试脚本**:
   将 `should_skip="true"` 改为 `should_skip="false"`

3. **运行完整测试**:
   ```bash
   ./test_all_commands.sh
   ```

## 持续集成

可以将测试脚本集成到 CI/CD 流程中：

```yaml
# .github/workflows/test.yml
name: Test CLI Commands

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run CLI tests
        run: ./test_all_commands.sh
```

## 故障排查

### 测试失败

如果测试失败，检查：

1. **依赖安装**: `uv sync` 是否成功
2. **配置文件**: `config.yaml` 是否存在
3. **源文件**: `sources/` 目录是否有数据
4. **权限问题**: 脚本是否有执行权限

### 命令找不到

```bash
# 确保 uv 已安装
pip install uv

# 确保依赖已安装
uv sync
```

### 编码问题（Windows）

如果遇到编码错误，确保：
- 终端使用 UTF-8 编码
- 配置文件使用 UTF-8 保存

## 添加新测试

当添加新命令时，更新测试脚本：

1. 在相应的功能模块下添加测试
2. 使用 `run_test` 函数
3. 更新本文档的测试覆盖范围

示例：

```bash
# 在 test_all_commands.sh 中添加
run_test "新命令测试" \
    "uv run python cli.py new-command --option value"
```

## 相关文档

- [README.md](../README.md) - 所有命令的使用说明
- [USAGE.md](USAGE.md) - 详细使用指南
- [测试文档](../tests/README.md) - 单元测试和集成测试说明
