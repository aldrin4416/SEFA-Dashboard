"""SEFA – Internationalization helpers."""

import re
import streamlit as st

from translations import LANGUAGES, get_text


DEFAULT_LANG = "en"


# =========================================================
# Session + language selector
# =========================================================

def init_language():
    if "lang" not in st.session_state:
        st.session_state["lang"] = DEFAULT_LANG


def current_lang():
    return st.session_state.get("lang", DEFAULT_LANG)


def set_lang(code):
    if code in LANGUAGES:
        st.session_state["lang"] = code


def t(key, **kwargs):
    return get_text(current_lang(), key, **kwargs)


def language_selector():
    codes = list(LANGUAGES.keys())
    labels = list(LANGUAGES.values())
    current = current_lang()
    idx = codes.index(current) if current in codes else 0

    choice = st.selectbox(
        "🌐 " + t("language"),
        options=range(len(codes)),
        format_func=lambda i: labels[i],
        index=idx,
        key="lang_selector",
    )
    picked = codes[choice]
    if picked != current:
        set_lang(picked)
        st.rerun()


# =========================================================
# Data value translators
# =========================================================

_STATUS_MAP = {
    "Normal":             "status_normal",
    "Monitor":            "status_monitor",
    "Attention Required": "status_attention",
    "No Data":            "status_no_data",
}

_PRED_MAP = {
    "Healthy":          "pred_healthy",
    "Possible Disease": "pred_disease",
    "Possible Pest":    "pred_pest",
    "Crop Stress":      "pred_stress",
    "Unknown":          "pred_unknown",
}

_SEV_MAP = {
    "High":   "sev_high",
    "Medium": "sev_medium",
    "Low":    "sev_low",
}

_ALERT_MAP = {
    "Dry Soil":         "alert_dry_soil",
    "Over-watered":     "alert_overwatered",
    "High Temperature": "alert_high_temp",
    "pH Out of Range":  "alert_ph",
    "Low Battery":      "alert_low_battery",
    "Possible Disease": "alert_disease",
    "Possible Pest":    "alert_pest",
    "Crop Stress":      "alert_stress",
}

_REC_REASON_MAP = {
    "dry soil":         "rec_reasons_dry",
    "over-watered":     "rec_reasons_overwatered",
    "heat stress":      "rec_reasons_heat",
    "pH out of range":  "rec_reasons_ph",
    "possible disease": "rec_reasons_disease",
    "possible pest":    "rec_reasons_pest",
    "crop stress":      "rec_reasons_stress",
}

_WEATHER_MAP = {
    "Clear sky":           "weather_condition_clear",
    "Mainly clear":        "weather_condition_mainly_clear",
    "Partly cloudy":       "weather_condition_partly_cloudy",
    "Overcast":            "weather_condition_overcast",
    "Fog":                 "weather_condition_fog",
    "Rime fog":            "weather_condition_fog",
    "Light drizzle":       "weather_condition_drizzle",
    "Drizzle":             "weather_condition_drizzle",
    "Heavy drizzle":       "weather_condition_heavy_rain",
    "Slight rain":         "weather_condition_rain",
    "Rain":                "weather_condition_rain",
    "Heavy rain":          "weather_condition_heavy_rain",
    "Slight snow":         "weather_condition_snow",
    "Snow":                "weather_condition_snow",
    "Heavy snow":          "weather_condition_snow",
    "Rain showers":        "weather_condition_rain",
    "Violent showers":     "weather_condition_heavy_rain",
    "Thunderstorm":        "weather_condition_storm",
    "Thunderstorm + hail": "weather_condition_storm",
    "Unknown":             "weather_condition_unknown",
}


def t_status(value):
    if not isinstance(value, str):
        return value
    key = _STATUS_MAP.get(value)
    return t(key) if key else value


def t_prediction(value):
    if not isinstance(value, str):
        return value
    key = _PRED_MAP.get(value)
    return t(key) if key else value


def t_severity(value):
    if not isinstance(value, str):
        return value
    key = _SEV_MAP.get(value)
    return t(key) if key else value


def t_alert_type(value):
    if not isinstance(value, str):
        return value
    key = _ALERT_MAP.get(value)
    return t(key) if key else value


def t_weather_condition(desc):
    """Translate a weather condition label. Falls back to English."""
    if not isinstance(desc, str):
        return desc
    key = _WEATHER_MAP.get(desc)
    if not key:
        return desc
    translated = t(key)
    return translated if translated != key else desc


def translate_recommendation(text):
    if not isinstance(text, str):
        return text
    if text == "No action needed":
        return t("rec_no_action")
    if text == "Check sensor node":
        return t("rec_check_sensor")

    def _translate_reasons(prefix, tmpl_key):
        reasons = text[len(prefix):].strip()
        parts = [
            t(_REC_REASON_MAP[r.strip()]) if r.strip() in _REC_REASON_MAP
            else r.strip()
            for r in reasons.split(",")
        ]
        return t(tmpl_key, reasons=", ".join(parts))

    if text.startswith("Inspect now:"):
        return _translate_reasons("Inspect now:", "rec_inspect_prefix")
    if text.startswith("Watch zone:"):
        return _translate_reasons("Watch zone:", "rec_watch_prefix")
    return text


_MSG_PATTERNS = [
    (re.compile(r"Moisture ([\d.]+)% — irrigation recommended\."),
     lambda m: t("msg_dry_soil", moisture=m.group(1))),
    (re.compile(r"Moisture ([\d.]+)% — reduce irrigation\."),
     lambda m: t("msg_overwatered", moisture=m.group(1))),
    (re.compile(r"Temp ([\d.]+)°C — heat stress risk\."),
     lambda m: t("msg_high_temp", temp=m.group(1))),
    (re.compile(r"pH ([\d.]+) outside ([\d.]+)–([\d.]+)\."),
     lambda m: t("msg_ph", ph=m.group(1),
                 ph_min=m.group(2), ph_max=m.group(3))),
    (re.compile(r"Sensor battery ([\d.]+)%\."),
     lambda m: t("msg_low_battery", battery=m.group(1))),
    (re.compile(r"(Possible Disease|Possible Pest) detected \(([\d.]+)% confidence\)\."),
     lambda m: t("msg_disease",
                 pred=t_prediction(m.group(1)),
                 conf=m.group(2))),
    (re.compile(r"Crop stress detected \(([\d.]+)% confidence\)\."),
     lambda m: t("msg_stress", conf=m.group(1))),
]


def translate_message(text):
    if not isinstance(text, str):
        return text
    for pattern, builder in _MSG_PATTERNS:
        m = pattern.match(text)
        if m:
            return builder(m)
    return text


def translate_df(df, columns):
    for col in columns:
        if col not in df.columns:
            continue
        if col == "status":
            df[col] = df[col].map(t_status)
        elif col in ("prediction", "AI Status", "AI Prediction"):
            df[col] = df[col].map(t_prediction)
        elif col == "severity":
            df[col] = df[col].map(t_severity)
        elif col == "alert_type":
            df[col] = df[col].map(t_alert_type)
        elif col == "recommendation":
            df[col] = df[col].map(translate_recommendation)
        elif col == "message":
            df[col] = df[col].map(translate_message)
    return df