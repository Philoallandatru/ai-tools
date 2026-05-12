"""
测试 llama.cpp vision API
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

def test_llamacpp_vision():
    """测试 llama.cpp 的 vision 功能"""

    # 读取测试图片
    image_path = Path("test_red_image.png")
    if not image_path.exists():
        print("❌ 测试图片不存在，创建一个...")
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='red')
        img.save(image_path)
        print(f"✓ 创建测试图片: {image_path}")

    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    # 测试 llama.cpp API
    url = "http://127.0.0.1:9090/v1/chat/completions"

    payload = {
        "model": "vision",  # llama.cpp 通常用 "vision" 或具体模型名
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "这张图片是什么颜色？请只回答颜色名称。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100,
        "temperature": 0.1
    }

    print(f"📡 发送请求到 {url}")
    print(f"📦 图片大小: {len(image_data)} bytes (base64)")

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"📊 状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 响应成功!")
            print(f"📝 模型回复: {result['choices'][0]['message']['content']}")
            print(f"🔢 Token 使用:")
            print(f"   - Prompt tokens: {result['usage']['prompt_tokens']}")
            print(f"   - Completion tokens: {result['usage']['completion_tokens']}")
            print(f"   - Total tokens: {result['usage']['total_tokens']}")

            # 验证是否真的处理了图片
            prompt_tokens = result['usage']['prompt_tokens']
            if prompt_tokens > 100:
                print(f"\n✅ 图片被正确处理! (prompt tokens = {prompt_tokens})")
            else:
                print(f"\n⚠️  图片可能未被处理 (prompt tokens = {prompt_tokens} 太少)")

            # 验证回答是否正确
            answer = result['choices'][0]['message']['content'].lower()
            if 'red' in answer or '红' in answer:
                print(f"✅ 模型正确识别了颜色!")
            else:
                print(f"⚠️  模型回答可能不正确: {answer}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == '__main__':
    test_llamacpp_vision()
