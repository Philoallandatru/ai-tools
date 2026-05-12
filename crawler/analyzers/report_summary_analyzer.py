"""
报告摘要分析器 - 生成执行摘要
"""

from typing import Dict, Any
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class ReportSummaryAnalyzer(BaseAnalyzer):
    """生成报告的执行摘要（3-5句话）"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化摘要分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config
        self.max_tokens = config.get('max_tokens', 300)

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        生成报告执行摘要

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含 'summary' 字段的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {'summary': ''}

        # 构建 prompt
        prompt = self._build_prompt(report_data)

        # 调用 LLM
        try:
            context.increment_llm_calls()
            summary = self.llm_client.generate(prompt, max_tokens=self.max_tokens)
            summary = summary.strip()

            return {
                'summary': summary,
                'success': True
            }

        except Exception as e:
            context.add_warning(f"摘要生成失败: {str(e)}")
            return {
                'summary': '',
                'success': False,
                'error': str(e)
            }

    def _build_prompt(self, report_data: Dict[str, Any]) -> str:
        """
        构建 LLM prompt

        Args:
            report_data: 报告数据

        Returns:
            Prompt 字符串
        """
        report_type = report_data.get('type', '报告')
        start_date = report_data.get('start_date', 'N/A')
        end_date = report_data.get('end_date', 'N/A')

        jira = report_data.get('jira', {})
        total = jira.get('total', 0)
        new = jira.get('new', 0)
        updated = jira.get('updated', 0)
        by_status = jira.get('by_status', {})
        by_priority = jira.get('by_priority', {})

        # 获取关键 issues（优先级高的或新建的）
        all_issues = jira.get('all_issues', [])
        top_issues = self._get_top_issues(all_issues, limit=5)
        top_issues_summary = self._format_issues_summary(top_issues)

        prompt = f"""基于以下报告数据生成执行摘要（3-5句话）：

报告类型: {report_type}
时间范围: {start_date} 至 {end_date}

Jira统计:
- 总计: {total} 个issues
- 新建: {new} 个
- 更新: {updated} 个
- 按状态: {self._format_dict(by_status)}
- 按优先级: {self._format_dict(by_priority)}

关键issues:
{top_issues_summary}

要求：
1. 第一句话概括整体情况
2. 突出最重要的进展或变化
3. 如有异常情况（如大量高优先级未完成），需指出
4. 语言简洁专业，面向管理层
5. 直接输出摘要内容，不要输出思考过程"""

        return prompt

    def _get_top_issues(self, issues: list, limit: int = 5) -> list:
        """
        获取最重要的 issues

        Args:
            issues: Issue 列表
            limit: 返回数量

        Returns:
            Top N issues
        """
        # 优先级权重
        priority_weight = {
            'Highest': 5,
            'High': 4,
            'Medium': 3,
            'Low': 2,
            'Lowest': 1
        }

        # 按优先级排序
        sorted_issues = sorted(
            issues,
            key=lambda x: priority_weight.get(x.get('priority', 'Medium'), 3),
            reverse=True
        )

        return sorted_issues[:limit]

    def _format_issues_summary(self, issues: list) -> str:
        """
        格式化 issues 摘要

        Args:
            issues: Issue 列表

        Returns:
            格式化的字符串
        """
        if not issues:
            return "无"

        lines = []
        for issue in issues:
            key = issue.get('key', 'N/A')
            title = issue.get('title', 'N/A')
            status = issue.get('status', 'N/A')
            priority = issue.get('priority', 'N/A')
            lines.append(f"- [{key}] {title} (状态: {status}, 优先级: {priority})")

        return '\n'.join(lines)

    def _format_dict(self, d: dict) -> str:
        """
        格式化字典为字符串

        Args:
            d: 字典

        Returns:
            格式化的字符串
        """
        if not d:
            return "无"
        return ', '.join([f"{k}: {v}" for k, v in d.items()])

    def get_name(self) -> str:
        """获取分析器名称"""
        return "report_summary"
