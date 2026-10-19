"""Generate brand assets: logo SVG/PNG, favicon, social image, and report charts."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "static" / "img"
BUILD = ROOT / "build-assets"

BASALT = "#1F2A2E"
CINDER = "#A8432A"
PINE = "#2F5D50"
SUN = "#D9A441"
SAND = "#F4EEE4"
FONT_DIR = Path("/usr/share/fonts/opentype/inter")

# Mark geometry in a 100x100 box; shared by SVG and PNG so they always match.
BIG_PEAK = [(4, 84), (40, 22), (76, 84)]
CONE = [(38, 84), (60, 46), (72, 46), (96, 84)]
SUN_C, SUN_R = (78, 24), 9


def mark_svg(size=None):
    pts = lambda p: " ".join(f"{x},{y}" for x, y in p)
    attrs = f' width="{size}" height="{size}"' if size else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"{attrs} role="img" aria-label="Cinder Peaks mark">'
        f'<circle cx="{SUN_C[0]}" cy="{SUN_C[1]}" r="{SUN_R}" fill="{SUN}"/>'
        f'<polygon points="{pts(BIG_PEAK)}" fill="{BASALT}"/>'
        f'<polygon points="{pts(CONE)}" fill="{CINDER}"/>'
        f'<rect x="4" y="84" width="92" height="5" rx="1" fill="{PINE}"/></svg>'
    )


def font(weight, size):
    name = {"bold": "Inter-Bold.otf", "semi": "Inter-SemiBold.otf", "reg": "Inter-Regular.otf", "med": "Inter-Medium.otf"}[weight]
    return ImageFont.truetype(str(FONT_DIR / name), size)


def draw_mark(draw, ox, oy, scale):
    sx = lambda p: [(ox + x * scale, oy + y * scale) for x, y in p]
    cx, cy = SUN_C
    draw.ellipse([ox + (cx - SUN_R) * scale, oy + (cy - SUN_R) * scale, ox + (cx + SUN_R) * scale, oy + (cy + SUN_R) * scale], fill=SUN)
    draw.polygon(sx(BIG_PEAK), fill=BASALT)
    draw.polygon(sx(CONE), fill=CINDER)
    draw.rectangle([ox + 4 * scale, oy + 84 * scale, ox + 96 * scale, oy + 89 * scale], fill=PINE)


def logo_png(path, transparent=True):
    W, H = 1090, 300
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0 if transparent else 255))
    d = ImageDraw.Draw(img)
    draw_mark(d, 10, 20, 2.6)
    d.text((300, 52), "CINDER PEAKS", font=font("bold", 104), fill=BASALT)
    d.text((304, 178), "COMMUNITY FOUNDATION", font=font("semi", 52), fill=CINDER)
    img.save(path)


def favicon(path):
    img = Image.new("RGBA", (256, 256), SAND)
    d = ImageDraw.Draw(img)
    draw_mark(d, 20, 14, 2.16)
    img.save(path)
    img.resize((32, 32), Image.LANCZOS).save(path.with_name("favicon-32.png"))


def social_card(path):
    img = Image.new("RGB", (1200, 630), SAND)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 470, 1200, 630], fill=PINE)
    draw_mark(d, 80, 120, 3.0)
    d.text((420, 170), "Cinder Peaks", font=font("bold", 96), fill=BASALT)
    d.text((424, 290), "Community Foundation", font=font("semi", 56), fill=CINDER)
    d.text((80, 520), "Grants and giving for Coconino, Yavapai, Navajo & Apache counties, Arizona", font=font("med", 28), fill="white")
    img.save(path)


def bar_chart(path, rows, title, value_fmt):
    """Horizontal bar chart for the annual and impact reports."""
    W = 1800
    row_h = 74
    top = 130
    H = top + row_h * len(rows) + 40
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 30), title, font=font("bold", 46), fill=BASALT)
    label_w = 620
    maxv = max(v for _, v in rows)
    avail = W - label_w - 300
    for i, (label, v) in enumerate(rows):
        y = top + i * row_h
        d.text((40, y + 14), label, font=font("reg", 34), fill=BASALT)
        w = int(avail * v / maxv)
        d.rounded_rectangle([label_w, y + 10, label_w + w, y + row_h - 14], radius=8, fill=PINE if i % 2 == 0 else CINDER)
        d.text((label_w + w + 16, y + 14), value_fmt(v), font=font("semi", 34), fill=BASALT)
    img.save(path)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    (IMG / "logo-mark.svg").write_text(mark_svg())
    logo_png(BUILD / "logo-doc.png")
    favicon(IMG / "favicon.png")
    social_card(IMG / "social-card.png")
    k = lambda v: f"${v/1000:,.0f}K" if v < 1_000_000 else f"${v/1_000_000:.2f}M"
    bar_chart(BUILD / "chart-focus-2025.png", [
        ("Health & Human Services", 2150000), ("Education & Youth", 1580000), ("Arts & Culture", 1040000),
        ("Environment & Land", 860000), ("Civic & Economic Opportunity", 790000), ("Early Childhood", 455000),
        ("Animal Welfare", 330000), ("Indigenous Communities", 221000), ("Rapid Response & Resilience", 208000),
        ("LGBTQ+ Communities", 128000), ("Black Futures", 84000)], "2025 grants by focus area (all fund types)", k)
    bar_chart(BUILD / "chart-county-2025.png", [
        ("Coconino County", 3620000), ("Yavapai County", 2310000), ("Navajo County", 1040000),
        ("Apache County", 660000), ("Statewide and other Arizona", 216000)], "2025 grants by county served", k)
    bar_chart(BUILD / "chart-infant-ratio.png", [
        ("Apache County", 10.8), ("Navajo County", 7.5), ("Yavapai County", 4.7), ("Coconino County", 3.8)],
        "Infants and toddlers per licensed care slot, 2026", lambda v: f"{v:.1f}")


if __name__ == "__main__":
    main()
