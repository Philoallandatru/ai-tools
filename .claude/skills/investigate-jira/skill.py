#!/usr/bin/env python3
"""
investigate-jira Skill 执行脚本
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional


def run_investigate_jira(
    issue_key: str,
    wiki: Optional[str] = None,
    config: str = "config.yaml",
    depth: str = "normal"
) -> int:
    """
    执行 Jira Issue 深度调查

    Args:
        issue_key: Jira Issue Key
        wiki: Wiki 目录名称
        config: 配置文件路径
        depth: 调查深度（quick/normal/thorough）

    Returns:
        退出码（0 表示成功）
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent.parent
    cli_path = project_root / "cli.py"

    if not cli_path.exists():
        print(f"❌ 错误: 找不到 CLI 脚本 {cli_path}")
        return 1

    # 构建命令
    cmd = ["python", str(cli_path), "jira-analyze", issue_key]

    if wiki:
        cmd.extend(["--wiki", wiki])

    if config != "config.yaml":
        cmd.extend(["--config", config])

    # 执行命令
    print(f"🔍 开始调查 Jira Issue: {issue_key}")
    print(f"📊 调查深度: {depth}")
    if wiki:
        print(f"📚 使用 Wiki: {wiki}")
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
        description="Jira Issue 深度调查 Skill"
    )
    parser.add_argument(
        "issue_key",
        help="Jira Issue Key（如 KAN-10）"
    )
    parser.add_argument(
        "--wiki",
        help="指定 Wiki 目录名称"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--depth",
        choices=["quick", "normal", "thorough"],
        default="normal",
        help="调查深度"
    )

    args = parser.parse_args()

    exit_code = run_investigate_jira(
        issue_key=args.issue_key,
        wiki=args.wiki,
        config=args.config,
        depth=args.depth
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
