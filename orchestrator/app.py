from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import requests, numpy as np, cv2, os, json, time
from datetime import datetime
from graph_utils import generate_graphs 
from gemini_api import analyze_with_gemini  
# from email_utils import send_email_alert 
from fastapi.staticfiles import StaticFiles
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()

# === Output folder setup ===
outputs_path = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(outputs_path, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=outputs_path), name="outputs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# These URLs should point to your microservices, and will not be localhost if Docker is used!!!
CROWD_URL = "http://127.0.0.1:8100/analyze/" 
ENV_URL = "http://127.0.0.1:8200/analyze/"
EMOTION_URL = "http://127.0.0.1:8300/analyze/"
BODY_URL = "http://127.0.0.1:8400/analyze/"

SENDER_EMAIL = "keerthana240904@gmail.com"
SENDER_PASSWORD = "jlnq ffix tlhl ttvm"   # Use an app password, not your main password!
AUTHORITY_EMAIL = "testusersneezy@gmail.com"

# create a different file for this util function later
import smtplib
def send_email_alert(subject, message):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = AUTHORITY_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"Alert email sent to {AUTHORITY_EMAIL}")
    except Exception as e:
        print(f"Failed to send alert email: {e}")

def detect_anomalies(crowd_resp, env_resp, emotion_resp, posture_resp):
    anomalies = []
    alerts = []

    # === Emotion anomalies ===
    if "dominant_emotion" in emotion_resp:
        dom_emotion = emotion_resp["dominant_emotion"].lower()
        if dom_emotion in ["fear", "anger", "sad"]:
            anomalies.append(f"Dominant emotion is {dom_emotion.upper()} — possible distress detected.")
            alerts.append("⚠️ Emotional distress detected in crowd.")

    # === Posture anomalies ===
    if "aggregated_posture_bodylang" in posture_resp:
        agg_posture = posture_resp["aggregated_posture_bodylang"].get("posture", "").lower()
        body_lang = posture_resp["aggregated_posture_bodylang"].get("body_language", "").lower()
        if "bent" in agg_posture or "collapsed" in agg_posture:
            anomalies.append("Posture suggests leaning/bent position — potential fatigue or fear.")
        if "gesturing" in body_lang or "raised" in body_lang:
            anomalies.append("Frequent gesturing body language — possible agitation or warning signals.")
            alerts.append("⚠️ Agitated behavior detected.")

    # === Environment anomalies ===
    if "aggregated_environment" in env_resp:
        env = env_resp["aggregated_environment"]
        if env.get("cleanliness") == "dirty" or env.get("lighting") == "dim":
            anomalies.append("Poor environment detected — dirty or low lighting.")
        if env.get("location") == "outdoor" and env.get("weather") in ["stormy", "rainy"]:
            anomalies.append("Adverse weather conditions in outdoor scene.")

    # === Crowd anomalies ===
    if "crowd" in crowd_resp:
        if isinstance(crowd_resp, dict) and "dominant_state" in crowd_resp:
            if crowd_resp["dominant_state"] in ["chaotic", "panic"]:
                anomalies.append("Crowd appears chaotic or panicked.")
                alerts.append("🚨 Crowd panic detected.")
        elif "error" in crowd_resp:
            anomalies.append("Crowd analysis failed — unable to verify state.")

    # === Fallback ===
    if not anomalies:
        anomalies.append("No anomalies detected.")
    
    return {"anomalies": anomalies, "alerts": alerts}

@app.post("/process/")
async def process(file: UploadFile, context: str = Form(...)):
    contents = await file.read()
    input_path = f"uploads/{int(time.time())}_{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(input_path, "wb") as f:
        f.write(contents)

    # This part will be replaced by something that hopefully maybe uses parallel processing (cuz currently its serial), and
    # adding RL choose which services to call based on context!
    with open(input_path, "rb") as f:
        files = {"file": (file.filename, f, file.content_type)}
        try:
            crowd_resp = requests.post(CROWD_URL, files=files, timeout=300).json()
            f.seek(0)
            environment_resp = requests.post(ENV_URL, files=files, timeout=300).json()
            f.seek(0)
            emotion_resp = requests.post(EMOTION_URL, files=files, timeout=300).json()
            f.seek(0)
            posture_resp = requests.post(BODY_URL, files=files, timeout=300).json()


        except Exception as e:
            # This needs to be updated cuz what is this logic tsk tsk tsk
            crowd_resp = {"error": f"Crowd service failed: {e}"}
            environment_resp = {"error": f"Environment service failed: {e}"}
            emotion_resp = {"error": f"Emotion service failed: {e}"}
            posture_resp = {"error": f"Posture service failed: {e}"}


    combined_output = {
        "timestamp": datetime.now().isoformat(),
        "context": context,
        "crowd": crowd_resp,
        "environment": environment_resp,  
        "emotion": emotion_resp,      
        "posture": posture_resp,      
    }
    anomaly_results = detect_anomalies(crowd_resp, environment_resp, emotion_resp, posture_resp)
    combined_output.update(anomaly_results)


    json_path = f"outputs/result_{int(time.time())}.json"
    with open(json_path, "w") as f:
        json.dump(combined_output, f, indent=2)

    try:
        gemini_analysis = analyze_with_gemini(combined_output)
        print(gemini_analysis)
    except Exception as e:
        gemini_analysis = {"error": f"Gemini failed: {e}"}

    graphs = generate_graphs(combined_output) 
    
    if anomaly_results["alerts"]:
        alert_message = "\n".join(anomaly_results["alerts"] + anomaly_results["anomalies"])
        send_email_alert("🚨 Smart Surveillance Alert Detected", alert_message)

    return {
        "status": "success",
        "context": context,
        "results": combined_output,
        "gemini": gemini_analysis,
        "graphs": graphs,
    }

