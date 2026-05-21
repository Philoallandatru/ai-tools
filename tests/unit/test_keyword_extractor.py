"""
测试统一的关键词提取器
"""

import pytest
from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.llm_client import MockLLMClient


class TestKeywordExtractor:
    """测试关键词提取器"""

    def test_extract_with_regex_basic(self):
        """测试基础正则表达式提取"""
        extractor = KeywordExtractor()

        text = "NVMe Reset功能需要实现spdk_nvme_ctrlr_reset接口"
        keywords = extractor.extract_from_text(text)

        assert "NVMe" in keywords
        assert "Reset" in keywords
        assert len(keywords) <= 15

    def test_extract_with_regex_filters_stop_words(self):
        """测试过滤停用词"""
        extractor = KeywordExtractor()

        text = "This is a Test Demo with Error and Warning"
        keywords = extractor.extract_from_text(text)

        # 停用词应该被过滤
        assert "Test" not in keywords
        assert "Demo" not in keywords
        assert "Error" not in keywords

    def test_extract_with_regex_camel_case(self):
        """测试提取驼峰命名"""
        extractor = KeywordExtractor()

        text = "使用 nvmeCtrlrReset 和 spdkNvmeInit 函数"
        keywords = extractor.extract_from_text(text)

        assert "nvmeCtrlrReset" in keywords
        assert "spdkNvmeInit" in keywords

    def test_extract_with_regex_snake_case(self):
        """测试提取下划线命名"""
        extractor = KeywordExtractor()

        text = "调用 spdk_nvme_ctrlr_reset 和 nvme_init_controller"
        keywords = extractor.extract_from_text(text)

        assert "spdk_nvme_ctrlr_reset" in keywords
        assert "nvme_init_controller" in keywords

    def test_extract_respects_length_limits(self):
        """测试长度限制"""
        extractor = KeywordExtractor(min_length=3, max_length=10)

        text = "AB VeryLongKeywordThatExceedsLimit NVMe OK"
        keywords = extractor.extract_from_text(text)

        # 太短的应该被过滤
        assert "AB" not in keywords
        assert "OK" not in keywords

        # 太长的应该被过滤
        assert "VeryLongKeywordThatExceedsLimit" not in keywords

        # 合适长度的应该保留
        assert "NVMe" in keywords

    def test_extract_respects_max_keywords(self):
        """测试最大关键词数量限制"""
        extractor = KeywordExtractor(max_keywords=5)

        text = "Keyword1 Keyword2 Keyword3 Keyword4 Keyword5 Keyword6 Keyword7"
        keywords = extractor.extract_from_text(text)

        assert len(keywords) <= 5

    def test_extract_from_jira_data(self):
        """测试从 Jira 数据提取"""
        extractor = KeywordExtractor()

        jira_data = {
            'title': 'NVMe Reset Issue',
            'description': 'The spdk_nvme_ctrlr_reset function fails with PCIe error'
        }

        keywords = extractor.extract_from_jira(jira_data)

        assert "NVMe" in keywords
        assert "Reset" in keywords
        assert "Issue" not in keywords  # 停用词

    def test_extract_with_mock_llm(self):
        """测试使用 Mock LLM 提取"""
        mock_llm = MockLLMClient()
        mock_llm.set_response('["NVMe", "Reset", "Controller", "PCIe"]')

        extractor = KeywordExtractor(llm_client=mock_llm)

        text = "NVMe controller reset functionality"
        keywords = extractor.extract_from_text(text)

        assert "NVMe" in keywords
        assert "Reset" in keywords
        assert "Controller" in keywords

    def test_extract_with_llm_fallback_on_error(self):
        """测试 LLM 失败时回退到正则"""
        mock_llm = MockLLMClient()
        mock_llm.set_response('invalid json')  # 无效响应

        extractor = KeywordExtractor(llm_client=mock_llm)

        text = "NVMe Reset functionality"
        keywords = extractor.extract_from_text(text)

        # 应该回退到正则提取
        assert len(keywords) > 0
        assert "NVMe" in keywords

    def test_extract_deduplicates_keywords(self):
        """测试关键词去重"""
        extractor = KeywordExtractor()

        text = "NVMe NVMe Reset Reset Controller Controller"
        keywords = extractor.extract_from_text(text)

        # 每个关键词应该只出现一次
        assert keywords.count("NVMe") == 1
        assert keywords.count("Reset") == 1
        assert keywords.count("Controller") == 1

    def test_extract_with_different_contexts(self):
        """测试不同上下文的提取"""
        mock_llm = MockLLMClient()
        mock_llm.set_response('["keyword1", "keyword2"]')

        extractor = KeywordExtractor(llm_client=mock_llm)

        # 测试不同上下文
        for context in ["document", "jira", "code"]:
            keywords = extractor.extract_from_text("test text", context=context)
            assert len(keywords) > 0


class TestKeywordExtractorIntegration:
    """集成测试"""

    def test_extract_from_real_jira_data(self):
        """测试真实 Jira 数据"""
        extractor = KeywordExtractor()

        jira_data = {
            'title': 'NVMe FFU Download Failure',
            'description': '''
            The firmware update (FFU) process fails during download phase.
            Error occurs in spdk_nvme_ctrlr_update_firmware function.
            PCIe link becomes unstable after CRC error.
            Need to implement retry mechanism with exponential backoff.
            '''
        }

        keywords = extractor.extract_from_jira(jira_data, max_description_length=500)

        # 应该提取技术术语
        assert any(k in keywords for k in ["NVMe", "FFU", "PCIe", "CRC"])

        # 不应该包含通用词
        assert "Error" not in keywords
        assert "Need" not in keywords

    def test_extract_from_real_document(self):
        """测试真实文档内容"""
        extractor = KeywordExtractor()

        doc_text = '''
        # NVMe Controller Reset Specification

        ## Overview
        The spdk_nvme_ctrlr_reset() function performs a controller-level reset.

        ## Implementation
        - Check PCIe link status
        - Send CC.EN = 0 to disable controller
        - Wait for CSTS.RDY = 0
        - Re-enable controller with CC.EN = 1
        '''

        keywords = extractor.extract_from_text(doc_text, context="document")

        # 应该提取 API 名称和技术术语
        assert any("nvme" in k.lower() for k in keywords)
        assert any("reset" in k.lower() for k in keywords)
