"""
团队协作分析器 - 分析团队负载分布、瓶颈和协作网络
"""

from typing import Dict, Any, List, Tuple
from collections import defaultdict
import statistics
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class TeamCollaborationAnalyzer(BaseAnalyzer):
    """分析团队协作情况，包括负载分布、瓶颈识别和协作网络"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化团队协作分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config

        # 阈值配置
        self.overload_threshold = config.get('overload_threshold', 1.5)  # 超过平均负载的倍数
        self.underload_threshold = config.get('underload_threshold', 0.5)  # 低于平均负载的倍数
        self.bottleneck_blocker_threshold = config.get('bottleneck_blocker_threshold', 3)  # 阻塞issue数量

    def get_name(self) -> str:
        """获取分析器名称"""
        return "team_collaboration"

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        分析团队协作情况

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含团队协作分析结果的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {}

        jira_data = report_data.get('jira', {})
        if not jira_data:
            return {'success': False, 'message': '无 Jira 数据'}

        # 使用 all_issues 而不是 issues
        issues = jira_data.get('all_issues', [])
        if not issues:
            return {'success': False, 'message': '无 Issue 数据'}

        # 执行各项分析
        workload_analysis = self._analyze_workload_distribution(issues)
        bottleneck_analysis = self._identify_bottlenecks(issues)
        collaboration_analysis = self._analyze_collaboration_network(issues)

        return {
            'success': True,
            'workload_distribution': workload_analysis,
            'bottlenecks': bottleneck_analysis,
            'collaboration_network': collaboration_analysis,
            'summary': self._generate_summary(workload_analysis, bottleneck_analysis, collaboration_analysis)
        }

    def _analyze_workload_distribution(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析团队负载分布

        Args:
            issues: Issue 列表

        Returns:
            负载分布分析结果
        """
        # 统计每个成员的工作量
        assignee_workload = defaultdict(lambda: {'total': 0, 'open': 0, 'in_progress': 0, 'high_priority': 0})

        for issue in issues:
            assignee = issue.get('assignee')
            if not assignee or assignee == 'Unassigned':
                continue

            status = issue.get('status', '').lower()
            priority = issue.get('priority', '').lower()

            assignee_workload[assignee]['total'] += 1

            if status in ['open', 'to do', 'todo', 'backlog']:
                assignee_workload[assignee]['open'] += 1
            elif status in ['in progress', 'in_progress', 'doing']:
                assignee_workload[assignee]['in_progress'] += 1

            if priority in ['highest', 'high', 'critical', 'blocker']:
                assignee_workload[assignee]['high_priority'] += 1

        if not assignee_workload:
            return {
                'members': [],
                'statistics': {},
                'overloaded': [],
                'underloaded': [],
                'balanced': True
            }

        # 计算统计指标
        workloads = [data['total'] for data in assignee_workload.values()]
        mean_workload = statistics.mean(workloads)
        std_dev = statistics.stdev(workloads) if len(workloads) > 1 else 0
        gini_coefficient = self._calculate_gini_coefficient(workloads)

        # 识别负载过重和过轻的成员
        overloaded = []
        underloaded = []

        for assignee, data in assignee_workload.items():
            workload = data['total']
            if workload > mean_workload * self.overload_threshold:
                overloaded.append({
                    'name': assignee,
                    'workload': workload,
                    'percentage': round((workload / mean_workload - 1) * 100, 1)
                })
            elif workload < mean_workload * self.underload_threshold and mean_workload > 0:
                underloaded.append({
                    'name': assignee,
                    'workload': workload,
                    'percentage': round((1 - workload / mean_workload) * 100, 1)
                })

        # 排序
        overloaded.sort(key=lambda x: x['workload'], reverse=True)
        underloaded.sort(key=lambda x: x['workload'])

        # 判断是否均衡
        balanced = len(overloaded) == 0 and len(underloaded) == 0

        return {
            'members': [
                {
                    'name': assignee,
                    'total': data['total'],
                    'open': data['open'],
                    'in_progress': data['in_progress'],
                    'high_priority': data['high_priority']
                }
                for assignee, data in sorted(assignee_workload.items(), key=lambda x: x[1]['total'], reverse=True)
            ],
            'statistics': {
                'mean': round(mean_workload, 2),
                'std_dev': round(std_dev, 2),
                'gini_coefficient': round(gini_coefficient, 3),
                'total_members': len(assignee_workload)
            },
            'overloaded': overloaded,
            'underloaded': underloaded,
            'balanced': balanced
        }

    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """
        计算基尼系数（衡量不平等程度，0=完全平等，1=完全不平等）

        Args:
            values: 数值列表

        Returns:
            基尼系数
        """
        if not values or len(values) == 1:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = 0

        for i, value in enumerate(sorted_values):
            cumsum += (i + 1) * value

        return (2 * cumsum) / (n * sum(sorted_values)) - (n + 1) / n

    def _identify_bottlenecks(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        识别团队瓶颈

        Args:
            issues: Issue 列表

        Returns:
            瓶颈分析结果
        """
        # 统计每个成员相关的阻塞情况
        assignee_blockers = defaultdict(int)
        assignee_high_priority = defaultdict(int)
        assignee_overdue = defaultdict(int)

        for issue in issues:
            assignee = issue.get('assignee')
            if not assignee or assignee == 'Unassigned':
                continue

            # 统计阻塞其他issue的数量
            if issue.get('is_blocker', False):
                assignee_blockers[assignee] += 1

            # 统计高优先级issue
            priority = issue.get('priority', '').lower()
            if priority in ['highest', 'high', 'critical', 'blocker']:
                assignee_high_priority[assignee] += 1

            # 统计逾期issue
            if issue.get('is_overdue', False):
                assignee_overdue[assignee] += 1

        # 识别瓶颈成员
        bottlenecks = []

        for assignee in set(list(assignee_blockers.keys()) + list(assignee_high_priority.keys()) + list(assignee_overdue.keys())):
            blockers = assignee_blockers.get(assignee, 0)
            high_priority = assignee_high_priority.get(assignee, 0)
            overdue = assignee_overdue.get(assignee, 0)

            # 计算瓶颈分数
            bottleneck_score = blockers * 3 + high_priority * 2 + overdue * 2

            if blockers >= self.bottleneck_blocker_threshold or bottleneck_score >= 10:
                bottlenecks.append({
                    'name': assignee,
                    'blockers': blockers,
                    'high_priority': high_priority,
                    'overdue': overdue,
                    'score': bottleneck_score,
                    'reasons': self._get_bottleneck_reasons(blockers, high_priority, overdue)
                })

        # 按分数排序
        bottlenecks.sort(key=lambda x: x['score'], reverse=True)

        return {
            'bottleneck_members': bottlenecks,
            'has_bottlenecks': len(bottlenecks) > 0,
            'total_blockers': sum(assignee_blockers.values()),
            'total_high_priority': sum(assignee_high_priority.values())
        }

    def _get_bottleneck_reasons(self, blockers: int, high_priority: int, overdue: int) -> List[str]:
        """
        生成瓶颈原因描述

        Args:
            blockers: 阻塞issue数量
            high_priority: 高优先级issue数量
            overdue: 逾期issue数量

        Returns:
            原因列表
        """
        reasons = []

        if blockers > 0:
            reasons.append(f"阻塞 {blockers} 个其他任务")
        if high_priority > 0:
            reasons.append(f"负责 {high_priority} 个高优先级任务")
        if overdue > 0:
            reasons.append(f"有 {overdue} 个任务逾期")

        return reasons

    def _analyze_collaboration_network(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析协作网络

        Args:
            issues: Issue 列表

        Returns:
            协作网络分析结果
        """
        # 统计协作关系（reporter -> assignee）
        collaboration_pairs = defaultdict(int)
        member_connections = defaultdict(set)

        for issue in issues:
            reporter = issue.get('reporter')
            assignee = issue.get('assignee')

            if not reporter or not assignee or assignee == 'Unassigned' or reporter == assignee:
                continue

            pair = (reporter, assignee)
            collaboration_pairs[pair] += 1
            member_connections[reporter].add(assignee)
            member_connections[assignee].add(reporter)

        # 识别协作频繁的配对
        frequent_collaborations = [
            {
                'reporter': pair[0],
                'assignee': pair[1],
                'count': count
            }
            for pair, count in sorted(collaboration_pairs.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # 识别孤立成员（连接数少）
        isolated_members = []
        if member_connections:
            avg_connections = statistics.mean([len(connections) for connections in member_connections.values()])

            for member, connections in member_connections.items():
                if len(connections) < avg_connections * 0.5 and len(connections) > 0:
                    isolated_members.append({
                        'name': member,
                        'connections': len(connections)
                    })

            isolated_members.sort(key=lambda x: x['connections'])

        # 识别核心成员（连接数多）
        core_members = []
        if member_connections:
            for member, connections in member_connections.items():
                if len(connections) >= avg_connections * 1.5:
                    core_members.append({
                        'name': member,
                        'connections': len(connections)
                    })

            core_members.sort(key=lambda x: x['connections'], reverse=True)

        return {
            'frequent_collaborations': frequent_collaborations,
            'isolated_members': isolated_members,
            'core_members': core_members,
            'total_collaboration_pairs': len(collaboration_pairs),
            'network_health': 'healthy' if len(isolated_members) == 0 else 'needs_attention'
        }

    def _generate_summary(self, workload: Dict[str, Any], bottlenecks: Dict[str, Any],
                         collaboration: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成团队协作分析摘要

        Args:
            workload: 负载分布分析结果
            bottlenecks: 瓶颈分析结果
            collaboration: 协作网络分析结果

        Returns:
            摘要信息
        """
        issues = []
        recommendations = []

        # 负载分布问题
        if not workload.get('balanced', True):
            overloaded_count = len(workload.get('overloaded', []))
            underloaded_count = len(workload.get('underloaded', []))

            if overloaded_count > 0:
                issues.append(f"{overloaded_count} 名成员负载过重")
                recommendations.append("重新分配任务，减轻负载过重成员的工作量")

            if underloaded_count > 0:
                issues.append(f"{underloaded_count} 名成员负载较轻")
                recommendations.append("考虑将任务分配给负载较轻的成员")

        # 瓶颈问题
        if bottlenecks.get('has_bottlenecks', False):
            bottleneck_count = len(bottlenecks.get('bottleneck_members', []))
            issues.append(f"{bottleneck_count} 名成员成为项目瓶颈")
            recommendations.append("优先解决瓶颈成员的阻塞任务，或寻求支援")

        # 协作网络问题
        isolated_count = len(collaboration.get('isolated_members', []))
        if isolated_count > 0:
            issues.append(f"{isolated_count} 名成员协作较少")
            recommendations.append("促进团队协作，增加成员间的沟通")

        # 整体评估
        gini = workload.get('statistics', {}).get('gini_coefficient', 0)
        if gini < 0.2:
            overall_status = 'excellent'
            status_text = '优秀'
        elif gini < 0.3:
            overall_status = 'good'
            status_text = '良好'
        elif gini < 0.4:
            overall_status = 'fair'
            status_text = '一般'
        else:
            overall_status = 'poor'
            status_text = '需要改进'

        return {
            'overall_status': overall_status,
            'status_text': status_text,
            'issues': issues,
            'recommendations': recommendations,
            'metrics': {
                'gini_coefficient': gini,
                'bottleneck_count': len(bottlenecks.get('bottleneck_members', [])),
                'isolated_count': isolated_count
            }
        }
