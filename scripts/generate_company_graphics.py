#!/usr/bin/env python3
"""Generate editorial 1200x640 SVG graphics for the MJR financial company directory."""
from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COMPANIES_PATH = ROOT / "data" / "companies.json"
OUTPUT_DIR = ROOT / "generated-assets" / "company-graphics"
LOGO_CACHE_DIR = ROOT / "generated-assets" / "company-logos"
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
LOGO_URLS = {
    "AMCX": "https://seeklogo.com/images/A/amc-networks-logo-0B6DCEC226-seeklogo.com.png",
    "BBGI": "https://bbgi.com/wp-content/uploads/2023/09/Beasley-Media-Group-LLC_Logo-01.png",
    "CMCSA": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Comcast.svg/3840px-Comcast.svg.png",
    "CURI": "https://upload.wikimedia.org/wikipedia/commons/3/37/CuriosityStream.svg",
    "DJCO": "https://upload.wikimedia.org/wikipedia/commons/0/05/Daily_Journal_Corporation_logo.svg",
    "DIS": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/The_Walt_Disney_company_logo.svg/1280px-The_Walt_Disney_company_logo.svg.png",
    "SSP": "https://cdn.mos.cms.futurecdn.net/XbQBCvQ7NUDURkSCqLrvaK.jpg",
    "EVC": "https://s29.q4cdn.com/283296970/files/design/new/EVC_Purple.png",
    "FOXA": "https://static.wikia.nocookie.net/mako-movies/images/4/4c/2880px-FOX_wordmark.svg.png/revision/latest/scale-to-width-down/1200?cb=20190127012836",
    "FUBO": "https://ppc.land/content/images/size/w2000/2025/10/fubo.jpg",
    "GHC": "https://companieslogo.com/img/orig/GHC-3ff27dd7.png?t=1720244492",
    "GTN": "https://cloudfront-us-east-1.images.arcpublishing.com/gray/6MKDJS7TTFCXLNYYOBWOMQ5Y2Y.jpg",
    "IHRT": "https://companieslogo.com/img/orig/IHRT_BIG-8cdd2bdc.png?t=1688833504",
    "LEE": "https://assets.quadcitiesbusiness.com/2024/07/Lee-logo.jpg",
    "LION": "https://cinema39.com/cdn/shop/collections/lionsgate-studios28120.logowik.com.webp?v=1761699112",
    "MDIA": "https://companieslogo.com/img/orig/MDIA_BIG-fc8899f4.png?download=true&t=1757619760",
    "NFLX": "https://www.citypng.com/public/uploads/preview/-11594682142fapt8mnyud.png",
    "NYT": "https://upload.wikimedia.org/wikipedia/commons/0/0e/The_New_York_Times_Company_Logo.svg",
    "NWSA": "https://cdn.prod.website-files.com/68de9c28ee29c8b50967ec08/6911f26a5fe85964d2966596_News_Corp_%282013%E2%80%93present%29-Logo.wine-p-1080.png",
    "NMAX": "https://www.companieslogo.com/img/orig/NMAX_BIG-266fb015.png?download=true&t=1743588724",
    "NXST": "https://cdn.mos.cms.futurecdn.net/SNwEzqB4wFhkpeio2aRxPZ-970-75.png",
    "PSKY": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Paramount_Pictures_Logo_2025.svg/3840px-Paramount_Pictures_Logo_2025.svg.png",
    "PPLI": "https://logowik.com/content/uploads/images/people-inc2151.logowik.com.webp",
    "RSVR": "https://companieslogo.com/img/orig/RSVR-f0aed646.png?t=1668498066",
    "ROKU": "https://logospng.org/download/roku/logo-roku-2048.png",
    "RUM": "https://mma.prnewswire.com/media/1897922/Rumble_Logo.jpg?p=facebook",
    "SGA": "https://mma.prnewswire.com/media/197361/saga_communications_logo.jpg?p=facebook",
    "SBGI": "https://sbgicdntest.z13.web.core.windows.net/Careers/Corporate/Home/sinclairblklogo.png",
    "SIRI": "https://mmx.prnewswire.com/media/MS1960335/SiriusXM-Logo.jpg?id=OA2799095&p=facebook",
    "SONY": "https://www.citypng.com/public/uploads/preview/hd-sony-black-logo-transparent-png-701751694773079o9p4y1cy4c.png?v=2026031811",
    "SPOT": "https://www.citypng.com/public/uploads/preview/logo-of-spotify-music-app-png-image-1166193987184wgya4gur.png",
    "STRZ": "https://cdn.prod.website-files.com/66b2141a9bb474b60eaef76d/66b604465b1f49f05642b0ee_watch-starz-outside-us.jpg",
    "TME": "https://wdwkmusic.com/assets/img/stories/index-stories-tencent.jpg",
    "TSQ": "https://companieslogo.com/img/orig/TSQ_BIG-a03a06be.png?t=1720244494",
    "UONE": "https://aimmgrowthfronts.com/wp-content/uploads/2024/02/U1_BLK.jpg",
    "TDAY": "https://upload.wikimedia.org/wikipedia/commons/3/3e/USA_Today_Co._Logo.svg",
    "WBD": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Warner_Bros._Discovery.svg/3840px-Warner_Bros._Discovery.svg.png",
    "WMG": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Warner_Music_Group_logo_%282021%29.svg/3840px-Warner_Music_Group_logo_%282021%29.svg.png",
}

