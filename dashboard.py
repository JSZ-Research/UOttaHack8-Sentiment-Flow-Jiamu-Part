# cd /Users/jiamulin/Desktop/Sentiment-Flow/UOttaHack8-Sentiment-Flow
# streamlit run dashboard.py

import streamlit as st
import json
import time
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import os

try:
    from analysis_agent import generate_and_submit_report
except ImportError:
    st.error("Missing analysis_agent.py! Please create it first.")

st.set_page_config(page_title="Sentiment-Flow | Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #F0F0F0; }
    .stMetric { background-color: rgba(45, 20, 10, 0.6); border: 1px solid #303030; padding: 15px; border-radius: 10px; }
    [data-testid="stMetricValue"] { color: #B4FF96; }
    </style>
    """, unsafe_allow_html=True)

def get_current_video():
    """读取由 launcher.py 写入的视频链接"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    txt_path = os.path.join(script_dir, "current_video.txt")
    try:
        if os.path.exists(txt_path):
            with open(txt_path, "r") as f:
                url = f.read().strip()
                if url: return url
    except:
        pass
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

def get_live_data():
    """从本地 JSON 读取实时检测数据"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    p = Path(os.path.join(script_dir, "live_data.json"))
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return None
    return None


if "view_mode" not in st.session_state:
    st.session_state.view_mode = "monitor"

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        "ts", "eye_open", "mouth", "stability", 
        "smile", "confused", "distraction"
    ])

if st.session_state.view_mode == "monitor":
    st_autorefresh(interval=300, key="datarefresh")

current_video_url = get_current_video()

if st.session_state.view_mode == "monitor":
    left_col, right_col = st.columns([1.8, 1.2], gap="large")

    with left_col:
        st.markdown("<h2 style='color: #B4FF96;'>RESEARCH STIMULUS</h2>", unsafe_allow_html=True)
        st.video(current_video_url) 
        st.caption(f"💡 Target: {current_video_url}")
        st.caption("JSZ SENTINEL: Capturing natural human response in real-time.")
        
        st.divider()
        st.markdown("### 🤖 AI Insight Agent")
        if st.button("🏁 END SESSION & ANALYZE RESULTS", use_container_width=True):
            if not st.session_state.history.empty:
                st.session_state.view_mode = "report"
                st.rerun()
            else:
                st.warning("No data captured. Please ensure the engine is running.")

    with right_col:
        st.markdown("<h2 style='color: #F0F0F0;'>LIVE ANALYTICS</h2>", unsafe_allow_html=True)
        
        st.image("http://localhost:5001/video_feed", use_container_width=True)

        live = get_live_data()
        
        if live:
            eye_open = 1.0 - float(live.get("eye_score") or 0.0)
            mouth_act = float(live.get("yawn_score") or 0.0)
            stability = max(0, 100 - float(live.get("tilt_val") or 0.0))
            smile = float(live.get("smile_score") or 0.0)
            confused = float(live.get("confused_score") or 0.0)
            distract = float(live.get("distraction_score") or 0.0)
            status = str(live.get("status") or "SCANNING")

            new_row = {
                "ts": time.time(), "eye_open": eye_open, "mouth": mouth_act, 
                "stability": stability/100.0, "smile": smile, 
                "confused": confused, "distraction": distract
            }
            st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([new_row])], ignore_index=True).tail(60)

            st.info(f"System State: {status}")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)
            
            fig.add_trace(go.Scatter(y=st.session_state.history["eye_open"], name="Eye", line=dict(color='#B4FF96', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(y=st.session_state.history["mouth"], name="Mouth", line=dict(color='#E196FF', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(y=st.session_state.history["stability"], name="Stability", line=dict(color='#64B4FF', width=2, dash='dot')), row=1, col=1)
            
            fig.add_trace(go.Scatter(y=st.session_state.history["smile"], name="Smile", line=dict(color='#FFB450', width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(y=st.session_state.history["confused"], name="Confusion", line=dict(color='#FF6464', width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(y=st.session_state.history["distraction"], name="Distract", line=dict(color='#FFFFFF', width=2, dash='dash')), row=2, col=1)

            fig.update_layout(
                height=480, margin=dict(l=0, r=0, t=10, b=0), 
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            fig.update_yaxes(range=[0, 1.1], gridcolor='#303030')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("📡 Awaiting Data Stream...")

elif st.session_state.view_mode == "report":
    st.markdown("<h1 style='color: #B4FF96; text-align: center;'>SENTIMENT SYNTHESIS</h1>", unsafe_allow_html=True)
    st.divider()

    with st.spinner("🧠 AI Agent is synthesizing facial telemetry and content context..."):
        final_text, avg_data = generate_and_submit_report(st.session_state.history, current_video_url)
        time.sleep(1.5)

    st.balloons()
    
    c_left, c_right = st.columns([1.3, 0.7])
    with c_left:
        st.success("### ✅ AI Generated Feedback")
        st.markdown(final_text) 
        st.info("📊 This insight has been automatically archived to SurveyMonkey Enterprise.")

    with c_right:
        st.markdown("#### 📊 Session Metrics (Averages)")
        st.json(avg_data)

    if st.button("🔄 START NEW RESEARCH SESSION", use_container_width=True):
        st.session_state.history = pd.DataFrame(columns=[
            "ts", "eye_open", "mouth", "stability", "smile", "confused", "distraction"
        ])
        st.session_state.view_mode = "monitor"
        st.rerun()