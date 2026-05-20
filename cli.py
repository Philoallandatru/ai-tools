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


def override_llm_config(cfg: dict, base_url: Optional[str], model: Optional[str]) -> None:
    """覆盖配置中的 LLM 设置"""
    if base_url or model:
        if 'llm' not in cfg:
            cfg['llm'] = {}
        if base_url:
            cfg['llm']['base_url'] = base_url
        if model:
            cfg['llm']['model'] = model


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
    result = SyncService(cfg.model_dump()).sync_all(source_name=source, source_type=type)

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
@click.option('--wiki-name', help='Wiki 名称')
@click.option('--files', multiple=True, help='要编译的文件（支持 glob）')
@click.option('--batch-size', default=5, help='每批文件数量')
@click.option('--resume', is_flag=True, help='从上次失败处继续')
@click.option('--all-wikis', is_flag=True, help='编译所有 wiki')
@click.option('--config', default='config.yaml', help='配置文件路径')
@click.option('--llm-base-url', help='LLM API base URL (覆盖配置文件)')
@click.option('--llm-model', help='LLM 模型名称 (覆盖配置文件)')
@require_config
@handle_cli_errors
def compile_wiki(wiki_name, files, batch_size, resume, all_wikis, config, llm_base_url, llm_model):
    """编译 wiki 知识库（支持批量编译和多 wiki）"""
    from crawler.config.config_manager import ConfigManager
    from crawler.wiki_manager import WikiManager
    from crawler.wiki_batch_compiler import WikiBatchCompiler, BatchCompilationConfig
    import glob
    import shutil

    output = CLIOutput()
    cfg = ConfigManager(config).load()

    # 获取要编译的 wiki 列表
    wikis_config = cfg.get('wikis', {})
    repositories = wikis_config.get('repositories', [])

    if not repositories:
        output.error("未配置任何 wiki，请在 config.yaml 中添加 wikis 配置")
        return

    wikis_to_compile = []

    if all_wikis:
        wikis_to_compile = repositories
    elif wiki_name:
        wiki_config = next((w for w in repositories if w['name'] == wiki_name), None)
        if not wiki_config:
            output.error(f"Wiki 不存在: {wiki_name}")
            return
        wikis_to_compile = [wiki_config]
    else:
        # 使用默认 wiki
        default_name = wikis_config.get('default_wiki', 'default')
        wiki_config = next((w for w in repositories if w['name'] == default_name), None)
        if wiki_config:
            wikis_to_compile = [wiki_config]
        else:
            output.error(f"默认 wiki 不存在: {default_name}")
            return

    # 编译每个 wiki
    for wiki_config in wikis_to_compile:
        output.header(f"编译 wiki: {wiki_config['display_name']}")

        wiki_path = Path(wiki_config['path'])
        temp_dir = wiki_path / 'temp'

        # 如果指定了文件，先复制到 temp/
        if files and not resume:
            output.info(f"复制 {len(files)} 个文件到 temp/")
            temp_dir.mkdir(parents=True, exist_ok=True)

            for file_pattern in files:
                # 支持 glob 模式
                matched_files = glob.glob(file_pattern)
                for file_path in matched_files:
                    src = Path(file_path)
                    dst = temp_dir / src.name
                    shutil.copy2(src, dst)
                    output.info(f"  复制: {src.name}")

        # 检查 temp/ 是否有文件
        if not temp_dir.exists() or not list(temp_dir.glob("**/*.md")):
            output.warning(f"temp/ 目录为空，跳过编译")
            continue

        # 覆盖 LLM 配置（如果提供了命令行参数）
        override_llm_config(cfg, llm_base_url, llm_model)

        # 创建批量编译器
        compilation_config = wiki_config.get('compilation', {})
        compiler = WikiBatchCompiler(
            wiki_path=wiki_path,
            config=BatchCompilationConfig(
                batch_size=batch_size or compilation_config.get('batch_size', 5),
                compile_timeout=compilation_config.get('compile_timeout', 300),
                stop_on_failure=compilation_config.get('stop_on_failure', True)
            ),
            llm_config=cfg.get('llm', {})
        )

        # 开始编译
        result = compiler.start_batch_compilation(resume=resume)

        if result['status'] == 'no_files':
            output.warning(result['message'])
        elif result['status'] == 'success':
            output.success(f"编译完成: {result['completed_batches']} 个批次")
        elif result['status'] == 'partial':
            output.warning(f"部分成功: {result['completed_batches']}/{result['total_batches']} 个批次")
            for batch in result['batches']:
                if batch['status'] == 'failed':
                    output.error(f"批次 {batch['batch']} 失败: {batch['error']}")
        else:
            output.error(f"编译失败: {result.get('message', 'Unknown error')}")


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
@click.option('--target-wiki', default='default', help='目标 wiki 名称')
@click.option('--dry-run', is_flag=True, help='预览迁移（不实际执行）')
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def migrate_wiki(target_wiki, dry_run, config):
    """迁移现有 wiki/ 目录到多 wiki 架构"""
    from crawler.config.config_manager import ConfigManager
    from crawler.wiki_manager import WikiManager, WikiMetadata
    from crawler.config.models import WikiRepositoryConfig, WikiAutoMatchConfig, WikiCompilationConfig
    import shutil
    import yaml

    output = CLIOutput()
    cfg = ConfigManager(config).load()

    old_wiki_dir = Path('./wiki')
    if not old_wiki_dir.exists():
        output.error("旧的 wiki/ 目录不存在")
        return

    new_wiki_path = Path(f'./wikis/{target_wiki}')

    output.header(f"迁移 wiki/ → wikis/{target_wiki}/")

    if dry_run:
        output.info("[预览模式] 将执行以下操作:")
        output.info(f"  1. 创建目录: {new_wiki_path}")
        output.info(f"  2. 移动 wiki/ → {new_wiki_path}/wiki/")
        output.info(f"  3. 创建 .wiki-metadata.json")
        output.info(f"  4. 更新 config.yaml")
        return

    # 1. 创建新的 wiki 目录结构
    output.info("创建目录结构...")
    (new_wiki_path / 'temp').mkdir(parents=True, exist_ok=True)
    (new_wiki_path / 'sources').mkdir(parents=True, exist_ok=True)
    (new_wiki_path / '.llmwiki').mkdir(parents=True, exist_ok=True)

    # 2. 移动旧的 wiki/ 目录
    output.info(f"移动 wiki/ → {new_wiki_path}/wiki/")
    if (new_wiki_path / 'wiki').exists():
        output.warning(f"{new_wiki_path}/wiki/ 已存在，将被覆盖")
        shutil.rmtree(new_wiki_path / 'wiki')
    shutil.move(str(old_wiki_dir), str(new_wiki_path / 'wiki'))

    # 3. 创建元数据
    output.info("创建 .wiki-metadata.json")
    metadata_manager = WikiMetadata(new_wiki_path)
    metadata_manager.create(
        name=target_wiki,
        display_name=f"{target_wiki.title()} Wiki",
        description="Migrated from legacy wiki/",
        auto_match={
            'jira_projects': [],
            'confluence_spaces': [],
            'keywords': []
        },
        compilation={
            'batch_size': 5,
            'auto_compile': True
        }
    )

    # 4. 更新 config.yaml
    output.info("更新 config.yaml")
    config_path = Path(config)

    # 读取现有配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    # 添加 wikis 配置（如果不存在）
    if 'wikis' not in config_data:
        config_data['wikis'] = {
            'default_wiki': target_wiki,
            'repositories': []
        }

    # 添加迁移的 wiki
    wiki_config = {
        'name': target_wiki,
        'display_name': f"{target_wiki.title()} Wiki",
        'description': "Migrated from legacy wiki/",
        'path': f"./wikis/{target_wiki}",
        'auto_match': {
            'jira_projects': [],
            'confluence_spaces': [],
            'keywords': []
        },
        'compilation': {
            'batch_size': 5,
            'auto_compile': True,
            'compile_timeout': 300,
            'stop_on_failure': True
        }
    }

    # 检查是否已存在
    existing = next((w for w in config_data['wikis']['repositories'] if w['name'] == target_wiki), None)
    if not existing:
        config_data['wikis']['repositories'].append(wiki_config)

    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    output.success(f"迁移完成！")
    output.info(f"旧的 wiki/ 已移动到 wikis/{target_wiki}/wiki/")
    output.info(f"配置已更新到 {config}")
    output.info(f"\n使用以下命令编译:")
    output.info(f"  uv run python cli.py compile-wiki --wiki-name {target_wiki}")


