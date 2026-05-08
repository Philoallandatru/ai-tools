"""
文档拆分模块

将长文档按照 Markdown 标题层级拆分为多个小文档，
便于 LLM 处理和概念提取。
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DocumentSection:
    """文档章节"""
    title: str
    level: int  # 标题层级 (1-6)
    content: str
    start_line: int
    end_line: int

    def __str__(self):
        return f"{'#' * self.level} {self.title} (lines {self.start_line}-{self.end_line}, {len(self.content)} chars)"


class DocumentSplitter:
    """文档拆分器"""

    def __init__(self, max_chars: int = 10000, split_level: int = 1):
        """
        初始化拆分器

        Args:
            max_chars: 单个文档最大字符数
            split_level: 拆分的标题层级 (1-6)
        """
        self.max_chars = max_chars
        self.split_level = split_level
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def parse_document(self, content: str) -> List[DocumentSection]:
        """
        解析文档，提取所有章节

        Args:
            content: 文档内容

        Returns:
            章节列表
        """
        lines = content.split('\n')
        sections = []
        current_section = None

        for i, line in enumerate(lines):
            match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if match:
                # 保存上一个章节
                if current_section:
                    current_section['end_line'] = i - 1
                    current_section['content'] = '\n'.join(
                        lines[current_section['start_line']:i]
                    )
                    sections.append(DocumentSection(**current_section))

                # 开始新章节
                level = len(match.group(1))
                title = match.group(2).strip()
                current_section = {
                    'title': title,
                    'level': level,
                    'start_line': i,
                    'end_line': None,
                    'content': None
                }

        # 保存最后一个章节
        if current_section:
            current_section['end_line'] = len(lines) - 1
            current_section['content'] = '\n'.join(
                lines[current_section['start_line']:]
            )
            sections.append(DocumentSection(**current_section))

        return sections

    def split_by_level(self, sections: List[DocumentSection], level: int) -> List[List[DocumentSection]]:
        """
        按指定层级拆分章节

        Args:
            sections: 所有章节
            level: 拆分层级

        Returns:
            拆分后的章节组
        """
        groups = []
        current_group = []

        for section in sections:
            if section.level == level:
                # 遇到目标层级的标题，开始新组
                if current_group:
                    groups.append(current_group)
                current_group = [section]
            elif section.level > level:
                # 子章节，加入当前组
                if current_group:
                    current_group.append(section)
            else:
                # 更高层级的标题，结束当前组
                if current_group:
                    groups.append(current_group)
                    current_group = []
                current_group = [section]

        if current_group:
            groups.append(current_group)

        return groups

    def merge_sections(self, sections: List[DocumentSection]) -> str:
        """
        合并多个章节为一个文档

        Args:
            sections: 章节列表

        Returns:
            合并后的文档内容
        """
        return '\n\n'.join(section.content for section in sections)

    def split_by_size(self, content: str, max_size: int) -> List[str]:
        """
        按固定大小切分内容（当没有标题可用时）

        Args:
            content: 内容
            max_size: 最大大小

        Returns:
            切分后的内容列表
        """
        if len(content) <= max_size:
            return [content]

        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            if current_size + line_size > max_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def split_document(self, content: str, source_file: str) -> List[Tuple[str, str]]:
        """
        拆分文档

        Args:
            content: 文档内容
            source_file: 源文件名

        Returns:
            (文件名, 内容) 元组列表
        """
        # 解析文档
        sections = self.parse_document(content)

        if not sections:
            # 没有标题，按大小切分
            if len(content) > self.max_chars:
                chunks = self.split_by_size(content, self.max_chars)
                source_stem = Path(source_file).stem
                return [
                    (f"{source_stem}-chunk{i:02d}.md", chunk)
                    for i, chunk in enumerate(chunks, 1)
                ]
            return [(source_file, content)]

        # 按指定层级拆分
        groups = self.split_by_level(sections, self.split_level)

        # 生成拆分后的文档
        results = []
        source_stem = Path(source_file).stem

        for i, group in enumerate(groups, 1):
            if not group:
                continue

            # 合并章节内容
            merged_content = self.merge_sections(group)

            # 检查是否超过大小限制
            if len(merged_content) > self.max_chars:
                if self.split_level < 6:
                    # 尝试递归拆分
                    sub_splitter = DocumentSplitter(
                        max_chars=self.max_chars,
                        split_level=self.split_level + 1
                    )
                    sub_results = sub_splitter.split_document(merged_content, source_file)

                    # 如果递归拆分有效（产生了多个文档），使用递归结果
                    if len(sub_results) > 1:
                        for j, (_, sub_content) in enumerate(sub_results, 1):
                            filename = f"{source_stem}-part{i:02d}-{j:02d}.md"
                            results.append((filename, sub_content))
                        continue

                # 递归拆分无效或已达最大层级，按大小切分
                chunks = self.split_by_size(merged_content, self.max_chars)
                for j, chunk in enumerate(chunks, 1):
                    filename = f"{source_stem}-part{i:02d}-chunk{j:02d}.md"
                    main_title = group[0].title
                    metadata = f"""---
source_file: {source_file}
part: {i}/{len(groups)}
chunk: {j}/{len(chunks)}
section: {main_title}
---

"""
                    results.append((filename, metadata + chunk))
            else:
                # 生成文件名
                main_title = group[0].title
                # 清理标题中的特殊字符
                safe_title = re.sub(r'[^\w\s-]', '', main_title)
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                safe_title = safe_title[:50]  # 限制长度

                filename = f"{source_stem}-{i:02d}-{safe_title}.md"

                # 添加元数据
                metadata = f"""---
source_file: {source_file}
part: {i}/{len(groups)}
section: {main_title}
---

"""
                full_content = metadata + merged_content
                results.append((filename, full_content))

        return results

    def split_file(self, input_file: Path, output_dir: Path, dry_run: bool = False) -> List[Path]:
        """
        拆分文件并保存

        Args:
            input_file: 输入文件路径
            output_dir: 输出目录
            dry_run: 是否只显示结果不实际写入

        Returns:
            生成的文件路径列表
        """
        # 读取文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 拆分文档
        results = self.split_document(content, input_file.name)

        print(f"\n📄 拆分文档: {input_file.name}")
        print(f"   原文档大小: {len(content):,} 字符")
        print(f"   拆分为: {len(results)} 个文档")
        print(f"   拆分层级: {'#' * self.split_level} (level {self.split_level})")
        print(f"   最大字符数: {self.max_chars:,}")

        if dry_run:
            print("\n🔍 预览拆分结果 (dry-run):")
            for filename, content in results:
                print(f"   - {filename}: {len(content):,} 字符")
            return []

        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        output_files = []
        print("\n💾 保存文件:")
        for filename, content in results:
            output_path = output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            output_files.append(output_path)
            print(f"   ✓ {output_path}")

        print(f"\n✅ 完成! 生成 {len(output_files)} 个文件")
        return output_files
