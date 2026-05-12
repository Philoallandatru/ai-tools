"""
Unit tests for LLM client factory
"""

import pytest
from crawler.llm_client import LLMClientFactory, MockLLMClient, LLMStudioClient, BaseLLMClient


class TestLLMClientFactory:
    """测试 LLM 客户端工厂"""

    def test_create_mock_client(self):
        """测试创建 Mock 客户端"""
        config = {'provider': 'mock'}
        client = LLMClientFactory.create_from_config(config)

        assert isinstance(client, MockLLMClient)
        assert isinstance(client, BaseLLMClient)

    def test_create_llmstudio_client(self):
        """测试创建 LLMStudio 客户端"""
        config = {
            'provider': 'llmstudio',
            'base_url': 'http://localhost:1234/v1',
            'model': 'test-model',
            'max_tokens': 1000,
            'temperature': 0.5
        }
        client = LLMClientFactory.create_from_config(config)

        assert isinstance(client, LLMStudioClient)
        assert isinstance(client, BaseLLMClient)
        assert client.base_url == 'http://localhost:1234/v1'
        assert client.model == 'test-model'

    def test_create_with_default_provider(self):
        """测试使用默认 provider（mock）"""
        config = {}
        client = LLMClientFactory.create_from_config(config)

        assert isinstance(client, MockLLMClient)

    def test_create_with_invalid_provider(self):
        """测试使用无效的 provider"""
        config = {'provider': 'invalid'}

        with pytest.raises(ValueError, match="不支持的 LLM 提供商"):
            LLMClientFactory.create_from_config(config)

    def test_mock_client_generate(self):
        """测试 Mock 客户端的生成功能"""
        client = MockLLMClient()
        response = client.generate("Test prompt")

        assert isinstance(response, str)
        assert len(response) > 0
        assert "Mock" in response or "模拟" in response
