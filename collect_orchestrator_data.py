"""
collect_from_multiple_videos_with_emotion_ratio.py

- Processes all videos in VIDEO_DIR (e.g. 10 videos)
- Sends frames to your 4 services (crowd, env, emo, body)
- Applies orchestrator logic (updated emotion rule: ratio threshold = 0.5)
- NULL-safe: handles missing/invalid responses
- Writes one CSV: orchestrator_dataset.csv
"""

import cv2
import requests
import csv
import json
import glob
import os
from datetime import datetime
from collections import Counter

# ============== CONFIG ==============
VIDEO_DIR = "videos/"               # put your 10 videos here
FRAME_SKIP = 5                      # use every Nth frame
MAX_FRAMES_PER_VIDEO = 300
OUTPUT_CSV = "orchestrator_dataset.csv"
TIMEOUT = 6                         # per-request timeout (seconds)

CROWD_URL = "http://127.0.0.1:8100/analyze/"
ENV_URL   = "http://127.0.0.1:8200/analyze/"
EMO_URL   = "http://127.0.0.1:8300/analyze/"
BODY_URL  = "http://127.0.0.1:8400/analyze/"

# Emotion aggregation threshold (you chose 0.5)
POSITIVE_RATIO_THRESHOLD = 0.5

# Lists used in orchestrator
POSITIVE_EMOTIONS = {"happy", "joy", "smile", "surprise", "neutral"}
NEGATIVE_EMOTIONS = {"fear", "anger", "sad", "disgust"}

# -------------------------------------

def safe_post(url, frame_bytes):
    """Post a frame and return JSON dict or None on failure."""
    try:
        r = requests.post(url, files={"file": ("frame.jpg", frame_bytes, "image/jpeg")}, timeout=TIMEOUT)
        try:
            return r.json()
        except Exception:
            return None
    except Exception:
        return None

def safe_json_load(x):
    """Return dict for valid JSON-like input, else {}."""
    if x is None: return {}
    if isinstance(x, dict): return x
    try:
        return json.loads(x)
    except:
        return {}

def compute_emotion_ratio_from_distribution(emo_resp):
    """
    emo_resp expected format per emo_analyzer:
    {
      "frames_analyzed": 1,
      "total_faces_detected": N,
      "emotion_distribution": {"happy": 22.4, "neutral": 33.1, ...},
      "dominant_emotion": "neutral"
    }
    Returns (positive_pct, negative_pct)
    """
    emo = safe_json_load(emo_resp)
    dist = emo.get("emotion_distribution") or {}
    # distribution uses percentages already (sum may be <=100 due to filtering)
    pos = sum(float(dist.get(e, 0) or 0) for e in POSITIVE_EMOTIONS)
    neg = sum(float(dist.get(e, 0) or 0) for e in NEGATIVE_EMOTIONS)
    return pos, neg, dist, emo.get("dominant_emotion")

