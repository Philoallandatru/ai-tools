"""
报告分析上下文模块 - 在报告分析流水线中传递状态
"""

from typing import Dict, Any
from datetime import datetime
from crawler.base_context import BaseContext


class ReportContext(BaseContext):
    """报告分析上下文 - 存储报告分析过程中的中间结果和元数据"""

    def __init__(self, report_data: Dict[str, Any]):
        """
        初始化报告分析上下文

        Args:
            report_data: 原始报告数据，包含 type, start_date, end_date, jira, confluence, summary
        """
        # 构建标识符：report_type_start_to_end
        report_type = report_data.get('type', 'unknown')
        start_date = report_data.get('start_date', 'unknown')
        end_date = report_data.get('end_date', 'unknown')
        identifier = f"{report_type}_{start_date}_to_{end_date}"

        super().__init__(identifier)
        self.report_data = report_data
        self.metadata['llm_calls'] = 0

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
            'report_type': self.report_data.get('type'),
            'start_date': self.report_data.get('start_date'),
            'end_date': self.report_data.get('end_date'),
            'results': self.results,
            'metadata': {
                **self.metadata,
                'end_time': datetime.now().isoformat(),
                'total_time_ms': self.get_total_time(),
                'warnings_count': len(self.warnings),
                'errors_count': len(self.errors)
            },
            'warnings': self.warnings,
            'errors': self.errors,
            'timing': self.timing
        }
