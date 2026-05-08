"""
CLI 入口 - Atlassian 数据爬取工具
"""

import os
import sys
import json
import subprocess
import click
import yaml
from pathlib import Path
from typing import Dict, Any

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

        # 根据参数过滤要同步的数据源
        sources_to_sync = filter_sources(cfg['sources'], source, type)

        # 同步 Confluence
        if sources_to_sync['confluence']:
            click.echo("Syncing Confluence...")
            for src in sources_to_sync['confluence']:
                click.echo(f"\nSource: {src['name']}")
                crawler = ConfluenceCrawler(
                    src['url'],
                    src['username'],
                    src['api_token'],
                    error_handler
                )
                for space in src['spaces']:
                    click.echo(f"  Processing space: {space['key']}")
                    crawler.crawl_space(src['name'], space['key'], storage)

        # 同步 Jira
        if sources_to_sync['jira']:
            click.echo("\nSyncing Jira...")
            for src in sources_to_sync['jira']:
                click.echo(f"\nSource: {src['name']}")
                crawler = JiraCrawler(
                    src['url'],
                    src['username'],
                    src['api_token'],
                    error_handler
                )
                for project in src['projects']:
                    click.echo(f"  Processing project: {project['key']}")
                    crawler.crawl_project(src['name'], project['key'], storage)

        storage.save_state()
        error_handler.generate_error_report()
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


if __name__ == '__main__':
    cli()
