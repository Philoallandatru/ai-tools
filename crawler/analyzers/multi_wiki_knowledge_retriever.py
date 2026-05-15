"""
多 Wiki 知识检索器 - 支持多个 wiki 仓库的知识检索
"""

from typing import Dict, Any, List, Optional, Literal
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.analyzers.knowledge_retriever import KnowledgeRetriever
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.wiki_manager import WikiManager


WikiSelectionMode = Literal['specify', 'auto_match', 'search_all']


@dataclass
class WikiSearchResult:
    """单个 wiki 的搜索结果"""
    wiki_name: str
    wiki_display_name: str
    keywords: List[str]
    wiki_concepts: List[Dict[str, str]]
    related_sources: List[Dict[str, Any]]
    relevance_score: float = 0.0


class MultiWikiKnowledgeRetriever:
    """多 Wiki 知识检索器 - 支持三种检索模式"""

    def __init__(self, wikis_root: str = './wikis',
                 source_dir: str = './sources',
                 llm_client: Optional[BaseLLMClient] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化多 Wiki 知识检索器

        Args:
            wikis_root: wikis 根目录
            source_dir: 源文件目录
            llm_client: LLM 客户端
            config: 配置字典
        """
        self.wikis_root = Path(wikis_root)
        self.source_dir = Path(source_dir)
        self.llm_client = llm_client
        self.config = config or {}

        # 加载 wiki 配置
        self.wiki_manager = WikiManager(str(wikis_root))
        self.wikis = self.wiki_manager.load_wiki_configs()

        # 获取默认 wiki
        wikis_config = config.get('wikis', {})
        self.default_wiki = wikis_config.get('default_wiki', 'default')

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext,
                mode: WikiSelectionMode = 'auto_match',
                wiki_name: Optional[str] = None) -> Dict[str, Any]:
        """
        执行知识检索

        Args:
            jira_data: Jira issue 数据
            context: 分析上下文
            mode: Wiki 选择模式 ('specify', 'auto_match', 'search_all')
            wiki_name: 指定的 wiki 名称（specify 模式必需）

        Returns:
            知识检索结果
        """
        if mode == 'specify':
            if not wiki_name:
                raise ValueError("wiki_name required for 'specify' mode")
            return self._search_single_wiki(jira_data, wiki_name, context)

        elif mode == 'auto_match':
            matched_wiki = self._auto_match_wiki(jira_data)
            if not matched_wiki:
                # 回退到默认 wiki
                matched_wiki = self.default_wiki
                context.add_warning(f"未匹配到 wiki，使用默认 wiki: {matched_wiki}")
            return self._search_single_wiki(jira_data, matched_wiki, context)

        elif mode == 'search_all':
            return self._search_all_wikis(jira_data, context)

        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _search_single_wiki(self, jira_data: Dict[str, Any],
                           wiki_name: str, context: AnalysisContext) -> Dict[str, Any]:
        """
        搜索单个指定的 wiki

        Args:
            jira_data: Jira 数据
            wiki_name: Wiki 名称
            context: 分析上下文

        Returns:
            搜索结果
        """
        wiki_config = self.wikis.get(wiki_name)
        if not wiki_config:
            raise ValueError(f"Wiki not found: {wiki_name}")

        wiki_path = Path(wiki_config['path'])
        wiki_dir = wiki_path / 'wiki'

        # 使用原有的 KnowledgeRetriever 搜索单个 wiki
        retriever = KnowledgeRetriever(
            source_dir=str(self.source_dir),
            wiki_dir=str(wiki_dir),
            llm_client=self.llm_client,
            config=self.config
        )

        result = retriever.analyze(jira_data, context)
        result['wiki_name'] = wiki_name
        result['wiki_display_name'] = wiki_config.get('display_name', wiki_name)
        result['mode'] = 'specify'

        return result

    def _auto_match_wiki(self, jira_data: Dict[str, Any]) -> Optional[str]:
        """
        根据 Jira 元数据自动匹配 wiki

        匹配优先级：
        1. Jira 项目键
        2. 标题/描述中的关键词
        3. Confluence Space（如果有）

        Args:
            jira_data: Jira 数据

        Returns:
            匹配的 wiki 名称，未匹配返回 None
        """
        jira_key = jira_data.get('key', '')
        project_key = jira_key.split('-')[0] if '-' in jira_key else ''
        title = jira_data.get('title', '').lower()
        description = jira_data.get('description', '').lower()

        for wiki_name, wiki_config in self.wikis.items():
            auto_match = wiki_config.get('auto_match_rules', {})

            # 优先级 1: 检查 Jira 项目
            jira_projects = auto_match.get('jira_projects', [])
            if project_key and project_key in jira_projects:
                print(f"   [multi-wiki] 自动匹配到 wiki: {wiki_name} (Jira 项目: {project_key})")
                return wiki_name

            # 优先级 2: 检查关键词
            keywords = auto_match.get('keywords', [])
            if any(kw.lower() in title or kw.lower() in description for kw in keywords):
                print(f"   [multi-wiki] 自动匹配到 wiki: {wiki_name} (关键词匹配)")
                return wiki_name

            # 优先级 3: 检查 Confluence Space（如果 Jira 数据中有）
            confluence_spaces = auto_match.get('confluence_spaces', [])
            jira_space = jira_data.get('confluence_space', '')
            if jira_space and jira_space in confluence_spaces:
                print(f"   [multi-wiki] 自动匹配到 wiki: {wiki_name} (Confluence Space: {jira_space})")
                return wiki_name

        return None

    def _search_all_wikis(self, jira_data: Dict[str, Any],
                         context: AnalysisContext) -> Dict[str, Any]:
        """
        搜索所有配置的 wiki 并合并结果

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            合并的搜索结果
        """
        all_results = []

        # 并行搜索所有 wiki
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_wiki = {
                executor.submit(self._search_single_wiki_safe, jira_data, wiki_name, context): wiki_name
                for wiki_name in self.wikis.keys()
            }

            for future in as_completed(future_to_wiki):
                wiki_name = future_to_wiki[future]
                try:
                    result = future.result()
                    if result:
                        # 计算相关性评分
                        relevance = self._calculate_relevance(result)

                        all_results.append(WikiSearchResult(
                            wiki_name=wiki_name,
                            wiki_display_name=result['wiki_display_name'],
                            keywords=result['keywords'],
                            wiki_concepts=result['wiki_concepts'],
                            related_sources=result['related_sources'],
                            relevance_score=relevance
                        ))
                except Exception as e:
                    context.add_warning(f"搜索 wiki '{wiki_name}' 失败: {str(e)}")

        # 按相关性排序
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)

        return self._merge_results(all_results, jira_data)

    def _search_single_wiki_safe(self, jira_data: Dict[str, Any],
                                 wiki_name: str, context: AnalysisContext) -> Optional[Dict[str, Any]]:
        """
        安全地搜索单个 wiki（捕获异常）

        Args:
            jira_data: Jira 数据
            wiki_name: Wiki 名称
            context: 分析上下文

        Returns:
            搜索结果或 None
        """
        try:
            return self._search_single_wiki(jira_data, wiki_name, context)
        except Exception as e:
            print(f"   [multi-wiki] 搜索 wiki '{wiki_name}' 失败: {str(e)}")
            return None

    def _calculate_relevance(self, result: Dict[str, Any]) -> float:
        """
        计算相关性评分

        Args:
            result: 搜索结果

        Returns:
            相关性评分
        """
        score = 0.0

        # 基于找到的概念数量
        wiki_concepts = result.get('wiki_concepts', [])
        score += len(wiki_concepts) * 2.0

        # 基于 LLM 分析评分
        for concept in wiki_concepts:
            llm_analysis = concept.get('llm_analysis', {})
            llm_score = llm_analysis.get('score', 0)
            score += llm_score * 0.5

        # 基于源文件匹配数量
        related_sources = result.get('related_sources', [])
        score += len(related_sources) * 1.0

        return score

    def _merge_results(self, results: List[WikiSearchResult],
                      jira_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个 wiki 的搜索结果

        Args:
            results: Wiki 搜索结果列表
            jira_data: Jira 数据

        Returns:
            合并的结果
        """
        merged = {
            'mode': 'search_all',
            'wikis_searched': len(results),
            'keywords': results[0].keywords if results else [],
            'results_by_wiki': []
        }

        for result in results:
            merged['results_by_wiki'].append({
                'wiki_name': result.wiki_name,
                'wiki_display_name': result.wiki_display_name,
                'relevance_score': result.relevance_score,
                'wiki_concepts': result.wiki_concepts,
                'related_sources': result.related_sources
            })

        return merged

    def get_available_wikis(self) -> List[str]:
        """获取所有可用的 wiki 名称"""
        return list(self.wikis.keys())

    def get_wiki_info(self, wiki_name: str) -> Optional[Dict[str, Any]]:
        """获取 wiki 信息"""
        return self.wikis.get(wiki_name)
