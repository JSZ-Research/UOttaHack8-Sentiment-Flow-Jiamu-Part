import subprocess
import time
import os
import sys
import urllib.request

def wait_for_engine(url="http://localhost:5001/video_feed", timeout=30, interval=0.5):
    """等待 sentiment_flow_engine 启动完成"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except:
            time.sleep(interval)
    return False

def start_sentiment_flow():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("   JSZ Research - Sentiment-Flow")

    target_url = input("\nPlese Enter Video/product URL: ")
    if not target_url:
        target_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    with open(os.path.join(script_dir, "current_video.txt"), "w") as f:
        f.write(target_url)

    print(f"✅ URL set!: {target_url}")
    print("🚀 Loading sentiment_flow_engine...")

    engine_process = subprocess.Popen(
        [sys.executable, os.path.join(script_dir, "sentiment_flow_engine.py")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )

    print("⏳ Waiting for engine to start...")
    if wait_for_engine():
        print("✅ Engine ready!")
    else:
        print("⚠️ Engine may not be fully ready, proceeding anyway...")

    try:
        print("🌍 Opening dashboard...")
        subprocess.run(["streamlit", "run", os.path.join(script_dir, "dashboard.py")])
    except KeyboardInterrupt:
        print("\n👋 Closing...")
        engine_process.terminate()

if __name__ == "__main__":
    start_sentiment_flow()

# https://youtu.be/3mGI4_BjEws