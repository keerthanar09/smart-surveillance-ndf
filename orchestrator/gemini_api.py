import json
import os
import requests
from datetime import datetime

import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_with_gemini(results):
    prompt = f"""
    You are an AI analysis system.
    Summarize the crowd, emotion, posture, and environment data below into concise insights.
    Explain correlations, trends, and possible causes in human terms.
    Data: {json.dumps(results, indent=2)}
    """
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    response = model.generate_content(prompt)
    print(response)

    if response.text:
        text = response.text
        return {"summary": text, "timestamp": str(datetime.now())}
    else:
        return {"summary": "Error generating insights.", "error": text}