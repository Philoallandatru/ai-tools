"""
评论分析器 - 分析 Jira 评论的时间线、决策和合理性
"""

from typing import Dict, Any, List
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output


class CommentAnalyzer(BaseAnalyzer):
    """评论分析器 - 分析评论的时间线、关键决策和合理性"""

    def __init__(self, llm_client: BaseLLMClient):
        """
        初始化评论分析器

        Args:
            llm_client: LLM 客户端
        """
        self.llm_client = llm_client

    def get_name(self) -> str:
        return "comments"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行评论分析

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含评论分析结果的字典
        """
        comments = jira_data.get('comments', [])

        if not comments:
            return {
                'has_comments': False,
                'comment_count': 0,
                'analysis': '该 Issue 没有评论'
            }

        # 分析每条评论
        comment_analyses = []
        for i, comment in enumerate(comments[:10], 1):  # 最多分析前 10 条评论
            analysis = self._analyze_single_comment(i, comment, jira_data, context)
            comment_analyses.append(analysis)
            context.increment_llm_calls()

        # 生成整体摘要
        summary = self._generate_summary(comment_analyses, jira_data)

        return {
            'has_comments': True,
            'comment_count': len(comments),
            'analyzed_count': len(comment_analyses),
            'comment_analyses': comment_analyses,
            'summary': summary
        }

    def _analyze_single_comment(
        self,
        index: int,
        comment: str,
        jira_data: Dict[str, Any],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """
        分析单条评论

        Args:
            index: 评论序号
            comment: 评论内容
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            评论分析结果
        """
        prompt = self._build_comment_prompt(index, comment, jira_data)
        response = self.llm_client.generate(prompt, max_tokens=600)

        # 清理输出
        response = clean_llm_output(response)

        return {
            'index': index,
            'comment_preview': comment[:200],
            'analysis': response.strip()
        }

    def _build_comment_prompt(self, index: int, comment: str, jira_data: Dict[str, Any]) -> str:
        """
        构建评论分析提示词

        Args:
            index: 评论序号
            comment: 评论内容
            jira_data: Jira 数据

        Returns:
            提示词字符串
        """
        prompt = f"""请分析以下 Jira Issue 的评论：

Issue: [{jira_data['key']}] {jira_data['title']}

评论 #{index}:
{comment[:1000]}

请从以下三个维度分析这条评论：
1. 时间线位置：这条评论在问题解决过程中处于什么阶段？（问题发现/根因定位/方案讨论/修复验证/总结回顾）
2. 关键决策：这条评论中是否包含重要的技术决策？如果有，是什么决策？
3. 合理性评估：这条评论中的分析或决策是否合理？有无明显问题？

请用简洁的语言回答，每个维度 1-2 句话。
"""
        return prompt

    def _generate_summary(self, comment_analyses: List[Dict[str, Any]], jira_data: Dict[str, Any]) -> str:
        """
        生成评论分析摘要

        Args:
            comment_analyses: 评论分析列表
            jira_data: Jira 数据

        Returns:
            摘要文本
        """
        if not comment_analyses:
            return "无评论可分析"

        # 简单的摘要生成
        total = len(comment_analyses)
        summary_lines = [
            f"共分析 {total} 条评论",
            "主要发现："
        ]

        # 提取关键信息（这里简化处理，实际可以用 LLM 生成更好的摘要）
        has_decisions = any('决策' in a['analysis'] for a in comment_analyses)
        if has_decisions:
            summary_lines.append("- 评论中包含重要技术决策")

        has_issues = any('问题' in a['analysis'] or '不合理' in a['analysis'] for a in comment_analyses)
        if has_issues:
            summary_lines.append("- 部分评论存在需要关注的问题")

        return '\n'.join(summary_lines)
