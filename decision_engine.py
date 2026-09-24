"""SEFA – Rule-based decision engine."""

from simulator import THRESHOLDS


def evaluate_zone(sensor, ai):
    if sensor is None:
        return "No Data", "Check sensor node", "Low", 0

    score = 0
    reasons = []

    m = sensor.get("moisture")
    t = sensor.get("temperature")
    ph = sensor.get("ph")
    ai_pred = (ai or {}).get("prediction", "Healthy")
    ai_conf = (ai or {}).get("confidence", 0) or 0

    if m is not None and m < THRESHOLDS["moisture_dry"]:
        score += 2
        reasons.append("dry soil")
    if m is not None and m > THRESHOLDS["moisture_wet"]:
        score += 1
        reasons.append("over-watered")
    if t is not None and t > THRESHOLDS["temp_high"]:
        score += 2
        reasons.append("heat stress")
    if ph is not None and (ph < THRESHOLDS["ph_min"] or ph > THRESHOLDS["ph_max"]):
        score += 1
        reasons.append("pH out of range")
    if ai_pred in ("Possible Disease", "Possible Pest") and ai_conf >= 75:
        score += 3
        reasons.append(ai_pred.lower())
    if ai_pred == "Crop Stress" and ai_conf >= 70:
        score += 2
        reasons.append("crop stress")

    if score >= 4:
        return ("Attention Required",
                "Inspect now: " + ", ".join(reasons),
                "High", score)
    if score >= 2:
        return ("Monitor",
                "Watch zone: " + ", ".join(reasons),
                "Medium", score)
    return "Normal", "No action needed", "Low", score


def field_summary(zones_evaluated):
    normal = sum(1 for z in zones_evaluated if z["status"] == "Normal")
    monitor = sum(1 for z in zones_evaluated if z["status"] == "Monitor")
    attention = sum(1 for z in zones_evaluated
                    if z["status"] == "Attention Required")
    moistures = [z["moisture"] for z in zones_evaluated
                 if z.get("moisture") is not None]
    avg = round(sum(moistures) / len(moistures), 1) if moistures else 0
    return normal, monitor, attention, avg