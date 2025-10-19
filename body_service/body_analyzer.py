from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import pandas as pd
import joblib
import cv2
import json
import tempfile
import os
import numpy as np

app = FastAPI(title="Body Posture and Language Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)
posture_model = joblib.load(os.path.join(BASE_DIR, "posture_rf_model.pkl"))
bodylang_model = joblib.load(os.path.join(BASE_DIR, "body_language_rf_model.pkl"))
yolo_model = YOLO("yolov8n-pose.pt")

feature_cols = ['torso_angle_deg', 'head_angle_deg', 'left_knee_angle_deg', 'right_knee_angle_deg']

outputs_dir = os.path.join(BASE_DIR, "outputs")
os.makedirs(outputs_dir, exist_ok=True)

def extract_features_from_keypoints(kpts):

    return {
        'torso_angle_deg': 100.0,
        'head_angle_deg': 90.0,
        'left_knee_angle_deg': 170.0,
        'right_knee_angle_deg': 175.0
    }


def analyze_frame(frame):
    results = yolo_model.predict(source=frame, imgsz=640, conf=0.25, device='cpu')
    r = results[0]
    if len(r.keypoints) == 0:
        return None

    kpts_array = r.keypoints.xy.cpu().numpy()
    person_kpts = kpts_array[0]
    features = extract_features_from_keypoints(person_kpts)

    features_df = pd.DataFrame([features], columns=feature_cols)
    posture_pred = posture_model.predict(features_df)[0]
    bodylang_pred = bodylang_model.predict(features_df)[0]

    return {
        "posture": posture_pred,
        "body_language": bodylang_pred
    }


@app.post("/analyze/")
async def analyze(file: UploadFile):
    suffix = os.path.splitext(file.filename)[-1] or ".mp4"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
        tmp.flush()
        tmp_path = tmp.name

    try:
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise ValueError(f"Uploaded video file is empty: {tmp_path}")

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video file: {tmp_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps):
            fps = 30
        frame_interval = int(fps * 5)  # one frame every 5 seconds

        frame_idx = 0
        frame_results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                preds = analyze_frame(frame)
                if preds:
                    frame_results.append(preds)
            frame_idx += 1

        cap.release()
        if frame_results:
            posture_modes = [r["posture"] for r in frame_results]
            body_modes = [r["body_language"] for r in frame_results]
            agg_posture = max(set(posture_modes), key=posture_modes.count)
            agg_bodylang = max(set(body_modes), key=body_modes.count)
        else:
            return {"error": "No persons detected in any frames."}

        output = {
            "frames_analyzed": len(frame_results),
            "frame_results": frame_results,
            "aggregated_posture_bodylang": {
                "posture": agg_posture,
                "body_language": agg_bodylang
            }
        }

        return output

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
