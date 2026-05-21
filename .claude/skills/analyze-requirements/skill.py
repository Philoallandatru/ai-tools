#!/usr/bin/env python3
"""
analyze-requirements Skill 执行脚本
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional


def run_analyze_requirements(
    doc_path: str,
    config: str = "config.yaml",
    llm_base_url: Optional[str] = None,
    llm_model: Optional[str] = None
) -> int:
    """
    执行需求文档分析

    Args:
        doc_path: 文档路径
        config: 配置文件路径
        llm_base_url: LLM API 地址
        llm_model: LLM 模型名称

    Returns:
        退出码（0 表示成功）
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent.parent
    cli_path = project_root / "cli.py"

    if not cli_path.exists():
        print(f"❌ 错误: 找不到 CLI 脚本 {cli_path}")
        return 1

    doc_path_obj = Path(doc_path)
    if not doc_path_obj.exists():
        print(f"❌ 错误: 文档不存在 {doc_path}")
        return 1

    # 构建命令
    cmd = ["python", str(cli_path), "analyze-doc", doc_path]

    if config != "config.yaml":
        cmd.extend(["--config", config])

    if llm_base_url:
        cmd.extend(["--llm-base-url", llm_base_url])

    if llm_model:
        cmd.extend(["--llm-model", llm_model])

    # 执行命令
    print(f"🚀 开始分析文档: {doc_path}")
    print(f"📝 执行命令: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            check=False
        )
        return result.returncode
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="智能需求分析 Skill"
    )
    parser.add_argument(
        "doc_path",
        help="需求文档路径（支持 .pdf 和 .md）"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--llm-base-url",
        help="LLM API 地址"
    )
    parser.add_argument(
        "--llm-model",
        help="LLM 模型名称"
    )

    args = parser.parse_args()

    exit_code = run_analyze_requirements(
        doc_path=args.doc_path,
        config=args.config,
        llm_base_url=args.llm_base_url,
        llm_model=args.llm_model
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
