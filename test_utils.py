"""
测试工具函数 - 提供统一的 LLM 客户端创建和自动降级功能
"""

import sys
import codecs

# Windows UTF-8 编码支持
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from crawler.llm_client import create_llm_client, LLMClientFactory


def create_test_llm_client(provider='openai', base_url='http://127.0.0.1:1234/v1',
                           model='qwen3.5-4b', auto_fallback=True, verbose=True):
    """
    创建测试用 LLM 客户端，支持自动降级到 Mock 模式

    Args:
        provider: LLM 提供商 ('openai' 或 'mock')
        base_url: OpenAI-compatible API 地址
        model: 模型名称
        auto_fallback: 连接失败时是否自动降级到 Mock 模式
        verbose: 是否打印详细信息

    Returns:
        LLM 客户端实例
    """
    if provider == 'mock':
        if verbose:
            print("⚠️  使用 Mock LLM（测试模式）")
        return LLMClientFactory.create('mock')

    if verbose:
        print(f"连接 OpenAI-compatible API: {base_url}")

    try:
        client = create_llm_client(provider, base_url=base_url, model=model)
        # 测试连接
        client.generate("test", max_tokens=10)
        if verbose:
            print("✓ LLM 连接成功")
        return client
    except Exception as e:
        if auto_fallback:
            if verbose:
                print(f"⚠️  LLM 连接失败: {e}")
                print("⚠️  自动降级到 Mock LLM 模式")
            return LLMClientFactory.create('mock')
        else:
            raise


def is_llm_available(base_url='http://127.0.0.1:1234/v1', model='qwen3.5-4b'):
    """
    检查 LLM 服务是否可用

    Args:
        base_url: OpenAI-compatible API 地址
        model: 模型名称

    Returns:
        bool: LLM 服务是否可用
    """
    try:
        client = create_llm_client('openai', base_url=base_url, model=model)
        client.generate("test", max_tokens=10)
        return True
    except:
        return False
