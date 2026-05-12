"""
CLI 入口 - Atlassian 数据爬取工具
"""

import os
import sys
import json
import subprocess
import click
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, date
import shutil

# 强制使用 UTF-8 编码（Windows 兼容性）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from crawler.confluence import ConfluenceCrawler
from crawler.jira import JiraCrawler
from crawler.storage import StorageManager
from crawler.error_handler import ErrorHandler
from crawler.doc_splitter import DocumentSplitter
from crawler.searcher import ContentSearcher
from crawler.report_generator import ReportGenerator
from crawler.jira_analyzer import JiraDeepAnalyzer
from crawler.llm_client import create_llm_client
from crawler.analyzers.knowledge_retriever import KnowledgeRetriever
from crawler.analyzers.root_cause_analyzer import RootCauseAnalyzer
from crawler.analyzers.similar_jira_finder import SimilarJiraFinder
from crawler.analyzers.closed_loop_checker import ClosedLoopChecker
from crawler.analyzers.comment_analyzer import CommentAnalyzer
from crawler.analyzers.action_recommender import ActionRecommender


def _sync_confluence_space(source: Dict[str, Any], space_key: str, is_cloud: bool, storage: StorageManager, error_handler: ErrorHandler) -> Dict[str, int]:
    """
    同步单个 Confluence space（用于并发执行）

    Args:
        source: 数据源配置
        space_key: Space key
        is_cloud: 是否为 Cloud 版本
        storage: 存储管理器
        error_handler: 错误处理器

    Returns:
        统计信息 {'pages': int, 'attachments': int}
    """
    crawler = ConfluenceCrawler(
        source['url'],
        source['api_token'],
        error_handler,
        username=source.get('username'),
        is_cloud=is_cloud
    )
    return crawler.crawl_space(source['name'], space_key, storage)


def _sync_jira_project(source: Dict[str, Any], project_key: str, is_cloud: bool, storage: StorageManager, error_handler: ErrorHandler, max_results_per_page: int = 50) -> Dict[str, int]:
    """
    同步单个 Jira project（用于并发执行）

    Args:
        source: 数据源配置
        project_key: Project key
        is_cloud: 是否为 Cloud 版本
        storage: 存储管理器
        error_handler: 错误处理器
        max_results_per_page: 每页获取的最大结果数

    Returns:
        统计信息 {'issues': int, 'attachments': int}
    """
    crawler = JiraCrawler(
        source['url'],
        source['api_token'],
        error_handler,
        username=source.get('username'),
        is_cloud=is_cloud,
        max_results_per_page=max_results_per_page
    )
    return crawler.crawl_project(source['name'], project_key, storage)


