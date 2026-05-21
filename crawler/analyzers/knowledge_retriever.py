"""
知识检索分析器 - 从 Wiki 和源文件中检索相关知识
"""

import subprocess
import re
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.searcher import ContentSearcher
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output, extract_json_from_llm
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine


class KnowledgeRetriever(BaseAnalyzer):
    """知识检索分析器 - 双重检索策略（Wiki + 源文件搜索）+ LLM 相关性分析"""

    VERSION = "1.0.0"

    def __init__(self, source_dir: str = './sources', wiki_dir: str = './wiki',
                 llm_client: Optional[BaseLLMClient] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化知识检索器

        Args:
            source_dir: 源文件目录
            wiki_dir: Wiki 目录
            llm_client: LLM 客户端（可选，用于分析概念相关性）
            config: 配置字典（可选）
        """
        self.source_dir = Path(source_dir)
        self.wiki_dir = Path(wiki_dir)
        self.searcher = ContentSearcher(str(self.source_dir))
        self.llm_client = llm_client

        # 从配置读取参数，如果没有则使用默认值
        config = config or {}
        knowledge_config = config.get('performance', {}).get('knowledge_retrieval', {})
        cache_config = config.get('cache', {})

        # 缓存配置
        cache_dir = cache_config.get('dir', './.cache')
        self.cache_dir = Path(cache_dir) / 'knowledge'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_enabled = cache_config.get('enabled', True)

        # 性能配置
        self.max_description_length = knowledge_config.get('max_description_length', 500)
        self.max_keywords = knowledge_config.get('max_keywords', 15)
        self.keyword_extraction_max_tokens = knowledge_config.get('keyword_extraction_max_tokens', 300)
        self.concept_analysis_max_tokens = knowledge_config.get('concept_analysis_max_tokens', 500)
        self.wiki_query_timeout = knowledge_config.get('wiki_query_timeout', 30)
        self.wiki_content_preview = knowledge_config.get('wiki_content_preview', 2000)
        self.max_thread_workers = knowledge_config.get('max_thread_workers', 3)
        self.min_keyword_length = knowledge_config.get('min_keyword_length', 2)
        self.max_keyword_length = knowledge_config.get('max_keyword_length', 20)
        self.max_search_keywords = knowledge_config.get('max_search_keywords', 8)
        self.max_results_per_keyword = knowledge_config.get('max_results_per_keyword', 3)
        self.min_relevance_score = knowledge_config.get('min_relevance_score', 3)

        # 初始化共享模块
        self.keyword_extractor = KeywordExtractor(
            llm_client=llm_client,
            min_length=self.min_keyword_length,
            max_length=self.max_keyword_length,
            max_keywords=self.max_keywords
        )

        self.search_engine = UnifiedSearchEngine(
            source_dir=source_dir,
            llm_client=llm_client,
            cache_dir=str(self.cache_dir / 'search') if self.cache_enabled else None,
            min_relevance_score=self.min_relevance_score
        )

    def get_name(self) -> str:
        return "knowledge"

    def _get_cache_key(self, jira_key: str) -> str:
        """
        生成缓存键

        Args:
            jira_key: Jira issue key

        Returns:
            缓存文件路径
        """
        # 使用 issue key + 版本号生成缓存键
        cache_key = f"{jira_key}_{self.VERSION}"
        return str(self.cache_dir / f"knowledge_{cache_key}.json")

    def _load_cache(self, jira_key: str) -> Optional[Dict[str, Any]]:
        """
        加载缓存结果

        Args:
            jira_key: Jira issue key

        Returns:
            缓存的分析结果，如果不存在返回 None
        """
        if not self.cache_enabled:
            return None

        cache_file = self._get_cache_key(jira_key)
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                print(f"   [knowledge] 使用缓存结果")
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"   [knowledge] 缓存加载失败: {str(e)}")
            return None

    def _save_cache(self, jira_key: str, result: Dict[str, Any]) -> None:
        """
        保存分析结果到缓存

        Args:
            jira_key: Jira issue key
            result: 分析结果
        """
        if not self.cache_enabled:
            return

        cache_file = self._get_cache_key(jira_key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   [knowledge] 缓存保存失败: {str(e)}")

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行知识检索

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含 wiki_concepts 和 related_sources 的字典
        """
        jira_key = jira_data.get('key', '')

        # 尝试加载缓存
        cached_result = self._load_cache(jira_key)
        if cached_result:
            return cached_result

        # 1. 提取关键词
        keywords = self._extract_keywords(jira_data)

        # 2. Wiki 检索
        wiki_results = self._query_wiki(keywords)

        # 3. 如果有 LLM 客户端，分析概念相关性
        if self.llm_client and wiki_results:
            wiki_results = self._analyze_concept_relevance(jira_data, wiki_results, context)

        # 4. 源文件搜索
        source_results = self._search_sources(keywords)

        result = {
            'keywords': keywords,
            'wiki_concepts': wiki_results,
            'related_sources': source_results
        }

        # 保存到缓存
        self._save_cache(jira_key, result)

        return result

    def _extract_keywords(self, jira_data: Dict[str, Any]) -> List[str]:
        """
        从 Jira 数据中提取关键词（使用共享的 KeywordExtractor）

        Args:
            jira_data: Jira 数据

        Returns:
            关键词列表
        """
        return self.keyword_extractor.extract_from_jira(
            jira_data,
            max_description_length=self.max_description_length,
            max_tokens=self.keyword_extraction_max_tokens
        )


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
                timeout=self.wiki_query_timeout,
                cwd=str(self.wiki_dir.parent)
            )

            if result.returncode == 0 and result.stdout.strip():
                # 成功获取回答
                results.append({
                    'keyword': ', '.join(keywords[:3]),
                    'content': result.stdout.strip()[:self.wiki_content_preview],
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
                        content = f.read(3000)  # 读取更多内容

                    # 提取相关段落
                    paragraphs = self._extract_relevant_paragraphs(content, keyword)

                    results.append({
                        'keyword': keyword,
                        'content': paragraphs,
                        'full_content': content.strip()[:2000],  # 保留完整内容预览
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
                            content = f.read(3000)

                        # 提取相关段落
                        paragraphs = self._extract_relevant_paragraphs(content, keyword)

                        results.append({
                            'keyword': keyword,
                            'content': paragraphs,
                            'full_content': content.strip()[:2000],
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
                                content = f.read(3000)

                            if keyword_lower in content.lower():
                                # 提取相关段落
                                paragraphs = self._extract_relevant_paragraphs(content, keyword)

                                results.append({
                                    'keyword': keyword,
                                    'content': paragraphs,
                                    'full_content': content.strip()[:2000],
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

    def _extract_relevant_paragraphs(self, content: str, keyword: str) -> str:
        """
        从文档内容中提取与关键词最相关的段落

        Args:
            content: 文档内容
            keyword: 关键词

        Returns:
            相关段落文本
        """
        # 按段落分割（双换行）
        paragraphs = re.split(r'\n\s*\n+', content)

        keyword_lower = keyword.lower()
        relevant_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 10:  # 忽略太短的段落
                continue

            # 计算关键词出现次数
            keyword_count = para.lower().count(keyword_lower)

            # 如果段落包含关键词，或者是标题/定义段落
            is_header = para.startswith('#')
            is_definition = '定义' in para or '概念' in para or '是指' in para or '是一种' in para

            if keyword_count > 0 or is_header or is_definition:
                # 计算相关性分数
                score = keyword_count * 2  # 关键词出现次数权重
                if is_header:
                    score += 3  # 标题权重
                if is_definition:
                    score += 2  # 定义段落权重
                if keyword_count > 0 and len(para) > 50:
                    score += 1  # 有内容的相关段落额外加分

                relevant_paragraphs.append({
                    'text': para,
                    'score': score
                })

        # 按相关性排序
        relevant_paragraphs.sort(key=lambda x: x['score'], reverse=True)

        # 返回前 5 个最相关的段落
        result_parts = [p['text'] for p in relevant_paragraphs[:5]]
        result = '\n\n'.join(result_parts)

        # 如果没有找到相关段落，返回前 1500 字符
        if not result or len(result) < 100:
            result = content[:1500]

        return result[:1500]  # 限制总长度

    def _analyze_single_concept(self, jira_data: Dict[str, Any], concept: Dict[str, str], index: int, total: int, context: AnalysisContext) -> Dict[str, str]:
        """
        分析单个概念的相关性（用于并行处理）

        Args:
            jira_data: Jira 数据
            concept: Wiki 概念
            index: 概念索引（用于进度显示）
            total: 总概念数
            context: 分析上下文

        Returns:
            增强了相关性分析的概念
        """
        # 构建结构化 prompt
        prompt = f"""请分析以下 Wiki 概念与 Jira Issue 的相关性：

Jira Issue: [{jira_data['key']}] {jira_data['title']}
描述: {jira_data['description'][:self.max_description_length]}

Wiki 概念: {concept['keyword']}
来源文件: {concept.get('file', 'unknown')}
内容: {concept['content'][:800]}

请评估：
1. 相关性得分（0-10分）
   - 8-10分: 直接相关，核心概念
   - 5-7分: 间接相关，背景知识
   - 3-4分: 弱相关，可能有用
   - 0-2分: 不相关
2. 相关原因（说明为什么相关，以及如何帮助理解问题）
3. 关键信息（从内容中提取 1-3 个最重要的知识点）

请以 JSON 格式返回：
{{"score": 分数, "reason": "原因", "key_points": ["知识点1", "知识点2"]}}"""

        try:
            # 显示进度
            print(f"   [knowledge] 分析概念相关性 {index}/{total}: {concept['keyword']}")

            # 调用 LLM
            context.increment_llm_calls()
            response = self.llm_client.generate(prompt, max_tokens=self.concept_analysis_max_tokens)

            # 使用统一的 JSON 提取函数
            data = extract_json_from_llm(response, expected_type='object')

            score = 0
            reason = '无法分析'
            key_points = []

            if data:
                score = int(data.get('score', 0))
                reason = data.get('reason', '无法分析')
                key_points = data.get('key_points', [])
            else:
                # 回退：尝试提取键值对
                score_match = re.search(r'["\']?score["\']?\s*[:：]\s*(\d+)', response, re.IGNORECASE)
                reason_match = re.search(r'["\']?reason["\']?\s*[:：]\s*["\']?([^"\'}\n]+)', response, re.IGNORECASE)

                if score_match:
                    score = int(score_match.group(1))
                if reason_match:
                    reason = reason_match.group(1).strip()

            # 添加 LLM 分析结果
            enhanced_concept = concept.copy()
            enhanced_concept['llm_analysis'] = {
                'score': score,
                'reason': reason,
                'key_points': key_points if isinstance(key_points, list) else []
            }
            return enhanced_concept

        except Exception as e:
            # LLM 调用失败，给默认低分
            enhanced_concept = concept.copy()
            enhanced_concept['llm_analysis'] = {
                'score': 0,
                'reason': f'分析失败: {str(e)}'
            }
            context.add_warning(f"概念 '{concept['keyword']}' 的 LLM 分析失败: {str(e)}")
            return enhanced_concept

    def _analyze_concept_relevance(self, jira_data: Dict[str, Any], wiki_results: List[Dict[str, str]], context: AnalysisContext) -> List[Dict[str, str]]:
        """
        使用 LLM 并行分析检索到的概念与 Jira issue 的相关性

        Args:
            jira_data: Jira 数据
            wiki_results: Wiki 检索结果
            context: 分析上下文

        Returns:
            增强了相关性分析的 Wiki 结果（已排序和过滤）
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        enhanced_results = []

        # 动态调整线程池大小
        max_workers = min(len(wiki_results), self.max_thread_workers, os.cpu_count() or 1)

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_concept = {
                executor.submit(
                    self._analyze_single_concept,
                    jira_data,
                    concept,
                    i,
                    len(wiki_results),
                    context
                ): concept
                for i, concept in enumerate(wiki_results, 1)
            }

            # 收集结果
            for future in as_completed(future_to_concept):
                try:
                    result = future.result()
                    enhanced_results.append(result)
                except Exception as e:
                    concept = future_to_concept[future]
                    # 如果线程执行失败，添加默认结果
                    enhanced_concept = concept.copy()
                    enhanced_concept['llm_analysis'] = {
                        'score': 0,
                        'reason': f'并行处理失败: {str(e)}'
                    }
                    enhanced_results.append(enhanced_concept)
                    context.add_warning(f"概念 '{concept['keyword']}' 的并行分析失败: {str(e)}")

        # 按相关性得分排序（降序）
        enhanced_results.sort(key=lambda x: x.get('llm_analysis', {}).get('score', 0), reverse=True)

        # 过滤掉低相关性概念（使用配置的阈值，默认 3 分）
        filtered_results = [r for r in enhanced_results if r.get('llm_analysis', {}).get('score', 0) >= self.min_relevance_score]

        # 如果过滤后结果太少（< 3 个），降低阈值保留更多结果
        if len(filtered_results) < 3 and enhanced_results:
            # 保留得分 >= 2 的，或者至少保留前 5 个
            filtered_results = [r for r in enhanced_results if r.get('llm_analysis', {}).get('score', 0) >= 2]
            if len(filtered_results) < 3:
                filtered_results = enhanced_results[:5]

        print(f"   [knowledge] 过滤后保留 {len(filtered_results)} 个相关概念（阈值: {self.min_relevance_score}）")

        return filtered_results

    def _search_sources(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        搜索源文件（使用共享的 UnifiedSearchEngine）

        Args:
            keywords: 关键词列表

        Returns:
            搜索结果列表
        """
        results = []

        for keyword in keywords[:self.max_search_keywords]:
            try:
                # 使用统一搜索引擎
                search_results = self.search_engine.search(
                    query=keyword,
                    keywords=[keyword],
                    max_results=self.max_results_per_keyword,
                    use_llm_ranking=True,
                    context_lines=2
                )

                if search_results:
                    results.append({
                        'keyword': keyword,
                        'matches': [
                            {
                                'file': r.file_path,
                                'line': r.line_number or 0,
                                'text': r.snippet[:200],  # 限制长度
                                'relevance_score': r.relevance_score,
                                'match_reason': r.match_reason
                            }
                            for r in search_results[:self.max_results_per_keyword]
                        ]
                    })

            except Exception:
                continue

        return results
