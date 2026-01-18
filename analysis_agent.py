import openai
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

# --- 配置区 ---
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
SM_TOKEN = os.environ.get("SM_TOKEN")
SM_COLLECTOR_ID = os.environ.get("SM_COLLECTOR_ID", "438509525")
SM_QUESTION_ID = os.environ.get("SM_QUESTION_ID", "275366150")

client = openai.OpenAI(api_key=OPENAI_KEY)

def generate_and_submit_report(history_df, video_url):
    """汇总历史数据，结合视频背景，调用AI生成深度洞察"""
    
    
    # 1. 计算平均指标
    avg_stats = {
        "Avg_Eye_Openness": history_df["eye_open"].mean(),
        "Avg_Smile": history_df["smile"].mean(),
        "Avg_Confusion": history_df["confused"].mean(),
        "Avg_Distraction": history_df["distraction"].mean(),
        "Max_Mouth_Activity": history_df["mouth"].max()
    }

    # 2. 构造更强大的上下文 Prompt
    # 注意：我们将视频链接传给 AI，GPT-4o 拥有训练数据，它大概率认识像 Rick Astley 这样的经典视频
    prompt = f"""
    You are a Senior UX Research Lead at SurveyMonkey. Analyze the user's physiological reaction to this URL: {video_url}
    
    DATA REFERENCE SCALE (0.0 to 1.0):
    - Eye Openness: >0.70 is focused, <0.30 is drowsy.
    - Smile Index: >0.15 is positive feedback.
    - Confusion Index: >0.25 means cognitive load/puzzlement.
    - Distraction: >0.30 means looking away from the screen.
    - Mouth/Yawn: >0.40 indicates high fatigue.
    - Stability: >90% is steady, <70% is significant head tilt/nodding.

    CURRENT SESSION AVERAGES:
    {json.dumps(avg_stats, indent=2)}

    Please write the report in English following this exact structure:

    [INTRODUCTION]
    A concise summary of the content at the URL and a high-level overview of the user's engagement. Explain how the user's overall state correlates with the nature of the stimulus.

    [CORE ANALYSIS]
    - DISTRACTION: Analyze if the user was visually anchored to the content. If the score is low, describe it as "intense visual focus." 
    - COGNITION: Analyze the Confusion Index (frowning). If low, describe it as "seamless processing." If high, mention "cognitive friction."
    - SENTIMENT: Analyze the Smile Index. IMPORTANT: If the user is expressionless (low score), do NOT say "no reaction." Instead, use professional terms like "stoic focus," "impassive observation," "neutral baseline," or "undemonstrative but attentive reception."
    - VIGILANCE: Analyze fatigue (eye closure, yawning, and head stability). Describe the user's physical readiness or exhaustion levels.

    [LIMITATIONS]
    A final paragraph mentioning potential data gaps, such as environmental lighting, session duration, or the need for a subjective baseline to improve accuracy.

    Format: Use clear headings and bullet points. Keep the tone industrial and sophisticated.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7 # 增加一点创造性
        )
        report_text = response.choices[0].message.content

        # 3. 自动提交到 SurveyMonkey
        url = f"https://api.surveymonkey.com/v3/collectors/{SM_COLLECTOR_ID}/responses"
        headers = {"Authorization": f"Bearer {SM_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "pages": [{"questions": [{"id": SM_QUESTION_ID, "answers": [{"text": report_text}]}]}]
        }
        requests.post(url, headers=headers, json=payload)

        return report_text, avg_stats
    except Exception as e:
        return f"Error connecting to AI Agent: {e}", avg_stats