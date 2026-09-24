"""SEFA – Smart Edge AI Farming Dashboard.

Mobile-first · PWA installable · farmer-simple mode · 10 languages · edge AI.
Query-param navigation that stays stable across reruns.
"""

import base64
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

import icons
from db import (
    init_db, latest_per_zone, latest_ai_per_zone,
    recent_alerts, history_for_zone, all_history, alert_counts,
    log_irrigation, irrigation_history,
    insert_camera_capture, recent_camera_captures, get_capture_image,
)
from simulator import simulate_cycle, ZONES, ROWS, COLS, THRESHOLDS
from decision_engine import evaluate_zone, field_summary
from camera import simulate_ai, encode_image, decode_image, save_capture
from i18n import (
    init_language, t, language_selector,
    t_status, t_prediction, t_severity, t_alert_type,
    translate_recommendation, translate_message,
    t_weather_condition,
)
from weather import (
    get_current_cached, get_forecast_cached,
    describe_weather, irrigation_advice,
    DEFAULT_LAT, DEFAULT_LON,
)

# =========================================================
# Mobile breakpoint
# =========================================================
MOBILE_BREAKPOINT = 768

# =========================================================
# Read URL query params FIRST (before any widget)
# =========================================================
_page_param = st.query_params.get("page")
_is_mobile_url = st.query_params.get("m") == "1"

# =========================================================
# Session state defaults
# =========================================================
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"
if "camera_url" not in st.session_state:
    st.session_state["camera_url"] = "http://192.168.1.150"

st.session_state["_is_mobile"] = _is_mobile_url

# If a page is requested via URL, force simple_mode off
if _page_param:
    st.session_state["simple_mode"] = False
else:
    if "simple_mode" not in st.session_state:
        st.session_state["simple_mode"] = True

_dark = st.session_state["theme"] == "dark"

# =========================================================
# Page setup
# =========================================================
st.set_page_config(
    page_title="SEFA",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed" if _is_mobile_url else "expanded",
)

try:
    st._config.set_option("theme.base", "dark" if _dark else "light")
    st._config.set_option(
        "theme.backgroundColor", "#0a0f0a" if _dark else "#ffffff"
    )
    st._config.set_option(
        "theme.secondaryBackgroundColor", "#0f1a0f" if _dark else "#f7f9f7"
    )
    st._config.set_option(
        "theme.textColor", "#d4f5d4" if _dark else "#0d3b1e"
    )
    st._config.set_option(
        "theme.primaryColor", "#00e676" if _dark else "#00a651"
    )
except Exception:
    pass

init_db()
init_language()

# ---------------------------------------------------------
# Initialize the sidebar radio state from URL param
# ---------------------------------------------------------
_page_map_from_url = {
    "live":       t("page_live"),
    "map":        t("page_map"),
    "camera":     t("page_camera"),
    "weather":    t("page_weather"),
    "irrigation": t("page_irrigation"),
    "alerts":     t("page_alerts"),
    "ai":         t("page_ai"),
    "trends":     t("page_trends"),
    "analytics":  t("page_analytics"),
}

if "view_widget" not in st.session_state:
    # Prefer the URL param, else default to Live
    if _page_param and _page_param in _page_map_from_url:
        st.session_state["view_widget"] = _page_map_from_url[_page_param]
    else:
        st.session_state["view_widget"] = t("page_live")

# Sync simple_toggle widget state with simple_mode flag
if "simple_toggle" not in st.session_state:
    st.session_state["simple_toggle"] = st.session_state["simple_mode"]

# If URL has a page param, force both simple_mode and simple_toggle off
if _page_param:
    st.session_state["simple_mode"] = False
    st.session_state["simple_toggle"] = False

# ---------------------------------------------------------
# Simple-mode button navigation
# ---------------------------------------------------------
if st.session_state.get("page_override"):
    _target = st.session_state["page_override"]
    st.session_state["page_override"] = None
    st.session_state["simple_mode"] = False
    st.session_state["simple_toggle"] = False
    _map = {
        "camera":     t("page_camera"),
        "irrigation": t("page_irrigation"),
        "weather":    t("page_weather"),
        "live":       t("page_live"),
        "map":        t("page_map"),
    }
    if _target in _map:
        st.session_state["view_widget"] = _map[_target]
        # Also set the URL so if the page reloads, we land on the right page
        try:
            st.query_params["page"] = _target
        except Exception:
            pass

# =========================================================
# Plotly theme
# =========================================================
pio.templates["sefa_base"] = pio.templates["plotly_white"]
pio.templates["sefa_base"].layout.paper_bgcolor = "rgba(0,0,0,0)"
pio.templates["sefa_base"].layout.plot_bgcolor  = "rgba(0,0,0,0)"
pio.templates["sefa_base"].layout.font.family   = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
pio.templates["sefa_base"].layout.font.size     = 11
pio.templates["sefa_base"].layout.colorway = [
    "#00a651", "#008a43", "#7bd39c", "#b8e6c8",
    "#ff9800", "#ffb74d", "#dc3545", "#4caf50",
]
pio.templates.default = "sefa_base"


# =========================================================
# Helper functions
# =========================================================
def apply_theme():
    theme = st.session_state.get("theme", "light")
    cls = "sefa-dark" if theme == "dark" else "sefa-light"
    components.html(f"""
    <script>
    (function() {{
        const p = window.parent;
        if (!p || !p.document || !p.document.body) return;
        p.document.body.classList.remove('sefa-dark', 'sefa-light');
        p.document.body.classList.add('{cls}');
    }})();
    </script>
    """, height=0, width=0)


def detect_mobile():
    """Sync ?m=1 param with viewport width. Bails out if ?page= is present."""
    components.html(f"""
    <script>
    (function() {{
        const P = window.parent;
        if (!P || !P.document) return;
        const BREAKPOINT = {MOBILE_BREAKPOINT};

        function sync() {{
            const url = new URL(P.location.href);

            // If ?page= is present, don't touch the URL — let Python handle it
            if (url.searchParams.get('page')) {{
                return;
            }}

            const isMobile = P.innerWidth <= BREAKPOINT;
            const has = url.searchParams.get('m');

            if (isMobile && has !== '1') {{
                url.searchParams.set('m', '1');
                P.history.replaceState({{}}, '', url);
                P.location.reload();
            }} else if (!isMobile && has === '1') {{
                url.searchParams.delete('m');
                P.history.replaceState({{}}, '', url);
                P.location.reload();
            }}
        }}
        sync();
        P.addEventListener('resize', () => setTimeout(sync, 500));
    }})();
    </script>
    """, height=0, width=0)


def fix_sidebar_toggle():
    components.html(f"""
    <script>
    (function() {{
        const P = window.parent;
        if (!P || !P.document) return;
        const doc = P.document;
        const BREAKPOINT = {MOBILE_BREAKPOINT};

        const SVG_LEFT = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>';
        const SVG_RIGHT = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';

        function styleAndFloat(btn, isExpand) {{
            if (!btn) return;
            const props = {{
                visibility: 'visible',
                display: 'inline-flex',
                opacity: '1',
                'pointer-events': 'auto',
                position: 'fixed',
                top: '16px',
                left: '16px',
                background: '#00a651',
                color: '#ffffff',
                border: '2px solid #ffffff',
                'border-radius': '10px',
                'box-shadow': '0 3px 12px rgba(0,0,0,0.3)',
                cursor: 'pointer',
                'align-items': 'center',
                'justify-content': 'center',
                width: '40px',
                height: '40px',
                'min-width': '40px',
                'min-height': '40px',
                padding: '0',
                margin: '0',
                'font-size': '0',
                'z-index': '2147483646',
            }};
            for (const [k, v] of Object.entries(props)) {{
                btn.style.setProperty(k, v, 'important');
            }}
            if (!btn.querySelector('svg[data-sefa-arrow]')) {{
                btn.innerHTML = (isExpand ? SVG_RIGHT : SVG_LEFT)
                    .replace('<svg', '<svg data-sefa-arrow="1"');
            }}
        }}

        function styleToggle() {{
            const expand = doc.querySelector('[data-testid="stExpandSidebarButton"]');
            const collapse = doc.querySelector('[data-testid="stBaseButton-headerNoPadding"]');

            if (P.innerWidth <= BREAKPOINT) {{
                if (expand) styleAndFloat(expand, true);
            }} else {{
                if (expand) styleAndFloat(expand, true);
                if (collapse) styleAndFloat(collapse, false);
            }}

            doc.querySelectorAll('[data-testid="stBaseButton-header"]').forEach(b => {{
                const text = (b.textContent || '').trim();
                if (text.includes('Deploy') || text.includes('Stop')) {{
                    b.style.setProperty('display', 'none', 'important');
                }}
            }});
        }}

        styleToggle();
        setTimeout(styleToggle, 100);
        setTimeout(styleToggle, 400);
        setTimeout(styleToggle, 1000);
        setTimeout(styleToggle, 2000);

        if (doc.__sefaSidebarObserver) doc.__sefaSidebarObserver.disconnect();
        doc.__sefaSidebarObserver = new MutationObserver(styleToggle);
        doc.__sefaSidebarObserver.observe(doc.body, {{
            childList: true, subtree: true,
            attributes: true,
            attributeFilter: ['data-testid', 'class', 'style'],
        }});
    }})();
    </script>
    """, height=0, width=0)


