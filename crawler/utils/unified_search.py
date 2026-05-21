"""
统一的搜索接口

解决问题：
- Doc 分析和 Jira 分析的搜索质量不一致
- 提供统一的 LLM 相关性分析
- 支持缓存和性能优化
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from crawler.searcher import ContentSearcher, SearchMatch
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import extract_json_from_llm


@dataclass
class SearchResult:
    """统一的搜索结果"""
    file_path: str
    snippet: str
    relevance_score: float  # 0-10
    match_reason: str
    line_number: Optional[int] = None
    context: Optional[str] = None


class UnifiedSearchEngine:
    """统一的搜索引擎 - 支持 LLM 相关性分析"""

    def __init__(
        self,
        source_dir: str = './sources',
        llm_client: Optional[BaseLLMClient] = None,
        cache_dir: Optional[str] = None,
        min_relevance_score: float = 3.0
    ):
        """
        初始化搜索引擎

        Args:
            source_dir: 源文件目录
            llm_client: LLM 客户端（用于相关性分析）
            cache_dir: 缓存目录
            min_relevance_score: 最低相关性阈值
        """
        self.content_searcher = ContentSearcher(source_dir)
        self.llm_client = llm_client
        self.min_relevance_score = min_relevance_score

        # 缓存配置
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_enabled = True
        else:
            self.cache_enabled = False

    def search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        max_results: int = 10,
        use_llm_ranking: bool = True,
        context_lines: int = 3
    ) -> List[SearchResult]:
        """
        执行搜索

        Args:
            query: 搜索查询（自然语言描述）
            keywords: 关键词列表（可选）
            max_results: 最大结果数
            use_llm_ranking: 是否使用 LLM 相关性排序
            context_lines: 上下文行数

        Returns:
            搜索结果列表（按相关性排序）
        """
        # 1. 检查缓存
        if self.cache_enabled:
            cached = self._load_cache(query, keywords)
            if cached:
                print(f"   [UnifiedSearch] 使用缓存结果")
                return cached

        # 2. 基础搜索
        raw_matches = self._basic_search(keywords or [query], context_lines, max_results * 3)

        if not raw_matches:
            return []

        # 3. LLM 相关性分析和排序
        if use_llm_ranking and self.llm_client:
            results = self._rank_with_llm(query, raw_matches, max_results)
        else:
            results = self._simple_ranking(raw_matches, max_results)

        # 4. 保存缓存
        if self.cache_enabled:
            self._save_cache(query, keywords, results)

        return results

    def _basic_search(
        self,
        keywords: List[str],
        context_lines: int,
        max_results: int
    ) -> List[SearchMatch]:
        """
        基础关键词搜索

        Args:
            keywords: 关键词列表
            context_lines: 上下文行数
            max_results: 最大结果数

        Returns:
            原始搜索匹配列表
        """
        all_matches = []

        for keyword in keywords[:10]:  # 限制关键词数量
            try:
                matches = self.content_searcher.search(
                    query=keyword,
                    file_type='all',
                    context_lines=context_lines,
                    max_results=max_results
                )
                all_matches.extend(matches)
            except Exception as e:
                print(f"   [UnifiedSearch] 搜索关键词 '{keyword}' 失败: {str(e)}")

        # 去重（基于文件路径和行号）
        seen = set()
        unique_matches = []
        for match in all_matches:
            key = (str(match.file_path), match.line_number)
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        return unique_matches[:max_results]

    def _rank_with_llm(
        self,
        query: str,
        matches: List[SearchMatch],
        max_results: int
    ) -> List[SearchResult]:
        """
        使用 LLM 分析相关性并排序

        Args:
            query: 搜索查询
            matches: 原始匹配列表
            max_results: 最大结果数

        Returns:
            排序后的搜索结果
        """
        print(f"   [UnifiedSearch] 使用 LLM 分析 {len(matches)} 个匹配的相关性...")

        results = []

        for match in matches:
            try:
                # 构建上下文
                context = self._build_context(match)

                # 调用 LLM 评分
                score, reason = self._score_relevance(query, context)

                if score >= self.min_relevance_score:
                    results.append(SearchResult(
                        file_path=str(match.file_path),
                        snippet=match.line_content,
                        relevance_score=score,
                        match_reason=reason,
                        line_number=match.line_number,
                        context=context
                    ))

            except Exception as e:
                print(f"   [UnifiedSearch] LLM 评分失败: {str(e)}")
                # 回退到简单评分
                results.append(SearchResult(
                    file_path=str(match.file_path),
                    snippet=match.line_content,
                    relevance_score=5.0,  # 默认中等相关性
                    match_reason="基础关键词匹配",
                    line_number=match.line_number,
                    context=self._build_context(match)
                ))

        # 按相关性排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:max_results]

    def _score_relevance(self, query: str, context: str) -> tuple[float, str]:
        """
        使用 LLM 评估相关性

        Args:
            query: 搜索查询
            context: 代码上下文

        Returns:
            (相关性分数 0-10, 原因说明)
        """
        prompt = f"""评估以下代码片段与查询的相关性。

