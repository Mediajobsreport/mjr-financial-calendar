#!/usr/bin/env python3
"""Generate reusable 1200x640 company-specific MJR finance story graphics."""
from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
COMPANIES_PATH = ROOT / "data" / "companies.json"
OUTPUT_DIR = ROOT / "generated-assets" / "company-graphics"
WIDTH, HEIGHT = 1200, 640
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Editorial accent colors chosen to make each card recognizable at a glance.
# These graphics use company names and tickers, not recreated corporate logos.
ACCENTS = {
    "AMCX": "#E45D45", "BBGI": "#00A5D9", "CMCSA": "#1676D2",
    "CURI": "#35B6C8", "DJCO": "#C9A96E", "DIS": "#6A78D1",
    "SSP": "#E25E57", "EVC": "#E94B62", "FOXA": "#3B8DC4",
    "FUBO": "#E94B67", "GHC": "#D1AD68", "GTN": "#E99B4B",
    "IHRT": "#D12B83", "LEE": "#E2AA54", "LION": "#D84646",
    "MDIA": "#A858D2", "NFLX": "#E50914", "NYT": "#E4E6EB",
    "NWSA": "#D14F55", "NMAX": "#D43D47", "NXST": "#4B9BDC",
    "PSKY": "#56A9E6", "PPLI": "#6ABF70", "RSVR": "#D68A9B",
    "ROKU": "#8C5EE8", "RUM": "#65B969", "SGA": "#D9B56D",
    "SBGI": "#5D91E2", "SIRI": "#E64C60", "SONY": "#EAECEF",
    "SPOT": "#1ED760", "STRZ": "#9671DF", "TME": "#48B981",
    "TSQ": "#55A8E1", "UONE": "#D7B55C", "TDAY": "#EF5A56",
    "WBD": "#A36BE0", "WMG": "#E9E9EC", "PAAI": "#7E7BEA",
}
SECTOR_LABELS = {
    "Broadcast & Local": "BROADCAST & LOCAL MEDIA",
    "News & Publishing": "NEWS & PUBLISHING",
    "TV & Streaming": "TELEVISION & STREAMING",
    "Music & Audio": "MUSIC & AUDIO",
}

def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)

def wrap_to_width(draw: ImageDraw.ImageDraw, text: str, max_width: int, face) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines

def draw_gradient(img: Image.Image, accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(img)
    left = (13, 24, 43)
    right = (23, 34, 56)
    for x in range(WIDTH):
        t = x / (WIDTH - 1)
        r = int(left[0] * (1-t) + right[0] * t)
        g = int(left[1] * (1-t) + right[1] * t)
        b = int(left[2] * (1-t) + right[2] * t)
        draw.line((x, 0, x, HEIGHT), fill=(r, g, b))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = 1000, 270
    for radius in range(440, 40, -8):
        alpha = int(2 + 17 * (1 - radius / 440))
        gd.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                   fill=(*accent, alpha))
    img.alpha_composite(glow)