@click.group()
def cli():
    """Atlassian 数据爬取工具 - 从 Jira 和 Confluence 爬取数据到本地 markdown"""
    pass


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
def init(config):
    """初始化配置文件"""
    config_path = Path(config)

    if config_path.exists():
        click.echo(f"配置文件 {config} 已存在")
        return

    # 创建默认配置
    default_config = {
        'sources': {
            'confluence': [
                {
                    'name': 'my-confluence',
                    'url': 'https://your-domain.atlassian.net',
                    'username': 'your-email@example.com',
                    'api_token': '${CONFLUENCE_API_TOKEN}',
                    'spaces': [
                        {'key': 'ENG', 'name': 'Engineering'}
                    ]
                }
            ],
            'jira': [
                {
                    'name': 'my-jira',
                    'url': 'https://your-domain.atlassian.net',
                    'username': 'your-email@example.com',
                    'api_token': '${JIRA_API_TOKEN}',
                    'projects': [
                        {'key': 'PROJ', 'name': 'Project Alpha'}
                    ]
                }
            ]
        },
        'output': {
            'base_dir': './sources'
        },
        'sync': {
            'state_file': './.atlassian-sync-state.json'
        },
        'error_handling': {
            'max_retries': 3,
            'retry_delay': 5,
            'error_log': './sync-errors.log'
        }
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

    click.echo(f"[OK] Config file created: {config}")
    click.echo("\nPlease edit the config file and set environment variables:")
    click.echo("  export CONFLUENCE_API_TOKEN='your-token'")
    click.echo("  export JIRA_API_TOKEN='your-token'")


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
def list_sources(config):
    """列出所有配置的数据源"""
    try:
        cfg = load_config(config)

        click.echo("\n=== Confluence Sources ===")
        for src in cfg['sources'].get('confluence', []):
            click.echo(f"  - {src['name']}")
            click.echo(f"    URL: {src['url']}")
            click.echo(f"    Spaces: {', '.join([s['key'] for s in src['spaces']])}")

        click.echo("\n=== Jira Sources ===")
        for src in cfg['sources'].get('jira', []):
            click.echo(f"  - {src['name']}")
            click.echo(f"    URL: {src['url']}")
            click.echo(f"    Projects: {', '.join([p['key'] for p in src['projects']])}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
@click.option('--source', help='指定要同步的数据源名称')
@click.option('--type', type=click.Choice(['confluence', 'jira', 'all']), default='all', help='数据源类型')
def sync(config, source, type):
    """
    执行同步

    示例:
      python cli.py sync                              # 同步所有数据源
      python cli.py sync --type confluence            # 只同步所有 Confluence
      python cli.py sync --type jira                  # 只同步所有 Jira
      python cli.py sync --source my-confluence       # 同步指定数据源
    """
    try:
        cfg = load_config(config)
        storage = StorageManager(cfg['output']['base_dir'], cfg['sync']['state_file'])
        error_handler = ErrorHandler(**cfg['error_handling'])

        # 获取并发数配置
        max_workers = cfg.get('performance', {}).get('max_workers', 10)
        max_workers = min(max_workers, 10)  # 限制最大并发数为 10

        # 获取每页结果数配置
        max_results_per_page = cfg.get('performance', {}).get('max_results_per_page', 50)

        # 根据参数过滤要同步的数据源
        sources_to_sync = filter_sources(cfg['sources'], source, type)

        # 统计信息
        stats = {
            'confluence': {'pages': 0, 'attachments': 0, 'skipped': 0, 'total': 0},
            'jira': {'issues': 0, 'attachments': 0, 'skipped': 0, 'total': 0}
        }

        # 同步 Confluence
        if sources_to_sync['confluence']:
            click.echo("Syncing Confluence...")

            # 准备所有任务
            tasks = []
            for src in sources_to_sync['confluence']:
                is_cloud = src.get('type', 'cloud').lower() == 'cloud'
                for space in src['spaces']:
                    tasks.append({
                        'type': 'confluence',
                        'source': src,
                        'space_key': space['key'],
                        'is_cloud': is_cloud
                    })

            # 并发执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for task in tasks:
                    future = executor.submit(
                        _sync_confluence_space,
                        task['source'],
                        task['space_key'],
                        task['is_cloud'],
                        storage,
                        error_handler
                    )
                    futures[future] = task

                # 收集结果
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        stats['confluence']['pages'] += result['pages']
                        stats['confluence']['attachments'] += result['attachments']
                        stats['confluence']['skipped'] += result.get('skipped', 0)
                        stats['confluence']['total'] += result.get('total', 0)
                        click.echo(f"  ✓ {task['source']['name']}/{task['space_key']}: {result['pages']} pages, {result['attachments']} attachments")
                    except Exception as e:
                        click.echo(f"  ✗ {task['source']['name']}/{task['space_key']}: {str(e)}", err=True)

        # 同步 Jira
        if sources_to_sync['jira']:
            click.echo("\nSyncing Jira...")

            # 准备所有任务
            tasks = []
            for src in sources_to_sync['jira']:
                is_cloud = src.get('type', 'cloud').lower() == 'cloud'
                for project in src['projects']:
                    tasks.append({
                        'type': 'jira',
                        'source': src,
                        'project_key': project['key'],
                        'is_cloud': is_cloud
                    })

            # 并发执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for task in tasks:
                    future = executor.submit(
                        _sync_jira_project,
                        task['source'],
                        task['project_key'],
                        task['is_cloud'],
                        storage,
                        error_handler,
                        max_results_per_page
                    )
                    futures[future] = task

                # 收集结果
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        stats['jira']['issues'] += result['issues']
                        stats['jira']['attachments'] += result['attachments']
                        stats['jira']['skipped'] += result.get('skipped', 0)
                        stats['jira']['total'] += result.get('total', 0)
                        click.echo(f"  ✓ {task['source']['name']}/{task['project_key']}: {result['issues']} issues, {result['attachments']} attachments")
                    except Exception as e:
                        click.echo(f"  ✗ {task['source']['name']}/{task['project_key']}: {str(e)}", err=True)

        storage.save_state()
        error_handler.generate_error_report()

        # 显示统计信息
        click.echo("\n" + "="*50)
        click.echo("Sync Summary:")
        if sources_to_sync['confluence']:
            click.echo(f"  Confluence:")
            click.echo(f"    - 总页面: {stats['confluence']['total']}")
            click.echo(f"    - 已拉取: {stats['confluence']['pages']} (新增或已更新)")
            click.echo(f"    - 已跳过: {stats['confluence']['skipped']} (未变化)")
            click.echo(f"    - 附件: {stats['confluence']['attachments']}")
        if sources_to_sync['jira']:
            click.echo(f"  Jira:")
            click.echo(f"    - 总 issues: {stats['jira']['total']}")
            click.echo(f"    - 已拉取: {stats['jira']['issues']} (新增或已更新)")
            click.echo(f"    - 已跳过: {stats['jira']['skipped']} (未变化)")
            click.echo(f"    - 附件: {stats['jira']['attachments']}")
        click.echo("="*50)
        click.echo("\n[OK] Sync completed!")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
def status(config):
    """查看同步状态"""
    try:
        cfg = load_config(config)
        state_file = Path(cfg['sync']['state_file'])

        if not state_file.exists():
            click.echo("No sync has been performed yet")
            return

        with open(state_file, encoding='utf-8') as f:
            state = json.load(f)

        click.echo(f"\nLast sync: {state.get('last_sync', 'N/A')}")

        # 统计 Confluence
        confluence_count = 0
        for source_data in state.get('confluence', {}).values():
            for space_data in source_data.values():
                confluence_count += len(space_data.get('pages', {}))

        # 统计 Jira
        jira_count = 0
        for source_data in state.get('jira', {}).values():
            for project_data in source_data.values():
                jira_count += len(project_data.get('issues', {}))

        click.echo(f"Confluence pages: {confluence_count}")
        click.echo(f"Jira issues: {jira_count}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置文件，支持环境变量替换

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}\nPlease run: python cli.py init")

    with open(config_file, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    # 替换环境变量
    cfg = _replace_env_vars(cfg)

    return cfg


def _replace_env_vars(obj):
    """递归替换配置中的环境变量"""
    if isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
        env_var = obj[2:-1]
        value = os.getenv(env_var, '')
        if not value:
            raise ValueError(f"Environment variable not set: {env_var}")
        return value
    else:
        return obj


def filter_sources(sources: Dict[str, Any], source_name: str, source_type: str) -> Dict[str, list]:
    """
    根据参数过滤数据源

    Args:
        sources: 所有数据源配置
        source_name: 指定的数据源名称（可选）
        source_type: 数据源类型 (confluence/jira/all)

    Returns:
        过滤后的数据源字典
    """
    result = {'confluence': [], 'jira': []}

    # 如果指定了数据源名称
    if source_name:
        # 在 Confluence 中查找
        if source_type in ['confluence', 'all']:
            for src in sources.get('confluence', []):
                if src['name'] == source_name:
                    result['confluence'].append(src)

        # 在 Jira 中查找
        if source_type in ['jira', 'all']:
            for src in sources.get('jira', []):
                if src['name'] == source_name:
                    result['jira'].append(src)
    else:
        # 没有指定数据源，根据类型返回所有
        if source_type in ['confluence', 'all']:
            result['confluence'] = sources.get('confluence', [])
        if source_type in ['jira', 'all']:
            result['jira'] = sources.get('jira', [])

    return result


@cli.command()
def compile_wiki():
    """编译 sources 到 wiki（使用 llm-wiki-compiler）"""
    click.echo("开始编译 wiki...")

    result = subprocess.run(
        ["npx", "llm-wiki-compiler", "compile"],
        capture_output=True,
        text=True,
        shell=True,
        encoding='utf-8',
        errors='replace'
    )

    if result.returncode == 0:
        click.echo("[OK] Wiki 编译完成")
        if result.stdout:
            click.echo(result.stdout)
    else:
        click.echo("[ERROR] Wiki 编译失败", err=True)
        if result.stderr:
            click.echo(result.stderr, err=True)
        raise click.Abort()


@cli.command()
@click.argument('question')
@click.option('--save', is_flag=True, help='保存查询结果为 wiki 页面')
def query_wiki(question, save):
    """查询已编译的 wiki"""
    cmd = ["npx", "llm-wiki-compiler", "query", question]
    if save:
        cmd.append("--save")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True,
        encoding='utf-8',
        errors='replace'
    )

    if result.returncode == 0:
        click.echo(result.stdout)
    else:
        click.echo("[ERROR] 查询失败", err=True)
        if result.stderr:
            click.echo(result.stderr, err=True)
        raise click.Abort()


@cli.command()
def wiki_status():
    """显示 wiki 状态"""
    wiki_dir = Path("wiki/concepts")
    llmwiki_dir = Path(".llmwiki")

    if not wiki_dir.exists():
        click.echo("Wiki 尚未编译")
        click.echo("运行 'python cli.py compile-wiki' 开始编译")
        return

    # 统计概念数量
    concept_count = len(list(wiki_dir.glob("*.md")))
    click.echo(f"Wiki 概念数量: {concept_count}")

    # 显示索引文件
    index_file = Path("wiki/index.md")
    if index_file.exists():
        click.echo(f"索引文件: {index_file}")

    # 显示状态目录
    if llmwiki_dir.exists():
        click.echo(f"状态目录: {llmwiki_dir}")

    # 运行 lint 检查
    click.echo("\n运行质量检查...")
    result = subprocess.run(
        ["npx", "llm-wiki-compiler", "lint"],
        capture_output=True,
        text=True,
        shell=True,
        encoding='utf-8',
        errors='replace'
    )

    if result.stdout:
        click.echo(result.stdout)


@cli.command()
@click.option('--time', default='02:00', help='编译时间 (HH:MM 格式)')
def watch_wiki(time):
    """监控 sources 目录并自动重新编译 wiki"""
    click.echo(f"启动 wiki watch 模式...")
    click.echo(f"将监控 sources/ 目录的变化并自动重新编译")
    click.echo("按 Ctrl+C 停止")

    try:
        subprocess.run(
            ["npx", "llm-wiki-compiler", "watch"],
            shell=True,
            encoding='utf-8',
            errors='replace'
        )
    except KeyboardInterrupt:
        click.echo("\n[OK] Watch 模式已停止")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', default='sources/', help='输出目录')
@click.option('--max-chars', default=10000, help='单个文档最大字符数')
@click.option('--split-level', default=1, help='拆分的标题层级 (1-6)')
@click.option('--dry-run', is_flag=True, help='只显示拆分结果，不实际写入文件')
def split_doc(input_file, output_dir, max_chars, split_level, dry_run):
    """
    拆分长文档为多个小文档

    将长文档按照 Markdown 标题层级拆分为多个小文档，
    便于 LLM 处理和概念提取。

    示例:
        uv run python cli.py split-doc test-sources/nvme.md
        uv run python cli.py split-doc test-sources/nvme.md --max-chars 8000 --split-level 2
        uv run python cli.py split-doc test-sources/nvme.md --dry-run
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)

    # 创建拆分器
    splitter = DocumentSplitter(max_chars=max_chars, split_level=split_level)

    # 拆分文件
    try:
        output_files = splitter.split_file(input_path, output_path, dry_run=dry_run)

        if not dry_run and output_files:
            click.echo(f"\n💡 提示: 运行以下命令编译 wiki:")
            click.echo(f"   uv run python cli.py compile-wiki")
    except Exception as e:
        click.echo(f"❌ 拆分失败: {e}", err=True)
        raise


def _parse_jira_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    解析 Jira markdown 文件的元数据

    Args:
        file_path: Jira markdown 文件路径

    Returns:
        元数据字典，包含 update_date, status, priority, type
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata = {}

        # 提取更新时间: > 更新时间: 2026-05-01T22:08:11.433+0800
        update_match = re.search(r'>\s*更新时间:\s*(\d{4}-\d{2}-\d{2})', content)
        if update_match:
            date_str = update_match.group(1)
            metadata['update_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()

        # 提取状态: - **状态**: 进行中
        status_match = re.search(r'-\s*\*\*状态\*\*:\s*([^\n]+)', content)
        if status_match:
            metadata['status'] = status_match.group(1).strip()

        # 提取优先级: - **优先级**: Medium
        priority_match = re.search(r'-\s*\*\*优先级\*\*:\s*([^\n]+)', content)
        if priority_match:
            metadata['priority'] = priority_match.group(1).strip()

        # 提取类型: - **类型**: Bug
        type_match = re.search(r'-\s*\*\*类型\*\*:\s*([^\n]+)', content)
        if type_match:
            metadata['type'] = type_match.group(1).strip()

        return metadata
    except Exception as e:
        click.echo(f"Warning: Failed to parse {file_path}: {e}", err=True)
        return None


def _parse_confluence_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    解析 Confluence markdown 文件的元数据

    Args:
        file_path: Confluence markdown 文件路径

    Returns:
        元数据字典，包含 update_date
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata = {}

        # 提取更新时间: > 更新时间: 2026-05-01T22:08:11.433+0800
        update_match = re.search(r'>\s*更新时间:\s*(\d{4}-\d{2}-\d{2})', content)
        if update_match:
            date_str = update_match.group(1)
            metadata['update_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()

        return metadata
    except Exception as e:
        click.echo(f"Warning: Failed to parse {file_path}: {e}", err=True)
        return None


@cli.command()
@click.argument('query')
@click.option('--type', 'file_type', default='all', type=click.Choice(['all', 'jira', 'confluence']), help='文件类型过滤')
@click.option('--context', 'context_lines', default=2, type=int, help='显示上下文行数')
@click.option('--regex', is_flag=True, help='使用正则表达式搜索')
@click.option('--case-sensitive', is_flag=True, help='区分大小写')
@click.option('--max-results', default=100, type=int, help='最大结果数')
@click.option('--source-dir', default='./sources', help='源文件目录')
@click.option('--no-highlight', is_flag=True, help='不高亮显示匹配内容')
@click.option('--stats-only', is_flag=True, help='只显示统计信息')
def search(query, file_type, context_lines, regex, case_sensitive, max_results, source_dir, no_highlight, stats_only):
    """
    在 sources 目录中搜索内容

    示例:
        uv run python cli.py search "NVMe Reset"
        uv run python cli.py search "性能优化" --type jira
        uv run python cli.py search "NVMe.*Reset" --regex
        uv run python cli.py search "CSTS.RDY" --context 5
        uv run python cli.py search "nvme" --case-sensitive
        uv run python cli.py search "测试" --stats-only
    """
    try:
        # 创建搜索器
        searcher = ContentSearcher(source_dir)

        # 执行搜索
        click.echo(f"搜索关键词: {query}")
        click.echo(f"文件类型: {file_type}")
        if regex:
            click.echo("使用正则表达式")
        click.echo()

        matches = searcher.search(
            query=query,
            file_type=file_type,
            context_lines=context_lines,
            use_regex=regex,
            case_sensitive=case_sensitive,
            max_results=max_results
        )

        if not matches:
            click.echo("未找到匹配结果")
            return

        # 获取统计信息
        stats = searcher.get_statistics(matches)

        # 显示统计信息
        click.echo("=" * 60)
        click.echo(f"找到 {stats['total_matches']} 个匹配，分布在 {stats['total_files']} 个文件中")
        click.echo("=" * 60)

        if stats_only:
            # 只显示统计信息
            click.echo("\n文件匹配统计:")
            for file_info in stats['files'][:20]:  # 最多显示前20个文件
                click.echo(f"  {file_info['count']:3d} 个匹配 - {file_info['path']}")
            if len(stats['files']) > 20:
                click.echo(f"  ... 还有 {len(stats['files']) - 20} 个文件")
        else:
            # 显示详细匹配结果
            for match in matches:
                formatted = searcher.format_match(
                    match,
                    highlight=not no_highlight,
                    show_context=context_lines > 0
                )
                click.echo(formatted)

            # 底部再次显示统计
            click.echo("\n" + "=" * 60)
            click.echo(f"共 {stats['total_matches']} 个匹配")
            if len(matches) >= max_results:
                click.echo(f"(已达到最大结果数限制: {max_results})")
            click.echo("=" * 60)

    except FileNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
    except ValueError as e:
        click.echo(f"错误: {e}", err=True)
    except Exception as e:
        click.echo(f"搜索失败: {e}", err=True)
        raise


@cli.command()
@click.argument('issue_key')
@click.option('--source-dir', default='./sources', help='源文件目录')
def find_jira(issue_key, source_dir):
    """
    根据 issue key 查找 Jira 文件

    示例:
        uv run python cli.py find-jira KAN-10
        uv run python cli.py find-jira kan-21
    """
    try:
        searcher = ContentSearcher(source_dir)
        file_path = searcher.find_jira_by_key(issue_key)

        if file_path:
            click.echo(f"✓ 找到文件: {file_path}")
            click.echo()

            # 读取并显示文件的前几行
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:20]  # 显示前20行

                click.echo("文件预览:")
                click.echo("=" * 60)
                for i, line in enumerate(lines, 1):
                    click.echo(f"{i:3d} | {line.rstrip()}")

                if len(lines) >= 20:
                    click.echo("...")
                    click.echo(f"\n(显示前 20 行，共 {sum(1 for _ in open(file_path, 'r', encoding='utf-8'))} 行)")

            except Exception as e:
                click.echo(f"无法读取文件内容: {e}", err=True)
        else:
            click.echo(f"✗ 未找到 issue: {issue_key}", err=True)
            click.echo(f"\n提示: 确保文件名格式为 {issue_key.upper()}.md")

    except ValueError as e:
        click.echo(f"错误: {e}", err=True)
    except Exception as e:
        click.echo(f"查找失败: {e}", err=True)


@cli.command()
@click.option('--source-dir', default='./sources', help='源文件目录')
@click.option('--status', help='按状态过滤')
@click.option('--priority', help='按优先级过滤')
@click.option('--type', 'issue_type', help='按类型过滤')
def list_jira(source_dir, status, priority, issue_type):
    """
    列出所有 Jira issues

    示例:
        uv run python cli.py list-jira
        uv run python cli.py list-jira --status "进行中"
        uv run python cli.py list-jira --priority High
        uv run python cli.py list-jira --type Bug
    """
    try:
        searcher = ContentSearcher(source_dir)
        issues = searcher.list_all_jira_issues()

        if not issues:
            click.echo("未找到任何 Jira issue 文件")
            return

        # 应用过滤
        if status:
            issues = [i for i in issues if i['status'] == status]
        if priority:
            issues = [i for i in issues if i['priority'] == priority]
        if issue_type:
            issues = [i for i in issues if i['type'] == issue_type]

        if not issues:
            click.echo("没有匹配的 issues")
            return

        # 显示结果
        click.echo(f"\n找到 {len(issues)} 个 Jira issues:")
        click.echo("=" * 100)
        click.echo(f"{'Key':<12} {'类型':<8} {'状态':<10} {'优先级':<10} {'标题':<50}")
        click.echo("=" * 100)

        for issue in issues:
            title = issue['title'][:47] + '...' if len(issue['title']) > 50 else issue['title']
            click.echo(f"{issue['key']:<12} {issue['type']:<8} {issue['status']:<10} {issue['priority']:<10} {title:<50}")

        click.echo("=" * 100)
        click.echo(f"总计: {len(issues)} 个 issues")

        # 统计信息
        if len(issues) > 0:
            status_counts = {}
            priority_counts = {}
            type_counts = {}

            for issue in issues:
                status_counts[issue['status']] = status_counts.get(issue['status'], 0) + 1
                priority_counts[issue['priority']] = priority_counts.get(issue['priority'], 0) + 1
                type_counts[issue['type']] = type_counts.get(issue['type'], 0) + 1

            click.echo("\n统计信息:")
            click.echo(f"  状态: {', '.join(f'{k}({v})' for k, v in status_counts.items())}")
            click.echo(f"  优先级: {', '.join(f'{k}({v})' for k, v in priority_counts.items())}")
            click.echo(f"  类型: {', '.join(f'{k}({v})' for k, v in type_counts.items())}")

    except Exception as e:
        click.echo(f"列出 issues 失败: {e}", err=True)


@cli.command()
@click.option('--type', 'report_type', default='weekly', type=click.Choice(['daily', 'weekly', 'monthly']), help='报告类型')
@click.option('--start', 'start_date', help='开始日期 (YYYY-MM-DD)')
@click.option('--end', 'end_date', help='结束日期 (YYYY-MM-DD)')
@click.option('--output', default='./reports', help='输出目录')
@click.option('--source-dir', default='./sources', help='源文件目录')
@click.option('--format', 'output_format', default='markdown', type=click.Choice(['markdown', 'json']), help='输出格式')
def generate_report(report_type, start_date, end_date, output, source_dir, output_format):
    """
    生成周报/日报/月报

    示例:
        # 生成本周周报
        uv run python cli.py generate-report

        # 生成今日日报
        uv run python cli.py generate-report --type daily

        # 生成指定时间范围的报告
        uv run python cli.py generate-report --start 2026-05-01 --end 2026-05-07

        # 生成月报
        uv run python cli.py generate-report --type monthly

        # 输出为 JSON 格式
        uv run python cli.py generate-report --format json
    """
    try:
        from datetime import datetime
        import json
        import yaml

        # 解析日期
        start = None
        end = None

        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                click.echo(f"错误: 无效的开始日期格式: {start_date}，应为 YYYY-MM-DD", err=True)
                return

        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                click.echo(f"错误: 无效的结束日期格式: {end_date}，应为 YYYY-MM-DD", err=True)
                return

        # 加载配置文件
        config = {}
        config_path = Path('config.yaml')
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

        # 创建报告生成器
        generator = ReportGenerator(source_dir, config)

        # 生成报告
        report_name_map = {'daily': '日报', 'weekly': '周报', 'monthly': '月报'}
        click.echo(f"正在生成{report_name_map[report_type]}...")
        report = generator.generate_report(report_type, start, end)

        # 创建输出目录
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        report_name = {
            'daily': '日报',
            'weekly': '周报',
            'monthly': '月报'
        }[report_type]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_name}_{report['start_date']}_to_{report['end_date']}_{timestamp}"

        if output_format == 'markdown':
            # 输出 Markdown
            md_content = generator.format_report_markdown(report)
            output_file = output_dir / f"{filename}.md"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)

            click.echo(f"\n✅ 报告已生成: {output_file}")
            click.echo("\n" + "=" * 60)
            click.echo("报告预览:")
            click.echo("=" * 60)
            # 显示前 30 行
            lines = md_content.split('\n')
            for line in lines[:30]:
                click.echo(line)
            if len(lines) > 30:
                click.echo(f"\n... (共 {len(lines)} 行，完整内容请查看文件)")

        else:
            # 输出 JSON
            output_file = output_dir / f"{filename}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            click.echo(f"\n✅ 报告已生成: {output_file}")

            # 显示摘要
            click.echo("\n" + "=" * 60)
            click.echo("报告摘要:")
            click.echo("=" * 60)
            summary = report['summary']
            click.echo(f"时间范围: {report['start_date']} 至 {report['end_date']}")
            click.echo(f"总活动数: {summary['total_items']} 项")
            click.echo(f"  - 新增: {summary['total_new']} 项")
            click.echo(f"  - 更新: {summary['total_updated']} 项")
            click.echo(f"\nJira: {summary['jira_summary']['total']} 个 issues")
            click.echo(f"  - 新增: {summary['jira_summary']['new']} 个")
            click.echo(f"  - 更新: {summary['jira_summary']['updated']} 个")
            if summary['confluence_summary']['total'] > 0:
                click.echo(f"\nConfluence: {summary['confluence_summary']['total']} 个页面")
                click.echo(f"  - 新增: {summary['confluence_summary']['new']} 个")
                click.echo(f"  - 更新: {summary['confluence_summary']['updated']} 个")

    except Exception as e:
        click.echo(f"生成报告失败: {e}", err=True)
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--type', 'doc_type', default='jira', type=click.Choice(['confluence', 'jira']), help='文档类型')
@click.option('--status', 'statuses', multiple=True, help='状态过滤 (可多次指定，如: --status "进行中" --status "待办")')
@click.option('--today', is_flag=True, help='只导出今天更新的文档')
@click.option('--yesterday', is_flag=True, help='只导出昨天更新的文档')
@click.option('--days', type=int, help='导出最近 N 天更新的文档')
@click.option('--output', default='./filtered_export', help='导出目录')
@click.option('--source-dir', default='./sources', help='源文件目录')
def export_filtered(doc_type, statuses, today, yesterday, days, output, source_dir):
    """
    根据时间和状态筛选导出文档

    示例:
        # 导出今天更新的进行中的 Jira issues
        uv run python cli.py export-filtered --today --status "进行中"

        # 导出最近 7 天更新的待办和进行中的 issues
        uv run python cli.py export-filtered --days 7 --status "待办" --status "进行中"

        # 导出昨天更新的所有 Confluence 页面
        uv run python cli.py export-filtered --type confluence --yesterday
    """
    source_path = Path(source_dir)
    output_path = Path(output)

    # 确定时间过滤条件
    target_date = None
    date_range_start = None
    date_range_end = None

    if today:
        target_date = date.today()
        click.echo(f"筛选条件: 今天更新 ({target_date})")
    elif yesterday:
        target_date = date.today() - timedelta(days=1)
        click.echo(f"筛选条件: 昨天更新 ({target_date})")
    elif days:
        date_range_end = date.today()
        date_range_start = date_range_end - timedelta(days=days)
        click.echo(f"筛选条件: 最近 {days} 天更新 ({date_range_start} 至 {date_range_end})")

    # 状态过滤
    if statuses:
        click.echo(f"状态筛选: {', '.join(statuses)}")

    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)

    # 查找并过滤文件
    matched_files = []

    if doc_type == 'jira':
        # 查找所有 Jira markdown 文件
        jira_pattern = re.compile(r'^[A-Z]+-\d+\.md$')

        # 在 sources/ 目录和 sources/jira/ 子目录中查找
        search_paths = [source_path, source_path / 'jira']

        for search_dir in search_paths:
            if not search_dir.exists():
                continue

            for md_file in search_dir.rglob('*.md'):
                # 检查文件名是否匹配 Jira issue key 格式
                if not jira_pattern.match(md_file.name):
                    continue

                # 解析元数据
                metadata = _parse_jira_metadata(md_file)
                if not metadata:
                    continue

                # 时间过滤
                if target_date and metadata.get('update_date') != target_date:
                    continue
                if date_range_start and date_range_end:
                    update_date = metadata.get('update_date')
                    if not update_date or not (date_range_start <= update_date <= date_range_end):
                        continue

                # 状态过滤
                if statuses and metadata.get('status') not in statuses:
                    continue

                matched_files.append((md_file, metadata))

    elif doc_type == 'confluence':
        # 查找所有 Confluence markdown 文件
        confluence_dir = source_path / 'confluence'

        if not confluence_dir.exists():
            click.echo(f"错误: Confluence 目录不存在: {confluence_dir}", err=True)
            return

        for md_file in confluence_dir.rglob('*.md'):
            # 解析元数据
            metadata = _parse_confluence_metadata(md_file)
            if not metadata:
                continue

            # 时间过滤
            if target_date and metadata.get('update_date') != target_date:
                continue
            if date_range_start and date_range_end:
                update_date = metadata.get('update_date')
                if not update_date or not (date_range_start <= update_date <= date_range_end):
                    continue

            matched_files.append((md_file, metadata))

    # 导出文件
    if not matched_files:
        click.echo("\n未找到匹配的文件")
        return

    click.echo(f"\n找到 {len(matched_files)} 个匹配的文件，开始导出...")

    exported_count = 0
    for file_path, metadata in matched_files:
        try:
            # 保持相对路径结构
            rel_path = file_path.relative_to(source_path)
            dest_path = output_path / rel_path

            # 创建目标目录
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # 复制文件
            shutil.copy2(file_path, dest_path)
            exported_count += 1

            click.echo(f"  ✓ {rel_path}")
        except Exception as e:
            click.echo(f"  ✗ {file_path}: {e}", err=True)

    # 生成摘要文件
    summary_path = output_path / 'SUMMARY.md'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# 导出摘要\n\n")
        f.write(f"- **导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **文档类型**: {doc_type}\n")

        if target_date:
            f.write(f"- **时间筛选**: {target_date}\n")
        elif date_range_start and date_range_end:
            f.write(f"- **时间筛选**: {date_range_start} 至 {date_range_end}\n")

        if statuses:
            f.write(f"- **状态筛选**: {', '.join(statuses)}\n")

        f.write(f"- **导出文件数**: {exported_count}\n\n")

        f.write(f"## 文件列表\n\n")
        for file_path, metadata in matched_files:
            rel_path = file_path.relative_to(source_path)
            f.write(f"- [{rel_path}](./{rel_path})")
            if doc_type == 'jira':
                f.write(f" - 状态: {metadata.get('status', 'N/A')}, 更新: {metadata.get('update_date', 'N/A')}")
            else:
                f.write(f" - 更新: {metadata.get('update_date', 'N/A')}")
            f.write("\n")

    click.echo(f"\n✅ 导出完成!")
    click.echo(f"   导出目录: {output_path}")
    click.echo(f"   导出文件数: {exported_count}")
    click.echo(f"   摘要文件: {summary_path}")


@cli.command()
@click.argument('issue_key')
@click.option('--source-dir', default='./sources', help='源文件目录')
@click.option('--wiki-dir', default='./wiki', help='Wiki 目录')
@click.option('--output-dir', default='./reports', help='报告输出目录')
@click.option('--llm-provider', default='mock', type=click.Choice(['mock', 'llmstudio']), help='LLM 提供商')
def analyze_jira(issue_key, source_dir, wiki_dir, output_dir, llm_provider):
    """
    深度分析 Jira Issue

    示例:
        uv run python cli.py analyze-jira KAN-1
        uv run python cli.py analyze-jira KAN-2 --llm-provider llmstudio
    """
    click.echo(f"🔍 开始分析 Jira Issue: {issue_key}")
    click.echo(f"   LLM 提供商: {llm_provider}")
    click.echo("")

    try:
        # 1. 加载配置
        config_path = Path('config.yaml')
        if not config_path.exists():
            click.echo("❌ 错误: config.yaml 不存在", err=True)
            sys.exit(1)

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 2. 创建 LLM 客户端
        llm_config = config.get('llm', {})
        if llm_provider == 'llmstudio':
            llm_client = create_llm_client(
                'llmstudio',
                base_url=llm_config.get('base_url', 'http://127.0.0.1:1234'),
                model=llm_config.get('model', 'qwen3.5-0.8b')
            )
            click.echo(f"   使用 LLMStudio: {llm_config.get('base_url')}")
        else:
            llm_client = create_llm_client('mock')
            click.echo("   使用 Mock LLM（测试模式）")

        click.echo("")

        # 3. 创建分析器
        analyzer = JiraDeepAnalyzer(source_dir=source_dir, llm_client=llm_client)

        # 4. 注册所有分析器
        click.echo("📋 注册分析器...")
        analyzer.register_analyzer(KnowledgeRetriever(source_dir=source_dir, wiki_dir=wiki_dir, llm_client=llm_client, config=config))
        analyzer.register_analyzer(RootCauseAnalyzer(llm_client))
        analyzer.register_analyzer(SimilarJiraFinder(source_dir=source_dir, top_k=3, llm_client=llm_client))
        analyzer.register_analyzer(ClosedLoopChecker(llm_client))
        analyzer.register_analyzer(CommentAnalyzer(llm_client))
        analyzer.register_analyzer(ActionRecommender(llm_client))

        # 5. 注册自定义分析器
        from crawler.analyzers.custom_analyzer import CustomAnalyzer
        custom_analyzers_config = config.get('custom_analyzers', [])
        if custom_analyzers_config:
            click.echo(f"📋 注册 {len(custom_analyzers_config)} 个自定义分析器...")
            for custom_config in custom_analyzers_config:
                if not custom_config.get('enabled', True):
                    continue

                custom_analyzer = CustomAnalyzer(custom_config, llm_client)
                analyzer.register_analyzer(custom_analyzer)
                click.echo(f"   ✓ {custom_config['name']}")

        click.echo(f"   已注册 {len(analyzer.pipeline)} 个分析器")
        click.echo("")

        # 5. 执行分析
        click.echo("🚀 开始执行分析流水线...")
        click.echo(f"   调用 analyzer.analyze('{issue_key}')")
        import sys
        sys.stdout.flush()
        report = analyzer.analyze(issue_key)
        click.echo("   ✓ 分析完成")

        # 6. 保存报告
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_path / f"jira_analysis_{issue_key}_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        click.echo("")
        click.echo(f"✅ 分析完成!")
        click.echo(f"   报告文件: {report_file}")
        click.echo("")

        # 7. 显示报告预览
        click.echo("=" * 60)
        click.echo("报告预览:")
        click.echo("=" * 60)
        lines = report.split('\n')
        for line in lines[:40]:
            click.echo(line)
        if len(lines) > 40:
            click.echo(f"\n... (共 {len(lines)} 行，完整内容请查看文件)")

    except FileNotFoundError as e:
        click.echo(f"❌ 错误: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"❌ 分析失败: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 未知错误: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('doc_path', type=click.Path(exists=True))
@click.option('--config',
              default='configs/doc_analysis_config.yaml',
              help='配置文件路径')
@click.option('--output',
              help='输出报告路径（可选，默认使用配置中的规则）')
@click.option('--dry-run',
              is_flag=True,
              help='预览模式：只显示会处理哪些小节，不实际调用 LLM')
def analyze_doc(doc_path, config, output, dry_run):
    """
    分析文档并生成需求/测试用例建议报告

    示例:
        uv run python cli.py analyze-doc sources/KAN-1.md
        uv run python cli.py analyze-doc sources/requirements.md --config custom_config.yaml
        uv run python cli.py analyze-doc sources/spec.md --dry-run
    """
    from crawler.doc_analyzer import DocumentAnalyzer

    click.echo(f"📄 文档分析工具")
    click.echo(f"   文档: {doc_path}")
    click.echo(f"   配置: {config}")
    if dry_run:
        click.echo(f"   模式: 预览模式（不调用 LLM）")
    click.echo("")

    try:
        # 创建分析器
        analyzer = DocumentAnalyzer(config_path=config)

        # 执行分析
        report_path = analyzer.analyze_document(
            doc_path=doc_path,
            output_path=output,
            dry_run=dry_run
        )

        if not dry_run:
            click.echo("")
            click.echo(f"✅ 分析完成!")
            click.echo(f"   报告文件: {report_path}")
            click.echo("")

            # 显示报告预览
            click.echo("=" * 60)
            click.echo("报告预览:")
            click.echo("=" * 60)
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[:40]:
                    click.echo(line.rstrip())
                if len(lines) > 40:
                    click.echo(f"\n... (共 {len(lines)} 行，完整内容请查看文件)")

    except FileNotFoundError as e:
        click.echo(f"❌ 错误: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"❌ 分析失败: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ 未知错误: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli()
