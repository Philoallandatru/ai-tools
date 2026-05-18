"""
根因分析器 - 使用 LLM 分析问题根因
"""

from typing import Dict, Any, Optional
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.prompt_templates import RootCausePromptTemplate


class RootCauseAnalyzer(ConfigurableAnalyzer):
    """根因分析器 - 分析问题的直接原因、深层原因和触发条件"""

    def get_name(self) -> str:
        return "root_cause"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行根因分析

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含根因分析结果的字典
        """
        # 构建提示词
        prompt = self._build_prompt(jira_data, context)

        # 调用 LLM (使用基类方法)
        response = self.call_llm(prompt, context, default_max_tokens=3000)

        # 解析响应
        result = self._parse_response(response)

        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建根因分析提示词（使用优化的模板）

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 使用基类的知识上下文格式化
        knowledge_context = self.format_knowledge_context(context)

        # 使用优化的模板
        return RootCausePromptTemplate.build(jira_data, knowledge_context)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的结果字典
        """
        # 使用基类的键值对提取方法
        fields = self.extract_key_value_pairs(response, ['直接原因', '深层原因', '触发条件'])

        result = {
            'direct_cause': fields.get('直接原因', ''),
            'deep_cause': fields.get('深层原因', ''),
            'trigger_condition': fields.get('触发条件', ''),
            'raw_response': response
        }

        # 如果没有提取到结构化信息，使用原始响应
        if not any([result['direct_cause'], result['deep_cause'], result['trigger_condition']]):
            result['summary'] = response.strip()

        return result
