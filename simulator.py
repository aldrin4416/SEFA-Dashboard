"""SEFA – Simulated sensor + AI data generator."""

import random
from datetime import datetime

from db import insert_sensor, insert_ai, insert_alert

ROWS = ["A", "B", "C", "D"]
COLS = [1, 2, 3, 4]
ZONES = [f"{r}{c}" for r in ROWS for c in COLS]

NODES = {f"SEFA-NODE-{i+1:03d}": z for i, z in enumerate(ZONES)}

DRY_ZONES  = {"B2", "B3", "C2", "C3"}
WET_ZONES  = {"A1", "A4", "D1", "D4"}
HOT_ZONES  = {"C3", "D3", "D4"}
SICK_ZONES = {"B3", "C2"}

THRESHOLDS = {
    "moisture_dry": 30,
    "moisture_wet": 70,
    "temp_high":    35,
    "temp_low":     10,
    "ph_min":       5.5,
    "ph_max":       7.5,
    "battery_low":  20,
}

AI_CLASSES = [
    "Healthy",
    "Possible Disease",
    "Possible Pest",
    "Crop Stress",
    "Unknown",
]


def _reading(zone):
    if zone in DRY_ZONES:
        moisture = random.uniform(14, 30)
    elif zone in WET_ZONES:
        moisture = random.uniform(62, 80)
    else:
        moisture = random.uniform(35, 60)

    if zone in HOT_ZONES:
        temperature = random.uniform(33, 39)
    else:
        temperature = random.uniform(24, 34)

    return {
        "moisture":    round(moisture, 1),
        "temperature": round(temperature, 1),
        "ph":          round(random.uniform(5.9, 7.3), 2),
        "ec":          round(random.uniform(0.4, 2.1), 2),
        "battery":     round(random.uniform(40, 100), 1),
    }


def _ai_result(zone):
    if zone in SICK_ZONES:
        pred = random.choices(
            ["Possible Disease", "Possible Pest", "Crop Stress", "Healthy"],
            weights=[45, 25, 15, 15],
        )[0]
        conf = round(random.uniform(72, 95), 1)
    else:
        pred = random.choices(AI_CLASSES, weights=[78, 6, 5, 8, 3])[0]
        conf = round(random.uniform(55, 92), 1)
    image_id = f"IMG-{zone}-{datetime.now().strftime('%H%M%S')}"
    return pred, conf, image_id


def _emit_alerts(zone, r, ai_pred, ai_conf):
    if r["moisture"] < THRESHOLDS["moisture_dry"]:
        insert_alert(zone, "Dry Soil", "High",
                     f"Moisture {r['moisture']}% — irrigation recommended.")
    if r["moisture"] > THRESHOLDS["moisture_wet"]:
        insert_alert(zone, "Over-watered", "Medium",
                     f"Moisture {r['moisture']}% — reduce irrigation.")
    if r["temperature"] > THRESHOLDS["temp_high"]:
        insert_alert(zone, "High Temperature", "Medium",
                     f"Temp {r['temperature']}°C — heat stress risk.")
    if r["ph"] < THRESHOLDS["ph_min"] or r["ph"] > THRESHOLDS["ph_max"]:
        insert_alert(zone, "pH Out of Range", "Low",
                     f"pH {r['ph']} outside {THRESHOLDS['ph_min']}–{THRESHOLDS['ph_max']}.")
    if r["battery"] < THRESHOLDS["battery_low"]:
        insert_alert(zone, "Low Battery", "Low",
                     f"Sensor battery {r['battery']}%.")
    if ai_pred in ("Possible Disease", "Possible Pest") and ai_conf >= 75:
        insert_alert(zone, ai_pred, "High",
                     f"{ai_pred} detected ({ai_conf}% confidence).")
    if ai_pred == "Crop Stress" and ai_conf >= 70:
        insert_alert(zone, "Crop Stress", "Medium",
                     f"Crop stress detected ({ai_conf}% confidence).")


def simulate_cycle():
    for zone in ZONES:
        node = next(n for n, z in NODES.items() if z == zone)
        r = _reading(zone)
        insert_sensor(node, zone, r["moisture"], r["temperature"],
                      r["ph"], r["ec"], r["battery"])
        pred, conf, img = _ai_result(zone)
        insert_ai(zone, img, pred, conf)
        _emit_alerts(zone, r, pred, conf)
    return len(ZONES)