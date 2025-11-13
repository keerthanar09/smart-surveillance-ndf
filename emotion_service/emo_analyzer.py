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

# ================================
# Load model once
# ================================
MODEL_PATH = "./emomodel.keras"
emotion_model = load_model(MODEL_PATH)

emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
picture_size = 48

# Haar Cascade for face detection
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def bytes_to_cv2_image(b: bytes):
    arr = np.frombuffer(b, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def predict_single_face(gray_crop):
    """Predicts using the emotion model and returns numpy preds + percentage mappings."""
    resized = cv2.resize(gray_crop, (picture_size, picture_size))
    img_arr = img_to_array(resized)
    img_arr = np.expand_dims(img_arr, axis=0)
    img_arr = img_arr / 255.0

    preds = emotion_model.predict(img_arr, verbose=0)[0]

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

    # Detect faces
    faces = face_detector.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
    total_faces = len(faces)

    if total_faces == 0:
        return {
            "frames_analyzed": 1,
            "total_faces_detected": 0,
            "emotion_distribution": {},
            "dominant_emotion": None,
        }

    # Accumulate scores
    accumulated = [0.0] * len(emotion_labels)

    for (x, y, w, h) in faces:
        face_crop = gray[y:y + h, x:x + w]
        preds, _ = predict_single_face(face_crop)

        # Convert numpy → Python float
        for i in range(len(accumulated)):
            accumulated[i] += float(preds[i])

    avg_scores = [acc / total_faces for acc in accumulated]

    # ✅ REMOVE ANGRY from distribution
    emotion_distribution = {
        emotion_labels[i]: float(avg_scores[i]*100)
        for i in range(len(emotion_labels))
        if emotion_labels[i] != "angry"
    }

    # ✅ REMOVE ANGRY from dominant emotion
    filtered_scores = {
        emotion_labels[i]: float(avg_scores[i]*100)
        for i in range(len(emotion_labels))
        if emotion_labels[i] != "angry"
    }

    dominant = max(filtered_scores, key=filtered_scores.get) if filtered_scores else None

    return {
        "frames_analyzed": 1,
        "total_faces_detected": total_faces,
        "emotion_distribution": emotion_distribution,
        "dominant_emotion": dominant,
    }
