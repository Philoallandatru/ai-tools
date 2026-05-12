"""
基础上下文模块 - 所有分析器上下文的抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class BaseContext(ABC):
    """分析上下文基类 - 管理分析流水线中的状态和结果"""

    def __init__(self, identifier: str):
        """
        初始化上下文

        Args:
            identifier: 上下文标识符（如 issue_key, report_type 等）
        """
        self.identifier = identifier
        self.results: Dict[str, Any] = {}
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.metadata: Dict[str, Any] = {
            'created_at': datetime.now().isoformat(),
            'identifier': identifier
        }
        self.timing: Dict[str, float] = {}

    def set_result(self, analyzer_name: str, result: Any) -> None:
        """
        设置分析器结果

        Args:
            analyzer_name: 分析器名称
            result: 分析结果
        """
        self.results[analyzer_name] = result

    def get_result(self, analyzer_name: str) -> Optional[Any]:
        """
        获取分析器结果

        Args:
            analyzer_name: 分析器名称

        Returns:
            分析结果，如果不存在返回 None
        """
        return self.results.get(analyzer_name)

    def get_all_results(self) -> Dict[str, Any]:
        """
        获取所有分析结果

        Returns:
            所有分析结果的字典
        """
        return self.results.copy()

    def add_warning(self, message: str) -> None:
        """
        添加警告信息

        Args:
            message: 警告消息
        """
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """
        添加错误信息

        Args:
            message: 错误消息
        """
        self.errors.append(message)

    def has_warnings(self) -> bool:
        """检查是否有警告"""
        return len(self.warnings) > 0

    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0

    def record_timing(self, analyzer_name: str, duration_ms: float) -> None:
        """
        记录分析器执行时间

        Args:
            analyzer_name: 分析器名称
            duration_ms: 执行时间（毫秒）
        """
        self.timing[analyzer_name] = duration_ms

    def get_timing(self, analyzer_name: str) -> Optional[float]:
        """
        获取分析器执行时间

        Args:
            analyzer_name: 分析器名称

        Returns:
            执行时间（毫秒），如果不存在返回 None
        """
        return self.timing.get(analyzer_name)

    def get_total_time(self) -> float:
        """
        获取总执行时间

        Returns:
            总执行时间（毫秒）
        """
        return sum(self.timing.values())

    def set_metadata(self, key: str, value: Any) -> None:
        """
        设置元数据

        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value

    def get_metadata(self, key: str) -> Optional[Any]:
        """
        获取元数据

        Args:
            key: 元数据键

        Returns:
            元数据值，如果不存在返回 None
        """
        return self.metadata.get(key)

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """
        获取上下文摘要（子类必须实现）

        Returns:
            上下文摘要字典
        """
        pass

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(identifier='{self.identifier}', "
                f"results={len(self.results)}, warnings={len(self.warnings)}, "
                f"errors={len(self.errors)})")
