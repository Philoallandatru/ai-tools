# OpenCode 测试环境设置指南

## 📅 创建日期
2026-05-21

## 🎯 目标

建立 OpenCode 测试环境，用于：
1. 基准性能测试（对比重构前后）
2. 自动化回归测试
3. 持续集成验证

---

## 📖 什么是 OpenCode？

OpenCode 是一个开源的代码分析和测试框架，用于：
- **代码质量评估**: 静态分析、复杂度计算
- **性能基准测试**: 执行时间、内存使用
- **回归测试**: 对比不同版本的行为
- **自动化测试**: 集成到 CI/CD 流程

---

## 🔧 安装 OpenCode

### 方法 1: 使用 pip 安装（推荐）

```bash
# 安装 OpenCode
pip install opencode-analyzer

# 验证安装
opencode --version
```

### 方法 2: 从源码安装

```bash
# 克隆仓库
git clone https://github.com/opencode/opencode-analyzer.git
cd opencode-analyzer

# 安装依赖
pip install -r requirements.txt

# 安装
pip install -e .
```

### 方法 3: 使用 Docker（隔离环境）

```bash
# 拉取镜像
docker pull opencode/analyzer:latest

# 运行容器
docker run -v $(pwd):/workspace opencode/analyzer:latest
```

---

## ⚙️ 配置 OpenCode

### 1. 创建配置文件

在项目根目录创建 `.opencode.yaml`:

```yaml
# OpenCode 配置文件
version: "1.0"

# 项目信息
project:
  name: "ai-tools"
  language: "python"
  version: "1.0.0"

# 分析配置
analysis:
  # 代码质量检查
  quality:
    enabled: true
    metrics:
      - complexity
      - maintainability
      - duplication
    thresholds:
      complexity: 10
      maintainability: 60
      duplication: 5

  # 性能测试
  performance:
    enabled: true
    benchmarks:
      - name: "keyword_extraction"
        command: "python -m pytest tests/unit/test_keyword_extractor.py -v"
        timeout: 60
      - name: "unified_search"
        command: "python -m pytest tests/unit/test_unified_search.py -v"
        timeout: 120
      - name: "doc_analysis"
        command: "python cli.py analyze-doc sources/KAN-1.md"
        timeout: 300
      - name: "jira_analysis"
        command: "python cli.py analyze-jira KAN-10"
        timeout: 300

  # 回归测试
  regression:
    enabled: true
    baseline: "baseline_results.json"
    tolerance: 0.1  # 10% 性能波动容忍度

# 报告配置
reporting:
  format: ["html", "json", "markdown"]
  output_dir: "./opencode-reports"
  include_graphs: true

# 排除路径
exclude:
  - "venv/"
  - ".venv/"
  - "__pycache__/"
  - "*.pyc"
  - ".git/"
  - "node_modules/"
```

### 2. 创建基准测试脚本

创建 `tests/benchmarks/benchmark_suite.py`:

