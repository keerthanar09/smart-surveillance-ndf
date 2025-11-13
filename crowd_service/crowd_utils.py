import torch
import torch.nn as nn
import torch.nn.functional as F
class MC_CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.column1 = nn.Sequential(
            nn.Conv2d(3, 8, 9, padding='same'),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 7, padding='same'),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 7, padding='same'),
            nn.ReLU(),
            nn.Conv2d(32, 16, 7, padding='same'),
            nn.ReLU(),
            nn.Conv2d(16, 8, 7, padding='same'),
            nn.ReLU(),
        )

        self.column2 = nn.Sequential(
            nn.Conv2d(3, 10, 7,padding='same'),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(10, 20, 5,padding='same'),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(20, 40, 5,padding='same'),
            nn.ReLU(),
            nn.Conv2d(40, 20, 5,padding='same'),
            nn.ReLU(),
            nn.Conv2d(20, 10, 5,padding='same'),
            nn.ReLU(),
        )

        self.column3 = nn.Sequential(
            nn.Conv2d(3, 12, 5, padding='same'),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(12, 24, 3, padding='same'),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(24, 48, 3, padding='same'),
            nn.ReLU(),
            nn.Conv2d(48, 24, 3, padding='same'),
            nn.ReLU(),
            nn.Conv2d(24, 12, 3, padding='same'),
            nn.ReLU(),
        )
        

        self.fusion_layer = nn.Sequential(
            nn.Conv2d(30, 1, 1, padding=0),
            #nn.ReLU()
        )


    def forward(self,img_tensor):
        x1 = self.column1(img_tensor)
        x2 = self.column2(img_tensor)
        x3 = self.column3(img_tensor)
        x = torch.cat((x1, x2, x3),1)
        x = self.fusion_layer(x)
        return x

# import cv2
# import numpy as np
# import torch


# def compute_flow_mag(prev_frame, curr_frame, resize_to=None):
#     """Compute normalized optical flow magnitude."""
#     prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
#     curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

#     flow = cv2.calcOpticalFlowFarneback(
#         prev_gray, curr_gray, None,
#         pyr_scale=0.5, levels=3, winsize=15,
#         iterations=3, poly_n=5, poly_sigma=1.2, flags=0
#     )

#     mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
#     mag = np.clip(mag, 0, 20)

#     if resize_to is not None:
#         mag = cv2.resize(mag, resize_to)

#     # Normalize
#     if mag.max() > 0:
#         mag = mag / (mag.max() + 1e-8)

#     return mag


# def detect_density_change(count_history, window=5, threshold_factor=2.0):
#     """Stat-based spike detection."""
#     anomaly_intensity = 0.0
#     if len(count_history) < window:
#         return False, anomaly_intensity

#     recent = np.array(count_history[-window:])
#     latest = recent[-1]
#     mean = np.mean(recent[:-1])
#     std = np.std(recent[:-1])

#     if std == 0:
#         return (latest != mean), abs(latest - mean)

#     z = abs(latest - mean) / std
#     if z > threshold_factor:
#         return True, abs(latest - mean)

#     return False, anomaly_intensity
