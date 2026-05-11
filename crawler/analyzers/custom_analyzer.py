"""
自定义分析器 - 配置驱动的 LLM 分析器
"""

import re
from typing import Dict, Any, Optional
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output


class CustomAnalyzer(BaseAnalyzer):
    """配置驱动的自定义分析器"""

    def __init__(self, config: Dict[str, Any], llm_client: BaseLLMClient):
        """
        初始化自定义分析器

        Args:
            config: 单个自定义分析器的配置字典
            llm_client: LLM 客户端
        """
        self.config = config
        self.llm_client = llm_client
        self.analyzer_name = config['name']
        self.prompt_template = config['prompt']
        self.context_config = config.get('context', {})
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', None)

    def get_name(self) -> str:
        return f"custom_{self._slugify(self.analyzer_name)}"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """执行自定义分析"""
        # 1. 构建 prompt（变量替换 + 上下文注入）
        prompt = self._build_prompt(jira_data, context)

        # 2. 调用 LLM
        context.increment_llm_calls()
        response = self.llm_client.generate(
            prompt,
            max_tokens=self.max_tokens
        )

        # 3. 清理输出
        cleaned_response = clean_llm_output(response)

        # 4. 返回结果
        return {
            'analyzer_name': self.analyzer_name,
            'result': cleaned_response,
            'raw_response': response,
            'prompt_used': prompt
        }

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """构建 prompt：变量替换 + 上下文注入"""
        prompt = self.prompt_template

        # 1. 替换 Jira 字段变量
        prompt = self._replace_jira_variables(prompt, jira_data)

        # 2. 替换上下文变量
        prompt = self._replace_context_variables(prompt, context)

        return prompt

    def _replace_jira_variables(self, prompt: str, jira_data: Dict[str, Any]) -> str:
        """替换 Jira 字段变量"""
        replacements = {
            '{key}': jira_data.get('key', ''),
            '{title}': jira_data.get('title', ''),
            '{description}': jira_data.get('description', '')[:1000],
            '{status}': jira_data.get('status', ''),
            '{priority}': jira_data.get('priority', ''),
            '{type}': jira_data.get('type', ''),
            '{assignee}': jira_data.get('assignee', ''),
        }

        for var, value in replacements.items():
            prompt = prompt.replace(var, value)

        return prompt

    def _replace_context_variables(self, prompt: str, context: AnalysisContext) -> str:
        """替换上下文变量"""
        context_replacements = {}

        if self.context_config.get('include_knowledge', False):
            context_replacements['{knowledge_context}'] = self._format_knowledge_context(context)

        if self.context_config.get('include_root_cause', False):
            context_replacements['{root_cause_context}'] = self._format_root_cause_context(context)

        if self.context_config.get('include_similar_jira', False):
            context_replacements['{similar_jira_context}'] = self._format_similar_jira_context(context)

        if self.context_config.get('include_comments', False):
            context_replacements['{comments_context}'] = self._format_comments_context(context)

        # 替换已配置的上下文变量
        for var, value in context_replacements.items():
            prompt = prompt.replace(var, value)

        # 移除未配置的上下文变量（替换为空字符串）
        for var in ['{knowledge_context}', '{root_cause_context}',
                    '{similar_jira_context}', '{comments_context}']:
            if var not in context_replacements:
                prompt = prompt.replace(var, '')

        return prompt

    def _format_knowledge_context(self, context: AnalysisContext) -> str:
        """格式化知识检索上下文"""
        knowledge = context.get_result('knowledge')
        if not knowledge:
            return ""

        lines = ["\n相关技术知识:"]

        keywords = knowledge.get('keywords', [])
        if keywords:
            lines.append(f"关键词: {', '.join(keywords[:5])}")

        wiki_concepts = knowledge.get('wiki_concepts', [])
        for concept in wiki_concepts[:3]:
            keyword = concept.get('keyword', '')
            content = concept.get('content', '')[:200]
            lines.append(f"- {keyword}: {content}")

        return '\n'.join(lines)

    def _format_root_cause_context(self, context: AnalysisContext) -> str:
        """格式化根因分析上下文"""
        root_cause = context.get_result('root_cause')
        if not root_cause:
            return ""

        lines = ["\n根因分析:"]

        direct = root_cause.get('direct_cause', '')
        if direct:
            lines.append(f"直接原因: {direct}")

        deep = root_cause.get('deep_cause', '')
        if deep:
            lines.append(f"深层原因: {deep}")

        trigger = root_cause.get('trigger_condition', '')
        if trigger:
            lines.append(f"触发条件: {trigger}")

        return '\n'.join(lines)

    def _format_similar_jira_context(self, context: AnalysisContext) -> str:
        """格式化相似问题上下文"""
        similar = context.get_result('similar_jira')
        if not similar:
            return ""

        issues = similar.get('similar_issues', [])
        if not issues:
            return ""

        lines = ["\n相似问题:"]
        for issue in issues[:3]:
            key = issue.get('key', '')
            title = issue.get('title', '')
            score = issue.get('similarity_score', 0)
            lines.append(f"- [{key}] {title} (相似度: {score})")

        return '\n'.join(lines)

    def _format_comments_context(self, context: AnalysisContext) -> str:
        """格式化评论分析上下文"""
        comments = context.get_result('comments')
        if not comments:
            return ""

        lines = ["\n评论分析:"]

        timeline = comments.get('timeline_position', '')
        if timeline:
            lines.append(f"时间线位置: {timeline}")

        decisions = comments.get('key_decisions', [])
        if decisions:
            lines.append(f"关键决策: {', '.join(decisions[:3])}")

        return '\n'.join(lines)

    def _slugify(self, name: str) -> str:
        """将名称转换为 slug（用于 analyzer key）"""
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug
