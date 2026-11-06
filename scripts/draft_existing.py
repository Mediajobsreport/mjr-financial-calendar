#!/usr/bin/env python3
"""Move automatically posted financial notices into review drafts with editorial headlines and graphics."""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import publish
import publish_results

ROOT = Path(__file__).resolve().parents[1]
EVENTS_STATE = ROOT / "data" / "published-events.json"
RESULTS_STATE = ROOT / "data" / "published-results.json"
MIGRATED_STATE = ROOT / "data" / "drafted-existing.json"
API_URL = "https://www.mediajobsreport.com/api/v2/data_posts/update"
AUTHOR_ID = "110"
NEWS_ARTICLE_ID = "15"
SINGLE_IMAGE_DATA_TYPE = "20"


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(state):
    MIGRATED_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def request_update(post_id: int, title: str, caption: str, content: str, graphic_url: str, api_key: str):
    payload = {
        "post_id": str(post_id),
        "user_id": AUTHOR_ID,
        "data_id": NEWS_ARTICLE_ID,
        "data_type": SINGLE_IMAGE_DATA_TYPE,
        "post_title": title[:180],
        "post_caption": caption,
        "post_content": content,
        "post_status": "0",
        "post_image": graphic_url,
        "auto_image_import": "1",
    }
    request = urllib.request.Request(
        API_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"X-Api-Key": api_key, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"BD API returned HTTP {exc.code} while saving post {post_id}: {body}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"BD API connection failed while saving post {post_id}: {exc.reason}") from None
    message = result.get("message", {})
    if result.get("status") != "success" or not isinstance(message, dict):
        raise RuntimeError(f"BD API did not confirm the draft update for post {post_id}.")


def result_content(record, title, release_date):
    company = html.escape(record["company"])
    release_url = html.escape(record["release_url"], quote=True)
    accession = record.get("accession", "").replace("-", "")
    match = re.search(r"/edgar/data/(\d+)/", record["release_url"])
    filing_link = ""
    if match and accession:
        filing_link = f"https://www.sec.gov/Archives/edgar/data/{match.group(1)}/{accession}/{record['accession']}-index.htm"
    links = [f'<a href="{release_url}" rel="noopener">Company earnings release</a>']
    if filing_link:
        links.append(f'<a href="{html.escape(filing_link, quote=True)}" rel="noopener">SEC filing</a>')
    return (
        f"<p>{company} reported financial results in a release dated {release_date}.</p>"
        f"<p>{html.escape(title)}.</p>"
        f"<p>{' &nbsp;|&nbsp; '.join(links)}</p>"
        '<p>See the <a href="https://www.mediajobsreport.com/financial-calendar" '
        'rel="noopener">MJR Financial Calendar</a> for upcoming reporting dates.</p>'
    )


def main():
    api_key = os.environ.get("BD_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("BD_API_KEY is missing; no existing stories were changed.")
    migrated = read_json(MIGRATED_STATE, {"post_ids": []})
    done = set(int(value) for value in migrated.get("post_ids", []))
    event_records = read_json(EVENTS_STATE, {"published": []}).get("published", [])
    result_records = read_json(RESULTS_STATE, {"published": []}).get("published", [])
    events_by_source = {
        item.get("source_url"): item
        for item in read_json(ROOT / "data" / "events.json", [])
    }

    for record in event_records:
        post_id = int(record.get("post_id", 0))
        if not post_id or post_id in done:
            continue
        event = events_by_source.get(record.get("source_url"))
        if event:
            title = publish.event_headline(event)
            caption = f"{event['company']} has an upcoming or recent {event.get('fiscal_period', 'earnings')} report."
            content = publish.event_content(event)
            image = publish.company_graphic_url(event)
        else:
            title = f"{record.get('company', 'Media Company')} Earnings Announcement"
            caption = title
            content = "<p>Financial announcement. Source details should be reviewed before approval.</p>"
            image = ""
        request_update(post_id, title, caption, content, image, api_key)
        done.add(post_id)
        write_state({"post_ids": sorted(done)})
        print(f"Moved existing financial announcement {post_id} to draft.")

    for record in result_records:
        post_id = int(record.get("post_id", 0))
        if not post_id or post_id in done:
            continue
        try:
            _, lines = publish_results.filing_text(record["release_url"])
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            lines = []
        title = publish_results.release_headline(lines, record.get("company", "Media Company"))
        release_date = str(record.get("published_at", ""))[:10]
        if release_date:
            try:
                release_date = dt.date.fromisoformat(release_date).strftime("%B %-d, %Y")
            except ValueError:
                pass
        caption = f"{record.get('company', 'Media company')} reports {publish_results.result_period(lines)} financial results."
        image = publish_results.company_graphic_url(record.get("ticker", ""))
        content = result_content(record, title, release_date or "recently")
        request_update(post_id, title, caption, content, image, api_key)
        done.add(post_id)
        write_state({"post_ids": sorted(done)})
        print(f"Moved existing financial results story {post_id} to draft.")

    print(f"Prepared {len(done)} existing financial posts as review drafts.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
