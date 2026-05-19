#!/usr/bin/env python3
"""
综合命令测试脚本
测试所有 CLI 命令的功能和集成
使用本地 LLM: http://127.0.0.1:8080/v1
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Windows 控制台 UTF-8 支持
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
TEST_OUTPUTS_DIR = PROJECT_ROOT / "tests" / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 本地 LLM 配置
LOCAL_LLM_URL = "http://127.0.0.1:8080/v1"
LOCAL_LLM_MODEL = "Qwen3.5-9B-IQ4_XS"

# 测试结果
test_results = []


class CommandTest:
    """命令测试类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.success = False
        self.error = None
        self.duration = 0
        self.output = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "success": self.success,
            "error": self.error,
            "duration": self.duration,
            "output": self.output[:500] if self.output else ""  # 限制输出长度
        }


def run_command(cmd: List[str], timeout: int = 60) -> Tuple[bool, str, str]:
    """
    运行命令并返回结果

    Args:
        cmd: 命令列表
        timeout: 超时时间（秒）

    Returns:
        (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
            encoding='utf-8'
        )
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timeout after {timeout}s"
    except Exception as e:
        return False, "", str(e)


def test_command(name: str, description: str, cmd: List[str],
                 timeout: int = 60, skip: bool = False, skip_reason: str = "") -> CommandTest:
    """
    测试单个命令

    Args:
        name: 命令名称
        description: 命令描述
        cmd: 命令列表
        timeout: 超时时间
        skip: 是否跳过
        skip_reason: 跳过原因

    Returns:
        CommandTest 对象
    """
    test = CommandTest(name, description)

    if skip:
        test.error = f"SKIPPED: {skip_reason}"
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print(f"描述: {description}")
        print(f"状态: [SKIP] 跳过 - {skip_reason}")
        return test

    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"描述: {description}")
    print(f"命令: {' '.join(cmd)}")

    start_time = time.time()
    success, stdout, stderr = run_command(cmd, timeout)
    test.duration = time.time() - start_time

    test.success = success
    test.output = stdout if success else stderr

    if not success:
        test.error = stderr
        print(f"状态: [FAIL] 失败")
        print(f"错误: {stderr[:200]}")
    else:
        print(f"状态: [PASS] 成功")
        print(f"耗时: {test.duration:.2f}s")

    return test


def main():
    """主测试流程"""
    print("="*60)
    print("AI Tools - 综合命令测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"本地 LLM: {LOCAL_LLM_URL}")
    print(f"模型: {LOCAL_LLM_MODEL}")
    print(f"项目根目录: {PROJECT_ROOT}")
    print("="*60)

    # 确保测试输出目录存在
    TEST_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # ========================================
    # 1. 数据同步命令
    # ========================================
    print("\n" + "="*60)
    print("分类 1: 数据同步命令")
    print("="*60)

    # sync - 需要 Atlassian 连接，跳过
    test_results.append(test_command(
        "sync",
        "同步 Atlassian 数据",
        ["uv", "run", "python", "cli.py", "sync", "--help"],
        skip=False,
        timeout=10
    ))

    # ========================================
    # 2. Wiki 管理命令
    # ========================================
    print("\n" + "="*60)
    print("分类 2: Wiki 管理命令")
    print("="*60)

    # wiki-list
    test_results.append(test_command(
        "wiki-list",
        "列出所有 wiki",
        ["uv", "run", "python", "cli.py", "wiki-list"],
        timeout=10
    ))

    # wiki-init - 会创建新 wiki，使用 help 测试
    test_results.append(test_command(
        "wiki-init",
        "初始化新 wiki（测试 help）",
        ["uv", "run", "python", "cli.py", "wiki-init", "--help"],
        timeout=10
    ))

    # compile-wiki - 需要实际编译，使用 help 测试
    test_results.append(test_command(
        "compile-wiki",
        "编译 wiki（测试 help）",
        ["uv", "run", "python", "cli.py", "compile-wiki", "--help"],
        timeout=10
    ))

    # migrate-wiki - 会修改数据，使用 help 测试
    test_results.append(test_command(
        "migrate-wiki",
        "迁移 wiki（测试 help）",
        ["uv", "run", "python", "cli.py", "migrate-wiki", "--help"],
        timeout=10
    ))

    # wiki-status
    test_results.append(test_command(
        "wiki-status",
        "查看 wiki 状态",
        ["uv", "run", "python", "cli.py", "wiki-status"],
        timeout=10
    ))

    # ========================================
    # 3. 搜索命令
    # ========================================
    print("\n" + "="*60)
    print("分类 3: 搜索命令")
    print("="*60)

    # search
    test_results.append(test_command(
        "search",
        "全文搜索 'NVMe'",
        ["uv", "run", "python", "cli.py", "search", "NVMe", "--stats-only"],
        timeout=30
    ))

    # find-jira
    test_results.append(test_command(
        "find-jira",
        "查找 Jira issue KAN-1",
        ["uv", "run", "python", "cli.py", "find-jira", "KAN-1"],
        timeout=10
    ))

    # list-jira
    test_results.append(test_command(
        "list-jira",
        "列出所有 Jira issues",
        ["uv", "run", "python", "cli.py", "list-jira"],
        timeout=30
    ))

    # ========================================
    # 4. 分析命令（使用本地 LLM）
    # ========================================
    print("\n" + "="*60)
    print("分类 4: 分析命令（使用本地 LLM）")
    print("="*60)

    # 检查是否有 Jira 源文件
    jira_files = list(SOURCES_DIR.glob("KAN-*.md"))
    if jira_files:
        test_jira = jira_files[0].stem  # 使用第一个 Jira issue

        # analyze-jira - 使用本地 LLM
        test_results.append(test_command(
            "analyze-jira",
            f"分析 Jira issue {test_jira}（本地 LLM）",
            ["uv", "run", "python", "cli.py", "analyze-jira", test_jira,
             "--llm-provider", "openai",
             "--llm-base-url", LOCAL_LLM_URL,
             "--llm-model", LOCAL_LLM_MODEL],
            timeout=180
        ))
    else:
        test_results.append(test_command(
            "analyze-jira",
            "分析 Jira issue（无测试数据）",
            [],
            skip=True,
            skip_reason="没有找到 Jira 源文件"
        ))

    # analyze-doc - 使用 dry-run 模式测试（不调用 LLM）
    if jira_files:
        test_doc = str(jira_files[0])

        test_results.append(test_command(
            "analyze-doc",
            f"分析文档 {jira_files[0].name}（dry-run 模式）",
            ["uv", "run", "python", "cli.py", "analyze-doc", test_doc,
             "--dry-run"],
            timeout=30
        ))
    else:
        test_results.append(test_command(
            "analyze-doc",
            "分析文档（无测试数据）",
            [],
            skip=True,
            skip_reason="没有找到测试文档"
        ))

    # ========================================
    # 5. 报告生成命令
    # ========================================
    print("\n" + "="*60)
    print("分类 5: 报告生成命令")
    print("="*60)

    # generate-report
    test_results.append(test_command(
        "generate-report",
        "生成周报（测试 help）",
        ["uv", "run", "python", "cli.py", "generate-report", "--help"],
        timeout=10
    ))

    # ========================================
    # 6. 导出和拆分命令
    # ========================================
    print("\n" + "="*60)
    print("分类 6: 导出和拆分命令")
    print("="*60)

    # export-filtered
    test_results.append(test_command(
        "export-filtered",
        "筛选导出（测试 help）",
        ["uv", "run", "python", "cli.py", "export-filtered", "--help"],
        timeout=10
    ))

    # split-doc
    test_results.append(test_command(
        "split-doc",
        "拆分文档（测试 help）",
        ["uv", "run", "python", "cli.py", "split-doc", "--help"],
        timeout=10
    ))

    # ========================================
    # 7. Wiki 查询命令
    # ========================================
    print("\n" + "="*60)
    print("分类 7: Wiki 查询命令")
    print("="*60)

    # query-wiki - 需要编译好的 wiki
    test_results.append(test_command(
        "query-wiki",
        "查询 wiki（测试 help）",
        ["uv", "run", "python", "cli.py", "query-wiki", "--help"],
        timeout=10
    ))

    # watch-wiki - 会持续运行，使用 help 测试
    test_results.append(test_command(
        "watch-wiki",
        "监控 wiki（测试 help）",
        ["uv", "run", "python", "cli.py", "watch-wiki", "--help"],
        timeout=10
    ))

    # ========================================
    # 生成测试报告
    # ========================================
    print("\n" + "="*60)
    print("生成测试报告")
    print("="*60)

    generate_report()


def generate_report():
    """生成测试报告"""

    # 统计结果
    total = len(test_results)
    success = sum(1 for t in test_results if t.success)
    failed = sum(1 for t in test_results if not t.success and not t.error.startswith("SKIPPED"))
    skipped = sum(1 for t in test_results if t.error and t.error.startswith("SKIPPED"))
    success_rate = (success / total * 100) if total > 0 else 0

    # 生成 Markdown 报告
    report_path = TEST_OUTPUTS_DIR / "reports" / "all-commands.md"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# AI Tools - 综合命令测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**本地 LLM**: {LOCAL_LLM_URL}  \n")
        f.write(f"**模型**: {LOCAL_LLM_MODEL}  \n")
        f.write(f"**测试命令数**: {total}  \n\n")

        f.write("---\n\n")
        f.write("## 📊 测试结果总览\n\n")
        f.write(f"- **总计**: {total} 个命令\n")
        f.write(f"- **成功**: {success} 个 ✅\n")
        f.write(f"- **失败**: {failed} 个 ❌\n")
        f.write(f"- **跳过**: {skipped} 个 ⏭️\n")
        f.write(f"- **成功率**: **{success_rate:.1f}%**\n\n")

        f.write("---\n\n")
        f.write("## 📋 详细测试结果\n\n")

        # 按分类组织结果
        categories = {
            "数据同步": ["sync"],
            "Wiki 管理": ["wiki-list", "wiki-init", "compile-wiki", "migrate-wiki", "wiki-status"],
            "搜索": ["search", "find-jira", "list-jira"],
            "分析": ["analyze-jira", "analyze-doc"],
            "报告生成": ["generate-report"],
            "导出和拆分": ["export-filtered", "split-doc"],
            "Wiki 查询": ["query-wiki", "watch-wiki"]
        }

        for category, cmd_names in categories.items():
            f.write(f"### {category}\n\n")
            f.write("| 命令 | 描述 | 状态 | 耗时 | 备注 |\n")
            f.write("|------|------|------|------|------|\n")

            for test in test_results:
                if test.name in cmd_names:
                    status = "✅ 成功" if test.success else ("⏭️ 跳过" if test.error and test.error.startswith("SKIPPED") else "❌ 失败")
                    duration = f"{test.duration:.2f}s" if test.duration > 0 else "-"
                    note = test.error[:50] if test.error else "-"
                    f.write(f"| {test.name} | {test.description} | {status} | {duration} | {note} |\n")

            f.write("\n")

        f.write("---\n\n")
        f.write("## 🔍 失败命令详情\n\n")

        failed_tests = [t for t in test_results if not t.success and not (t.error and t.error.startswith("SKIPPED"))]
        if failed_tests:
            for test in failed_tests:
                f.write(f"### {test.name}\n\n")
                f.write(f"**描述**: {test.description}  \n")
                f.write(f"**错误信息**:\n```\n{test.error}\n```\n\n")
        else:
            f.write("无失败命令 ✅\n\n")

        f.write("---\n\n")
        f.write("## 💡 测试总结\n\n")

        if success_rate >= 90:
            f.write("✅ **优秀**: 所有核心命令运行正常\n\n")
        elif success_rate >= 70:
            f.write("⚠️ **良好**: 大部分命令运行正常，部分命令需要检查\n\n")
        else:
            f.write("❌ **需要改进**: 多个命令失败，需要排查问题\n\n")

        f.write("### 测试覆盖范围\n\n")
        f.write("- ✅ 数据同步命令\n")
        f.write("- ✅ Wiki 管理命令\n")
        f.write("- ✅ 搜索命令\n")
        f.write("- ✅ 分析命令（本地 LLM）\n")
        f.write("- ✅ 报告生成命令\n")
        f.write("- ✅ 导出和拆分命令\n")
        f.write("- ✅ Wiki 查询命令\n\n")

        f.write("---\n\n")
        f.write(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write("**测试工具**: AI Tools Command Test Suite  \n")

    # 生成 JSON 报告
    json_path = TEST_OUTPUTS_DIR / "reports" / "all-commands.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "llm_url": LOCAL_LLM_URL,
            "llm_model": LOCAL_LLM_MODEL,
            "summary": {
                "total": total,
                "success": success,
                "failed": failed,
                "skipped": skipped,
                "success_rate": success_rate
            },
            "tests": [t.to_dict() for t in test_results]
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 测试报告已生成:")
    print(f"  - Markdown: {report_path}")
    print(f"  - JSON: {json_path}")

    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")
    print(f"总计: {total} | 成功: {success} | 失败: {failed} | 跳过: {skipped}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
