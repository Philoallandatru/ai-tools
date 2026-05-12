"""
统一分析器模块 - 所有分析器的统一基础架构
"""

import time
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from crawler.base_context import BaseContext
from crawler.analyzers.base import BaseAnalyzer
from crawler.llm_client import BaseLLMClient


class UnifiedAnalyzer(ABC):
    """
    统一分析器基类 - 提供通用的分析流水线管理

    所有分析器（JiraDeepAnalyzer, ReportAnalyzer, DocAnalyzer）都应继承此类
    """

    def __init__(self, llm_client: BaseLLMClient):
        """
        初始化统一分析器

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm_client = llm_client
        self.pipeline: List[BaseAnalyzer] = []

    def register_analyzer(self, analyzer: BaseAnalyzer) -> None:
        """
        注册分析器到流水线

        Args:
            analyzer: 分析器实例
        """
        self.pipeline.append(analyzer)

    def clear_pipeline(self) -> None:
        """清空分析流水线"""
        self.pipeline.clear()

    def get_pipeline(self) -> List[BaseAnalyzer]:
        """
        获取当前流水线

        Returns:
            分析器列表
        """
        return self.pipeline.copy()

    @abstractmethod
    def analyze(self, data: Dict[str, Any], context: Optional[BaseContext] = None) -> Dict[str, Any]:
        """
        执行分析流水线（子类必须实现）

        Args:
            data: 输入数据
            context: 分析上下文（可选）

        Returns:
            分析结果字典
        """
        pass

    def execute_pipeline(
        self,
        data: Dict[str, Any],
        context: BaseContext,
        stop_on_error: bool = False
    ) -> BaseContext:
        """
        执行分析流水线的通用逻辑

        Args:
            data: 输入数据
            context: 分析上下文
            stop_on_error: 是否在遇到错误时停止（默认 False，继续执行）

        Returns:
            更新后的分析上下文

        Raises:
            RuntimeError: 当 stop_on_error=True 且分析器失败时
        """
        for analyzer in self.pipeline:
            analyzer_name = analyzer.get_name()
            start_time = time.time()

            try:
                result = analyzer.analyze(data, context)
                context.set_result(analyzer_name, result)

                duration_ms = (time.time() - start_time) * 1000
                context.record_timing(analyzer_name, duration_ms)

            except Exception as e:
                error_msg = f"{analyzer_name} 分析失败: {str(e)}"
                context.add_error(error_msg)

                if stop_on_error:
                    raise RuntimeError(error_msg) from e
                else:
                    # 记录警告并继续
                    context.add_warning(error_msg)
                    print(f"   ⚠ 警告: {error_msg}")

        return context

    def get_llm_client(self) -> BaseLLMClient:
        """
        获取 LLM 客户端

        Returns:
            LLM 客户端实例
        """
        return self.llm_client

    def set_llm_client(self, llm_client: BaseLLMClient) -> None:
        """
        设置 LLM 客户端

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm_client = llm_client

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}("
                f"llm_client={type(self.llm_client).__name__}, "
                f"pipeline_size={len(self.pipeline)})")