def draw_motif(draw: ImageDraw.ImageDraw, sector: str, accent: tuple[int, int, int]) -> None:
    color = (*accent, 150)
    if sector == "Broadcast & Local":
        for radius in (90, 155, 220):
            draw.arc((875-radius, 115-radius, 875+radius, 115+radius),
                     210, 330, fill=color, width=5)
        draw.ellipse((864, 104, 886, 126), fill=(*accent, 210))
    elif sector == "Music & Audio":
        heights = [48, 86, 132, 74, 164, 112, 58, 126, 92, 42, 108]
        x0 = 840
        for i, h in enumerate(heights):
            x = x0 + i * 23
            draw.rounded_rectangle((x, 275-h//2, x+10, 275+h//2),
                                   radius=5, fill=(*accent, 115))
    elif sector == "News & Publishing":
        for i, w in enumerate((300, 245, 285, 205)):
            y = 176 + i*44
            draw.rounded_rectangle((830, y, 830+w, y+8), radius=4,
                                   fill=(*accent, 120))
        draw.rounded_rectangle((830, 144, 865, 158), radius=5,
                               fill=(*accent, 170))
    else:
        draw.rounded_rectangle((845, 135, 1105, 315), radius=26,
                               outline=(*accent, 145), width=5)
        draw.polygon(((950, 185), (950, 265), (1020, 225)),
                     fill=(*accent, 175))
        draw.rounded_rectangle((1040, 184, 1075, 267), radius=8,
                               fill=(*accent, 110))

def render(company: dict) -> Path:
    ticker = str(company["ticker"]).strip().upper()
    name = str(company["name"]).strip()
    sector = str(company.get("sector", "TV & Streaming")).strip()
    hex_color = ACCENTS.get(ticker, "#62A4DC").lstrip("#")
    accent = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    img = Image.new("RGBA", (WIDTH, HEIGHT), (13, 24, 43, 255))
    draw_gradient(img, accent)
    draw = ImageDraw.Draw(img, "RGBA")

    # Layered bands add movement while leaving a quiet text-safe area.
    draw.polygon(((770, 0), (1200, 0), (1200, 640), (1030, 640)),
                 fill=(255, 255, 255, 8))
    draw.polygon(((1040, 0), (1200, 0), (1200, 640), (1175, 640)),
                 fill=(*accent, 24))
    draw_motif(draw, sector, accent)

    # Oversized ticker creates a distinct, reusable watermark for this company.
    ticker_face = font(FONT_BOLD, 158)
    ticker_box = draw.textbbox((0, 0), ticker, font=ticker_face)
    ticker_width = ticker_box[2] - ticker_box[0]
    ticker_x = max(760, WIDTH - ticker_width - 72)
    draw.text((ticker_x, 424), ticker, font=ticker_face,
              fill=(255, 255, 255, 28), stroke_width=1,
              stroke_fill=(*accent, 42))

    # Small editorial label and accent rule.
    draw.rounded_rectangle((66, 54, 310, 96), radius=21,
                           fill=(*accent, 255))
    draw.text((88, 65), "MJR FINANCIAL COVERAGE", font=font(FONT_BOLD, 16),
              fill=(10, 20, 36, 255))
    draw.rounded_rectangle((66, 127, 151, 135), radius=4,
                           fill=(*accent, 255))

    # Company name, sized and wrapped to fit the left half cleanly.
    max_text_width = 725
    name_size = 72
    while name_size > 48:
        name_face = font(FONT_BOLD, name_size)
        lines = wrap_to_width(draw, name, max_text_width, name_face)
        if len(lines) <= 2:
            break
        name_size -= 2
    line_height = name_size + 15
    name_y = 183
    for line in lines:
        draw.text((66, name_y), line, font=name_face, fill=(250, 252, 255, 255))
        name_y += line_height

    # Ticker badge and sector line.
    badge_y = name_y + 21
    ticker_face_small = font(FONT_BOLD, 28)
    ticker_box = draw.textbbox((0, 0), ticker, font=ticker_face_small)
    badge_w = ticker_box[2] + 54
    draw.rounded_rectangle((66, badge_y, 66+badge_w, badge_y+58), radius=13,
                           fill=(*accent, 255))
    draw.text((92, badge_y+11), ticker, font=ticker_face_small,
              fill=(9, 20, 36, 255))
    draw.text((66, badge_y+83), SECTOR_LABELS.get(sector, sector.upper()),
              font=font(FONT_BOLD, 19), fill=(216, 225, 238, 255))

    # Footer keeps the illustration reusable for different quarters and story types.
    draw.line((66, 564, 1134, 564), fill=(255, 255, 255, 48), width=2)
    draw.text((66, 585), "EARNINGS  •  INVESTOR CALLS  •  COMPANY NEWS",
              font=font(FONT_REGULAR, 17), fill=(193, 205, 221, 255))
    draw.text((1018, 583), "1200 × 640", font=font(FONT_BOLD, 14),
              fill=(150, 164, 184, 220))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"{ticker}.webp"
    img.convert("RGB").save(target, "WEBP", quality=93, method=6)
    return target

def main() -> None:
    companies = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
    if not companies:
        raise SystemExit("No companies found in data/companies.json")
    for company in companies:
        path = render(company)
        print(f"Generated {path.relative_to(ROOT)}")
    print(f"Generated {len(companies)} company graphics.")

if __name__ == "__main__":
    main()