@cli.command()
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def wiki_list(config):
    """列出所有配置的 wiki"""
    from crawler.config.config_manager import ConfigManager
    from crawler.wiki_manager import WikiManager

    output = CLIOutput()
    cfg = ConfigManager(config).load()

    wikis_config = cfg.get('wikis', {})
    repositories = wikis_config.get('repositories', [])
    default_wiki = wikis_config.get('default_wiki', 'default')

    if not repositories:
        output.warning("未配置任何 wiki")
        return

    output.header(f"配置的 Wiki ({len(repositories)} 个)")
    output.info(f"默认 wiki: {default_wiki}\n")

    for wiki in repositories:
        is_default = " [默认]" if wiki['name'] == default_wiki else ""
        output.subheader(f"{wiki['display_name']}{is_default}")
        output.key_value("名称", wiki['name'])
        output.key_value("路径", wiki['path'])
        output.key_value("描述", wiki.get('description', 'N/A'))

        # 检查是否存在
        wiki_path = Path(wiki['path'])
        exists = wiki_path.exists()
        output.key_value("状态", "已初始化" if exists else "未初始化")

        if exists:
            # 统计文件
            temp_files = list((wiki_path / 'temp').glob("**/*.md")) if (wiki_path / 'temp').exists() else []
            source_files = list((wiki_path / 'sources').glob("**/*.md")) if (wiki_path / 'sources').exists() else []
            wiki_files = list((wiki_path / 'wiki' / 'concepts').glob("*.md")) if (wiki_path / 'wiki' / 'concepts').exists() else []

            output.key_value("temp/ 文件", len(temp_files))
            output.key_value("sources/ 文件", len(source_files))
            output.key_value("wiki/concepts/ 文件", len(wiki_files))

        # 自动匹配规则
        auto_match = wiki.get('auto_match', {})
        if auto_match.get('jira_projects'):
            output.key_value("Jira 项目", ', '.join(auto_match['jira_projects']))
        if auto_match.get('keywords'):
            output.key_value("关键词", ', '.join(auto_match['keywords'][:3]) + ('...' if len(auto_match['keywords']) > 3 else ''))

        output.info("")


