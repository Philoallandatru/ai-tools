"""
测试文件类型验证功能

确保 analyze-doc 命令只接受 Markdown 文件，
并对 PDF 等其他文件类型给出友好的错误提示。
"""

import pytest
from pathlib import Path
from click.testing import CliRunner
from cli import cli


class TestFileTypeValidation:
    """测试文件类型验证"""

    def test_analyze_doc_rejects_pdf_files(self, tmp_path):
        """测试 analyze-doc 拒绝 PDF 文件"""
        # 创建一个假的 PDF 文件
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%\xb5\xb5\xb5\xb5")  # PDF 文件头

        runner = CliRunner()
        result = runner.invoke(cli, [
            'analyze-doc',
            str(pdf_file),
            '--config', 'configs/doc_analysis_config.yaml'
        ])

        # 应该失败（但不是崩溃）
        assert result.exit_code == 0  # 正常退出，只是提示错误
        assert "不支持的文件类型: .pdf" in result.output
        assert "analyze-doc 命令仅支持 Markdown 文件" in result.output
        assert "convert-pdf" in result.output  # 应该提示正确的工作流

    def test_analyze_doc_accepts_markdown_files(self, tmp_path):
        """测试 analyze-doc 接受 Markdown 文件"""
        # 创建一个简单的 Markdown 文件
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nThis is a test.", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(cli, [
            'analyze-doc',
            str(md_file),
            '--config', 'configs/doc_analysis_config.yaml',
            '--dry-run'  # 使用 dry-run 避免实际调用 LLM
        ])

        # 应该成功
        assert result.exit_code == 0
        assert "将分析文档" in result.output

    def test_analyze_doc_accepts_markdown_extension(self, tmp_path):
        """测试 analyze-doc 接受 .markdown 扩展名"""
        md_file = tmp_path / "test.markdown"
        md_file.write_text("# Test\n\nThis is a test.", encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(cli, [
            'analyze-doc',
            str(md_file),
            '--config', 'configs/doc_analysis_config.yaml',
            '--dry-run'
        ])

        assert result.exit_code == 0
        assert "将分析文档" in result.output

    def test_document_splitter_rejects_non_markdown(self, tmp_path):
        """测试 DocumentSplitter 拒绝非 Markdown 文件"""
        from crawler.doc_splitter import DocumentSplitter

        # 创建一个假的 PDF 文件
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%\xb5\xb5\xb5\xb5")

        splitter = DocumentSplitter()
        output_dir = tmp_path / "output"

        with pytest.raises(ValueError) as exc_info:
            splitter.split_file(pdf_file, output_dir)

        assert "不支持的文件类型: .pdf" in str(exc_info.value)
        assert "DocumentSplitter 仅支持 Markdown 文件" in str(exc_info.value)

    def test_document_splitter_handles_encoding_errors(self, tmp_path):
        """测试 DocumentSplitter 处理编码错误"""
        from crawler.doc_splitter import DocumentSplitter

        # 创建一个非 UTF-8 编码的 .md 文件
        md_file = tmp_path / "test.md"
        md_file.write_bytes(b"\xff\xfe# Test\n\nGBK content: \xb5\xc4")  # UTF-16 BOM + 混合内容

        splitter = DocumentSplitter()
        output_dir = tmp_path / "output"

        with pytest.raises(ValueError) as exc_info:
            splitter.split_file(md_file, output_dir)

        assert "无法读取文件" in str(exc_info.value)
        assert "文件编码不是 UTF-8" in str(exc_info.value)
