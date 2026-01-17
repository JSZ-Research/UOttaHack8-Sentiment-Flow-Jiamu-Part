from flask import Flask, request, jsonify, render_template_string
import time, json

app = Flask(__name__)

SURVEY = [
    {"id": "q1", "text": "Overall, how would you describe your experience at uOttaHack 8?", "seconds": 6},
    {"id": "q2", "text": "How did you perceive the organization and flow of the event?", "seconds": 6},
    {"id": "q3", "text": "How did you find the support and resources provided by the University of Ottawa during the event?", "seconds": 6},
    {"id": "q4", "text": "How clear was the SurveyMonkey Challenge theme to you during the hackathon?", "seconds": 6},
    {"id": "q5", "text": "How engaging did you find the activities and challenges throughout the event?", "seconds": 6},
    {"id": "q6", "text": "Based on your experience, how likely are you to participate in a future uOttaHack event?", "seconds": 6},
]

HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>uOttaHack 8 Survey - Invisible Feedback</title>
  <style>
    :root{--bg:#0b1020;--muted:#a9b2d3;--fg:#eef2ff;--accent:#6ee7ff;}
    *{box-sizing:border-box}
    body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,"Noto Sans",Arial;background:radial-gradient(1200px 600px at 20% 10%,#182355 0%,transparent 60%),radial-gradient(900px 500px at 80% 20%,#23306a 0%,transparent 55%),var(--bg);color:var(--fg);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
    .wrap{width:min(1100px,100%);display:grid;grid-template-columns:1.25fr 0.75fr;gap:18px}
    @media(max-width:920px){.wrap{grid-template-columns:1fr}}
    .card{background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.03));border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:18px;box-shadow:0 10px 40px rgba(0,0,0,.35);backdrop-filter:blur(10px)}
    .header{display:flex;justify-content:space-between;gap:12px;margin-bottom:10px}
    .sub{color:var(--muted);font-size:13px;line-height:1.4}
    .pill{padding:8px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.18);color:var(--muted);font-size:12px;white-space:nowrap}
    .qbox{margin-top:14px;padding:18px;border-radius:18px;background:rgba(10,14,30,.45);border:1px solid rgba(255,255,255,.10);min-height:240px;display:flex;flex-direction:column;justify-content:space-between;gap:16px}
    .progress{height:8px;width:100%;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden}
    .bar{height:100%;width:0%;background:linear-gradient(90deg,var(--accent),#8b5cf6);border-radius:999px;transition:width 250ms ease}
    .question{font-size:28px;line-height:1.25;margin:0}
    .hint{color:var(--muted);font-size:14px;line-height:1.55;margin:0}
    .controls{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px}
    button{appearance:none;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.08);color:var(--fg);padding:12px 16px;border-radius:14px;font-size:14px;cursor:pointer;transition:transform 120ms ease,background 180ms ease,opacity 180ms ease}
    button:disabled{opacity:.45;cursor:not-allowed}
    button:active{transform:scale(.98)}
    .cam{display:flex;flex-direction:column;gap:10px}
    video{width:100%;border-radius:16px;background:#000;border:1px solid rgba(255,255,255,.12);aspect-ratio:16/9;object-fit:cover}
    .small{color:var(--muted);font-size:12px;line-height:1.4}
    .err{color:#ff9dbb;font-size:12px;line-height:1.4}
    .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono";font-size:12px;color:var(--muted)}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="header">
        <div>
          <div style="font-size:18px;">uOttaHack 8 — Quick Survey (No Options)</div>
          <div class="sub">No buttons, no ratings. Read naturally. The Next button unlocks after a short delay for passive capture.</div>
        </div>
        <div class="pill" id="pill">Question 1 / {{ total }}</div>
      </div>
      <div class="progress"><div class="bar" id="bar"></div></div>
      <div class="qbox">
        <div>
          <p class="question" id="question"></p>
          <p class="hint" id="hint"></p>
        </div>
        <div class="controls">
          <div class="mono" id="timer">Next available in …</div>
          <div style="display:flex;gap:10px;">
            <button id="skipBtn" title="Demo only">Skip</button>
            <button id="nextBtn" disabled>Next</button>
          </div>
        </div>
      </div>
    </div>
    <div class="card cam">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
        <div>
          <div style="font-size:16px;">Camera Capture</div>
          <div class="small">Camera runs continuously in-browser for expression capture during reading.</div>
        </div>
        <div class="pill" id="camStatus">Starting…</div>
      </div>
      <video id="video" autoplay playsinline muted></video>
      <div id="camErr" class="err" style="display:none;"></div>
      <div class="small">Open via <span class="mono">http://127.0.0.1:8000</span> (not file://) so the browser can request camera permission.</div>
    </div>
  </div>

<script>
  const SURVEY = {{ survey | safe }};
  const total = SURVEY.length;

  const elQ = document.getElementById("question");
  const elHint = document.getElementById("hint");
  const elPill = document.getElementById("pill");
  const elBar = document.getElementById("bar");
  const elTimer = document.getElementById("timer");
  const nextBtn = document.getElementById("nextBtn");
  const skipBtn = document.getElementById("skipBtn");

  let idx = 0;
  let t0 = performance.now();
  let unlockAt = 0;
  let tickHandle = null;

  function nowISO(){ return new Date().toISOString(); }

  function setProgress(){
    elPill.textContent = `Question ${idx+1} / ${total}`;
    elBar.style.width = `${Math.round((idx / total) * 100)}%`;
  }

  function postEvent(payload){
    fetch("/event", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    }).catch(()=>{});
  }

  function renderQuestion(){
    const q = SURVEY[idx];
    elQ.textContent = q.text;
    elHint.textContent = `Read naturally. Next unlocks in ${q.seconds}s.`;
    nextBtn.disabled = true;

    setProgress();

    t0 = performance.now();
    unlockAt = t0 + q.seconds * 1000;

    if (tickHandle) cancelAnimationFrame(tickHandle);
    function tick(){
      const t = performance.now();
      const left = Math.max(0, unlockAt - t);
      if (left > 0){
        elTimer.textContent = `Next available in ${(left/1000).toFixed(1)}s`;
        tickHandle = requestAnimationFrame(tick);
      } else {
        elTimer.textContent = `Ready.`;
        nextBtn.disabled = false;
      }
    }
    tickHandle = requestAnimationFrame(tick);

    postEvent({type:"question_start", question_id:q.id, question_index:idx, ts:nowISO()});
  }

  async function sendStep(type){
    const q = SURVEY[idx];
    const dwell_ms = Math.round(performance.now() - t0);
    try{
      await fetch("/event", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({type, question_id:q.id, question_index:idx, ts:nowISO(), dwell_ms})
      });
    }catch(e){}
  }

  nextBtn.addEventListener("click", async ()=>{
    if (nextBtn.disabled) return;
    await sendStep("next_clicked");
    idx += 1;
    if (idx >= total){
      elBar.style.width = "100%";
      elPill.textContent = "Complete";
      elQ.textContent = "Thank you. Survey complete.";
      elHint.textContent = "You may close this page.";
      nextBtn.disabled = true;
      skipBtn.disabled = true;
      elTimer.textContent = "Done.";
      postEvent({type:"survey_complete", ts:nowISO()});
      return;
    }
    renderQuestion();
  });

  skipBtn.addEventListener("click", async ()=>{
    await sendStep("skip_clicked");
    idx += 1;
    if (idx >= total) idx = total - 1;
    renderQuestion();
  });

  const video = document.getElementById("video");
  const camStatus = document.getElementById("camStatus");
  const camErr = document.getElementById("camErr");

  async function startCamera(){
    try{
      camStatus.textContent = "Requesting…";
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: {ideal: 1280}, height: {ideal: 720}, facingMode: "user" },
        audio: false
      });
      video.srcObject = stream;
      camStatus.textContent = "Live";
      camStatus.style.borderColor = "rgba(110,231,255,0.6)";
    }catch(e){
      camStatus.textContent = "Blocked";
      camErr.style.display = "block";
      camErr.textContent = "Camera permission blocked or unavailable: " + (e && e.message ? e.message : e);
    }
  }

  startCamera();
  renderQuestion();
</script>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(HTML, survey=json.dumps(SURVEY, ensure_ascii=False), total=len(SURVEY))

@app.post("/event")
def event():
    data = request.get_json(silent=True) or {}
    print(f"[EVENT] {time.strftime('%Y-%m-%d %H:%M:%S')} {data}")
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
