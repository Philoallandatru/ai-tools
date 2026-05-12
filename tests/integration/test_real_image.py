"""
测试 llama.cpp vision API - 使用真实图片
"""

import sys
import codecs
import base64
import requests
from pathlib import Path

# Windows UTF-8 兼容性
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def test_with_real_image():
    """使用真实图片测试"""

    # 使用报告中提到的图片
    image_path = Path("test-sources/images/20a9fa361108a8dc7772ca79df75adbd654084118bf6604fe89002ce22e629e6.jpg")

    if not image_path.exists():
        print(f"❌ 图片不存在: {image_path}")
        print("请提供一个存在的图片路径")
        return

    print(f"📷 使用图片: {image_path}")
    print(f"📦 图片大小: {image_path.stat().st_size} bytes")

    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    print(f"📦 Base64 大小: {len(image_data)} bytes")

    # 测试 llama.cpp API
    url = "http://127.0.0.1:9090/v1/chat/completions"

    payload = {
        "model": "Qwen3-VL-4B-Instruct-Q4_K_M.gguf",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请描述这张图片的内容。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 200,
        "temperature": 0.3
    }

    print(f"\n📡 发送请求到 {url}")

    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"📊 状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 响应成功!")
            print(f"📝 模型回复:\n{result['choices'][0]['message']['content']}")
            print(f"\n🔢 Token 使用:")
            print(f"   - Prompt tokens: {result['usage']['prompt_tokens']}")
            print(f"   - Completion tokens: {result['usage']['completion_tokens']}")
            print(f"   - Total tokens: {result['usage']['total_tokens']}")

            # 验证是否真的处理了图片
            prompt_tokens = result['usage']['prompt_tokens']
            if prompt_tokens > 500:
                print(f"\n✅ 图片被正确处理! (prompt tokens = {prompt_tokens})")
            else:
                print(f"\n⚠️  图片可能未被处理 (prompt tokens = {prompt_tokens} 太少)")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == '__main__':
    test_with_real_image()
