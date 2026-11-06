#!/usr/bin/env python3
"""Create review drafts for verified quarterly and annual financial results."""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "published-results.json"
COMPANIES_PATH = ROOT / "data" / "companies.json"
COMPANY_GRAPHICS_BASE = "https://mediajobsreport.github.io/mjr-financial-calendar/generated-assets/company-graphics"
ET = ZoneInfo("America/New_York")
API_URL = "https://www.mediajobsreport.com/api/v2/data_posts/create"
MJR_LOGO = "https://www.mediajobsreport.com/images/Social-Profile-Pic-2-Media-Jobs-Report-Social-Media-Icon.png"
AUTHOR_ID = "110"
NEWS_ARTICLE_ID = "15"
SINGLE_IMAGE_DATA_TYPE = "20"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "Media Jobs Report financial coverage jerry@mediajobsreport.com",
)
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK"
LOOKBACK_DAYS = 3
BLOCK_TAGS = {"address", "article", "br", "div", "h1", "h2", "h3", "h4", "li", "p", "section", "table", "tr"}


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif not self.hidden and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_lines(source: str) -> list[str]:
    parser = VisibleText()
    parser.feed(source)
    text = html.unescape("".join(parser.parts))
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def request_bytes(url: str, sec: bool = True) -> bytes:
    headers = {"User-Agent": SEC_USER_AGENT} if sec else {}
    headers["Accept"] = "application/json, text/html, */*"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()


def request_json(url: str):
    return json.loads(request_bytes(url).decode("utf-8"))


def archive_base(cik: int, accession: str) -> str:
    accession_path = accession.replace("-", "")
    return f"{SEC_ARCHIVES}/{cik}/{accession_path}"


def exhibit_url(cik: int, accession: str, primary_document: str) -> str:
    base = archive_base(cik, accession)
    try:
        index = request_json(base + "/index.json").get("directory", {}).get("item", [])
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        index = []

    exhibits = [item for item in index if str(item.get("type", "")).upper().startswith("EX-99")]
    exhibits.sort(key=lambda item: (
        0 if str(item.get("type", "")).upper() in {"EX-99.1", "EX-99.01"} else 1,
        0 if "press release" in str(item.get("description", "")).casefold() else 1,
        str(item.get("name", "")),
    ))
    if exhibits:
        name = exhibits[0].get("name") or exhibits[0].get("href")
        if name:
            return base + "/" + urllib.parse.quote(str(name))
    return base + "/" + urllib.parse.quote(primary_document)


def filing_text(url: str) -> tuple[str, list[str]]:
    raw = request_bytes(url)
    source = raw.decode("utf-8", errors="replace")
    return source, html_lines(source)


def is_results_release(lines: list[str]) -> bool:
    sample = " ".join(lines[:180]).casefold()
    has_results_term = bool(re.search(r"financial results|earnings results|quarterly results|results for the (three|six|nine|twelve|first|second|third|fourth|fiscal|quarter|year)|reports? (its )?(financial|quarterly|fiscal|third|fourth|first|second)", sample))
    is_future_notice = bool(re.search(r"to report (its )?(financial|quarterly|fiscal)|will report (its )?(financial|quarterly|fiscal)", sample))
    return has_results_term and not is_future_notice


