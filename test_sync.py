import requests
import json

# --- 填入你刚才拿到的真实参数 ---
TOKEN = "VoT9W4PuK0AzA.xUGQSK2qNvPU8VgIGnaC-LOKkqPy3ID5lD8K6Aos8hVWUdQtYCXNo9Yc1UUJYy.7f.7AFYbYQSEz7nO7uF8sOpjc12cqbttxGvK-hacBdlN8DMVTv4"
COLLECTOR_ID = "438509525"
QUESTION_ID = "275366150"

url = f"https://api.surveymonkey.com/v3/collectors/{COLLECTOR_ID}/responses"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "pages": [
        {
            "questions": [
                {
                    "id": QUESTION_ID,
                    "answers": [
                        {"text": "JSZ Diagnostic Test: The system is attempting to sync."}
                    ]
                }
            ]
        }
    ]
}

print("正在发送诊断测试数据...")
response = requests.post(url, headers=headers, json=payload)

print(f"服务器状态码: {response.status_code}")
print("服务器原始回复:")
print(json.dumps(response.json(), indent=2))