"""
行动建议生成器 - 基于分析结果生成行动建议
"""

from typing import Dict, Any, Optional
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output


class ActionRecommender(BaseAnalyzer):
    """行动建议生成器 - 综合所有分析结果生成短期、中期、长期建议"""

    def __init__(self, llm_client: BaseLLMClient, config: Optional[Dict[str, Any]] = None):
        """
        初始化行动建议生成器

        Args:
            llm_client: LLM 客户端
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}

    def get_name(self) -> str:
        return "actions"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        生成行动建议

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含行动建议的字典
        """
        # 构建提示词（综合前面所有分析结果）
        prompt = self._build_prompt(jira_data, context)

        # 调用 LLM
        context.increment_llm_calls()
        max_tokens = self.config.get('max_tokens', 2000)
        response = self.llm_client.generate(prompt, max_tokens=max_tokens)

        # 清理输出
        response = clean_llm_output(response)

        # 解析响应
        result = self._parse_response(response)

        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建行动建议提示词

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 收集前面的分析结果
        root_cause = context.get_result('root_cause')
        similar_jira = context.get_result('similar_jira')
        closed_loop = context.get_result('closed_loop')

        # 构建上下文信息
        context_info = []

        if root_cause:
            context_info.append(f"根因分析: {root_cause.get('direct_cause', 'N/A')}")

        if similar_jira and similar_jira.get('similar_issues'):
            similar_count = len(similar_jira['similar_issues'])
            context_info.append(f"发现 {similar_count} 个类似问题")

        if closed_loop:
            is_closed = closed_loop.get('is_closed', False)
            context_info.append(f"闭环状态: {'已闭环' if is_closed else '未闭环'}")

        context_text = "\n".join(context_info) if context_info else "无额外上下文"

        prompt = f"""请基于以下 Jira Issue 的分析结果，提供行动建议：

Issue: [{jira_data['key']}] {jira_data['title']}
状态: {jira_data['status']}
优先级: {jira_data['priority']}

分析上下文:
{context_text}

描述:
{jira_data['description'][:800]}

请从以下三个时间维度提供行动建议：
1. 短期行动（1-2 周内）：立即需要采取的措施
2. 中期行动（1-2 个月内）：需要规划和实施的改进
3. 长期行动（3 个月以上）：系统性的优化和预防措施

要求：
- 必须用中文回答
- 每个维度提供 2-3 条具体可执行的建议
- 使用列表格式（数字或破折号开头）
- 直接输出建议，不要输出思考过程
- 不要使用 <think> 标签
- 按照以下格式回答：

短期行动（1-2 周内）：
1. [具体建议]
2. [具体建议]

中期行动（1-2 个月内）：
1. [具体建议]
2. [具体建议]

长期行动（3 个月以上）：
1. [具体建议]
2. [具体建议]
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

        # 额外清理：移除代码块标记
        response = re.sub(r'^```\s*\n', '', response, flags=re.MULTILINE)
        response = re.sub(r'\n```\s*$', '', response, flags=re.MULTILINE)
        response = re.sub(r'```', '', response)

        # 移除占位符行（包含 [具体建议] 的行）
        lines = response.split('\n')
        cleaned_lines = [line for line in lines if '[具体建议]' not in line]
        response = '\n'.join(cleaned_lines)

        result = {
            'short_term': [],
            'medium_term': [],
            'long_term': [],
            'raw_response': response
        }

        # 提取短期行动（支持带括号的时间说明）
        short_match = re.search(
            r'短期行动[^：:]*[：:](.+?)(?=中期行动|长期行动|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if short_match:
            result['short_term'] = self._extract_action_items(short_match.group(1))

        # 提取中期行动（支持带括号的时间说明）
        medium_match = re.search(
            r'中期行动[^：:]*[：:](.+?)(?=长期行动|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if medium_match:
            result['medium_term'] = self._extract_action_items(medium_match.group(1))

        # 提取长期行动（支持带括号的时间说明）
        long_match = re.search(
            r'长期行动[^：:]*[：:](.+?)$',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if long_match:
            result['long_term'] = self._extract_action_items(long_match.group(1))

        return result

    def _extract_action_items(self, text: str) -> list:
        """
        从文本中提取行动项

        Args:
            text: 文本内容

        Returns:
            行动项列表
        """
        import re

        # 提取列表项（支持数字、破折号、星号等）
        items = re.findall(r'(?:^|\n)\s*(?:\d+[.、)]|[-*•])\s*(.+?)(?=\n|$)', text)

        # 清理并过滤
        items = [item.strip() for item in items if item.strip()]

        return items[:5]  # 最多返回 5 条
