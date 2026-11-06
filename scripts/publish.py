#!/usr/bin/env python3
"""Create review drafts for confirmed quarterly and major financial announcements."""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "published-events.json"
EVENTS_PATH = ROOT / "data" / "events.json"
COMPANIES_PATH = ROOT / "data" / "companies.json"
COMPANY_GRAPHICS_BASE = "https://mediajobsreport.github.io/mjr-financial-calendar/generated-assets/company-graphics"
ET = ZoneInfo("America/New_York")
API_URL = "https://www.mediajobsreport.com/api/v2/data_posts/create"
MJR_LOGO = "https://www.mediajobsreport.com/images/Social-Profile-Pic-2-Media-Jobs-Report-Social-Media-Icon.png"
# Confirmed in the MJR admin: Media Jobs Report author #110, News Article post type #15.
AUTHOR_ID = "110"
NEWS_ARTICLE_ID = "15"
# Brilliant Directories' Single Image Posts data type, as defined in its API example.
SINGLE_IMAGE_DATA_TYPE = "20"
LOOKAHEAD_DAYS = 14
DAILY_POST_LIMIT = 2


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def valid_https(url: str | None) -> bool:
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def company_graphic_url(event: dict) -> str:
    companies = read_json(COMPANIES_PATH, [])
    by_name = {
        "".join(ch for ch in company.get("name", "").casefold() if ch.isalnum()): company.get("ticker", "").upper()
        for company in companies
    }
    event_ticker = str(event.get("ticker", "")).strip().upper()
    key = "".join(ch for ch in str(event.get("company", "")).casefold() if ch.isalnum())
    ticker = event_ticker or by_name.get(key)
    if ticker:
        return COMPANY_GRAPHICS_BASE + "/" + urllib.parse.quote(ticker) + ".png"
    return ""


def period_label(event: dict) -> str:
    value = str(event.get("fiscal_period", "financial")).strip()
    match = re.search(r"Q([1-4])\s*(?:and\s*FY\s*)?(20\d{2})", value, re.I)
    if match:
        quarter = {"1": "First-Quarter", "2": "Second-Quarter", "3": "Third-Quarter", "4": "Fourth-Quarter"}[match.group(1)]
        if "FY" in value.upper():
            return f"{quarter} and Full-Year {match.group(2)}"
        return f"{quarter} {match.group(2)}"
    match = re.search(r"20\d{2}", value)
    if re.search(r"FY|full year|annual", value, re.I):
        return f"Full-Year {match.group(0)}" if match else "Full-Year"
    return value


def event_headline(event: dict) -> str:
    name = "Disney" if event["company"] == "The Walt Disney Company" else event["company"]
    period = period_label(event)
    date = dt.date.fromisoformat(event["date"]).strftime("%b %-d")
    kind = str(event.get("event_type", "")).casefold()
    if "webcast" in kind:
        return f"{name} to Host {period} Earnings Webcast {date}"
    return f"{name} to Report {period} Results {date}"


def qualifies_for_draft(event: dict) -> bool:
    period = str(event.get("fiscal_period", "")).casefold()
    details = " ".join((str(event.get("event_type", "")), str(event.get("title", "")))).casefold()
    quarterly_or_annual = bool(re.search(r"\bq[1-4]\b|quarter|fiscal year|full year|annual", period))
    earnings_related = "earning" in details or "financial result" in details
    return bool(event.get("major_announcement")) or (quarterly_or_annual and earnings_related)