@cli.command()
@click.argument('wiki_name')
@click.option('--display-name', help='显示名称')
@click.option('--description', default='', help='描述')
@click.option('--jira-projects', help='Jira 项目（逗号分隔）')
@click.option('--keywords', help='关键词（逗号分隔）')
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def wiki_init(wiki_name, display_name, description, jira_projects, keywords, config):
    """初始化新的 wiki 仓库"""
    from crawler.config.config_manager import ConfigManager
    from crawler.wiki_manager import WikiManager
    from crawler.config.models import WikiRepositoryConfig, WikiAutoMatchConfig, WikiCompilationConfig
    import yaml

    output = CLIOutput()
    cfg = ConfigManager(config).load()

    # 检查 wiki 是否已存在
    wikis_config = cfg.get('wikis', {})
    repositories = wikis_config.get('repositories', [])
    existing = next((w for w in repositories if w['name'] == wiki_name), None)

    if existing:
        output.error(f"Wiki '{wiki_name}' 已存在")
        return

    # 创建 wiki 配置
    wiki_config = WikiRepositoryConfig(
        name=wiki_name,
        display_name=display_name or f"{wiki_name.title()} Wiki",
        description=description,
        path=f"./wikis/{wiki_name}",
        auto_match=WikiAutoMatchConfig(
            jira_projects=jira_projects.split(',') if jira_projects else [],
            confluence_spaces=[],
            keywords=keywords.split(',') if keywords else []
        ),
        compilation=WikiCompilationConfig(
            batch_size=5,
            auto_compile=True,
            compile_timeout=300,
            stop_on_failure=True
        )
    )

    # 初始化 wiki
    output.info(f"初始化 wiki: {wiki_config.display_name}")
    wiki_manager = WikiManager()
    wiki_path = wiki_manager.initialize_wiki(wiki_config)

    # 更新 config.yaml
    output.info("更新 config.yaml")
    config_path = Path(config)

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)

    if 'wikis' not in config_data:
        config_data['wikis'] = {
            'default_wiki': wiki_name,
            'repositories': []
        }

    config_data['wikis']['repositories'].append({
        'name': wiki_config.name,
        'display_name': wiki_config.display_name,
        'description': wiki_config.description,
        'path': wiki_config.path,
        'auto_match': {
            'jira_projects': wiki_config.auto_match.jira_projects,
            'confluence_spaces': wiki_config.auto_match.confluence_spaces,
            'keywords': wiki_config.auto_match.keywords
        },
        'compilation': {
            'batch_size': wiki_config.compilation.batch_size,
            'auto_compile': wiki_config.compilation.auto_compile,
            'compile_timeout': wiki_config.compilation.compile_timeout,
            'stop_on_failure': wiki_config.compilation.stop_on_failure
        }
    })

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    output.success(f"Wiki '{wiki_name}' 初始化完成！")
    output.info(f"路径: {wiki_path}")
    output.info(f"\n使用以下命令编译:")
    output.info(f"  uv run python cli.py compile-wiki --wiki-name {wiki_name} --files sources/*.md")


