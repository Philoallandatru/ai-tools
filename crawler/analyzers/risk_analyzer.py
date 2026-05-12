"""
风险分析器 - 评估潜在风险
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class RiskAnalyzer(BaseAnalyzer):
    """评估报告中的潜在风险（3个核心维度）"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化风险分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config
        self.max_tokens = config.get('max_tokens', 600)

        # 阈值配置
        thresholds = config.get('thresholds', {})
        self.stalled_days = thresholds.get('stalled_days', 7)
        self.overload_issues = thresholds.get('overload_issues', 5)

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        评估风险

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含 'risks' 字典的结果
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {'risks': {}}

        # 预处理：识别风险数据
        risk_data = self._identify_risks(report_data)

        # 构建 prompt
        prompt = self._build_prompt(report_data, risk_data)

        # 调用 LLM
        try:
            context.increment_llm_calls()
            response = self.llm_client.generate(prompt, max_tokens=self.max_tokens)

            # 解析响应
            risks = self._parse_risks(response)

            return {
                'risks': risks,
                'risk_data': risk_data,  # 保留原始数据供调试
                'success': True
            }

        except Exception as e:
            context.add_warning(f"风险分析失败: {str(e)}")
            return {
                'risks': {},
                'success': False,
                'error': str(e)
            }

    def _identify_risks(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理：识别风险相关数据

        Args:
            report_data: 报告数据

        Returns:
            风险数据字典
        """
        jira = report_data.get('jira', {})
        all_issues = jira.get('all_issues', [])
        by_assignee = jira.get('by_assignee', {})

        # 1. 进度风险：识别停滞的 issues
        stalled_issues = self._find_stalled_issues(all_issues)

        # 2. 优先级风险：识别高优先级未完成的 issues
        high_priority_issues = self._find_high_priority_incomplete(all_issues)

        # 3. 资源风险：识别负载过重的成员
        overloaded_members = self._find_overloaded_members(by_assignee)

        return {
            'stalled_issues': stalled_issues,
            'high_priority_issues': high_priority_issues,
            'overloaded_members': overloaded_members
        }

    def _find_stalled_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        查找停滞的 issues（>N天处于 In Progress）

        Args:
            issues: Issue 列表

        Returns:
            停滞的 issues
        """
        stalled = []
        cutoff_date = datetime.now() - timedelta(days=self.stalled_days)

        for issue in issues:
            status = issue.get('status', '')
            if 'progress' in status.lower() or 'doing' in status.lower():
                # 检查更新时间
                updated = issue.get('updated', '')
                if updated:
                    try:
                        # 尝试解析日期
                        updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        if updated_date < cutoff_date:
                            stalled.append(issue)
                    except:
                        # 如果解析失败，跳过
                        pass

        return stalled

    def _find_high_priority_incomplete(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        查找高优先级但未完成的 issues

        Args:
            issues: Issue 列表

        Returns:
            高优先级未完成的 issues
        """
        high_priority = []

        for issue in issues:
            priority = issue.get('priority', '')
            status = issue.get('status', '')

            # 高优先级且未完成
            if priority in ['Highest', 'High']:
                if status not in ['Done', 'Closed', 'Resolved', '已完成', '已关闭']:
                    high_priority.append(issue)

        return high_priority

    def _find_overloaded_members(self, by_assignee: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        查找负载过重的成员

        Args:
            by_assignee: 按负责人统计的字典 (可能是 {assignee: count} 或 {assignee: [issues]})

        Returns:
            负载过重的成员列表
        """
        overloaded = []

        for assignee, value in by_assignee.items():
            # 处理两种数据格式
            if isinstance(value, list):
                count = len(value)
            else:
                count = value

            if count >= self.overload_issues:
                overloaded.append({
                    'assignee': assignee,
                    'issue_count': count
                })

        # 按 issue 数量降序排序
        overloaded.sort(key=lambda x: x['issue_count'], reverse=True)

        return overloaded

    def _build_prompt(self, report_data: Dict[str, Any], risk_data: Dict[str, Any]) -> str:
        """
        构建 LLM prompt

        Args:
            report_data: 报告数据
            risk_data: 风险数据

        Returns:
            Prompt 字符串
        """
        jira = report_data.get('jira', {})
        by_status = jira.get('by_status', {})
        by_priority = jira.get('by_priority', {})

        # 格式化风险数据
        stalled_summary = self._format_stalled_issues(risk_data['stalled_issues'])
        high_priority_summary = self._format_high_priority_issues(risk_data['high_priority_issues'])
        overloaded_summary = self._format_overloaded_members(risk_data['overloaded_members'])

        prompt = f"""评估以下报告的潜在风险：

按状态分布: {self._format_dict(by_status)}
按优先级分布: {self._format_dict(by_priority)}

识别到的风险数据：

1. 停滞issues（>{self.stalled_days}天处于In Progress）:
{stalled_summary}

2. 高优先级未完成issues:
{high_priority_summary}

3. 负载过重的成员（≥{self.overload_issues}个issues）:
{overloaded_summary}

请从以下3个维度评估风险：

1. 进度风险
   - 基于停滞issues评估
   - 评估影响和可能原因

2. 优先级风险
   - 基于高优先级未完成issues评估
   - 评估紧急程度

3. 资源风险
   - 基于负载过重的成员评估
   - 评估资源分配问题

每个风险输出格式：
### 风险维度名称 (风险等级)
- 描述: 1-2句话描述风险
- 影响: 具体影响
- 建议: 缓解措施

风险等级: 高/中/低
直接输出风险评估，不要输出思考过程"""

        return prompt

    def _format_stalled_issues(self, issues: List[Dict[str, Any]]) -> str:
        """格式化停滞 issues"""
        if not issues:
            return "无"

        lines = []
        for issue in issues[:5]:  # 最多显示5个
            key = issue.get('key', 'N/A')
            title = issue.get('title', 'N/A')
            updated = issue.get('updated', 'N/A')
            lines.append(f"- [{key}] {title} (最后更新: {updated})")

        if len(issues) > 5:
            lines.append(f"... 还有 {len(issues) - 5} 个停滞issues")

        return '\n'.join(lines)

    def _format_high_priority_issues(self, issues: List[Dict[str, Any]]) -> str:
        """格式化高优先级 issues"""
        if not issues:
            return "无"

        lines = []
        for issue in issues[:5]:
            key = issue.get('key', 'N/A')
            title = issue.get('title', 'N/A')
            priority = issue.get('priority', 'N/A')
            status = issue.get('status', 'N/A')
            lines.append(f"- [{key}] {title} (优先级: {priority}, 状态: {status})")

        if len(issues) > 5:
            lines.append(f"... 还有 {len(issues) - 5} 个高优先级issues")

        return '\n'.join(lines)

    def _format_overloaded_members(self, members: List[Dict[str, Any]]) -> str:
        """格式化负载过重的成员"""
        if not members:
            return "无"

        lines = []
        for member in members[:5]:
            assignee = member['assignee']
            count = member['issue_count']
            lines.append(f"- {assignee}: {count} 个issues")

        return '\n'.join(lines)

    def _format_dict(self, d: dict) -> str:
        """格式化字典"""
        if not d:
            return "无"
        return ', '.join([f"{k}: {v}" for k, v in d.items()])

    def _parse_risks(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应为结构化的风险字典

        Args:
            response: LLM 响应文本

        Returns:
            风险字典，包含 progress, priority, resource 三个维度
        """
        risks = {
            'progress': {},
            'priority': {},
            'resource': {}
        }

        # 按 ### 分割各个风险维度
        import re
        sections = re.split(r'###\s+', response)

        for section in sections:
            if not section.strip():
                continue

            # 解析风险维度和等级
            lines = section.strip().split('\n')
            if not lines:
                continue

            # 第一行: 风险维度名称 (风险等级)
            header = lines[0]
            level_match = re.search(r'\(([^)]+)\)', header)
            level = level_match.group(1) if level_match else '未知'

            # 确定风险类型
            risk_type = None
            if '进度' in header:
                risk_type = 'progress'
            elif '优先级' in header:
                risk_type = 'priority'
            elif '资源' in header:
                risk_type = 'resource'

            if not risk_type:
                continue

            # 解析描述、影响、建议
            description = ''
            impact = ''
            suggestion = ''

            for line in lines[1:]:
                line = line.strip()
                # 处理中英文冒号
                line_normalized = line.replace('：', ':')

                # 匹配各种可能的格式
                if any(prefix in line_normalized for prefix in ['- **描述**:', '- 描述:', '**描述**:', '描述:']):
                    description = line_normalized.split(':', 1)[1].strip() if ':' in line_normalized else ''
                elif any(prefix in line_normalized for prefix in ['- **影响**:', '- 影响:', '**影响**:', '影响:']):
                    impact = line_normalized.split(':', 1)[1].strip() if ':' in line_normalized else ''
                elif any(prefix in line_normalized for prefix in ['- **建议**:', '- 建议:', '**建议**:', '建议:']):
                    suggestion = line_normalized.split(':', 1)[1].strip() if ':' in line_normalized else ''
                # 特殊字段映射
                elif any(prefix in line_normalized for prefix in ['- **紧急程度**:', '紧急程度:']):
                    impact = line_normalized.split(':', 1)[1].strip() if ':' in line_normalized else ''
                elif any(prefix in line_normalized for prefix in ['- **资源分配问题**:', '资源分配问题:']):
                    impact = line_normalized.split(':', 1)[1].strip() if ':' in line_normalized else ''

            risks[risk_type] = {
                'level': level,
                'description': description,
                'impact': impact,
                'suggestion': suggestion
            }

        return risks

    def get_name(self) -> str:
        """获取分析器名称"""
        return "risk_analyzer"