def event_content(event: dict) -> str:
    company = html.escape(event["company"])
    date = dt.date.fromisoformat(event["date"]).strftime("%B %-d, %Y")
    fiscal_period = html.escape(period_label(event))
    timing = ""
    if event.get("time") and event.get("timezone"):
        timing = f" at {html.escape(event['time'])} {html.escape(event['timezone'])}"
    elif event.get("time"):
        timing = f" at {html.escape(event['time'])}"
    links = [("Official announcement", event["source_url"])]
    for label, key in (("Webcast", "webcast_url"), ("Financial reports", "report_url")):
        if valid_https(event.get(key)):
            links.append((label, event[key]))
    link_html = " &nbsp;|&nbsp; ".join(
        f'<a href="{html.escape(url, quote=True)}" rel="noopener">{html.escape(label)}</a>'
        for label, url in links
    )
    event_kind = html.escape(event.get("event_type", "earnings event"))
    headline = html.escape(event_headline(event))
    return (
        f"<p>{company} is scheduled to report {fiscal_period} results on {date}{timing}. "
        f"The {event_kind} is part of the company’s quarterly or annual financial reporting.</p>"
        f"<p>{headline}</p><p>{link_html}</p>"
        '<p>See the <a href="https://www.mediajobsreport.com/financial-calendar" '
        'rel="noopener">MJR Financial Calendar</a> for other confirmed media-company reporting dates.</p>'
    )


def publish(event: dict, api_key: str) -> int:
    title = event_headline(event)
    period = event.get("fiscal_period", "earnings")
    time_note = f" at {event['time']} {event.get('timezone', '')}".rstrip() if event.get("time") else ""
    caption = (
        f"{event['company']} is scheduled to report {period} on "
        f"{dt.date.fromisoformat(event['date']).strftime('%b %-d, %Y')}{time_note}."
    )
    payload = {
        "user_id": AUTHOR_ID,
        "data_id": NEWS_ARTICLE_ID,
        "data_type": SINGLE_IMAGE_DATA_TYPE,
        "post_title": title,
        "post_caption": caption,
        "post_content": event_content(event),
        "post_status": "0",
        "post_image": company_graphic_url(event),
        "auto_image_import": "1",
        "post_org_url": event["source_url"],
    }
    request = urllib.request.Request(
        API_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"X-Api-Key": api_key, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"BD API returned HTTP {exc.code}; no event was marked published.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"BD API connection failed: {exc.reason}") from None
    message = result.get("message", {})
    if result.get("status") != "success" or not isinstance(message, dict) or not message.get("post_id"):
        raise RuntimeError("BD API did not confirm post creation; no event was marked published.")
    return int(message["post_id"])


def main() -> int:
    api_key = os.environ.get("BD_API_KEY", "").strip()
    if not api_key:
        print("BD_API_KEY is missing; nothing was published.", file=sys.stderr)
        return 1

    now = dt.datetime.now(ET)
    today = now.date()
    state = read_json(STATE_PATH, {"published": []})
    published = state.get("published", [])
    published_sources = {item.get("source_url") for item in published}
    posted_today = sum(
        1 for item in published
        if item.get("published_at", "").startswith(today.isoformat())
    )
    if posted_today >= DAILY_POST_LIMIT:
        print(f"Daily publishing limit reached ({DAILY_POST_LIMIT}); no post created.")
        return 0

    events = read_json(EVENTS_PATH, [])
    eligible = []
    for event in events:
        if event.get("status") != "confirmed" or not event.get("source_url") or not qualifies_for_draft(event):
            continue
        if not valid_https(event.get("source_url")) or event["source_url"] in published_sources:
            continue
        if not company_graphic_url(event):
            print(f"No company graphic is available for {event.get('company')}; skipping draft.")
            continue
        try:
            report_date = dt.date.fromisoformat(event["date"])
            verified_date = dt.date.fromisoformat(event["verified_at"])
        except (KeyError, ValueError):
            continue
        if report_date < today or report_date > today + dt.timedelta(days=LOOKAHEAD_DAYS):
            continue
        if verified_date > today:
            continue
        eligible.append(event)

    eligible.sort(key=lambda event: (event["date"], event.get("time", ""), event["company"]))
    remaining = DAILY_POST_LIMIT - posted_today
    for event in eligible[:remaining]:
        post_id = publish(event, api_key)
        published.append({
            "source_url": event["source_url"],
            "company": event["company"],
            "post_id": post_id,
            "published_at": now.isoformat(timespec="seconds"),
        })
        published_sources.add(event["source_url"])
        print(f"Created approval draft for {event['company']} (post {post_id}).")

    STATE_PATH.write_text(json.dumps({"published": published}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not eligible:
        print("No new qualifying quarterly or major announcements within the 14-day draft window.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
