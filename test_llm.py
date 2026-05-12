"""
测试 LLM 客户端连接
"""

import sys
import codecs

# Windows UTF-8 编码支持
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from test_utils import create_test_llm_client

def test_openai_api():
    print("测试 OpenAI-compatible API 连接...")
    print()

    # 创建客户端（自动降级到 Mock）
    client = create_test_llm_client(
        provider='openai',
        base_url='http://127.0.0.1:1234/v1',
        model='qwen3.5-0.8b',
        auto_fallback=True
    )

    # 测试简单提示
    prompt = "请用一句话解释什么是 NVMe。"
    print(f"\n提示词: {prompt}")
    print("\n生成中...")

    try:
        response = client.generate(prompt, max_tokens=100)

        print(f"\n响应成功!")
        print(f"响应内容: {response}")
        print(f"响应长度: {len(response)} 字符")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_openai_api()
