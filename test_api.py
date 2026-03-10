import requests
from src.config import Config

test_urls = [
    Config.LLM_API_URL,
    Config.LLM_API_URL + "/chat/completions",
    "https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions",
]

for url in test_urls:
    print(f"\nTesting: {url}")
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": Config.LLM_MODEL,
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:200] if response.text else 'empty'}")
    except Exception as e:
        print(f"  Error: {e}")
