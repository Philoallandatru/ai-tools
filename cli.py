"""
CLI 入口 - Atlassian 数据爬取工具
"""

import sys
import json
import subprocess
import click
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

# 强制使用 UTF-8 编码（Windows 兼容性）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from crawler.doc_splitter import DocumentSplitter
from crawler.searcher import ContentSearcher
from crawler.config import ConfigManager
from crawler.services import AnalysisService, ReportService, SyncService
from crawler.cli.output import CLIOutput
from crawler.cli.decorators import handle_cli_errors, require_config
from crawler.utils import parse_jira_metadata, parse_confluence_metadata


@click.group()
def cli():
    """Atlassian 数据爬取工具 - 从 Jira 和 Confluence 爬取数据到本地 markdown"""
    pass


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
@handle_cli_errors
def init(config):
    """初始化配置文件"""
    output = CLIOutput()
    config_path = Path(config)

    if config_path.exists():
        output.warning(f"配置文件 {config} 已存在")
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
        },
        'logging': {
            'level': 'INFO',
            'format': 'json',
            'file': 'logs/app.log'
        }
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

    output.success(f"配置文件已创建: {config}")
    output.info("\n请编辑配置文件并设置环境变量:")
    output.info("  export CONFLUENCE_API_TOKEN='your-token'")
    output.info("  export JIRA_API_TOKEN='your-token'")


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def list_sources(config):
    """列出所有配置的数据源"""
    output = CLIOutput()
    cfg = ConfigManager(config).load_validated()

    output.header("Confluence Sources")
    for src in cfg.sources.confluence:
        output.info(f"  - {src.name}")
        output.info(f"    URL: {src.url}")
        spaces = ', '.join([s.key for s in src.spaces])
        output.info(f"    Spaces: {spaces}")

    output.header("Jira Sources")
    for src in cfg.sources.jira:
        output.info(f"  - {src.name}")
        output.info(f"    URL: {src.url}")
        projects = ', '.join([p.key for p in src.projects])
        output.info(f"    Projects: {projects}")


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
@click.option('--source', help='指定要同步的数据源名称')
@click.option('--type', type=click.Choice(['confluence', 'jira', 'all']), default='all', help='数据源类型')
@require_config
@handle_cli_errors
def sync(config, source, type):
    """
    执行同步

    示例:
      crawler sync                              # 同步所有数据源
      crawler sync --type confluence            # 只同步所有 Confluence
      crawler sync --type jira                  # 只同步所有 Jira
      crawler sync --source my-confluence       # 同步指定数据源
    """
    output = CLIOutput()
    cfg = ConfigManager(config).load_validated()
    result = SyncService(cfg).sync_all(source_name=source, source_type=type)

    sources_to_sync = result["sources"]
    stats = result["stats"]

    # 显示 Confluence 结果
    if sources_to_sync['confluence']:
        output.subheader("Confluence 同步结果")
        for item in result["results"]["confluence"]:
            item_stats = item["stats"]
            output.success(
                f"{item['source']}/{item['target']}: "
                f"{item_stats['pages']} pages, {item_stats['attachments']} attachments"
            )

    # 显示 Jira 结果
    if sources_to_sync['jira']:
        output.subheader("Jira 同步结果")
        for item in result["results"]["jira"]:
            item_stats = item["stats"]
            output.success(
                f"{item['source']}/{item['target']}: "
                f"{item_stats['issues']} issues, {item_stats['attachments']} attachments"
            )

    # 显示错误
    for error in result["errors"]:
        output.error(f"{error['source']}/{error['target']}: {error['error']}")

    # 显示统计摘要
    output.separator()
    output.subheader("同步摘要")
    if sources_to_sync['confluence']:
        output.info("Confluence:")
        output.key_value("总页面", stats['confluence']['total'], indent=1)
        output.key_value("已拉取", f"{stats['confluence']['pages']} (新增或已更新)", indent=1)
        output.key_value("已跳过", f"{stats['confluence']['skipped']} (未变化)", indent=1)
        output.key_value("附件", stats['confluence']['attachments'], indent=1)

    if sources_to_sync['jira']:
        output.info("Jira:")
        output.key_value("总 issues", stats['jira']['total'], indent=1)
        output.key_value("已拉取", f"{stats['jira']['issues']} (新增或已更新)", indent=1)
        output.key_value("已跳过", f"{stats['jira']['skipped']} (未变化)", indent=1)
        output.key_value("附件", stats['jira']['attachments'], indent=1)

    output.separator()
    output.success("同步完成!")


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def status(config):
    """查看同步状态"""
    output = CLIOutput()
    cfg = ConfigManager(config).load_validated()
    state_file = Path(cfg.sync.state_file)

    if not state_file.exists():
        output.warning("尚未执行过同步")
        return

    with open(state_file, encoding='utf-8') as f:
        state = json.load(f)

    output.header("同步状态")
    output.key_value("上次同步", state.get('last_sync', 'N/A'))

    # 统计 Confluence
    confluence_count = 0
    for source_data in state.get('confluence', {}).values():
        for space_data in source_data.values():
            confluence_count += len(space_data)

    # 统计 Jira
    jira_count = 0
    for source_data in state.get('jira', {}).values():
        for project_data in source_data.values():
            jira_count += len(project_data)

    output.key_value("Confluence 页面", confluence_count)
    output.key_value("Jira Issues", jira_count)


