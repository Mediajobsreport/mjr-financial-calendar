#!/usr/bin/env python3
"""Generate editorial 1200x640 SVG graphics for the MJR financial company directory."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPANIES_PATH = ROOT / "data" / "companies.json"
OUTPUT_DIR = ROOT / "generated-assets" / "company-graphics"
WIDTH, HEIGHT = 1200, 640

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

def esc(value: object) -> str:
    return html.escape(str(value), quote=True)

def wrap_name(name: str, max_chars: int = 25) -> list[str]:
    words = name.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:2] or [name]

def motif(sector: str, accent: str) -> str:
    if sector == "Broadcast & Local":
        return f'<g fill="none" stroke="{accent}" stroke-width="8" opacity=".58"><path d="M855 290a110 110 0 0 1 220 0"/><path d="M815 290a150 150 0 0 1 300 0"/><path d="M775 290a190 190 0 0 1 380 0"/></g><circle cx="965" cy="290" r="14" fill="{accent}" opacity=".8"/>'
    if sector == "Music & Audio":
        heights = [55, 95, 142, 78, 172, 118, 64, 134, 98, 48, 112]
        bars = []
        for i, height in enumerate(heights):
            x = 810 + i * 28
            bars.append(f'<rect x="{x}" y="{280-height/2:.0f}" width="12" height="{height}" rx="6" fill="{accent}" opacity=".5"/>')
        return "".join(bars)
    if sector == "News & Publishing":
        return f'<g fill="{accent}" opacity=".45"><rect x="820" y="165" width="42" height="22" rx="6"/><rect x="820" y="210" width="315" height="10" rx="5"/><rect x="820" y="245" width="270" height="10" rx="5"/><rect x="820" y="280" width="300" height="10" rx="5"/><rect x="820" y="315" width="220" height="10" rx="5"/></g>'
    return f'<g stroke="{accent}" stroke-width="7" fill="none" opacity=".55"><rect x="820" y="155" width="300" height="205" rx="28"/><path d="M930 205l95 53-95 54z" fill="{accent}" stroke="none" opacity=".7"/><rect x="1048" y="205" width="32" height="105" rx="9" fill="{accent}" stroke="none" opacity=".55"/></g>'

def render(company: dict) -> Path:
    ticker = str(company["ticker"]).strip().upper()
    name = str(company["name"]).strip()
    sector = str(company.get("sector", "TV & Streaming")).strip()
    accent = ACCENTS.get(ticker, "#62A4DC")
    lines = wrap_name(name)
    title_size = 70 if len(lines[0]) <= 19 else 58
    title_y = 250 if len(lines) == 1 else 215
    title = "".join(
        f'<text x="68" y="{title_y + i * (title_size + 14)}" class="title" font-size="{title_size}px">{esc(line)}</text>'
        for i, line in enumerate(lines)
    )
    sector_label = SECTOR_LABELS.get(sector, sector.upper())
    graphic = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{esc(name)} ({esc(ticker)}) — MJR Financial Coverage</title>
<desc id="desc">A reusable 1200 by 640 editorial graphic for {esc(name)} company news and financial reports.</desc>
<defs>
  <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#0d182b"/><stop offset="1" stop-color="#172238"/></linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="{accent}" stop-opacity=".26"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
  <style>.title{{font-family:Arial,Helvetica,sans-serif;font-weight:700;letter-spacing:-2px;fill:#fafcff}}.label{{font-family:Arial,Helvetica,sans-serif;font-weight:700}}</style>
</defs>
<rect width="1200" height="640" fill="url(#bg)"/>
<ellipse cx="960" cy="260" rx="390" ry="350" fill="url(#glow)"/>
<path d="M770 0h430v640h-170z" fill="#fff" opacity=".025"/>
<path d="M1040 0h160v640h-25z" fill="{accent}" opacity=".075"/>
{motif(sector, accent)}
<text x="1160" y="530" text-anchor="end" class="label" font-size="150px" fill="#fff" opacity=".07">{esc(ticker)}</text>
<rect x="66" y="54" width="252" height="44" rx="22" fill="{accent}"/>
<text x="88" y="82" class="label" font-size="16px" letter-spacing="1" fill="#0a1424">MJR FINANCIAL COVERAGE</text>
<rect x="66" y="127" width="86" height="8" rx="4" fill="{accent}"/>
{title}
<rect x="66" y="388" width="135" height="58" rx="13" fill="{accent}"/>
<text x="133.5" y="426" text-anchor="middle" class="label" font-size="28px" fill="#091424">{esc(ticker)}</text>
<text x="66" y="486" class="label" font-size="19px" letter-spacing="1.4" fill="#d8e1ee">{esc(sector_label)}</text>
<path d="M66 564H1134" stroke="#fff" stroke-opacity=".18" stroke-width="2"/>
<text x="66" y="600" font-family="Arial,Helvetica,sans-serif" font-size="17px" letter-spacing=".4" fill="#c1cddd">EARNINGS  •  INVESTOR CALLS  •  COMPANY NEWS</text>
<text x="1134" y="600" text-anchor="end" class="label" font-size="14px" fill="#96a4b8">1200 × 640</text>
</svg>
'''
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"{ticker}.svg"
    target.write_text(graphic, encoding="utf-8")
    return target

def main() -> None:
    companies = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
    if not companies:
        raise SystemExit("No companies found in data/companies.json")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    expected = set()
    for company in companies:
        path = render(company)
        expected.add(path.name)
        print(f"Generated {path.relative_to(ROOT)}")
    for stale in OUTPUT_DIR.glob("*.svg"):
        if stale.name not in expected:
            stale.unlink()
    print(f"Generated {len(companies)} company graphics ({WIDTH}x{HEIGHT}).")

if __name__ == "__main__":
    main()