```python
#!/usr/bin/env python3
"""
OpenCode 基准测试套件
"""

import time
import psutil
import json
from pathlib import Path
from typing import Dict, Any, List
import subprocess

class BenchmarkRunner:
    """基准测试运行器"""
    
    def __init__(self, output_dir: str = "./opencode-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[Dict[str, Any]] = []
    
    def measure_performance(self, name: str, command: List[str], timeout: int = 300) -> Dict[str, Any]:
        """
        测量命令执行性能
        
        Args:
            name: 测试名称
            command: 命令列表
            timeout: 超时时间（秒）
        
        Returns:
            性能指标字典
        """
        print(f"🧪 运行基准测试: {name}")
        
        # 记录初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行命令
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
        except subprocess.TimeoutExpired:
            success = False
            output = ""
            error = f"Timeout after {timeout} seconds"
        except Exception as e:
            success = False
            output = ""
            error = str(e)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 记录最终内存
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = final_memory - initial_memory
        
        result_data = {
            "name": name,
            "success": success,
            "duration": round(duration, 2),
            "memory_delta": round(memory_delta, 2),
            "initial_memory": round(initial_memory, 2),
            "final_memory": round(final_memory, 2),
            "output_size": len(output),
            "error": error if not success else None
        }
        
        status = "✅" if success else "❌"
        print(f"  {status} 完成 (耗时: {duration:.2f}s, 内存: {memory_delta:+.2f}MB)")
        
        return result_data
    
    def run_benchmark_suite(self):
        """运行完整的基准测试套件"""
        print("=" * 60)
        print("🚀 OpenCode 基准测试套件")
        print("=" * 60)
        
        # 测试 1: 关键词提取
        self.results.append(
            self.measure_performance(
                "keyword_extraction",
                ["python", "-m", "pytest", "tests/unit/test_keyword_extractor.py", "-v"],
                timeout=60
            )
        )
        
        # 测试 2: 统一搜索
        self.results.append(
            self.measure_performance(
                "unified_search",
                ["python", "-m", "pytest", "tests/unit/test_unified_search.py", "-v"],
                timeout=120
            )
        )
        
        # 测试 3: 文档分析
        self.results.append(
            self.measure_performance(
                "doc_analysis",
                ["python", "cli.py", "analyze-doc", "sources/KAN-1.md"],
                timeout=300
            )
        )
        
        # 测试 4: Jira 分析
        self.results.append(
            self.measure_performance(
                "jira_analysis",
                ["python", "cli.py", "analyze-jira", "KAN-10"],
                timeout=300
            )
        )
        
        # 测试 5: 报告生成
        self.results.append(
            self.measure_performance(
                "report_generation",
                ["python", "cli.py", "generate-report", "--report-type", "weekly"],
                timeout=180
            )
        )
        
        # 保存结果
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """保存测试结果"""
        output_file = self.output_dir / "benchmark_results.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 结果已保存到: {output_file}")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("📊 基准测试摘要")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        total_time = sum(r["duration"] for r in self.results)
        total_memory = sum(r["memory_delta"] for r in self.results)
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"总内存变化: {total_memory:+.2f}MB")
        print()
        
        print("详细结果:")
        print("-" * 60)
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['name']:<25} {result['duration']:>6.2f}s  {result['memory_delta']:>+7.2f}MB")
    
    def compare_with_baseline(self, baseline_file: str):
        """
        与基准结果对比
        
        Args:
            baseline_file: 基准结果文件路径
        """
        baseline_path = Path(baseline_file)
        if not baseline_path.exists():
            print(f"⚠️  基准文件不存在: {baseline_file}")
            print("   使用当前结果作为基准")
            self.save_baseline(baseline_file)
            return
        
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)
        
        baseline_results = {r["name"]: r for r in baseline_data["results"]}
        
        print("\n" + "=" * 60)
        print("📈 性能对比（当前 vs 基准）")
        print("=" * 60)
        
        for result in self.results:
            name = result["name"]
            if name not in baseline_results:
                print(f"⚠️  {name}: 无基准数据")
                continue
            
            baseline = baseline_results[name]
            
            # 计算变化
            time_delta = result["duration"] - baseline["duration"]
            time_percent = (time_delta / baseline["duration"]) * 100 if baseline["duration"] > 0 else 0
            
            memory_delta = result["memory_delta"] - baseline["memory_delta"]
            
            # 判断趋势
            time_trend = "↗" if time_delta > 0 else "↘" if time_delta < 0 else "→"
            memory_trend = "↗" if memory_delta > 0 else "↘" if memory_delta < 0 else "→"
            
            print(f"\n{name}:")
            print(f"  时间: {result['duration']:.2f}s (基准: {baseline['duration']:.2f}s, {time_delta:+.2f}s {time_trend} {time_percent:+.1f}%)")
            print(f"  内存: {result['memory_delta']:+.2f}MB (基准: {baseline['memory_delta']:+.2f}MB, {memory_delta:+.2f}MB {memory_trend})")
    
    def save_baseline(self, baseline_file: str):
        """保存当前结果作为基准"""
        baseline_path = Path(baseline_file)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 基准已保存到: {baseline_file}")

if __name__ == "__main__":
    runner = BenchmarkRunner()
    runner.run_benchmark_suite()
    runner.compare_with_baseline("baseline_results.json")
```

---

## 🚀 运行基准测试

### 1. 首次运行（建立基准）

```bash
# 运行基准测试套件
python tests/benchmarks/benchmark_suite.py

# 这将创建 baseline_results.json 作为基准
```

### 2. 后续运行（对比基准）

```bash
# 重构代码后运行
python tests/benchmarks/benchmark_suite.py

# 自动对比与基准的差异
```