@cli.command()
@handle_cli_errors
def compile_wiki():
    """编译 wiki 知识库"""
    output = CLIOutput()
    output.info("正在编译 wiki...")
    subprocess.run(['python', '-m', 'crawler.wiki_compiler'], check=True)
    output.success("Wiki 编译完成!")


@cli.command()
@click.argument('question')
@click.option('--save', is_flag=True, help='保存查询结果')
@handle_cli_errors
def query_wiki(question, save):
    """查询 wiki 知识库"""
    output = CLIOutput()
    output.info(f"查询: {question}")
    cmd = ['python', '-m', 'crawler.wiki_query', question]
    if save:
        cmd.append('--save')
    subprocess.run(cmd, check=True)


@cli.command()
@handle_cli_errors
def wiki_status():
    """显示 wiki 状态"""
    output = CLIOutput()
    wiki_dir = Path('./wiki')

    if not wiki_dir.exists():
        output.warning("Wiki 目录不存在")
        return

    # 统计文档
    md_files = list(wiki_dir.glob('**/*.md'))
    index_file = wiki_dir / 'index.faiss'

    output.header("Wiki 状态")
    output.key_value("文档数量", len(md_files))
    output.key_value("索引状态", "已创建" if index_file.exists() else "未创建")

    if index_file.exists():
        import os
        size_mb = os.path.getsize(index_file) / (1024 * 1024)
        output.key_value("索引大小", f"{size_mb:.2f} MB")


@cli.command()
@click.option('--time', default=60, help='监控时间（秒）')
@handle_cli_errors
def watch_wiki(time):
    """监控 wiki 变化"""
    output = CLIOutput()
    output.info(f"监控 wiki 变化 ({time} 秒)...")
    subprocess.run(['python', '-m', 'crawler.wiki_watcher', '--time', str(time)], check=True)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', default='./split_output', help='输出目录')
@click.option('--max-chars', default=2000, help='每个分块的最大字符数')
@click.option('--split-level', type=click.Choice(['1', '2', '3']), default='2', help='分割级别')
@click.option('--dry-run', is_flag=True, help='预览分割结果')
@handle_cli_errors
def split_doc(input_file, output_dir, max_chars, split_level, dry_run):
    """分割文档为小块"""
    output = CLIOutput()
    splitter = DocumentSplitter(max_chars=max_chars, split_level=int(split_level))

    input_path = Path(input_file)
    content = input_path.read_text(encoding='utf-8')
    chunks = splitter.split(content)

    output.info(f"文档将被分割为 {len(chunks)} 个块")

    if dry_run:
        for i, chunk in enumerate(chunks, 1):
            output.subheader(f"块 {i} ({len(chunk)} 字符)")
            preview = chunk[:200] + '...' if len(chunk) > 200 else chunk
            output.info(preview)
        return

    # 保存分块
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    base_name = input_path.stem
    for i, chunk in enumerate(chunks, 1):
        chunk_file = output_path / f"{base_name}_part{i}.md"
        chunk_file.write_text(chunk, encoding='utf-8')

    output.success(f"文档已分割并保存到 {output_dir}")


