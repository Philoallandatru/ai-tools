"""
趋势分析器 - 分析项目指标的历史趋势
"""

from typing import Dict, Any, List, Optional, Tuple
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.metrics_history import MetricsHistoryManager


class TrendAnalyzer(BaseAnalyzer):
    """分析最近N周的项目指标趋势"""

    def __init__(self, llm_client: Any, config: Dict[str, Any]):
        """
        初始化趋势分析器

        Args:
            llm_client: LLM 客户端（本分析器不使用LLM）
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config
        self.lookback_weeks = config.get('lookback_weeks', 4)
        self.min_data_points = config.get('min_data_points', 2)
        self.trend_threshold = config.get('trend_threshold', 0.1)  # 10%
        self.history_manager = MetricsHistoryManager()

    def get_name(self) -> str:
        """获取分析器名称"""
        return "trend_analysis"

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        分析趋势

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含趋势分析结果的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {}

        # 获取历史数据
        report_type = report_data.get('type', 'weekly')
        history = self.history_manager.get_last_n_weeks(self.lookback_weeks, report_type)

        # 检查数据是否充足
        if len(history) < self.min_data_points:
            return {
                'success': False,
                'message': f'趋势分析需要至少 {self.min_data_points} 周的历史数据（当前: {len(history)} 周）',
                'available_weeks': len(history)
            }

        # 分析各维度趋势
        health_trends = self._analyze_health_trends(history)
        team_trends = self._analyze_team_trends(history)
        issues_trends = self._analyze_issues_trends(history)

        # 生成洞察和建议
        insights = self._generate_insights(health_trends, team_trends, issues_trends, history)
        recommendations = self._generate_recommendations(health_trends, team_trends, issues_trends)

        return {
            'success': True,
            'data_points': len(history),
            'time_range': {
                'start': history[0].get('start_date') if history else None,
                'end': history[-1].get('end_date') if history else None
            },
            'trends': {
                'health': health_trends,
                'team': team_trends,
                'issues': issues_trends
            },
            'insights': insights,
            'recommendations': recommendations
        }

    def _analyze_health_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析健康度趋势"""
        # 提取健康度数据
        total_scores = [h.get('health', {}).get('total_score', 0) for h in history]
        progress_scores = [h.get('health', {}).get('progress_score', 0) for h in history]
        quality_scores = [h.get('health', {}).get('quality_score', 0) for h in history]
        resource_scores = [h.get('health', {}).get('resource_score', 0) for h in history]
        risk_scores = [h.get('health', {}).get('risk_score', 0) for h in history]

        # 计算趋势
        total_trend, total_change = self._calculate_trend(total_scores)
        progress_trend, progress_change = self._calculate_trend(progress_scores)
        quality_trend, quality_change = self._calculate_trend(quality_scores)
        resource_trend, resource_change = self._calculate_trend(resource_scores)
        risk_trend, risk_change = self._calculate_trend(risk_scores)

        return {
            'total': {
                'trend': total_trend,
                'change': total_change,
                'current': total_scores[-1] if total_scores else 0,
                'previous': total_scores[0] if total_scores else 0,
                'weekly_data': total_scores
            },
            'dimensions': {
                'progress': {
                    'trend': progress_trend,
                    'change': progress_change,
                    'current': progress_scores[-1] if progress_scores else 0,
                    'previous': progress_scores[0] if progress_scores else 0
                },
                'quality': {
                    'trend': quality_trend,
                    'change': quality_change,
                    'current': quality_scores[-1] if quality_scores else 0,
                    'previous': quality_scores[0] if quality_scores else 0
                },
                'resource': {
                    'trend': resource_trend,
                    'change': resource_change,
                    'current': resource_scores[-1] if resource_scores else 0,
                    'previous': resource_scores[0] if resource_scores else 0
                },
                'risk': {
                    'trend': risk_trend,
                    'change': risk_change,
                    'current': risk_scores[-1] if risk_scores else 0,
                    'previous': risk_scores[0] if risk_scores else 0
                }
            }
        }

    def _analyze_team_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析团队效率趋势"""
        # 提取团队数据
        gini_coefficients = [h.get('team', {}).get('gini_coefficient', 0) for h in history]
        bottleneck_counts = [h.get('team', {}).get('bottleneck_count', 0) for h in history]
        overloaded_counts = [h.get('team', {}).get('overloaded_count', 0) for h in history]
        team_sizes = [h.get('team', {}).get('total_members', 0) for h in history]

        # 计算趋势（注意：Gini系数和瓶颈数越低越好）
        gini_trend, gini_change = self._calculate_trend(gini_coefficients, lower_is_better=True)
        bottleneck_trend, bottleneck_change = self._calculate_trend(bottleneck_counts, lower_is_better=True)
        overloaded_trend, overloaded_change = self._calculate_trend(overloaded_counts, lower_is_better=True)
        size_trend, size_change = self._calculate_trend(team_sizes, neutral=True)

        return {
            'load_balance': {
                'trend': gini_trend,
                'change': gini_change,
                'current': gini_coefficients[-1] if gini_coefficients else 0,
                'previous': gini_coefficients[0] if gini_coefficients else 0,
                'weekly_data': gini_coefficients
            },
            'bottlenecks': {
                'trend': bottleneck_trend,
                'change': bottleneck_change,
                'current': bottleneck_counts[-1] if bottleneck_counts else 0,
                'previous': bottleneck_counts[0] if bottleneck_counts else 0
            },
            'overloaded': {
                'trend': overloaded_trend,
                'change': overloaded_change,
                'current': overloaded_counts[-1] if overloaded_counts else 0,
                'previous': overloaded_counts[0] if overloaded_counts else 0
            },
            'team_size': {
                'trend': size_trend,
                'change': size_change,
                'current': team_sizes[-1] if team_sizes else 0,
                'previous': team_sizes[0] if team_sizes else 0
            }
        }

    def _analyze_issues_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析Issues活动趋势"""
        # 提取Issues数据
        total_items = [h.get('jira', {}).get('total_items', 0) for h in history]
        new_items = [h.get('jira', {}).get('new', 0) for h in history]
        updated_items = [h.get('jira', {}).get('updated', 0) for h in history]

        # 计算趋势
        total_trend, total_change = self._calculate_trend(total_items, neutral=True)
        new_trend, new_change = self._calculate_trend(new_items, neutral=True)
        updated_trend, updated_change = self._calculate_trend(updated_items, neutral=True)

        return {
            'total': {
                'trend': total_trend,
                'change': total_change,
                'current': total_items[-1] if total_items else 0,
                'previous': total_items[0] if total_items else 0,
                'average': sum(total_items) / len(total_items) if total_items else 0,
                'weekly_data': total_items
            },
            'new': {
                'trend': new_trend,
                'change': new_change,
                'current': new_items[-1] if new_items else 0,
                'average': sum(new_items) / len(new_items) if new_items else 0
            },
            'updated': {
                'trend': updated_trend,
                'change': updated_change,
                'current': updated_items[-1] if updated_items else 0,
                'average': sum(updated_items) / len(updated_items) if updated_items else 0
            }
        }

    def _calculate_trend(self, values: List[float], lower_is_better: bool = False,
                        neutral: bool = False) -> Tuple[str, float]:
        """
        计算趋势方向和变化量

        Args:
            values: 时间序列数据（从旧到新）
            lower_is_better: 是否越低越好（如Gini系数）
            neutral: 是否中性指标（如团队规模）

        Returns:
            (趋势描述, 变化量)
        """
        if len(values) < 2:
            return "insufficient_data", 0

        # 计算线性回归斜率
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # 计算总变化量和百分比
        first_value = values[0]
        last_value = values[-1]
        total_change = last_value - first_value
        change_pct = abs(total_change / first_value) if first_value != 0 else 0

        # 判断趋势
        if change_pct < self.trend_threshold:
            trend = "stable"
        elif slope > 0:
            if neutral:
                trend = "increasing"
            elif lower_is_better:
                trend = "declining"  # 数值上升但实际变差
            else:
                trend = "improving"  # 数值上升且实际变好
        else:
            if neutral:
                trend = "decreasing"
            elif lower_is_better:
                trend = "improving"  # 数值下降但实际变好
            else:
                trend = "declining"  # 数值下降且实际变差

        return trend, total_change

    def _generate_insights(self, health_trends: Dict[str, Any],
                          team_trends: Dict[str, Any],
                          issues_trends: Dict[str, Any],
                          history: List[Dict[str, Any]]) -> List[str]:
        """生成关键洞察"""
        insights = []

        # 健康度洞察
        health_total = health_trends.get('total', {})
        if health_total.get('trend') == 'improving':
            change = health_total.get('change', 0)
            insights.append(f"项目健康度持续改善，{len(history)}周内提升 {change:.1f} 分")
        elif health_total.get('trend') == 'declining':
            change = abs(health_total.get('change', 0))
            insights.append(f"⚠️ 项目健康度下降，{len(history)}周内降低 {change:.1f} 分，需要关注")

        # 团队负载洞察
        load_balance = team_trends.get('load_balance', {})
        if load_balance.get('trend') == 'improving':
            current = load_balance.get('current', 0)
            previous = load_balance.get('previous', 0)
            change_pct = abs((current - previous) / previous * 100) if previous != 0 else 0
            insights.append(f"团队负载分布更加均衡（基尼系数: {previous:.3f} → {current:.3f}, ↓ {change_pct:.1f}%）")

        # 瓶颈洞察
        bottlenecks = team_trends.get('bottlenecks', {})
        if bottlenecks.get('trend') == 'improving':
            current = bottlenecks.get('current', 0)
            previous = bottlenecks.get('previous', 0)
            if previous > 0:
                change_pct = abs((current - previous) / previous * 100)
                insights.append(f"瓶颈成员数减少 {change_pct:.0f}%（{previous} → {current}）")

        # Issues活动洞察
        issues_total = issues_trends.get('total', {})
        if issues_total.get('trend') == 'stable':
            avg = issues_total.get('average', 0)
            insights.append(f"Issues总量保持稳定（平均 {avg:.1f} issues/周）")

        return insights

    def _generate_recommendations(self, health_trends: Dict[str, Any],
                                  team_trends: Dict[str, Any],
                                  issues_trends: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于健康度趋势
        health_total = health_trends.get('total', {})
        if health_total.get('trend') == 'improving':
            recommendations.append("继续当前实践 - 项目健康度趋势积极")
        elif health_total.get('trend') == 'declining':
            recommendations.append("需要采取措施改善项目健康度，重点关注下降的维度")

        # 基于团队趋势
        team_size = team_trends.get('team_size', {})
        if team_size.get('trend') == 'increasing':
            recommendations.append("团队规模扩大，注意新成员融入和知识传递")

        overloaded = team_trends.get('overloaded', {})
        if overloaded.get('current', 0) > 0:
            recommendations.append("存在负载过重成员，建议重新分配任务或增加资源")

        return recommendations
