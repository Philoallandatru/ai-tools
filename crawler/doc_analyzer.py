"""
文档分析器 - 批量分析文档小节并生成需求/测试用例建议报告
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from crawler.doc_splitter import DocumentSplitter, DocumentSection
from crawler.searcher import ContentSearcher, SearchMatch
from crawler.llm_client import BaseLLMClient, create_llm_client

logger = logging.getLogger(__name__)


@dataclass
class CodeSnippet:
    """代码片段"""
    file_path: str
    line_start: int
    line_end: int
    content: str
    match_keyword: str


@dataclass
class RetrievalContext:
    """检索上下文"""
    code_snippets: List[CodeSnippet]
    doc_snippets: List[CodeSnippet]  # 复用结构


@dataclass
class AnalysisResult:
    """分析结果"""
    section: DocumentSection
    llm_response: str
    retrieval_context: RetrievalContext
    keywords: List[str]
    image_references: List[Dict[str, str]]


class DocumentAnalyzer:
    """文档分析器"""

    def __init__(self, config_path: str = "configs/doc_analysis_config.yaml"):
        """
        初始化分析器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # 初始化组件
        self.splitter = DocumentSplitter(
            max_chars=self.config['splitting']['max_chars'],
            split_level=self.config['splitting']['split_level']
        )
        self.searcher = ContentSearcher()

        # 初始化 LLM 客户端
        llm_config = self.config['llm']
        if llm_config['provider'] == 'llmstudio':
            self.llm_client = create_llm_client(
                provider='llmstudio',
                base_url=llm_config.get('base_url', 'http://127.0.0.1:1234'),
                model=llm_config.get('model', 'qwen3.5-4b')
            )
        else:
            self.llm_client = create_llm_client(provider='mock')

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def analyze_document(
        self,
        doc_path: str,
        output_path: Optional[str] = None,
        dry_run: bool = False
    ) -> str:
        """
        分析文档并生成报告

        Args:
            doc_path: 文档路径
            output_path: 输出报告路径（可选）
            dry_run: 预览模式，不实际调用 LLM

        Returns:
            生成的报告文件路径
        """
        doc_path = Path(doc_path)
        if not doc_path.exists():
            raise FileNotFoundError(f"文档不存在: {doc_path}")

        print(f"\n📄 开始分析文档: {doc_path.name}")

        # 1. 切分文档
        print(f"   🔪 切分文档...")
        sections = self._split_document(doc_path)
        print(f"   ✓ 切分完成，共 {len(sections)} 个小节")

        if dry_run:
            print(f"\n🔍 预览模式 - 将处理以下小节:")
            for i, section in enumerate(sections, 1):
                print(f"   {i}. {section.title} ({len(section.content)} 字符)")
            return ""

        # 2. 分析每个小节
        results = []
        for i, section in enumerate(sections, 1):
            print(f"\n   📝 分析第 {i}/{len(sections)} 节: {section.title}")

            try:
                # 提取关键词
                keywords = self._extract_keywords(section.content)
                print(f"      关键词: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")

                # 提取图片引用
                images = self._extract_images(section.content)
                if images:
                    print(f"      📷 找到 {len(images)} 个图片引用")

                # 检索上下文
                print(f"      🔍 检索相关内容...")
                context = self._retrieve_context(section, keywords)
                print(f"      ✓ 找到 {len(context.code_snippets)} 个代码片段, {len(context.doc_snippets)} 个文档片段")

                # 构建 prompt
                prompt = self._build_prompt(section, context)

                # 调用 LLM
                print(f"      🤖 调用 LLM 分析...")
                llm_response = self._call_llm(prompt)
                print(f"      ✓ LLM 分析完成")

                results.append(AnalysisResult(
                    section=section,
                    llm_response=llm_response,
                    retrieval_context=context,
                    keywords=keywords,
                    image_references=images
                ))

            except Exception as e:
                # LLM 调用失败，立即停止
                error_msg = f"处理第 {i} 节 '{section.title}' 时失败: {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        # 3. 生成报告
        print(f"\n   📊 生成分析报告...")
        report_path = self._generate_report(doc_path, results, output_path)
        print(f"   ✓ 报告已保存: {report_path}")

        return str(report_path)

    def _split_document(self, doc_path: Path) -> List[DocumentSection]:
        """切分文档（复用 doc_splitter）"""
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = self.splitter.parse_document(content)

        # 按配置的层级过滤
        split_level = self.config['splitting']['split_level']
        filtered_sections = [s for s in sections if s.level == split_level]

        if not filtered_sections:
            # 如果没有找到指定层级的标题，返回所有章节
            return sections

        return filtered_sections

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词用于检索

        策略：
        1. 提取技术术语（大写缩写词，如 NVMe, CSTS, CC.EN）
        2. 提取驼峰命名或下划线命名的标识符
        3. 提取中文技术词汇（2-4 字）
        4. 去重并过滤
        """
        keywords = []

        # 正则模式
        patterns = [
            r'\b[A-Z]{2,}\b',                    # 大写缩写：NVMe, CSTS
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # 驼峰命名：ReadyState
            r'\b[a-z_]+_[a-z_]+\b',              # 下划线命名：nvme_reset
            r'[一-龥]{2,4}',             # 中文词汇
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        # 去重并过滤短词
        min_length = self.config['retrieval']['search']['min_match_length']
        keywords = list(set(k for k in keywords if len(k) >= min_length))

        return keywords

    def _extract_images(self, content: str) -> List[Dict[str, str]]:
        """
        从 Markdown 内容中提取图片引用

        Args:
            content: Markdown 文本内容

        Returns:
            图片引用列表，每项包含 alt 和 path
        """
        # Markdown 图片语法：![alt text](image_path)
        pattern = r'!\[(.*?)\]\((.*?)\)'
        matches = re.findall(pattern, content)

        images = []
        for alt, path in matches:
            images.append({
                'alt': alt.strip() if alt.strip() else '(无描述)',
                'path': path.strip()
            })

        return images

    def _retrieve_context(
        self,
        section: DocumentSection,
        keywords: List[str]
    ) -> RetrievalContext:
        """检索相关上下文"""
        code_snippets = []
        doc_snippets = []

        max_results = self.config['retrieval']['search']['max_results']

        # 检索代码库
        if self.config['retrieval']['code']['enabled']:
            code_context_lines = self.config['retrieval']['code']['context_lines']

            for keyword in keywords[:10]:  # 限制关键词数量
                try:
                    matches = self.searcher.search(
                        query=keyword,
                        file_type='all',
                        context_lines=code_context_lines,
                        use_regex=False,
                        max_results=max_results
                    )

                    # 过滤代码文件
                    code_matches = [
                        m for m in matches
                        if self._is_code_file(m.file_path)
                    ]

                    for match in code_matches[:2]:  # 每个关键词最多2个结果
                        snippet = self._format_code_snippet(match, keyword, code_context_lines)
                        if snippet:
                            code_snippets.append(snippet)

                except Exception as e:
                    logger.warning(f"检索关键词 '{keyword}' 失败: {e}")

        # 检索需求文档
        if self.config['retrieval']['docs']['enabled']:
            doc_context_lines = self.config['retrieval']['docs']['context_lines']
            docs_path = self.config['retrieval']['docs']['path']

            for keyword in keywords[:10]:
                try:
                    matches = self.searcher.search(
                        query=keyword,
                        file_type='all',
                        context_lines=doc_context_lines,
                        use_regex=False,
                        max_results=max_results
                    )

                    # 过滤文档文件
                    doc_matches = [
                        m for m in matches
                        if self._is_doc_file(m.file_path) and docs_path in str(m.file_path)
                    ]

                    for match in doc_matches[:2]:
                        snippet = self._format_code_snippet(match, keyword, doc_context_lines)
                        if snippet:
                            doc_snippets.append(snippet)

                except Exception as e:
                    logger.warning(f"检索文档关键词 '{keyword}' 失败: {e}")

        # 去重（基于文件路径和行号）
        code_snippets = self._deduplicate_snippets(code_snippets)
        doc_snippets = self._deduplicate_snippets(doc_snippets)

        return RetrievalContext(
            code_snippets=code_snippets[:max_results],
            doc_snippets=doc_snippets[:max_results]
        )

    def _is_code_file(self, file_path: Path) -> bool:
        """判断是否为代码文件"""
        code_extensions = ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.go', '.rs']
        return file_path.suffix in code_extensions

    def _is_doc_file(self, file_path: Path) -> bool:
        """判断是否为文档文件"""
        return file_path.suffix == '.md'

    def _format_code_snippet(
        self,
        match: SearchMatch,
        keyword: str,
        context_lines: int
    ) -> Optional[CodeSnippet]:
        """格式化代码片段"""
        try:
            # 计算行号范围
            line_start = match.line_number - len(match.context_before)
            line_end = match.line_number + len(match.context_after)

            # 组合内容
            content_lines = (
                match.context_before +
                [match.line_content] +
                match.context_after
            )
            content = '\n'.join(content_lines)

            return CodeSnippet(
                file_path=str(match.file_path),
                line_start=line_start,
                line_end=line_end,
                content=content,
                match_keyword=keyword
            )
        except Exception as e:
            logger.warning(f"格式化代码片段失败: {e}")
            return None

    def _deduplicate_snippets(self, snippets: List[CodeSnippet]) -> List[CodeSnippet]:
        """去重代码片段"""
        seen = set()
        unique = []

        for snippet in snippets:
            key = (snippet.file_path, snippet.line_start, snippet.line_end)
            if key not in seen:
                seen.add(key)
                unique.append(snippet)

        return unique

    def _build_prompt(
        self,
        section: DocumentSection,
        context: RetrievalContext
    ) -> str:
        """构建 LLM prompt"""
        # 格式化代码上下文
        if context.code_snippets:
            code_context = "\n\n".join([
                f"**文件**: `{snippet.file_path}:{snippet.line_start}-{snippet.line_end}`\n"
                f"```\n{snippet.content}\n```"
                for snippet in context.code_snippets
            ])
        else:
            code_context = "（未找到相关代码）"

        # 格式化文档上下文
        if context.doc_snippets:
            docs_context = "\n\n".join([
                f"**文件**: `{snippet.file_path}:{snippet.line_start}-{snippet.line_end}`\n"
                f"> {snippet.content}"
                for snippet in context.doc_snippets
            ])
        else:
            docs_context = "（未找到相关文档）"

        # 使用模板
        template = self.config['prompts']['user_template']
        prompt = template.format(
            section_content=section.content,
            code_context=code_context,
            docs_context=docs_context
        )

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（复用 jira_analyzer 的逻辑）"""
        system_prompt = self.config['prompts']['system']

        try:
            # 组合 system prompt 和 user prompt
            full_prompt = f"{system_prompt}\n\n{prompt}"
            response = self.llm_client.generate(full_prompt, max_tokens=2000)
            return response
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def _generate_report(
        self,
        doc_path: Path,
        results: List[AnalysisResult],
        output_path: Optional[str] = None
    ) -> Path:
        """生成最终的 Markdown 报告"""
        # 确定输出路径
        if output_path:
            report_path = Path(output_path)
        else:
            output_dir = Path(self.config['report']['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config['report']['filename_template'].format(
                source_filename=doc_path.stem,
                timestamp=timestamp
            )
            report_path = output_dir / filename

        # 生成报告内容
        report_lines = []

        # 标题和元数据
        report_lines.append("# 文档分析报告\n")
        report_lines.append(f"**源文档**: {doc_path}\n")
        report_lines.append(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append(f"**配置文件**: {self.config_path}\n")
        report_lines.append(f"**LLM 模型**: {self.config['llm']['model']}\n")
        report_lines.append("\n---\n")

        # 目录
        if self.config['report']['include_toc']:
            report_lines.append("\n## 目录\n")
            for i, result in enumerate(results, 1):
                anchor = self._generate_anchor(result.section.title, i)
                report_lines.append(f"- [第 {i} 节：{result.section.title}](#{anchor})\n")
            report_lines.append("- [总结](#总结)\n")
            report_lines.append("\n---\n")

        # 各小节分析
        for i, result in enumerate(results, 1):
            report_lines.append(f"\n## 第 {i} 节：{result.section.title}\n")

            # 原始内容
            report_lines.append("\n### 原始内容\n")
            report_lines.append(f"> {result.section.content[:500]}{'...' if len(result.section.content) > 500 else ''}\n")

            # 图片引用
            if result.image_references:
                report_lines.append("\n### 包含的图片\n")
                for img in result.image_references:
                    report_lines.append(f"- **{img['alt']}**: `{img['path']}`\n")

            # 检索到的上下文
            report_lines.append("\n### 检索到的相关上下文\n")

            if result.retrieval_context.code_snippets:
                report_lines.append(f"\n#### 代码参考 ({len(result.retrieval_context.code_snippets)} 个匹配)\n")
                for snippet in result.retrieval_context.code_snippets:
                    report_lines.append(f"\n**文件**: `{snippet.file_path}:{snippet.line_start}-{snippet.line_end}`\n")
                    report_lines.append(f"```\n{snippet.content}\n```\n")
            else:
                report_lines.append("\n#### 代码参考\n\n（未找到相关代码）\n")

            if result.retrieval_context.doc_snippets:
                report_lines.append(f"\n#### 需求文档参考 ({len(result.retrieval_context.doc_snippets)} 个匹配)\n")
                for snippet in result.retrieval_context.doc_snippets:
                    report_lines.append(f"\n**文件**: `{snippet.file_path}:{snippet.line_start}-{snippet.line_end}`\n")
                    report_lines.append(f"> {snippet.content}\n")
            else:
                report_lines.append("\n#### 需求文档参考\n\n（未找到相关文档）\n")

            # LLM 分析结果
            report_lines.append("\n### LLM 分析结果\n")
            report_lines.append(f"\n{result.llm_response}\n")
            report_lines.append("\n---\n")

        # 总结
        if self.config['report']['include_summary']:
            report_lines.append("\n## 总结\n")
            report_lines.append(self._generate_summary(results))

        # 写入文件
        report_content = ''.join(report_lines)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_path

    def _generate_anchor(self, title: str, index: int) -> str:
        """生成 Markdown 锚点"""
        # 简化：使用索引
        return f"第-{index}-节{title[:10]}"

    def _generate_summary(self, results: List[AnalysisResult]) -> str:
        """生成总结统计"""
        total_sections = len(results)
        total_code_snippets = sum(len(r.retrieval_context.code_snippets) for r in results)
        total_doc_snippets = sum(len(r.retrieval_context.doc_snippets) for r in results)
        total_images = sum(len(r.image_references) for r in results)

        summary_lines = []
        summary_lines.append("\n### 统计信息\n")
        summary_lines.append(f"- **总小节数**: {total_sections}\n")
        summary_lines.append(f"- **检索到的代码片段**: {total_code_snippets}\n")
        summary_lines.append(f"- **检索到的文档片段**: {total_doc_snippets}\n")
        summary_lines.append(f"- **包含的图片**: {total_images}\n")

        summary_lines.append("\n### 关键发现\n")
        summary_lines.append("（基于 LLM 分析结果，请查看各小节的详细分析）\n")

        return ''.join(summary_lines)
