"""
类似 Jira 查找器 - 查找相似的 Jira Issues
"""

import re
from typing import Dict, Any, List
from pathlib import Path
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output


class SimilarJiraFinder(BaseAnalyzer):
    """类似 Jira 查找器 - 基于关键词、问题类型和根因匹配，并使用 LLM 分析相关性"""

    def __init__(self, source_dir: str = './sources', top_k: int = 3, llm_client: BaseLLMClient = None, config: Dict[str, Any] = None):
        """
        初始化类似 Jira 查找器

        Args:
            source_dir: 源文件目录
            top_k: 返回最相似的 K 个 Issues
            llm_client: LLM 客户端（用于深度关联分析）
            config: 配置字典
        """
        self.source_dir = Path(source_dir)
        self.top_k = top_k
        self.llm_client = llm_client
        self.config = config or {}

    def get_name(self) -> str:
        return "similar_jira"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        查找类似的 Jira Issues

        Args:
            jira_data: 当前 Jira 数据
            context: 分析上下文

        Returns:
            包含相似 Issues 列表的字典
        """
        import sys

        # 1. 获取所有 Jira Issues
        print("   [similar_jira] 加载所有 issues...", flush=True)
        all_issues = self._load_all_issues()
        print(f"   [similar_jira] 找到 {len(all_issues)} 个 issues", flush=True)

        # 2. 计算相似度
        print("   [similar_jira] 计算相似度...", flush=True)
        similarities = []
        current_key = jira_data['key']

        for issue in all_issues:
            if issue['key'] == current_key:
                continue  # 跳过自己

            score = self._calculate_similarity(jira_data, issue, context)
            if score > 0:
                similarities.append({
                    'key': issue['key'],
                    'title': issue['title'],
                    'status': issue['status'],
                    'priority': issue['priority'],
                    'similarity_score': score,
                    'description': issue['description'][:500]  # 保存描述用于后续分析
                })

        # 3. 排序并返回 Top K
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        top_similar = similarities[:self.top_k]
        print(f"   [similar_jira] 找到 {len(top_similar)} 个相似 issues", flush=True)

        # 4. 使用 LLM 分析相关性（如果有 LLM 客户端）
        if self.llm_client and top_similar:
            print(f"   [similar_jira] 开始 LLM 相关性分析（{len(top_similar)} 个）...", flush=True)
            for i, similar in enumerate(top_similar, 1):
                print(f"   [similar_jira] 分析 {i}/{len(top_similar)}: {similar['key']}", flush=True)
                analysis = self._analyze_relevance(jira_data, similar, context)
                similar['relevance_analysis'] = analysis
                context.increment_llm_calls()
                print(f"   [similar_jira] 完成 {i}/{len(top_similar)}", flush=True)

        print("   [similar_jira] 分析完成", flush=True)
        return {
            'similar_issues': top_similar,
            'total_candidates': len(similarities)
        }

    def _load_all_issues(self) -> List[Dict[str, Any]]:
        """
        加载所有 Jira Issues

        Returns:
            Issues 列表
        """
        issues = []
        jira_pattern = re.compile(r'^[A-Z]+-\d+\.md$')

        for md_file in self.source_dir.rglob('*.md'):
            if not jira_pattern.match(md_file.name):
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read(2000)

                issue_key = md_file.stem
                title_match = re.search(r'^#\s+\[' + issue_key + r'\]\s+(.+)$', content, re.MULTILINE)
                status_match = re.search(r'-\s*\*\*状态\*\*:\s*([^\n]+)', content)
                priority_match = re.search(r'-\s*\*\*优先级\*\*:\s*([^\n]+)', content)
                desc_match = re.search(r'##\s+描述\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)

                issues.append({
                    'key': issue_key,
                    'title': title_match.group(1).strip() if title_match else 'N/A',
                    'status': status_match.group(1).strip() if status_match else 'N/A',
                    'priority': priority_match.group(1).strip() if priority_match else 'N/A',
                    'description': desc_match.group(1).strip() if desc_match else '',
                    'content': content
                })

            except Exception:
                continue

        return issues

    def _calculate_similarity(
        self,
        current: Dict[str, Any],
        candidate: Dict[str, Any],
        context: AnalysisContext
    ) -> float:
        """
        计算两个 Issues 的相似度

        Args:
            current: 当前 Issue
            candidate: 候选 Issue
            context: 分析上下文

        Returns:
            相似度分数 (0-1)
        """
        score = 0.0

        # 1. 关键词匹配 (权重 0.4)
        knowledge = context.get_result('knowledge')
        if knowledge and knowledge.get('keywords'):
            keywords = set(k.lower() for k in knowledge['keywords'])
            candidate_text = (candidate['title'] + ' ' + candidate['description']).lower()

            matched_keywords = sum(1 for kw in keywords if kw.lower() in candidate_text)
            if keywords:
                score += 0.4 * (matched_keywords / len(keywords))

        # 2. 问题类型匹配 (权重 0.3)
        if current.get('type') == candidate.get('type'):
            score += 0.3

        # 3. 优先级匹配 (权重 0.1)
        if current.get('priority') == candidate.get('priority'):
            score += 0.1

        # 4. 根因相似度 (权重 0.2)
        root_cause = context.get_result('root_cause')
        if root_cause and root_cause.get('direct_cause'):
            cause_keywords = set(re.findall(r'\b[A-Za-z]{3,}\b', root_cause['direct_cause'].lower()))
            candidate_text = candidate['content'].lower()

            matched_cause = sum(1 for kw in cause_keywords if kw in candidate_text)
            if cause_keywords:
                score += 0.2 * (matched_cause / len(cause_keywords))

        return min(score, 1.0)  # 确保不超过 1.0

    def _analyze_relevance(
        self,
        current: Dict[str, Any],
        similar: Dict[str, Any],
        context: AnalysisContext
    ) -> str:
        """
        使用 LLM 分析两个 Issue 的相关性

        Args:
            current: 当前 Issue
            similar: 相似 Issue
            context: 分析上下文

        Returns:
            相关性分析文本
        """
        import sys
        # 获取根因分析结果
        root_cause = context.get_result('root_cause')
        root_cause_text = ""
        if root_cause and root_cause.get('direct_cause'):
            root_cause_text = f"\n当前问题根因: {root_cause['direct_cause']}"

        prompt = f"""请分析以下两个 Jira Issue 的相关性：

