"""SEFA – Central configuration."""

from db import get_conn


# Default name (used if not set in DB)
DEFAULT_FARMER_NAME = "Karthik"


def get_farmer_name():
    """Read farmer name from settings table; fall back to default."""
    try:
        conn = get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'farmer_name'"
        ).fetchone()
        conn.commit()
        conn.close()
        if row and row["value"]:
            return row["value"]
    except Exception:
        pass
    return DEFAULT_FARMER_NAME


def set_farmer_name(name):
    """Persist farmer name to settings table."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute("""
        INSERT OR REPLACE INTO settings (key, value) VALUES ('farmer_name', ?)
    """, (str(name).strip(),))
    conn.commit()
    conn.close()


# Tab definitions
TABS = [
    ("home",     "Home",     ""),
    ("field",    "Field",    ""),
    ("camera",   "Camera",   ""),
    ("insights", "Insights", ""),
]

# Extra pages (More menu)
MORE_PAGES = [
    ("alerts",     "Alerts",     "🚨"),
    ("ai",         "AI Monitor", "🤖"),
    ("irrigation", "Irrigation", "💧"),
    ("trends",     "Trends",     "📈"),
    ("weather",    "Weather",    "🌦️"),
    ("analytics",  "Analytics",  "🌱"),
    ("settings",   "Settings",   "⚙️"),
]

# Convenience alias for existing code
FARMER_NAME = DEFAULT_FARMER_NAME