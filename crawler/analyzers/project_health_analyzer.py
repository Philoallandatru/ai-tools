"""
项目健康度分析器 - 评估项目整体健康状况
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class ProjectHealthAnalyzer(BaseAnalyzer):
    """评估项目整体健康度（0-100分）"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化项目健康度分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config

        # 权重配置
        weights = config.get('weights', {})
        self.weight_progress = weights.get('progress', 0.30)
        self.weight_quality = weights.get('quality', 0.25)
        self.weight_resource = weights.get('resource', 0.25)
        self.weight_risk = weights.get('risk', 0.20)

        # 阈值配置
        thresholds = config.get('thresholds', {})
        self.threshold_healthy = thresholds.get('healthy', 80)
        self.threshold_warning = thresholds.get('warning', 60)

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        评估项目健康度

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含健康度评分和详细信息的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {'health_score': 0, 'enabled': False}

        jira = report_data.get('jira', {})

        # 计算各维度得分
        progress_score = self._calculate_progress_score(jira)
        quality_score = self._calculate_quality_score(jira)
        resource_score = self._calculate_resource_score(jira)
        risk_score = self._calculate_risk_score(jira)

        # 计算总分
        total_score = (
            progress_score * self.weight_progress +
            quality_score * self.weight_quality +
            resource_score * self.weight_resource +
            risk_score * self.weight_risk
        )

        # 确定健康等级
        if total_score >= self.threshold_healthy:
            health_level = "健康"
            emoji = "🟢"
            status = "good"
        elif total_score >= self.threshold_warning:
            health_level = "警告"
            emoji = "🟡"
            status = "warning"
        else:
            health_level = "危险"
            emoji = "🔴"
            status = "critical"

        return {
            'total_score': round(total_score, 1),
            'health_level': health_level,
            'emoji': emoji,
            'status': status,
            'dimension_scores': {
                'progress': {
                    'score': round(progress_score, 1),
                    'max_score': 30,
                    'weight': self.weight_progress
                },
                'quality': {
                    'score': round(quality_score, 1),
                    'max_score': 25,
                    'weight': self.weight_quality
                },
                'resource': {
                    'score': round(resource_score, 1),
                    'max_score': 25,
                    'weight': self.weight_resource
                },
                'risk': {
                    'score': round(risk_score, 1),
                    'max_score': 20,
                    'weight': self.weight_risk
                }
            },
            'success': True
        }

    def _calculate_progress_score(self, jira: Dict[str, Any]) -> float:
        """
        计算进度健康度（满分30分）

        评估指标：
        1. 完成率 (10分): Done / Total
        2. 停滞率 (10分): 1 - (Stalled / InProgress)
        3. 流动性 (10分): Closed / (New + Closed)
        """
        by_status = jira.get('by_status', {})
        total = jira.get('total', 0)

        if total == 0:
            return 30.0  # 没有 issues 视为健康

        # 统计各状态数量
        done_count = sum(len(issues) for status, issues in by_status.items()
                        if any(keyword in status.lower() for keyword in ['done', 'closed', 'resolved', '已完成', '已关闭']))
        in_progress_count = sum(len(issues) for status, issues in by_status.items()
                               if any(keyword in status.lower() for keyword in ['progress', 'doing', '进行中']))

        # 1. 完成率得分
        completion_rate = done_count / total if total > 0 else 0
        completion_score = completion_rate * 10

        # 2. 停滞率得分（需要从 risk_data 获取，这里简化处理）
        # 假设停滞 issues 占进行中的 20% 以下为健康
        stalled_score = 10.0  # 默认满分，实际应该从风险数据获取

        # 3. 流动性得分
        new_count = jira.get('new', 0)
        closed_count = done_count  # 简化：用 done 代替 closed
        flow_rate = closed_count / (new_count + closed_count) if (new_count + closed_count) > 0 else 0.5
        flow_score = flow_rate * 10

        return completion_score + stalled_score + flow_score

    def _calculate_quality_score(self, jira: Dict[str, Any]) -> float:
        """
        计算质量健康度（满分25分）

        评估指标：
        1. Bug 占比 (10分): 1 - (Bug / Total)
        2. 高优先级占比 (10分): 1 - (High+Highest / Total)
        3. 类型分布 (5分): 多样性评分
        """
        by_type = jira.get('by_type', {})
        by_priority = jira.get('by_priority', {})
        total = jira.get('total', 0)

        if total == 0:
            return 25.0

        # 1. Bug 占比得分
        bug_count = sum(len(issues) for issue_type, issues in by_type.items()
                       if 'bug' in issue_type.lower() or '缺陷' in issue_type.lower())
        bug_ratio = bug_count / total if total > 0 else 0
        # Bug 占比 < 20% 为健康
        bug_score = max(0, (1 - bug_ratio / 0.2) * 10)

        # 2. 高优先级占比得分
        high_priority_count = sum(len(issues) for priority, issues in by_priority.items()
                                 if priority in ['Highest', 'High', '最高', '高'])
        high_priority_ratio = high_priority_count / total if total > 0 else 0
        # 高优先级 < 30% 为健康
        priority_score = max(0, (1 - high_priority_ratio / 0.3) * 10)

        # 3. 类型分布得分（类型越多样化越好）
        type_count = len(by_type)
        diversity_score = min(5, type_count * 1.25)  # 4种类型满分

        return bug_score + priority_score + diversity_score

    def _calculate_resource_score(self, jira: Dict[str, Any]) -> float:
        """
        计算资源健康度（满分25分）

        评估指标：
        1. 负载均衡度 (10分): 基于标准差
        2. 未分配占比 (10分): 1 - (Unassigned / Total)
        3. 活跃度 (5分): 有分配的成员数量
        """
        by_assignee = jira.get('by_assignee', {})
        total = jira.get('total', 0)

        if total == 0:
            return 25.0

        # 1. 负载均衡度得分
        assignee_counts = []
        unassigned_count = 0

        for assignee, issues in by_assignee.items():
            count = len(issues) if isinstance(issues, list) else issues
            if assignee.lower() in ['unassigned', '未分配', 'none']:
                unassigned_count = count
            else:
                assignee_counts.append(count)

        if len(assignee_counts) > 1:
            # 计算标准差
            mean = sum(assignee_counts) / len(assignee_counts)
            variance = sum((x - mean) ** 2 for x in assignee_counts) / len(assignee_counts)
            std_dev = variance ** 0.5
            # 标准差越小越好，标准差 < 2 为满分
            balance_score = max(0, (1 - std_dev / 4) * 10)
        else:
            balance_score = 5.0  # 只有一个人，给一半分

        # 2. 未分配占比得分
        unassigned_ratio = unassigned_count / total if total > 0 else 0
        # 未分配 < 10% 为健康
        unassigned_score = max(0, (1 - unassigned_ratio / 0.1) * 10)

        # 3. 活跃度得分
        active_members = len([a for a in by_assignee.keys()
                            if a.lower() not in ['unassigned', '未分配', 'none']])
        activity_score = min(5, active_members * 1.0)  # 5人以上满分

        return balance_score + unassigned_score + activity_score

    def _calculate_risk_score(self, jira: Dict[str, Any]) -> float:
        """
        计算风险健康度（满分20分）

        评估指标：
        1. 高优先级未完成 (10分): 基于数量
        2. 停滞 issues (10分): 基于数量
        """
        by_priority = jira.get('by_priority', {})
        by_status = jira.get('by_status', {})
        total = jira.get('total', 0)

        if total == 0:
            return 20.0

        # 1. 高优先级未完成得分
        high_priority_incomplete = 0
        for priority, issues in by_priority.items():
            if priority in ['Highest', 'High', '最高', '高']:
                for issue in issues:
                    status = issue.get('status', '')
                    if status not in ['Done', 'Closed', 'Resolved', '已完成', '已关闭']:
                        high_priority_incomplete += 1

        # 高优先级未完成 < 5个为健康
        high_priority_score = max(0, (1 - high_priority_incomplete / 5) * 10)

        # 2. 停滞 issues 得分（简化处理，实际应该从风险分析器获取）
        # 假设进行中的 20% 可能停滞
        in_progress_count = sum(len(issues) for status, issues in by_status.items()
                               if any(keyword in status.lower() for keyword in ['progress', 'doing', '进行中']))
        estimated_stalled = in_progress_count * 0.2
        stalled_score = max(0, (1 - estimated_stalled / 5) * 10)

        return high_priority_score + stalled_score

    def get_name(self) -> str:
        """获取分析器名称"""
        return "project_health"
