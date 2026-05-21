#!/usr/bin/env python3
"""
smart-search Skill 执行脚本
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional


def run_smart_search(
    query: str,
    scope: str = "all",
    min_score: float = 6.0,
    limit: int = 10,
    config: str = "config.yaml"
) -> int:
    """
    执行智能语义搜索

    Args:
        query: 搜索查询
        scope: 搜索范围（code/docs/wiki/all）
        min_score: 最低相关性分数
        limit: 返回结果数量
        config: 配置文件路径

    Returns:
        退出码（0 表示成功）
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent.parent
    cli_path = project_root / "cli.py"

    if not cli_path.exists():
        print(f"❌ 错误: 找不到 CLI 脚本 {cli_path}")
        return 1

    if not query.strip():
        print("❌ 错误: 查询不能为空")
        return 1

    # 构建命令
    cmd = ["python", str(cli_path), "search", query]

    if config != "config.yaml":
        cmd.extend(["--config", config])

    # 执行命令
    print(f"🔍 搜索查询: {query}")
    print(f"📂 搜索范围: {scope}")
    print(f"📊 最低分数: {min_score}")
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
        description="智能语义搜索 Skill"
    )
    parser.add_argument(
        "query",
        help="搜索查询（自然语言或关键词）"
    )
    parser.add_argument(
        "--scope",
        choices=["code", "docs", "wiki", "all"],
        default="all",
        help="搜索范围"
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=6.0,
        help="最低相关性分数（0-10）"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="返回结果数量"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径"
    )

    args = parser.parse_args()

    exit_code = run_smart_search(
        query=args.query,
        scope=args.scope,
        min_score=args.min_score,
        limit=args.limit,
        config=args.config
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
