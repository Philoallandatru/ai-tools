# Claude Code Skills 测试计划

## 📅 创建日期
2026-05-21

## 🎯 测试目标

验证三个 Claude Code Skills 的功能完整性、性能和用户体验：
1. `/analyze-requirements` - 智能需求分析
2. `/investigate-jira` - Jira Issue 深度调查
3. `/smart-search` - 智能语义搜索

---

## 📋 测试环境

### 系统要求
- **操作系统**: Windows 11 Pro for Workstations
- **Python**: 3.10+
- **Claude Code**: 最新版本
- **LLM**: Qwen3.5-9B-IQ4_XS.gguf (本地)
- **LLM Server**: llama.cpp (http://127.0.0.1:8080)

### 测试数据
- **Jira Issues**: KAN-1, KAN-2, KAN-10, KAN-14
- **需求文档**: sources/KAN-*.md
- **代码库**: sources/ 目录
- **Wiki**: 已编译的知识库

---

## 🧪 测试用例

### 1. `/analyze-requirements` Skill 测试

#### 测试用例 1.1: Markdown 文档分析
**目标**: 验证 Markdown 文档的端到端分析流程

**输入**:
```bash
/analyze-requirements sources/KAN-1.md
```

**预期输出**:
- ✅ 文档成功切分为多个小节
- ✅ 每个小节提取关键词（至少 3-5 个）
- ✅ 搜索到相关代码片段（至少 3 个）
- ✅ LLM 分析相关性（评分 0-10）
- ✅ 生成完整的分析报告（reports/doc_analysis_*.md）
- ✅ 报告包含：目录、原始内容、关键词、检索结果、LLM 分析

**性能要求**:
- 处理时间 < 3 分钟（9 个小节）
- LLM 调用次数 < 20 次
- 报告大小 > 50KB

**验证步骤**:
1. 运行命令
2. 检查控制台输出（进度信息）
3. 验证报告文件生成
4. 检查报告内容完整性
5. 验证关键词提取质量
6. 验证代码匹配相关性

---

#### 测试用例 1.2: PDF 文档分析（如果支持）
**目标**: 验证 PDF 转换和分析流程

**输入**:
```bash
/analyze-requirements docs/requirements.pdf
```

**预期输出**:
- ✅ PDF 自动转换为 Markdown
- ✅ 转换后的文档保存到 sources/
- ✅ 后续流程与测试用例 1.1 相同

**性能要求**:
- PDF 转换时间 < 1 分钟
- 总处理时间 < 5 分钟

---

#### 测试用例 1.3: 错误处理
**目标**: 验证异常情况的处理

**测试场景**:
1. **文件不存在**
   ```bash
   /analyze-requirements nonexistent.md
   ```
   - 预期: 友好的错误提示

2. **不支持的文件格式**
   ```bash
   /analyze-requirements test.txt
   ```
   - 预期: 提示仅支持 PDF 和 Markdown

3. **LLM 服务不可用**
   - 停止 LLM 服务器
   - 运行分析命令
   - 预期: 降级到正则表达式提取，继续执行

---

### 2. `/investigate-jira` Skill 测试

#### 测试用例 2.1: 完整 Issue 调查
**目标**: 验证 Jira Issue 的深度分析流程

**输入**:
```bash
/investigate-jira KAN-10
```

**预期输出**:
- ✅ 成功获取 Jira Issue 数据
- ✅ 执行 9 个分析器：
  1. issue_summary - 问题摘要
  2. root_cause - 根因分析
  3. similar_jira - 相似问题搜索
  4. knowledge - 知识检索（Wiki + 代码）
  5. actions - 解决方案建议
  6. closed_loop - 闭环检查
  7. code_coverage - 代码覆盖分析
  8. comments - 评论分析
  9. custom_技术债务评估 - 技术债务评估
- ✅ 生成完整的调查报告（reports/jira_analysis_*.md）
- ✅ 报告包含所有分析器的结果

**性能要求**:
- 处理时间 < 2 分钟
- LLM 调用次数 15-20 次
- 报告大小 > 30KB

**验证步骤**:
1. 运行命令
2. 检查控制台输出（分析器执行进度）
3. 验证报告文件生成
4. 检查每个分析器的输出质量
5. 验证相似问题匹配准确性
6. 验证知识检索相关性

---

#### 测试用例 2.2: 指定 Wiki 调查
**目标**: 验证手动指定 Wiki 的功能

**输入**:
```bash
/investigate-jira KAN-10 --wiki kan-project
```

**预期输出**:
- ✅ 使用指定的 Wiki 进行知识检索
- ✅ 其他流程与测试用例 2.1 相同

---

#### 测试用例 2.3: 错误处理
**目标**: 验证异常情况的处理

**测试场景**:
1. **Issue 不存在**
   ```bash
   /investigate-jira KAN-999
   ```
   - 预期: 提示 Issue 不存在

2. **Jira 连接失败**
   - 修改 config.yaml 中的 Jira URL
   - 运行命令
   - 预期: 友好的连接错误提示

3. **Wiki 不存在**
   ```bash
   /investigate-jira KAN-10 --wiki nonexistent-wiki
   ```
   - 预期: 提示 Wiki 不存在，建议可用的 Wiki

---

### 3. `/smart-search` Skill 测试

#### 测试用例 3.1: 自然语言搜索
**目标**: 验证自然语言查询的理解和搜索

**输入**:
```bash
/smart-search "如何实现 NVMe 控制器重置？"
```

**预期输出**:
- ✅ 自动提取关键词（NVMe, Controller, Reset, 等）
- ✅ 搜索代码和文档
- ✅ LLM 相关性排序（0-10 分）
- ✅ 返回 Top 10 结果
- ✅ 每个结果包含：文件路径、相关性评分、匹配原因

**性能要求**:
- 搜索时间 < 5 秒
- LLM 调用次数 < 3 次
- 结果数量 5-10 个

**验证步骤**:
1. 运行命令
2. 检查关键词提取质量
3. 验证搜索结果相关性
4. 检查相关性评分合理性
5. 验证结果排序正确性

---

#### 测试用例 3.2: 指定搜索范围
**目标**: 验证搜索范围过滤功能

**输入**:
```bash
/smart-search "错误处理" --scope code
/smart-search "架构设计" --scope docs
```

**预期输出**:
- ✅ 仅搜索指定范围的内容
- ✅ 结果符合范围限制

---

#### 测试用例 3.3: 调整相关性阈值
**目标**: 验证相关性过滤功能

**输入**:
```bash
/smart-search "NVMe" --min-score 8.0
/smart-search "NVMe" --min-score 3.0
```

**预期输出**:
- ✅ 高阈值返回少量高质量结果
- ✅ 低阈值返回更多结果

---

#### 测试用例 3.4: 错误处理
**目标**: 验证异常情况的处理

**测试场景**:
1. **空查询**
   ```bash
   /smart-search ""
   ```
   - 预期: 提示查询不能为空

2. **无结果**
   ```bash
   /smart-search "完全不相关的内容xyz123"
   ```
   - 预期: 提示未找到相关结果

3. **LLM 服务不可用**
   - 停止 LLM 服务器
   - 运行搜索命令
   - 预期: 降级到基础搜索（无 LLM 排序）

---

## 📊 性能基准测试

### 测试指标

| Skill | 测试场景 | 目标时间 | LLM 调用 | 内存使用 |
|-------|---------|---------|---------|---------|
| analyze-requirements | 9 节文档 | < 3 分钟 | < 20 次 | < 500MB |
| investigate-jira | 完整调查 | < 2 分钟 | 15-20 次 | < 300MB |
| smart-search | 自然语言查询 | < 5 秒 | < 3 次 | < 200MB |

### 测试方法

1. **时间测量**
   ```bash
   # Windows
   Measure-Command { /analyze-requirements sources/KAN-1.md }
   
   # 或使用 Python
   import time
   start = time.time()
   # 运行 Skill
   end = time.time()
   print(f"耗时: {end - start:.2f} 秒")
   ```

2. **LLM 调用统计**
   - 检查日志文件
   - 统计 LLM API 调用次数

3. **内存监控**
   ```bash
   # Windows Task Manager
   # 或使用 Python
   import psutil
   process = psutil.Process()
   print(f"内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB")
   ```

---

## 🔍 质量验证

### 关键词提取质量

**评估标准**:
- ✅ 提取的关键词与文档主题相关
- ✅ 包含技术术语和标识符
- ✅ 过滤掉停用词和无意义词汇
- ✅ 关键词数量合理（3-10 个）

**验证方法**:
1. 人工审核提取的关键词
2. 对比预期关键词列表
3. 计算准确率和召回率

---

### 搜索相关性质量

**评估标准**:
- ✅ Top-1 准确率 > 80%（最相关的结果排在第一）
- ✅ Top-5 准确率 > 95%（前 5 个结果中包含相关内容）
- ✅ 相关性评分合理（高相关 > 7 分，低相关 < 4 分）

**验证方法**:
1. 准备测试查询和预期结果
2. 运行搜索并记录结果
3. 计算准确率指标
4. 人工审核评分合理性

---

### 报告质量

**评估标准**:
- ✅ 报告结构清晰（目录、章节、格式）
- ✅ 内容完整（所有分析器都有输出）
- ✅ 分析深度足够（不是简单罗列）
- ✅ 建议可操作（具体、明确）

**验证方法**:
1. 检查报告 Markdown 格式
2. 验证所有章节存在
3. 人工审核分析质量
4. 评估建议的可操作性

---

## 🐛 已知问题和限制

### 当前限制
1. **PDF 支持**: 需要外部工具（pdf2md）
2. **大文档处理**: 超过 100 页的文档可能超时
3. **LLM 依赖**: 本地 LLM 性能影响整体速度
4. **中文支持**: 某些分析器对中文支持有限

### 待改进项
1. **并行处理**: 多个小节可以并行分析
2. **缓存机制**: 重复查询应使用缓存
3. **增量分析**: 文档变更时只分析变更部分
4. **交互式细化**: 支持用户细化搜索结果

---

## 📝 测试报告模板

### 测试执行记录

**测试日期**: YYYY-MM-DD  
**测试人员**: [姓名]  
**测试环境**: [环境描述]

#### Skill: [Skill 名称]

**测试用例**: [用例编号和名称]

**执行步骤**:
1. [步骤 1]
2. [步骤 2]
3. ...

**实际结果**:
- [结果描述]

**性能数据**:
- 执行时间: X 秒
- LLM 调用: X 次
- 内存使用: X MB

**问题记录**:
- [问题 1]
- [问题 2]

**结论**: ✅ 通过 / ❌ 失败

---

## 🚀 自动化测试脚本

### 测试脚本示例

```python
#!/usr/bin/env python3
"""
Skills 自动化测试脚本
"""

import subprocess
import time
import json
from pathlib import Path

class SkillTester:
    def __init__(self):
        self.results = []
    
    def test_analyze_requirements(self):
        """测试 analyze-requirements Skill"""
        print("🧪 测试 /analyze-requirements...")
        
        start = time.time()
        result = subprocess.run(
            ["python", "cli.py", "analyze-doc", "sources/KAN-1.md"],
            capture_output=True,
            text=True,
            timeout=300
        )
        duration = time.time() - start
        
        success = result.returncode == 0
        report_exists = Path("reports").glob("doc_analysis_KAN-1_*.md")
        
        self.results.append({
            "skill": "analyze-requirements",
            "success": success and any(report_exists),
            "duration": duration,
            "output": result.stdout
        })
        
        print(f"  ✅ 完成 (耗时: {duration:.2f}s)" if success else "  ❌ 失败")
    
    def test_investigate_jira(self):
        """测试 investigate-jira Skill"""
        print("🧪 测试 /investigate-jira...")
        
        start = time.time()
        result = subprocess.run(
            ["python", "cli.py", "analyze-jira", "KAN-10"],
            capture_output=True,
            text=True,
            timeout=300
        )
        duration = time.time() - start
        
        success = result.returncode == 0
        report_exists = Path("reports").glob("jira_analysis_KAN-10_*.md")
        
        self.results.append({
            "skill": "investigate-jira",
            "success": success and any(report_exists),
            "duration": duration,
            "output": result.stdout
        })
        
        print(f"  ✅ 完成 (耗时: {duration:.2f}s)" if success else "  ❌ 失败")
    
    def test_smart_search(self):
        """测试 smart-search Skill"""
        print("🧪 测试 /smart-search...")
        
        start = time.time()
        result = subprocess.run(
            ["python", "cli.py", "search", "NVMe 控制器重置"],
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = time.time() - start
        
        success = result.returncode == 0
        has_results = "找到" in result.stdout or "results" in result.stdout
        
        self.results.append({
            "skill": "smart-search",
            "success": success and has_results,
            "duration": duration,
            "output": result.stdout
        })
        
        print(f"  ✅ 完成 (耗时: {duration:.2f}s)" if success else "  ❌ 失败")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🚀 开始 Skills 自动化测试")
        print("=" * 60)
        
        self.test_analyze_requirements()
        self.test_investigate_jira()
        self.test_smart_search()
        
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        for result in self.results:
            status = "✅ 通过" if result["success"] else "❌ 失败"
            print(f"{result['skill']}: {status} (耗时: {result['duration']:.2f}s)")
        
        # 保存结果
        with open("test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print("\n✅ 测试结果已保存到 test_results.json")

if __name__ == "__main__":
    tester = SkillTester()
    tester.run_all_tests()
```

**使用方法**:
```bash
python tests/test_skills.py
```

---

## 📚 参考资料

- [Claude Code Skills 文档](https://docs.anthropic.com/claude/docs/skills)
- [项目 README](../README.md)
- [Skill 开发计划](./skill_development_plan.md)
- [代码质量改进](./code_quality_improvements.md)

---

## ✅ 测试检查清单

### 测试前准备
- [ ] LLM 服务器运行正常（http://127.0.0.1:8080）
- [ ] 测试数据准备完整（Jira Issues, 文档）
- [ ] 配置文件正确（config.yaml）
- [ ] 依赖安装完整（requirements.txt）

### 功能测试
- [ ] `/analyze-requirements` 基础功能
- [ ] `/analyze-requirements` 错误处理
- [ ] `/investigate-jira` 基础功能
- [ ] `/investigate-jira` 错误处理
- [ ] `/smart-search` 基础功能
- [ ] `/smart-search` 错误处理

### 性能测试
- [ ] 执行时间符合要求
- [ ] LLM 调用次数合理
- [ ] 内存使用在限制内

### 质量验证
- [ ] 关键词提取准确
- [ ] 搜索相关性高
- [ ] 报告质量良好
- [ ] 建议可操作

### 文档更新
- [ ] 测试结果记录
- [ ] 问题清单更新
- [ ] 改进建议整理
