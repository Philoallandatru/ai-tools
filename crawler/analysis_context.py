"""
分析上下文模块 - 在分析流水线中传递状态
"""

from typing import Dict, Any, List
from datetime import datetime


class AnalysisContext:
    """分析上下文 - 存储分析过程中的中间结果和元数据"""

    def __init__(self, issue_key: str):
        """
        初始化分析上下文

        Args:
            issue_key: Jira Issue Key (例如: KAN-1)
        """
        self.issue_key = issue_key
        self.results: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            'warnings': [],
            'timing': {},
            'llm_calls': 0,
            'start_time': datetime.now().isoformat()
        }

    def set_result(self, analyzer_name: str, result: Dict[str, Any]) -> None:
        """
        设置分析器结果

        Args:
            analyzer_name: 分析器名称
            result: 分析结果字典
        """
        self.results[analyzer_name] = result

    def get_result(self, analyzer_name: str) -> Dict[str, Any]:
        """
        获取分析器结果

        Args:
            analyzer_name: 分析器名称

        Returns:
            分析结果字典，如果不存在返回空字典
        """
        return self.results.get(analyzer_name, {})

    def add_warning(self, message: str) -> None:
        """
        添加警告信息

        Args:
            message: 警告消息
        """
        self.metadata['warnings'].append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def record_timing(self, analyzer_name: str, duration_ms: float) -> None:
        """
        记录分析器执行时间

        Args:
            analyzer_name: 分析器名称
            duration_ms: 执行时间（毫秒）
        """
        self.metadata['timing'][analyzer_name] = duration_ms

    def increment_llm_calls(self) -> None:
        """增加 LLM 调用计数"""
        self.metadata['llm_calls'] += 1

    def get_summary(self) -> Dict[str, Any]:
        """
        获取分析摘要

        Returns:
            包含所有结果和元数据的摘要字典
        """
        return {
            'issue_key': self.issue_key,
            'results': self.results,
            'metadata': {
                **self.metadata,
                'end_time': datetime.now().isoformat()
            }
        }
