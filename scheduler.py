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

        # 获取所有数据源
        sources_to_sync = filter_sources(cfg['sources'], None, 'all')

        # 同步 Confluence
        if sources_to_sync['confluence']:
            print("Syncing Confluence...")
            for src in sources_to_sync['confluence']:
                print(f"\nSource: {src['name']}")
                crawler = ConfluenceCrawler(
                    src['url'],
                    src['username'],
                    src['api_token'],
                    error_handler
                )
                for space in src['spaces']:
                    print(f"  Processing space: {space['key']}")
                    crawler.crawl_space(src['name'], space['key'], storage)

        # 同步 Jira
        if sources_to_sync['jira']:
            print("\nSyncing Jira...")
            for src in sources_to_sync['jira']:
                print(f"\nSource: {src['name']}")
                crawler = JiraCrawler(
                    src['url'],
                    src['username'],
                    src['api_token'],
                    error_handler
                )
                for project in src['projects']:
                    print(f"  Processing project: {project['key']}")
                    crawler.crawl_project(src['name'], project['key'], storage)

        storage.save_state()
        error_handler.generate_error_report()

        print(f"\n{'='*60}")
        print(f"Sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error during sync: {str(e)}")
        logging.error(f"Sync failed: {str(e)}")


def run_scheduler(config_path: str = "config.yaml", sync_time: str = "09:00"):
    """运行定时调度器

    Args:
        config_path: 配置文件路径
        sync_time: 每日同步时间（HH:MM 格式）
    """
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
        "--time",
        default="09:00",
        help="每日同步时间 HH:MM 格式 (默认: 09:00)"
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
        run_scheduler(args.config, args.time)
