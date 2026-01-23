import os
import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from crowd_utils import MC_CNN
import tempfile

app = FastAPI(title="Crowd Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

outputs_path = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(outputs_path, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

CROWD_MODEL_PATH = os.path.join(os.path.dirname(__file__), "mccnn_crowd.pth")

GRID_SIZE = 4
MOTION_ZSCORE_THRESHOLD = 1.0 
MOTION_AVG_THRESHOLD = 1.2
MIN_PEOPLE_FOR_ALERT = 3 
DENSITY_SHIFT_ALERT = 0.15

crowd_model = MC_CNN().to(DEVICE)
crowd_model.load_state_dict(torch.load(CROWD_MODEL_PATH, map_location=DEVICE))
crowd_model.eval()

prev_gray = None
motion_history = []
MAX_MOTION_HISTORY = 12

prev_density_zones = None
avg_density = 0.0
frame_counter = 0


def compute_motion_anomaly(frame):
    global prev_gray, motion_history
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if prev_gray is None:
        prev_gray = gray
        motion_history = [0.0]
        return 0.0, 0.0

    flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None,
                                        pyr_scale=0.5, levels=3, winsize=15,
                                        iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    avg_motion = float(np.mean(mag))

    motion_history.append(avg_motion)
    if len(motion_history) > MAX_MOTION_HISTORY:
        motion_history.pop(0)

    mean_motion = float(np.mean(motion_history)) if motion_history else 0.0
    std_motion = float(np.std(motion_history)) if motion_history else 0.0

    if std_motion < 1e-6:
        anomaly_score = 0.0
    else:
        anomaly_score = float((avg_motion - mean_motion) / (std_motion + 1e-6))

    prev_gray = gray
    return avg_motion, anomaly_score


def dynamic_threshold(frame, total_count):
    global avg_density, frame_counter

    frame_area = frame.shape[0] * frame.shape[1]
    density_norm = total_count / (frame_area + 1e-6)

    frame_counter += 1
    avg_density = (avg_density * (frame_counter - 1) + density_norm) / frame_counter

    density_thresh = max(0.00001, 0.00015 * (frame_area / (640 * 480)))
    motion_thresh = MOTION_AVG_THRESHOLD * (1 + 0.5 * (density_norm / (avg_density + 1e-6)))

    return density_thresh, motion_thresh


def process_crowd_frame(frame, frame_idx, emotion_state=None):
    global prev_density_zones
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    h = (h // GRID_SIZE) * GRID_SIZE
    w = (w // GRID_SIZE) * GRID_SIZE
    img = cv2.resize(img, (w, h))

    img_t = img.transpose((2, 0, 1))
    tensor = torch.tensor(img_t / 255.0, dtype=torch.float32).unsqueeze(0).to(DEVICE)

    with torch.inference_mode():
        density_map = crowd_model(tensor)
        total_count = float(torch.sum(density_map))

    dmap = density_map.squeeze().cpu().numpy()
    H, W = dmap.shape
    zH, zW = H // GRID_SIZE, W // GRID_SIZE

    zones = []
    current_zones = []

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            zone = dmap[r*zH:(r+1)*zH, c*zW:(c+1)*zW]
            zone_count = float(np.sum(zone))
            zone_density = zone_count / (zH * zW + 1e-6)
            zones.append({"id": f"{r}_{c}", "count": zone_count, "density": zone_density})
            current_zones.append(zone)

    density_shift = 0.0
    if prev_density_zones is not None:
        total_diff = sum(abs(np.sum(current_zones[i]) - np.sum(prev_density_zones[i])) for i in range(GRID_SIZE**2))
        density_shift = float(total_diff / (GRID_SIZE**2))
    prev_density_zones = current_zones

    frame_area = w * h
    avg_density = total_count / (frame_area + 1e-6)
    low_thr, motion_thresh = dynamic_threshold(frame, total_count)[0], dynamic_threshold(frame, total_count)[1]

    if avg_density < 0.00012:
        dominant_state = "low_density"
    elif avg_density < 0.00035:
        dominant_state = "moderate"
    elif avg_density < 0.0008:
        dominant_state = "high_density"
    else:
        dominant_state = "overcrowded"

    if total_count < MIN_PEOPLE_FOR_ALERT:
        dominant_state = "calm"

    avg_motion, motion_anomaly_score = compute_motion_anomaly(frame)

    is_running = (motion_anomaly_score > MOTION_ZSCORE_THRESHOLD) or (avg_motion > MOTION_AVG_THRESHOLD)
    is_density_spike = density_shift > DENSITY_SHIFT_ALERT
    negative_emotions = {"fear", "anger", "sad", "disgust"}
    is_negative_emotion = bool(emotion_state and str(emotion_state).lower() in negative_emotions)

    is_anomaly = False
    reason = "steady state"

    if dominant_state == "overcrowded" and (is_running or is_negative_emotion or is_density_spike):
        is_anomaly = True
        reason = "crowd panic detected"

    elif is_running and (total_count >= MIN_PEOPLE_FOR_ALERT or is_density_spike):
        is_anomaly = True
        reason = "sudden running / surge detected"

    elif is_density_spike and avg_density > 0.0002 and total_count >= MIN_PEOPLE_FOR_ALERT:
        is_anomaly = True
        reason = "sudden density shift detected"

    aggregate = {
        z["id"]: {
            "avg_people": z["count"],
            "avg_density": z["density"],
            "dominant_state": dominant_state,
            "dominant_insight": ""
        }
        for z in zones
    }

    total_people = float(sum(z["count"] for z in zones))

    result = {
        "frame": frame_idx,
        "overall_crowd_count": float(total_people),
        "zones": zones,
        "aggregated_outputs": [{"aggregate": aggregate}],
        "density_shift_anomaly": {"score": float(density_shift), "is_anomaly": bool(density_shift > DENSITY_SHIFT_ALERT)},
        "motion_anomaly": {
            "is_running": bool(is_running),
            "avg_motion": float(avg_motion),
            "anomaly_score": float(motion_anomaly_score)
        },
        "combined_anomaly": bool(is_anomaly),
        "reason": reason or "steady state",
        "dominant_state": dominant_state,
        "avg_density": float(avg_density)
    }

    return result


def compute_crowd_state(crowd_frames):
    if not crowd_frames:
        return "unknown"
    counts = [c.get("overall_crowd_count", 0) for c in crowd_frames]
    max_count = max(counts)
    if max_count < 10:
        return "low_density"
    if max_count < 30:
        return "moderate"
    if max_count < 60:
        return "high_density"
    return "extreme"


@app.post("/analyze/")
async def analyze_frame_api(file: UploadFile):
    data = await file.read()
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return {"error": "failed to decode image"}
    return process_crowd_frame(frame, 0)
