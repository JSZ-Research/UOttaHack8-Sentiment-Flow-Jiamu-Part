import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Sentiment-Flow | Dashboard", layout="wide")

with st.sidebar:
    st.markdown("### Data Source")
    file_json = st.text_input("live_data.json", "live_data.json")
    file_img = st.text_input("live_frame.jpg", "live_frame.jpg")
    upload_portrait = st.file_uploader("Upload portrait (jpg/png)", type=["jpg","jpeg","png"])
    refresh_ms = st.number_input("refresh_ms", 100, 5000, 300, 50)

st_autorefresh(interval=int(refresh_ms), key="tick")

def safe_float(x, d=0.0):
    try:
        return float(x)
    except Exception:
        return float(d)

if "series" not in st.session_state:
    st.session_state.series = pd.DataFrame(
        columns=["ts", "eye", "yawn", "tilt", "status"]
    ).set_index("ts")

if "last_ts" not in st.session_state:
    st.session_state.last_ts = None

if "last_good_live" not in st.session_state:
    st.session_state.last_good_live = None

if "last_img_mtime" not in st.session_state:
    st.session_state.last_img_mtime = 0.0
if "last_img_bytes" not in st.session_state:
    st.session_state.last_img_bytes = None

if "survey_path" not in st.session_state:
    st.session_state.survey_path = Path("survey_log.csv")

def read_live_json(p: Path):
    if not p.exists():
        return st.session_state.last_good_live
    try:
        data = json.load(open(p, "r", encoding="utf-8"))
        st.session_state.last_good_live = data
        return data
    except Exception:
        return st.session_state.last_good_live

left, mid, right = st.columns([1.15, 1.05, 0.95], gap="large")

with left:
    st.subheader("Camera Portrait")
    img_ph = st.empty()

with mid:
    st.subheader("Live Signals")
    chart_ph = st.empty()
    latest_ph = st.empty()

with right:
    st.subheader("Survey")

live = read_live_json(Path(file_json))

if live is not None:
    ts = safe_float(live.get("timestamp", time.time()))
    eye = safe_float(live.get("eye_score", 0.0))
    yawn = safe_float(live.get("yawn_score", 0.0))
    tilt = safe_float(live.get("tilt_val", 0.0))
    status = str(live.get("status", ""))

    if st.session_state.last_ts is None or ts > st.session_state.last_ts:
        st.session_state.last_ts = ts
        add = pd.DataFrame(
            {"eye": [eye], "yawn": [yawn], "tilt": [tilt], "status": [status]},
            index=[ts],
        )
        st.session_state.series = pd.concat([st.session_state.series, add]).tail(1200)

    latest_ph.markdown(
        f"**STATUS:** {status}  \n"
        f"**eye:** {eye:.3f} · **yawn:** {yawn:.3f} · **tilt:** {tilt:.2f}"
    )

img_p = Path(file_img)
if upload_portrait is not None:
    img_ph.image(upload_portrait, use_container_width=True)
elif img_p.exists():
    mtime = img_p.stat().st_mtime
    if mtime != st.session_state.last_img_mtime:
        st.session_state.last_img_mtime = mtime
        st.session_state.last_img_bytes = img_p.read_bytes()
    if st.session_state.last_img_bytes is not None:
        img_ph.image(st.session_state.last_img_bytes, use_container_width=True)
else:
    img_ph.info("Waiting for live_frame.jpg ...")

if len(st.session_state.series) > 0:
    chart_ph.line_chart(st.session_state.series[["eye", "yawn", "tilt"]], height=320)
else:
    chart_ph.info("Waiting for live_data.json ...")

with right:
    with st.form("survey_form", clear_on_submit=False):
        user_id = st.text_input("user_id", value="anon")
        perceived = st.selectbox(
            "How does the user look?",
            ["Focused", "Normal", "Sleepy", "Confused", "Stressed"],
        )
        rating = st.slider("Overall impression (0-10)", 0, 10, 7)
        submit = st.form_submit_button("Submit")

    if submit:
        row = {
            "ts": time.time(),
            "user_id": user_id,
            "perceived": perceived,
            "rating": rating,
            "eye": float(st.session_state.series["eye"].iloc[-1]) if len(st.session_state.series) else None,
            "yawn": float(st.session_state.series["yawn"].iloc[-1]) if len(st.session_state.series) else None,
            "tilt": float(st.session_state.series["tilt"].iloc[-1]) if len(st.session_state.series) else None,
            "status": str(st.session_state.series["status"].iloc[-1]) if len(st.session_state.series) else "",
        }
        df_row = pd.DataFrame([row])
        sp = st.session_state.survey_path
        if sp.exists():
            df_row.to_csv(sp, mode="a", header=False, index=False)
        else:
            df_row.to_csv(sp, index=False)

    st.divider()
    st.markdown("#### Survey Stats")
    sp = st.session_state.survey_path
    if sp.exists():
        df = pd.read_csv(sp)
        st.markdown(
            f"**Responses:** {len(df)}  \n"
            f"**Avg rating:** {df['rating'].mean():.2f}"
        )
        c = df["perceived"].value_counts()
        st.bar_chart(c)
    else:
        st.info("No survey yet (survey_log.csv will be created on submit).")