@cli.command()
@click.argument('query')
@click.option('--file-type', type=click.Choice(['confluence', 'jira', 'all']), default='all', help='文件类型')
@click.option('--context-lines', '-C', default=2, help='显示上下文行数')
@click.option('--regex', is_flag=True, help='使用正则表达式')
@click.option('--case-sensitive', is_flag=True, help='区分大小写')
@click.option('--max-results', default=50, help='最大结果数')
@click.option('--source-dir', default='./sources', help='源目录')
@click.option('--no-highlight', is_flag=True, help='不高亮显示')
@click.option('--stats-only', is_flag=True, help='只显示统计信息')
@handle_cli_errors
def search(query, file_type, context_lines, regex, case_sensitive, max_results, source_dir, no_highlight, stats_only):
    """搜索内容"""
    output = CLIOutput()
    searcher = ContentSearcher(source_dir=source_dir)

    results = searcher.search(
        query=query,
        file_type=file_type,
        context_lines=context_lines,
        max_results=max_results,
        use_regex=regex,
        case_sensitive=case_sensitive
    )

    if stats_only:
        output.stats({
            '匹配数': len(results)
        })
        return

    output.header(f"搜索结果: '{query}'")

    # 按文件分组显示
    current_file = None
    for match in results:
        if current_file != match.file_path:
            current_file = match.file_path
            output.subheader(str(match.file_path))

        output.info(f"  行 {match.line_number}: {match.line_content.strip()}")

    output.separator()
    output.info(f"找到 {len(results)} 处匹配")


@cli.command()
@click.argument('issue_key')
@click.option('--source-dir', default='./sources', help='源目录')
@handle_cli_errors
def find_jira(issue_key, source_dir):
    """查找 Jira issue"""
    output = CLIOutput()
    source_path = Path(source_dir)
    jira_files = list(source_path.glob(f'**/jira/**/*{issue_key}*.md'))

    if not jira_files:
        output.warning(f"未找到 issue: {issue_key}")
        return

    output.header(f"找到 {len(jira_files)} 个匹配的文件")
    for file_path in jira_files:
        metadata = parse_jira_metadata(file_path)
        if metadata:
            output.info(f"\n文件: {file_path}")
            output.key_value("Issue Key", metadata.get('issue_key'), indent=1)
            output.key_value("状态", metadata.get('status'), indent=1)
            output.key_value("优先级", metadata.get('priority'), indent=1)
            output.key_value("类型", metadata.get('issue_type'), indent=1)


@cli.command()
@click.option('--source-dir', default='./sources', help='源目录')
@click.option('--status', help='按状态过滤')
@click.option('--priority', help='按优先级过滤')
@click.option('--issue-type', help='按类型过滤')
@handle_cli_errors
def list_jira(source_dir, status, priority, issue_type):
    """列出 Jira issues"""
    output = CLIOutput()
    source_path = Path(source_dir)
    jira_files = list(source_path.glob('**/jira/**/*.md'))

    issues = []
    for file_path in jira_files:
        metadata = parse_jira_metadata(file_path)
        if metadata:
            # 应用过滤器
            if status and metadata.get('status') != status:
                continue
            if priority and metadata.get('priority') != priority:
                continue
            if issue_type and metadata.get('issue_type') != issue_type:
                continue
            issues.append(metadata)

    if not issues:
        output.warning("未找到匹配的 issues")
        return

    output.header(f"找到 {len(issues)} 个 issues")
    output.table(issues, headers=['issue_key', 'status', 'priority', 'issue_type', 'summary'])