def inject_pwa_meta():
    components.html("""
    <script>
    (function() {
        const P = window.parent;
        if (!P || !P.document) return;
        const doc = P.document;

        if (!doc.querySelector('link[rel="manifest"]')) {
            const link = doc.createElement('link');
            link.rel = 'manifest';
            link.href = '/app/static/manifest.json';
            doc.head.appendChild(link);
        }

        const metas = [
            ['theme-color', '#00a651'],
            ['apple-mobile-web-app-capable', 'yes'],
            ['apple-mobile-web-app-status-bar-style', 'black-translucent'],
            ['apple-mobile-web-app-title', 'SEFA'],
            ['mobile-web-app-capable', 'yes'],
        ];
        metas.forEach(([name, content]) => {
            if (!doc.querySelector(`meta[name="${name}"]`)) {
                const m = doc.createElement('meta');
                m.name = name;
                m.content = content;
                doc.head.appendChild(m);
            }
        });

        if (!doc.querySelector('link[rel="apple-touch-icon"]')) {
            const icon = doc.createElement('link');
            icon.rel = 'apple-touch-icon';
            icon.href = '/app/static/icon-192.png';
            doc.head.appendChild(icon);
        }

        let vp = doc.querySelector('meta[name="viewport"]');
        if (!vp) {
            vp = doc.createElement('meta');
            vp.name = 'viewport';
            doc.head.appendChild(vp);
        }
        vp.content = 'width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no';

        if ('serviceWorker' in P.navigator && !P.__sefaSW) {
            P.__sefaSW = true;
            P.navigator.serviceWorker.register(
                '/app/static/service-worker.js',
                { scope: '/app/' }
            ).then(() => console.log('SEFA: SW active'))
              .catch((err) => console.log('SEFA: SW error', err));
        }
    })();
    </script>
    """, height=0, width=0)


def mobile_bottom_nav(active_page):
    """Bottom nav — links set ?page=key and preserve ?m=1."""
    nav_items = [
        ("live",       "Home",     "🏠"),
        ("map",        "Map",      "🗺️"),
        ("camera",     "Camera",   "📷"),
        ("weather",    "Weather",  "🌦️"),
        ("irrigation", "Water",    "💧"),
    ]

    is_mobile = st.session_state.get("_is_mobile", False)
    m_param = "&m=1" if is_mobile else ""

    items_html = ""
    for key, label, emoji in nav_items:
        active = "active" if key == active_page else ""

        # Home clears page param → returns to Simple mode
        if key == "live":
            href = f"?{m_param.lstrip('&')}" if m_param else "/"
        else:
            href = f"?page={key}{m_param}"

        items_html += f"""
        <a class="sefa-nav-item {active}"
           href="{href}"
           aria-label="{label}">
            <span class="sefa-nav-emoji">{emoji}</span>
            <span class="sefa-nav-label">{label}</span>
        </a>
        """

    st.html(f"""
    <div class="sefa-bottom-nav">
        {items_html}
    </div>
    """)


def _sparkline_svg(zone):
    rows = history_for_zone(zone, limit=10)
    vals = [r["moisture"] for r in rows if r.get("moisture") is not None]
    if len(vals) < 2:
        return ""
    w, h = 100, 22
    mn, mx = min(vals), max(vals)
    rng = (mx - mn) or 1
    step = w / (len(vals) - 1)
    pts = []
    for i, v in enumerate(vals):
        x = round(i * step, 2)
        y = round(h - 2 - ((v - mn) / rng) * (h - 4), 2)
        pts.append(f"{x},{y}")
    poly = " ".join(pts)
    return (
        f'<svg class="sparkline" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="none">'
        f'<polyline points="{poly}" fill="none" '
        f'stroke="currentColor" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>'
        f'</svg>'
    )


