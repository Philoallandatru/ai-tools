#!/usr/bin/env python3
"""端到端测试运行脚本。

这个脚本用于运行完整的端到端测试，包括：
1. 检查本地 LLM 是否可用
2. 运行所有 E2E 测试
3. 生成测试报告
"""

import subprocess
import sys
from pathlib import Path

import requests


def check_ollama_running() -> bool:
    """检查 Ollama 是否运行。"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def check_model_available(model_name: str = "qwen2.5-coder:7b") -> bool:
    """检查指定模型是否可用。"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return model_name in models
    except Exception:
        return False


def run_tests(test_type: str = "all") -> int:
    """运行测试。

    Args:
        test_type: 测试类型
            - "all": 运行所有测试
            - "no-llm": 只运行不需要 LLM 的测试
            - "llm-only": 只运行需要 LLM 的测试

    Returns:
        退出码
    """
    project_root = Path(__file__).parent.parent
    e2e_tests = project_root / "tests" / "e2e"

    # 构建 pytest 命令
    cmd = ["pytest", str(e2e_tests), "-v", "-s"]

    if test_type == "no-llm":
        # 跳过需要 LLM 的测试
        cmd.extend(["-m", "not requires_local_llm"])
    elif test_type == "llm-only":
        # 只运行需要 LLM 的测试
        cmd.extend(["-m", "requires_local_llm"])

    # 添加覆盖率报告
    cmd.extend(["--cov=crawler", "--cov-report=html", "--cov-report=term"])

    # 运行测试
    print(f"运行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)

    return result.returncode


def main():
    """主函数。"""
    print("=" * 80)
    print("端到端测试运行器")
    print("=" * 80)
    print()

    # 检查 Ollama
    print("检查本地 LLM 环境...")
    ollama_running = check_ollama_running()

    if ollama_running:
        print("✓ Ollama 正在运行")

        # 检查模型
        model_available = check_model_available("qwen2.5-coder:7b")
        if model_available:
            print("✓ qwen2.5-coder:7b 模型可用")
            print()
            print("将运行所有测试（包括需要 LLM 的测试）")
            test_type = "all"
        else:
            print("✗ qwen2.5-coder:7b 模型不可用")
            print()
            print("请运行: ollama pull qwen2.5-coder:7b")
            print()
            print("将只运行不需要 LLM 的测试")
            test_type = "no-llm"
    else:
        print("✗ Ollama 未运行")
        print()
        print("请先启动 Ollama:")
        print("  - macOS/Linux: ollama serve")
        print("  - Windows: 启动 Ollama 应用")
        print()
        print("将只运行不需要 LLM 的测试")
        test_type = "no-llm"

    print()
    print("-" * 80)
    print()

    # 运行测试
    exit_code = run_tests(test_type)

    print()
    print("=" * 80)
    if exit_code == 0:
        print("✓ 所有测试通过")
    else:
        print("✗ 部分测试失败")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