当前问题:
- [{current['key']}] {current['title']}
- 描述: {current['description'][:300]}{root_cause_text}

相似问题:
- [{similar['key']}] {similar['title']}
- 描述: {similar['description'][:300]}

请从以下角度分析它们的相关性（用 2-3 句话）：
1. 共同点：它们有什么相似之处？（技术领域、问题类型、触发条件等）
2. 参考价值：这个相似问题能为当前问题提供什么参考？（解决思路、注意事项等）

要求：
- 必须用中文回答
- 直接回答，不要使用 Markdown 格式
- 不要输出思考过程
"""

        try:
            print(f"   [similar_jira] 调用 LLM (prompt 长度: {len(prompt)} 字符)...", flush=True)
            sys.stdout.flush()
            max_tokens = self.config.get('max_tokens', 2000)
            response = self.llm_client.generate(prompt, max_tokens=max_tokens)
            print(f"   [similar_jira] LLM 响应完成 (长度: {len(response)} 字符)", flush=True)
            sys.stdout.flush()
            # 清理响应（移除 <think> 标签等）
            response = clean_llm_output(response)
            return response.strip()
        except Exception as e:
            print(f"   [similar_jira] LLM 调用失败: {str(e)}", flush=True)
            sys.stdout.flush()
            return f"相关性分析失败: {str(e)}"
