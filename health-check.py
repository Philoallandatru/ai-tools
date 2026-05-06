"""
健康检查脚本 - 检查同步状态
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def check_sync_health(state_file: str = ".atlassian-sync-state.json", max_hours: int = 25):
    """
    检查同步健康状态

    Args:
        state_file: 状态文件路径
        max_hours: 最大允许的未同步小时数

    Returns:
        0: 健康
        1: 警告或错误
    """
    state_path = Path(state_file)

    if not state_path.exists():
        print("WARNING: No sync has been performed yet")
        return 1

    try:
        with open(state_path, encoding='utf-8') as f:
            state = json.load(f)

        last_sync_str = state.get('last_sync')
        if not last_sync_str:
            print("ERROR: No last_sync timestamp found")
            return 1

        # 解析时间戳
        last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
        now = datetime.now(last_sync.tzinfo)
        hours_since_sync = (now - last_sync).total_seconds() / 3600

        # 统计数据
        confluence_count = 0
        for source_data in state.get('confluence', {}).values():
            for space_data in source_data.values():
                confluence_count += len(space_data.get('pages', {}))

        jira_count = 0
        for source_data in state.get('jira', {}).values():
            for project_data in source_data.values():
                jira_count += len(project_data.get('issues', {}))

        # 检查健康状态
        if hours_since_sync > max_hours:
            print(f"ERROR: Last sync was {hours_since_sync:.1f} hours ago (threshold: {max_hours}h)")
            print(f"Last sync: {last_sync_str}")
            return 1
        else:
            print(f"OK: Sync is healthy")
            print(f"Last sync: {last_sync_str} ({hours_since_sync:.1f} hours ago)")
            print(f"Confluence pages: {confluence_count}")
            print(f"Jira issues: {jira_count}")

            # 检查 wiki 状态
            check_wiki_status()

            return 0

    except Exception as e:
        print(f"ERROR: Failed to check sync health: {str(e)}")
        return 1


def check_wiki_status():
    """检查 wiki 编译状态"""
    wiki_dir = Path("wiki/concepts")

    if not wiki_dir.exists():
        print("\nWiki status: Not compiled yet")
        return

    try:
        # 统计概念数量
        concept_count = len(list(wiki_dir.glob("*.md")))
        print(f"\nWiki status: OK")
        print(f"Wiki concepts: {concept_count}")

        # 检查索引文件
        index_file = Path("wiki/index.md")
        if index_file.exists():
            print(f"Index file: {index_file}")

    except Exception as e:
        print(f"\nWiki status: ERROR - {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="检查 Atlassian 同步健康状态")
    parser.add_argument(
        "--state-file",
        default=".atlassian-sync-state.json",
        help="状态文件路径"
    )
    parser.add_argument(
        "--max-hours",
        type=int,
        default=25,
        help="最大允许的未同步小时数"
    )

    args = parser.parse_args()
    sys.exit(check_sync_health(args.state_file, args.max_hours))
