"""
历史指标管理模块 - 管理报告指标的历史数据存储
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class MetricsHistoryManager:
    """历史指标管理器 - 存储和查询报告的关键指标"""

    def __init__(self, history_file: str = "./.report-metrics-history.json"):
        """
        初始化历史指标管理器

        Args:
            history_file: 历史数据文件路径
        """
        self.history_file = Path(history_file)
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        """加载历史数据"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] 加载历史数据失败: {e}，使用空历史")
                return self._create_empty_history()
        return self._create_empty_history()

    def _create_empty_history(self) -> Dict[str, Any]:
        """创建空的历史数据结构"""
        return {
            "version": "1.0.0",
            "last_updated": None,
            "metrics": []
        }

    def _save_history(self):
        """保存历史数据到文件"""
        self.history["last_updated"] = datetime.utcnow().isoformat() + 'Z'
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def extract_metrics(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从完整报告中提取关键指标

        Args:
            report_data: 完整的报告数据

        Returns:
            提取的轻量级指标
        """
        # 生成报告ID
        report_type = report_data.get('type', 'unknown')
        start_date = report_data.get('start_date', '')
        end_date = report_data.get('end_date', '')
        report_id = f"{report_type}_{start_date}_to_{end_date}"

        # 提取Jira指标
        jira_data = report_data.get('jira', {})
        jira_metrics = {
            'total_items': jira_data.get('total', 0),
            'new': jira_data.get('new', 0),
            'updated': jira_data.get('updated', 0),
            'by_status_counts': {},
            'by_priority_counts': {},
            'by_type_counts': {}
        }

        # 统计状态分布
        by_status = jira_data.get('by_status', {})
        for status, issues in by_status.items():
            jira_metrics['by_status_counts'][status] = len(issues) if isinstance(issues, list) else 0

        # 统计优先级分布
        by_priority = jira_data.get('by_priority', {})
        for priority, issues in by_priority.items():
            jira_metrics['by_priority_counts'][priority] = len(issues) if isinstance(issues, list) else 0

        # 统计类型分布
        by_type = jira_data.get('by_type', {})
        for issue_type, issues in by_type.items():
            jira_metrics['by_type_counts'][issue_type] = len(issues) if isinstance(issues, list) else 0

        # 提取健康度指标
        analysis = report_data.get('analysis', {})
        health_data = analysis.get('project_health', {})
        health_metrics = {
            'total_score': health_data.get('total_score', 0),
            'progress_score': 0,
            'quality_score': 0,
            'resource_score': 0,
            'risk_score': 0
        }

        # 从维度评分中提取
        dimension_scores = health_data.get('dimension_scores', {})
        if dimension_scores:
            # 使用英文键名
            if 'progress' in dimension_scores:
                health_metrics['progress_score'] = dimension_scores['progress'].get('score', 0)
            if 'quality' in dimension_scores:
                health_metrics['quality_score'] = dimension_scores['quality'].get('score', 0)
            if 'resource' in dimension_scores:
                health_metrics['resource_score'] = dimension_scores['resource'].get('score', 0)
            if 'risk' in dimension_scores:
                health_metrics['risk_score'] = dimension_scores['risk'].get('score', 0)

        # 提取团队协作指标
        team_data = analysis.get('team_collaboration', {})
        team_metrics = {
            'gini_coefficient': 0,
            'bottleneck_count': 0,
            'overloaded_count': 0,
            'underloaded_count': 0,
            'total_members': 0
        }

        # 从工作负载分布中提取
        workload_dist = team_data.get('workload_distribution', {})
        if workload_dist:
            stats = workload_dist.get('statistics', {})
            team_metrics['gini_coefficient'] = stats.get('gini_coefficient', 0)
            team_metrics['total_members'] = stats.get('total_members', 0)

            overloaded = workload_dist.get('overloaded', [])
            underloaded = workload_dist.get('underloaded', [])
            team_metrics['overloaded_count'] = len(overloaded) if isinstance(overloaded, list) else 0
            team_metrics['underloaded_count'] = len(underloaded) if isinstance(underloaded, list) else 0

        # 从瓶颈数据中提取
        bottlenecks = team_data.get('bottlenecks', {})
        if isinstance(bottlenecks, dict):
            bottleneck_members = bottlenecks.get('bottleneck_members', [])
            team_metrics['bottleneck_count'] = len(bottleneck_members) if isinstance(bottleneck_members, list) else 0

        # 组装指标记录
        metrics_record = {
            'report_id': report_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'start_date': start_date,
            'end_date': end_date,
            'report_type': report_type,
            'jira': jira_metrics,
            'health': health_metrics,
            'team': team_metrics
        }

        return metrics_record

    def save_metrics(self, report_data: Dict[str, Any]) -> None:
        """
        保存报告指标到历史记录

        Args:
            report_data: 完整的报告数据
        """
        try:
            # 提取指标
            metrics_record = self.extract_metrics(report_data)

            # 检查是否已存在相同的报告ID
            report_id = metrics_record['report_id']
            existing_index = None
            for i, record in enumerate(self.history['metrics']):
                if record.get('report_id') == report_id:
                    existing_index = i
                    break

            # 更新或添加
            if existing_index is not None:
                self.history['metrics'][existing_index] = metrics_record
            else:
                self.history['metrics'].append(metrics_record)

            # 按时间戳排序（最新的在后面）
            self.history['metrics'].sort(key=lambda x: x.get('timestamp', ''))

            # 保存到文件
            self._save_history()

        except Exception as e:
            print(f"[ERROR] 保存指标历史失败: {e}")

    def get_last_n_weeks(self, n: int = 4, report_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取最近N周的指标数据

        Args:
            n: 周数
            report_type: 报告类型过滤（如 'weekly'），None表示不过滤

        Returns:
            最近N周的指标列表（按时间升序）
        """
        metrics = self.history.get('metrics', [])

        # 按报告类型过滤
        if report_type:
            metrics = [m for m in metrics if m.get('report_type') == report_type]

        # 返回最后N条记录
        return metrics[-n:] if len(metrics) >= n else metrics

    def cleanup_old_metrics(self, keep_weeks: int = 52) -> int:
        """
        清理超过指定周数的旧指标

        Args:
            keep_weeks: 保留的周数

        Returns:
            删除的记录数
        """
        metrics = self.history.get('metrics', [])
        original_count = len(metrics)

        if original_count > keep_weeks:
            # 保留最新的 keep_weeks 条记录
            self.history['metrics'] = metrics[-keep_weeks:]
            self._save_history()
            deleted_count = original_count - keep_weeks
            print(f"[INFO] 清理了 {deleted_count} 条旧指标记录")
            return deleted_count

        return 0

    def get_metrics_count(self, report_type: Optional[str] = None) -> int:
        """
        获取指标记录数量

        Args:
            report_type: 报告类型过滤，None表示不过滤

        Returns:
            记录数量
        """
        metrics = self.history.get('metrics', [])
        if report_type:
            metrics = [m for m in metrics if m.get('report_type') == report_type]
        return len(metrics)
