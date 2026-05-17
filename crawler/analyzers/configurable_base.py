"""
增强版可配置分析器基类 - 提供通用的 LLM 调用、缓存、上下文格式化等功能
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from abc import abstractmethod

from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output, extract_json_from_llm


class ConfigurableAnalyzer(BaseAnalyzer):
    """
    增强版可配置分析器基类

    提供功能：
    1. 统一的 LLM 调用和配置管理
    2. 缓存机制（可选）
    3. 上下文格式化工具
    4. Jira 变量替换
    5. JSON 和正则提取辅助
    6. 并行 LLM 调用
    7. 进度显示工具

    子类只需实现：
    - get_name(): 返回分析器名称
    - analyze(): 实现分析逻辑
    """

    def __init__(self, llm_client: BaseLLMClient, config: Optional[Dict[str, Any]] = None):
        """
        初始化可配置分析器

        Args:
            llm_client: LLM 客户端
            config: 配置字典，支持的配置项：
                - max_tokens: 最大 token 数
                - cache_enabled: 是否启用缓存（默认 False）
                - cache_dir: 缓存目录（默认 ./.cache/analyzers）
                - cache_version: 缓存版本（默认 1.0.0）
        """
        self.llm_client = llm_client
        self.config = config or {}

        # 缓存配置
        self.cache_enabled = self.config.get('cache_enabled', False)
        cache_dir = self.config.get('cache_dir', './.cache/analyzers')
        self.cache_dir = Path(cache_dir)
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_version = self.config.get('cache_version', '1.0.0')

    # ==================== 基础 LLM 调用 ====================

    def get_max_tokens(self, default: int = 2000) -> int:
        """
        从配置获取 max_tokens

        Args:
            default: 默认值

        Returns:
            max_tokens 值
        """
        return self.config.get('max_tokens', default)

    def call_llm(
        self,
        prompt: str,
        context: AnalysisContext,
        default_max_tokens: int = 2000,
        temperature: Optional[float] = None
    ) -> str:
        """
        调用 LLM 并自动清理响应

        Args:
            prompt: 提示词
            context: 分析上下文
            default_max_tokens: 默认 max_tokens
            temperature: 温度参数（可选）

        Returns:
            清理后的响应
        """
        context.increment_llm_calls()
        max_tokens = self.get_max_tokens(default_max_tokens)

        kwargs = {'max_tokens': max_tokens}
        if temperature is not None:
            kwargs['temperature'] = temperature

        response = self.llm_client.generate(prompt, **kwargs)
        return clean_llm_output(response)

    def call_llm_with_fallback(
        self,
        prompt: str,
        context: AnalysisContext,
        fallback_value: Any = None,
        default_max_tokens: int = 2000
    ) -> str:
        """
        调用 LLM，失败时返回 fallback 值

        Args:
            prompt: 提示词
            context: 分析上下文
            fallback_value: 失败时的返回值
            default_max_tokens: 默认 max_tokens

        Returns:
            LLM 响应或 fallback 值
        """
        try:
            return self.call_llm(prompt, context, default_max_tokens)
        except Exception as e:
            self.log_progress(f"LLM 调用失败: {str(e)}")
            if fallback_value is not None:
                return fallback_value
            raise

    def call_llm_parallel(
        self,
        prompts: List[str],
        context: AnalysisContext,
        max_workers: int = 3,
        default_max_tokens: int = 2000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        并行调用 LLM

        Args:
            prompts: 提示词列表
            context: 分析上下文
            max_workers: 最大并发数
            default_max_tokens: 默认 max_tokens
            progress_callback: 进度回调函数 (current, total)

        Returns:
            响应列表（顺序与输入一致）
        """
        results = [None] * len(prompts)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self.call_llm, prompt, context, default_max_tokens): i
                for i, prompt in enumerate(prompts)
            }

            completed = 0
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    results[index] = f"错误: {str(e)}"
                    context.add_warning(f"并行 LLM 调用失败 (索引 {index}): {str(e)}")

                completed += 1
                if progress_callback:
                    progress_callback(completed, len(prompts))

        return results

    # ==================== 缓存机制 ====================

    def _get_cache_key(self, jira_key: str) -> str:
        """
        生成缓存键

        Args:
            jira_key: Jira issue key

        Returns:
            缓存文件路径
        """
        analyzer_name = self.get_name()
        cache_key = f"{analyzer_name}_{jira_key}_{self.cache_version}"
        return str(self.cache_dir / f"{cache_key}.json")

    def load_cache(self, jira_key: str) -> Optional[Dict[str, Any]]:
        """
        加载缓存结果

        Args:
            jira_key: Jira issue key

        Returns:
            缓存的结果，不存在返回 None
        """
        if not self.cache_enabled:
            return None

        cache_file = self._get_cache_key(jira_key)
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                self.log_progress("使用缓存结果")
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            self.log_progress(f"缓存加载失败: {str(e)}")
            return None

    def save_cache(self, jira_key: str, result: Dict[str, Any]) -> None:
        """
        保存结果到缓存

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
            self.log_progress(f"缓存保存失败: {str(e)}")

    # ==================== 上下文格式化 ====================

    def format_knowledge_context(self, context: AnalysisContext) -> str:
        """
        格式化知识检索上下文

        Args:
            context: 分析上下文

        Returns:
            格式化的知识上下文
        """
        knowledge = context.get_result('knowledge')
        if not knowledge:
            return ""

        lines = ["\n相关技术知识:"]

        keywords = knowledge.get('keywords', [])
        if keywords:
            lines.append(f"关键词: {', '.join(keywords[:5])}")

        wiki_concepts = knowledge.get('wiki_concepts', [])
        for concept in wiki_concepts[:3]:
            keyword = concept.get('keyword', '')
            content = concept.get('content', '')[:200]
            lines.append(f"- {keyword}: {content}")

        return '\n'.join(lines)

    def format_root_cause_context(self, context: AnalysisContext) -> str:
        """
        格式化根因分析上下文

        Args:
            context: 分析上下文

        Returns:
            格式化的根因上下文
        """
        root_cause = context.get_result('root_cause')
        if not root_cause:
            return ""

        lines = ["\n根因分析:"]

        direct = root_cause.get('direct_cause', '')
        if direct:
            lines.append(f"直接原因: {direct}")

        deep = root_cause.get('deep_cause', '')
        if deep:
            lines.append(f"深层原因: {deep}")

        trigger = root_cause.get('trigger_condition', '')
        if trigger:
            lines.append(f"触发条件: {trigger}")

        return '\n'.join(lines)

    def format_similar_jira_context(self, context: AnalysisContext) -> str:
        """
        格式化相似问题上下文

        Args:
            context: 分析上下文

        Returns:
            格式化的相似问题上下文
        """
        similar = context.get_result('similar_jira')
        if not similar:
            return ""

        issues = similar.get('similar_issues', [])
        if not issues:
            return ""

        lines = ["\n相似问题:"]
        for issue in issues[:3]:
            key = issue.get('key', '')
            title = issue.get('title', '')
            score = issue.get('similarity_score', 0)
            lines.append(f"- [{key}] {title} (相似度: {score:.2f})")

        return '\n'.join(lines)

    def format_comments_context(self, context: AnalysisContext) -> str:
        """
        格式化评论分析上下文

        Args:
            context: 分析上下文

        Returns:
            格式化的评论上下文
        """
        comments = context.get_result('comments')
        if not comments:
            return ""

        lines = ["\n评论分析:"]

        summary = comments.get('summary', '')
        if summary:
            lines.append(summary)

        return '\n'.join(lines)

    # ==================== Jira 变量替换 ====================

    def replace_jira_variables(self, prompt: str, jira_data: Dict[str, Any]) -> str:
        """
        替换 prompt 中的 Jira 变量

        支持的变量：
        - {key}: Issue key
        - {title}: 标题
        - {description}: 描述（限制 1000 字符）
        - {status}: 状态
        - {priority}: 优先级
        - {type}: 类型
        - {assignee}: 负责人

        Args:
            prompt: 包含变量的 prompt
            jira_data: Jira 数据

        Returns:
            替换后的 prompt
        """
        replacements = {
            '{key}': jira_data.get('key', ''),
            '{title}': jira_data.get('title', ''),
            '{description}': jira_data.get('description', '')[:1000],
            '{status}': jira_data.get('status', ''),
            '{priority}': jira_data.get('priority', ''),
            '{type}': jira_data.get('type', ''),
            '{assignee}': jira_data.get('assignee', ''),
        }

        for var, value in replacements.items():
            prompt = prompt.replace(var, str(value))

        return prompt

    def replace_context_variables(self, prompt: str, context: AnalysisContext) -> str:
        """
        替换 prompt 中的上下文变量

        支持的变量：
        - {knowledge_context}: 知识检索上下文
        - {root_cause_context}: 根因分析上下文
        - {similar_jira_context}: 相似问题上下文
        - {comments_context}: 评论分析上下文

        Args:
            prompt: 包含变量的 prompt
            context: 分析上下文

        Returns:
            替换后的 prompt
        """
        replacements = {
            '{knowledge_context}': self.format_knowledge_context(context),
            '{root_cause_context}': self.format_root_cause_context(context),
            '{similar_jira_context}': self.format_similar_jira_context(context),
            '{comments_context}': self.format_comments_context(context),
        }

        for var, value in replacements.items():
            prompt = prompt.replace(var, value)

        return prompt

    # ==================== 解析辅助 ====================

    def parse_json_response(
        self,
        response: str,
        expected_type: str = 'object'
    ) -> Optional[Any]:
        """
        解析 JSON 响应

        Args:
            response: LLM 响应
            expected_type: 期望的类型 ('object' 或 'array')

        Returns:
            解析后的 JSON，失败返回 None
        """
        return extract_json_from_llm(response, expected_type)

    def extract_field(
        self,
        text: str,
        field_name: str,
        pattern: Optional[str] = None
    ) -> str:
        """
        从文本中提取字段值

        Args:
            text: 文本内容
            field_name: 字段名（如 "直接原因"）
            pattern: 自定义正则模式（可选）

        Returns:
            提取的值，未找到返回空字符串
        """
        if pattern is None:
            # 默认模式：字段名 + 冒号 + 值
            pattern = rf'{re.escape(field_name)}[：:]\s*(.+?)(?=\n|$)'

        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def extract_key_value_pairs(
        self,
        text: str,
        keys: List[str]
    ) -> Dict[str, str]:
        """
        提取多个键值对

        Args:
            text: 文本内容
            keys: 键名列表

        Returns:
            键值对字典
        """
        result = {}
        for key in keys:
            result[key] = self.extract_field(text, key)
        return result

    def extract_list_items(
        self,
        text: str,
        max_items: int = 5
    ) -> List[str]:
        """
        提取列表项

        支持格式：
        - 数字列表：1. 项目
        - 破折号：- 项目
        - 星号：* 项目

        Args:
            text: 文本内容
            max_items: 最大项目数

        Returns:
            列表项
        """
        # 匹配各种列表格式
        items = re.findall(r'(?:^|\n)\s*(?:\d+[.、)]|[-*•])\s*(.+?)(?=\n|$)', text)

        # 清理并过滤
        items = [item.strip() for item in items if item.strip()]

        return items[:max_items]

    # ==================== 工具方法 ====================

    @staticmethod
    def build_chinese_requirements() -> str:
        """
        标准中文输出要求

        Returns:
            格式化的要求文本
        """
        return """要求：
- 必须用中文回答
- 直接输出最终答案，不要包含任何思考过程、推理步骤、分析过程
- 不要使用 <think> 标签或类似的思考标记
- 不要输出"让我分析"、"首先"、"然后"等过程性语言
- 立即给出结论性的回答"""

    def log_progress(self, message: str, flush: bool = True) -> None:
        """
        输出进度信息

        Args:
            message: 消息内容
            flush: 是否立即刷新输出
        """
        import sys
        analyzer_name = self.get_name()
        print(f"   [{analyzer_name}] {message}", flush=flush)

    def log_step(self, current: int, total: int, message: str = "") -> None:
        """
        输出步骤进度

        Args:
            current: 当前步骤
            total: 总步骤数
            message: 附加消息
        """
        msg = f"{current}/{total}"
        if message:
            msg += f": {message}"
        self.log_progress(msg)

    # ==================== 抽象方法 ====================

    @abstractmethod
    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行分析（子类必须实现）

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            分析结果
        """
        pass
