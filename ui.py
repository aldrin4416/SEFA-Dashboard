"""SEFA – Reusable UI components (travel-app style)."""

import streamlit as st
from config import FARMER_NAME


# =========================================================
# Greeting header
# =========================================================
def greeting_header(subtitle="Your field is doing well"):
    """Top greeting block with avatar. Reads name fresh each render."""
    from config import get_farmer_name
    name = get_farmer_name()
    initial = name.strip()[0].upper() if name.strip() else "K"

    st.html(f"""
    <div class="sefa-header">
        <div class="sefa-header-text">
            <div class="sefa-hello">Hi, {name} 👋</div>
            <div class="sefa-sub">{subtitle}</div>
        </div>
        <div class="sefa-avatar">{initial}</div>
    </div>
    """)


# =========================================================
# Search bar (decorative)
# =========================================================
def search_bar(placeholder="Search zones..."):
    st.html(f"""
    <div class="sefa-search">
        <span class="sefa-search-icon">🔍</span>
        <span class="sefa-search-text">{placeholder}</span>
    </div>
    """)


# =========================================================
# Section header
# =========================================================
def section_header(title, action="View all"):
    st.html(f"""
    <div class="sefa-section">
        <div class="sefa-section-title">{title}</div>
        <div class="sefa-section-action">{action} →</div>
    </div>
    """)


# =========================================================
# Filter chips
# =========================================================
def filter_chips(options, active, key="chip_filter"):
    """Horizontal row of pill chips. Returns selected value."""
    from streamlit import session_state as ss

    if key not in ss:
        ss[key] = active

    chips_html = ""
    for opt in options:
        cls = "active" if ss[key] == opt else ""
        chips_html += f'<div class="sefa-chip {cls}" data-val="{opt}">{opt}</div>'

    st.html(f'<div class="sefa-chip-row">{chips_html}</div>')

    # Below: invisible radio to capture selection via Streamlit (styled off)
    selection = st.radio(
        "filter", options,
        index=options.index(ss[key]),
        key=key + "_radio",
        label_visibility="collapsed",
    )
    ss[key] = selection
    return selection


# =========================================================
# Hero card (travel-app style big image card)
# =========================================================
def hero_card(title, value, subtitle, badge="", accent="#00a676",
              gradient=("135deg", "#0f5132", "#00a676")):
    """Large hero card with gradient background."""
    badge_html = (
        f'<div class="sefa-hero-badge">{badge}</div>' if badge else ""
    )
    st.html(f"""
    <div class="sefa-hero-card" style="
        background: linear-gradient({gradient[0]},
            {gradient[1]} 0%, {gradient[2]} 100%);
    ">
        <div class="sefa-hero-overlay"></div>
        <div class="sefa-hero-content">
            <div class="sefa-hero-title">{title}</div>
            <div class="sefa-hero-value" style="color:{accent}">{value}</div>
            <div class="sefa-hero-sub">{subtitle}</div>
        </div>
        {badge_html}
    </div>
    """)


# =========================================================
# Zone card (small horizontal-scroll card)
# =========================================================
def zone_card(zone, status, moisture, accent="#00a676"):
    """Small zone summary card."""
    tint_map = {
        "Normal":             "#0f2b17",
        "Monitor":            "#2b2410",
        "Attention Required": "#2b1010",
        "No Data":            "#1a1a1a",
    }
    bg = tint_map.get(status, "#1a1a1a")
    st.html(f"""
    <div class="sefa-zone-card" style="background:{bg}">
        <div class="sefa-zone-name">{zone}</div>
        <div class="sefa-zone-status">{status}</div>
        <div class="sefa-zone-moist" style="color:{accent}">{moisture}%</div>
    </div>
    """)


# =========================================================
# Stat tile (KPI row)
# =========================================================
def stat_tile(icon, label, value, tint="#00a676"):
    """Small rounded KPI tile."""
    st.html(f"""
    <div class="sefa-stat-tile">
        <div class="sefa-stat-icon" style="color:{tint}">{icon}</div>
        <div class="sefa-stat-value">{value}</div>
        <div class="sefa-stat-label">{label}</div>
    </div>
    """)


# =========================================================
# Alert row (travel-app list style)
# =========================================================
def alert_row(icon, title, subtitle, time_text, color="#dc3545"):
    st.html(f"""
    <div class="sefa-alert-row">
        <div class="sefa-alert-icon" style="color:{color}">{icon}</div>
        <div class="sefa-alert-body">
            <div class="sefa-alert-title">{title}</div>
            <div class="sefa-alert-sub">{subtitle}</div>
        </div>
        <div class="sefa-alert-time">{time_text}</div>
    </div>
    """)

TAB_SVG = {
    "home": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 10.5 12 3l9 7.5"/>'
        '<path d="M5 9.5V21h14V9.5"/>'
        '</svg>'
    ),
    "field": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 22V10"/>'
        '<path d="M12 10c-2-3-5-4-8-4 0 3 1 6 4 8"/>'
        '<path d="M12 10c2-3 5-4 8-4 0 3-1 6-4 8"/>'
        '</svg>'
    ),
    "camera": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 8a2 2 0 0 1 2-2h3l2-2h4l2 2h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8Z"/>'
        '<circle cx="12" cy="13" r="3.2"/>'
        '</svg>'
    ),
    "insights": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 20h18"/>'
        '<path d="M6 16v-4"/>'
        '<path d="M11 16V8"/>'
        '<path d="M16 16v-6"/>'
        '<path d="M21 16V5"/>'
        '</svg>'
    ),
}
# =========================================================
# Bottom tab bar
# =========================================================
def bottom_tab_bar(active_tab):
    """Fixed bottom bar with 4 tabs. SVG icons."""
    from config import TABS

    items = ""
    for key, label, _emoji in TABS:
        cls = "active" if key == active_tab else ""
        icon_svg = TAB_SVG.get(key, "")
        items += f"""
        <a class="sefa-tab-item {cls}"
           href="?tab={key}"
           aria-label="{label}">
            <span class="sefa-tab-icon">{icon_svg}</span>
            <span class="sefa-tab-label">{label}</span>
        </a>
        """

    st.html(f"""
    <div class="sefa-tab-bar">
        {items}
    </div>
    """)

# =========================================================
# Bottom sheet (full-screen detail view)
# =========================================================
def detail_sheet_header(title, subtitle, back_label="Back"):
    """Header for the detail view."""
    st.html(f"""
    <div class="sefa-sheet-header">
        <a class="sefa-sheet-back" href="?tab=field">‹ {back_label}</a>
        <div class="sefa-sheet-title">{title}</div>
        <div class="sefa-sheet-sub">{subtitle}</div>
    </div>
    """)


# =========================================================
# Metric row (detail view — 3 inline metrics)
# =========================================================
def metric_row(items):
    """items = [(icon, label, value), ...] up to 3."""
    cells = ""
    for icon, label, value in items[:3]:
        cells += f"""
        <div class="sefa-metric-cell">
            <div class="sefa-metric-icon">{icon} {label}</div>
            <div class="sefa-metric-val">{value}</div>
        </div>
        """
    st.html(f'<div class="sefa-metric-row">{cells}</div>')