"""
定时同步服务 - 每日自动同步 Atlassian 数据
"""

import time
import schedule
import logging
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from cli import load_config, filter_sources
from crawler.confluence import ConfluenceCrawler
from crawler.jira import JiraCrawler
from crawler.storage import StorageManager
from crawler.error_handler import ErrorHandler


def sync_all(config_path: str = "config.yaml"):
    """执行完整同步"""
    try:
        print(f"\n{'='*60}")
        print(f"Starting sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # 加载配置
        cfg = load_config(config_path)
        storage = StorageManager(cfg['output']['base_dir'], cfg['sync']['state_file'])
        error_handler = ErrorHandler(**cfg['error_handling'])

        # 获取性能配置
        max_results_per_page = cfg.get('performance', {}).get('max_results_per_page', 50)

        # 获取所有数据源
        sources_to_sync = filter_sources(cfg['sources'], None, 'all')

        # 统计信息
        stats = {
            'confluence': {'pages': 0, 'attachments': 0, 'skipped': 0, 'total': 0},
            'jira': {'issues': 0, 'attachments': 0, 'skipped': 0, 'total': 0}
        }

        # 同步 Confluence
        if sources_to_sync['confluence']:
            print("Syncing Confluence...")
            for src in sources_to_sync['confluence']:
                print(f"\nSource: {src['name']}")
                is_cloud = src.get('type', 'cloud').lower() == 'cloud'
                crawler = ConfluenceCrawler(
                    src['url'],
                    src['api_token'],
                    error_handler,
                    username=src.get('username'),
                    is_cloud=is_cloud
                )
                for space in src['spaces']:
                    print(f"  Processing space: {space['key']}")
                    result = crawler.crawl_space(
                        src['name'],
                        space['key'],
                        storage,
                        max_pages=space.get('max_pages'),
                        root_page_id=space.get('root_page_id')
                    )
                    stats['confluence']['pages'] += result['pages']
                    stats['confluence']['attachments'] += result['attachments']
                    stats['confluence']['skipped'] += result.get('skipped', 0)
                    stats['confluence']['total'] += result.get('total', 0)

        # 同步 Jira
        if sources_to_sync['jira']:
            print("\nSyncing Jira...")
            for src in sources_to_sync['jira']:
                print(f"\nSource: {src['name']}")
                is_cloud = src.get('type', 'cloud').lower() == 'cloud'
                crawler = JiraCrawler(
                    src['url'],
                    src['api_token'],
                    error_handler,
                    username=src.get('username'),
                    is_cloud=is_cloud,
                    max_results_per_page=max_results_per_page
                )
                for project in src['projects']:
                    print(f"  Processing project: {project['key']}")
                    result = crawler.crawl_project(src['name'], project['key'], storage)
                    stats['jira']['issues'] += result['issues']
                    stats['jira']['attachments'] += result['attachments']
                    stats['jira']['skipped'] += result.get('skipped', 0)
                    stats['jira']['total'] += result.get('total', 0)

        storage.save_state()
        error_handler.generate_error_report()

        print(f"\n{'='*60}")
        print(f"Sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Summary:")
        if sources_to_sync['confluence']:
            print(f"  Confluence: {stats['confluence']['pages']}/{stats['confluence']['total']} pages fetched, {stats['confluence']['skipped']} skipped")
        if sources_to_sync['jira']:
            print(f"  Jira: {stats['jira']['issues']}/{stats['jira']['total']} issues fetched, {stats['jira']['skipped']} skipped")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error during sync: {str(e)}")
        logging.error(f"Sync failed: {str(e)}")


def run_scheduler(config_path: str = "config.yaml"):
    """运行定时调度器

    Args:
        config_path: 配置文件路径
    """
    # 加载配置
    cfg = load_config(config_path)
    scheduler_config = cfg.get('scheduler', {})

    sync_time = scheduler_config.get('sync_time', '02:00')
    enabled = scheduler_config.get('enabled', True)

    if not enabled:
        print("Scheduler is disabled in config")
        return

    print(f"Scheduler started. Daily sync scheduled at {sync_time}")
    print(f"Config file: {config_path}")
    print(f"Press Ctrl+C to stop\n")

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scheduler.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # 调度每日同步
    schedule.every().day.at(sync_time).do(sync_all, config_path)

    # 可选：启动时立即执行一次
    # sync_all(config_path)

    # 运行调度器
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Atlassian 数据定时同步服务")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只执行一次同步，不启动定时服务"
    )

    args = parser.parse_args()

    if args.once:
        # 只执行一次
        sync_all(args.config)
    else:
        # 启动定时服务
        run_scheduler(args.config)
