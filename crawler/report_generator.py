"""
报告生成模块 - 自动生成周报和日报
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict


class ReportGenerator:
    """报告生成器 - 生成周报和日报"""

    def __init__(self, source_dir: str = './sources', config: Optional[Dict[str, Any]] = None):
        """
        初始化报告生成器

        Args:
            source_dir: 源文件目录
            config: 配置字典（可选）
        """
        self.source_dir = Path(source_dir)
        self.config = config or {}

        # 报告配置
        reports_config = self.config.get('reports', {})
        self.fixed_issues = reports_config.get('fixed_issues', [])
        self.max_issues_per_report = reports_config.get('max_issues_per_report', 100)
        self.group_by = reports_config.get('group_by', 'status')
        self.include_attachments = reports_config.get('include_attachments', True)

    def generate_report(
        self,
        report_type: str = 'weekly',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        生成报告

        Args:
            report_type: 报告类型 (daily/weekly/monthly)
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            报告数据字典
        """
        # 确定时间范围
        if not end_date:
            end_date = date.today()

        if not start_date:
            if report_type == 'daily':
                start_date = end_date
            elif report_type == 'weekly':
                start_date = end_date - timedelta(days=7)
            elif report_type == 'monthly':
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=7)

        # 收集数据
        jira_data = self._collect_jira_data(start_date, end_date)
        confluence_data = self._collect_confluence_data(start_date, end_date)

        # 生成报告
        report = {
            'type': report_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'generated_at': datetime.now().isoformat(),
            'jira': jira_data,
            'confluence': confluence_data,
            'summary': self._generate_summary(jira_data, confluence_data)
        }

        # 执行报告分析（如果启用）
        analysis_results = self._analyze_report(report)
        if analysis_results:
            report['analysis'] = analysis_results

        return report

    def _collect_jira_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        收集 Jira 数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Jira 数据字典
        """
        jira_pattern = re.compile(r'^[A-Z]+-\d+\.md$')
        time_range_issues = []
        fixed_issues = []
        fixed_issue_keys = set(self.fixed_issues)

        for md_file in self.source_dir.rglob('*.md'):
            if not jira_pattern.match(md_file.name):
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read(3000)

                # 提取元数据
                issue_key = md_file.stem
                update_match = re.search(r'>\s*更新时间:\s*(\d{4}-\d{2}-\d{2})', content)
                create_match = re.search(r'>\s*创建时间:\s*(\d{4}-\d{2}-\d{2})', content)
                status_match = re.search(r'-\s*\*\*状态\*\*:\s*([^\n]+)', content)
                priority_match = re.search(r'-\s*\*\*优先级\*\*:\s*([^\n]+)', content)
                type_match = re.search(r'-\s*\*\*类型\*\*:\s*([^\n]+)', content)
                title_match = re.search(r'^#\s+\[' + issue_key + r'\]\s+(.+)$', content, re.MULTILINE)
                assignee_match = re.search(r'-\s*\*\*经办人\*\*:\s*([^\n]+)', content)

                update_date = None
                create_date = None

                if update_match:
                    update_date = datetime.strptime(update_match.group(1), '%Y-%m-%d').date()
                if create_match:
                    create_date = datetime.strptime(create_match.group(1), '%Y-%m-%d').date()

                issue_data = {
                    'key': issue_key,
                    'title': title_match.group(1).strip() if title_match else 'N/A',
                    'status': status_match.group(1).strip() if status_match else 'N/A',
                    'priority': priority_match.group(1).strip() if priority_match else 'N/A',
                    'type': type_match.group(1).strip() if type_match else 'N/A',
                    'assignee': assignee_match.group(1).strip() if assignee_match else 'Unassigned',
                    'created_date': create_date.isoformat() if create_date else None,
                    'updated_date': update_date.isoformat() if update_date else None,
                    'is_new': False,
                    'is_updated': False
                }

                # 判断是否在时间范围内
                is_new = create_date and start_date <= create_date <= end_date
                is_updated = update_date and start_date <= update_date <= end_date

                if is_new or is_updated:
                    issue_data['is_new'] = is_new
                    issue_data['is_updated'] = is_updated
                    time_range_issues.append(issue_data)

                # 收集固定跟踪的issues
                if issue_key in fixed_issue_keys:
                    fixed_issues.append(issue_data)

            except Exception:
                continue

        # 合并所有issues（去重）
        all_issues_dict = {}
        for issue in time_range_issues:
            all_issues_dict[issue['key']] = issue
        for issue in fixed_issues:
            if issue['key'] not in all_issues_dict:
                all_issues_dict[issue['key']] = issue

        all_issues = list(all_issues_dict.values())

        # 按状态分组
        by_status = defaultdict(list)
        by_priority = defaultdict(list)
        by_type = defaultdict(list)
        by_assignee = defaultdict(list)
        new_issues = []
        updated_issues = []

        for issue in time_range_issues:
            by_status[issue['status']].append(issue)
            by_priority[issue['priority']].append(issue)
            by_type[issue['type']].append(issue)
            by_assignee[issue['assignee']].append(issue)
            if issue['is_new']:
                new_issues.append(issue)
            if issue['is_updated'] and not issue['is_new']:
                updated_issues.append(issue)

        return {
            'total': len(time_range_issues),
            'new': len(new_issues),
            'updated': len(updated_issues),
            'by_status': dict(by_status),
            'by_priority': dict(by_priority),
            'by_type': dict(by_type),
            'by_assignee': dict(by_assignee),
            'new_issues': new_issues,
            'updated_issues': updated_issues,
            'all_issues': all_issues,
            'time_range_issues': time_range_issues,
            'fixed_issues': fixed_issues
        }

    def _collect_confluence_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        收集 Confluence 数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Confluence 数据字典
        """
        confluence_dir = self.source_dir / 'confluence'
        if not confluence_dir.exists():
            return {'total': 0, 'new': 0, 'updated': 0, 'pages': []}

        pages = []

        for md_file in confluence_dir.rglob('*.md'):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read(2000)

                # 提取元数据
                update_match = re.search(r'>\s*更新时间:\s*(\d{4}-\d{2}-\d{2})', content)
                create_match = re.search(r'>\s*创建时间:\s*(\d{4}-\d{2}-\d{2})', content)
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)

                update_date = None
                create_date = None

                if update_match:
                    update_date = datetime.strptime(update_match.group(1), '%Y-%m-%d').date()
                if create_match:
                    create_date = datetime.strptime(create_match.group(1), '%Y-%m-%d').date()

                # 判断是否在时间范围内
                is_new = create_date and start_date <= create_date <= end_date
                is_updated = update_date and start_date <= update_date <= end_date

                if is_new or is_updated:
                    pages.append({
                        'title': title_match.group(1).strip() if title_match else md_file.stem,
                        'file': str(md_file.relative_to(self.source_dir)),
                        'created_date': create_date.isoformat() if create_date else None,
                        'updated_date': update_date.isoformat() if update_date else None,
                        'is_new': is_new,
                        'is_updated': is_updated
                    })

            except Exception:
                continue

        new_pages = [p for p in pages if p['is_new']]
        updated_pages = [p for p in pages if p['is_updated'] and not p['is_new']]

        return {
            'total': len(pages),
            'new': len(new_pages),
            'updated': len(updated_pages),
            'new_pages': new_pages,
            'updated_pages': updated_pages,
            'all_pages': pages
        }

    def _generate_summary(self, jira_data: Dict[str, Any], confluence_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成摘要信息

        Args:
            jira_data: Jira 数据
            confluence_data: Confluence 数据

        Returns:
            摘要字典
        """
        return {
            'total_items': jira_data['total'] + confluence_data['total'],
            'total_new': jira_data['new'] + confluence_data['new'],
            'total_updated': jira_data['updated'] + confluence_data['updated'],
            'jira_summary': {
                'total': jira_data['total'],
                'new': jira_data['new'],
                'updated': jira_data['updated'],
                'by_status': {k: len(v) for k, v in jira_data['by_status'].items()},
                'by_priority': {k: len(v) for k, v in jira_data['by_priority'].items()}
            },
            'confluence_summary': {
                'total': confluence_data['total'],
                'new': confluence_data['new'],
                'updated': confluence_data['updated']
            }
        }

    def _analyze_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行报告分析

        Args:
            report: 报告数据

        Returns:
            分析结果字典
        """
        # 检查是否启用报告分析
        report_analysis_config = self.config.get('report_analysis', {})
        if not report_analysis_config.get('enabled', True):
            return {}

        try:
            from crawler.report_analyzer import ReportAnalyzer
            from crawler.analyzers.report_summary_analyzer import ReportSummaryAnalyzer
            from crawler.analyzers.key_insights_analyzer import KeyInsightsAnalyzer
            from crawler.analyzers.risk_analyzer import RiskAnalyzer
            from crawler.analyzers.project_health_analyzer import ProjectHealthAnalyzer
            from crawler.analyzers.project_status_analyzer import ProjectStatusAnalyzer
            from crawler.analyzers.team_collaboration_analyzer import TeamCollaborationAnalyzer

            # 创建报告分析器
            analyzer = ReportAnalyzer(config=self.config)

            # 注册分析器
            analyzers_config = report_analysis_config.get('analyzers', {})

            # 项目健康度分析器（优先执行，其他分析器可能依赖其结果）
            if analyzers_config.get('project_health', {}).get('enabled', True):
                health_analyzer = ProjectHealthAnalyzer(
                    analyzer.llm_client,
                    analyzers_config.get('project_health', {})
                )
                analyzer.register_analyzer(health_analyzer)

            # 摘要分析器
            if analyzers_config.get('summary', {}).get('enabled', True):
                summary_analyzer = ReportSummaryAnalyzer(
                    analyzer.llm_client,
                    analyzers_config.get('summary', {})
                )
                analyzer.register_analyzer(summary_analyzer)

            # 关键发现分析器
            if analyzers_config.get('insights', {}).get('enabled', True):
                insights_analyzer = KeyInsightsAnalyzer(
                    analyzer.llm_client,
                    analyzers_config.get('insights', {})
                )
                analyzer.register_analyzer(insights_analyzer)

            # 风险分析器
            if analyzers_config.get('risks', {}).get('enabled', True):
                risk_analyzer = RiskAnalyzer(
                    analyzer.llm_client,
                    analyzers_config.get('risks', {})
                )
                analyzer.register_analyzer(risk_analyzer)

            # 团队协作分析器
            if analyzers_config.get('team_collaboration', {}).get('enabled', True):
                collaboration_analyzer = TeamCollaborationAnalyzer(
                    analyzer.llm_client,
                    analyzers_config.get('team_collaboration', {})
                )
                analyzer.register_analyzer(collaboration_analyzer)

            # 项目状态分析器（依赖健康度分析结果，最后执行）
            if analyzers_config.get('project_status', {}).get('enabled', True):
                status_analyzer = ProjectStatusAnalyzer(
                    analyzer.llm_client,
                    analyzers_config.get('project_status', {})
                )
                analyzer.register_analyzer(status_analyzer)

            # 执行分析
            print("   🔍 开始报告分析...")
            results = analyzer.analyze(report)
            print("   ✓ 报告分析完成")

            return results

        except Exception as e:
            print(f"   ⚠ 报告分析失败: {str(e)}")
            return {}

    def format_report_markdown(self, report: Dict[str, Any]) -> str:
        """
        格式化报告为 Markdown

        Args:
            report: 报告数据

        Returns:
            Markdown 格式的报告
        """
        lines = []

        # 标题
        report_type_name = {
            'daily': '日报',
            'weekly': '周报',
            'monthly': '月报'
        }.get(report['type'], '报告')

        lines.append(f"# {report_type_name}")
        lines.append("")
        lines.append(f"**时间范围**: {report['start_date']} 至 {report['end_date']}")
        lines.append(f"**生成时间**: {report['generated_at']}")
        lines.append("")

        # 分析结果部分（如果有）
        analysis = report.get('analysis', {})
        if analysis:
            # 项目健康度（优先显示）
            health_result = analysis.get('project_health', {})
            if health_result.get('success'):
                lines.append("## 🏥 项目健康度")
                lines.append("")

                total_score = health_result.get('total_score', 0)
                health_level = health_result.get('health_level', '未知')
                emoji = health_result.get('emoji', '⚪')

                lines.append(f"**总体评分**: {emoji} {total_score}/100 ({health_level})")
                lines.append("")

                # 维度评分
                dimension_scores = health_result.get('dimension_scores', {})
                if dimension_scores:
                    lines.append("### 维度评分")
                    lines.append("")

                    for dimension, data in dimension_scores.items():
                        score = data.get('score', 0)
                        max_score = data.get('max_score', 0)

                        # 判断状态
                        ratio = score / max_score if max_score > 0 else 0
                        if ratio >= 0.8:
                            status_emoji = "✅"
                        elif ratio >= 0.6:
                            status_emoji = "⚠️"
                        else:
                            status_emoji = "❌"

                        dimension_name = {
                            'progress': '进度健康度',
                            'quality': '质量健康度',
                            'resource': '资源健康度',
                            'risk': '风险健康度'
                        }.get(dimension, dimension)

                        lines.append(f"- **{dimension_name}**: {score}/{max_score} {status_emoji}")

                    lines.append("")

            # 项目状态评估
            status_result = analysis.get('project_status', {})
            if status_result.get('success'):
                lines.append("## 🎯 项目状态评估")
                lines.append("")

                # 状态描述
                status_desc = status_result.get('status_description', '')
                if status_desc:
                    lines.append("### 当前状态")
                    lines.append("")
                    lines.append(status_desc)
                    lines.append("")

                # 主要问题
                problems = status_result.get('main_problems', [])
                if problems:
                    lines.append("### 主要问题")
                    lines.append("")
                    for i, problem in enumerate(problems, 1):
                        lines.append(f"{i}. {problem}")
                    lines.append("")

                # 行动建议
                recommendations = status_result.get('action_recommendations', [])
                if recommendations:
                    lines.append("### 行动建议")
                    lines.append("")

                    # 按优先级分组
                    high_priority = [r for r in recommendations if r.get('priority') == 'high']
                    medium_priority = [r for r in recommendations if r.get('priority') == 'medium']
                    low_priority = [r for r in recommendations if r.get('priority') == 'low']

                    if high_priority:
                        lines.append("#### 🔴 高优先级")
                        lines.append("")
                        for i, rec in enumerate(high_priority, 1):
                            lines.append(f"{i}. {rec.get('text', '')}")
                        lines.append("")

                    if medium_priority:
                        lines.append("#### 🟡 中优先级")
                        lines.append("")
                        for i, rec in enumerate(medium_priority, 1):
                            lines.append(f"{i}. {rec.get('text', '')}")
                        lines.append("")

                    if low_priority:
                        lines.append("#### 🟢 低优先级")
                        lines.append("")
                        for i, rec in enumerate(low_priority, 1):
                            lines.append(f"{i}. {rec.get('text', '')}")
                        lines.append("")

            # 团队协作分析
            collaboration_result = analysis.get('team_collaboration', {})
            if collaboration_result.get('success'):
                lines.append("## 👥 团队协作分析")
                lines.append("")

                # 整体状态
                summary = collaboration_result.get('summary', {})
                if summary:
                    status_text = summary.get('status_text', '未知')
                    status_emoji = {
                        'excellent': '🟢',
                        'good': '🟢',
                        'fair': '🟡',
                        'poor': '🔴'
                    }.get(summary.get('overall_status'), '⚪')

                    lines.append(f"**整体状态**: {status_emoji} {status_text}")
                    lines.append("")

                    # 关键指标
                    metrics = summary.get('metrics', {})
                    if metrics:
                        gini = metrics.get('gini_coefficient', 0)
                        lines.append(f"- **负载均衡度**: {gini:.3f} (基尼系数，越小越均衡)")
                        lines.append(f"- **瓶颈成员数**: {metrics.get('bottleneck_count', 0)}")
                        lines.append(f"- **协作较少成员数**: {metrics.get('isolated_count', 0)}")
                        lines.append("")

                # 负载分布
                workload = collaboration_result.get('workload_distribution', {})
                if workload:
                    lines.append("### 负载分布")
                    lines.append("")

                    stats = workload.get('statistics', {})
                    if stats:
                        lines.append(f"- **团队规模**: {stats.get('total_members', 0)} 人")
                        lines.append(f"- **平均负载**: {stats.get('mean', 0):.1f} 个任务/人")
                        lines.append(f"- **标准差**: {stats.get('std_dev', 0):.1f}")
                        lines.append("")

                    # 负载过重成员
                    overloaded = workload.get('overloaded', [])
                    if overloaded:
                        lines.append("#### 🔴 负载过重")
                        lines.append("")
                        for member in overloaded[:5]:
                            name = member.get('name')
                            workload_count = member.get('workload')
                            percentage = member.get('percentage')
                            lines.append(f"- **{name}**: {workload_count} 个任务 (超出平均 {percentage}%)")
                        lines.append("")

                    # 负载较轻成员
                    underloaded = workload.get('underloaded', [])
                    if underloaded:
                        lines.append("#### 🟢 负载较轻")
                        lines.append("")
                        for member in underloaded[:5]:
                            name = member.get('name')
                            workload_count = member.get('workload')
                            percentage = member.get('percentage')
                            lines.append(f"- **{name}**: {workload_count} 个任务 (低于平均 {percentage}%)")
                        lines.append("")

                # 瓶颈识别
                bottlenecks = collaboration_result.get('bottlenecks', {})
                if bottlenecks and bottlenecks.get('has_bottlenecks'):
                    lines.append("### ⚠️ 瓶颈成员")
                    lines.append("")

                    bottleneck_members = bottlenecks.get('bottleneck_members', [])
                    for member in bottleneck_members[:5]:
                        name = member.get('name')
                        reasons = member.get('reasons', [])
                        lines.append(f"- **{name}**: {', '.join(reasons)}")
                    lines.append("")

                # 协作网络
                collaboration_network = collaboration_result.get('collaboration_network', {})
                if collaboration_network:
                    # 核心成员
                    core_members = collaboration_network.get('core_members', [])
                    if core_members:
                        lines.append("### 🌟 核心成员")
                        lines.append("")
                        for member in core_members[:5]:
                            name = member.get('name')
                            connections = member.get('connections')
                            lines.append(f"- **{name}**: 与 {connections} 名成员协作")
                        lines.append("")

                    # 协作较少成员
                    isolated = collaboration_network.get('isolated_members', [])
                    if isolated:
                        lines.append("### 💡 协作较少成员")
                        lines.append("")
                        for member in isolated[:5]:
                            name = member.get('name')
                            connections = member.get('connections')
                            lines.append(f"- **{name}**: 仅与 {connections} 名成员协作")
                        lines.append("")

                # 改进建议
                recommendations = summary.get('recommendations', [])
                if recommendations:
                    lines.append("### 改进建议")
                    lines.append("")
                    for i, rec in enumerate(recommendations, 1):
                        lines.append(f"{i}. {rec}")
                    lines.append("")

            # 执行摘要
            summary_result = analysis.get('report_summary', {})
            if summary_result.get('success') and summary_result.get('summary'):
                lines.append("## 📋 执行摘要")
                lines.append("")
                lines.append(summary_result['summary'])
                lines.append("")

            # 关键发现
            insights_result = analysis.get('key_insights', {})
            if insights_result.get('success') and insights_result.get('insights'):
                lines.append("## 🔍 关键发现")
                lines.append("")
                for i, insight in enumerate(insights_result['insights'], 1):
                    insight_type = insight.get('type', '其他')
                    description = insight.get('description', '')
                    related_issue = insight.get('related_issue')

                    if related_issue:
                        lines.append(f"{i}. **[{insight_type}]** {description} (相关issue: {related_issue})")
                    else:
                        lines.append(f"{i}. **[{insight_type}]** {description}")
                lines.append("")

            # 潜在风险
            risks_result = analysis.get('risk_analyzer', {})
            if risks_result.get('success') and risks_result.get('risks'):
                lines.append("## ⚠️ 潜在风险")
                lines.append("")

                risks = risks_result['risks']

                # 进度风险
                if risks.get('progress'):
                    progress_risk = risks['progress']
                    level = progress_risk.get('level', '未知')
                    lines.append(f"### 进度风险 ({level})")
                    lines.append("")
                    if progress_risk.get('description'):
                        lines.append(f"- **描述**: {progress_risk['description']}")
                    if progress_risk.get('impact'):
                        lines.append(f"- **影响**: {progress_risk['impact']}")
                    if progress_risk.get('suggestion'):
                        lines.append(f"- **建议**: {progress_risk['suggestion']}")
                    lines.append("")

                # 优先级风险
                if risks.get('priority'):
                    priority_risk = risks['priority']
                    level = priority_risk.get('level', '未知')
                    lines.append(f"### 优先级风险 ({level})")
                    lines.append("")
                    if priority_risk.get('description'):
                        lines.append(f"- **描述**: {priority_risk['description']}")
                    if priority_risk.get('impact'):
                        lines.append(f"- **影响**: {priority_risk['impact']}")
                    if priority_risk.get('suggestion'):
                        lines.append(f"- **建议**: {priority_risk['suggestion']}")
                    lines.append("")

                # 资源风险
                if risks.get('resource'):
                    resource_risk = risks['resource']
                    level = resource_risk.get('level', '未知')
                    lines.append(f"### 资源风险 ({level})")
                    lines.append("")
                    if resource_risk.get('description'):
                        lines.append(f"- **描述**: {resource_risk['description']}")
                    if resource_risk.get('impact'):
                        lines.append(f"- **影响**: {resource_risk['impact']}")
                    if resource_risk.get('suggestion'):
                        lines.append(f"- **建议**: {resource_risk['suggestion']}")
                    lines.append("")

        # 摘要
        summary = report['summary']
        lines.append("## 📊 总体概况")
        lines.append("")
        lines.append(f"- **总活动数**: {summary['total_items']} 项")
        lines.append(f"- **新增**: {summary['total_new']} 项")
        lines.append(f"- **更新**: {summary['total_updated']} 项")
        lines.append("")

        # Jira 部分 - 时间范围内的活动
        jira = report['jira']
        lines.append("## 🎯 时间范围内的活动")
        lines.append("")
        lines.append("### Jira Issues")
        lines.append("")
        lines.append(f"- **总计**: {jira['total']} 个 issues")
        lines.append(f"- **新增**: {jira['new']} 个")
        lines.append(f"- **更新**: {jira['updated']} 个")
        lines.append("")

        # 按状态统计
        if jira['by_status']:
            lines.append("#### 按状态分布")
            lines.append("")
            for status, issues in sorted(jira['by_status'].items(), key=lambda x: len(x[1]), reverse=True):
                lines.append(f"- **{status}**: {len(issues)} 个")
            lines.append("")

        # 按优先级统计
        if jira['by_priority']:
            lines.append("#### 按优先级分布")
            lines.append("")
            priority_order = {'Highest': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            sorted_priorities = sorted(
                jira['by_priority'].items(),
                key=lambda x: priority_order.get(x[0], 99)
            )
            for priority, issues in sorted_priorities:
                lines.append(f"- **{priority}**: {len(issues)} 个")
            lines.append("")

        # 根据配置的 group_by 显示详细分组
        if self.group_by and jira['time_range_issues']:
            lines.append(f"#### 按{self._get_group_name(self.group_by)}分组")
            lines.append("")
            self._append_grouped_issues(lines, jira, self.group_by)
            lines.append("")

        # 新增 issues
        if jira['new_issues']:
            lines.append("#### 🆕 新增 Issues")
            lines.append("")
            display_count = min(len(jira['new_issues']), self.max_issues_per_report)
            for issue in jira['new_issues'][:display_count]:
                lines.append(f"- **[{issue['key']}]** {issue['title']}")
                lines.append(f"  - 状态: {issue['status']} | 优先级: {issue['priority']} | 类型: {issue['type']}")
                lines.append(f"  - 经办人: {issue['assignee']}")
            if len(jira['new_issues']) > display_count:
                lines.append(f"  - ... 还有 {len(jira['new_issues']) - display_count} 个新增")
            lines.append("")

        # 更新的 issues
        if jira['updated_issues']:
            lines.append("#### 🔄 更新的 Issues")
            lines.append("")
            display_count = min(len(jira['updated_issues']), self.max_issues_per_report)
            for issue in jira['updated_issues'][:display_count]:
                lines.append(f"- **[{issue['key']}]** {issue['title']}")
                lines.append(f"  - 状态: {issue['status']} | 优先级: {issue['priority']}")
            if len(jira['updated_issues']) > display_count:
                lines.append(f"  - ... 还有 {len(jira['updated_issues']) - display_count} 个更新")
            lines.append("")

        # Confluence 部分
        confluence = report['confluence']
        if confluence['total'] > 0:
            lines.append("### 📝 Confluence 页面")
            lines.append("")
            lines.append(f"- **总计**: {confluence['total']} 个页面")
            lines.append(f"- **新增**: {confluence['new']} 个")
            lines.append(f"- **更新**: {confluence['updated']} 个")
            lines.append("")

            # 新增页面
            if confluence['new_pages']:
                lines.append("#### 🆕 新增页面")
                lines.append("")
                for page in confluence['new_pages']:
                    lines.append(f"- {page['title']}")
                lines.append("")

            # 更新的页面
            if confluence['updated_pages']:
                lines.append("#### 🔄 更新的页面")
                lines.append("")
                display_count = min(len(confluence['updated_pages']), self.max_issues_per_report)
                for page in confluence['updated_pages'][:display_count]:
                    lines.append(f"- {page['title']}")
                if len(confluence['updated_pages']) > display_count:
                    lines.append(f"  - ... 还有 {len(confluence['updated_pages']) - display_count} 个更新")
                lines.append("")

        # 固定跟踪的Issues部分
        if jira.get('fixed_issues'):
            lines.append("## 📌 固定跟踪的 Issues")
            lines.append("")
            lines.append(f"**总计**: {len(jira['fixed_issues'])} 个重点关注的 issues")
            lines.append("")

            for issue in jira['fixed_issues']:
                lines.append(f"### [{issue['key']}] {issue['title']}")
                lines.append("")
                lines.append(f"- **状态**: {issue['status']}")
                lines.append(f"- **优先级**: {issue['priority']}")
                lines.append(f"- **类型**: {issue['type']}")
                lines.append(f"- **经办人**: {issue['assignee']}")
                if issue['created_date']:
                    lines.append(f"- **创建时间**: {issue['created_date']}")
                if issue['updated_date']:
                    lines.append(f"- **最后更新**: {issue['updated_date']}")
                lines.append("")

        # 页脚
        lines.append("---")
        lines.append("")
        lines.append("*本报告由 AI Tools 自动生成*")

        return '\n'.join(lines)

    def _get_group_name(self, group_by: str) -> str:
        """获取分组名称"""
        group_names = {
            'status': '状态',
            'priority': '优先级',
            'assignee': '经办人',
            'type': '类型'
        }
        return group_names.get(group_by, group_by)

    def _append_grouped_issues(self, lines: List[str], jira: Dict[str, Any], group_by: str) -> None:
        """
        按指定维度分组显示 issues

        Args:
            lines: 输出行列表
            jira: Jira 数据
            group_by: 分组维度 (status/priority/assignee/type)
        """
        group_key = f'by_{group_by}'
        if group_key not in jira:
            return

        grouped_data = jira[group_key]
        if not grouped_data:
            return

        # 排序规则
        if group_by == 'priority':
            priority_order = {'Highest': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            sorted_groups = sorted(grouped_data.items(), key=lambda x: priority_order.get(x[0], 99))
        else:
            # 按 issue 数量降序排序
            sorted_groups = sorted(grouped_data.items(), key=lambda x: len(x[1]), reverse=True)

        for group_name, issues in sorted_groups:
            lines.append(f"##### {group_name} ({len(issues)} 个)")
            lines.append("")

            display_count = min(len(issues), 5)  # 每组最多显示 5 个
            for issue in issues[:display_count]:
                lines.append(f"- **[{issue['key']}]** {issue['title']}")
                # 显示其他维度信息
                info_parts = []
                if group_by != 'status':
                    info_parts.append(f"状态: {issue['status']}")
                if group_by != 'priority':
                    info_parts.append(f"优先级: {issue['priority']}")
                if group_by != 'assignee':
                    info_parts.append(f"经办人: {issue['assignee']}")
                if group_by != 'type':
                    info_parts.append(f"类型: {issue['type']}")

                if info_parts:
                    lines.append(f"  - {' | '.join(info_parts)}")

            if len(issues) > display_count:
                lines.append(f"  - ... 还有 {len(issues) - display_count} 个")
            lines.append("")

