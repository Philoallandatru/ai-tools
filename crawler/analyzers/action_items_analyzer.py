"""
行动项清单分析器 - 将建议转化为可追踪的行动项
"""

from typing import Dict, Any, List
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class ActionItemsAnalyzer(BaseAnalyzer):
    """汇总报告中的建议，生成结构化的行动项清单"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化行动项分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config
        self.max_tokens = config.get('max_tokens', 8000)

    def get_name(self) -> str:
        """获取分析器名称"""
        return "action_items"

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        分析报告并生成行动项清单

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含行动项清单的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {}

        # 从 context 中获取其他分析器的结果
        analysis_results = context.results if hasattr(context, 'results') else {}

        # 收集所有建议
        recommendations = self._collect_recommendations(analysis_results, report_data)

        if not recommendations:
            return {
                'success': True,
                'action_items': [],
                'summary': '当前无需执行的行动项'
            }

        # 使用 LLM 将建议转化为结构化的行动项
        action_items = self._generate_action_items(recommendations, report_data, context)

        # 按优先级分类
        categorized_items = self._categorize_by_priority(action_items)

        return {
            'success': True,
            'action_items': action_items,
            'by_priority': categorized_items,
            'total_count': len(action_items),
            'summary': self._generate_summary(categorized_items)
        }

    def _collect_recommendations(self, analysis_results: Dict[str, Any], report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从分析结果中收集所有建议

        Args:
            analysis_results: 分析结果
            report_data: 报告数据

        Returns:
            建议列表
        """
        recommendations = []

        # 从项目状态分析中提取建议
        status_analysis = analysis_results.get('project_status', {})
        action_recs = status_analysis.get('action_recommendations', [])
        if action_recs:
            for rec in action_recs:
                recommendations.append({
                    'source': '项目状态评估',
                    'content': rec,
                    'context': status_analysis.get('main_problems', [])
                })

        # 从健康度分析中提取改进建议
        health_analysis = analysis_results.get('project_health', {})
        dimension_scores = health_analysis.get('dimension_scores', {})
        for dimension, data in dimension_scores.items():
            if isinstance(data, dict) and data.get('recommendations'):
                for rec in data['recommendations']:
                    recommendations.append({
                        'source': f'项目健康度 - {dimension}',
                        'content': rec,
                        'context': {'score': data.get('score'), 'dimension': dimension}
                    })

        # 从团队协作分析中提取建议
        team_analysis = analysis_results.get('team_collaboration', {})
        team_summary = team_analysis.get('summary', {})
        team_recs = team_summary.get('recommendations', [])
        if team_recs:
            for rec in team_recs:
                recommendations.append({
                    'source': '团队协作分析',
                    'content': rec,
                    'context': team_analysis.get('bottlenecks', {})
                })

        # 从风险分析中提取建议
        risk_analysis = analysis_results.get('risk_analyzer', {})
        risks = risk_analysis.get('risks', {}) if isinstance(risk_analysis, dict) else {}

        # risks 是一个字典，包含 progress, priority, resource 三个维度
        if isinstance(risks, dict):
            for dimension, risk_data in risks.items():
                if isinstance(risk_data, dict):
                    # 字段名是 'suggestion' 而不是 'mitigation'
                    suggestion = risk_data.get('suggestion') or risk_data.get('mitigation')
                    if suggestion:
                        recommendations.append({
                            'source': f"风险管理 - {dimension}",
                            'content': suggestion,
                            'context': {
                                'risk_level': risk_data.get('level', '未知'),
                                'description': risk_data.get('description', ''),
                                'impact': risk_data.get('impact', '')
                            }
                        })

        return recommendations

    def _generate_action_items(self, recommendations: List[Dict[str, Any]],
                               report_data: Dict[str, Any],
                               context: ReportContext) -> List[Dict[str, Any]]:
        """
        使用 LLM 将建议转化为结构化的行动项

        Args:
            recommendations: 建议列表
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            行动项列表
        """
        if not recommendations:
            return []

        # 构建 prompt
        prompt = self._build_action_items_prompt(recommendations, report_data)

        # 调用 LLM
        try:
            context.increment_llm_calls()
            response = self.llm_client.generate(prompt, max_tokens=self.max_tokens)

            # 解析响应
            action_items = self._parse_action_items_response(response, recommendations)
            return action_items

        except Exception as e:
            print(f"[WARNING] 生成行动项时出错: {e}")
            # 降级方案：直接将建议转化为行动项
            return self._fallback_action_items(recommendations)

    def _build_action_items_prompt(self, recommendations: List[Dict[str, Any]],
                                   report_data: Dict[str, Any]) -> str:
        """构建生成行动项的 prompt"""

        # 获取项目概况
        jira = report_data.get('jira', {})
        total_issues = jira.get('total', 0)

        prompt = f"""基于以下项目报告中的建议，生成结构化的行动项清单。

项目概况：
- 总 Issues 数: {total_issues}
- 时间范围: {report_data.get('time_range', {}).get('start', '')} 至 {report_data.get('time_range', {}).get('end', '')}

收集到的建议：
"""

        for i, rec in enumerate(recommendations, 1):
            prompt += f"\n{i}. 来源: {rec['source']}\n"
            prompt += f"   建议: {rec['content']}\n"

        prompt += """

请将这些建议转化为具体的、可执行的行动项。每个行动项应包含：
1. 标题：简洁明确的行动描述（不超过50字）
2. 优先级：高/中/低（基于影响和紧急程度）
3. 描述：详细的执行步骤和预期结果
4. 预期效果：完成后的预期改善
5. 建议责任人：适合执行此行动的角色（如：项目经理、开发负责人、团队 Lead 等）

请按以下格式输出（每个行动项之间用 "---" 分隔）：

标题: [行动项标题]
优先级: [高/中/低]
描述: [详细描述]
预期效果: [预期改善]
建议责任人: [角色]
---

注意：
- 合并相似的建议，避免重复
- 优先级判断标准：高=影响大且紧急，中=影响中等或不太紧急，低=优化类建议
- 行动项应具体可执行，避免模糊表述
"""

        return prompt

    def _parse_action_items_response(self, response: str,
                                    recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析 LLM 响应，提取行动项

        Args:
            response: LLM 响应
            recommendations: 原始建议列表

        Returns:
            行动项列表
        """
        action_items = []

        # 按 "---" 分割行动项
        items = response.split('---')

        for item_text in items:
            item_text = item_text.strip()
            if not item_text:
                continue

            # 解析每个字段
            action_item = {}
            lines = item_text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('标题:') or line.startswith('标题：'):
                    action_item['title'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                elif line.startswith('优先级:') or line.startswith('优先级：'):
                    priority_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                    action_item['priority'] = self._normalize_priority(priority_text)
                elif line.startswith('描述:') or line.startswith('描述：'):
                    action_item['description'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                elif line.startswith('预期效果:') or line.startswith('预期效果：'):
                    action_item['expected_outcome'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                elif line.startswith('建议责任人:') or line.startswith('建议责任人：'):
                    action_item['suggested_owner'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()

            # 验证必填字段
            if action_item.get('title') and action_item.get('priority'):
                action_items.append(action_item)

        return action_items

    def _normalize_priority(self, priority_text: str) -> str:
        """标准化优先级文本"""
        priority_text = priority_text.lower().strip()
        if '高' in priority_text or 'high' in priority_text:
            return '高'
        elif '低' in priority_text or 'low' in priority_text:
            return '低'
        else:
            return '中'

    def _fallback_action_items(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        降级方案：直接将建议转化为行动项（不使用 LLM）

        Args:
            recommendations: 建议列表

        Returns:
            行动项列表
        """
        action_items = []

        for rec in recommendations:
            # 简单的优先级判断
            priority = '中'
            if '立即' in rec['content'] or '紧急' in rec['content'] or '高优先级' in rec['content']:
                priority = '高'
            elif '建议' in rec['content'] or '可以' in rec['content']:
                priority = '低'

            action_item = {
                'title': rec['content'][:50] + ('...' if len(rec['content']) > 50 else ''),
                'priority': priority,
                'description': rec['content'],
                'expected_outcome': '改善项目状态',
                'suggested_owner': '项目负责人',
                'source': rec['source']
            }
            action_items.append(action_item)

        return action_items

    def _categorize_by_priority(self, action_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按优先级分类行动项

        Args:
            action_items: 行动项列表

        Returns:
            按优先级分类的字典
        """
        categorized = {
            '高': [],
            '中': [],
            '低': []
        }

        for item in action_items:
            priority = item.get('priority', '中')
            if priority in categorized:
                categorized[priority].append(item)

        return categorized

    def _generate_summary(self, categorized_items: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        生成行动项摘要

        Args:
            categorized_items: 按优先级分类的行动项

        Returns:
            摘要文本
        """
        high_count = len(categorized_items.get('高', []))
        medium_count = len(categorized_items.get('中', []))
        low_count = len(categorized_items.get('低', []))

        total = high_count + medium_count + low_count

        if total == 0:
            return '当前无需执行的行动项'

        summary = f"共 {total} 项行动建议"
        if high_count > 0:
            summary += f"，其中 {high_count} 项高优先级需立即处理"
        if medium_count > 0:
            summary += f"，{medium_count} 项中优先级"
        if low_count > 0:
            summary += f"，{low_count} 项低优先级"

        return summary