def result_period(lines: list[str]) -> str:
    sample = " ".join(lines[:180])
    match = re.search(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter(?:\s+of)?\s+(20\d{2})\b", sample, re.I)
    if match:
        word = match.group(1).lower()
        quarter = {"first":"First-Quarter","second":"Second-Quarter","third":"Third-Quarter","fourth":"Fourth-Quarter",
                   "1st":"First-Quarter","2nd":"Second-Quarter","3rd":"Third-Quarter","4th":"Fourth-Quarter"}[word]
        return f"{quarter} {match.group(2)}"
    match = re.search(r"\bQ([1-4])\s*(20\d{2})\b", sample, re.I)
    if match:
        quarter = {"1":"First-Quarter","2":"Second-Quarter","3":"Third-Quarter","4":"Fourth-Quarter"}[match.group(1)]
        return f"{quarter} {match.group(2)}"
    match = re.search(r"(?:fiscal|full)\s+year\s+(20\d{2})", sample, re.I)
    if match:
        return f"Full-Year {match.group(1)}"
    return "Quarterly"


def release_headline(lines: list[str], company_name: str) -> str:
    generic = re.compile(r"press release issued|date of report|date of earliest event|financial results$|earnings release$", re.I)
    candidates = []
    for line in lines[:180]:
        candidate = re.sub(r"\s+", " ", line).strip(" •-–—")
        if not 24 <= len(candidate) <= 180 or generic.search(candidate):
            continue
        if re.search(r"\b(reports?|reported|results?|revenue|earnings|profit|income|ebitda)\b", candidate, re.I):
            candidates.append(candidate)
    company_key = re.sub(r"[^a-z0-9]", "", company_name.casefold())
    for candidate in candidates:
        candidate_key = re.sub(r"[^a-z0-9]", "", candidate.casefold())
        if company_key and company_key in candidate_key:
            headline = candidate.title() if candidate.isupper() else candidate
            headline = re.sub(r"\bQ([1-4])\b", lambda m: m.group(0).upper(), headline, flags=re.I)
            return headline[:180]
    return f"{company_name} Reports {result_period(lines)} Results"


def company_graphic_url(ticker: str) -> str:
    if ticker:
        return COMPANY_GRAPHICS_BASE + "/" + urllib.parse.quote(ticker.upper()) + ".png"
    return MJR_LOGO


def post_result(result: dict, api_key: str) -> int:
    company = html.escape(result["company"])
    title = html.escape(result["headline"])
    filing_date = dt.date.fromisoformat(result["filing_date"]).strftime("%B %-d, %Y")
    release_link = html.escape(result["release_url"], quote=True)
    filing_link = html.escape(result["filing_url"], quote=True)
    caption = (
        f"{result['company']} reported financial results in a filing dated "
        f"{dt.date.fromisoformat(result['filing_date']).strftime('%b %-d, %Y')}. "
        "Read the official release and SEC filing for the complete results."
    )
    content = (
        f"<p>{company} reported financial results on {filing_date}. "
        "The headline reflects the company’s release; the complete results and financial detail "
        "are available in the official linked materials.</p>"
        f'<p><a href="{release_link}" rel="noopener">Company earnings release</a>'
        f' &nbsp;|&nbsp; <a href="{filing_link}" rel="noopener">SEC filing</a></p>'
        '<p>See the <a href="https://www.mediajobsreport.com/financial-calendar" '
        'rel="noopener">MJR Financial Calendar</a> for upcoming reporting dates.</p>'
    )
    payload = {
        "user_id": AUTHOR_ID,
        "data_id": NEWS_ARTICLE_ID,
        "data_type": SINGLE_IMAGE_DATA_TYPE,
        "post_title": result["headline"][:180],
        "post_caption": caption,
        "post_content": content,
        "post_status": "0",
        "post_image": company_graphic_url(result["ticker"]),
        "auto_image_import": "1",
        "post_org_url": result["release_url"],
    }
    request = urllib.request.Request(
        API_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"X-Api-Key": api_key, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_json = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"BD API returned HTTP {exc.code}; results filing was not marked published.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"BD API connection failed: {exc.reason}") from None
    message = response_json.get("message", {})
    if response_json.get("status") != "success" or not isinstance(message, dict) or not message.get("post_id"):
        raise RuntimeError("BD API did not confirm results-post creation; filing was not marked published.")
    return int(message["post_id"])


def main() -> int:
    api_key = os.environ.get("BD_API_KEY", "").strip()
    if not api_key:
        print("BD_API_KEY is missing; no results posts were created.", file=sys.stderr)
        return 1

    today = dt.datetime.now(ET).date()
    first_date = today - dt.timedelta(days=LOOKBACK_DAYS)
    state = read_json(STATE_PATH, {"published": []})
    published = state.get("published", [])
    published_accessions = {item.get("accession") for item in published}

    companies = read_json(COMPANIES_PATH, [])
    try:
        ticker_data = request_json(SEC_TICKERS_URL)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        raise RuntimeError(f"Could not load SEC ticker map: {exc}") from None
    cik_by_ticker = {
        str(item.get("ticker", "")).upper(): int(item["cik_str"])
        for item in ticker_data.values()
        if item.get("ticker") and item.get("cik_str")
    }

    results = []
    for company in companies:
        ticker = str(company.get("ticker", "")).upper()
        cik = cik_by_ticker.get(ticker)
        if not cik:
            print(f"SEC ticker map has no CIK for {ticker}; skipping.")
            continue
        try:
            submissions = request_json(f"{SEC_SUBMISSIONS}{cik:010d}.json")
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
            print(f"Could not read SEC submissions for {ticker}: {exc}", file=sys.stderr)
            time.sleep(0.12)
            continue

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        for i, form in enumerate(forms):
            if form not in {"8-K", "6-K"}:
                continue
            accession = recent.get("accessionNumber", [""])[i]
            if not accession or accession in published_accessions:
                continue
            try:
                filed = dt.date.fromisoformat(recent.get("filingDate", [""])[i])
            except (IndexError, ValueError):
                continue
            if filed < first_date or filed > today:
                continue
            items = str(recent.get("items", [""] * len(forms))[i] or "")
            if form == "8-K" and "2.02" not in items:
                continue
            primary = recent.get("primaryDocument", [""])[i]
            if not primary:
                continue

            release_url = exhibit_url(cik, accession, primary)
            filing_url = f"{SEC_ARCHIVES}/{cik}/{accession.replace('-', '')}/{accession}-index.htm"
            try:
                source, lines = filing_text(release_url)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
                continue
            if form == "6-K" and not is_results_release(lines):
                continue
            if not lines:
                continue

            results.append({
                "company": company["name"],
                "ticker": ticker,
                "headline": release_headline(lines, company["name"]),
                "filing_date": filed.isoformat(),
                "form": form,
                "accession": accession,
                "release_url": release_url,
                "filing_url": filing_url,
            })
            time.sleep(0.12)

        time.sleep(0.12)

    results.sort(key=lambda item: (item["filing_date"], item["company"]))
    if not results:
        print("No new quarterly or annual earnings-result filings found in the three-day window.")
        return 0

    for result in results:
        post_id = post_result(result, api_key)
        published.append({
            "accession": result["accession"],
            "company": result["company"],
            "ticker": result["ticker"],
            "release_url": result["release_url"],
            "post_id": post_id,
            "published_at": dt.datetime.now(ET).isoformat(timespec="seconds"),
        })
        published_accessions.add(result["accession"])
        STATE_PATH.write_text(
            json.dumps({"published": published}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Created results approval draft for {result['ticker']} ({result['accession']}, post {post_id}).")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
