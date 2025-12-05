import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from keras.models import load_model
from keras.preprocessing.image import img_to_array

app = FastAPI(title="Emotion Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


MODEL_PATH = "./emomodel.hdf5"
emotion_model = load_model(MODEL_PATH, compile=False)

emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
picture_size = 64

face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def bytes_to_cv2_image(b: bytes):
    arr = np.frombuffer(b, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def predict_single_face(gray_crop):
    resized = cv2.resize(gray_crop, (64, 64))
    resized = resized.astype("float32") / 255.0
    resized = np.expand_dims(resized, axis=-1)
    resized = np.expand_dims(resized, axis=0)

    preds = emotion_model.predict(resized, verbose=0)[0]

    percentages = {
        emotion_labels[i]: f"{float(preds[i]) * 100:.2f}%"
        for i in range(len(emotion_labels))
    }

    return preds, percentages



@app.post("/analyze/")
async def analyze_emotions(file: UploadFile):
    data = await file.read()
    frame = bytes_to_cv2_image(data)

    if frame is None:
        return {"error": "Failed to decode image"}

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
    total_faces = len(faces)

    if total_faces == 0:
        return {
            "frames_analyzed": 1,
            "total_faces_detected": 0,
            "emotion_distribution": {},
            "dominant_emotion": None,
        }

    accumulated = np.zeros(len(emotion_labels), dtype=float)
    for (x, y, w, h) in faces:
        face_crop = gray[y:y+h, x:x+w]

        if face_crop.size == 0:
            continue

        preds, _ = predict_single_face(face_crop)
        accumulated += preds
    avg_scores = accumulated / total_faces

    emotion_distribution = {
        emotion_labels[i]: float(avg_scores[i]) * 100.0
        for i in range(len(emotion_labels))
    }
    dominant = max(emotion_distribution, key=emotion_distribution.get)

    return {
        "frames_analyzed": 1,
        "total_faces_detected": total_faces,
        "emotion_distribution": emotion_distribution,
        "dominant_emotion": dominant,
    }
