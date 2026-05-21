"""
文档分析器 - 批量分析文档小节并生成需求/测试用例建议报告
"""

import re
import yaml
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# 设置环境变量强制 UTF-8 输出（Windows 兼容）
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from crawler.doc_splitter import DocumentSplitter, DocumentSection
from crawler.searcher import ContentSearcher, SearchMatch
from crawler.llm_client import BaseLLMClient, LLMClientFactory
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.section_processor import DocumentProcessor, SectionGroup

logger = logging.getLogger(__name__)

def safe_print(text: str):
    """
    安全打印文本，处理 Windows 控制台编码问题

    Args:
        text: 要打印的文本
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # 如果遇到编码错误，替换无法编码的字符
        safe_text = text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
        print(safe_text)


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

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化分析器

        Args:
            config_path: 配置文件路径（默认使用主配置文件）
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # 初始化组件
        self.splitter = DocumentSplitter(
            max_chars=self.config['splitting']['max_chars'],
            split_level=self.config['splitting']['split_level']
        )

        # 初始化两个搜索器：一个用于代码，一个用于文档
        code_base_dir = self.config['retrieval']['code'].get('base_dir', '.')
        self.code_searcher = ContentSearcher(source_dir=code_base_dir)
        docs_path = self.config['retrieval']['docs']['path']
        self.doc_searcher = ContentSearcher(source_dir=docs_path)

        # 初始化 LLM 客户端（使用文档分析专用配置）
        llm_config = self.config['llm']
        self.llm_client = LLMClientFactory.create_from_config(llm_config)

        # 初始化 Vision LLM 客户端（如果启用）
        vision_config = self.config.get('vision', {})
        if vision_config.get('enabled', False):
            self.vision_client = LLMClientFactory.create_from_config(vision_config)
        else:
            self.vision_client = None

        # 初始化共享的关键词提取器
        self.keyword_extractor = KeywordExtractor(
            llm_client=self.llm_client,
            min_length=2,
            max_length=20,
            max_keywords=15
        )

        # 初始化文档处理器（用于智能分组和过滤）
        self.doc_processor = DocumentProcessor(self.config)

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件（使用统一的配置管理器）"""
        from crawler.config import load_config

        # 使用统一的配置管理器加载配置
        full_config = load_config(str(self.config_path))

        # 如果是主配置文件，提取 doc_analysis 部分
        if 'doc_analysis' in full_config:
            doc_config = full_config['doc_analysis'].copy()

            # 合并 LLM 配置：优先使用 doc_analysis 专用配置
            if 'llm' in full_config:
                base_llm = full_config['llm'].copy()
                # 如果有 doc_analysis 专用 LLM 配置，覆盖基础配置
                if 'doc_analysis' in base_llm:
                    base_llm.update(base_llm.pop('doc_analysis'))
                doc_config['llm'] = base_llm

            # 合并 Vision LLM 配置
            if 'llm' in full_config and 'vision' in full_config['llm']:
                doc_config['vision'] = full_config['llm']['vision']

            return doc_config

        # 兼容旧的独立配置文件格式
        return full_config

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

        print(f"\n[开始] 分析文档: {doc_path.name}")

        # 1. 切分文档
        print(f"   [切分] 切分文档...")
        sections = self._split_document(doc_path)
        print(f"   [完成] 切分完成，共 {len(sections)} 个小节")

        # 2. 智能处理小节（过滤 + 分组）
        print(f"   [处理] 智能处理小节...")
        section_groups = self.doc_processor.process_sections(sections)
        print(f"   [完成] 处理完成，共 {len(section_groups)} 个小节组")

        if dry_run:
            print(f"\n[预览] 预览模式 - 将处理以下小节组:")
            for i, group in enumerate(section_groups, 1):
                safe_print(f"   {i}. {group.title} ({len(group.sections)} 个小节, {group.total_chars} 字符)")
                for section in group.sections:
                    safe_print(f"      - {section.title}")
            return ""

        # 3. 分析每个小节组
        results = []
        for i, group in enumerate(section_groups, 1):
            safe_print(f"\n   [分析] 第 {i}/{len(section_groups)} 组: {group.title}")
            safe_print(f"      包含 {len(group.sections)} 个小节: {', '.join(group.section_titles)}")

            try:
                # 使用合并后的内容进行分析
                combined_content = group.combined_content

                # 提取关键词
                keywords = self._extract_keywords(combined_content)
                print(f"      关键词: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")

                # 提取图片引用（从所有小节）
                images = []
                image_analyses = {}
                for section in group.sections:
                    section_images = self._extract_images(section.content)
                    images.extend(section_images)

                if images:
                    print(f"      [图片] 找到 {len(images)} 个图片引用")
                    # 分析图片内容
                    if self.vision_client:
                        for img in images:
                            print(f"         分析图片: {img['path']}")
                            analysis = self._analyze_image(Path(img['path']), doc_path.parent)
                            if analysis:
                                image_analyses[img['path']] = analysis
                                print(f"         [完成] 图片分析完成")
                            else:
                                print(f"         [警告] 图片分析失败")

                # 检索上下文（使用合并后的内容）
                print(f"      [检索] 检索相关内容...")
                # 创建一个临时的 section 对象用于检索
                temp_section = type('obj', (object,), {
                    'title': group.title,
                    'content': combined_content,
                    'level': group.sections[0].level if group.sections else 2
                })()
                context = self._retrieve_context(temp_section, keywords)
                print(f"      [完成] 找到 {len(context.code_snippets)} 个代码片段, {len(context.doc_snippets)} 个文档片段")

                # 构建 prompt（使用合并后的内容）
                prompt = self._build_prompt(temp_section, context)

                # 调用 LLM
                print(f"      [LLM] 调用 LLM 分析...")
                llm_response = self._call_llm(prompt)
                print(f"      [完成] LLM 分析完成")

                # 创建结果，包含图片分析和小节组信息
                result = AnalysisResult(
                    section=temp_section,
                    llm_response=llm_response,
                    retrieval_context=context,
                    keywords=keywords,
                    image_references=images
                )
                # 添加图片分析结果和小节组信息（作为额外属性）
                result.image_analyses = image_analyses
                result.section_group = group
                results.append(result)

            except Exception as e:
                # LLM 调用失败，立即停止
                error_msg = f"处理第 {i} 组 '{group.title}' 时失败: {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        # 3. 生成报告
        print(f"\n   [报告] 生成分析报告...")
        report_path = self._generate_report(doc_path, results, output_path, section_groups)
        print(f"   [完成] 报告已保存: {report_path}")

        return str(report_path)

    def _split_document(self, doc_path: Path) -> List[DocumentSection]:
        """切分文档（复用 doc_splitter）"""
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sections = self.splitter.parse_document(content)

        # 按配置的层级分组
        split_level = self.config['splitting']['split_level']
        section_groups = self.splitter.split_by_level(sections, split_level)

        if not section_groups:
            # 如果没有找到指定层级的标题，返回所有章节
            return sections

        # 合并每组的内容为一个 DocumentSection
        merged_sections = []
        for group in section_groups:
            if not group:
                continue

            # 使用第一个章节（主标题）的元数据
            main_section = group[0]
            # 合并所有子章节的内容
            merged_content = self.splitter.merge_sections(group)

            merged_section = DocumentSection(
                title=main_section.title,
                level=main_section.level,
                content=merged_content,
                start_line=main_section.start_line,
                end_line=group[-1].end_line
            )
            merged_sections.append(merged_section)

        return merged_sections

    def _extract_keywords(self, text: str) -> List[str]:
        """
        使用共享的 KeywordExtractor 从文本中提取关键词

        Args:
            text: 文档文本内容

        Returns:
            关键词列表
        """
        logger.info("=" * 60)
        logger.info("开始提取关键词")
        logger.info(f"文本长度: {len(text)} 字符")
        logger.info(f"文本预览: {text[:200]}...")

        keywords = self.keyword_extractor.extract_from_text(
            text=text,
            context="document",
            max_tokens=300
        )

        logger.info(f"提取到 {len(keywords)} 个关键词: {keywords}")
        logger.info("=" * 60)

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

    def _analyze_image(self, image_path: Path, doc_base_path: Path) -> Optional[str]:
        """
        使用 vision LLM 分析图片内容

        Args:
            image_path: 图片相对路径
            doc_base_path: 文档所在目录（用于解析相对路径）

        Returns:
            图片分析结果，如果失败返回 None
        """
        if not self.vision_client:
            return None

        try:
            import base64
            from PIL import Image
            import io

            # 解析图片的绝对路径
            if image_path.is_absolute():
                full_path = image_path
            else:
                full_path = doc_base_path / image_path

            if not full_path.exists():
                logger.warning(f"图片不存在: {full_path}")
                return None

            # 读取并压缩图片
            img = Image.open(full_path)

            # 压缩图片到合理大小（最大边 512px）
            max_size = 512
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 转换为 JPEG 格式并压缩
            buffer = io.BytesIO()
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(buffer, format='JPEG', quality=70)
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # 构建 vision API 请求
            vision_config = self.config.get('vision_llm', {})
            prompt = self.config['prompts'].get('image_analysis', '请描述这张图片的内容。')

            # 使用 OpenAI vision API 格式
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]

            # 调用 vision LLM（增加超时时间）
            max_tokens = vision_config.get('max_tokens', 500)
            timeout = vision_config.get('timeout', 180)  # 默认 180 秒

            # 临时修改客户端超时
            import requests
            response = requests.post(
                f"{self.vision_client.base_url}/v1/chat/completions",
                json={
                    "model": self.vision_client.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3
                },
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=timeout
            )
            response.raise_for_status()
            response.encoding = 'utf-8'

            result = response.json()
            return result['choices'][0]['message']['content'].strip()

        except Exception as e:
            logger.error(f"图片分析失败 {image_path}: {e}")
            return None

    def _retrieve_context(
        self,
        section: DocumentSection,
        keywords: List[str]
    ) -> RetrievalContext:
        """检索相关上下文"""
        logger.info("\n" + "=" * 80)
        logger.info("开始检索相关上下文")
        logger.info("=" * 80)

        code_snippets = []
        doc_snippets = []

        max_results = self.config['retrieval']['search']['max_results']

        # 检索代码库
        if self.config['retrieval']['code']['enabled']:
            logger.info("\n[代码检索] 开始检索代码库")
            code_config = self.config['retrieval']['code']
            logger.info(f"  配置信息:")
            logger.info(f"    - 基础目录: {code_config.get('base_dir', '.')}")
            logger.info(f"    - 文件类型: {code_config.get('patterns', [])}")
            logger.info(f"    - 排除目录: {code_config.get('exclude_dirs', [])}")
            logger.info(f"    - 上下文行数: {code_config['context_lines']}")
            logger.info(f"    - 最大结果数: {max_results}")

            code_context_lines = code_config['context_lines']
            keywords_to_search = keywords[:10]  # 限制关键词数量
            logger.info(f"\n  将搜索 {len(keywords_to_search)} 个关键词: {keywords_to_search}")

            for i, keyword in enumerate(keywords_to_search, 1):
                logger.info(f"\n  [{i}/{len(keywords_to_search)}] 搜索关键词: '{keyword}'")
                try:
                    matches = self.code_searcher.search(
                        query=keyword,
                        file_type='all',
                        context_lines=code_context_lines,
                        use_regex=False,
                        max_results=max_results
                    )

                    logger.info(f"      原始匹配数: {len(matches)}")

                    # 过滤代码文件
                    code_matches = [
                        m for m in matches
                        if self._is_code_file(m.file_path)
                    ]

                    logger.info(f"      过滤后代码文件匹配数: {len(code_matches)}")

                    if code_matches:
                        logger.info(f"      匹配的文件:")
                        for match in code_matches[:2]:  # 每个关键词最多2个结果
                            logger.info(f"        - {match.file_path}:{match.line_number}")
                            snippet = self._format_code_snippet(match, keyword, code_context_lines)
                            if snippet:
                                code_snippets.append(snippet)
                                logger.info(f"          [OK] 已添加代码片段 (行 {snippet.line_start}-{snippet.line_end})")
                    else:
                        logger.info(f"      未找到匹配的代码文件")

                except Exception as e:
                    logger.warning(f"      [ERROR] 检索失败: {e}")

            logger.info(f"\n  [代码检索] 完成，共收集 {len(code_snippets)} 个代码片段")

        else:
            logger.info("\n[代码检索] 已禁用")

        # 检索需求文档
        if self.config['retrieval']['docs']['enabled']:
            logger.info("\n[文档检索] 开始检索需求文档")
            docs_config = self.config['retrieval']['docs']
            logger.info(f"  配置信息:")
            logger.info(f"    - 文档目录: {docs_config['path']}")
            logger.info(f"    - 文件类型: {docs_config.get('patterns', [])}")
            logger.info(f"    - 排除文件: {docs_config.get('exclude_files', [])}")
            logger.info(f"    - 上下文行数: {docs_config['context_lines']}")
            logger.info(f"    - 最大结果数: {max_results}")

            doc_context_lines = docs_config['context_lines']
            keywords_to_search = keywords[:10]
            logger.info(f"\n  将搜索 {len(keywords_to_search)} 个关键词: {keywords_to_search}")

            for i, keyword in enumerate(keywords_to_search, 1):
                logger.info(f"\n  [{i}/{len(keywords_to_search)}] 搜索关键词: '{keyword}'")
                try:
                    matches = self.doc_searcher.search(
                        query=keyword,
                        file_type='all',
                        context_lines=doc_context_lines,
                        use_regex=False,
                        max_results=max_results
                    )

                    logger.info(f"      原始匹配数: {len(matches)}")

                    # 过滤文档文件
                    doc_matches = [
                        m for m in matches
                        if self._is_doc_file(m.file_path)
                    ]

                    logger.info(f"      过滤后文档文件匹配数: {len(doc_matches)}")

                    if doc_matches:
                        logger.info(f"      匹配的文件:")
                        for match in doc_matches[:2]:
                            logger.info(f"        - {match.file_path}:{match.line_number}")
                            snippet = self._format_code_snippet(match, keyword, doc_context_lines)
                            if snippet:
                                doc_snippets.append(snippet)
                                logger.info(f"          [OK] 已添加文档片段 (行 {snippet.line_start}-{snippet.line_end})")
                    else:
                        logger.info(f"      未找到匹配的文档文件")

                except Exception as e:
                    logger.warning(f"      [ERROR] 检索失败: {e}")

            logger.info(f"\n  [文档检索] 完成，共收集 {len(doc_snippets)} 个文档片段")

        else:
            logger.info("\n[文档检索] 已禁用")

        # 去重（基于文件路径和行号）
        logger.info("\n[去重处理]")
        logger.info(f"  去重前: 代码片段 {len(code_snippets)} 个, 文档片段 {len(doc_snippets)} 个")

        code_snippets = self._deduplicate_snippets(code_snippets)
        doc_snippets = self._deduplicate_snippets(doc_snippets)

        logger.info(f"  去重后: 代码片段 {len(code_snippets)} 个, 文档片段 {len(doc_snippets)} 个")

        # 限制最终结果数量
        final_code_snippets = code_snippets[:max_results]
        final_doc_snippets = doc_snippets[:max_results]

        if len(code_snippets) > max_results:
            logger.info(f"  代码片段超过限制，截取前 {max_results} 个")
        if len(doc_snippets) > max_results:
            logger.info(f"  文档片段超过限制，截取前 {max_results} 个")

        logger.info("\n[检索总结]")
        logger.info(f"  最终返回: 代码片段 {len(final_code_snippets)} 个, 文档片段 {len(final_doc_snippets)} 个")

        if final_code_snippets:
            logger.info(f"  代码片段来源文件:")
            for snippet in final_code_snippets:
                logger.info(f"    - {snippet.file_path}:{snippet.line_start}-{snippet.line_end} (关键词: {snippet.match_keyword})")

        if final_doc_snippets:
            logger.info(f"  文档片段来源文件:")
            for snippet in final_doc_snippets:
                logger.info(f"    - {snippet.file_path}:{snippet.line_start}-{snippet.line_end} (关键词: {snippet.match_keyword})")

        logger.info("=" * 80 + "\n")

        return RetrievalContext(
            code_snippets=final_code_snippets,
            doc_snippets=final_doc_snippets
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
        output_path: Optional[str] = None,
        section_groups: Optional[List[SectionGroup]] = None
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

        # 添加分析策略信息
        strategy = self.config.get('splitting', {}).get('strategy', 'fixed')
        if strategy == 'smart' and section_groups:
            report_lines.append(f"**分析策略**: 智能合并 ({len(section_groups)} 个小节组)\n")
        else:
            report_lines.append(f"**分析策略**: 固定拆分 ({len(results)} 个小节)\n")

        report_lines.append("\n---\n")

        # 目录
        if self.config['report']['include_toc']:
            report_lines.append("\n## 目录\n")
            for i, result in enumerate(results, 1):
                anchor = self._generate_anchor(result.section.title, i)
                title = result.section.title

                # 如果有小节组信息，显示包含的小节
                if hasattr(result, 'section_group') and result.section_group:
                    group = result.section_group
                    if len(group.sections) > 1:
                        title = f"{title} (包含 {len(group.sections)} 个小节)"

                report_lines.append(f"- [第 {i} 组：{title}](#{anchor})\n")
            report_lines.append("- [总结](#总结)\n")
            report_lines.append("\n---\n")

        # 各小节/小节组分析
        for i, result in enumerate(results, 1):
            # 检查是否有小节组信息
            if hasattr(result, 'section_group') and result.section_group:
                group = result.section_group
                report_lines.append(f"\n## 第 {i} 组：{result.section.title}\n")

                # 显示包含的小节
                if len(group.sections) > 1:
                    report_lines.append(f"\n**包含小节**: {', '.join(group.section_titles)}\n")
                    report_lines.append(f"**总字符数**: {group.total_chars}\n")
            else:
                report_lines.append(f"\n## 第 {i} 节：{result.section.title}\n")

            # 原始内容（简化显示）
            report_lines.append("\n### 原始内容\n")
            content_preview = result.section.content[:500]
            if len(result.section.content) > 500:
                content_preview += "..."
            report_lines.append(f"> {content_preview}\n")

            # 图片引用
            if result.image_references:
                report_lines.append("\n### 包含的图片\n")
                for img in result.image_references:
                    report_lines.append(f"- **{img['alt']}**: `{img['path']}`\n")

                    # 如果有图片分析结果，添加到报告中
                    if hasattr(result, 'image_analyses') and img['path'] in result.image_analyses:
                        report_lines.append(f"\n**图片分析**:\n")
                        report_lines.append(f"{result.image_analyses[img['path']]}\n")

            # 提取的关键词
            if result.keywords:
                report_lines.append(f"\n**关键词**: {', '.join(result.keywords[:10])}\n")

            # 检索到的上下文（简化显示）
            report_lines.append("\n### 检索到的相关上下文\n")

            if result.retrieval_context.code_snippets:
                report_lines.append(f"\n#### 代码参考 ({len(result.retrieval_context.code_snippets)} 个匹配)\n")
                for snippet in result.retrieval_context.code_snippets[:3]:  # 只显示前3个
                    report_lines.append(f"\n**文件**: `{snippet.file_path}:{snippet.line_start}-{snippet.line_end}`\n")
                    report_lines.append(f"```\n{snippet.content}\n```\n")
                if len(result.retrieval_context.code_snippets) > 3:
                    report_lines.append(f"\n（还有 {len(result.retrieval_context.code_snippets) - 3} 个匹配未显示）\n")
            else:
                report_lines.append("\n#### 代码参考\n\n（未找到相关代码）\n")

            if result.retrieval_context.doc_snippets:
                report_lines.append(f"\n#### 需求文档参考 ({len(result.retrieval_context.doc_snippets)} 个匹配)\n")
                for snippet in result.retrieval_context.doc_snippets[:3]:  # 只显示前3个
                    report_lines.append(f"\n**文件**: `{snippet.file_path}:{snippet.line_start}-{snippet.line_end}`\n")
                    report_lines.append(f"> {snippet.content}\n")
                if len(result.retrieval_context.doc_snippets) > 3:
                    report_lines.append(f"\n（还有 {len(result.retrieval_context.doc_snippets) - 3} 个匹配未显示）\n")
            else:
                report_lines.append("\n#### 需求文档参考\n\n（未找到相关文档）\n")

            # LLM 分析结果
            report_lines.append("\n### LLM 分析结果\n")
            report_lines.append(f"\n{result.llm_response}\n")
            report_lines.append("\n---\n")

        # 总结
        if self.config['report']['include_summary']:
            report_lines.append("\n## 总结\n")
            report_lines.append(self._generate_summary(results, section_groups))

        # 写入文件
        report_content = ''.join(report_lines)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_path

    def _generate_anchor(self, title: str, index: int) -> str:
        """
        生成 Markdown 锚点

        遵循 GitHub Flavored Markdown 锚点规则：
        1. 转为小写
        2. 移除特殊字符（保留字母、数字、连字符、下划线、中文）
        3. 空格转为连字符

        Args:
            title: 标题文本
            index: 章节索引

        Returns:
            锚点字符串
        """
        # 构建完整标题
        full_title = f"第-{index}-节：{title}"

        # 移除 Markdown 格式符号
        anchor = full_title.replace('*', '').replace('`', '').replace('[', '').replace(']', '')

        # 空格转为连字符
        anchor = anchor.replace(' ', '-')

        # 移除其他特殊字符（保留字母、数字、连字符、下划线、中文）
        import re
        anchor = re.sub(r'[^\w一-鿿-]', '', anchor)

        return anchor

    def _generate_summary(self, results: List[AnalysisResult], section_groups: Optional[List[SectionGroup]] = None) -> str:
        """生成总结统计"""
        total_sections = len(results)
        total_code_snippets = sum(len(r.retrieval_context.code_snippets) for r in results)
        total_doc_snippets = sum(len(r.retrieval_context.doc_snippets) for r in results)
        total_images = sum(len(r.image_references) for r in results)

        summary_lines = []
        summary_lines.append("\n### 统计信息\n")

        # 如果使用了智能分组，显示分组信息
        if section_groups:
            original_sections = sum(len(g.sections) for g in section_groups)
            summary_lines.append(f"- **原始小节数**: {original_sections}\n")
            summary_lines.append(f"- **合并后小节组数**: {total_sections}\n")
            summary_lines.append(f"- **压缩率**: {(1 - total_sections/original_sections)*100:.1f}%\n")
        else:
            summary_lines.append(f"- **总小节数**: {total_sections}\n")

        summary_lines.append(f"- **检索到的代码片段**: {total_code_snippets}\n")
        summary_lines.append(f"- **检索到的文档片段**: {total_doc_snippets}\n")
        summary_lines.append(f"- **包含的图片**: {total_images}\n")

        summary_lines.append("\n### 关键发现\n")
        summary_lines.append("（基于 LLM 分析结果，请查看各小节的详细分析）\n")

        return ''.join(summary_lines)
