"""
行动建议生成器 - 基于分析结果生成行动建议
"""

from typing import Dict, Any, Optional
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.prompt_templates import ActionRecommenderPromptTemplate


class ActionRecommender(ConfigurableAnalyzer):
    """行动建议生成器 - 综合所有分析结果生成短期、中期、长期建议"""

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

        # 调用 LLM (使用基类方法)
        response = self.call_llm(prompt, context, default_max_tokens=2000)

        # 解析响应
        result = self._parse_response(response)

        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建行动建议提示词（使用优化的模板）

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 收集前面的分析结果（精简版）
        root_cause = context.get_result('root_cause')
        similar_jira = context.get_result('similar_jira')
        closed_loop = context.get_result('closed_loop')
        code_coverage = context.get_result('code_coverage')

        # 构建上下文摘要
        context_info = []

        if root_cause:
            context_info.append(f"根因: {root_cause.get('direct_cause', 'N/A')[:100]}")

        if code_coverage:
            files = code_coverage.get('code_references', {}).get('files', [])
            if files:
                context_info.append(f"涉及文件: {', '.join(files[:3])}")

        if similar_jira and similar_jira.get('similar_issues'):
            similar_count = len(similar_jira['similar_issues'])
            context_info.append(f"类似问题: {similar_count}个")

        if closed_loop:
            is_closed = closed_loop.get('is_closed', False)
            context_info.append(f"闭环: {'是' if is_closed else '否'}")

        context_text = "\n".join(context_info) if context_info else ""

        # 使用优化的模板
        return ActionRecommenderPromptTemplate.build(jira_data, context_text)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的结果字典
        """
        import re

        # 额外清理：移除代码块标记和占位符
        response = re.sub(r'^```\s*\n', '', response, flags=re.MULTILINE)
        response = re.sub(r'\n```\s*$', '', response, flags=re.MULTILINE)
        response = re.sub(r'```', '', response)

        # 移除占位符行
        lines = response.split('\n')
        cleaned_lines = [line for line in lines if '[具体建议]' not in line]
        response = '\n'.join(cleaned_lines)

        result = {
            'short_term': [],
            'medium_term': [],
            'long_term': [],
            'raw_response': response
        }

        # 提取短期行动
        short_match = re.search(
            r'短期行动[^：:]*[：:](.+?)(?=中期行动|长期行动|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if short_match:
            result['short_term'] = self._parse_structured_actions(short_match.group(1))

        # 提取中期行动
        medium_match = re.search(
            r'中期行动[^：:]*[：:](.+?)(?=长期行动|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if medium_match:
            result['medium_term'] = self._parse_structured_actions(medium_match.group(1))

        # 提取长期行动
        long_match = re.search(
            r'长期行动[^：:]*[：:](.+?)$',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if long_match:
            result['long_term'] = self._parse_structured_actions(long_match.group(1))

        return result

    def _parse_structured_actions(self, text: str) -> list:
        """
        解析结构化的行动建议

        Args:
            text: 包含行动建议的文本

        Returns:
            结构化的行动建议列表
        """
        import re

        actions = []

        # 匹配每个行动项（以数字开头，可能包含优先级标签）
        # 格式：1. [P0] 标题
        action_pattern = r'^\s*(\d+)\.\s*(\[P[0-2]\])?\s*(.+?)(?=^\s*\d+\.\s*(?:\[P[0-2]\])?\s*\S|$)'
        matches = re.finditer(action_pattern, text, re.MULTILINE | re.DOTALL)

        for match in matches:
            priority = match.group(2).strip('[]') if match.group(2) else 'P1'
            content = match.group(3).strip()

            # 解析标题（第一行）
            lines = content.split('\n')
            title = lines[0].strip()

            # 解析详细信息
            location = ''
            effort = ''
            steps = []
            acceptance = []

            in_steps = False
            in_acceptance = False

            for line in lines[1:]:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # 提取位置
                if line.startswith('- 位置：') or line.startswith('- 位置:'):
                    location = re.sub(r'^- 位置[：:]\s*', '', line)
                    in_steps = False
                    in_acceptance = False

                # 提取工作量
                elif line.startswith('- 工作量：') or line.startswith('- 工作量:'):
                    effort = re.sub(r'^- 工作量[：:]\s*', '', line)
                    in_steps = False
                    in_acceptance = False

                # 提取步骤标题
                elif line.startswith('- 步骤：') or line.startswith('- 步骤:'):
                    in_steps = True
                    in_acceptance = False

                # 提取验收标准标题
                elif line.startswith('- 验收标准：') or line.startswith('- 验收标准:'):
                    in_steps = False
                    in_acceptance = True

                # 提取步骤子项（数字列表）
                elif in_steps and re.match(r'^\d+\.\s+', line):
                    step = re.sub(r'^\d+\.\s+', '', line)
                    steps.append(step)

                # 提取验收标准子项（破折号列表）
                elif in_acceptance and line.startswith('- '):
                    criterion = re.sub(r'^- ', '', line)
                    acceptance.append(criterion)

            # 如果没有解析到结构化信息，使用简单格式
            if not location and not effort and not steps and not acceptance:
                # 简单格式：只有标题
                actions.append({
                    'priority': priority,
                    'title': title,
                    'action': title  # 兼容旧格式
                })
            else:
                # 结构化格式
                actions.append({
                    'priority': priority,
                    'title': title,
                    'action': title,  # 兼容旧格式
                    'location': location,
                    'effort': effort,
                    'steps': steps,
                    'acceptance_criteria': acceptance
                })

        # 如果没有匹配到结构化格式，回退到简单列表提取
        if not actions:
            simple_actions = self.extract_list_items(text)
            # 转换为字典格式
            actions = [{'priority': 'P1', 'title': action, 'action': action} for action in simple_actions]

        return actions
