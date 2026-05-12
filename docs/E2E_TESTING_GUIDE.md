# 端到端测试指南

本文档介绍如何运行和维护端到端测试。

---

## 📋 测试概述

端到端测试覆盖以下功能：

### 1. Confluence 同步测试
- ✅ 完整的空间同步流程
- ✅ 页面数据持久化
- ✅ 状态文件更新

### 2. Jira 同步测试
- ✅ 完整的项目同步流程
- ✅ 问题数据持久化
- ✅ 状态文件更新

### 3. 报告生成测试（需要本地 LLM）
- ✅ 周报生成
- ✅ 月报生成
- ✅ LLM 分析内容验证

### 4. Jira 分析测试（需要本地 LLM）
- ✅ 单个问题分析
- ✅ 批量问题分析
- ✅ 分析报告生成

### 5. 错误处理测试
- ✅ 网络错误重试
- ✅ 无效配置处理
- ✅ LLM 超时处理

### 6. 完整工作流测试（需要本地 LLM）
- ✅ 同步 → 分析 → 报告生成
- ✅ 多服务协作
- ✅ 端到端数据流

---

## 🚀 快速开始

### 前置条件

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **启动本地 LLM（可选，用于完整测试）**
   ```bash
   # 启动 Ollama
   ollama serve
   
   # 拉取模型
   ollama pull qwen2.5-coder:7b
   ```

### 运行测试

#### 方式 1: 使用测试运行脚本（推荐）

```bash
python run_e2e_tests.py
```

脚本会自动：
- ✅ 检查 Ollama 是否运行
- ✅ 检查模型是否可用
- ✅ 根据环境选择运行哪些测试
- ✅ 生成覆盖率报告

#### 方式 2: 直接使用 pytest

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v -s

# 只运行不需要 LLM 的测试
pytest tests/e2e/ -v -s -m "not requires_local_llm"

# 只运行需要 LLM 的测试
pytest tests/e2e/ -v -s -m "requires_local_llm"

# 运行特定测试类
pytest tests/e2e/test_full_workflow.py::TestConfluenceE2E -v -s

# 运行特定测试方法
pytest tests/e2e/test_full_workflow.py::TestConfluenceE2E::test_confluence_sync_workflow -v -s
```

---

## 📊 测试标记

测试使用 pytest 标记来分类：

### `@requires_local_llm`
标记需要本地 LLM 的测试。如果 LLM 不可用，这些测试会被跳过。

**使用场景**:
- 报告生成测试
- Jira 分析测试
- 完整工作流测试

**检查逻辑**:
```python
def check_local_llm_available() -> bool:
    """检查本地 LLM 是否可用。"""
    try:
        client = LLMClient(
            provider="openai",
            model="qwen2.5-coder:7b",
            base_url="http://localhost:11434/v1",
            api_key="dummy",
        )
        response = client.generate("test", max_tokens=10)
        return bool(response)
    except Exception:
        return False
```

---

## 🧪 测试结构

### 测试文件组织

```
tests/e2e/
├── __init__.py
└── test_full_workflow.py    # 完整的端到端测试
```

### 测试类组织

```python
# 基础功能测试（不需要 LLM）
class TestConfluenceE2E:
    """Confluence 端到端测试。"""

class TestJiraE2E:
    """Jira 端到端测试。"""

class TestErrorHandlingE2E:
    """错误处理端到端测试。"""

# 需要 LLM 的测试
@requires_local_llm
class TestReportGenerationE2E:
    """报告生成端到端测试。"""

@requires_local_llm
class TestJiraAnalysisE2E:
    """Jira 分析端到端测试。"""

@requires_local_llm
class TestFullWorkflowE2E:
    """完整工作流端到端测试。"""
```

---

## 🔧 Fixtures

### `temp_workspace`
创建临时工作空间，包含所有必要的目录结构。

**提供**:
- `workspace`: 临时工作目录路径
- `sources_dir`: 源数据目录
- `reports_dir`: 报告目录
- `state_file`: 状态文件路径
- `error_log`: 错误日志路径

**自动清理**: 测试结束后自动删除

### `e2e_config`
创建端到端测试配置。

**包含**:
- Confluence 和 Jira 源配置
- 输出目录配置
- 同步状态配置
- 错误处理配置
- LLM 配置（指向本地 Ollama）

### `mock_confluence_data`
提供模拟的 Confluence 数据。

**包含**:
- 空间信息
- 2 个示例页面（架构文档、API 文档）

### `mock_jira_data`
提供模拟的 Jira 数据。

**包含**:
- 项目信息
- 2 个示例问题（功能开发、Bug 修复）
- 评论数据

---

## 📝 编写新测试

### 基础测试（不需要 LLM）

```python
class TestMyFeatureE2E:
    """我的功能端到端测试。"""

    def test_my_workflow(self, e2e_config, temp_workspace, mocker):
        """测试我的工作流。"""
        # 1. Mock 外部依赖
        mock_api = mocker.patch("crawler.services.my_service.MyAPI")
        mock_api.return_value.fetch_data.return_value = {"data": "test"}

        # 2. 创建服务
        service = MyService(e2e_config)

        # 3. 执行操作
        result = service.do_something()

        # 4. 验证结果
        assert result["status"] == "success"

        # 5. 验证文件系统状态
        output_file = temp_workspace["workspace"] / "output.txt"
        assert output_file.exists()
```

### 需要 LLM 的测试

```python
@requires_local_llm
class TestMyLLMFeatureE2E:
    """我的 LLM 功能端到端测试。"""

    def test_llm_workflow(self, e2e_config, temp_workspace):
        """测试 LLM 工作流。"""
        # 1. 创建服务（会使用真实的本地 LLM）
        service = MyLLMService(e2e_config)

        # 2. 执行 LLM 操作
        result = service.analyze_with_llm("test input")

        # 3. 验证 LLM 响应
        assert result["status"] == "success"
        assert len(result["analysis"]) > 100  # LLM 应该生成有意义的内容
```

---

## 🐛 调试测试

### 查看详细输出

```bash
pytest tests/e2e/ -v -s --log-cli-level=DEBUG
```

### 保留临时文件

修改 `temp_workspace` fixture:

```python
@pytest.fixture
def temp_workspace():
    """创建临时工作空间。"""
    tmpdir = tempfile.mkdtemp(prefix="e2e_test_")
    workspace = Path(tmpdir)
    
    # ... 创建目录结构 ...
    
    yield {...}
    
    # 注释掉清理代码以保留文件
    # shutil.rmtree(tmpdir)
    print(f"临时文件保留在: {tmpdir}")
```

### 单独运行失败的测试

```bash
pytest tests/e2e/test_full_workflow.py::TestFullWorkflowE2E::test_complete_workflow -v -s
```

---

## 📈 覆盖率报告

### 生成覆盖率报告

```bash
pytest tests/e2e/ --cov=crawler --cov-report=html --cov-report=term
```

### 查看 HTML 报告

```bash
# 报告生成在 htmlcov/ 目录
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

---

## ⚡ 性能考虑

### LLM 调用优化

1. **使用较小的模型**: `qwen2.5-coder:7b` 而不是更大的模型
2. **设置合理的超时**: 默认 120 秒
3. **限制生成长度**: 使用 `max_tokens` 参数

### 测试并行化

```bash
# 使用 pytest-xdist 并行运行测试
pip install pytest-xdist

# 运行测试（使用 4 个进程）
pytest tests/e2e/ -n 4
```

**注意**: 需要 LLM 的测试不适合并行运行，因为会竞争 LLM 资源。

---

## 🔍 常见问题

### Q: 测试被跳过，显示 "本地 LLM 不可用"

**A**: 确保 Ollama 正在运行并且模型已下载：

```bash
# 检查 Ollama 状态
curl http://localhost:11434/api/tags

# 启动 Ollama
ollama serve

# 下载模型
ollama pull qwen2.5-coder:7b
```

### Q: LLM 测试超时

**A**: 增加超时时间或使用更快的模型：

```python
e2e_config["llm"]["timeout"] = 300  # 5 分钟
```

### Q: 测试失败，提示 "ModuleNotFoundError"

**A**: 确保安装了所有依赖：

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Q: Mock 数据不够真实

**A**: 可以从真实环境导出数据作为测试数据：

```bash
# 导出真实的 Jira 问题
python cli.py sync-jira --source my-jira --project TEST
# 然后从 sources/jira/my-jira/TEST/ 复制数据到测试 fixtures
```

---

## 📚 相关文档

- [测试策略文档](./TESTING_STRATEGY.md)
- [单元测试指南](./UNIT_TESTING.md)
- [集成测试指南](./INTEGRATION_TESTING.md)
- [可观测性指南](./OBSERVABILITY_GUIDE.md)

---

## 🎯 最佳实践

### 1. 测试隔离
- ✅ 每个测试使用独立的临时目录
- ✅ Mock 所有外部 API 调用
- ✅ 不依赖测试执行顺序

### 2. 测试数据
- ✅ 使用真实但简化的测试数据
- ✅ 覆盖常见场景和边界情况
- ✅ 数据应该有代表性

### 3. 断言
- ✅ 验证关键结果，不是所有细节
- ✅ 使用有意义的断言消息
- ✅ 验证文件系统状态

### 4. 性能
- ✅ 控制测试运行时间（< 5 分钟）
- ✅ 使用较小的测试数据集
- ✅ 合理使用 Mock

### 5. 可维护性
- ✅ 清晰的测试命名
- ✅ 适当的注释
- ✅ 复用 fixtures 和辅助函数

---

**最后更新**: 2026-05-13  
**维护者**: AI Tools Team
