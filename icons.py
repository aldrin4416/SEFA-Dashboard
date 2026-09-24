"""SEFA – Inline SVG icons.

Each icon is a small SVG string. Sizes and colors are inherited via CSS
(width, height, fill: currentColor). Drop into any HTML string.
"""

def _svg(path, viewbox="0 0 24 24", size=18, stroke=True):
    stroke_attrs = (
        'stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round" fill="none"'
        if stroke else 'fill="currentColor"'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{viewbox}" width="{size}" height="{size}" '
        f'{stroke_attrs} style="vertical-align:-2px">{path}</svg>'
    )


def icon_leaf(size=18):
    return _svg(
        '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 '
        '2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>'
        '<path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
        size=size
    )


def icon_home(size=18):
    return _svg(
        '<path d="M3 10.5 12 3l9 7.5"/>'
        '<path d="M5 9.5V21h14V9.5"/>',
        size=size
    )


def icon_map(size=18):
    return _svg(
        '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6z"/>'
        '<path d="M9 3v15"/>'
        '<path d="M15 6v15"/>',
        size=size
    )


def icon_alert(size=18):
    return _svg(
        '<path d="M12 9v4"/>'
        '<circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>'
        '<path d="M10.3 3.6 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z"/>',
        size=size
    )


def icon_camera(size=18):
    return _svg(
        '<path d="M3 8a2 2 0 0 1 2-2h3l2-2h4l2 2h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8Z"/>'
        '<circle cx="12" cy="13" r="3.2"/>',
        size=size
    )


def icon_chart(size=18):
    return _svg(
        '<path d="M3 20h18"/>'
        '<path d="M6 16v-4"/>'
        '<path d="M11 16V8"/>'
        '<path d="M16 16v-6"/>'
        '<path d="M21 16V5"/>',
        size=size
    )


def icon_cloud(size=18):
    return _svg(
        '<path d="M17 18a4 4 0 0 0 .6-7.96A6 6 0 0 0 6.2 10 4 4 0 0 0 7 18h10Z"/>'
        '<path d="M8 21h8"/>',
        size=size
    )


def icon_droplet(size=18):
    return _svg(
        '<path d="M12 2.5s6 6.5 6 12a6 6 0 1 1-12 0c0-5.5 6-12 6-12Z"/>',
        size=size
    )


def icon_activity(size=18):
    return _svg(
        '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
        size=size
    )


def icon_sun(size=18):
    return _svg(
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
        size=size
    )


def icon_moon(size=18):
    return _svg(
        '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
        size=size
    )


def icon_battery(size=18):
    return _svg(
        '<rect x="2" y="8" width="17" height="8" rx="2"/>'
        '<path d="M22 11v2"/>'
        '<rect x="4" y="10" width="10" height="4" fill="currentColor" stroke="none"/>',
        size=size
    )


def icon_signal(size=18):
    return _svg(
        '<path d="M4 20v-3"/><path d="M9 20v-7"/>'
        '<path d="M14 20v-11"/><path d="M19 20V5"/>',
        size=size
    )


def icon_clock(size=18):
    return _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 7v5l3 2"/>',
        size=size
    )