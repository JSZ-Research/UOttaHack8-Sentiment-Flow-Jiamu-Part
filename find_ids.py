import requests

TOKEN = "VoT9W4PuK0AzA.xUGQSK2qNvPU8VgIGnaC-LOKkqPy3ID5lD8K6Aos8hVWUdQtYCXNo9Yc1UUJYy.7f.7AFYbYQSEz7nO7uF8sOpjc12cqbttxGvK-hacBdlN8DMVTv4"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

s_url = "https://api.surveymonkey.com/v3/surveys"
try:
    s_res = requests.get(s_url, headers=headers).json()
    survey_id = s_res['data'][0]['id']
    print(f"✅ 你的 Survey ID 是: {survey_id}")

    c_url = f"https://api.surveymonkey.com/v3/surveys/{survey_id}/collectors"
    c_res = requests.get(c_url, headers=headers).json()
    collector_id = c_res['data'][0]['id']
    print(f"✅ 你的 Collector ID 是: {collector_id}")
except Exception as e:
    print(f"❌ 出错了，请检查 Token 是否正确: {e}")