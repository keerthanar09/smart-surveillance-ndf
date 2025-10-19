import os
import json
import torch
from torch import nn
from torchvision import models, transforms
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import cv2
import numpy as np
from collections import Counter
import tempfile

app = FastAPI(title="Environment Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

features = {
    "weather": ["sunny", "rainy", "snowy", "cloudy"],
    "lighting": ["day", "night", "dim", "bright"],
    "location": ["indoor", "outdoor"],
    "cleanliness": ["clean", "messy"]
}

num_features = 512

class MultiFeatureModel(nn.Module):
    def __init__(self, backbone, features):
        super().__init__()
        self.backbone = backbone
        self.backbone.fc = nn.Identity()
        self.feature_heads = nn.ModuleDict({
            feat: nn.Linear(num_features, len(classes)) for feat, classes in features.items()
        })

    def forward(self, x):
        x = self.backbone(x)
        out = {feat: head(x) for feat, head in self.feature_heads.items()}
        return out

model = MultiFeatureModel(models.resnet18(weights=None), features)
model_path = os.path.join(os.path.dirname(__file__), "multi_feature_model.pth")
model.load_state_dict(torch.load(model_path, map_location="cpu"))
model.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(outputs_dir, exist_ok=True)

def analyze_frame(frame):
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    img_t = transform(img).unsqueeze(0)
    with torch.no_grad():
        outputs = model(img_t)
        preds = {feat: features[feat][torch.argmax(out).item()] for feat, out in outputs.items()}
    return preds


def aggregate_results(results):
    agg = {}
    if not results:
        return agg
    for feat in features.keys():
        feat_values = [r[feat] for r in results]
        agg[feat] = Counter(feat_values).most_common(1)[0][0]
    return agg

@app.post("/analyze/")
async def analyze(file: UploadFile):
    suffix = os.path.splitext(file.filename)[-1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = await file.read(1024 * 1024)  
            if not chunk:
                break
            tmp.write(chunk)
        tmp.flush()  
        tmp_path = tmp.name

    try:
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise ValueError(f"Uploaded video file is empty: {tmp_path}")

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video file: {tmp_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or np.isnan(fps):
            fps = 30 
        frame_interval = int(fps * 10)  

        frame_idx = 0
        frame_results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                preds = analyze_frame(frame)
                frame_results.append(preds)
            frame_idx += 1

        cap.release()

        agg = aggregate_results(frame_results)
        output = {
            "frames_analyzed": len(frame_results),
            "frame_results": frame_results,
            "aggregated_environment": agg
        }

        return output

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
