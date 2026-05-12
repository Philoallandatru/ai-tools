import requests
import json

# Test chat completions
url = "http://127.0.0.1:1234/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen3.5-4B",
    "messages": [
        {"role": "user", "content": "你好"}
    ],
    "max_tokens": 50,
    "temperature": 0.7
}

print("Testing chat completions endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
print()

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")

    if response.status_code == 200:
        result = response.json()
        print(f"\nParsed Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
