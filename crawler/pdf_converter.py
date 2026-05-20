"""
PDF转Markdown转换器 - 使用pymupdf4llm提取PDF内容（为LLM优化）
"""

import pymupdf4llm
import fitz  # pymupdf (用于获取PDF信息)
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFConverter:
    """PDF转Markdown转换器（使用pymupdf4llm）"""

    def __init__(self):
        """初始化转换器"""
        pass

    def convert_to_markdown(
        self,
        pdf_path: str,
        output_path: Optional[str] = None,
        start_page: int = 0,
        end_page: Optional[int] = None,
        page_chunks: bool = False
    ) -> str:
        """
        将PDF转换为Markdown格式（为LLM优化）

        Args:
            pdf_path: PDF文件路径
            output_path: 输出Markdown文件路径（可选）
            start_page: 起始页码（从0开始）
            end_page: 结束页码（不包含，None表示到最后）
            page_chunks: 是否按页分块（True返回列表，False返回单个字符串）

        Returns:
            Markdown内容
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        logger.info(f"开始转换PDF: {pdf_path}")

        # 获取PDF信息
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        # 确定页码范围
        if end_page is None:
            end_page = total_pages
        else:
            end_page = min(end_page, total_pages)

        logger.info(f"PDF总页数: {total_pages}, 转换范围: {start_page + 1}-{end_page}")

        # 使用pymupdf4llm转换（为LLM优化）
        # 它会自动识别标题、段落、列表、表格等结构
        if page_chunks:
            # 按页分块
            md_text = pymupdf4llm.to_markdown(
                str(pdf_path),
                pages=list(range(start_page, end_page)),
                page_chunks=True
            )
        else:
            # 单个文档
            md_text = pymupdf4llm.to_markdown(
                str(pdf_path),
                pages=list(range(start_page, end_page))
            )

        # 添加元数据头部
        header = f"""# {pdf_path.stem}

**来源**: {pdf_path.name}
**页码范围**: {start_page + 1}-{end_page}
**总页数**: {total_pages}

---

"""

        if isinstance(md_text, list):
            # 如果是分块的，给每块添加页码标记
            final_markdown = header
            for i, chunk in enumerate(md_text):
                page_num = start_page + i + 1
                final_markdown += f"\n## Page {page_num}\n\n{chunk['text']}\n\n"
        else:
            final_markdown = header + md_text

        # 保存到文件
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
            logger.info(f"Markdown已保存到: {output_path}")

        return final_markdown

    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        获取PDF文件信息

        Args:
            pdf_path: PDF文件路径

        Returns:
            PDF信息字典
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        doc = fitz.open(pdf_path)

        info = {
            'filename': pdf_path.name,
            'total_pages': len(doc),
            'metadata': doc.metadata,
            'file_size_mb': pdf_path.stat().st_size / (1024 * 1024)
        }

        doc.close()
        return info

    def extract_page_range(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int,
        output_path: str
    ) -> None:
        """
        提取PDF的指定页码范围并保存为新PDF

        Args:
            pdf_path: 源PDF文件路径
            start_page: 起始页码（从0开始）
            end_page: 结束页码（不包含）
            output_path: 输出PDF文件路径
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

        doc = fitz.open(pdf_path)

        # 创建新文档
        new_doc = fitz.open()

        # 复制指定页面
        for page_num in range(start_page, min(end_page, len(doc))):
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

        # 保存
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_doc.save(output_path)

        doc.close()
        new_doc.close()

        logger.info(f"已提取页面 {start_page}-{end_page} 到: {output_path}")


def main():
    """命令行测试"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python pdf_converter.py <pdf_path> [output_path] [start_page] [end_page]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    start_page = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    end_page = int(sys.argv[4]) if len(sys.argv) > 4 else None

    converter = PDFConverter()

    # 显示PDF信息
    info = converter.get_pdf_info(pdf_path)
    print(f"\nPDF信息:")
    print(f"   文件名: {info['filename']}")
    print(f"   总页数: {info['total_pages']}")
    print(f"   文件大小: {info['file_size_mb']:.2f} MB")
    if info['metadata'].get('title'):
        print(f"   标题: {info['metadata']['title']}")

    # 转换
    print(f"\n开始转换...")
    markdown = converter.convert_to_markdown(pdf_path, output_path, start_page, end_page)

    if output_path:
        print(f"转换完成: {output_path}")
        print(f"   内容长度: {len(markdown):,} 字符")
    else:
        print(f"转换完成，共 {len(markdown):,} 字符")
        print(f"\n预览前500字符:")
        print(markdown[:500])


if __name__ == '__main__':
    main()