def compute_label_and_reasons(crowd, env, emo, posture, crowd_history):
    """
    Implements orchestrator detect_anomalies with changes:
    - Positive override only when positive_ratio >= POSITIVE_RATIO_THRESHOLD
    - Adds posture, body-language, mixed-individuals, and environment cleanliness checks
    Returns: dict with alert (bool), reason (str), anomalies (list), wellness_score (float)
    """
    # Normalize inputs
    crowd = safe_json_load(crowd)
    env = safe_json_load(env)
    emo = safe_json_load(emo)
    posture = safe_json_load(posture)

    total_people = float(crowd.get("overall_crowd_count", 0) or 0)

    # crowd motion/density
    motion_info = (crowd.get("motion_anomaly") or {}) 
    motion = bool(motion_info.get("is_running", False))
    motion_score = float(motion_info.get("anomaly_score", 0) or motion_info.get("avg_motion", 0) or 0)
    density_shift = float((crowd.get("density_shift_anomaly") or {}).get("score", 0) or 0)
    crowd_state = str(crowd.get("dominant_state", "calm")).lower()

    # posture summary from posture_resp format (we constructed posture={"frame_results":[...]})
    posture_list = posture.get("frame_results", []) or []
    bent = sum(1 for p in posture_list if (p.get("posture") or "").lower() in ("crouching",))
    aggressive = sum(1 for p in posture_list if (p.get("body_language") or "").lower() == "aggressive")
    gesturing = sum(1 for p in posture_list if (p.get("body_language") or "").lower() == "gesturing")

    posture_anomaly = (bent >= 3 and total_people > 5)
    bodylang_anomaly = (aggressive >= 2 or gesturing >= 4)

    # Mixed individuals rule: if many people and >15% differ from majority posture/body label
    mixed_individuals = False
    try:
        indiv = posture.get("frame_results", []) or []
        total_indiv = len(indiv)
        if total_indiv > 0:
            body_counts = Counter([(p.get("body_language") or "unknown").lower() for p in indiv])
            posture_counts = Counter([(p.get("posture") or "unknown").lower() for p in indiv])
            majority_body = body_counts.most_common(1)[0][1] if body_counts else total_indiv
            mismatch_body = total_indiv - majority_body
            if total_indiv > 0 and (mismatch_body / float(total_indiv)) >= 0.15:
                mixed_individuals = True
    except Exception:
        mixed_individuals = False

    # environment cleanliness
    cleanliness = (env or {}).get("cleanliness", "").lower() if env else ""
    env_dirty = cleanliness == "messy"

    # crowd recent surge detection
    recent_counts = [c.get("overall_crowd_count", 0) for c in (crowd_history or []) if isinstance(c, dict)]
    significant_increase = False
    if len(recent_counts) >= 3:
        try:
            import numpy as _np
            if recent_counts[-1] > _np.mean(recent_counts[-3:]) * 1.3:
                significant_increase = True
        except Exception:
            significant_increase = False

    # emotion aggregation using distribution (percentage)
    pos_pct, neg_pct, dist, dominant = compute_emotion_ratio_from_distribution(emo)
    # If no emotion data, treat as unknown (so cannot suppress alert)
    positive_ratio = 0.0
    if (pos_pct + neg_pct) > 0:
        positive_ratio = pos_pct / (pos_pct + neg_pct)
    else:
        positive_ratio = 0.0

    # Decide positive_override: only suppress alerts if positive_ratio >= threshold
    positive_override = positive_ratio >= POSITIVE_RATIO_THRESHOLD

    # Compose logic similar to original but with new positive_override
    should_alert = False
    reason_parts = []
    anomalies = []

    # Crowd panic conditions (only if NOT positive_override)
    if not positive_override and (
        motion
        or motion_score > 1.2
        or density_shift > 0.15
        or crowd_state in ("high_density", "overcrowded", "extreme")
        or significant_increase
    ):
        should_alert = True
        reason_parts.append("Crowd panic detected.")
        anomalies.append("Crowd anomaly: unusual motion or density surge detected.")

    if posture_anomaly:
        should_alert = True
        reason_parts.append(f"⚠️ Posture anomaly: {bent} crouching.")
        anomalies.append(f"{bent} people show crouching posture (possible stress).")

    if bodylang_anomaly:
        should_alert = True
        reason_parts.append(f"⚠️ Body-language anomaly: {aggressive + gesturing} aggressive/gesturing.")
        anomalies.append(f"{aggressive + gesturing} people show aggressive/gesturing behaviour.")

    if mixed_individuals:
        should_alert = True
        reason_parts.append("Mixed individual behaviour detected.")
        anomalies.append("Population shows heterogeneous posture/body-language (possible isolated incidents).")

    if env_dirty:
        should_alert = True
        reason_parts.append("Environment cleanliness issue detected.")
        anomalies.append("Environment flagged messy.")

    # If positive_override is true -> suppress alerts and clear anomalies (but still keep env_dirty? user asked positive suppresses all; we'll follow your previous instruction: positive allows no alert only if positive overtakes negative)
    if positive_override:
        # preserve environment cleanliness as separate anomaly? You wanted "no alert only when positive emotions overtake negative emotions", not necessarily to ignore other anomalies.
        # Interpretation chosen: positive_override suppresses alerts caused by crowd panic/motion/density and body/posture anomalies too.
        # But we will still include environment cleanliness as an anomaly (since it's about environment, not emotions).
        if env_dirty:
            # keep environment anomaly but don't set should_alert if only env_dirty exists? You asked "otherwise there must be alert" — we'll treat env_dirty as cause for alert even if positive_ratio >= threshold.
            # To follow your instruction strictly: "there is an alert only if the aggregate of positive emotions overtake the aggregate of negative emotions over a certain threshold. otherwise there must be alert" -> that applies mainly to suppression (positive cancels). But cleanliness is independent — enforce cleanliness causes alert regardless.
            should_alert = True
            # reason parts keep the cleanliness reason already added above
        else:
            # suppress non-environment reasons and clear them
            suppressed = [r for r in reason_parts if "Environment" not in r and "cleanliness" not in r]
            # If only environment remains, should_alert handled as above
            # For clarity, if positive override true and env_dirty false -> no alert
            if not env_dirty:
                should_alert = False
                reason_parts = ["No alert — positive emotions dominate (ratio {:.2f}).".format(positive_ratio)]
                anomalies = []

    # If no reason parts -> steady state
    if not reason_parts:
        reason_parts = ["steady state"] if not positive_override else [f"No alert — positive emotions dominate (ratio {positive_ratio:.2f})."]

    # wellness score: keep original formula but use posture/bodylang/env contributions
    stress_factor = (density_shift + motion_score) / 4.0
    posture_factor = 0.25 if posture_anomaly else 0
    bodylang_factor = 0.25 if bodylang_anomaly else 0
    env_factor = 0.2 if env_dirty else 0
    wellness_score = 1.0 if positive_override else max(0.0, 1.0 - stress_factor - posture_factor - bodylang_factor - env_factor)
    wellness_score = round(float(wellness_score), 2)

    env_summary = "Weather: {}, Lighting: {}, Cleanliness: {}".format(
        env.get("weather", "unknown"), env.get("lighting", "unknown"), env.get("cleanliness", "unknown")
    )

    return {
        "alert": bool(should_alert),
        "reason": " ".join(reason_parts),
        "anomalies": anomalies,
        "wellness_score": wellness_score,
        "positive_ratio": round(positive_ratio, 3),
        "emotion_distribution": dist,
        "environment_summary": env_summary
    }

