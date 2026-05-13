"""
根因分析器 - 使用 LLM 分析问题根因
"""

from typing import Dict, Any, Optional
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output, extract_structured_response


class RootCauseAnalyzer(BaseAnalyzer):
    """根因分析器 - 分析问题的直接原因、深层原因和触发条件"""

    def __init__(self, llm_client: BaseLLMClient, config: Optional[Dict[str, Any]] = None):
        """
        初始化根因分析器

        Args:
            llm_client: LLM 客户端
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}

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

        # 调用 LLM
        context.increment_llm_calls()
        max_tokens = self.config.get('max_tokens', 3000)
        response = self.llm_client.generate(prompt, max_tokens=max_tokens)

        # 清理输出
        response = clean_llm_output(response)

        # 解析响应
        result = self._parse_response(response)

        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建根因分析提示词

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 获取知识检索结果作为上下文
        knowledge = context.get_result('knowledge')
        knowledge_context = ""

        if knowledge and knowledge.get('wiki_concepts'):
            knowledge_context = "\n相关技术知识:\n"
            for concept in knowledge['wiki_concepts'][:3]:
                knowledge_context += f"- {concept['keyword']}: {concept['content'][:200]}\n"

        prompt = f"""请对以下 Jira Issue 进行根因分析：

Issue: [{jira_data['key']}] {jira_data['title']}
状态: {jira_data['status']}
优先级: {jira_data['priority']}

描述:
{jira_data['description'][:1000]}

{knowledge_context}

请从以下三个层面分析问题根因：
1. 直接原因：问题的表面原因是什么？
2. 深层原因：导致这个问题的底层技术原因是什么？
3. 触发条件：在什么条件下会触发这个问题？

要求：
- 必须用中文回答
- 每个层面用 1-2 句话简洁回答
- 直接输出分析结果，不要输出思考过程
- 不要使用 <think> 标签
- 不要输出 JSON 格式
- 按照以下格式回答：

直接原因: [你的分析]
深层原因: [你的分析]
触发条件: [你的分析]
"""
        return prompt

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的结果字典
        """
        import re

        result = {
            'direct_cause': '',
            'deep_cause': '',
            'trigger_condition': '',
            'raw_response': response
        }

        # 尝试提取结构化信息
        direct_match = re.search(r'直接原因[：:]\s*(.+?)(?=\n|深层原因|触发条件|$)', response, re.DOTALL)
        deep_match = re.search(r'深层原因[：:]\s*(.+?)(?=\n|触发条件|$)', response, re.DOTALL)
        trigger_match = re.search(r'触发条件[：:]\s*(.+?)(?=\n|$)', response, re.DOTALL)

        if direct_match:
            result['direct_cause'] = direct_match.group(1).strip()
        if deep_match:
            result['deep_cause'] = deep_match.group(1).strip()
        if trigger_match:
            result['trigger_condition'] = trigger_match.group(1).strip()

        # 如果没有提取到结构化信息，使用原始响应
        if not any([result['direct_cause'], result['deep_cause'], result['trigger_condition']]):
            result['summary'] = response.strip()

        return result