# =========================================================
# Global CSS
# =========================================================
st.html(f"""
<style>
:root, body.sefa-light {{
    --bg: #ffffff;
    --bg-gradient: radial-gradient(ellipse 80% 60% at 50% 0%, #f0f9f3 0%, #ffffff 70%);
    --text: #0d3b1e;
    --text-soft: #4d6b57;
    --text-mute: #7a8f82;
    --accent: #00a651;
    --accent-soft: #7bd39c;
    --accent-deep: #008a43;
    --surface: rgba(255, 255, 255, 0.95);
    --surface-2: #f7f9f7;
    --surface-solid: #ffffff;
    --border: rgba(0, 166, 81, 0.15);
    --border-soft: rgba(0, 166, 81, 0.10);
    --danger: #dc3545;
    --warn: #ff9800;
    --shadow: 0 2px 12px rgba(0, 100, 40, 0.06);
    --shadow-lift: 0 8px 24px rgba(0, 100, 40, 0.12);
    --nav-bg: #ffffff;
    --nav-border: rgba(0, 166, 81, 0.15);
    --nav-active: #00a651;
    --nav-inactive: #7a8f82;
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --input-bg: #ffffff;
    --code-bg: #f0f4f0;
    --code-text: #0d3b1e;
}}

body.sefa-dark {{
    --bg: #0a0f0a;
    --bg-gradient: radial-gradient(ellipse 80% 60% at 50% 0%, #0f1a12 0%, #060a06 70%);
    --text: #d4f5d4;
    --text-soft: #9ccc9c;
    --text-mute: #6a8a6a;
    --accent: #00e676;
    --accent-soft: #69f0ae;
    --accent-deep: #00b060;
    --surface: rgba(15, 26, 15, 0.95);
    --surface-2: #0f1a0f;
    --surface-solid: #0f1a0f;
    --border: rgba(0, 230, 118, 0.20);
    --border-soft: rgba(0, 230, 118, 0.10);
    --danger: #ff5252;
    --warn: #ffd54f;
    --shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
    --shadow-lift: 0 8px 24px rgba(0, 230, 118, 0.15);
    --nav-bg: #0f1a0f;
    --nav-border: rgba(0, 230, 118, 0.20);
    --nav-active: #00e676;
    --nav-inactive: #6a8a6a;
    --input-bg: #0f1a0f;
    --code-bg: #0f1a0f;
    --code-text: #d4f5d4;
}}

* {{
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, 'Helvetica Neue', Arial, sans-serif;
    -webkit-tap-highlight-color: transparent;
}}

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    background: var(--bg) !important;
    color: var(--text) !important;
}}
.stApp {{ background: var(--bg-gradient); }}

#MainMenu, footer {{ visibility: hidden; }}

header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 3.5rem !important;
    min-height: 3.5rem !important;
    z-index: 999998 !important;
    pointer-events: auto !important;
}}
header[data-testid="stHeader"] * {{
    pointer-events: auto !important;
}}

@media (min-width: {MOBILE_BREAKPOINT + 1}px) {{
    [data-testid="stExpandSidebarButton"],
    [data-testid="stBaseButton-headerNoPadding"],
    button[kind="header"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 9999999 !important;
    }}
    section[data-testid="stSidebar"] {{
        display: block !important;
    }}
}}

h1, h2, h3, h4 {{
    color: var(--accent) !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em;
}}
h2 {{ font-size: 22px !important; margin: 12px 0 8px !important; }}
h3 {{
    font-size: 16px !important; margin: 10px 0 6px !important;
    text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--accent-deep) !important; font-weight: 600 !important;
}}
h3 svg, h2 svg {{ stroke: var(--accent); margin-right: 6px; }}

@media (max-width: {MOBILE_BREAKPOINT}px) {{
    section[data-testid="stSidebar"] {{
        display: none !important;
    }}
    [data-testid="stExpandSidebarButton"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }}
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    .block-container {{
        padding-top: 4rem !important;
        padding-bottom: 120px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        max-width: 100% !important;
    }}
    .stDataFrame {{ font-size: 12px !important; }}
}}

/* BOTTOM NAV */
.sefa-bottom-nav {{
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: calc(64px + env(safe-area-inset-bottom, 0px)) !important;
    padding-bottom: env(safe-area-inset-bottom, 0px) !important;
    padding-top: 4px !important;
    margin: 0 !important;
    background: var(--nav-bg) !important;
    border-top: 1px solid var(--nav-border) !important;
    display: flex !important;
    justify-content: space-around !important;
    align-items: center !important;
    z-index: 2147483647 !important;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.10) !important;
    transform: translateZ(0) !important;
    pointer-events: auto !important;
}}
.sefa-bottom-nav .sefa-nav-item {{
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 3px !important;
    padding: 6px 4px !important;
    color: var(--nav-inactive) !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    border: none !important;
    background: transparent !important;
    cursor: pointer !important;
    font-family: inherit !important;
    min-height: 56px !important;
    text-decoration: none !important;
    -webkit-tap-highlight-color: transparent !important;
    transition: color 0.2s ease !important;
}}
.sefa-bottom-nav .sefa-nav-item.active {{
    color: var(--nav-active) !important;
}}
.sefa-bottom-nav .sefa-nav-emoji {{
    font-size: 22px !important;
    line-height: 1 !important;
}}
.sefa-bottom-nav .sefa-nav-label {{
    font-size: 10px !important;
    line-height: 1 !important;
    color: currentColor !important;
}}
@media (min-width: {MOBILE_BREAKPOINT + 1}px) {{
    .sefa-bottom-nav {{ display: none !important; }}
    .block-container {{
        padding-top: 3rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1360px !important;
    }}
}}

/* HERO */
.sefa-hero {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    gap: 16px;
    position: relative;
    overflow: hidden;
}}
.sefa-hero.hero-alert {{
    border-color: var(--danger);
    box-shadow: var(--shadow), 0 0 24px rgba(220, 53, 69, 0.15);
}}
.sefa-title-wrap {{
    display: inline-flex;
    align-items: baseline;
    gap: 1px;
    font-weight: 300;
    letter-spacing: -0.04em;
}}
.sefa-title-letter {{
    display: inline-block;
    font-weight: 300;
    background: linear-gradient(90deg,
        var(--accent) 0%, var(--accent-soft) 50%,
        var(--accent) 100%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: brand-shimmer 6s ease-in-out infinite;
}}
@keyframes brand-shimmer {{
    0%   {{ background-position: 200% 50%; }}
    100% {{ background-position: -100% 50%; }}
}}
.hero-alert-chip {{
    display: none;
    background: var(--danger);
    color: #ffffff;
    font-weight: 700;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 8px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
.sefa-hero.hero-alert .hero-alert-chip {{ display: inline-block; }}
.hero-num {{ display: inline-block; font-weight: 500; letter-spacing: -0.02em; }}

/* METRICS */
[data-testid="stMetric"] {{
    background: var(--surface) !important;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px !important;
    box-shadow: var(--shadow);
    transition: all 0.3s ease;
}}
[data-testid="stMetric"]:active {{ transform: scale(0.98); }}
[data-testid="stMetricValue"] {{
    color: var(--accent) !important;
    font-weight: 600 !important;
    font-size: 28px !important;
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
}}
[data-testid="stMetricLabel"] {{
    color: var(--text-soft) !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 11px !important;
    font-weight: 600 !important;
}}

/* SIDEBAR */
section[data-testid="stSidebar"] > div:first-child {{
    background: var(--surface-2) !important;
    border-right: 1px solid var(--border-soft);
}}
section[data-testid="stSidebar"] .stButton button {{
    background: var(--accent) !important;
    color: #ffffff !important;
    font-weight: 500;
    border: none !important;
    border-radius: 12px;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
    padding: 10px 14px !important;
    border-radius: 10px;
    border: 1px solid transparent;
    font-weight: 400;
    color: var(--text) !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    background: var(--surface);
    border-color: var(--border-soft);
}}

/* SIDEBAR WEATHER */
.sefa-sidebar-weather {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
    margin: 8px 0;
    font-size: 12px;
}}
.sefa-sidebar-weather .title {{
    font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.15em; color: var(--text-mute);
    font-weight: 600; margin-bottom: 8px;
}}
.sefa-sidebar-weather .temp {{
    font-size: 26px; font-weight: 500;
    letter-spacing: -0.02em; color: var(--accent); line-height: 1;
}}
.sefa-sidebar-weather .desc {{
    color: var(--text-soft); font-size: 11px;
    margin-top: 6px;
}}
.sefa-sidebar-weather .row {{
    display: flex; justify-content: space-between;
    color: var(--text-mute); font-size: 11px;
    margin-top: 6px;
}}

/* ZONE CARDS */
.sefa-zone {{
    padding: 14px 10px;
    border-radius: 16px;
    text-align: center;
    border: 1px solid var(--border);
    font-size: 13px;
    line-height: 1.5;
    background: var(--surface);
    color: var(--text);
    transition: all 0.3s ease;
    font-weight: 400;
    box-shadow: var(--shadow);
    margin-bottom: 8px;
}}
.sefa-zone:active {{
    transform: scale(0.97);
    background: var(--surface-2);
}}
.sefa-zone b {{
    font-size: 17px;
    color: var(--accent);
    font-weight: 600;
}}
.sefa-zone .sparkline {{
    margin: 4px auto;
    display: block;
    width: 100%;
    max-width: 100px;
    height: 20px;
    opacity: 0.85;
}}
@media (max-width: {MOBILE_BREAKPOINT}px) {{
    .sefa-zone .sparkline {{ display: none; }}
}}
.sefa-zone.zone-attention {{
    border-color: var(--danger);
    background: rgba(220, 53, 69, 0.06);
    animation: attention-pulse 2.4s ease-in-out infinite;
}}
@keyframes attention-pulse {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.0); }}
    50%      {{ box-shadow: 0 0 20px 4px rgba(220, 53, 69, 0.25); }}
}}
.sefa-zone.zone-monitor {{ border-color: var(--warn); background: rgba(255, 152, 0, 0.06); }}
.sefa-zone.zone-critical {{ border-color: var(--danger); }}

/* LEGEND, STATUS STRIP, ALERTS */
.sefa-legend span {{
    display: inline-block; padding: 5px 12px; border-radius: 20px;
    margin-right: 6px; margin-bottom: 6px; font-size: 11px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase;
}}
.sefa-status-strip {{
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 13px;
    color: var(--text-soft);
    box-shadow: var(--shadow);
}}
@media (min-width: {MOBILE_BREAKPOINT + 1}px) {{
    .sefa-status-strip {{
        flex-direction: row;
        justify-content: space-between;
        flex-wrap: wrap;
        font-size: 12px;
    }}
}}
.sefa-status-strip b {{ color: var(--accent); font-weight: 600; }}
.sefa-alert-row {{
    background: var(--surface);
    border-left: 4px solid var(--accent);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow: var(--shadow);
    font-size: 14px;
}}
.sefa-alert-row.sev-high {{ border-left-color: var(--danger); }}
.sefa-alert-row.sev-med  {{ border-left-color: var(--warn); }}
.sefa-alert-row.sev-low  {{ border-left-color: var(--accent); }}

/* SIMPLE MODE */
.sefa-answer-card {{
    border-radius: 24px;
    padding: 32px 24px;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: var(--shadow-lift);
}}
.sefa-answer-icon {{
    font-size: 80px;
    line-height: 1;
    margin-bottom: 16px;
}}
.sefa-answer-title {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
}}
.sefa-answer-sub {{
    font-size: 15px;
    margin-top: 12px;
    color: var(--text-soft);
    line-height: 1.5;
}}
@media (max-width: {MOBILE_BREAKPOINT}px) {{
    .sefa-answer-icon {{ font-size: 64px; margin-bottom: 12px; }}
    .sefa-answer-title {{ font-size: 22px; }}
    .sefa-answer-card {{ padding: 24px 18px; }}
}}

.sefa-status-card {{
    background: var(--surface);
    border: 2px solid;
    border-radius: 18px;
    padding: 18px;
    text-align: center;
    margin-bottom: 12px;
    box-shadow: var(--shadow);
}}
.sefa-status-icon {{ font-size: 40px; line-height: 1; }}
.sefa-status-label {{ font-size: 15px; font-weight: 700; margin-top: 8px; }}
.sefa-status-sub {{ font-size: 12px; color: var(--text-mute); margin-top: 6px; }}

/* BUTTONS */
.stButton button,
.stFormSubmitButton button,
.stDownloadButton button {{
    min-height: 52px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    border-radius: 14px !important;
    padding: 12px 20px !important;
    transition: all 0.2s ease !important;
    background: var(--accent) !important;
    color: #ffffff !important;
    border: none !important;
}}
.stButton button:active {{
    transform: scale(0.97) !important;
}}

/* INPUTS */
.stTextInput input,
.stNumberInput input,
.stSelectbox > div > div,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
.stTextArea textarea {{
    min-height: 48px !important;
    background: var(--input-bg) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    font-size: 16px !important;
    padding: 12px 14px !important;
}}
.stTextInput input:focus,
.stNumberInput input:focus,
.stSelectbox > div > div:focus-within {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(0, 166, 81, 0.15) !important;
}}
[role="radiogroup"] label {{
    min-height: 48px;
    padding: 12px 8px !important;
}}
[data-testid="stToggle"] {{ padding: 8px 0; }}
[role="radiogroup"] label span,
[role="radiogroup"] label p,
[data-testid="stToggle"] label,
[data-testid="stToggle"] span,
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p,
.stCheckbox label,
.stRadio label {{ color: var(--text) !important; }}

/* POPOVER */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[role="listbox"] {{
    background: var(--surface-solid) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}}
[role="option"] {{
    background: var(--surface-solid) !important;
    color: var(--text) !important;
    padding: 12px 14px !important;
    min-height: 44px;
}}
[role="option"]:hover,
[role="option"][aria-selected="true"] {{
    background: var(--surface-2) !important;
    color: var(--accent) !important;
}}

/* DATAFRAMES */
.stDataFrame {{
    background: var(--surface) !important;
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    box-shadow: var(--shadow);
}}
body.sefa-dark .stDataFrame,
body.sefa-dark .stDataFrame *,
body.sefa-dark [data-testid="stDataFrame"],
body.sefa-dark [data-testid="stDataFrame"] * {{
    --gdg-bg-cell: #0f1a0f;
    --gdg-bg-cell-medium: #0a0f0a;
    --gdg-bg-header: #0f1a0f;
    --gdg-bg-header-has-focus: #152215;
    --gdg-bg-header-hovered: #152215;
    --gdg-bg-bubble: #1a2a1a;
    --gdg-bg-bubble-selected: #1a2a1a;
    --gdg-bg-search-result: #2a3a2a;
    --gdg-border-color: rgba(0, 230, 118, 0.15);
    --gdg-horizontal-border-color: rgba(0, 230, 118, 0.10);
    --gdg-drilldown-border: rgba(0, 230, 118, 0.30);
    --gdg-accent-color: #00e676;
    --gdg-accent-light: rgba(0, 230, 118, 0.15);
    --gdg-accent-fg: #0a0f0a;
    --gdg-text-dark: #d4f5d4;
    --gdg-text-medium: #9ccc9c;
    --gdg-text-light: #6a8a6a;
    --gdg-text-bubble: #d4f5d4;
    --gdg-text-header: #d4f5d4;
    --gdg-text-group-header: #00e676;
    --gdg-text-header-selected: #0a0f0a;
    --gdg-link-color: #00e676;
    --gdg-fg-error: #ff5252;
    --gdg-fg-icon: #9ccc9c;
}}

/* EXPANDERS */
details {{
    background: var(--surface) !important;
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    margin-bottom: 10px;
}}
details summary {{
    color: var(--accent) !important;
    font-weight: 600 !important;
    padding: 14px 16px !important;
    font-size: 15px;
    min-height: 48px;
    display: flex;
    align-items: center;
}}
details summary p, details summary span, details summary div {{
    color: var(--accent) !important;
}}

/* TABS */
button[data-baseweb="tab"] {{
    font-size: 13px !important;
    padding: 12px 16px !important;
    min-height: 48px;
    font-weight: 600;
    color: var(--text-soft) !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}}
[data-baseweb="tab-list"] {{
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    background: transparent !important;
    border: none !important;
}}
[data-baseweb="tab-list"]::-webkit-scrollbar {{ display: none; }}

/* FORMS */
[data-testid="stForm"] {{
    background: var(--surface) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 14px;
    padding: 16px !important;
}}

/* CODE / ALERTS */
code, pre, .stCodeBlock, [data-testid="stCodeBlock"] {{
    background: var(--code-bg) !important;
    color: var(--code-text) !important;
    border-radius: 8px;
}}
.stAlert, [data-testid="stAlert"] {{
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px;
}}

/* HR / SCROLLBAR */
hr {{
    border: none; height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 16px 0 !important;
}}
::-webkit-scrollbar {{ width: 3px; height: 3px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

/* LAYOUT */
[data-testid="stVerticalBlock"] > div {{ gap: 0.6rem !important; }}

/* DISABLE HOVER ON TOUCH */
@media (hover: none) {{
    [data-testid="stMetric"]:hover,
    .sefa-zone:hover {{ transform: none !important; }}
}}
</style>
""")

