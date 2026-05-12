"""
关键发现分析器 - 识别最重要的发现
"""

from typing import Dict, Any, List
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class KeyInsightsAnalyzer(BaseAnalyzer):
    """识别报告中 Top N 最重要的发现"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化关键发现分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config
        self.max_items = config.get('max_items', 5)
        self.max_tokens = config.get('max_tokens', 500)

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        识别关键发现

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含 'insights' 列表的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {'insights': []}

        # 构建 prompt
        prompt = self._build_prompt(report_data)

        # 调用 LLM
        try:
            context.increment_llm_calls()
            response = self.llm_client.generate(prompt, max_tokens=self.max_tokens)

            # 解析响应
            insights = self._parse_insights(response)

            return {
                'insights': insights,
                'success': True
            }

        except Exception as e:
            context.add_warning(f"关键发现分析失败: {str(e)}")
            return {
                'insights': [],
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
        jira = report_data.get('jira', {})

        new_issues = jira.get('new_issues', [])
        updated_issues = jira.get('updated_issues', [])
        fixed_issues = jira.get('fixed_issues', [])

        new_count = len(new_issues)
        updated_count = len(updated_issues)
        fixed_count = len(fixed_issues)

        # 格式化 issues
        new_issues_list = self._format_issues_list(new_issues, limit=10)
        updated_issues_list = self._format_issues_list(updated_issues, limit=10)
        fixed_issues_list = self._format_issues_list(fixed_issues, limit=5)

        prompt = f"""分析以下issues，识别Top {self.max_items}最重要的发现：

新建issues ({new_count}个):
{new_issues_list}

更新issues ({updated_count}个):
{updated_issues_list}

固定跟踪issues ({fixed_count}个):
{fixed_issues_list}

要求：
1. 每个发现包含：类型（进展/风险/异常）、描述、相关issue
2. 优先级排序：高优先级 > 功能完成 > bug修复 > 其他
3. 关注状态变化大的issues
4. 每个发现1-2句话
5. 输出格式（每行一个发现）：
   [类型] 描述 (相关issue: KEY-123)
6. 直接输出发现列表，不要输出思考过程"""

        return prompt

    def _format_issues_list(self, issues: List[Dict[str, Any]], limit: int = 10) -> str:
        """
        格式化 issues 列表

        Args:
            issues: Issue 列表
            limit: 最大显示数量

        Returns:
            格式化的字符串
        """
        if not issues:
            return "无"

        lines = []
        for issue in issues[:limit]:
            key = issue.get('key', 'N/A')
            title = issue.get('title', 'N/A')
            status = issue.get('status', 'N/A')
            priority = issue.get('priority', 'N/A')
            issue_type = issue.get('type', 'N/A')

            lines.append(f"- [{key}] {title}")
            lines.append(f"  状态: {status}, 优先级: {priority}, 类型: {issue_type}")

        if len(issues) > limit:
            lines.append(f"... 还有 {len(issues) - limit} 个issues")

        return '\n'.join(lines)

    def _parse_insights(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 响应为结构化的发现列表

        Args:
            response: LLM 响应文本

        Returns:
            发现列表
        """
        insights = []
        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 移除列表标记
            if line.startswith('-') or line.startswith('*'):
                line = line[1:].strip()
            elif line[0].isdigit() and '.' in line[:3]:
                # 移除 "1. " 这样的编号
                line = line.split('.', 1)[1].strip()

            # 解析格式: [类型] 描述 (相关issue: KEY-123)
            import re
            match = re.match(r'\[([^\]]+)\]\s*(.+?)(?:\s*\(相关issue:\s*([^)]+)\))?$', line)

            if match:
                insight_type = match.group(1).strip()
                description = match.group(2).strip()
                related_issue = match.group(3).strip() if match.group(3) else None

                insights.append({
                    'type': insight_type,
                    'description': description,
                    'related_issue': related_issue
                })
            elif line:
                # 如果格式不匹配，作为纯文本保存
                insights.append({
                    'type': '其他',
                    'description': line,
                    'related_issue': None
                })

        return insights[:self.max_items]

    def get_name(self) -> str:
        """获取分析器名称"""
        return "key_insights"
