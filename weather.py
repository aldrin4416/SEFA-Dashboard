"""SEFA – Weather integration via Open-Meteo (no API key needed)."""

import json
from datetime import datetime, timedelta
from urllib.request import urlopen
from urllib.parse import urlencode

from db import get_conn


# Coimbatore, Tamil Nadu, India
DEFAULT_LAT = 11.0168
DEFAULT_LON = 76.9558
DEFAULT_TZ  = "Asia/Kolkata"

CACHE_MINUTES = 30


def _fetch_json(url):
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_current(lat=DEFAULT_LAT, lon=DEFAULT_LON, tz=DEFAULT_TZ):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "wind_speed_10m,precipitation,weather_code"
        ),
        "timezone": tz,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    data = _fetch_json(url)
    c = data.get("current", {})
    return {
        "temperature":   c.get("temperature_2m"),
        "humidity":      c.get("relative_humidity_2m"),
        "wind":          c.get("wind_speed_10m"),
        "precipitation": c.get("precipitation"),
        "weather_code":  c.get("weather_code"),
        "timestamp":     c.get("time"),
    }


def fetch_forecast(lat=DEFAULT_LAT, lon=DEFAULT_LON, tz=DEFAULT_TZ, days=7):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": (
            "temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,precipitation_probability_max,"
            "weather_code"
        ),
        "timezone": tz,
        "forecast_days": days,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    data = _fetch_json(url)
    d = data.get("daily", {})
    dates = d.get("time", [])
    out = []
    for i, date in enumerate(dates):
        out.append({
            "date":          date,
            "temp_max":      d.get("temperature_2m_max", [None]*len(dates))[i],
            "temp_min":      d.get("temperature_2m_min", [None]*len(dates))[i],
            "rain_mm":       d.get("precipitation_sum", [None]*len(dates))[i],
            "rain_prob":     d.get("precipitation_probability_max", [None]*len(dates))[i],
            "weather_code":  d.get("weather_code", [None]*len(dates))[i],
        })
    return out


def _cache_get(key):
    conn = get_conn()
    row = conn.execute("""
        SELECT payload, timestamp FROM weather_cache
        WHERE key = ?
    """, (key,)).fetchone()
    conn.close()
    if not row:
        return None
    age = datetime.now() - datetime.fromisoformat(row["timestamp"])
    if age > timedelta(minutes=CACHE_MINUTES):
        return None
    try:
        return json.loads(row["payload"])
    except Exception:
        return None


def _cache_set(key, payload):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO weather_cache (key, payload, timestamp)
        VALUES (?, ?, ?)
    """, (key, json.dumps(payload),
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def get_current_cached(**kw):
    cached = _cache_get("current")
    if cached:
        return cached
    try:
        data = fetch_current(**kw)
        _cache_set("current", data)
        return data
    except Exception as e:
        return {"error": str(e)}


def get_forecast_cached(**kw):
    cached = _cache_get("forecast")
    if cached:
        return cached
    try:
        data = fetch_forecast(**kw)
        _cache_set("forecast", data)
        return data
    except Exception as e:
        return []


WMO_CODES = {
    0:  ("Clear sky", "☀️"),
    1:  ("Mainly clear", "🌤️"),
    2:  ("Partly cloudy", "⛅"),
    3:  ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "⛈️"),
    71: ("Slight snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + hail", "⛈️"),
    99: ("Thunderstorm + hail", "⛈️"),
}


def describe_weather(code):
    return WMO_CODES.get(code, ("Unknown", "❔"))


def irrigation_advice(forecast, dry_threshold_rain_mm=5.0):
    if not forecast:
        return {
            "today_rain_mm": 0,
            "next_rainy_day": None,
            "skip_irrigation": False,
            "reason": "no forecast data",
        }

    today = forecast[0]
    today_rain = today.get("rain_mm") or 0
    rain_prob  = today.get("rain_prob") or 0

    next_rainy = None
    for i, day in enumerate(forecast[1:], start=1):
        r = day.get("rain_mm") or 0
        p = day.get("rain_prob") or 0
        if r >= dry_threshold_rain_mm or p >= 60:
            next_rainy = {"day": i, "date": day["date"],
                          "rain_mm": r, "rain_prob": p}
            break

    if today_rain >= dry_threshold_rain_mm or rain_prob >= 70:
        return {
            "today_rain_mm": today_rain,
            "next_rainy_day": next_rainy,
            "skip_irrigation": True,
            "reason": f"Rain expected today ({today_rain:.1f}mm, {rain_prob}% chance)",
        }
    if next_rainy and next_rainy["day"] <= 2:
        return {
            "today_rain_mm": today_rain,
            "next_rainy_day": next_rainy,
            "skip_irrigation": True,
            "reason": f"Rain in {next_rainy['day']} day(s) ({next_rainy['rain_mm']:.1f}mm expected)",
        }
    return {
        "today_rain_mm": today_rain,
        "next_rainy_day": next_rainy,
        "skip_irrigation": False,
        "reason": "No significant rain expected",
    }