import cv2
import json
import joblib
import numpy as np
import tempfile
import os
from collections import deque, Counter
from ultralytics import YOLO
from sklearn.cluster import DBSCAN
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

class CrowdAnalyser:
    def __init__(self, grid_size=(4, 4), history=10):
        self.model = YOLO("yolov8_mot20_best.pt")
        self.grid_size = grid_size
        self.classifier = joblib.load("zone_rf.pkl")
        self.history_len = history
        self.history = {
            f"{chr(65+i)}{j+1}": deque(maxlen=history)
            for i in range(grid_size[0]) for j in range(grid_size[1])
        }

    def divide_frame(self, frame):
        h, w, _ = frame.shape
        gh, gw = self.grid_size
        sx, sy = w // gw, h // gh
        zones = []
        for i in range(gh):
            for j in range(gw):
                x1, y1, x2, y2 = j*sx, i*sy, (j+1)*sx, (i+1)*sy
                zones.append(((x1, y1, x2, y2), f"{chr(65+i)}{j+1}"))
        return zones

    def extract_features(self, frame):
        results = self.model(frame, verbose=False)
        people = [box.xyxy[0].cpu().numpy() for box in results[0].boxes if int(box.cls[0]) == 0]
        zones = self.divide_frame(frame)
        feats = {}
        for (x1, y1, x2, y2), name in zones:
            zp = [p for p in people if x1 <= (p[0]+p[2])/2 <= x2 and y1 <= (p[1]+p[3])/2 <= y2]
            n = len(zp)
            d = n / ((x2-x1)*(y2-y1))
            centroids = [((p[0]+p[2])/2, (p[1]+p[3])/2) for p in zp]
            c = 0
            if centroids:
                clustering = DBSCAN(eps=40, min_samples=2).fit(np.array(centroids))
                c = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
            feats[name] = [n, d, c]
        return feats

    def classify_zones(self, features):
        json_out = {"zones": {}}
        for z, fs in features.items():
            pred = self.classifier.predict([fs])[0]
            conf = max(self.classifier.predict_proba([fs])[0])
            prev = self.history[z][-1] if len(self.history[z]) else None
            insight = self.get_zone_insight(z, prev, fs, pred)
            self.history[z].append({
                "people": fs[0],
                "density": fs[1],
                "clusters": fs[2],
                "state": pred,
                "insight": insight
            })
            json_out["zones"][z] = {
                "people": fs[0],
                "density": fs[1],
                "clusters": fs[2],
                "state": pred,
                "confidence": float(conf),
                "insight": insight
            }
        return json_out

    def get_zone_insight(self, zone, prev, fs, pred):
        if not prev:
            return "initial observation"
        delta_people = fs[0] - prev["people"]
        delta_density = fs[1] - prev["density"]
        if delta_people > 3 or delta_density > 0.001:
            return "crowd surge detected"
        elif prev["state"] == "calm" and pred == "chaotic":
            return "panic onset"
        elif prev["state"] == "chaotic" and pred == "calm":
            return "crowd calming"
        elif abs(delta_people) < 1 and abs(delta_density) < 0.0001:
            return "steady state"
        else:
            return "minor variation"

    def aggregate_results(self, frames):
        agg = {}
        all_zones = frames[-1]["zones"].keys()
        for z in all_zones:
            people_vals = [f["zones"][z]["people"] for f in frames]
            density_vals = [f["zones"][z]["density"] for f in frames]
            cluster_vals = [f["zones"][z]["clusters"] for f in frames]
            states = [f["zones"][z]["state"] for f in frames]
            insights = [f["zones"][z]["insight"] for f in frames]

            agg[z] = {
                "avg_people": np.mean(people_vals),
                "avg_density": np.mean(density_vals),
                "avg_clusters": np.mean(cluster_vals),
                "dominant_state": Counter(states).most_common(1)[0][0],
                "dominant_insight": Counter(insights).most_common(1)[0][0]
            }
        return agg

    def analyse_video(self, video_path):
        """Main function to analyze a full video and return JSON results"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_interval = int(fps)
        frame_idx = 0
        processed_frames = []
        aggregated_outputs = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                feats = self.extract_features(frame)
                zones_json = self.classify_zones(feats)
                processed_frames.append({"frame": frame_idx, "zones": zones_json["zones"]})

                if len(processed_frames) % 10 == 0:
                    agg = self.aggregate_results(processed_frames[-10:])
                    aggregated_outputs.append({
                        "frame_window": [processed_frames[-10]["frame"], frame_idx],
                        "aggregate": agg,
                    })
                    print(f"Aggregated output for frames {processed_frames[-10]['frame']}–{frame_idx}")
            frame_idx += 1

        cap.release()

        # Handle short videos (<10s)
        if len(processed_frames) > 0 and len(processed_frames) % 10 != 0:
            agg = self.aggregate_results(processed_frames[-(len(processed_frames) % 10):])
            aggregated_outputs.append({
                "frame_window": [processed_frames[0]["frame"], processed_frames[-1]["frame"]],
                "aggregate": agg,
            })
            print(f"Final aggregated output for frames {processed_frames[0]['frame']}–{processed_frames[-1]['frame']}")

        return {"aggregated_outputs": aggregated_outputs}



app = FastAPI(title="Crowd Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = CrowdAnalyser()

@app.post("/analyze/")
async def analyze(file: UploadFile):
    """Handles video upload and returns crowd analysis results."""
    suffix = os.path.splitext(file.filename)[-1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = analyzer.analyse_video(tmp_path)
        return result
    finally:
        os.remove(tmp_path)