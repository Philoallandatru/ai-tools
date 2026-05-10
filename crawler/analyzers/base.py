"""
分析器基类模块
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from crawler.analysis_context import AnalysisContext


class BaseAnalyzer(ABC):
    """分析器基类 - 所有分析器的抽象接口"""

    @abstractmethod
    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行分析

        Args:
            jira_data: Jira Issue 数据字典
            context: 分析上下文对象

        Returns:
            分析结果字典
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        获取分析器名称

        Returns:
            分析器名称
        """
        pass