@cli.command()
@click.argument('pdf_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='输出Markdown文件路径')
@click.option('--start-page', default=0, help='起始页码（从0开始）')
@click.option('--end-page', type=int, help='结束页码（不包含）')
@handle_cli_errors
def convert_pdf(pdf_file, output, start_page, end_page):
    """将PDF转换为Markdown格式"""
    from crawler.pdf_converter import PDFConverter

    output_cli = CLIOutput()
    converter = PDFConverter()

    # 获取PDF信息
    info = converter.get_pdf_info(pdf_file)
    output_cli.header(f"PDF信息")
    output_cli.key_value("文件名", info['filename'])
    output_cli.key_value("总页数", info['total_pages'])
    output_cli.key_value("文件大小", f"{info['file_size_mb']:.2f} MB")
    if info['metadata'].get('title'):
        output_cli.key_value("标题", info['metadata']['title'])

    # 确定输出路径
    if not output:
        pdf_path = Path(pdf_file)
        output = f"./test_output/{pdf_path.stem}_pages_{start_page+1}-{end_page or info['total_pages']}.md"

    # 转换
    output_cli.info(f"\n开始转换...")
    markdown = converter.convert_to_markdown(pdf_file, output, start_page, end_page)

    output_cli.success(f"转换完成: {output}")
    output_cli.key_value("内容长度", f"{len(markdown):,} 字符")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', default='./split_output', help='输出目录')
@click.option('--max-chars', default=2000, help='每个分块的最大字符数')
@click.option('--split-level', type=click.Choice(['1', '2', '3']), default='2', help='分割级别')
@click.option('--dry-run', is_flag=True, help='预览分割结果')
@handle_cli_errors
def split_doc(input_file, output_dir, max_chars, split_level, dry_run):
    """分割文档为小块"""
    from crawler.doc_splitter import DocumentSplitter

    input_path = Path(input_file)
    output_path = Path(output_dir)

    splitter = DocumentSplitter(max_chars=max_chars, split_level=int(split_level))
    splitter.split_file(input_path, output_path, dry_run=dry_run)


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
    # 支持两种目录结构：sources/jira/*.md 和 sources/*.md
    jira_files = list(source_path.glob(f'**/*{issue_key}*.md'))

    # 精确匹配：只保留文件名中包含完整 issue key 的文件
    # 使用正则表达式确保 issue_key 是完整的（有单词边界）
    import re
    pattern = re.compile(rf'\b{re.escape(issue_key)}\b')
    jira_files = [f for f in jira_files if pattern.search(f.name)]

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
@click.option('--wiki-name', help='指定 wiki 名称')
@click.option('--wiki-mode', type=click.Choice(['specify', 'auto_match', 'search_all']),
              default='auto_match', help='Wiki 选择模式')
@click.option('--output-dir', default='./reports', help='输出目录')
@click.option('--llm-provider', type=click.Choice(['openai', 'mock']), default='openai', help='LLM 提供商')
@click.option('--llm-base-url', help='LLM API base URL')
@click.option('--llm-model', help='LLM 模型名称')
@click.option('--config', default='config.yaml', help='配置文件路径')
@require_config
@handle_cli_errors
def analyze_jira(issue_key, source_dir, wiki_name, wiki_mode, output_dir, llm_provider, llm_base_url, llm_model, config):
    """分析 Jira issue（支持多 wiki）"""
    output_cli = CLIOutput()
    cfg = ConfigManager(config).load()  # 返回字典

    # 如果指定了 wiki_name，强制使用 specify 模式
    if wiki_name and wiki_mode != 'specify':
        wiki_mode = 'specify'

    # 覆盖 LLM 配置
    override_llm_config(cfg, llm_base_url, llm_model)

    service = AnalysisService(config=cfg)
    report_path = service.analyze_jira(
        issue_key=issue_key,
        output_dir=output_dir,
        wiki_mode=wiki_mode,
        wiki_name=wiki_name,
        llm_provider=llm_provider
    )

    output_cli.success(f"分析报告已生成: {report_path}")


@cli.command()
@click.argument('doc_path', type=click.Path(exists=True))
@click.option('--config', default='configs/doc_analysis_config.yaml', help='配置文件路径')
@click.option('--output', help='输出文件路径')
@click.option('--dry-run', is_flag=True, help='预览分析结果')
@handle_cli_errors
def analyze_doc(doc_path, config, output, dry_run):
    """分析文档"""
    from crawler.doc_analyzer import DocumentAnalyzer

    output_cli = CLIOutput()

    if dry_run:
        output_cli.info(f"将分析文档: {doc_path}")
        output_cli.info(f"配置: {config}")
        return

    analyzer = DocumentAnalyzer(config_path=config)
    result = analyzer.analyze_document(doc_path, output_path=output, dry_run=False)
    output_cli.success(f"分析完成: {result}")


if __name__ == '__main__':
    cli()