查询: {query}

代码片段:
{context}

请评估相关性（0-10分）：
- 10分：完全匹配，直接实现了查询的功能
- 7-9分：高度相关，包含查询的核心概念
- 4-6分：中等相关，有一定关联
- 1-3分：弱相关，仅有间接关联
- 0分：不相关

请以 JSON 格式返回：
{{
  "score": 8,
  "reason": "该代码实现了 NVMe 控制器重置功能，直接对应查询需求"
}}"""

        try:
            response = self.llm_client.generate(prompt, max_tokens=200)
            result = extract_json_from_llm(response, expected_type='object')

            if result and 'score' in result:
                score = float(result['score'])
                reason = result.get('reason', '相关')
                return score, reason

        except Exception as e:
            print(f"   [UnifiedSearch] LLM 评分解析失败: {str(e)}")

        return 5.0, "无法评估"

    def _simple_ranking(
        self,
        matches: List[SearchMatch],
        max_results: int
    ) -> List[SearchResult]:
        """
        简单排序（不使用 LLM）

        Args:
            matches: 原始匹配列表
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        results = []

        for match in matches:
            # 简单评分：基于文件类型和匹配位置
            score = 5.0  # 基础分数

            # 文件类型加分
            file_path = str(match.file_path)
            if file_path.endswith(('.c', '.cpp', '.h')):
                score += 2.0
            elif file_path.endswith('.py'):
                score += 1.5
            elif file_path.endswith('.md'):
                score += 1.0

            results.append(SearchResult(
                file_path=file_path,
                snippet=match.line_content,
                relevance_score=score,
                match_reason="关键词匹配",
                line_number=match.line_number,
                context=self._build_context(match)
            ))

        # 按分数排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:max_results]

    def _build_context(self, match: SearchMatch) -> str:
        """
        构建代码上下文

        Args:
            match: 搜索匹配

        Returns:
            上下文字符串
        """
        lines = []

        # 添加前置上下文
        for line in match.context_before:
            lines.append(line)

        # 添加匹配行（高亮）
        lines.append(f">>> {match.line_content}")

        # 添加后置上下文
        for line in match.context_after:
            lines.append(line)

        return '\n'.join(lines)

    def _get_cache_key(self, query: str, keywords: Optional[List[str]]) -> str:
        """生成缓存键"""
        import hashlib
        key_str = f"{query}_{keywords}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _load_cache(self, query: str, keywords: Optional[List[str]]) -> Optional[List[SearchResult]]:
        """加载缓存"""
        if not self.cache_enabled:
            return None

        cache_key = self._get_cache_key(query, keywords)
        cache_file = self.cache_dir / f"search_{cache_key}.json"

        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [SearchResult(**item) for item in data]
        except Exception as e:
            print(f"   [UnifiedSearch] 缓存加载失败: {str(e)}")

        return None

    def _save_cache(self, query: str, keywords: Optional[List[str]], results: List[SearchResult]) -> None:
        """保存缓存"""
        if not self.cache_enabled:
            return

        cache_key = self._get_cache_key(query, keywords)
        cache_file = self.cache_dir / f"search_{cache_key}.json"

        try:
            data = [
                {
                    'file_path': r.file_path,
                    'snippet': r.snippet,
                    'relevance_score': r.relevance_score,
                    'match_reason': r.match_reason,
                    'line_number': r.line_number,
                    'context': r.context
                }
                for r in results
            ]

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"   [UnifiedSearch] 缓存保存失败: {str(e)}")
