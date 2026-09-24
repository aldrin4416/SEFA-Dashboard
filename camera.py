"""SEFA – Camera capture and simulated AI analysis."""

import base64
import random
from datetime import datetime

from db import insert_camera_capture, insert_ai

# Simulated AI classes (matches simulator.AI_CLASSES)
AI_CLASSES = [
    "Healthy",
    "Possible Disease",
    "Possible Pest",
    "Crop Stress",
    "Unknown",
]


def simulate_ai(image_bytes=None, zone="A1"):
    """Simulated AI prediction. Replace with a real model later.

    The result is weighted toward Healthy but biased by zone:
    'sick' zones (B3, C2) are more likely to return problems.
    """
    sick_zones = {"B3", "C2", "B4", "C3"}
    if zone in sick_zones:
        pred = random.choices(
            ["Possible Disease", "Possible Pest", "Crop Stress", "Healthy"],
            weights=[45, 25, 15, 15],
        )[0]
        conf = round(random.uniform(72, 96), 1)
    else:
        pred = random.choices(AI_CLASSES, weights=[78, 6, 5, 8, 3])[0]
        conf = round(random.uniform(55, 92), 1)
    return pred, conf


def encode_image(image_file):
    """Convert an uploaded file (Streamlit) to base64 string."""
    if image_file is None:
        return None
    try:
        image_file.seek(0)
        raw = image_file.read()
        return base64.b64encode(raw).decode("utf-8")
    except Exception:
        return None


def decode_image(b64_string):
    """Return raw bytes from a base64 string."""
    if not b64_string:
        return None
    try:
        return base64.b64decode(b64_string)
    except Exception:
        return None


def save_capture(zone, image_b64, prediction, confidence, note=""):
    """Persist a capture + AI result, and also feed it into ai_results."""
    insert_camera_capture(zone, image_b64, prediction, confidence, note)
    # Also log to ai_results so the AI Monitoring page sees it
    image_id = f"CAM-{zone}-{datetime.now().strftime('%H%M%S')}"
    insert_ai(zone, image_id, prediction, confidence)