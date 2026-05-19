#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量 Jira 分析测试脚本

使用本地 LLM 对所有 KAN issue 进行完整分析，并生成 MD 报告
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime
from crawler.jira_analyzer import JiraDeepAnalyzer
from crawler.llm_client import LLMClientFactory

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_llm_connection(llm_client):
    """测试 LLM 连接"""
    print("🔍 测试 LLM 连接...")
    try:
        response = llm_client.generate("你好，请回复'连接成功'", max_tokens=50)
        print(f"✓ LLM 响应: {response[:100]}")
        return True
    except Exception as e:
        print(f"✗ LLM 连接失败: {e}")
        return False


def analyze_single_issue(analyzer, issue_key: str, output_dir: Path) -> bool:
    """分析单个 issue 并保存报告"""
    print(f"\n{'='*60}")
    print(f"📊 分析 {issue_key}")
    print(f"{'='*60}")

    try:
        # 执行分析
        report = analyzer.analyze(issue_key)

        # 保存报告
        jira_dir = output_dir / "jira"
        jira_dir.mkdir(parents=True, exist_ok=True)
        output_file = jira_dir / f"{issue_key}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✓ 分析完成，报告已保存: {output_file}")

        # 打印报告预览（前500字符）
        print(f"\n📄 报告预览:")
        print("-" * 60)
        print(report[:500])
        if len(report) > 500:
            print("...")
        print("-" * 60)

        return True

    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 开始全量 Jira 分析测试")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 加载配置
    print("\n📋 加载配置...")
    config = load_config()
    llm_config = config.get('llm', {})
    print(f"   LLM Provider: {llm_config.get('provider')}")
    print(f"   Base URL: {llm_config.get('base_url')}")
    print(f"   Model: {llm_config.get('model')}")

    # 2. 创建 LLM 客户端
    print("\n🤖 创建 LLM 客户端...")
    try:
        llm_client = LLMClientFactory.create_from_config(llm_config)
        print("   ✓ LLM 客户端创建成功")
    except Exception as e:
        print(f"   ✗ LLM 客户端创建失败: {e}")
        return 1

    # 3. 测试连接
    if not test_llm_connection(llm_client):
        print("\n❌ LLM 连接测试失败，请检查本地模型是否运行")
        return 1

    # 4. 创建分析器
    print("\n🔧 创建 Jira 分析器...")
    analyzer = JiraDeepAnalyzer(source_dir='./sources', llm_client=llm_client)

    # 注册所有分析器
    print("   📦 注册分析器...")
    from crawler.analyzers.issue_summary_analyzer import IssueSummaryAnalyzer
    from crawler.analyzers.root_cause_analyzer import RootCauseAnalyzer
    from crawler.analyzers.similar_jira_finder import SimilarJiraFinder
    from crawler.analyzers.closed_loop_checker import ClosedLoopChecker
    from crawler.analyzers.action_recommender import ActionRecommender
    from crawler.analyzers.metadata_extractor import MetadataExtractor
    from crawler.analyzers.comment_analyzer import CommentAnalyzer

    # 从配置中获取分析器配置
    jira_analysis_config = config.get('jira_analysis', {})

    # 1. Issue 摘要分析器（带代码覆盖）
    if jira_analysis_config.get('issue_summary', {}).get('enabled', True):
        analyzer.register_analyzer(IssueSummaryAnalyzer(llm_client, jira_analysis_config.get('issue_summary', {})))

    # 2. 根因分析器
    analyzer.register_analyzer(RootCauseAnalyzer(llm_client, jira_analysis_config.get('root_cause', {})))

    # 3. 类似问题查找器
    analyzer.register_analyzer(SimilarJiraFinder(
        source_dir='./sources',
        top_k=3,
        llm_client=llm_client,
        config=jira_analysis_config.get('similar_jira', {})
    ))

    # 4. 闭环检查器
    analyzer.register_analyzer(ClosedLoopChecker(llm_client, jira_analysis_config.get('closed_loop', {})))

    # 5. 元数据提取器
    analyzer.register_analyzer(MetadataExtractor(llm_client, jira_analysis_config.get('metadata_extractor', {})))

    # 6. 评论分析器
    analyzer.register_analyzer(CommentAnalyzer(llm_client, jira_analysis_config.get('comments', {})))

    # 7. 行动建议生成器
    analyzer.register_analyzer(ActionRecommender(llm_client, jira_analysis_config.get('action_recommender', {})))

    print(f"   ✓ 分析器创建成功，已注册 {len(analyzer.pipeline)} 个分析器")

    # 打印分析器列表
    print("\n   分析器列表:")
    for i, ana in enumerate(analyzer.pipeline, 1):
        print(f"      {i}. {ana.get_name()}")

    # 5. 获取所有 issue
    sources_dir = Path('./sources')
    issue_files = sorted(sources_dir.glob('KAN-*.md'))
    print(f"\n📁 找到 {len(issue_files)} 个 issue")

    # 6. 创建输出目录
    output_dir = Path('./tests/outputs')
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"   输出目录: {output_dir}")

    # 7. 分析所有 issue
    success_count = 0
    failed_issues = []

    for issue_file in issue_files:
        issue_key = issue_file.stem  # KAN-1, KAN-2, etc.

        if analyze_single_issue(analyzer, issue_key, output_dir):
            success_count += 1
        else:
            failed_issues.append(issue_key)

    # 8. 生成汇总报告
    print(f"\n{'='*60}")
    print("📊 分析汇总")
    print(f"{'='*60}")
    print(f"总计: {len(issue_files)} 个 issue")
    print(f"成功: {success_count} 个")
    print(f"失败: {len(failed_issues)} 个")

    if failed_issues:
        print(f"\n失败的 issue:")
        for issue in failed_issues:
            print(f"   - {issue}")

    # 生成汇总文件
    jira_dir = output_dir / "jira"
    summary_file = jira_dir / "summary.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"# Jira 分析汇总报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 统计信息\n\n")
        f.write(f"- 总计: {len(issue_files)} 个 issue\n")
        f.write(f"- 成功: {success_count} 个\n")
        f.write(f"- 失败: {len(failed_issues)} 个\n")
        f.write(f"- 成功率: {success_count/len(issue_files)*100:.1f}%\n\n")

        f.write(f"## 分析结果\n\n")
        for issue_file in issue_files:
            issue_key = issue_file.stem
            status = "✓" if issue_key not in failed_issues else "✗"
            report_file = f"jira/{issue_key}.md"
            f.write(f"- {status} [{issue_key}]({report_file})\n")

        if failed_issues:
            f.write(f"\n## 失败的 Issue\n\n")
            for issue in failed_issues:
                f.write(f"- {issue}\n")

    print(f"\n📄 汇总报告已保存: {summary_file}")
    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0 if len(failed_issues) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
