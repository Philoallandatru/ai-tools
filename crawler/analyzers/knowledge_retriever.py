"""
知识检索分析器 - 从 Wiki 和源文件中检索相关知识
"""

import subprocess
import re
from typing import Dict, Any, List
from pathlib import Path
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.searcher import ContentSearcher


class KnowledgeRetriever(BaseAnalyzer):
    """知识检索分析器 - 双重检索策略（Wiki + 源文件搜索）"""

    def __init__(self, source_dir: str = './sources', wiki_dir: str = './wiki'):
        """
        初始化知识检索器

        Args:
            source_dir: 源文件目录
            wiki_dir: Wiki 目录
        """
        self.source_dir = Path(source_dir)
        self.wiki_dir = Path(wiki_dir)
        self.searcher = ContentSearcher(str(self.source_dir))

    def get_name(self) -> str:
        return "knowledge"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行知识检索

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含 wiki_concepts 和 related_sources 的字典
        """
        # 1. 提取关键词
        keywords = self._extract_keywords(jira_data)

        # 2. Wiki 检索
        wiki_results = self._query_wiki(keywords)

        # 3. 源文件搜索
        source_results = self._search_sources(keywords)

        return {
            'keywords': keywords,
            'wiki_concepts': wiki_results,
            'related_sources': source_results
        }

    def _extract_keywords(self, jira_data: Dict[str, Any]) -> List[str]:
        """
        从 Jira 数据中提取关键词

        Args:
            jira_data: Jira 数据

        Returns:
            关键词列表
        """
        keywords = []

        # 从标题提取
        title = jira_data.get('title', '')
        # 提取技术术语（大写字母开头的词、缩写、特殊术语）
        tech_terms = re.findall(r'\b[A-Z][A-Za-z0-9]*\b', title)
        keywords.extend(tech_terms)

        # 从描述提取
        description = jira_data.get('description', '')
        desc_terms = re.findall(r'\b[A-Z][A-Za-z0-9]*\b', description[:500])
        keywords.extend(desc_terms)

        # 去重并过滤
        keywords = list(set(keywords))
        # 过滤掉常见词
        stop_words = {'The', 'This', 'That', 'With', 'From', 'When', 'Where', 'Demo', 'Test'}
        keywords = [k for k in keywords if k not in stop_words and len(k) > 2]

        return keywords[:10]  # 最多返回 10 个关键词

    def _query_wiki(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        查询 Wiki 概念 - 直接搜索本地 wiki 文件

        Args:
            keywords: 关键词列表

        Returns:
            Wiki 概念列表
        """
        if not self.wiki_dir.exists():
            return []

        results = []
        concepts_dir = self.wiki_dir / 'concepts'

        if not concepts_dir.exists():
            return []

        for keyword in keywords[:5]:
            try:
                for md_file in concepts_dir.glob('*.md'):
                    if keyword.lower() in md_file.stem.lower():
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read(500)
                        results.append({
                            'keyword': keyword,
                            'content': content.strip()[:500]
                        })
                        break
            except Exception:
                continue

        return results

    def _search_sources(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        搜索源文件

        Args:
            keywords: 关键词列表

        Returns:
            搜索结果列表
        """
        results = []

        for keyword in keywords[:5]:  # 最多搜索前 5 个关键词
            try:
                search_results = self.searcher.search(
                    keyword,
                    file_type='all',
                    context_lines=2,
                    max_results=3
                )

                if search_results:
                    results.append({
                        'keyword': keyword,
                        'matches': [
                            {
                                'file': r['file'],
                                'line': r['line_number'],
                                'text': r['line'][:200]  # 限制长度
                            }
                            for r in search_results[:3]
                        ]
                    })

            except Exception:
                continue

        return results