# ===== MAIN LOOP =====
videos = sorted(glob.glob(os.path.join(VIDEO_DIR, "*.*")))
if not videos:
    print("No videos found in", VIDEO_DIR)
    raise SystemExit(1)

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    header = [
        "timestamp", "video_name", "frame_index",
        "crowd_json", "environment_json", "emotion_json", "posture_json",
        "alert", "reason", "anomalies", "wellness_score",
        "positive_ratio", "emotion_distribution", "environment_summary"
    ]
    writer.writerow(header)

    for vid_path in videos:
        print("Processing", vid_path)
        cap = cv2.VideoCapture(vid_path)
        if not cap.isOpened():
            print("Cannot open", vid_path)
            continue

        frame_no = 0
        collected = 0
        crowd_history = []

        while collected < MAX_FRAMES_PER_VIDEO:
            ret, frame = cap.read()
            if not ret:
                break
            frame_no += 1
            if frame_no % FRAME_SKIP != 0:
                continue

            _, jpg = cv2.imencode(".jpg", frame)
            frame_bytes = jpg.tobytes()

            # query services (NULL-safe)
            crowd = safe_post(CROWD_URL, frame_bytes)
            env = safe_post(ENV_URL, frame_bytes)
            emo = safe_post(EMO_URL, frame_bytes)
            post_raw = safe_post(BODY_URL, frame_bytes)

            # normalize posture to { "frame_results": [ {posture, body_language}, ... ] }
            posture_frame_results = []
            post_raw_safe = safe_json_load(post_raw)
            if isinstance(post_raw_safe, dict) and "individual" in post_raw_safe:
                for ind in post_raw_safe.get("individual", []):
                    posture_frame_results.append({
                        "posture": ind.get("posture"),
                        "body_language": ind.get("body_language")
                    })

            posture = {"frame_results": posture_frame_results}

            # update crowd_history for recent surge detection
            crowd_safe = safe_json_load(crowd)
            # ensure overall_crowd_count present, fallback to sum of zones/aggregated
            if isinstance(crowd_safe, dict):
                if "overall_crowd_count" not in crowd_safe or (isinstance(crowd_safe.get("overall_crowd_count"), (int, float)) and crowd_safe.get("overall_crowd_count") == 0 and crowd_safe.get("zones")):
                    try:
                        total = 0.0
                        for el in (crowd_safe.get("aggregated_outputs") or []):
                            agg = el.get("aggregate", {})
                            for z in agg.values():
                                total += float(z.get("avg_people", 0))
                        if total == 0.0 and crowd_safe.get("zones"):
                            for z in crowd_safe.get("zones", []):
                                total += float(z.get("count", 0))
                        crowd_safe["overall_crowd_count"] = float(total)
                    except Exception:
                        crowd_safe["overall_crowd_count"] = 0.0
            crowd_history.append(crowd_safe)
            if len(crowd_history) > 8:
                crowd_history.pop(0)

            # compute label & metadata
            anomaly = compute_label_and_reasons(crowd_safe, env, emo, posture, crowd_history)

            writer.writerow([
                datetime.utcnow().isoformat(),
                os.path.basename(vid_path),
                frame_no,
                json.dumps(crowd_safe) if crowd_safe else "NULL",
                json.dumps(safe_json_load(env)) if env else "NULL",
                json.dumps(safe_json_load(emo)) if emo else "NULL",
                json.dumps(posture) if posture else "NULL",
                anomaly["alert"],
                anomaly["reason"],
                json.dumps(anomaly["anomalies"]),
                anomaly["wellness_score"],
                anomaly["positive_ratio"],
                json.dumps(anomaly["emotion_distribution"]),
                anomaly["environment_summary"]
            ])

            collected += 1
            print("  collected", collected, "frames from", os.path.basename(vid_path))

        cap.release()

print("Done. CSV saved to:", OUTPUT_CSV)
