from keras.models import load_model
from collections import Counter
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware  
import cv2, numpy as np, os, json, tempfile


app = FastAPI(title="Emotion Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

model_path = os.path.join(os.path.dirname(__file__), "emotion_model.keras")
model  = load_model(model_path)
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

@app.post("/analyze/")
async def analyze_emotions(file: UploadFile):
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, file.filename)
    with open(video_path, "wb") as f:
        f.write(await file.read())

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Could not open uploaded video file"}

    frame_skip = 5  # process every 3rd frame
    frame_count = 0
    all_emotions = []

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        frame_emotions = []

        for (x, y, w, h) in faces:
            face_img = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_img, (48, 48))
            face_normalized = face_resized / 255.0
            face_input = np.expand_dims(face_normalized, axis=(0, -1))
            pred = model.predict(face_input, verbose=0)
            emotion_index = int(np.argmax(pred))
            frame_emotions.append(emotion_labels[emotion_index])

        all_emotions.extend(frame_emotions)

    cap.release()

    if len(all_emotions) == 0:
        result = {"message": "No faces detected in processed frames."}
    else:
        counts = Counter(all_emotions)
        total = len(all_emotions)
        percentages = {emo: round((count / total) * 100, 2) for emo, count in counts.items()}
        result = {
            "frames_analyzed": frame_count,
            "total_faces_detected": total,
            "emotion_distribution": percentages,
            "dominant_emotion": max(percentages, key=percentages.get),
        }

    return result