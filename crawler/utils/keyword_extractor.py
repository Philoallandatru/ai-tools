"""
统一的关键词提取模块

解决问题：
- DocumentAnalyzer 和 KnowledgeRetriever 中重复的关键词提取逻辑
- 提供统一的接口和配置
"""

import re
from typing import List, Dict, Any, Optional
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import extract_json_from_llm


class KeywordExtractor:
    """统一的关键词提取器"""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        min_length: int = 2,
        max_length: int = 20,
        max_keywords: int = 15
    ):
        """
        初始化关键词提取器

        Args:
            llm_client: LLM 客户端（可选，如果不提供则使用正则表达式）
            min_length: 关键词最小长度
            max_length: 关键词最大长度
            max_keywords: 最大关键词数量
        """
        self.llm_client = llm_client
        self.min_length = min_length
        self.max_length = max_length
        self.max_keywords = max_keywords

    def extract_from_text(
        self,
        text: str,
        context: str = "document",
        max_tokens: int = 300
    ) -> List[str]:
        """
        从文本中提取关键词

        Args:
            text: 输入文本
            context: 上下文类型（document/jira/code）
            max_tokens: LLM 最大 token 数

        Returns:
            关键词列表
        """
        if self.llm_client:
            try:
                return self._extract_with_llm(text, context, max_tokens)
            except Exception as e:
                print(f"   [KeywordExtractor] LLM 提取失败，回退到正则: {str(e)}")

        return self._extract_with_regex(text)

    def extract_from_jira(
        self,
        jira_data: Dict[str, Any],
        max_description_length: int = 500,
        max_tokens: int = 300
    ) -> List[str]:
        """
        从 Jira 数据中提取关键词

        Args:
            jira_data: Jira 数据字典
            max_description_length: 描述最大长度
            max_tokens: LLM 最大 token 数

        Returns:
            关键词列表
        """
        title = jira_data.get('title', '')
        description = jira_data.get('description', '')[:max_description_length]

        combined_text = f"{title}\n{description}"
        return self.extract_from_text(combined_text, context="jira", max_tokens=max_tokens)

    def _extract_with_llm(
        self,
        text: str,
        context: str,
        max_tokens: int
    ) -> List[str]:
        """
        使用 LLM 提取关键词

        Args:
            text: 输入文本
            context: 上下文类型
            max_tokens: 最大 token 数

        Returns:
            关键词列表
        """
        prompt = self._build_prompt(text, context)

        response = self.llm_client.generate(prompt, max_tokens=max_tokens)
        keywords = extract_json_from_llm(response, expected_type='array')

        if keywords:
            # 过滤和清理
            keywords = [
                k.strip()
                for k in keywords
                if isinstance(k, str) and self.min_length <= len(k.strip()) <= self.max_length
            ]
            return keywords[:self.max_keywords]

        return []

    def _build_prompt(self, text: str, context: str) -> str:
        """
        构建 LLM 提示词

        Args:
            text: 输入文本
            context: 上下文类型

        Returns:
            提示词字符串
        """
        if context == "jira":
            return f"""从以下 Jira Issue 中提取 10-15 个最重要的技术关键词，用于搜索相关文档。

标题和描述: {text}

要求：
1. 提取技术术语、产品名称、协议名称、组件名称、功能模块名等
2. 优先提取专有名词和缩写（如 NVMe, SSD, PCIe, Firmware）
3. 包含问题相关的技术领域词汇（如 Memory, Buffer, Download, Update）
4. 包含同义词和相关术语（如 FFU/Firmware Update, CRC/Checksum）
5. 忽略通用词汇（如 Test, Demo, Issue, Problem）
6. 每个关键词 {self.min_length}-{self.max_length} 个字符

请以 JSON 数组格式返回：
["关键词1", "关键词2", "关键词3", ...]"""

        elif context == "document":
            return f"""从以下文档内容中提取适合代码搜索的关键词。

文档内容: {text}

要求：
1. 提取技术术语、API 名称、组件名称、功能名称
2. 保留完整的技术术语（如 "NVMe Reset" 而不是拆分）
3. 提取核心概念和功能关键词
4. 中英文关键词都要提取
5. 每个关键词 {self.min_length}-{self.max_length} 个字符
6. 提取 5-15 个最重要的关键词

请以 JSON 数组格式返回：
["关键词1", "关键词2", "关键词3", ...]"""

        else:  # code or generic
            return f"""从以下文本中提取技术关键词。

文本: {text}

要求：
1. 提取技术术语、函数名、类名、模块名
2. 每个关键词 {self.min_length}-{self.max_length} 个字符
3. 最多提取 {self.max_keywords} 个关键词

请以 JSON 数组格式返回：
["关键词1", "关键词2", "关键词3", ...]"""

    def _extract_with_regex(self, text: str) -> List[str]:
        """
        使用正则表达式提取关键词（回退方案）

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        keywords = []

        # 提取技术术语（大写字母开头的词、缩写、特殊术语）
        tech_terms = re.findall(r'\b[A-Z][A-Za-z0-9]*\b', text)
        keywords.extend(tech_terms)

        # 提取驼峰命名的标识符
        camel_case = re.findall(r'\b[a-z]+[A-Z][a-zA-Z0-9]*\b', text)
        keywords.extend(camel_case)

        # 提取下划线命名的标识符
        snake_case = re.findall(r'\b[a-z]+_[a-z_]+\b', text)
        keywords.extend(snake_case)

        # 去重并过滤
        keywords = list(set(keywords))

        # 过滤掉常见词
        stop_words = {
            'The', 'This', 'That', 'With', 'From', 'When', 'Where',
            'Demo', 'Test', 'Issue', 'Problem', 'Error', 'Warning'
        }
        keywords = [
            k for k in keywords
            if k not in stop_words and self.min_length <= len(k) <= self.max_length
        ]

        return keywords[:self.max_keywords]
