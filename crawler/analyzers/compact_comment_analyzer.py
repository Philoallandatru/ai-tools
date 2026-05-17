"""
精简评论分析器 - 用简洁格式分析 Jira 评论

改进点：
1. 精简格式：每条评论 2-3 行，去除冗长的标签
2. 时间线视图：按时间组织评论，清晰展示问题解决过程
3. 关键信息提取：只提取有价值的信息（决策、发现、验证）
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext


class CompactCommentAnalyzer(ConfigurableAnalyzer):
    """精简评论分析器 - 用简洁格式分析评论"""

    def get_name(self) -> str:
        return "comments_compact"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行精简评论分析

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含精简评论分析结果的字典
        """
        comments = jira_data.get('comments', [])

        if not comments:
            return {
                'has_comments': False,
                'comment_count': 0,
                'compact_analysis': [],
                'timeline_view': None
            }

        # 分析评论（最多 10 条）
        comments_to_analyze = comments[:10]

        # 构建提示词
        prompt = self._build_compact_prompt(comments_to_analyze, jira_data)

        # 调用 LLM
        response = self.call_llm(prompt, context, default_max_tokens=2000)

        # 解析响应
        result = self._parse_response(response, comments_to_analyze)

        return result

    def _build_compact_prompt(self, comments: List[str], jira_data: Dict[str, Any]) -> str:
        """
        构建精简分析提示词

        Args:
            comments: 评论列表
            jira_data: Jira 数据

        Returns:
            提示词字符串
        """
        # 格式化评论
        comments_text = []
        for i, comment in enumerate(comments, 1):
            # 限制每条评论长度
            comment_preview = comment[:500] if len(comment) > 500 else comment
            comments_text.append(f"评论 #{i}:\n{comment_preview}\n")

        comments_str = "\n".join(comments_text)

        prompt = f"""请用精简格式分析以下 Jira Issue 的评论。

Issue: [{jira_data['key']}] {jira_data['title']}
状态: {jira_data['status']}

评论内容:
{comments_str}

请为每条评论生成精简分析，格式如下：

**评论 #N** [角色 - 姓名]:
评论摘要（1 句话概括评论内容）
→ 关键点（问题发现/技术决策/修复实施/效果验证/建议改进等，1 句话）

**要求**:
1. 每条评论最多 3 行（标题 + 摘要 + 关键点）
2. 摘要要简洁，提取核心信息
3. 关键点用 → 开头，标注评论的价值（是发现问题、提出方案、实施修复还是验证效果）
4. 如果评论没有实质内容，可以省略关键点
5. 从评论中提取角色和姓名（如 [SV - Li Qiang]、[FW - Zhao Li]）

{self.build_chinese_requirements()}
- 去除冗长的分析和套话
- 只保留有价值的信息

请按照上述格式输出所有评论的分析。
"""
        return prompt

    def _parse_response(self, response: str, comments: List[str]) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本
            comments: 原始评论列表

        Returns:
            解析后的结果字典
        """
        # 提取每条评论的分析
        compact_analyses = []

        # 按 **评论 #N** 分割
        pattern = r'\*\*评论 #(\d+)\*\*\s*(.+?)(?=\*\*评论 #|\Z)'
        matches = re.finditer(pattern, response, re.DOTALL)

        for match in matches:
            index = int(match.group(1))
            content = match.group(2).strip()

            # 解析角色和姓名
            role_match = re.search(r'\[([^\]]+)\]', content)
            role = role_match.group(1) if role_match else '未知'

            # 提取摘要和关键点
            lines = content.split('\n')
            summary = ''
            key_point = ''

            for line in lines:
                line = line.strip()
                if not line or line.startswith('['):
                    continue
                if line.startswith('→'):
                    key_point = line[1:].strip()
                elif not summary:
                    # 第一行非空行作为摘要
                    summary = line

            compact_analyses.append({
                'index': index,
                'role': role,
                'summary': summary,
                'key_point': key_point,
                'original_comment': comments[index - 1] if index <= len(comments) else ''
            })

        # 生成时间线视图
        timeline_view = self._generate_timeline_view(compact_analyses)

        return {
            'has_comments': True,
            'comment_count': len(comments),
            'analyzed_count': len(compact_analyses),
            'compact_analysis': compact_analyses,
            'timeline_view': timeline_view,
            'raw_response': response
        }

    def _generate_timeline_view(self, compact_analyses: List[Dict[str, Any]]) -> Optional[str]:
        """
        生成时间线视图

        Args:
            compact_analyses: 精简分析列表

        Returns:
            时间线视图文本
        """
        if not compact_analyses:
            return None

        # 按阶段分组
        stages = {
            '问题发现': [],
            '根因定位': [],
            '方案讨论': [],
            '修复实施': [],
            '效果验证': [],
            '后续改进': []
        }

        # 根据关键点分类
        for analysis in compact_analyses:
            key_point = analysis.get('key_point', '').lower()
            role = analysis.get('role', '')
            summary = analysis.get('summary', '')

            # 提取时间（如果有）
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', analysis.get('original_comment', ''))
            time_str = time_match.group(1) if time_match else ''

            entry = f"  [{role}] {summary}"
            if time_str:
                entry = f"{time_str} - {entry}"

            # 分类到阶段
            if any(keyword in key_point for keyword in ['发现', '问题', '现象', '报告']):
                stages['问题发现'].append(entry)
            elif any(keyword in key_point for keyword in ['根因', '定位', '分析', '原因']):
                stages['根因定位'].append(entry)
            elif any(keyword in key_point for keyword in ['方案', '建议', '讨论', '决策']):
                stages['方案讨论'].append(entry)
            elif any(keyword in key_point for keyword in ['修复', '实施', '实现', '完成']):
                stages['修复实施'].append(entry)
            elif any(keyword in key_point for keyword in ['验证', '测试', '效果', '成功率']):
                stages['效果验证'].append(entry)
            elif any(keyword in key_point for keyword in ['改进', '优化', '后续']):
                stages['后续改进'].append(entry)
            else:
                # 默认放到方案讨论
                stages['方案讨论'].append(entry)

        # 生成时间线文本
        timeline_lines = []
        for stage, entries in stages.items():
            if entries:
                timeline_lines.append(f"\n{stage}:")
                timeline_lines.extend(entries)

        return '\n'.join(timeline_lines) if timeline_lines else None

    def _extract_time_from_comment(self, comment: str) -> Optional[str]:
        """
        从评论中提取时间

        Args:
            comment: 评论内容

        Returns:
            时间字符串，如果未找到返回 None
        """
        # 尝试多种时间格式
        patterns = [
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',  # 2026-05-02 08:00
            r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})',  # 2026/05/02 08:00
            r'(\d{2}:\d{2})',  # 08:00
        ]

        for pattern in patterns:
            match = re.search(pattern, comment)
            if match:
                return match.group(1)

        return None