SECTOR_LABELS = {
    "Broadcast & Local": "BROADCAST & LOCAL MEDIA",
    "News & Publishing": "NEWS & PUBLISHING",
    "TV & Streaming": "TELEVISION & STREAMING",
    "Music & Audio": "MUSIC & AUDIO",
}

def logo_data_uri(ticker: str) -> str | None:
    """Fetch and cache a company logo, returning an embedded data URI."""
    url = LOGO_URLS.get(ticker)
    if not url:
        return None

    import hashlib
    source_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    LOGO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = next(LOGO_CACHE_DIR.glob(f"{ticker}-{source_key}.*"), None)
    if cached:
        suffix = cached.suffix.lower()
        media_type = mimetypes.types_map.get(suffix, "application/octet-stream")
        if suffix == ".svg":
            media_type = "image/svg+xml"
        return f"data:{media_type};base64,{base64.b64encode(cached.read_bytes()).decode('ascii')}"

    request = Request(url, headers={"User-Agent": "MJR Financial Calendar/1.0 (mediajobsreport.com)"})
    try:
        with urlopen(request, timeout=35) as response:
            payload = response.read()
            media_type = response.headers.get_content_type().lower()
    except Exception as exc:
        print(f"Warning: could not cache {ticker} logo ({exc}); using its source URL.")
        return url

    if not payload:
        raise RuntimeError(f"Empty logo response for {ticker}: {url}")
    if media_type == "text/html" or media_type.startswith("text/"):
        head = payload[:4096].lstrip().lower()
        if b"<svg" in head:
            media_type = "image/svg+xml"
        else:
            raise RuntimeError(f"Logo source returned {media_type} for {ticker}: {url}")

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
        "image/avif": ".avif",
    }.get(media_type)
    if not ext:
        raise RuntimeError(f"Unsupported logo format {media_type} for {ticker}: {url}")

    # Reject unexpected HTML error pages mislabeled as images.
    sample = payload[:256].lstrip().lower()
    if ext != ".svg" and (sample.startswith(b"<!doctype html") or sample.startswith(b"<html")):
        raise RuntimeError(f"Logo source returned an HTML page for {ticker}: {url}")

    cached = LOGO_CACHE_DIR / f"{ticker}-{source_key}{ext}"
    cached.write_bytes(payload)
    return f"data:{media_type};base64,{base64.b64encode(payload).decode('ascii')}"

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
<rect x="790" y="144" width="350" height="230" rx="24" fill="#ffffff"/>
{(f'<image href="{esc(logo_data_uri(ticker) or '')}" x="812" y="157" width="306" height="204" preserveAspectRatio="xMidYMid meet"/>' if ticker in LOGO_URLS else f'<text x="965" y="266" text-anchor="middle" font-family="Georgia,serif" font-size="48px" fill="#111">Paradium.AI</text>')}
<text x="1160" y="530" text-anchor="end" class="label" font-size="150px" fill="#fff" opacity=".07">{esc(ticker)}</text>
<rect x="66" y="54" width="310" height="44" rx="22" fill="{accent}"/>
<text x="84" y="82" class="label" font-size="15px" letter-spacing=".5" fill="#0a1424">MJR FINANCIAL COVERAGE</text>
<rect x="66" y="127" width="86" height="8" rx="4" fill="{accent}"/>
{title}
<rect x="66" y="388" width="135" height="58" rx="13" fill="{accent}"/>
<text x="133.5" y="426" text-anchor="middle" class="label" font-size="28px" fill="#091424">{esc(ticker)}</text>
<text x="66" y="486" class="label" font-size="19px" letter-spacing="1.4" fill="#d8e1ee">{esc(sector_label)}</text>
<path d="M66 564H1134" stroke="#fff" stroke-opacity=".18" stroke-width="2"/>
<text x="66" y="600" font-family="Arial,Helvetica,sans-serif" font-size="17px" letter-spacing=".4" fill="#c1cddd">EARNINGS  •  INVESTOR CALLS  •  COMPANY NEWS</text>
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
