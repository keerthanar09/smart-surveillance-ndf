from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import cv2, os, json, asyncio
import numpy as np
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CROWD_URL = "http://127.0.0.1:8100/analyze/"
ENV_URL   = "http://127.0.0.1:8200/analyze/"
EMOTION_URL = "http://127.0.0.1:8300/analyze/"
BODY_URL = "http://127.0.0.1:8400/analyze/"
MIN_PEOPLE_FOR_ALERT = 30

from fastapi.staticfiles import StaticFiles
app.mount("/outputs", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "outputs")), name="outputs")


def encode_frame(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()


def send_email_with_frame(subject, message, frame_bytes):
    msg = MIMEMultipart()
    msg["From"] = "keerthana240904@gmail.com"
    msg["To"] = "testusersneezy@gmail.com"
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    part = MIMEText(frame_bytes, "base64", "utf-8")
    part.add_header("Content-Disposition", "attachment; filename=alert.jpg")
    part.add_header("Content-Type", "image/jpeg")
    msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com",587) as server:
            server.starttls()
            server.login("keerthana240904@gmail.com","jlnq ffix tlhl ttvm")
            server.sendmail(msg["From"], msg["To"], msg.as_string())
    except Exception as e:
        print("send_email_with_frame: email send failed:", str(e))


def normalize_crowd_response(crowd_resp):
    if not isinstance(crowd_resp, dict):
        return crowd_resp

    if "zones" in crowd_resp and "aggregated_outputs" not in crowd_resp:
        try:
            agg = {z["id"]: {"avg_people": z.get("count", 0), "avg_density": z.get("density", 0), "dominant_state": z.get("state", "")} for z in crowd_resp.get("zones", [])}
            crowd_resp["aggregated_outputs"] = [{"aggregate": agg}]
        except Exception:
            crowd_resp["aggregated_outputs"] = []

    zones_summary = []
    total_people = 0.0
    agg_list = crowd_resp.get("aggregated_outputs") or []
    if agg_list and isinstance(agg_list, list):
        first = agg_list[0] or {}
        aggregate = first.get("aggregate", {})
        for zone_id, z in aggregate.items():
            avg_people = float(z.get("avg_people", 0))
            avg_density = float(z.get("avg_density", 0))
            dominant_state = str(z.get("dominant_state", "")).lower()
            dominant_insight = str(z.get("dominant_insight", "") if isinstance(z.get("dominant_insight", ""), str) else "")
            zones_summary.append({
                "id": zone_id,
                "avg_people": avg_people,
                "avg_density": avg_density,
                "dominant_state": dominant_state,
                "dominant_insight": dominant_insight
            })
            total_people += avg_people

    if not zones_summary and "zones" in crowd_resp:
        for z in crowd_resp.get("zones", []):
            cnt = float(z.get("count", 0))
            density = float(z.get("density", 0))
            zones_summary.append({
                "id": z.get("id"),
                "avg_people": cnt,
                "avg_density": density,
                "dominant_state": str(z.get("state", "")).lower(),
                "dominant_insight": ""
            })
            total_people += cnt

    crowd_resp["overall_crowd_count"] = float(total_people)
    crowd_resp["zones_summary"] = zones_summary
    if "dominant_state" not in crowd_resp or not crowd_resp.get("dominant_state"):
        if total_people >= 60:
            crowd_resp["dominant_state"] = "extreme"
        elif total_people >= 30:
            crowd_resp["dominant_state"] = "high_density"
        elif total_people >= 10:
            crowd_resp["dominant_state"] = "moderate"
        else:
            crowd_resp["dominant_state"] = "calm"

    if "motion_anomaly" not in crowd_resp:
        crowd_resp["motion_anomaly"] = {"is_running": False, "avg_motion": 0.0, "anomaly_score": 0.0}
    if "density_shift_anomaly" not in crowd_resp:
        crowd_resp["density_shift_anomaly"] = {"is_anomaly": False, "score": 0.0}

    return crowd_resp


def analyze_frame_with_services(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    files = {"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")}

    try:
        crowd = requests.post(CROWD_URL, files=files, timeout=6).json()
    except Exception as e:
        crowd = {"error": str(e)}

    try:
        env = requests.post(ENV_URL, files=files, timeout=6).json()
    except Exception as e:
        env = {"error": str(e)}

    try:
        emo = requests.post(EMOTION_URL, files=files, timeout=6).json()
    except Exception as e:
        emo = {"error": str(e)}

    try:
        post = requests.post(BODY_URL, files=files, timeout=6).json()
    except Exception as e:
        post = {"error": str(e)}

    try:
        crowd = normalize_crowd_response(crowd)
    except Exception:
        crowd = crowd if isinstance(crowd, dict) else {"error": "invalid crowd response"}

    posture_frame_results = []
    if isinstance(post, dict) and "individual" in post:
        for ind in post.get("individual", []):
            posture_frame_results.append({
                "posture": ind.get("posture"),
                "body_language": ind.get("body_language")
            })

    return {
        "crowd": crowd,
        "environment": env,
        "emotion": emo,
        "posture": {"frame_results": posture_frame_results},
        "raw_posture": post
    }


def detect_anomalies(crowd_resp, environment_resp, emotion_resp, posture_resp, crowd_history):
    should_alert = False
    reason_parts = []
    anomalies = []

    total_people = float(crowd_resp.get("overall_crowd_count", 0))
    motion_info = crowd_resp.get("motion_anomaly", {}) or {}
    motion = bool(motion_info.get("is_running", False))
    motion_score = float(motion_info.get("anomaly_score", 0) or motion_info.get("avg_motion", 0))
    density_shift = float(crowd_resp.get("density_shift_anomaly", {}).get("score", 0))
    crowd_state = str(crowd_resp.get("dominant_state", "calm")).lower()

    for z in crowd_resp.get("zones", []):
        dens = z.get("density", 0)
        if not z.get("dominant_state"):
            if dens < 0.0005:
                z["dominant_state"] = "low"
            elif dens < 0.001:
                z["dominant_state"] = "moderate"
            elif dens < 0.002:
                z["dominant_state"] = "high"
            else:
                z["dominant_state"] = "very_high"

    dominant_emotion = (emotion_resp or {}).get("dominant_emotion")
    positive_emotions = {"happy", "joy", "smile", "surprise"}
    negative_emotions = {"fear", "anger", "sad", "disgust"}

    emotion_missing = not dominant_emotion
    is_positive = dominant_emotion and dominant_emotion.lower() in positive_emotions
    # is_negative = (not is_positive) and (dominant_emotion and dominant_emotion.lower() in negative_emotions)

    posture_data = posture_resp.get("frame_results", [])
    bent = sum(1 for p in posture_data if p.get("posture") in ("crouching"))
    aggressive = sum(1 for p in posture_data if p.get("body_language") == "aggressive")
    gesturing = sum(1 for p in posture_data if p.get("body_language") == "gesturing")

    posture_anomaly = bent >= 3 and total_people > 5
    bodylang_anomaly = aggressive >= 2 or gesturing >= 4

    recent_counts = [c.get("overall_crowd_count", 0) for c in crowd_history if isinstance(c, dict)]
    significant_increase = len(recent_counts) >= 3 and recent_counts[-1] > np.mean(recent_counts[-3:]) * 1.3

    if not is_positive and (
        motion
        or motion_score > 1.2
        or density_shift > 0.15
        or crowd_state in ("high_density", "overcrowded")
        or significant_increase
    ):
        should_alert = True
        reason_parts.append("Crowd panic detected.")
        anomalies.append("Crowd anomaly: unusual motion or density surge detected.")

    if posture_anomaly:
        should_alert = True
        reason_parts.append(f"⚠️ Posture anomaly detected, {bent} people crouching.")
        anomalies.append(f"{bent} people show crouching posture (possible stress).")

    if bodylang_anomaly:
        should_alert = True
        reason_parts.append(f"⚠️ Body-language anomaly detected. {aggressive + gesturing} people showing possible agressive behaviour.")
        anomalies.append(f"{aggressive + gesturing} people show aggressive/gesturing behaviour.")

    if is_positive:
        should_alert = False
        reason_parts = [f"No alert — positive emotion ({dominant_emotion})."]
        anomalies = []

    env_summary = (
        f"Weather: {environment_resp.get('weather', 'unknown')}, "
        f"Lighting: {environment_resp.get('lighting', 'unknown')}, "
        f"Cleanliness: {environment_resp.get('cleanliness', 'unknown')}."
    )

    stress_factor = (density_shift + motion_score) / 4.0
    posture_factor = 0.2 if posture_anomaly else 0
    bodylang_factor = 0.2 if bodylang_anomaly else 0
    wellness_score = 1.0 if is_positive else max(0.2, 1.0 - stress_factor - posture_factor - bodylang_factor)

    return {
        "alert": should_alert,
        "reason": " ".join(reason_parts) if reason_parts else "steady state",
        "anomalies": anomalies,
        "wellness_score": round(wellness_score, 2),
        "environment_summary": env_summary,
    }



@app.post("/stream/")
async def stream(file: UploadFile, context: str = Form(...), request: Request = None):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp.write(await file.read())
    temp.flush()
    video_path = temp.name

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = max(1, int(fps * 1.5)) 

    HISTORY_LEN = 8
    recent_crowd_history = []

    async def event_stream():
        frame_count = 0
        anomalous_frame = None
        accumulated = []

        try:
            while True:
                if request is not None:
                    try:
                        if await request.is_disconnected():
                            break
                    except Exception:
                        pass

                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    loop = asyncio.get_running_loop()
                    results = await loop.run_in_executor(None, analyze_frame_with_services, frame)
                    accumulated.append({"time": datetime.now().isoformat(), "results": results})

                    # ensure crowd has overall_crowd_count
                    crowd = results.get("crowd", {}) or {}
                    if "overall_crowd_count" not in crowd or (isinstance(crowd.get("overall_crowd_count"), (int, float)) and crowd.get("overall_crowd_count") == 0 and crowd.get("zones")):
                        # fallback: sum aggregated_outputs or zones
                        try:
                            total = 0.0
                            for el in (crowd.get("aggregated_outputs") or []):
                                agg = el.get("aggregate", {})
                                for z in agg.values():
                                    total += float(z.get("avg_people", 0))
                            if total == 0.0 and crowd.get("zones"):
                                for z in crowd.get("zones", []):
                                    total += float(z.get("count", 0))
                            crowd["overall_crowd_count"] = float(total)
                        except Exception:
                            crowd["overall_crowd_count"] = 0.0

                    recent_crowd_history.append(crowd)
                    if len(recent_crowd_history) > HISTORY_LEN:
                        recent_crowd_history.pop(0)

                    anomaly = detect_anomalies(
                        crowd,
                        results.get("environment", {}),
                        results.get("emotion", {}),
                        results.get("posture", {}),
                        recent_crowd_history
                    )

                    payload = {
                        "time": datetime.now().isoformat(),
                        "context": context,
                        "results": results,
                        "alert": anomaly.get("alert", False),
                        "reason": anomaly.get("reason", ""),
                        "graphs": None,
                        "gemini": None
                    }

                    # include anomaly metadata / wellness
                    payload["anomaly_meta"] = anomaly

                    if anomaly.get("alert", False):
                        anomalous_frame = encode_frame(frame)
                        try:
                            send_email_with_frame(
                                "🚨 Crowd Alert Detected",
                                anomaly["reason"],
                                anomalous_frame
                            )
                        except Exception as e:
                            print("email send attempt failed:", str(e))
                        payload["anomaly_frame"] = anomalous_frame.hex()

                    yield f"data: {json.dumps(payload)}\n\n"

                frame_count += 1
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            pass
        finally:
            try:
                cap.release()
            except Exception:
                pass
            try:
                os.remove(video_path)
            except Exception:
                pass

        yield f"data: {json.dumps({'done': True, 'frames_sent': frame_count, 'accumulated': accumulated})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
