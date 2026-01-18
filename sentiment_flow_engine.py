import cv2
import mediapipe as mp
from mediapipe.tasks import python
import time
import math
import numpy as np
from collections import deque
import os 
import json
from flask import Flask, Response
import threading

COLOR_BG = (45, 20, 10)       
COLOR_TEXT_MAIN = (240, 240, 240)  
COLOR_SAFE = (180, 255, 150)  
COLOR_WARN = (80, 180, 255)   
COLOR_DANGER = (100, 100, 255) 

script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, 'face_landmarker.task')

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.VIDEO,
    output_face_blendshapes=True,
    num_faces=1)

detector = FaceLandmarker.create_from_options(options)


EYE_THRESH_WARN = 0.30   
EYE_THRESH_DANGER = 0.55
TILT_THRESH_WARN = 18    
TILT_THRESH_DANGER = 35  

status_history = deque(maxlen=25)
current_global_status = "STABLE"
current_global_color = COLOR_SAFE

cap = cv2.VideoCapture(0)
FONT = cv2.FONT_HERSHEY_SIMPLEX

app = Flask(__name__)
output_frame = None  # 这是全局变量，存最新的画面
lock = threading.Lock() # 线程锁，防止读写冲突

def generate():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

def run_server():
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True, use_reloader=False)