### 3. 使用 OpenCode CLI

```bash
# 运行完整分析
opencode analyze --config .opencode.yaml

# 仅运行性能测试
opencode benchmark --config .opencode.yaml

# 生成报告
opencode report --format html --output ./opencode-reports
```

---

## 📊 解读测试结果

### 性能指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| **执行时间** | 命令完成所需时间 | 与基准相比 ±10% |
| **内存使用** | 内存增量（MB） | 与基准相比 ±20% |
| **成功率** | 测试通过率 | 100% |
| **输出大小** | 生成文件大小 | 与基准相比 ±5% |

### 性能趋势判断

**改善** ✅:
- 执行时间减少 > 10%
- 内存使用减少 > 20%
- 成功率保持 100%

**稳定** ➡️:
- 执行时间变化 < 10%
- 内存使用变化 < 20%
- 成功率保持 100%

**退化** ❌:
- 执行时间增加 > 10%
- 内存使用增加 > 20%
- 成功率下降

---

## 🔄 持续集成配置

### GitHub Actions 示例

创建 `.github/workflows/opencode-test.yml`:

```yaml
name: OpenCode Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install opencode-analyzer
    
    - name: Run OpenCode analysis
      run: |
        opencode analyze --config .opencode.yaml
    
    - name: Run benchmark suite
      run: |
        python tests/benchmarks/benchmark_suite.py
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: opencode-reports
        path: opencode-reports/
    
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const results = JSON.parse(fs.readFileSync('opencode-reports/benchmark_results.json'));
          // 格式化并发布评论
```

---

## 📝 测试检查清单

### 环境准备
- [ ] OpenCode 已安装
- [ ] 配置文件已创建（.opencode.yaml）
- [ ] 基准测试脚本已创建
- [ ] 测试数据准备完整

### 基准建立
- [ ] 首次运行基准测试
- [ ] 基准结果已保存（baseline_results.json）
- [ ] 基准数据合理（无异常值）

### 回归测试
- [ ] 重构后运行测试
- [ ] 对比基准结果
- [ ] 性能变化在容忍范围内
- [ ] 无功能退化

### 报告生成
- [ ] HTML 报告生成
- [ ] JSON 数据导出
- [ ] Markdown 摘要生成
- [ ] 图表可视化

---

## 🐛 故障排查

### 问题 1: OpenCode 安装失败

**症状**: `pip install opencode-analyzer` 失败

**解决方案**:
```bash
# 方案 1: 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple opencode-analyzer

# 方案 2: 从源码安装
git clone https://github.com/opencode/opencode-analyzer.git
cd opencode-analyzer
pip install -e .

# 方案 3: 使用 Docker
docker pull opencode/analyzer:latest
```

---

### 问题 2: 基准测试超时

**症状**: 测试运行超过设定的超时时间

**解决方案**:
1. 增加超时时间（在配置文件中）
2. 优化测试数据大小
3. 检查 LLM 服务器响应速度
4. 使用更快的硬件

---

### 问题 3: 内存使用过高

**症状**: 测试过程中内存使用超过预期

**解决方案**:
1. 检查是否有内存泄漏
2. 减少批处理大小
3. 增加垃圾回收频率
4. 使用内存分析工具（memory_profiler）

---

### 问题 4: 结果不一致

**症状**: 多次运行结果差异较大

**解决方案**:
1. 确保测试环境一致（关闭其他程序）
2. 多次运行取平均值
3. 检查是否有随机因素（LLM 温度参数）
4. 固定随机种子

---

## 📚 参考资料

- [OpenCode 官方文档](https://opencode.io/docs)
- [Python 性能测试最佳实践](https://docs.python.org/3/library/profile.html)
- [基准测试指南](https://github.com/python/performance)
- [项目 README](../README.md)

---

## 🎯 下一步

1. **建立基准**: 运行首次测试，保存基准数据
2. **持续监控**: 每次重构后运行测试
3. **性能优化**: 根据测试结果优化瓶颈
4. **自动化**: 集成到 CI/CD 流程

---

## ✅ 完成标准

- [ ] OpenCode 环境搭建完成
- [ ] 配置文件创建完成
- [ ] 基准测试脚本可运行
- [ ] 基准数据已建立
- [ ] 测试报告可生成
- [ ] 文档完整清晰
