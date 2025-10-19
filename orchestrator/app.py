from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import requests, numpy as np, cv2, os, json, time
from datetime import datetime
from graph_utils import generate_graphs 
from gemini_api import analyze_with_gemini  
# from email_utils import send_email_alert 
from fastapi.staticfiles import StaticFiles

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


@app.post("/process/")
async def process(file: UploadFile, context: str = Form(...)):
    contents = await file.read()
    input_path = f"uploads/{int(time.time())}_{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(input_path, "wb") as f:
        f.write(contents)

    # sends the video to be processed by crowdservice
    with open(input_path, "rb") as f:
        files = {"file": (file.filename, f, file.content_type)}
        try:
            crowd_resp = requests.post(CROWD_URL, files=files, timeout=300).json()
            f.seek(0)
            environment_resp = requests.post(ENV_URL, files=files, timeout=300).json()
            f.seek(0)
            emotion_resp = requests.post(EMOTION_URL, files=files, timeout=300).json()


        except Exception as e:
            crowd_resp = {"error": f"Crowd service failed: {e}"}
            environment_resp = {"error": f"Environment service failed: {e}"}
            emotion_resp = {"error": f"Emotion service failed: {e}"}


    # Placeholders for other services ===
    # environment_resp = requests.post(ENV_URL, files=files).json()
    # emotion_resp = requests.post(EMOTION_URL, files=files).json()
    # posture_resp = requests.post(POSTURE_URL, files=files).json()

    combined_output = {
        "timestamp": datetime.now().isoformat(),
        "context": context,
        "crowd": crowd_resp,
        "environment": environment_resp,  
        "emotion": emotion_resp,      
        "posture": None,      
    }

    json_path = f"outputs/result_{int(time.time())}.json"
    with open(json_path, "w") as f:
        json.dump(combined_output, f, indent=2)

    # Gemini processing
    try:
        gemini_analysis = analyze_with_gemini(combined_output)
        print(gemini_analysis)
    except Exception as e:
        gemini_analysis = {"error": f"Gemini failed: {e}"}

    graphs = generate_graphs(combined_output)  # Save graphs under outputs/
    
    # # === Alert ===
    # if "anomaly" in gemini_analysis.get("summary", "").lower():
    #     send_email_alert("Anomaly detected in surveillance", gemini_analysis["summary"])

    return {
        "status": "success",
        "context": context,
        "results": combined_output,
        "gemini": gemini_analysis,
        "graphs": graphs,
    }

