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

        # 智能采样：根据评论数量选择合适的分析策略
        comments_to_analyze, selected_indices = self._smart_sample_comments(comments)
        self.log_progress(f"准备分析 {len(comments_to_analyze)} 条评论（共 {len(comments)} 条）...")

        # 构建所有 prompts
        prompts = [
            self._build_comment_prompt(idx + 1, comment, jira_data)
            for idx, comment in zip(selected_indices, comments_to_analyze)
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
                'index': idx + 1,
                'comment_preview': comment[:200],
                'analysis': response.strip()
            }
            for idx, comment, response in zip(selected_indices, comments_to_analyze, responses)
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

    def _smart_sample_comments(self, comments: List[str]) -> tuple[List[str], List[int]]:
        """
        智能采样评论 - 混合策略

        策略：
        - ≤10条：全部分析
        - 11-30条：前5条 + 后5条
        - 31-50条：前5条 + 关键词匹配5条 + 后5条
        - >50条：前3条 + 关键词匹配10条 + 后3条

        Args:
            comments: 所有评论列表

        Returns:
            (选中的评论列表, 选中的索引列表)
        """
        total = len(comments)

        # ≤10条：全部分析
        if total <= 10:
            return comments, list(range(total))

        # 11-30条：前5条 + 后5条
        if total <= 30:
            indices = list(range(5)) + list(range(total - 5, total))
            return [comments[i] for i in indices], indices

        # 31-50条：前5条 + 关键词匹配5条 + 后5条
        if total <= 50:
            head_indices = list(range(5))
            tail_indices = list(range(total - 5, total))

            # 从中间部分找关键词匹配的评论
            middle_start = 5
            middle_end = total - 5
            keyword_indices = self._find_keyword_comments(
                comments[middle_start:middle_end],
                middle_start,
                max_count=5
            )

            # 合并并去重
            all_indices = sorted(set(head_indices + keyword_indices + tail_indices))
            return [comments[i] for i in all_indices], all_indices

        # >50条：前3条 + 关键词匹配10条 + 后3条
        head_indices = list(range(3))
        tail_indices = list(range(total - 3, total))

        # 从中间部分找关键词匹配的评论
        middle_start = 3
        middle_end = total - 3
        keyword_indices = self._find_keyword_comments(
            comments[middle_start:middle_end],
            middle_start,
            max_count=10
        )

        # 合并并去重
        all_indices = sorted(set(head_indices + keyword_indices + tail_indices))
        return [comments[i] for i in all_indices], all_indices

    def _find_keyword_comments(self, comments: List[str], offset: int, max_count: int) -> List[int]:
        """
        从评论中找出包含关键词的评论

        关键词优先级：
        1. 根因相关：根因、root cause、原因、cause
        2. 修复相关：修复、fix、patch、PR、commit
        3. 验证相关：测试、验证、通过、test、verify
        4. 决策相关：决定、建议、方案、决策、decision

        Args:
            comments: 评论列表
            offset: 索引偏移量
            max_count: 最多返回数量

        Returns:
            选中的评论索引列表（绝对索引）
        """
        # 定义关键词及其权重
        keywords = {
            # 根因相关（权重3）
            '根因': 3, 'root cause': 3, '原因': 3, 'cause': 3,
            # 修复相关（权重3）
            '修复': 3, 'fix': 3, 'patch': 3, 'PR': 3, 'commit': 3,
            # 验证相关（权重2）
            '测试': 2, '验证': 2, '通过': 2, 'test': 2, 'verify': 2,
            # 决策相关（权重2）
            '决定': 2, '建议': 2, '方案': 2, '决策': 2, 'decision': 2,
        }

        # 计算每条评论的得分
        scored_comments = []
        for i, comment in enumerate(comments):
            comment_lower = comment.lower()
            score = 0
            matched_keywords = []

            for keyword, weight in keywords.items():
                if keyword.lower() in comment_lower:
                    score += weight
                    matched_keywords.append(keyword)

            if score > 0:
                scored_comments.append({
                    'index': offset + i,
                    'score': score,
                    'keywords': matched_keywords
                })

        # 按得分排序，取前 max_count 个
        scored_comments.sort(key=lambda x: x['score'], reverse=True)
        selected = scored_comments[:max_count]

        # 返回索引列表（按原始顺序）
        indices = sorted([item['index'] for item in selected])

        # 调试信息
        if selected:
            print(f"[DEBUG] 关键词匹配: 从 {len(comments)} 条中选出 {len(selected)} 条")
            for item in selected[:3]:  # 只打印前3个
                print(f"  - 索引 {item['index']}: 得分 {item['score']}, 关键词 {item['keywords'][:3]}")

        return indices

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
