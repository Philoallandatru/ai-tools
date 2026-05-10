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

    def __init__(self, source_dir: str = './sources'):
        """
        初始化报告生成器

        Args:
            source_dir: 源文件目录
        """
        self.source_dir = Path(source_dir)

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
        issues = []

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

                # 判断是否在时间范围内
                is_new = create_date and start_date <= create_date <= end_date
                is_updated = update_date and start_date <= update_date <= end_date

                if is_new or is_updated:
                    issues.append({
                        'key': issue_key,
                        'title': title_match.group(1).strip() if title_match else 'N/A',
                        'status': status_match.group(1).strip() if status_match else 'N/A',
                        'priority': priority_match.group(1).strip() if priority_match else 'N/A',
                        'type': type_match.group(1).strip() if type_match else 'N/A',
                        'assignee': assignee_match.group(1).strip() if assignee_match else 'Unassigned',
                        'created_date': create_date.isoformat() if create_date else None,
                        'updated_date': update_date.isoformat() if update_date else None,
                        'is_new': is_new,
                        'is_updated': is_updated
                    })

            except Exception:
                continue

        # 按状态分组
        by_status = defaultdict(list)
        by_priority = defaultdict(list)
        by_type = defaultdict(list)
        new_issues = []
        updated_issues = []

        for issue in issues:
            by_status[issue['status']].append(issue)
            by_priority[issue['priority']].append(issue)
            by_type[issue['type']].append(issue)
            if issue['is_new']:
                new_issues.append(issue)
            if issue['is_updated'] and not issue['is_new']:
                updated_issues.append(issue)

        return {
            'total': len(issues),
            'new': len(new_issues),
            'updated': len(updated_issues),
            'by_status': dict(by_status),
            'by_priority': dict(by_priority),
            'by_type': dict(by_type),
            'new_issues': new_issues,
            'updated_issues': updated_issues,
            'all_issues': issues
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

        # 摘要
        summary = report['summary']
        lines.append("## 📊 总体概况")
        lines.append("")
        lines.append(f"- **总活动数**: {summary['total_items']} 项")
        lines.append(f"- **新增**: {summary['total_new']} 项")
        lines.append(f"- **更新**: {summary['total_updated']} 项")
        lines.append("")

        # Jira 部分
        jira = report['jira']
        lines.append("## 🎯 Jira Issues")
        lines.append("")
        lines.append(f"- **总计**: {jira['total']} 个 issues")
        lines.append(f"- **新增**: {jira['new']} 个")
        lines.append(f"- **更新**: {jira['updated']} 个")
        lines.append("")

        # 按状态统计
        if jira['by_status']:
            lines.append("### 按状态分布")
            lines.append("")
            for status, issues in sorted(jira['by_status'].items(), key=lambda x: len(x[1]), reverse=True):
                lines.append(f"- **{status}**: {len(issues)} 个")
            lines.append("")

        # 按优先级统计
        if jira['by_priority']:
            lines.append("### 按优先级分布")
            lines.append("")
            priority_order = {'Highest': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            sorted_priorities = sorted(
                jira['by_priority'].items(),
                key=lambda x: priority_order.get(x[0], 99)
            )
            for priority, issues in sorted_priorities:
                lines.append(f"- **{priority}**: {len(issues)} 个")
            lines.append("")

        # 新增 issues
        if jira['new_issues']:
            lines.append("### 🆕 新增 Issues")
            lines.append("")
            for issue in jira['new_issues']:
                lines.append(f"- **[{issue['key']}]** {issue['title']}")
                lines.append(f"  - 状态: {issue['status']} | 优先级: {issue['priority']} | 类型: {issue['type']}")
                lines.append(f"  - 经办人: {issue['assignee']}")
            lines.append("")

        # 更新的 issues
        if jira['updated_issues']:
            lines.append("### 🔄 更新的 Issues")
            lines.append("")
            for issue in jira['updated_issues'][:10]:  # 最多显示 10 个
                lines.append(f"- **[{issue['key']}]** {issue['title']}")
                lines.append(f"  - 状态: {issue['status']} | 优先级: {issue['priority']}")
            if len(jira['updated_issues']) > 10:
                lines.append(f"  - ... 还有 {len(jira['updated_issues']) - 10} 个更新")
            lines.append("")

        # Confluence 部分
        confluence = report['confluence']
        if confluence['total'] > 0:
            lines.append("## 📝 Confluence 页面")
            lines.append("")
            lines.append(f"- **总计**: {confluence['total']} 个页面")
            lines.append(f"- **新增**: {confluence['new']} 个")
            lines.append(f"- **更新**: {confluence['updated']} 个")
            lines.append("")

            # 新增页面
            if confluence['new_pages']:
                lines.append("### 🆕 新增页面")
                lines.append("")
                for page in confluence['new_pages']:
                    lines.append(f"- {page['title']}")
                lines.append("")

            # 更新的页面
            if confluence['updated_pages']:
                lines.append("### 🔄 更新的页面")
                lines.append("")
                for page in confluence['updated_pages'][:10]:
                    lines.append(f"- {page['title']}")
                if len(confluence['updated_pages']) > 10:
                    lines.append(f"  - ... 还有 {len(confluence['updated_pages']) - 10} 个更新")
                lines.append("")

        # 页脚
        lines.append("---")
        lines.append("")
        lines.append("*本报告由 AI Tools 自动生成*")

        return '\n'.join(lines)
