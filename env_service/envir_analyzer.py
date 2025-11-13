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

# ✅ Updated feature definitions (same as your Colab training code)
features = {
    "weather": ["sunny", "rainy", "snowy", "cloudy"],
    "lighting": ["day", "night", "dim", "bright", "dark"],
    "location": ["indoor", "outdoor"],
    "cleanliness": ["clean", "messy"]
}

# ✅ Load ResNet50 backbone dimension
base_model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
num_features = base_model.fc.in_features



# ✅ Multi-head model (same architecture as Colab)
class MultiFeatureModel(nn.Module):
    def __init__(self, backbone, features):
        super().__init__()
        self.backbone = backbone
        self.backbone.fc = nn.Identity()
        self.feature_heads = nn.ModuleDict({
            feat: nn.Linear(num_features, len(classes))
            for feat, classes in features.items()
        })

    def forward(self, x):
        x = self.backbone(x)
        out = {feat: head(x) for feat, head in self.feature_heads.items()}
        return out


# ✅ Load model for inference
model = MultiFeatureModel(base_model, features)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "best_multi_feature_model.pth")
state = torch.load(model_path, map_location="cpu")
model.load_state_dict(state)
model.eval()

# ✅ Inference transforms (same as your validation transform)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def analyze_frame(frame):
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    img_t = transform(img).unsqueeze(0)

    with torch.no_grad():
        outputs = model(img_t)
        preds = {
            feat: features[feat][torch.argmax(logits).item()]
            for feat, logits in outputs.items()
        }
    return preds


def aggregate_results(results):
    if not results:
        return {}

    agg = {}
    for feat in features.keys():
        values = [r[feat] for r in results]
        agg[feat] = Counter(values).most_common(1)[0][0]

    return agg


@app.post("/analyze/")
async def analyze(file: UploadFile):
    img_bytes = await file.read()
    npimg = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    preds = analyze_frame(frame)
    return preds
