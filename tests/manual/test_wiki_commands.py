"""
Wiki 命令综合测试

测试所有 wiki 相关命令的实际功能，确保能正确生成产物。
"""

import subprocess
import sys
import time
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_OUTPUTS_DIR = PROJECT_ROOT / "tests" / "outputs"

# LLM 配置
LLM_BASE_URL = "http://127.0.0.1:8080/v1"
LLM_MODEL = "Qwen3.5-9B-IQ4_XS"

# 测试用的 wiki 名称
TEST_WIKI = "kan-project"


def run_command(cmd: list, timeout: int = 120) -> tuple[bool, str, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timeout after {timeout}s"
    except Exception as e:
        return False, "", str(e)


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)


def test_wiki_list():
    """测试 wiki-list 命令"""
    print_section("测试 1: wiki-list - 列出所有 wiki")

    cmd = ["uv", "run", "python", "cli.py", "wiki-list"]
    success, stdout, stderr = run_command(cmd)

    if success and TEST_WIKI in stdout:
        print(f"[PASS] 成功列出 wiki，找到测试 wiki: {TEST_WIKI}")
        return True
    else:
        print(f"[FAIL] 未能正确列出 wiki")
        print(f"错误: {stderr}")
        return False


def test_wiki_status():
    """测试 wiki-status 命令"""
    print_section("测试 2: wiki-status - 查看 wiki 状态")

    # wiki-status 命令查看当前目录的 wiki，需要切换到 wiki 目录
    wiki_path = PROJECT_ROOT / "wikis" / TEST_WIKI

    cmd = ["uv", "run", "python", str(PROJECT_ROOT / "cli.py"), "wiki-status"]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(wiki_path),
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            print(f"[PASS] 成功获取 wiki 状态")
            print(f"状态信息:\n{result.stdout[:500]}")
            return True
        else:
            print(f"[FAIL] 获取 wiki 状态失败")
            print(f"错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"[FAIL] 执行失败: {e}")
        return False


def test_compile_wiki():
    """测试 compile-wiki 命令"""
    print_section("测试 3: compile-wiki - 编译 wiki")

    # 准备测试文件
    wiki_path = PROJECT_ROOT / "wikis" / TEST_WIKI
    temp_dir = wiki_path / "temp"
    sources_dir = wiki_path / "sources"

    # 清空 temp 目录
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 复制一个源文件到 temp
    source_files = list(sources_dir.glob("*.md"))
    if not source_files:
        print("[SKIP] 没有源文件可供测试")
        return None

    import shutil
    test_file = source_files[0]
    shutil.copy2(test_file, temp_dir / test_file.name)
    print(f"准备测试文件: {test_file.name}")

    # 运行编译
    cmd = [
        "uv", "run", "python", "cli.py", "compile-wiki",
        "--wiki-name", TEST_WIKI,
        "--llm-base-url", LLM_BASE_URL,
        "--llm-model", LLM_MODEL
    ]

    print(f"运行编译命令...")
    success, stdout, stderr = run_command(cmd, timeout=120)

    if success and "编译完成" in stdout:
        print(f"[PASS] Wiki 编译成功")

        # 检查是否生成了 wiki 文件
        wiki_concepts_dir = wiki_path / "wiki" / "concepts"
        if wiki_concepts_dir.exists():
            concept_files = list(wiki_concepts_dir.glob("*.md"))
            print(f"生成的概念文件数: {len(concept_files)}")
            if concept_files:
                print(f"示例文件: {concept_files[0].name}")

        return True
    else:
        print(f"[FAIL] Wiki 编译失败")
        print(f"输出: {stdout}")
        print(f"错误: {stderr}")
        return False


def test_query_wiki_direct():
    """测试直接使用 llm-wiki-compiler query"""
    print_section("测试 4: query-wiki - 查询 wiki（直接调用）")

    wiki_path = PROJECT_ROOT / "wikis" / TEST_WIKI

    # 检查是否有编译好的 wiki
    wiki_concepts_dir = wiki_path / "wiki" / "concepts"
    if not wiki_concepts_dir.exists() or not list(wiki_concepts_dir.glob("*.md")):
        print("[SKIP] 没有编译好的 wiki，跳过查询测试")
        return None

    # 直接调用 llm-wiki-compiler (Windows 需要 shell=True)
    cmd = "npx llm-wiki-compiler query \"What is NVMe?\""

    print(f"运行查询命令...")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(wiki_path),
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace',
            shell=True
        )

        if result.returncode == 0 and len(result.stdout) > 100:
            print(f"[PASS] Wiki 查询成功")
            print(f"查询结果长度: {len(result.stdout)} 字符")
            print(f"结果预览:\n{result.stdout[:300]}...")
            return True
        else:
            print(f"[FAIL] Wiki 查询失败或结果为空")
            print(f"错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"[FAIL] 查询执行失败: {e}")
        return False


def generate_report(results: dict):
    """生成测试报告"""
    print_section("测试报告")

    total = len(results)
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    print(f"\n总计: {total} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print(f"跳过: {skipped} 个")
    print(f"成功率: {passed}/{total-skipped} ({100*passed/(total-skipped) if total-skipped > 0 else 0:.1f}%)")

    print(f"\n详细结果:")
    for test_name, result in results.items():
        status = "PASS" if result is True else ("FAIL" if result is False else "SKIP")
        symbol = "+" if result is True else ("-" if result is False else "o")
        print(f"  {symbol} {test_name}: {status}")

    # 保存报告
    report_dir = TEST_OUTPUTS_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "wiki-commands.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Wiki 命令测试报告\n\n")
        f.write(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**测试 Wiki**: {TEST_WIKI}\n")
        f.write(f"**LLM**: {LLM_BASE_URL} ({LLM_MODEL})\n\n")

        f.write(f"## 测试结果\n\n")
        f.write(f"| 指标 | 数量 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总计 | {total} |\n")
        f.write(f"| 通过 | {passed} |\n")
        f.write(f"| 失败 | {failed} |\n")
        f.write(f"| 跳过 | {skipped} |\n")
        f.write(f"| 成功率 | {100*passed/(total-skipped) if total-skipped > 0 else 0:.1f}% |\n\n")

        f.write(f"## 详细结果\n\n")
        for test_name, result in results.items():
            status = "✅ 通过" if result is True else ("❌ 失败" if result is False else "⏭️ 跳过")
            f.write(f"- **{test_name}**: {status}\n")

    print(f"\n报告已保存到: {report_file}")


def main():
    """主测试流程"""
    print("="*60)
    print("Wiki 命令综合测试")
    print("="*60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试 Wiki: {TEST_WIKI}")
    print(f"LLM: {LLM_BASE_URL}")
    print(f"模型: {LLM_MODEL}")
    print("="*60)

    results = {}

    # 运行测试
    results["wiki-list"] = test_wiki_list()
    results["wiki-status"] = test_wiki_status()
    results["compile-wiki"] = test_compile_wiki()
    results["query-wiki"] = test_query_wiki_direct()

    # 生成报告
    generate_report(results)

    # 返回退出码
    failed = sum(1 for v in results.values() if v is False)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
