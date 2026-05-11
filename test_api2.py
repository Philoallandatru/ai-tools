import requests
import json

# Test with English
url = "http://127.0.0.1:1234/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen3.5-4B",
    "messages": [
        {"role": "user", "content": "What is 2+2?"}
    ],
    "max_tokens": 50,
    "temperature": 0.7
}

print("Testing with English prompt...")

try:
    response = requests.post(url, json=payload, timeout=30)
    response.encoding = 'utf-8'

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"Response content: {content}")
        print(f"Content type: {type(content)}")
        print(f"Content repr: {repr(content)}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
