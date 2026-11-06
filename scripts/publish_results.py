#!/usr/bin/env python3
"""Create review drafts only from verified issuer releases and material developments.

SEC filings are not story sources. Editors add a verified entry to
data/verified-releases.json after locating the issuer's actual release.
"""
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
RELEASES_PATH = ROOT / "data" / "verified-releases.json"
STATE_PATH = ROOT / "data" / "drafted-releases.json"
COMPANY_GRAPHICS_BASE = "https://mediajobsreport.github.io/mjr-financial-calendar/generated-assets/company-graphics"
ET = ZoneInfo("America/New_York")
API_URL = "https://www.mediajobsreport.com/api/v2/data_posts/create"
AUTHOR_ID = "110"
NEWS_ARTICLE_ID = "15"
SINGLE_IMAGE_DATA_TYPE = "20"


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def valid_release_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and bool(host)
        and host not in {"sec.gov", "www.sec.gov", "edgar.sec.gov"}
        and not host.endswith(".sec.gov")
        and "/edgar/" not in parsed.path.casefold()
    )


def validate(record: dict) -> list[str]:
    errors = []
    required = ("id", "company", "ticker", "story_type", "headline", "summary", "release_url", "release_date")
    for key in required:
        if not str(record.get(key, "")).strip():
            errors.append(f"missing {key}")
    if record.get("story_type") not in {"earnings_results", "major_development"}:
        errors.append("story_type must be earnings_results or major_development")
    if record.get("status") != "verified":
        errors.append("status must be verified")
    if record.get("release_url") and not valid_release_url(record["release_url"]):
        errors.append("release_url must link directly to a non-SEC issuer release")
    if record.get("highlights") is not None and not isinstance(record["highlights"], list):
        errors.append("highlights must be a list")
    if len(str(record.get("headline", ""))) > 180:
        errors.append("headline exceeds 180 characters")
    if len(str(record.get("summary", ""))) < 45:
        errors.append("summary must provide substantive story context")
    if not str(record.get("ticker", "")).strip():
        errors.append("ticker is required for the company graphic")
    return errors


def graphic_url(ticker: str) -> str:
    return COMPANY_GRAPHICS_BASE + "/" + urllib.parse.quote(ticker.upper()) + ".png"


def story_content(record: dict) -> str:
    company = html.escape(record["company"])
    release_url = html.escape(record["release_url"], quote=True)
    date = dt.date.fromisoformat(record["release_date"]).strftime("%B %-d, %Y")
    summary = html.escape(record["summary"])
    parts = [f"<p>{summary}</p>"]
    highlights = [str(item).strip() for item in record.get("highlights", []) if str(item).strip()]
    if highlights:
        parts.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in highlights) + "</ul>")
    parts.append(
        f'<p>{company} issued the release on {date}. '
        f'<a href="{release_url}" rel="noopener">Read the full company press release</a>.</p>'
    )
    parts.append(
        '<p>See the <a href="https://www.mediajobsreport.com/financial-calendar" '
        'rel="noopener">MJR Financial Calendar</a> for upcoming reporting dates.</p>'
    )
    return "".join(parts)


def create_draft(record: dict, api_key: str) -> int:
    payload = {
        "user_id": AUTHOR_ID,
        "data_id": NEWS_ARTICLE_ID,
        "data_type": SINGLE_IMAGE_DATA_TYPE,
        "post_title": record["headline"][:180],
        "post_caption": record["summary"],
        "post_content": story_content(record),
        "post_status": "0",
        "post_image": graphic_url(record["ticker"]),
        "auto_image_import": "1",
        "post_org_url": record["release_url"],
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
        raise RuntimeError(f"BD API returned HTTP {exc.code}; verified release was not marked drafted.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"BD API connection failed: {exc.reason}") from None
    message = result.get("message", {})
    if result.get("status") != "success" or not isinstance(message, dict) or not message.get("post_id"):
        raise RuntimeError("BD API did not confirm draft creation; verified release was not marked drafted.")
    return int(message["post_id"])


def main() -> int:
    releases = read_json(RELEASES_PATH, [])
    if not isinstance(releases, list):
        raise ValueError("data/verified-releases.json must contain a JSON list.")

    state = read_json(STATE_PATH, {"drafted": []})
    drafted = state.get("drafted", [])
    drafted_ids = {str(item.get("id")) for item in drafted}
    eligible = []
    for record in releases:
        if not isinstance(record, dict):
            print("Skipping invalid release record: expected an object.", file=sys.stderr)
            continue
        errors = validate(record)
        if errors:
            print(f"Skipping {record.get('id', '(no id)')}: {', '.join(errors)}", file=sys.stderr)
            continue
        if str(record["id"]) in drafted_ids:
            continue
        eligible.append(record)

    if not eligible:
        print("No new verified issuer releases or major developments to draft. SEC filings alone create no stories.")
        return 0

    api_key = os.environ.get("BD_API_KEY", "").strip()
    if not api_key:
        print("BD_API_KEY is missing; no drafts were created.", file=sys.stderr)
        return 1

    for record in eligible:
        post_id = create_draft(record, api_key)
        drafted.append({
            "id": str(record["id"]),
            "company": record["company"],
            "ticker": record["ticker"],
            "story_type": record["story_type"],
            "release_url": record["release_url"],
            "post_id": post_id,
            "drafted_at": dt.datetime.now(ET).isoformat(timespec="seconds"),
        })
        drafted_ids.add(str(record["id"]))
        write_json(STATE_PATH, {"drafted": drafted})
        print(f"Created unpublished {record['story_type']} draft for {record['ticker']} (post {post_id}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
