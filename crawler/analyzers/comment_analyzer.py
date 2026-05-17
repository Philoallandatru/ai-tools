"""
评论分析器 - 分析 Jira 评论的时间线、决策和合理性
"""

from typing import Dict, Any, List, Optional
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient


class CommentAnalyzer(ConfigurableAnalyzer):
    """评论分析器 - 分析评论的时间线、关键决策和合理性"""

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
        self.log_progress("开始分析评论...")

        comments = jira_data.get('comments', [])
        self.log_progress(f"找到 {len(comments)} 条评论")

        # 调试：打印前 3 条评论的预览
        if comments:
            print(f"[DEBUG] 评论预览:")
            for i, comment in enumerate(comments[:3], 1):
                preview = comment[:100].replace('\n', ' ')
                print(f"  评论 #{i}: {preview}...")

        if not comments:
            return {
                'has_comments': False,
                'comment_count': 0,
                'analysis': '该 Issue 没有评论'
            }

        # 分析每条评论（使用并行调用）
        comments_to_analyze = comments[:10]  # 最多分析前 10 条
        self.log_progress(f"准备分析 {len(comments_to_analyze)} 条评论...")

        # 构建所有 prompts
        prompts = [
            self._build_comment_prompt(i + 1, comment, jira_data)
            for i, comment in enumerate(comments_to_analyze)
        ]

        # 并行调用 LLM
        responses = self.call_llm_parallel(
            prompts,
            context,
            max_workers=3,
            default_max_tokens=4000,
            progress_callback=lambda curr, total: self.log_step(curr, total, "分析评论")
        )

        # 构建分析结果
        comment_analyses = [
            {
                'index': i + 1,
                'comment_preview': comment[:200],
                'analysis': response.strip()
            }
            for i, (comment, response) in enumerate(zip(comments_to_analyze, responses))
        ]

        # 生成整体摘要
        self.log_progress("生成摘要...")
        summary = self._generate_summary(comment_analyses, jira_data)
        self.log_progress("分析完成")

        return {
            'has_comments': True,
            'comment_count': len(comments),
            'analyzed_count': len(comment_analyses),
            'comment_analyses': comment_analyses,
            'summary': summary
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

{self.build_chinese_requirements()}
- 用简洁的语言回答，每个维度 1-2 句话
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

        # 提取关键信息
        has_decisions = any('决策' in a['analysis'] for a in comment_analyses)
        if has_decisions:
            summary_lines.append("- 评论中包含重要技术决策")

        has_issues = any('问题' in a['analysis'] or '不合理' in a['analysis'] for a in comment_analyses)
        if has_issues:
            summary_lines.append("- 部分评论存在需要关注的问题")

        return '\n'.join(summary_lines)