threading.Thread(target=run_server, daemon=True).start()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    overlay = frame.copy()
    
    rgb_frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    timestamp = int(time.time() * 1000)
    result = detector.detect_for_video(rgb_frame, timestamp)
    
    if result.face_blendshapes and result.face_landmarks:
        
        shapes = {s.category_name: s.score for s in result.face_blendshapes[0]}
        landmarks = result.face_landmarks[0]
        
        
        eye_val = (shapes.get('eyeBlinkLeft', 0) + shapes.get('eyeBlinkRight', 0)) / 2
        yawn_val = shapes.get('jawOpen', 0)
        p1, p2 = landmarks[33], landmarks[263]
        tilt_val = abs(math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x)))

        
        smile_val = (shapes.get('mouthSmileLeft', 0) + shapes.get('mouthSmileRight', 0)) / 2
        
        confused_val = (shapes.get('browDownLeft', 0) + shapes.get('browDownRight', 0)) / 2
        
        distracted_val = max(shapes.get('eyeLookOutLeft', 0), 
                             shapes.get('eyeLookInLeft', 0),
                             shapes.get('eyeLookOutRight', 0),
                             shapes.get('eyeLookInRight', 0))


        e_col = COLOR_DANGER if eye_val > EYE_THRESH_DANGER else (COLOR_WARN if eye_val > EYE_THRESH_WARN else COLOR_SAFE)
        y_col = COLOR_DANGER if yawn_val > 0.55 else (COLOR_WARN if yawn_val > 0.25 else COLOR_SAFE)
        t_col = COLOR_DANGER if tilt_val > TILT_THRESH_DANGER else (COLOR_WARN if tilt_val > TILT_THRESH_WARN else COLOR_SAFE)
        
        s_col = (255, 200, 100) if smile_val > 0.3 else (COLOR_TEXT_MAIN if confused_val < 0.3 else (200, 255, 255))

       
        this_frame_status = 0
        if eye_val > EYE_THRESH_DANGER or yawn_val > 0.5 or tilt_val > TILT_THRESH_DANGER:
            this_frame_status = 2
        elif eye_val > EYE_THRESH_WARN or distracted_val > 0.4:
            this_frame_status = 1
        
        status_history.append(this_frame_status)
        avg_status = sum(status_history) / len(status_history)

        if avg_status > 1.2: 
            current_global_status, current_global_color = "EXTREME FATIGUE", COLOR_DANGER
        elif avg_status > 0.4: 
            current_global_status, current_global_color = "MILD BOREDOM", COLOR_WARN
        elif smile_val > 0.2:
            current_global_status, current_global_color = "HIGH ENGAGEMENT", (255, 220, 150)
        else: 
            current_global_status, current_global_color = "ACTIVE / FOCUSED", COLOR_SAFE
            
        
        data_packet = {
            "eye_score": round(float(eye_val), 3),
            "yawn_score": round(float(yawn_val), 3),
            "tilt_val": round(float(tilt_val), 1),
            "smile_score": round(float(smile_val), 3),
            "confused_score": round(float(confused_val), 3),
            "distraction_score": round(float(distracted_val), 3), # <--- 检查这一行键名
            "status": current_global_status,
            "timestamp": time.time()
        }
        data_path = os.path.join(script_dir, "live_data.json")
        with open(data_path, "w") as f:
            json.dump(data_packet, f)
        
        # 轮廓
        horizontal_distract = max(shapes.get('eyeLookOutLeft', 0), 
                                  shapes.get('eyeLookInLeft', 0),
                                  shapes.get('eyeLookOutRight', 0),
                                  shapes.get('eyeLookInRight', 0))
        
        vertical_look_up = shapes.get('eyeLookUpLeft', 0)
        
        raw_distract = max(horizontal_distract, vertical_look_up)
        distracted_val = max(0, raw_distract - 0.2) * 1.5 
        distracted_val = min(1.0, distracted_val)

        all_x = [pt.x for pt in landmarks]
        all_y = [pt.y for pt in landmarks]
        x_min, x_max = int(min(all_x) * frame.shape[1]), int(max(all_x) * frame.shape[1])
        y_min, y_max = int(min(all_y) * frame.shape[0]), int(max(all_y) * frame.shape[0])
        
        # 主脸部框
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), COLOR_SAFE, 20, cv2.LINE_AA)
        
        def draw_eye_box(indices, color):
            ex_min = int(min([landmarks[i].x for i in indices]) * frame.shape[1])
            ex_max = int(max([landmarks[i].x for i in indices]) * frame.shape[1])
            ey_min = int(min([landmarks[i].y for i in indices]) * frame.shape[0])
            ey_max = int(max([landmarks[i].y for i in indices]) * frame.shape[0])
            cv2.rectangle(frame, (ex_min-5, ey_min-5), (ex_max+5, ey_max+5), color, 1, cv2.LINE_AA)

        LEFT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        RIGHT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        
        draw_eye_box(LEFT_EYE_INDICES, COLOR_TEXT_MAIN)
        draw_eye_box(RIGHT_EYE_INDICES, COLOR_TEXT_MAIN)

        # 3. 瞳孔定位
        if len(landmarks) > 473:
            for pupil_idx in [468, 473]:
                px, py = int(landmarks[pupil_idx].x * frame.shape[1]), int(landmarks[pupil_idx].y * frame.shape[0])
                cv2.circle(frame, (px, py), 1, COLOR_SAFE, -1)

        data_packet = {
            "eye_score": round(float(eye_val), 3),
            "yawn_score": round(float(yawn_val), 3),
            "tilt_val": round(float(tilt_val), 1),
            "smile_score": round(float(smile_val), 3),
            "confused_score": round(float(confused_val), 3),
            "distraction_score": round(float(distracted_val), 3),
            "status": current_global_status,
            "timestamp": time.time()
        }
        data_path = os.path.join(script_dir, "live_data.json")
        with open(data_path, "w") as f:
            json.dump(data_packet, f)
            # 以上是轮廓

        cv2.rectangle(overlay, (20, 20), (580, 380), COLOR_BG, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

       
        cv2.putText(frame, current_global_status, (40, 75), FONT, 1.4, current_global_color, 3, cv2.LINE_AA)
        cv2.line(frame, (40, 95), (540, 95), (100, 100, 100), 1, cv2.LINE_AA)

        
        cv2.putText(frame, f"EYE OPENNESS    {eye_val:.2f}", (45, 145), FONT, 0.7, e_col, 2, cv2.LINE_AA)
        cv2.putText(frame, f"MOUTH ACTIVITY  {yawn_val:.2f}", (45, 185), FONT, 0.7, y_col, 2, cv2.LINE_AA)
        cv2.putText(frame, f"HEAD STABILITY  {tilt_val:.1f} DEG", (45, 225), FONT, 0.7, t_col, 2, cv2.LINE_AA)
        
        
        cv2.line(frame, (45, 250), (300, 250), (60, 60, 60), 1, cv2.LINE_AA)
        cv2.putText(frame, f"SMILE (POSITIVE) {smile_val:.2f}", (45, 290), FONT, 0.7, s_col, 2, cv2.LINE_AA)
        cv2.putText(frame, f"CONFUSION INDEX  {confused_val:.2f}", (45, 330), FONT, 0.7, COLOR_TEXT_MAIN, 2, cv2.LINE_AA)
        cv2.putText(frame, f"DISTRACTION      {distracted_val:.2f}", (45, 370), FONT, 0.7, COLOR_TEXT_MAIN, 2, cv2.LINE_AA)

    else:
        cv2.rectangle(overlay, (20, 20), (580, 100), COLOR_BG, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, "SCANNING FOR OPERATOR", (40, 70), FONT, 1.0, (150, 150, 150), 2, cv2.LINE_AA)

    with lock:
        output_frame = frame.copy()

    cv2.imshow('Sentiment-Flow Sentinel Pro', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
