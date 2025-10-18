import os
import json
import cv2
import torch
import numpy as np
from torch import nn
from torchvision import models, transforms
from PIL import Image
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from collections import Counter, deque
import tempfile

app = FastAPI(title="Environmental Factor Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
