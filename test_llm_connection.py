#!/usr/bin/env python3
"""
测试 LLM 连接和响应的调试脚本
"""

import requests
import json
import yaml

def test_llm_connection():
    """测试 LLM Studio 连接"""

    # 1. 读取配置
    print("=" * 60)
    print("1. 读取配置文件")
    print("=" * 60)

    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    llm_config = config.get('llm', {})
    base_url = llm_config.get('base_url', 'http://127.0.0.1:1234/v1')
    model = llm_config.get('model', 'qwen3.5-4b')

    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print()

    # 2. 测试简单的 chat completions 请求
    print("=" * 60)
    print("2. 测试 Chat Completions API")
    print("=" * 60)

    test_messages = [
        {"role": "user", "content": "请用一句话介绍 NVMe 协议。"}
    ]

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": test_messages,
                "max_tokens": 100,
                "temperature": 0.7
            },
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=30
        )

        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print()

        if response.status_code == 200:
            result = response.json()
            print("响应 JSON 结构:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()

            # 检查响应内容
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                print(f"Choices 结构: {list(choice.keys())}")

                if 'message' in choice:
                    message = choice['message']
                    print(f"Message 结构: {list(message.keys())}")
                    content = message.get('content', '')
                    print(f"Content 长度: {len(content)}")
                    print(f"Content 内容: {content}")
                else:
                    print("⚠️  警告: 响应中没有 'message' 字段")
            else:
                print("⚠️  警告: 响应中没有 'choices' 或 choices 为空")
        else:
            print(f"❌ 错误: HTTP {response.status_code}")
            print(f"响应内容: {response.text}")

    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: 无法连接到 {base_url}")
        print(f"   请确认 LLM Studio 是否正在运行")
        print(f"   错误详情: {e}")
    except requests.exceptions.Timeout:
        print(f"❌ 超时: 请求超过 30 秒未响应")
    except Exception as e:
        print(f"❌ 未知错误: {e}")

    print()

    # 3. 测试使用 LLMClientFactory
    print("=" * 60)
    print("3. 测试 LLMClientFactory")
    print("=" * 60)

    try:
        from crawler.llm_client import LLMClientFactory

        client = LLMClientFactory.create_from_config(llm_config)
        print(f"客户端类型: {type(client).__name__}")
        print(f"Base URL: {client.base_url}")
        print(f"Model: {client.model}")
        print()

        print("发送测试请求...")
        response = client.generate("请用一句话介绍 NVMe 协议。", max_tokens=100)
        print(f"响应长度: {len(response)}")
        print(f"响应内容: {response}")

        if len(response) == 0:
            print("⚠️  警告: 响应为空！")
        else:
            print("✅ 成功获取响应")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_connection()
