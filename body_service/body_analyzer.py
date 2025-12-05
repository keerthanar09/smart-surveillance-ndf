import os
import cv2
import json
import joblib
import numpy as np
import tensorflow as tf
import traceback
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = "./models"   
POSTURE_PATHS = [
    "posture_rf_model.pkl",
    "posture_model.pkl",
    "posture_model_converted.h5",
    "fine_tuned_posture_model.h5",
    "posture_model.h5"
]

BODY_PATHS = [
    "body_language_rf_model.pkl",
    "body_language_model.pkl",
    "body_language_model.h5"
]

def load_first_available(paths):
    for p in paths:
        full = os.path.join(BASE, p)
        if os.path.exists(full):
            try:
                if full.endswith(".pkl") or full.endswith(".joblib"):
                    m = joblib.load(full)
                    return m, "sklearn"
                if full.endswith(".h5") or full.endswith(".keras"):
                    m = tf.keras.models.load_model(full)
                    return m, "keras"
            except Exception:
                traceback.print_exc()
                continue
    return None, None

posture_model, posture_type = load_first_available(POSTURE_PATHS)
body_model, body_type = load_first_available(BODY_PATHS)

print("✅ Loaded Posture model:", posture_type)
print("✅ Loaded Body model:", body_type)

yolo = YOLO("yolov8n-pose.pt")

POSTURE_CLASSES = ['bent_forward','crouching','slight_lean','slouching','upright']
BODY_CLASSES = ['normal','gesturing','aggressive','defensive']

def extract_8_features_from_kps(kps):
    kp = np.array(kps)
    xy = kp[:, :2] if kp.shape[-1] >= 2 else kp

    def g(i):
        return xy[i] if 0 <= i < len(xy) else None

    nose = g(0)
    left_eye = g(1)
    left_ear = g(3)
    left_shoulder = g(5)
    right_shoulder = g(6)
    left_hip = g(11)
    right_hip = g(12)
    left_knee = g(13)
    right_knee = g(14)
    left_ankle = g(15)
    right_ankle = g(16)
    left_wrist = g(9)
    right_wrist = g(10)

    def angle(a,b,c):
        if a is None or b is None or c is None: return 0.0
        a,b,c = np.array(a), np.array(b), np.array(c)
        ba = a - b
        bc = c - b
        denom = np.linalg.norm(ba)*np.linalg.norm(bc)
        if denom == 0: return 0.0
        cosang = np.dot(ba, bc)/denom
        cosang = np.clip(cosang, -1, 1)
        return float(np.degrees(np.arccos(cosang)))

    return {
        "torso_angle_deg": angle(left_shoulder, left_hip, right_hip),
        "head_angle_deg": angle(left_shoulder, left_ear, left_eye),
        "left_knee_angle_deg": angle(left_hip, left_knee, left_ankle),
        "right_knee_angle_deg": angle(right_hip, right_knee, right_ankle),
        "norm_nose_y": float(nose[1]) if nose is not None else 0,
        "shoulder_width_norm": float(np.linalg.norm(np.array(left_shoulder)-np.array(right_shoulder))) 
                               if left_shoulder is not None and right_shoulder is not None else 0,
        "left_wrist_shoulder_dist": float(np.linalg.norm(np.array(left_wrist)-np.array(left_shoulder))) 
                                    if left_wrist is not None and left_shoulder is not None else 0,
        "right_wrist_shoulder_dist": float(np.linalg.norm(np.array(right_wrist)-np.array(right_shoulder))) 
                                     if right_wrist is not None and right_shoulder is not None else 0,
    }

def model_predict(model, mtype, features):
    X = np.array([features], dtype=np.float32)

    # ✅ Automatic feature trimming/padding for sklearn models
    if mtype == "sklearn":
        expected = getattr(model, "n_features_in_", len(features))

        # If model expects fewer features → trim
        if X.shape[1] > expected:
            X = X[:, :expected]

        # If model expects more features → pad with zeros
        elif X.shape[1] < expected:
            diff = expected - X.shape[1]
            X = np.hstack([X, np.zeros((1, diff))])

        try:
            probs = model.predict_proba(X)[0]
        except:
            pred = model.predict(X)[0]
            probs = np.zeros(len(POSTURE_CLASSES))
            probs[pred] = 1
        return probs

    # ✅ Keras model (no trimming)
    elif mtype == "keras":
        return model.predict(X, verbose=0)[0]

    return None

@app.post("/analyze/")
async def analyze(file: UploadFile):

    img_bytes = await file.read()
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    results = yolo(frame)[0]
    if results.keypoints is None:
        return {"people": 0, "posture": {}, "body_language": {}}

    kps = results.keypoints.xy.cpu().numpy()

    person_postures = []
    person_bodies = []

    for kp in kps:
        feats = extract_8_features_from_kps(kp)

        posture_probs = model_predict(posture_model, posture_type, list(feats.values()))
        body_probs = model_predict(body_model, body_type, list(feats.values()))

        posture_label = POSTURE_CLASSES[int(np.argmax(posture_probs))]
        body_label = BODY_CLASSES[int(np.argmax(body_probs))]

        person_postures.append(posture_label)
        person_bodies.append(body_label)

    def summarize(preds, class_list):
        total = len(preds)
        out = {}
        for c in class_list:
            if total == 0:
                out[c] = 0.0
            out[c] = round(preds.count(c)/total*100, 2)
        return out

    return {
        "people": len(kps),
        "posture_summary": summarize(person_postures, POSTURE_CLASSES),
        "body_lang_summary": summarize(person_bodies, BODY_CLASSES),
        "individual": [
            {"posture": p, "body_language": b}
            for p,b in zip(person_postures, person_bodies)
        ]
    }