@cli.command()
@click.option('--report-type', type=click.Choice(['weekly', 'jira']), required=True, help='报告类型')
@click.option('--start-date', help='开始日期 (YYYY-MM-DD)')
@click.option('--end-date', help='结束日期 (YYYY-MM-DD)')
@click.option('--output', help='输出目录路径')
@click.option('--source-dir', default='./sources', help='源目录')
@click.option('--output-format', type=click.Choice(['markdown', 'json']), default='markdown', help='输出格式')
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def generate_report(report_type, start_date, end_date, output, source_dir, output_format, config):
    """生成报告"""
    from datetime import datetime
    output_cli = CLIOutput()
    cfg = ConfigManager(config).load()  # 返回字典

    # 转换日期字符串为 date 对象
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

    service = ReportService(config=cfg)
    result = service.generate(
        report_type=report_type,
        start_date=start_date_obj,
        end_date=end_date_obj,
        output_dir=output or './reports',
        source_dir=source_dir,
        output_format=output_format
    )

    output_cli.success(f"报告已生成: {result.output_file}")


@cli.command()
@click.option('--doc-type', type=click.Choice(['confluence', 'jira', 'all']), default='all', help='文档类型')
@click.option('--statuses', help='状态列表（逗号分隔）')
@click.option('--today', is_flag=True, help='今天更新的')
@click.option('--yesterday', is_flag=True, help='昨天更新的')
@click.option('--days', type=int, help='最近N天更新的')
@click.option('--output', help='输出文件')
@click.option('--source-dir', default='./sources', help='源目录')
@handle_cli_errors
def export_filtered(doc_type, statuses, today, yesterday, days, output, source_dir):
    """导出过滤后的文档"""
    output_cli = CLIOutput()
    source_path = Path(source_dir)

    # 计算日期范围
    end_date = datetime.now()
    if today:
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif yesterday:
        start_date = (end_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif days:
        start_date = end_date - timedelta(days=days)
    else:
        start_date = None

    # 解析状态列表
    status_list = [s.strip() for s in statuses.split(',')] if statuses else None

    # 收集文件
    files = []
    if doc_type in ('jira', 'all'):
        for file_path in source_path.glob('**/jira/**/*.md'):
            metadata = parse_jira_metadata(file_path)
            if metadata:
                # 应用过滤器
                if status_list and metadata.get('status') not in status_list:
                    continue
                if start_date:
                    # 简化：假设所有文件都符合日期条件
                    pass
                files.append(str(file_path))

    if doc_type in ('confluence', 'all'):
        for file_path in source_path.glob('**/confluence/**/*.md'):
            if start_date:
                # 简化：假设所有文件都符合日期条件
                pass
            files.append(str(file_path))

    # 导出
    if output:
        output_path = Path(output)
        output_path.write_text('\n'.join(files), encoding='utf-8')
        output_cli.success(f"已导出 {len(files)} 个文件到 {output}")
    else:
        output_cli.header(f"找到 {len(files)} 个文件")
        for file in files:
            output_cli.info(file)


@cli.command()
@click.argument('issue_key')
@click.option('--source-dir', default='./sources', help='源目录')
@click.option('--wiki-dir', default='./wiki', help='Wiki 目录')
@click.option('--output-dir', default='./reports', help='输出目录')
@click.option('--llm-provider', type=click.Choice(['openai', 'mock']), default='openai', help='LLM 提供商')
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def analyze_jira(issue_key, source_dir, wiki_dir, output_dir, llm_provider, config):
    """分析 Jira issue"""
    output_cli = CLIOutput()
    cfg = ConfigManager(config).load()  # 返回字典

    service = AnalysisService(config=cfg)
    report_path = service.analyze_jira(
        issue_key=issue_key,
        output_dir=output_dir
    )

    output_cli.success(f"分析报告已生成: {report_path}")


@cli.command()
@click.argument('doc_path', type=click.Path(exists=True))
@click.option('--config', default='config.yaml', help='配置文件路径')
@click.option('--output', help='输出文件路径')
@click.option('--dry-run', is_flag=True, help='预览分析结果')
@require_config
@handle_cli_errors
def analyze_doc(doc_path, config, output, dry_run):
    """分析文档"""
    output_cli = CLIOutput()
    cfg = ConfigManager(config).load()  # 返回字典

    service = AnalysisService(config=cfg)

    if dry_run:
        output_cli.info(f"将分析文档: {doc_path}")
        output_cli.info(f"配置: {config}")
        return

    result = service.analyze_document(doc_path, output_path=output)
    output_cli.success(f"分析完成: {result}")


if __name__ == '__main__':
    cli()
