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
        查询 Wiki 概念 - 使用多种策略检索相关概念

        策略优先级：
        1. 尝试使用 npx llm-wiki-compiler query（需要 LLM API）
        2. 回退到本地文件搜索（文件名 + 内容匹配）

        Args:
            keywords: 关键词列表

        Returns:
            Wiki 概念列表
        """
        if not self.wiki_dir.exists():
            return []

        # 策略 1: 尝试使用 llm-wiki-compiler query
        # 注意：这需要配置 LLM API，如果失败会回退到本地搜索
        query_results = self._try_llmwiki_query(keywords)
        if query_results:
            return query_results

        # 策略 2: 回退到本地文件搜索
        return self._local_wiki_search(keywords)

    def _try_llmwiki_query(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        尝试使用 llm-wiki-compiler query 命令

        注意：此命令会调用 LLM API 来回答问题，不是简单的检索。
        如果 API 配置有问题或超时，会返回空列表触发回退。

        Args:
            keywords: 关键词列表

        Returns:
            查询结果列表，失败返回空列表
        """
        results = []

        # 合并关键词为查询问题
        query = f"什么是 {', '.join(keywords[:3])}？"

        try:
            # 使用 npx llm-wiki-compiler query
            cmd = ["npx", "llm-wiki-compiler", "query", query]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30,  # 30秒超时
                cwd=str(self.wiki_dir.parent)  # 在项目根目录执行
            )

            if result.returncode == 0 and result.stdout.strip():
                # 成功获取回答
                results.append({
                    'keyword': ', '.join(keywords[:3]),
                    'content': result.stdout.strip()[:1000],
                    'source': 'llm-wiki-compiler'
                })
                return results
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # 任何失败都静默回退到本地搜索
            pass

        return []

    def _local_wiki_search(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        本地 Wiki 文件搜索 - 文件名和内容匹配

        改进的搜索策略：
        1. 文件名完全匹配（优先级最高）
        2. 文件名部分匹配
        3. 文件内容匹配

        Args:
            keywords: 关键词列表

        Returns:
            搜索结果列表
        """
        concepts_dir = self.wiki_dir / 'concepts'
        if not concepts_dir.exists():
            return []

        results = []
        matched_files = set()  # 避免重复

        for keyword in keywords[:5]:
            keyword_lower = keyword.lower()

            try:
                # 策略 1: 文件名完全匹配
                exact_match = concepts_dir / f"{keyword_lower}.md"
                if exact_match.exists() and exact_match not in matched_files:
                    with open(exact_match, 'r', encoding='utf-8') as f:
                        content = f.read(1000)
                    results.append({
                        'keyword': keyword,
                        'content': content.strip()[:800],
                        'source': 'filename_exact',
                        'file': exact_match.name
                    })
                    matched_files.add(exact_match)
                    continue

                # 策略 2: 文件名部分匹配
                for md_file in concepts_dir.glob('*.md'):
                    if md_file in matched_files:
                        continue

                    if keyword_lower in md_file.stem.lower():
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read(1000)
                        results.append({
                            'keyword': keyword,
                            'content': content.strip()[:800],
                            'source': 'filename_partial',
                            'file': md_file.name
                        })
                        matched_files.add(md_file)
                        break

                # 策略 3: 内容匹配（如果前两种都没找到）
                if len([r for r in results if r['keyword'] == keyword]) == 0:
                    for md_file in list(concepts_dir.glob('*.md'))[:50]:  # 限制搜索范围
                        if md_file in matched_files:
                            continue

                        try:
                            with open(md_file, 'r', encoding='utf-8') as f:
                                content = f.read(2000)

                            if keyword_lower in content.lower():
                                results.append({
                                    'keyword': keyword,
                                    'content': content.strip()[:800],
                                    'source': 'content_match',
                                    'file': md_file.name
                                })
                                matched_files.add(md_file)
                                break
                        except Exception:
                            continue

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