apply_theme()
detect_mobile()
fix_sidebar_toggle()
inject_pwa_meta()


# =========================================================
# Metric roll-up animator
# =========================================================
def _inject_metric_animator():
    components.html("""
    <script>
    (function() {
        const PARENT = window.parent;
        if (!PARENT || !PARENT.document) return;
        const doc = PARENT.document;
        if (doc.__sefaAnimatorV2) return;
        doc.__sefaAnimatorV2 = true;
        function parseNumber(text) {
            const m = String(text).match(/^(-?[\\d.,]+)/);
            if (!m) return null;
            const raw = m[1].replace(/,/g, '');
            const n = parseFloat(raw);
            if (isNaN(n)) return null;
            return { value: n, suffix: String(text).slice(m[1].length) };
        }
        function animateOne(el) {
            const original = el.getAttribute('data-sefa-orig') || el.textContent.trim();
            el.setAttribute('data-sefa-orig', original);
            el.setAttribute('data-sefa-done', '1');
            const parsed = parseNumber(original);
            if (!parsed) return;
            const target = parsed.value;
            const duration = 700;
            const start = performance.now();
            function tick(now) {
                const t = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - t, 3);
                const current = target * eased;
                const formatted = (Number.isInteger(target) ? Math.round(current) : current.toFixed(1));
                el.textContent = formatted + parsed.suffix;
                if (t < 1) requestAnimationFrame(tick);
                else el.textContent = original;
            }
            requestAnimationFrame(tick);
        }
        function runOnce() {
            const metrics = doc.querySelectorAll(
                '[data-testid="stMetricValue"]:not([data-sefa-done]), .hero-num:not([data-sefa-done])'
            );
            metrics.forEach(animateOne);
        }
        let runs = 0;
        const interval = setInterval(() => {
            runOnce();
            runs++;
            if (runs >= 6) clearInterval(interval);
        }, 300);
    })();
    </script>
    """, height=0, width=0)


# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.title(t("sidebar_title"))
    st.caption(t("app_subtitle"))

    simple = st.toggle(
        "🧑‍🌾 Simple mode",
        value=st.session_state.get("simple_mode", True),
        key="simple_toggle",
    )
    st.session_state["simple_mode"] = simple
    st.divider()

    language_selector()
    st.divider()

    if st.button(t("run_cycle"), use_container_width=True, type="primary"):
        with st.spinner(t("running_cycle", n=16)):
            n = simulate_cycle()
        st.success(t("cycle_done", n=n))
        st.rerun()

    auto = st.toggle(t("auto_refresh"), value=False)

    st.divider()
    page = st.radio(
        t("view"),
        [t("page_live"),
         t("page_map"),
         t("page_alerts"),
         t("page_ai"),
         t("page_camera"),
         t("page_trends"),
         t("page_weather"),
         t("page_analytics"),
         t("page_irrigation")],
        label_visibility="collapsed",
        key="view_widget",
    )

    st.divider()
    st.caption(f"**{t('thresholds')}**")
    st.code(
        f"{t('threshold_moisture_dry')}   < {THRESHOLDS['moisture_dry']}%\n"
        f"{t('threshold_moisture_wet')}   > {THRESHOLDS['moisture_wet']}%\n"
        f"{t('threshold_temp_high')}      > {THRESHOLDS['temp_high']}°C\n"
        f"{t('threshold_ph_range')}       {THRESHOLDS['ph_min']}–{THRESHOLDS['ph_max']}\n"
        f"{t('threshold_battery_low')}    < {THRESHOLDS['battery_low']}%",
        language="text",
    )

    st.divider()
    st.markdown(f"#### {t('zones')}")

    _quick = {r["zone"]: r for r in latest_per_zone()}
    _quick_ai = {r["zone"]: r for r in latest_ai_per_zone()}
    _counts = {"Normal": 0, "Monitor": 0, "Attention Required": 0, "No Data": 0}
    for _z in ZONES:
        _s, _rec, _p, _sc = evaluate_zone(_quick.get(_z), _quick_ai.get(_z))
        _counts[_s] = _counts.get(_s, 0) + 1

    st.markdown(f"""
    <div style="font-size:13px;color:var(--text);line-height:2.1;font-weight:400">
        <span style="color:var(--accent)">●</span> {t('status_normal')} · <b>{_counts['Normal']}</b><br>
        <span style="color:var(--warn)">●</span> {t('status_monitor')} · <b>{_counts['Monitor']}</b><br>
        <span style="color:var(--danger)">●</span> {t('status_attention')} · <b>{_counts['Attention Required']}</b>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    dark_now = st.session_state.get("theme") == "dark"
    new_dark = st.toggle(
        "🌙 Dark mode" if not dark_now else "☀️ Light mode",
        value=dark_now,
        key="theme_toggle",
    )
    if new_dark != dark_now:
        st.session_state["theme"] = "dark" if new_dark else "light"
        st.rerun()

    st.divider()

    try:
        _wc = get_current_cached()
        if _wc and "error" not in _wc:
            _desc_en, _icon = describe_weather(_wc.get("weather_code"))
            _desc = t_weather_condition(_desc_en)
            st.markdown(f"""
            <div class="sefa-sidebar-weather">
                <div class="title">{t('weather_current')}</div>
                <div style="display:flex;align-items:baseline;gap:10px">
                    <div class="temp">{_wc.get('temperature', '—')}°</div>
                    <div style="color:var(--text-soft);font-size:11px">
                        {_icon} {_desc}
                    </div>
                </div>
                <div class="row">
                    <span>{t('weather_humidity')} {_wc.get('humidity','—')}%</span>
                    <span>{t('weather_wind')} {_wc.get('wind','—')} km/h</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass

    st.divider()
    st.caption("Edge prototype — data is simulated.")


# =========================================================
# Load data + evaluate
# =========================================================
sensors = {r["zone"]: r for r in latest_per_zone()}
ais     = {r["zone"]: r for r in latest_ai_per_zone()}

evaluated = []
for zone in ZONES:
    s = sensors.get(zone)
    a = ais.get(zone)
    status, rec, pri, score = evaluate_zone(s, a)
    evaluated.append({
        "zone": zone, "status": status, "recommendation": rec,
        "priority": pri, "score": score,
        "moisture": s["moisture"] if s else None,
        "temperature": s["temperature"] if s else None,
        "ph": s["ph"] if s else None, "ec": s["ec"] if s else None,
        "battery": s["battery"] if s else None,
        "prediction": a["prediction"] if a else "—",
        "confidence": a["confidence"] if a else None,
        "node_id": s["node_id"] if s else "—",
        "timestamp": s["timestamp"] if s else None,
    })

ev_df = pd.DataFrame(evaluated)


# =========================================================
# Header
# =========================================================
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if not sensors:
    st.markdown(f"## {icons.icon_leaf(28)} {t('app_title')}",
                unsafe_allow_html=True)
    st.caption(t("app_caption", time=now))
    st.warning("No data yet. Click **▶ Run Simulation Cycle** to begin.")
    st.stop()


# =========================================================
# SIMPLE MODE
# =========================================================
if st.session_state["simple_mode"]:

    _normal, _monitor, _attention, _avg_m = field_summary(evaluated)

    _dry_zones = [z for z in evaluated
                  if z["moisture"] is not None
                  and z["moisture"] < THRESHOLDS["moisture_dry"]]
    _water_needed = len(_dry_zones) > 0

    try:
        _forecast = get_forecast_cached()
        _advice = irrigation_advice(_forecast)
        _rain_coming = _advice["skip_irrigation"]
    except Exception:
        _rain_coming = False

    _sick_zones = [z for z in evaluated
                   if z["prediction"] in ("Possible Disease",
                                          "Possible Pest",
                                          "Crop Stress")
                   and (z["confidence"] or 0) > 75]

    if _water_needed and not _rain_coming:
        answer_icon = "💧"
        answer_title = "YES — Water your field today"
        answer_sub = f"{len(_dry_zones)} zones are dry. No rain expected."
        answer_color = "#dc3545"
        answer_bg = "rgba(220, 53, 69, 0.08)"
    elif _rain_coming:
        answer_icon = "🌧️"
        answer_title = "NO — Rain is coming"
        answer_sub = "Wait for rain. Save water."
        answer_color = "#00a651"
        answer_bg = "rgba(0, 166, 81, 0.08)"
    else:
        answer_icon = "✅"
        answer_title = "NO — Field is fine today"
        answer_sub = "Soil moisture is good. Check again tomorrow."
        answer_color = "#00a651"
        answer_bg = "rgba(0, 166, 81, 0.08)"

    st.markdown(f"""
    <div class="sefa-answer-card"
         style="background:{answer_bg}; border:3px solid {answer_color};">
        <div class="sefa-answer-icon">{answer_icon}</div>
        <div class="sefa-answer-title" style="color:{answer_color};">
            {answer_title}
        </div>
        <div class="sefa-answer-sub">{answer_sub}</div>
    </div>
    """, unsafe_allow_html=True)

    if _attention > 0:
        field_icon, field_label, field_color = "🔴", "Check field", "#dc3545"
    elif _monitor > 0:
        field_icon, field_label, field_color = "🟡", "Watch field", "#ff9800"
    else:
        field_icon, field_label, field_color = "🟢", "Field is fine", "#00a651"

    if _avg_m < THRESHOLDS["moisture_dry"]:
        soil_label, soil_color = "Dry", "#dc3545"
    elif _avg_m < 40:
        soil_label, soil_color = "Getting dry", "#ff9800"
    elif _avg_m > THRESHOLDS["moisture_wet"]:
        soil_label, soil_color = "Too wet", "#0288d1"
    else:
        soil_label, soil_color = "Good", "#00a651"

    if _sick_zones:
        crop_icon, crop_label, crop_color = "🐛", "Look at crops", "#dc3545"
        crop_sub = f"{len(_sick_zones)} zone(s) may have issues"
    else:
        crop_icon, crop_label, crop_color = "🌱", "Crops healthy", "#00a651"
        crop_sub = "No problems detected"

    if st.session_state["_is_mobile"]:
        st.markdown(f"""
        <div class="sefa-status-card" style="border-color:{field_color};">
            <div class="sefa-status-icon">{field_icon}</div>
            <div class="sefa-status-label" style="color:{field_color};">
                {field_label}
            </div>
            <div class="sefa-status-sub">{_attention + _monitor} of {len(ZONES)} zones</div>
        </div>
        <div class="sefa-status-card" style="border-color:{soil_color};">
            <div class="sefa-status-icon">💧</div>
            <div class="sefa-status-label" style="color:{soil_color};">
                Soil is {soil_label.lower()}
            </div>
            <div class="sefa-status-sub">Average moisture: {_avg_m:.0f}%</div>
        </div>
        <div class="sefa-status-card" style="border-color:{crop_color};">
            <div class="sefa-status-icon">{crop_icon}</div>
            <div class="sefa-status-label" style="color:{crop_color};">
                {crop_label}
            </div>
            <div class="sefa-status-sub">{crop_sub}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="sefa-status-card" style="border-color:{field_color};">
                <div class="sefa-status-icon">{field_icon}</div>
                <div class="sefa-status-label" style="color:{field_color};">
                    {field_label}</div>
                <div class="sefa-status-sub">{_attention + _monitor} of {len(ZONES)} zones</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="sefa-status-card" style="border-color:{soil_color};">
                <div class="sefa-status-icon">💧</div>
                <div class="sefa-status-label" style="color:{soil_color};">
                    Soil is {soil_label.lower()}</div>
                <div class="sefa-status-sub">Average moisture: {_avg_m:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="sefa-status-card" style="border-color:{crop_color};">
                <div class="sefa-status-icon">{crop_icon}</div>
                <div class="sefa-status-label" style="color:{crop_color};">
                    {crop_label}</div>
                <div class="sefa-status-sub">{crop_sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    st.markdown("### What do you want to do?")

    if st.session_state["_is_mobile"]:
        if st.button("📷  Check my crops", use_container_width=True,
                     key="simple_cam_btn"):
            st.session_state["page_override"] = "camera"
            st.rerun()
        if st.button("💧  Start watering", use_container_width=True,
                     key="simple_water_btn"):
            st.session_state["page_override"] = "irrigation"
            st.rerun()
        if st.button("🌦️  See weather", use_container_width=True,
                     key="simple_weather_btn"):
            st.session_state["page_override"] = "weather"
            st.rerun()
    else:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("📷  Check my crops", use_container_width=True,
                         key="simple_cam_btn"):
                st.session_state["page_override"] = "camera"
                st.rerun()
        with b2:
            if st.button("💧  Start watering", use_container_width=True,
                         key="simple_water_btn"):
                st.session_state["page_override"] = "irrigation"
                st.rerun()
        with b3:
            if st.button("🌦️  See weather", use_container_width=True,
                         key="simple_weather_btn"):
                st.session_state["page_override"] = "weather"
                st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    st.markdown("### What needs attention")

    _alerts = recent_alerts(limit=5)
    if not _alerts:
        st.success("✅ No problems today. Come back tomorrow.")
    else:
        for a in _alerts:
            _sev = a["severity"]
            if _sev == "High":
                icon, color, word = "🔴", "#dc3545", "Now"
            elif _sev == "Medium":
                icon, color, word = "🟡", "#ff9800", "Soon"
            else:
                icon, color, word = "🟢", "#00a651", "Later"

            st.markdown(f"""
            <div class="sefa-alert-row" style="border-left-color:{color};">
                <div style="display:flex;align-items:center;gap:14px;">
                    <div style="font-size:28px;">{icon}</div>
                    <div style="flex:1;">
                        <div style="font-size:15px;font-weight:600;">
                            {t_alert_type(a['alert_type'])}
                        </div>
                        <div style="font-size:12px;color:var(--text-mute);
                                    margin-top:4px;">
                            Zone {a['zone']} · {word}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <a href="tel:+919876543210" style="
        display: block;
        background: #00a651;
        color: white;
        text-align: center;
        padding: 18px;
        border-radius: 16px;
        font-size: 18px;
        font-weight: 700;
        text-decoration: none;
        margin-top: 8px;
    ">📞  Call for help</a>
    """, unsafe_allow_html=True)

    if not st.session_state["_is_mobile"]:
        st.caption("Turn off Simple Mode in the sidebar to see the full dashboard.")

    mobile_bottom_nav("live")
    st.stop()


# =========================================================
# ADVANCED MODE
# =========================================================
_normal    = int((ev_df["status"] == "Normal").sum())
_attention = int((ev_df["status"] == "Attention Required").sum())
_alerts_recent = len(recent_alerts(limit=200))

hero_classes = "sefa-hero"
if _attention > 0:
    hero_classes += " hero-alert"

sefa_letters = "".join(
    f'<span class="sefa-title-letter">{ch}</span>' for ch in "SEFA"
)

st.markdown(f"""
<div class="{hero_classes}">
    <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;">
        <div class="sefa-title-wrap" style="font-size:44px;line-height:1">
            {sefa_letters}
        </div>
        <div style="color:var(--text-soft);font-size:11px;
                    letter-spacing:0.15em;text-transform:uppercase;
                    font-weight:500">
            {t('app_subtitle')}
        </div>
    </div>
    <div style="display:flex;gap:24px;justify-content:space-between;">
        <div style="flex:1;text-align:center;">
            <div style="color:var(--accent);font-size:26px;font-weight:600;
                        letter-spacing:-0.02em">
                <span class="hero-num">{_normal}</span>
            </div>
            <div style="color:var(--text-mute);font-size:10px;
                        text-transform:uppercase;letter-spacing:0.1em;
                        margin-top:2px;font-weight:600">
                {t('status_normal')}
            </div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="color:var(--danger);font-size:26px;font-weight:600;
                        letter-spacing:-0.02em">
                <span class="hero-num">{_attention}</span>
                <span class="hero-alert-chip">!</span>
            </div>
            <div style="color:var(--text-mute);font-size:10px;
                        text-transform:uppercase;letter-spacing:0.1em;
                        margin-top:2px;font-weight:600">
                {t('status_attention')}
            </div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="color:var(--warn);font-size:26px;font-weight:600;
                        letter-spacing:-0.02em">
                <span class="hero-num">{_alerts_recent}</span>
            </div>
            <div style="color:var(--text-mute);font-size:10px;
                        text-transform:uppercase;letter-spacing:0.1em;
                        margin-top:2px;font-weight:600">
                {t('page_alerts').replace('🚨','').strip()}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

_sensor_health = sum(1 for z in evaluated if z.get("moisture") is not None)
_battery_vals  = [z["battery"] for z in evaluated if z.get("battery") is not None]
_battery_min   = min(_battery_vals) if _battery_vals else 0
_data_age      = "—"
_ts = [z["timestamp"] for z in evaluated if z.get("timestamp")]
if _ts:
    try:
        _latest = max(pd.to_datetime(_ts))
        _age_s = int((pd.Timestamp.now() - _latest).total_seconds())
        _data_age = f"{_age_s}s" if _age_s < 3600 else f"{_age_s // 60}m"
    except Exception:
        _data_age = "—"

st.markdown(f"""
<div class="sefa-status-strip">
    <span>🛰 Sensors <b>{_sensor_health}/{len(ZONES)}</b></span>
    <span>🔋 Min battery <b>{_battery_min:.0f}%</b></span>
    <span>⏱ Last data <b>{_data_age}</b></span>
    <span>🌐 Edge / Offline</span>
    <span>📡 LoRa <b>OK</b></span>
</div>
""", unsafe_allow_html=True)

_inject_metric_animator()


# =========================================================
# PAGE: LIVE
# =========================================================
if page == t("page_live"):
    normal, monitor, attention, avg_m = field_summary(evaluated)

    if st.session_state["_is_mobile"]:
        c1, c2 = st.columns(2)
        c1.metric(t("zones"), len(ZONES))
        c2.metric(t("status_normal"), normal)
        c3, c4 = st.columns(2)
        c3.metric(t("status_monitor"), monitor)
        c4.metric(t("status_attention"), attention)
        c5, c6 = st.columns(2)
        c5.metric(t("avg_moisture"), f"{avg_m:.1f}%")
        c6.metric(t("page_alerts").replace('🚨','').strip(), _alerts_recent)
    else:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(t("zones"), len(ZONES))
        c2.metric(t("status_normal"), normal)
        c3.metric(t("status_monitor"), monitor)
        c4.metric(t("status_attention"), attention)
        c5.metric(t("avg_moisture"), f"{avg_m:.1f}%")
        c6.metric(t("page_alerts").replace('🚨','').strip(), _alerts_recent)

    st.markdown(f"<h3>{icons.icon_home()} {t('live_title')}</h3>",
                unsafe_allow_html=True)

    color = {
        "Normal":             ("rgba(0,166,81,0.06)",  "var(--accent)"),
        "Monitor":            ("rgba(255,152,0,0.06)", "var(--warn)"),
        "Attention Required": ("rgba(220,53,69,0.06)", "var(--danger)"),
        "No Data":            ("rgba(0,0,0,0.03)",     "var(--text-mute)"),
    }

    _n_cols = 2 if st.session_state["_is_mobile"] else 4
    cols = st.columns(_n_cols)
    sorted_df = ev_df.sort_values("zone").reset_index(drop=True)
    for i, row in sorted_df.iterrows():
        bg, fg = color.get(row["status"], color["No Data"])
        classes = "sefa-zone"
        if row["status"] == "Attention Required":
            classes += " zone-attention"
            if row.get("priority") == "High":
                classes += " zone-critical"
        elif row["status"] == "Monitor":
            classes += " zone-monitor"

        spark = _sparkline_svg(row["zone"])

        with cols[i % _n_cols]:
            st.markdown(f"""
                <div class="{classes}" style="background:{bg};color:{fg}">
                    <b>{row['zone']}</b>
                    {spark}<br>
                    💧 {row['moisture']}% · 🌡 {row['temperature']}°C<br>
                    pH {row['ph']} · 🔋 {row['battery']}%<br>
                    <small>{t_status(row['status'])}</small>
                </div>
            """, unsafe_allow_html=True)

    st.markdown(f"<h3>{icons.icon_alert()} {t('page_alerts').replace('🚨','').strip()}</h3>",
                unsafe_allow_html=True)

    alerts_side = recent_alerts(limit=6)
    if not alerts_side:
        st.info(t("no_alerts"))
    else:
        for a in alerts_side:
            sev_class = {"High": "sev-high",
                         "Medium": "sev-med",
                         "Low": "sev-low"}.get(a["severity"], "sev-low")
            st.markdown(f"""
            <div class="sefa-alert-row {sev_class}">
                <b style="color:var(--accent);font-weight:600">{a['zone']}</b>
                · {t_alert_type(a['alert_type'])}
                <div style="color:var(--text-mute);font-size:11px;margin-top:4px">
                    {a['timestamp'][11:19]}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown(f"**{t('moisture')}**")
    for z in sorted(evaluated, key=lambda x: x.get("moisture") or 0)[:6]:
        if z["moisture"] is None:
            continue
        pct = min(max(z["moisture"], 0), 100)
        st.markdown(f"""
        <div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;
                        font-size:12px;color:var(--text-soft);font-weight:500">
                <span>{z['zone']}</span>
                <span style="color:var(--accent)">{pct}%</span>
            </div>
            <div style="background:var(--border);height:4px;
                        border-radius:2px;overflow:hidden;margin-top:4px">
                <div style="width:{pct}%;height:100%;
                            background:var(--accent)"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown(f"<h3>{icons.icon_alert()} {t('zones_requiring_action')}</h3>",
                unsafe_allow_html=True)

    need = ev_df[ev_df["status"] != "Normal"].sort_values(
        "score", ascending=False).copy()

    if need.empty:
        st.success(t("all_normal"))
    else:
        need["status"]         = need["status"].map(t_status)
        need["prediction"]     = need["prediction"].map(t_prediction)
        need["recommendation"] = need["recommendation"].map(translate_recommendation)
        need["priority"]       = need["priority"].map(t_severity)
        st.dataframe(
            need[["zone", "status", "priority", "recommendation",
                  "moisture", "temperature", "prediction", "confidence"]],
            use_container_width=True, hide_index=True,
        )

    mobile_bottom_nav("live")


# =========================================================
# PAGE: ZONE MAP
# =========================================================
elif page == t("page_map"):
    st.markdown(f"<h3>{icons.icon_map()} {t('map_title')}</h3>",
                unsafe_allow_html=True)

    color_map = {
        "Normal":             "rgba(0,166,81,0.06)",
        "Monitor":            "rgba(255,152,0,0.06)",
        "Attention Required": "rgba(220,53,69,0.06)",
        "No Data":            "rgba(0,0,0,0.03)",
    }

    _n_cols = 2 if st.session_state["_is_mobile"] else 4
    grid = st.columns(_n_cols)
    for i, zone in enumerate(ZONES):
        row = ev_df[ev_df["zone"] == zone].iloc[0]
        bg = color_map.get(row["status"], color_map["No Data"])
        classes = "sefa-zone"
        if row["status"] == "Attention Required":
            classes += " zone-attention"
            if row.get("priority") == "High":
                classes += " zone-critical"
        elif row["status"] == "Monitor":
            classes += " zone-monitor"

        spark = _sparkline_svg(zone)

        with grid[i % _n_cols]:
            st.markdown(f"""
                <div class="{classes}" style="background:{bg}">
                    <b>{zone}</b>
                    {spark}<br>
                    💧 {row['moisture']}%<br>
                    🌡 {row['temperature']}°C<br>
                    🤖 {t_prediction(row['prediction'])}<br>
                    <small>{t_status(row['status'])}</small>
                </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="sefa-legend" style="margin-top:16px">
            <span>{t('status_normal')}</span>
            <span>{t('status_monitor')}</span>
            <span>{t('status_attention')}</span>
            <span>{t('status_no_data')}</span>
        </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"<h3>{icons.icon_droplet()} {t('moisture_heatmap')}</h3>",
                unsafe_allow_html=True)
    pivot = ev_df.pivot_table(index="zone", values="moisture",
                              aggfunc="mean").reset_index()
    pivot["row"] = pivot["zone"].str[0]
    pivot["col"] = pivot["zone"].str[1].astype(int)
    heat = pivot.pivot(index="row", columns="col", values="moisture")
    heat = heat.reindex(index=ROWS, columns=COLS)

    fig = px.imshow(
        heat, text_auto=True, aspect="auto",
        color_continuous_scale=[
            [0.00, "#ffe6e6"], [0.25, "#ffe0b2"], [0.50, "#c8e6c9"],
            [0.75, "#66bb6a"], [1.00, "#00695c"],
        ],
        zmin=0, zmax=100,
        labels=dict(color=t("moisture") + " %"),
    )
    fig.update_layout(height=340 if st.session_state["_is_mobile"] else 420,
                      margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    mobile_bottom_nav("map")


# =========================================================
# PAGE: ALERTS
# =========================================================
elif page == t("page_alerts"):
    st.markdown(f"<h3>{icons.icon_alert()} {t('alerts_title')}</h3>",
                unsafe_allow_html=True)

    alerts = recent_alerts(limit=50)
    if not alerts:
        st.info(t("no_alerts"))
    else:
        adf = pd.DataFrame(alerts)
        adf["timestamp"] = pd.to_datetime(adf["timestamp"])

        if st.session_state["_is_mobile"]:
            c1, c2 = st.columns(2)
            c1.metric(t("total_alerts"), len(adf))
            c2.metric(t("high_severity"),
                      int((adf["severity"] == "High").sum()))
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric(t("total_alerts"), len(adf))
            c2.metric(t("high_severity"),
                      int((adf["severity"] == "High").sum()))
            c3.metric(t("zones_affected"), adf["zone"].nunique())

        sev_filter = st.multiselect(
            t("filter_severity"),
            ["High", "Medium", "Low"],
            default=["High", "Medium", "Low"],
            format_func=t_severity,
        )
        filtered = adf[adf["severity"].isin(sev_filter)].copy()
        filtered["alert_type"] = filtered["alert_type"].map(t_alert_type)
        filtered["severity"]   = filtered["severity"].map(t_severity)
        filtered["message"]    = filtered["message"].map(translate_message)

        st.dataframe(
            filtered[["timestamp", "zone", "alert_type",
                      "severity", "message"]],
            use_container_width=True, hide_index=True,
        )

    mobile_bottom_nav("")


# =========================================================
# PAGE: AI MONITORING
# =========================================================
elif page == t("page_ai"):
    st.markdown(f"<h3>{icons.icon_camera()} {t('ai_title')}</h3>",
                unsafe_allow_html=True)

    ai_df = ev_df[ev_df["prediction"] != "—"].copy()

    if ai_df.empty:
        st.info(t("no_ai"))
    else:
        if st.session_state["_is_mobile"]:
            c1, c2 = st.columns(2)
            c1.metric(t("zones_analysed"), len(ai_df))
            c2.metric(t("flagged"),
                      int((ai_df["prediction"] != "Healthy").sum()))
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric(t("zones_analysed"), len(ai_df))
            c2.metric(t("pred_healthy"),
                      int((ai_df["prediction"] == "Healthy").sum()))
            c3.metric(t("flagged"),
                      int((ai_df["prediction"] != "Healthy").sum()))

        st.divider()
        st.markdown(f"<h3>{icons.icon_camera()} {t('zone_predictions')}</h3>",
                    unsafe_allow_html=True)

        ai_disp = ai_df.copy()
        ai_disp["prediction"]     = ai_disp["prediction"].map(t_prediction)
        ai_disp["status"]         = ai_disp["status"].map(t_status)
        ai_disp["recommendation"] = ai_disp["recommendation"].map(translate_recommendation)
        st.dataframe(
            ai_disp[["zone", "prediction", "confidence",
                     "status", "recommendation"]].sort_values("zone"),
            use_container_width=True, hide_index=True,
        )

        st.divider()
        if st.session_state["_is_mobile"]:
            counts = ai_df["prediction"].value_counts().reset_index()
            counts.columns = ["Prediction", "Count"]
            counts["Prediction"] = counts["Prediction"].map(t_prediction)
            fig = px.pie(
                counts, names="Prediction", values="Count",
                hole=0.55,
                color_discrete_sequence=[
                    "#00a651", "#4caf50", "#7bd39c", "#ff9800", "#dc3545",
                ],
            )
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            left, right = st.columns(2)
            with left:
                counts = ai_df["prediction"].value_counts().reset_index()
                counts.columns = ["Prediction", "Count"]
                counts["Prediction"] = counts["Prediction"].map(t_prediction)
                fig = px.pie(
                    counts, names="Prediction", values="Count",
                    hole=0.55,
                    color_discrete_sequence=[
                        "#00a651", "#4caf50", "#7bd39c", "#ff9800", "#dc3545",
                    ],
                )
                fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
            with right:
                fig = px.bar(
                    ai_df.sort_values("confidence"),
                    x="confidence", y="zone", orientation="h",
                    color="confidence",
                    color_continuous_scale=[
                        [0.0, "#dc3545"], [0.5, "#ff9800"], [1.0, "#00a651"],
                    ],
                    labels={"confidence": t("confidence") + " %", "zone": t("zone")},
                )
                fig.update_layout(height=360, showlegend=False,
                                  coloraxis_showscale=False,
                                  margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)

    mobile_bottom_nav("")


# =========================================================
# PAGE: CAMERA
# =========================================================
elif page == t("page_camera"):
    st.markdown(f"<h3>{icons.icon_camera()} {t('camera_title')}</h3>",
                unsafe_allow_html=True)

    cam_mode = st.radio(
        "Source",
        ["📡 ESP32 Live", "🎥 Device Webcam", "🖼 Mock"],
        horizontal=True,
        index=0,
        key="camera_mode_pick",
    )

    cam_zone = st.selectbox(
        t("camera_zone"),
        ZONES,
        index=ZONES.index("B3") if "B3" in ZONES else 0,
        key="camera_zone_pick",
    )

    if cam_mode == "📡 ESP32 Live":
        cam_url = st.text_input(
            "ESP32-CAM URL",
            value=st.session_state["camera_url"],
            key="cam_url_input",
        )
        st.session_state["camera_url"] = cam_url.rstrip("/")

    st.divider()

    if cam_mode == "📡 ESP32 Live":
        stream_url = f"{st.session_state['camera_url']}/stream"
        capture_url = f"{st.session_state['camera_url']}/capture"
        st.markdown(f"**{t('camera_live')} — ESP32-S3-CAM**")

        components.html(f"""
        <div style="
            border-radius:14px;
            border:1px solid rgba(0,166,81,0.3);
            overflow:hidden;
            background:#000;
            position:relative;
        ">
            <img src="{stream_url}"
                 style="width:100%;display:block;"
                 onerror="this.parentNode.innerHTML='<div style=&quot;padding:40px;text-align:center;color:#ff5252;font-family:monospace&quot;>Cannot reach ESP32-CAM<br><br>{stream_url}</div>'">
            <div style="
                position:absolute;top:12px;left:12px;
                background:rgba(220,53,69,0.9);
                color:#fff;padding:4px 10px;border-radius:6px;
                font-family:monospace;font-size:11px;
                letter-spacing:0.1em;font-weight:600;
            ">● LIVE</div>
        </div>
        """, height=400 if st.session_state["_is_mobile"] else 500)

        if st.button("📸 Capture Frame",
                     type="primary", use_container_width=True,
                     key="esp32_snap"):
            import urllib.request
            try:
                with urllib.request.urlopen(capture_url, timeout=5) as resp:
                    img_bytes = resp.read()
                pred, conf = simulate_ai(img_bytes, cam_zone)
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                save_capture(cam_zone, img_b64, pred, conf,
                             note="ESP32 live capture")
                st.success(t("camera_saved", zone=cam_zone))
                st.rerun()
            except Exception as e:
                st.error(f"Capture failed: {e}")

    elif cam_mode == "🎥 Device Webcam":
        cam_file = st.camera_input(t("camera_capture"), key="webcam_input")
        if cam_file is not None:
            img_bytes = cam_file.getvalue()
            pred, conf = simulate_ai(img_bytes, cam_zone)
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            save_capture(cam_zone, img_b64, pred, conf, note="Webcam capture")
            st.success(t("camera_saved", zone=cam_zone))

    else:  # Mock
        if st.button(t("camera_capture"), type="primary",
                     use_container_width=True, key="mock_cap"):
            pred, conf = simulate_ai(b"MOCK", cam_zone)
            save_capture(cam_zone, None, pred, conf, note="Mock capture")
            st.success(t("camera_saved", zone=cam_zone))
            st.rerun()

    st.divider()
    st.markdown(f"**{t('camera_result')}**")
    recent = recent_camera_captures(limit=1, zone=cam_zone)
    if recent:
        cap = recent[0]
        pred = cap["prediction"]
        conf = cap["confidence"] or 0
        if pred == "Healthy":
            card_color = "#00a651"
            card_bg = "rgba(0,166,81,0.08)"
        elif pred == "Crop Stress":
            card_color = "#ff9800"
            card_bg = "rgba(255,152,0,0.08)"
        else:
            card_color = "#dc3545"
            card_bg = "rgba(220,53,69,0.08)"

        st.markdown(f"""
        <div style="background:{card_bg}; border:2px solid {card_color};
                    border-radius:14px; padding:20px; text-align:center;">
            <div style="font-size:11px;letter-spacing:0.15em;
                        text-transform:uppercase;color:var(--text-mute);
                        font-weight:600">{t('camera_predicted')}</div>
            <div style="font-size:26px;font-weight:600;margin-top:8px;
                        color:{card_color}">{t_prediction(pred)}</div>
            <div style="font-size:12px;color:var(--text-soft);margin-top:8px">
                {t('camera_confidence')}: <b>{conf}%</b>
            </div>
            <div style="font-size:11px;color:var(--text-mute);margin-top:8px">
                {cap['zone']} · {cap['timestamp'][11:19]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        img_b64 = get_capture_image(cap["id"])
        if img_b64:
            try:
                st.image(base64.b64decode(img_b64),
                         caption=f"{cap['zone']} · {cap['timestamp'][11:19]}",
                         use_container_width=True)
            except Exception:
                pass
    else:
        st.info("No captures yet for this zone.")

    st.divider()
    st.markdown(f"<h3>{icons.icon_camera()} {t('camera_history')}</h3>",
                unsafe_allow_html=True)

    captures = recent_camera_captures(limit=12)
    if not captures:
        st.info(t("camera_no_history"))
    else:
        _n_cols = 3 if st.session_state["_is_mobile"] else 6
        cols = st.columns(_n_cols)
        for i, cap in enumerate(captures):
            pred = cap["prediction"]
            conf = cap["confidence"] or 0
            if pred == "Healthy":
                border = "#00a651"
            elif pred == "Crop Stress":
                border = "#ff9800"
            else:
                border = "#dc3545"

            with cols[i % _n_cols]:
                st.markdown(f"""
                <div style="background:var(--surface);
                            border:1px solid {border};
                            border-radius:10px; padding:8px;
                            text-align:center; margin-bottom:8px;">
                    <div style="font-size:11px;font-weight:600;
                                color:var(--accent)">{cap['zone']}</div>
                    <div style="font-size:10px;color:var(--text-soft);
                                margin-top:4px;line-height:1.3">
                        {t_prediction(pred)}<br>
                        <span style="color:{border};font-weight:500">
                            {conf:.0f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    mobile_bottom_nav("camera")


# =========================================================
# PAGE: TRENDS
# =========================================================
elif page == t("page_trends"):
    st.markdown(f"<h3>{icons.icon_chart()} {t('trends_title')}</h3>",
                unsafe_allow_html=True)

    zone = st.selectbox(t("select_zone"), ZONES, index=ZONES.index("B2"))
    rows = history_for_zone(zone, limit=300)

    if not rows:
        st.info(t("no_history"))
    else:
        hdf = pd.DataFrame(rows)
        hdf["timestamp"] = pd.to_datetime(hdf["timestamp"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hdf["timestamp"], y=hdf["moisture"],
            name=t("moisture") + " %", mode="lines+markers",
            line=dict(color="#00a651", width=2), marker=dict(size=4),
        ))
        fig.add_trace(go.Scatter(
            x=hdf["timestamp"], y=hdf["temperature"],
            name=t("temperature") + " °C", mode="lines+markers",
            yaxis="y2", line=dict(color="#ff9800", width=2),
            marker=dict(size=4),
        ))
        fig.update_layout(
            yaxis=dict(title=t("moisture") + " %"),
            yaxis2=dict(title=t("temperature") + " °C",
                        overlaying="y", side="right"),
            legend=dict(orientation="h"),
            height=340 if st.session_state["_is_mobile"] else 420,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric(t("avg_moisture"), f"{hdf['moisture'].mean():.1f}%")
        c2.metric(t("avg_temp"), f"{hdf['temperature'].mean():.1f}°C")

    mobile_bottom_nav("")


# =========================================================
# PAGE: WEATHER
# =========================================================
elif page == t("page_weather"):
    st.markdown(f"<h3>{icons.icon_cloud()} {t('weather_title')}</h3>",
                unsafe_allow_html=True)

    current  = get_current_cached()
    forecast = get_forecast_cached()

    if not current or "error" in current:
        st.warning(t("weather_error"))
    else:
        desc_en, icon = describe_weather(current.get("weather_code"))
        desc = t_weather_condition(desc_en)

        if st.session_state["_is_mobile"]:
            c1, c2 = st.columns(2)
            c1.metric(f"{icon} {t('weather_temp')}",
                      f"{current.get('temperature','—')}°C")
            c2.metric(f"💧 {t('weather_humidity')}",
                      f"{current.get('humidity','—')}%")
            c3, c4 = st.columns(2)
            c3.metric(f"🌬 {t('weather_wind')}",
                      f"{current.get('wind','—')} km/h")
            c4.metric(f"🌧 {t('weather_rain')}",
                      f"{current.get('precipitation',0):.1f}mm")
            st.metric(f"🌤 {t('weather_condition')}", desc)
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(f"{icon} {t('weather_temp')}",
                      f"{current.get('temperature','—')} °C")
            c2.metric(f"💧 {t('weather_humidity')}",
                      f"{current.get('humidity','—')} %")
            c3.metric(f"🌬 {t('weather_wind')}",
                      f"{current.get('wind','—')} km/h")
            c4.metric(f"🌧 {t('weather_rain')}",
                      f"{current.get('precipitation',0):.1f} mm")
            c5.metric(f"🌤 {t('weather_condition')}", desc)

        st.divider()
        st.markdown(f"<h3>{icons.icon_cloud()} {t('weather_advisor')}</h3>",
                    unsafe_allow_html=True)
        advice = irrigation_advice(forecast)
        if advice["skip_irrigation"]:
            st.success(f"{t('weather_skip')} — {advice['reason']}")
        else:
            st.info(f"{t('weather_proceed')} — {advice['reason']}")

        st.divider()
        st.markdown(f"<h3>{icons.icon_cloud()} {t('weather_forecast')}</h3>",
                    unsafe_allow_html=True)

        if forecast:
            fdf = pd.DataFrame(forecast)
            fdf["date"] = pd.to_datetime(fdf["date"]).dt.strftime("%a %d")
            fdf["condition"] = fdf["weather_code"].apply(
                lambda c: f"{describe_weather(c)[1]} "
                          f"{t_weather_condition(describe_weather(c)[0])}"
            )
            display = fdf[["date", "condition", "temp_max", "temp_min",
                           "rain_mm", "rain_prob"]].copy()
            display.columns = [
                t("weather_today"), t("weather_condition"),
                f"{t('weather_max')} °C", f"{t('weather_min')} °C",
                f"{t('weather_rain')} (mm)", t("weather_rain_prob") + " %",
            ]
            st.dataframe(display, use_container_width=True, hide_index=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=fdf["date"], y=fdf["rain_mm"],
                name=t("weather_rain") + " (mm)",
                marker_color="#4caf50", yaxis="y2",
            ))
            fig.add_trace(go.Scatter(
                x=fdf["date"], y=fdf["temp_max"],
                name=t("weather_max") + " °C", mode="lines+markers",
                line=dict(color="#ff9800", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=fdf["date"], y=fdf["temp_min"],
                name=t("weather_min") + " °C", mode="lines+markers",
                line=dict(color="#00a651", width=2),
            ))
            fig.update_layout(
                height=340 if st.session_state["_is_mobile"] else 380,
                yaxis=dict(title="°C"),
                yaxis2=dict(title="mm", overlaying="y", side="right"),
                legend=dict(orientation="h"),
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    mobile_bottom_nav("weather")


# =========================================================
# PAGE: ANALYTICS
# =========================================================
elif page == t("page_analytics"):
    st.markdown(f"<h3>{icons.icon_activity()} {t('analytics_title')}</h3>",
                unsafe_allow_html=True)

    normal, monitor, attention, avg_m = field_summary(evaluated)
    total = len(evaluated)
    dry = int((ev_df["moisture"] < THRESHOLDS["moisture_dry"]).sum())
    optimal = total - dry

    if st.session_state["_is_mobile"]:
        c1, c2 = st.columns(2)
        c1.metric(t("zones_optimal"), f"{optimal}/{total}")
        c2.metric(t("avg_moisture"), f"{avg_m}%")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("water_saved"),
                  f"{round(35 * (optimal / total), 1) if total else 0}%")
        c2.metric(t("labour_saved"), "40%")
        c3.metric(t("zones_optimal"), f"{optimal}/{total}")
        c4.metric(t("avg_moisture"), f"{avg_m}%")

    st.divider()
    labels = [t("status_normal"), t("status_monitor"), t("status_attention")]
    values = [normal, monitor, attention]
    fig = px.bar(
        x=labels, y=values, color=labels,
        color_discrete_map={
            t("status_normal"):    "#00a651",
            t("status_monitor"):   "#ff9800",
            t("status_attention"): "#dc3545",
        },
    )
    fig.update_layout(height=300, showlegend=False,
                      margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    mobile_bottom_nav("")


# =========================================================
# PAGE: IRRIGATION
# =========================================================
elif page == t("page_irrigation"):
    st.markdown(f"<h3>{icons.icon_droplet()} {t('irrigation_title').replace('💧','').strip()}</h3>",
                unsafe_allow_html=True)

    total_zones = len(evaluated)
    dry_zones = [z for z in evaluated
                 if z["moisture"] is not None
                 and z["moisture"] < THRESHOLDS["moisture_dry"]]
    wet_zones = [z for z in evaluated
                 if z["moisture"] is not None
                 and z["moisture"] > THRESHOLDS["moisture_wet"]]

    if st.session_state["_is_mobile"]:
        c1, c2 = st.columns(2)
        c1.metric(t("zones_need_water"), len(dry_zones))
        c2.metric(t("zones_overwatered"), len(wet_zones))
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("zones_monitored"), total_zones)
        c2.metric(t("zones_need_water"), len(dry_zones))
        c3.metric(t("zones_overwatered"), len(wet_zones))
        avg_val = (sum(z["moisture"] for z in evaluated
                       if z["moisture"] is not None) / total_zones
                   if total_zones else 0)
        c4.metric(t("avg_moisture"), f"{avg_val:.1f}%")

    try:
        _forecast = get_forecast_cached()
        _advice   = irrigation_advice(_forecast)
        if _advice["skip_irrigation"]:
            st.warning(f"🌦 {t('weather_skip')} — {_advice['reason']}")
        else:
            st.info(f"🌦 {t('weather_proceed')} — {_advice['reason']}")
    except Exception:
        pass

    st.divider()
    st.markdown(f"<h3>{icons.icon_droplet()} {t('zone_recommendation')}</h3>",
                unsafe_allow_html=True)

    irrig_rows = []
    for z in sorted(evaluated, key=lambda x: x["zone"]):
        m = z["moisture"]
        if m is None:
            continue
        if m < THRESHOLDS["moisture_dry"]:
            rec, color = t("irr_irrigate_now"), "#dc3545"
        elif m < THRESHOLDS["moisture_dry"] + 10:
            rec, color = t("irr_monitor"), "#ff9800"
        elif m > THRESHOLDS["moisture_wet"]:
            rec, color = t("irr_stop"), "#0288d1"
        else:
            rec, color = t("irr_no_action"), "#00a651"

        irrig_rows.append({
            t("zone"): z["zone"],
            t("moisture") + " %": m,
            t("temperature") + " °C": z["temperature"],
            "AI " + t("status"): t_prediction(z["prediction"]),
            t("recommendation"): rec,
            "_color": color,
        })

    irr_df = pd.DataFrame(irrig_rows)

    def _color_row(row):
        c = row.get("_color", "#0d3b1e")
        return [f"background-color: {c}15; color: {c}; font-weight: 500"] * len(row)

    styled = irr_df.style.apply(_color_row, axis=1).hide(axis="columns", subset=["_color"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown(f"<h3>{icons.icon_droplet()} {t('manual_valve')}</h3>",
                unsafe_allow_html=True)

    with st.form("irrigation_form", clear_on_submit=True):
        zone_pick = st.selectbox(t("zone"), ZONES, key="irrig_zone")
        action = st.radio(t("action"),
                          [t("start_irrigation"), t("stop_irrigation_action")],
                          horizontal=True)
        duration = st.number_input(t("duration"), min_value=0, max_value=3600,
                                   value=300, step=30)
        note = st.text_input(t("note"), placeholder="")
        submitted = st.form_submit_button(t("apply"),
                                          use_container_width=True, type="primary")
    if submitted:
        act = "started" if action == t("start_irrigation") else "stopped"
        dur = int(duration) if act == "started" else None
        log_irrigation(zone_pick, act, dur, note)
        st.success(t("irrigation_logged", zone=zone_pick, action=action))
        st.rerun()

    mobile_bottom_nav("irrigation")


# =========================================================
# Footer
# =========================================================
st.divider()
st.caption(t("footer"))

if auto:
    time.sleep(10)
    st.rerun()