"""
Jira 深度分析器 - 主控制器
"""

from pathlib import Path
from typing import Dict, Any, Optional
from crawler.analysis_context import AnalysisContext
from crawler.unified_analyzer import UnifiedAnalyzer
from crawler.llm_client import BaseLLMClient, LLMClientFactory


class JiraDeepAnalyzer(UnifiedAnalyzer):
    """Jira 深度分析器 - 协调分析流水线"""

    def __init__(self, source_dir: str = './sources', llm_client: Optional[BaseLLMClient] = None):
        """
        初始化分析器

        Args:
            source_dir: 源文件目录
            llm_client: LLM 客户端（如果为 None，使用 Mock 客户端）
        """
        llm = llm_client or LLMClientFactory.create_from_config({'provider': 'mock'})
        super().__init__(llm)
        self.source_dir = Path(source_dir)

    def analyze(self, issue_key: str, context: Optional[AnalysisContext] = None) -> str:
        """
        执行完整分析流水线

        Args:
            issue_key: Jira Issue Key (例如: KAN-1) 或数据字典
            context: 分析上下文（可选）

        Returns:
            Markdown 格式的分析报告

        Raises:
            FileNotFoundError: Issue 文件不存在
            RuntimeError: 分析过程中发生错误
        """
        # 支持传入 issue_key 字符串或数据字典
        if isinstance(issue_key, str):
            # 1. 加载 Jira 数据
            print(f"   📄 加载 Jira 数据: {issue_key}", flush=True)
            jira_data = self._load_jira_data(issue_key)
            print(f"   ✓ 数据加载完成", flush=True)
            key = issue_key
        else:
            # 传入的是数据字典
            jira_data = issue_key
            key = jira_data.get('key', 'unknown')

        # 2. 创建分析上下文
        if context is None:
            print(f"   🔧 创建分析上下文", flush=True)
            context = AnalysisContext(key)
            print(f"   ✓ 上下文创建完成", flush=True)

        # 3. 执行分析流水线（使用统一的 execute_pipeline）
        print(f"   🚀 开始执行 {len(self.pipeline)} 个分析器", flush=True)
        context = self.execute_pipeline(jira_data, context, stop_on_error=True)

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
        matches = list(comment_pattern.finditer(content))
        print(f"[DEBUG] 从 markdown 中提取到 {len(matches)} 条评论")

        for match in matches:
            author = match.group(1).strip()
            timestamp = match.group(2).strip()
            comment_text = match.group(3).strip()
            comments.append(f"[{author} @ {timestamp}]\n{comment_text}")

        print(f"[DEBUG] 最终评论列表包含 {len(comments)} 条评论")

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

        # 问题摘要（新增）
        summary_result = context.get_result('issue_summary')
        if summary_result:
            lines.append("## 📋 问题摘要")
            lines.append("")
            lines.append(f"**客户名称**: {summary_result.get('customer', '无')}")
            lines.append(f"**测试项目**: {summary_result.get('test_project', '无')}")
            lines.append(f"**测试平台**: {summary_result.get('test_platform', '无')}")
            lines.append("")

            test_steps = summary_result.get('test_steps', [])
            if test_steps:
                lines.append("**测试步骤**:")
                for i, step in enumerate(test_steps, 1):
                    lines.append(f"{i}. {step}")
            else:
                lines.append("**测试步骤**: 无")
            lines.append("")

            lines.append(f"**根因**: {summary_result.get('root_cause', '无')}")
            lines.append(f"**修复方案**: {summary_result.get('fix_solution', '无')}")
            lines.append("")

            code_coverage = summary_result.get('code_coverage')
            if code_coverage and code_coverage.get('enabled'):
                matches = code_coverage.get('matches', 0)
                if matches > 0:
                    lines.append(f"**代码覆盖检查**: 找到 {matches} 个相关代码文件")
                else:
                    lines.append("**代码覆盖检查**: 未找到相关代码")
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append(f"**生成时间**: {context.metadata.get('created_at', 'N/A')}")
        lines.append(f"**状态**: {jira_data['status']} | **优先级**: {jira_data['priority']} | **类型**: {jira_data['type']}")
        lines.append("")

        # 各部分分析结果
        sections = [
            ('knowledge', '相关知识检索'),
            ('root_cause', '根因分析'),
            ('similar_jira', '类似 Jira 分析'),
            ('closed_loop', '闭环检查'),
            ('code_coverage', '代码覆盖率分析'),
            ('comments', '评论分析'),
            ('comments_compact', '评论分析'),  # Phase 2: 精简评论分析
            ('metadata', '关键元数据'),  # Phase 2: 元数据提取
            ('actions', '行动建议')
        ]

        for key, title in sections:
            result = context.get_result(key)
            if result:
                lines.append(f"## {title}")
                lines.append("")
                lines.append(self._format_section(key, result))
                lines.append("")

        # 自定义分析器结果
        custom_results = []
        for analyzer_key, result in context.results.items():
            if analyzer_key.startswith('custom_'):
                custom_results.append((analyzer_key, result))

        if custom_results:
            lines.append("---")
            lines.append("")
            lines.append("## 🔧 自定义分析")
            lines.append("")

            for analyzer_key, result in custom_results:
                analyzer_name = result.get('analyzer_name', analyzer_key)
                analysis_result = result.get('result', '')

                lines.append(f"### {analyzer_name}")
                lines.append("")
                lines.append(analysis_result)
                lines.append("")

        # 元数据
        if context.warnings:
            lines.append("## ⚠️ 警告")
            lines.append("")
            for warning in context.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        lines.append("## 📊 分析统计")
        lines.append("")
        lines.append(f"- **LLM 调用次数**: {context.metadata.get('llm_calls', 0)}")
        lines.append(f"- **总耗时**: {context.get_total_time():.2f} ms")
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
            'code_coverage': self._format_code_coverage,
            'comments': self._format_comments,
            'comments_compact': self._format_comments_compact,  # Phase 2: 精简评论分析
            'metadata': self._format_metadata,  # Phase 2: 元数据提取
            'actions': self._format_actions
        }

        formatter = formatters.get(section_key)
        if formatter:
            return formatter(result)

        # 默认格式化
        return self._format_default(result)

    def _clean_wiki_content(self, content: str) -> str:
        """清理 Wiki 内容，去除 frontmatter 和 <think> 标签"""
        import re

        if not content:
            return ""

        # 1. 首先尝试提取 summary（在 frontmatter 中）
        summary_match = re.search(r'summary:\s*(.+?)(?:\n|sources:|kind:|createdAt:)', content, re.IGNORECASE | re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            # 清理 summary 中可能的多余空白
            summary = re.sub(r'\s+', ' ', summary)
            return summary

        # 2. 去除 frontmatter (--- ... ---)
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

        # 3. 去除 <think> 标签及其内容（循环处理嵌套）
        max_iterations = 5
        for _ in range(max_iterations):
            prev_content = content
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)
            if content == prev_content:
                break

        # 4. 去除单独的标签
        content = re.sub(r'</?think>', '', content, flags=re.IGNORECASE)

        # 5. 去除多余的空行
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 6. 返回清理后的内容
        return content.strip()

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

            # 统计搜索策略
            strategy_counts = {}
            for concept in wiki_concepts:
                source = concept.get('source', 'unknown')
                strategy_counts[source] = strategy_counts.get(source, 0) + 1

            # 显示搜索策略信息
            if strategy_counts:
                strategy_names = {
                    'llm-wiki-compiler': 'LLM 查询',
                    'filename_exact': '文件名精确匹配',
                    'filename_partial': '文件名部分匹配',
                    'content_match': '内容匹配'
                }
                strategy_info = ', '.join([f"{strategy_names.get(k, k)}({v})" for k, v in strategy_counts.items()])
                lines.append(f"*检索策略: {strategy_info}*")
                lines.append("")

            for concept in wiki_concepts:
                keyword = concept['keyword']
                source = concept.get('source', 'unknown')
                file_name = concept.get('file', '')
                llm_analysis = concept.get('llm_analysis', {})

                # 显示关键词和来源
                if file_name:
                    lines.append(f"**{keyword}** (`{file_name}`):")
                else:
                    lines.append(f"**{keyword}**:")

                # 清理并提取概念内容
                content = concept.get('content', '')
                cleaned_content = self._clean_wiki_content(content)

                # 显示清理后的内容（最多 300 字符）
                if cleaned_content:
                    lines.append(f"   {cleaned_content[:300]}...")
                lines.append("")

                # 如果有 LLM 分析，显示相关性分析
                if llm_analysis:
                    score = llm_analysis.get('score', 0)
                    reason = llm_analysis.get('reason', '无分析')

                    # 根据得分显示相关性等级
                    if score >= 7:
                        relevance = "高"
                    elif score >= 4:
                        relevance = "中"
                    else:
                        relevance = "低"

                    lines.append(f"   **相关性**: {relevance} ({score}/10)")
                    lines.append(f"   **分析**: {reason}")
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

            # 添加相关性分析
            if issue.get('relevance_analysis'):
                lines.append("")
                lines.append("**相关性分析**:")
                lines.append(issue['relevance_analysis'])

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

        conclusion = result.get('conclusion', '')
        if conclusion:
            lines.append("")
            lines.append(f"**结论**: {conclusion}")

        return '\n'.join(lines)

    def _format_code_coverage(self, result: Dict[str, Any]) -> str:
        """格式化代码覆盖率分析结果"""
        lines = []

        if not result.get('has_code_coverage'):
            return result.get('message', '无代码覆盖率信息')

        # 核心模块
        core_modules = result.get('core_modules', [])
        if core_modules:
            lines.append("**核心模块**:")
            lines.append("")
            for module in core_modules:
                lines.append(f"- {module}")
            lines.append("")

        # 关键文件
        key_files = result.get('key_files', [])
        if key_files:
            lines.append("**关键文件**:")
            lines.append("")
            for file in key_files:
                lines.append(f"- `{file}`")
            lines.append("")

        # 影响范围
        impact_scope = result.get('impact_scope', '')
        if impact_scope:
            lines.append("**影响范围**:")
            lines.append("")
            lines.append(impact_scope)
            lines.append("")

        # 测试覆盖
        test_coverage = result.get('test_coverage', '')
        if test_coverage:
            lines.append("**测试覆盖建议**:")
            lines.append("")
            lines.append(test_coverage)
            lines.append("")

        # 提取的代码引用
        extracted_refs = result.get('extracted_references', {})
        if any(extracted_refs.values()):
            lines.append("**提取的代码引用**:")
            lines.append("")
            if extracted_refs.get('file_paths'):
                lines.append(f"- 文件路径: {len(extracted_refs['file_paths'])} 个")
            if extracted_refs.get('functions'):
                lines.append(f"- 函数: {len(extracted_refs['functions'])} 个")
            if extracted_refs.get('commits'):
                lines.append(f"- 提交: {len(extracted_refs['commits'])} 个")

        return '\n'.join(lines)

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
                # 显示评论原文
                if ca.get('comment_preview'):
                    lines.append("")
                    lines.append(f"```")
                    lines.append(ca['comment_preview'])
                    lines.append(f"```")
                    lines.append("")
                # 显示 LLM 分析
                lines.append("**分析**:")
                lines.append(ca['analysis'])
                lines.append("")

        return '\n'.join(lines)

    def _format_actions(self, result: Dict[str, Any]) -> str:
        """格式化行动建议结果 (Phase 2: 支持结构化信息)"""
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
                    # 检查是否是字典（结构化信息）
                    if isinstance(action, dict):
                        # Phase 2: 结构化行动建议
                        priority = action.get('priority', '')
                        title_text = action.get('title', action.get('action', ''))
                        location = action.get('location', '')
                        effort = action.get('effort', '')
                        steps = action.get('steps', [])
                        acceptance = action.get('acceptance_criteria', '')

                        # 格式化输出
                        if priority:
                            lines.append(f"{i}. **{priority}** {title_text}")
                        else:
                            lines.append(f"{i}. {title_text}")

                        if location:
                            lines.append(f"   - **位置**: {location}")
                        if effort:
                            lines.append(f"   - **工作量**: {effort}")
                        if steps:
                            lines.append(f"   - **步骤**:")
                            for step in steps:
                                lines.append(f"     - {step}")
                        if acceptance:
                            lines.append(f"   - **验收标准**: {acceptance}")
                    else:
                        # 简单字符串格式
                        lines.append(f"{i}. {action}")

                    lines.append("")

        return '\n'.join(lines)

    def _format_comments_compact(self, result: Dict[str, Any]) -> str:
        """格式化精简评论分析结果 (Phase 2: Task #10)"""
        lines = []

        if not result.get('has_comments'):
            return result.get('message', '无评论')

        comment_count = result.get('comment_count', 0)
        lines.append(f"共 {comment_count} 条评论")
        lines.append("")

        # 精简评论分析
        compact_analyses = result.get('compact_analysis', [])
        if compact_analyses:
            for ca in compact_analyses:
                index = ca.get('index', 0)
                role = ca.get('role', '未知')
                summary = ca.get('summary', '')
                key_point = ca.get('key_point', '')

                lines.append(f"**评论 #{index}**")
                lines.append(f"[{role}]")
                if summary:
                    lines.append(summary)
                if key_point:
                    lines.append(f"→ {key_point}")
                lines.append("")

        # 时间线视图
        timeline_view = result.get('timeline_view')
        if timeline_view:
            lines.append("### 时间线视图")
            lines.append("")

            # timeline_view 可能是字符串或字典列表
            if isinstance(timeline_view, str):
                # 如果是字符串，直接添加
                lines.append(timeline_view)
            elif isinstance(timeline_view, list):
                # 如果是列表，按阶段组织
                for stage in timeline_view:
                    if isinstance(stage, dict):
                        stage_name = stage.get('stage', '')
                        comment_indices = stage.get('comments', [])

                        if stage_name and comment_indices:
                            lines.append(f"**{stage_name}** (评论 #{', #'.join(map(str, comment_indices))})")

                            # 显示该阶段的评论摘要
                            for idx in comment_indices:
                                for ca in compact_analyses:
                                    if ca.get('index') == idx:
                                        summary = ca.get('summary', '')
                                        if summary:
                                            lines.append(f"- {summary}")
                                        break
                            lines.append("")
                    elif isinstance(stage, str):
                        # 如果列表元素是字符串，直接添加
                        lines.append(stage)

        return '\n'.join(lines)

    def _format_metadata(self, result: Dict[str, Any]) -> str:
        """格式化元数据提取结果 (Phase 2: Task #9)"""
        lines = []

        # 1. 影响范围
        impact = result.get('impact', {})
        if impact and any(impact.values()):
            lines.append("### 影响范围")
            lines.append("")
            if impact.get('affected_customers'):
                lines.append(f"**受影响客户**: {impact['affected_customers']}")
            if impact.get('affected_devices'):
                lines.append(f"**受影响设备数**: {impact['affected_devices']}")
            if impact.get('affected_products'):
                products = impact['affected_products']
                if isinstance(products, list) and products:
                    lines.append(f"**受影响产品**: {', '.join(products)}")
                elif isinstance(products, str) and products:
                    lines.append(f"**受影响产品**: {products}")
            if impact.get('severity'):
                lines.append(f"**影响等级**: {impact['severity']}")
            lines.append("")

        # 2. 时间线
        timeline = result.get('timeline', {})
        if timeline and any(timeline.values()):
            lines.append("### 时间线")
            lines.append("")
            if timeline.get('discovered'):
                lines.append(f"**问题发现时间**: {timeline['discovered']}")
            if timeline.get('fixed'):
                lines.append(f"**修复完成时间**: {timeline['fixed']}")
            if timeline.get('verified'):
                lines.append(f"**验证完成时间**: {timeline['verified']}")
            if timeline.get('duration'):
                lines.append(f"**总耗时**: {timeline['duration']}")

            # 关键里程碑
            milestones = timeline.get('milestones', [])
            if milestones:
                lines.append("")
                lines.append("**关键里程碑**:")
                for milestone in milestones:
                    lines.append(f"- {milestone}")
            lines.append("")

        # 3. 修复详情
        fix_details = result.get('fix_details', {})
        if fix_details and any(fix_details.values()):
            lines.append("### 修复详情")
            lines.append("")
            if fix_details.get('modified_files'):
                lines.append(f"**修改文件**: {fix_details['modified_files']}")
            if fix_details.get('commit_id'):
                lines.append(f"**Commit ID**: {fix_details['commit_id']}")
            if fix_details.get('code_changes'):
                lines.append(f"**代码变更**: {fix_details['code_changes']}")
            if fix_details.get('core_changes'):
                lines.append(f"**核心修改**: {fix_details['core_changes']}")
            if fix_details.get('code_review'):
                lines.append(f"**Code Review**: {fix_details['code_review']}")
            lines.append("")

        # 4. 测试信息
        test_info = result.get('test_info', {})
        if test_info and any(test_info.values()):
            lines.append("### 测试信息")
            lines.append("")
            if test_info.get('test_cases'):
                lines.append(f"**新增测试用例**: {test_info['test_cases']}")
            if test_info.get('coverage'):
                lines.append(f"**测试覆盖率**: {test_info['coverage']}")
            if test_info.get('automated'):
                lines.append(f"**自动化测试**: {test_info['automated']}")
            if test_info.get('regression'):
                lines.append(f"**回归测试**: {test_info['regression']}")
            if test_info.get('test_result'):
                lines.append(f"**测试结果**: {test_info['test_result']}")
            if test_info.get('stress_test'):
                lines.append(f"**压力测试**: {test_info['stress_test']}")
            lines.append("")

        # 5. 风险评估
        risk = result.get('risk_assessment', {})
        if risk and any(risk.values()):
            lines.append("### 风险评估")
            lines.append("")
            if risk.get('no_fix_consequence'):
                lines.append(f"**不修复后果**: {risk['no_fix_consequence']}")
            if risk.get('fix_risk'):
                lines.append(f"**修复风险**: {risk['fix_risk']}")
            if risk.get('upgrade_required'):
                lines.append(f"**是否需要升级**: {risk['upgrade_required']}")
            lines.append("")

        # 6. 成本分析
        cost = result.get('cost_analysis', {})
        if cost and any(cost.values()):
            lines.append("### 成本分析")
            lines.append("")
            if cost.get('fix_cost'):
                lines.append(f"**修复成本**: {cost['fix_cost']}")
            if cost.get('test_cost'):
                lines.append(f"**测试成本**: {cost['test_cost']}")
            if cost.get('no_fix_cost'):
                lines.append(f"**不修复成本**: {cost['no_fix_cost']}")
            if cost.get('roi'):
                lines.append(f"**ROI**: {cost['roi']}")
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
