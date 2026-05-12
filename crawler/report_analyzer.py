"""
报告分析器 - 主控制器
"""

from typing import Dict, Any, Optional
from crawler.report_context import ReportContext
from crawler.unified_analyzer import UnifiedAnalyzer
from crawler.llm_client import BaseLLMClient, LLMClientFactory


class ReportAnalyzer(UnifiedAnalyzer):
    """报告分析器 - 协调报告分析流水线"""

    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[BaseLLMClient] = None):
        """
        初始化报告分析器

        Args:
            config: 配置字典（包含 report_analysis 配置）
            llm_client: LLM 客户端（如果为 None，从配置创建）
        """
        self.config = config or {}
        self.report_config = self.config.get('report_analysis', {})

        # 创建 LLM 客户端
        if llm_client:
            llm = llm_client
        else:
            llm_config = self.config.get('llm', {})
            llm = LLMClientFactory.create_from_config(llm_config)

        super().__init__(llm)

    def analyze(self, report_data: Dict[str, Any], context: Optional[ReportContext] = None) -> Dict[str, Any]:
        """
        执行完整报告分析流水线

        Args:
            report_data: 报告数据字典，包含 type, start_date, end_date, jira, confluence, summary
            context: 报告上下文（可选）

        Returns:
            分析结果字典，包含 summary, insights, risks 等

        Raises:
            RuntimeError: 分析过程中发生错误
        """
        # 检查是否启用分析
        if not self.report_config.get('enabled', True):
            return {}

        # 创建分析上下文
        if context is None:
            context = ReportContext(report_data)

        # 执行分析流水线（使用统一的 execute_pipeline，不在错误时停止）
        context = self.execute_pipeline(report_data, context, stop_on_error=False)

        return context.results

    def is_enabled(self) -> bool:
        """
        检查报告分析是否启用

        Returns:
            True 如果启用，否则 False
        """
        return self.report_config.get('enabled', True)

    def get_analyzer_config(self, analyzer_name: str) -> Dict[str, Any]:
        """
        获取特定分析器的配置

        Args:
            analyzer_name: 分析器名称（如 'summary', 'insights', 'risks'）

        Returns:
            分析器配置字典
        """
        analyzers_config = self.report_config.get('analyzers', {})
        return analyzers_config.get(analyzer_name, {})
