"""SEFA – SQLite database layer."""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "sefa.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id     TEXT    NOT NULL,
            zone        TEXT    NOT NULL,
            moisture    REAL,
            temperature REAL,
            ph          REAL,
            ec          REAL,
            battery     REAL,
            timestamp   TEXT    NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            zone       TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity   TEXT NOT NULL,
            message    TEXT,
            timestamp  TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_results (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            zone       TEXT NOT NULL,
            image_id   TEXT,
            prediction TEXT NOT NULL,
            confidence REAL,
            timestamp  TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS irrigation_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            zone       TEXT NOT NULL,
            action     TEXT NOT NULL,
            duration_s INTEGER,
            note       TEXT,
            timestamp  TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS weather_cache (
            key       TEXT PRIMARY KEY,
            payload   TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_data(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ai_ts     ON ai_results(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_irrig_ts  ON irrigation_log(timestamp)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS camera_captures (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            zone        TEXT NOT NULL,
            image_b64   TEXT,
            prediction  TEXT NOT NULL,
            confidence  REAL,
            note        TEXT,
            timestamp   TEXT NOT NULL
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_cam_ts ON camera_captures(timestamp)")
    conn.commit()
    conn.close()


# ---------- Writers ----------

def insert_sensor(node_id, zone, moisture, temperature, ph, ec, battery):
    conn = get_conn()
    conn.execute("""
        INSERT INTO sensor_data
            (node_id, zone, moisture, temperature, ph, ec, battery, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (node_id, zone, moisture, temperature, ph, ec, battery,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def insert_alert(zone, alert_type, severity, message):
    conn = get_conn()
    conn.execute("""
        INSERT INTO alerts (zone, alert_type, severity, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (zone, alert_type, severity, message,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def insert_ai(zone, image_id, prediction, confidence):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ai_results (zone, image_id, prediction, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (zone, image_id, prediction, confidence,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def log_irrigation(zone, action, duration_s=None, note=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO irrigation_log (zone, action, duration_s, note, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (zone, action, duration_s, note,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


# ---------- Readers ----------

def latest_per_zone():
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*
        FROM sensor_data s
        JOIN (
            SELECT zone, MAX(timestamp) AS ts
            FROM sensor_data GROUP BY zone
        ) m ON s.zone = m.zone AND s.timestamp = m.ts
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def latest_ai_per_zone():
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*
        FROM ai_results a
        JOIN (
            SELECT zone, MAX(timestamp) AS ts
            FROM ai_results GROUP BY zone
        ) m ON a.zone = m.zone AND a.timestamp = m.ts
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def recent_alerts(limit=25):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM alerts
        ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def history_for_zone(zone, limit=200):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM sensor_data
        WHERE zone = ?
        ORDER BY timestamp DESC LIMIT ?
    """, (zone, limit)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def all_history(limit=500):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM sensor_data
        ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def alert_counts():
    conn = get_conn()
    rows = conn.execute("""
        SELECT alert_type, COUNT(*) as n
        FROM alerts GROUP BY alert_type
    """).fetchall()
    conn.close()
    return {r["alert_type"]: r["n"] for r in rows}


def irrigation_history(zone=None, limit=50):
    conn = get_conn()
    if zone:
        rows = conn.execute("""
            SELECT * FROM irrigation_log
            WHERE zone = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (zone, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM irrigation_log
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def irrigation_events_per_zone():
    conn = get_conn()
    rows = conn.execute("""
        SELECT zone, COUNT(*) AS n
        FROM irrigation_log
        WHERE action = 'started'
        GROUP BY zone
    """).fetchall()
    conn.close()
    return {r["zone"]: r["n"] for r in rows}


def insert_camera_capture(zone, image_b64, prediction, confidence, note=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO camera_captures
            (zone, image_b64, prediction, confidence, note, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (zone, image_b64, prediction, confidence, note,
          datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def recent_camera_captures(limit=20, zone=None):
    conn = get_conn()
    if zone:
        rows = conn.execute("""
            SELECT id, zone, prediction, confidence, note, timestamp
            FROM camera_captures
            WHERE zone = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (zone, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, zone, prediction, confidence, note, timestamp
            FROM camera_captures
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_capture_image(capture_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT image_b64 FROM camera_captures WHERE id = ?
    """, (capture_id,)).fetchone()
    conn.close()
    return row["image_b64"] if row else None