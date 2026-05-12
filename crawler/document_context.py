"""
文档分析上下文模块 - 在文档分析流水线中传递状态
"""

from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from crawler.base_context import BaseContext


class DocumentContext(BaseContext):
    """文档分析上下文 - 存储文档分析过程中的中间结果和元数据"""

    def __init__(self, doc_path: str):
        """
        初始化文档分析上下文

        Args:
            doc_path: 文档路径
        """
        # 使用文档文件名作为标识符
        doc_name = Path(doc_path).stem
        super().__init__(doc_name)

        self.doc_path = doc_path
        self.sections_analyzed: List[str] = []
        self.metadata['llm_calls'] = 0
        self.metadata['vision_calls'] = 0
        self.metadata['total_sections'] = 0
        self.metadata['keywords_extracted'] = []

    def increment_llm_calls(self) -> None:
        """增加 LLM 调用计数"""
        self.metadata['llm_calls'] += 1

    def increment_vision_calls(self) -> None:
        """增加 Vision LLM 调用计数"""
        self.metadata['vision_calls'] += 1

    def add_section_result(self, section_id: str, result: Dict[str, Any]) -> None:
        """
        添加小节分析结果

        Args:
            section_id: 小节标识符
            result: 分析结果
        """
        self.sections_analyzed.append(section_id)
        self.set_result(section_id, result)

    def add_keywords(self, keywords: List[str]) -> None:
        """
        添加提取的关键词

        Args:
            keywords: 关键词列表
        """
        existing = self.metadata.get('keywords_extracted', [])
        # 去重并合并
        all_keywords = list(set(existing + keywords))
        self.metadata['keywords_extracted'] = all_keywords

    def set_total_sections(self, count: int) -> None:
        """
        设置总小节数

        Args:
            count: 小节总数
        """
        self.metadata['total_sections'] = count

    def get_sections_count(self) -> int:
        """
        获取已分析的小节数

        Returns:
            已分析的小节数
        """
        return len(self.sections_analyzed)

    def get_summary(self) -> Dict[str, Any]:
        """
        获取分析摘要

        Returns:
            包含所有结果和元数据的摘要字典
        """
        return {
            'doc_path': self.doc_path,
            'doc_name': self.identifier,
            'sections_analyzed': self.sections_analyzed,
            'sections_count': len(self.sections_analyzed),
            'total_sections': self.metadata.get('total_sections', 0),
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
