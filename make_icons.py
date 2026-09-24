"""Generate SEFA app icons — run once."""
from PIL import Image, ImageDraw
import os


def make_icon(size, path):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 12
    radius = size // 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius, fill=(0, 166, 81, 255),
    )
    cx, cy = size // 2, size // 2
    lw, lh = size // 3, size // 2
    draw.polygon([
        (cx, cy - lh // 2),
        (cx + lw // 2, cy),
        (cx, cy + lh // 2),
        (cx - lw // 2, cy),
    ], fill=(255, 255, 255, 245))
    draw.line(
        [(cx, cy + lh // 2 - 6), (cx, cy + lh // 2 + 12)],
        fill=(255, 255, 255, 245),
        width=max(3, size // 50),
    )
    draw.line(
        [(cx, cy - lh // 2 + 8), (cx, cy + lh // 2 - 8)],
        fill=(0, 166, 81, 120),
        width=max(1, size // 80),
    )
    img.save(path, "PNG")
    print(f"OK  {path}")


if __name__ == "__main__":
    os.makedirs(".streamlit/static", exist_ok=True)
    make_icon(192, ".streamlit/static/icon-192.png")
    make_icon(512, ".streamlit/static/icon-512.png")
    print("Done.")