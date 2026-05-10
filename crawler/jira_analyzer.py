"""
Jira 深度分析器 - 主控制器
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from crawler.analysis_context import AnalysisContext
from crawler.analyzers.base import BaseAnalyzer
from crawler.llm_client import BaseLLMClient, create_llm_client


class JiraDeepAnalyzer:
    """Jira 深度分析器 - 协调分析流水线"""

    def __init__(self, source_dir: str = './sources', llm_client: Optional[BaseLLMClient] = None):
        """
        初始化分析器

        Args:
            source_dir: 源文件目录
            llm_client: LLM 客户端（如果为 None，使用 Mock 客户端）
        """
        self.source_dir = Path(source_dir)
        self.llm_client = llm_client or create_llm_client("mock")
        self.pipeline: List[BaseAnalyzer] = []

    def register_analyzer(self, analyzer: BaseAnalyzer) -> None:
        """
        注册分析器到流水线

        Args:
            analyzer: 分析器实例
        """
        self.pipeline.append(analyzer)

    def analyze(self, issue_key: str) -> str:
        """
        执行完整分析流水线

        Args:
            issue_key: Jira Issue Key (例如: KAN-1)

        Returns:
            Markdown 格式的分析报告

        Raises:
            FileNotFoundError: Issue 文件不存在
            RuntimeError: 分析过程中发生错误
        """
        # 1. 加载 Jira 数据
        jira_data = self._load_jira_data(issue_key)

        # 2. 创建分析上下文
        context = AnalysisContext(issue_key)

        # 3. 执行分析流水线
        for analyzer in self.pipeline:
            analyzer_name = analyzer.get_name()
            start_time = time.time()

            try:
                result = analyzer.analyze(jira_data, context)
                context.set_result(analyzer_name, result)

                duration_ms = (time.time() - start_time) * 1000
                context.record_timing(analyzer_name, duration_ms)

            except Exception as e:
                error_msg = f"{analyzer_name} 分析失败: {str(e)}"
                context.add_warning(error_msg)
                raise RuntimeError(error_msg) from e

        # 4. 生成报告
        report = self._generate_report(jira_data, context)

        return report

    def _load_jira_data(self, issue_key: str) -> Dict[str, Any]:
        """
        加载 Jira Issue 数据

        Args:
            issue_key: Jira Issue Key

        Returns:
            Jira 数据字典

        Raises:
            FileNotFoundError: Issue 文件不存在
        """
        issue_file = self.source_dir / f"{issue_key}.md"

        if not issue_file.exists():
            raise FileNotFoundError(f"Jira Issue 文件不存在: {issue_file}")

        with open(issue_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 Markdown 内容
        return self._parse_jira_markdown(issue_key, content)

    def _parse_jira_markdown(self, issue_key: str, content: str) -> Dict[str, Any]:
        """
        解析 Jira Markdown 文件

        Args:
            issue_key: Issue Key
            content: Markdown 内容

        Returns:
            解析后的数据字典
        """
        import re

        # 提取标题
        title_match = re.search(r'^#\s+\[' + issue_key + r'\]\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else 'N/A'

        # 提取元数据
        status_match = re.search(r'-\s*\*\*状态\*\*:\s*([^\n]+)', content)
        priority_match = re.search(r'-\s*\*\*优先级\*\*:\s*([^\n]+)', content)
        type_match = re.search(r'-\s*\*\*类型\*\*:\s*([^\n]+)', content)
        assignee_match = re.search(r'-\s*\*\*经办人\*\*:\s*([^\n]+)', content)

        # 提取描述
        desc_match = re.search(r'##\s+描述\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ''

        # 提取评论
        comments = []
        # 匹配格式: ### 作者 - 时间\n\n内容
        comment_pattern = re.compile(r'###\s+(.+?)\s+-\s+(.+?)\n\n(.+?)(?=\n###|\n##|\Z)', re.DOTALL)
        for match in comment_pattern.finditer(content):
            author = match.group(1).strip()
            timestamp = match.group(2).strip()
            comment_text = match.group(3).strip()
            comments.append(f"[{author} @ {timestamp}]\n{comment_text}")

        return {
            'key': issue_key,
            'title': title,
            'status': status_match.group(1).strip() if status_match else 'N/A',
            'priority': priority_match.group(1).strip() if priority_match else 'N/A',
            'type': type_match.group(1).strip() if type_match else 'N/A',
            'assignee': assignee_match.group(1).strip() if assignee_match else 'Unassigned',
            'description': description,
            'comments': comments,
            'raw_content': content
        }

    def _generate_report(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        生成 Markdown 分析报告

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            Markdown 格式的报告
        """
        lines = []

        # 标题
        lines.append(f"# Jira 深度分析报告: [{jira_data['key']}] {jira_data['title']}")
        lines.append("")
        lines.append(f"**生成时间**: {context.metadata['start_time']}")
        lines.append(f"**状态**: {jira_data['status']} | **优先级**: {jira_data['priority']} | **类型**: {jira_data['type']}")
        lines.append("")

        # 各部分分析结果
        sections = [
            ('knowledge', '相关知识检索'),
            ('root_cause', '根因分析'),
            ('similar_jira', '类似 Jira 分析'),
            ('closed_loop', '闭环检查'),
            ('comments', '评论分析'),
            ('actions', '行动建议')
        ]

        for key, title in sections:
            result = context.get_result(key)
            if result:
                lines.append(f"## {title}")
                lines.append("")
                lines.append(self._format_section(key, result))
                lines.append("")

        # 元数据
        if context.metadata['warnings']:
            lines.append("## ⚠️ 警告")
            lines.append("")
            for warning in context.metadata['warnings']:
                lines.append(f"- {warning['message']}")
            lines.append("")

        lines.append("## 📊 分析统计")
        lines.append("")
        lines.append(f"- **LLM 调用次数**: {context.metadata['llm_calls']}")
        lines.append(f"- **总耗时**: {sum(context.metadata['timing'].values()):.2f} ms")
        lines.append("")

        lines.append("---")
        lines.append("*本报告由 AI Tools Jira 深度分析器自动生成*")

        return '\n'.join(lines)

    def _format_section(self, section_key: str, result: Dict[str, Any]) -> str:
        """
        格式化报告章节

        Args:
            section_key: 章节键
            result: 分析结果

        Returns:
            格式化后的文本
        """
        # 根据不同的分析器类型使用专门的格式化方法
        formatters = {
            'knowledge': self._format_knowledge,
            'root_cause': self._format_root_cause,
            'similar_jira': self._format_similar_jira,
            'closed_loop': self._format_closed_loop,
            'comments': self._format_comments,
            'actions': self._format_actions
        }

        formatter = formatters.get(section_key)
        if formatter:
            return formatter(result)

        # 默认格式化
        return self._format_default(result)

    def _format_knowledge(self, result: Dict[str, Any]) -> str:
        """格式化知识检索结果"""
        lines = []

        keywords = result.get('keywords', [])
        if keywords:
            lines.append(f"**提取的关键词**: {', '.join(keywords)}")
            lines.append("")

        wiki_concepts = result.get('wiki_concepts', [])
        if wiki_concepts:
            lines.append("### Wiki 概念")
            lines.append("")
            for concept in wiki_concepts:
                lines.append(f"**{concept['keyword']}**:")
                lines.append(f"{concept['content'][:300]}...")
                lines.append("")

        related_sources = result.get('related_sources', [])
        if related_sources:
            lines.append("### 相关源文件")
            lines.append("")
            for source in related_sources:
                lines.append(f"**{source['keyword']}**:")
                for match in source['matches']:
                    lines.append(f"- [{match['file']}:{match['line']}] {match['text'][:150]}...")
                lines.append("")

        return '\n'.join(lines)

    def _format_root_cause(self, result: Dict[str, Any]) -> str:
        """格式化根因分析结果"""
        lines = []

        if result.get('direct_cause'):
            lines.append(f"**直接原因**: {result['direct_cause']}")
            lines.append("")

        if result.get('deep_cause'):
            lines.append(f"**深层原因**: {result['deep_cause']}")
            lines.append("")

        if result.get('trigger_condition'):
            lines.append(f"**触发条件**: {result['trigger_condition']}")
            lines.append("")

        if result.get('summary'):
            lines.append(result['summary'])
            lines.append("")

        return '\n'.join(lines)

    def _format_similar_jira(self, result: Dict[str, Any]) -> str:
        """格式化类似 Jira 结果"""
        lines = []

        similar_issues = result.get('similar_issues', [])
        total = result.get('total_candidates', 0)

        lines.append(f"找到 {len(similar_issues)} 个相似问题（共扫描 {total} 个候选）")
        lines.append("")

        for issue in similar_issues:
            score = issue['similarity_score']
            lines.append(f"### [{issue['key']}] {issue['title']}")
            lines.append(f"- **相似度**: {score:.2%}")
            lines.append(f"- **状态**: {issue['status']} | **优先级**: {issue['priority']}")
            lines.append("")

        return '\n'.join(lines)

    def _format_closed_loop(self, result: Dict[str, Any]) -> str:
        """格式化闭环检查结果"""
        lines = []

        is_closed = result.get('is_closed', False)
        status_icon = "✅" if is_closed else "❌"

        lines.append(f"**闭环状态**: {status_icon} {'已闭环' if is_closed else '未闭环'}")
        lines.append("")

        checks = [
            ('has_root_cause', 'root_cause_note', '根因识别'),
            ('has_fix', 'fix_note', '修复方案'),
            ('has_verification', 'verification_note', '验证测试')
        ]

        for has_key, note_key, label in checks:
            has_item = result.get(has_key, False)
            note = result.get(note_key, '')
            icon = "✓" if has_item else "✗"
            lines.append(f"- **{label}**: {icon} {note}")

        if result.get('conclusion'):
            lines.append("")
            lines.append(f"**结论**: {result['conclusion']}")

        return '\n'.join(lines)

    def _format_comments(self, result: Dict[str, Any]) -> str:
        """格式化评论分析结果"""
        lines = []

        if not result.get('has_comments'):
            return result.get('analysis', '无评论')

        count = result.get('comment_count', 0)
        analyzed = result.get('analyzed_count', 0)

        lines.append(f"共 {count} 条评论，已分析 {analyzed} 条")
        lines.append("")

        if result.get('summary'):
            lines.append(f"**整体摘要**: {result['summary']}")
            lines.append("")

        comment_analyses = result.get('comment_analyses', [])
        if comment_analyses:
            lines.append("### 详细分析")
            lines.append("")
            for ca in comment_analyses:
                lines.append(f"**评论 #{ca['index']}**:")
                lines.append(ca['analysis'])
                lines.append("")

        return '\n'.join(lines)

    def _format_actions(self, result: Dict[str, Any]) -> str:
        """格式化行动建议结果"""
        lines = []

        sections = [
            ('short_term', '短期行动（1-2 周）'),
            ('medium_term', '中期行动（1-2 月）'),
            ('long_term', '长期行动（3 月以上）')
        ]

        for key, title in sections:
            actions = result.get(key, [])
            if actions:
                lines.append(f"### {title}")
                lines.append("")
                for i, action in enumerate(actions, 1):
                    lines.append(f"{i}. {action}")
                lines.append("")

        return '\n'.join(lines)

    def _format_default(self, result: Dict[str, Any]) -> str:
        """默认格式化方法"""
        lines = []
        for key, value in result.items():
            if isinstance(value, list):
                lines.append(f"**{key}**:")
                for item in value:
                    lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append(f"**{key}**:")
                for k, v in value.items():
                    lines.append(f"  - {k}: {v}")
            else:
                lines.append(f"**{key}**: {value}")

        return '\n'.join(lines)
