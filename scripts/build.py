import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
companies = json.loads((ROOT / "data/companies.json").read_text(encoding="utf-8"))
source_events = json.loads((ROOT / "data/events.json").read_text(encoding="utf-8"))
company_names = {company["name"] for company in companies}
events = []

for event in source_events:
    required = ("company", "title", "date", "source_url", "verified_at")
    if not all(event.get(key) for key in required):
        continue
    if event.get("status") != "confirmed" or event["company"] not in company_names:
        continue
    try:
        dt.date.fromisoformat(event["date"])
        dt.date.fromisoformat(event["verified_at"])
    except ValueError:
        continue
    if not event["source_url"].startswith("https://"):
        continue
    events.append(event)

events.sort(key=lambda event: (event["date"], event.get("time", ""), event["company"]))
output_path = ROOT / "calendar.json"
previous = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
updated = previous.get("updated_utc")
if previous.get("companies") != companies or previous.get("events") != events or not updated:
    updated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

calendar = {"updated_utc": updated, "companies": companies, "events": events}
output_path.write_text(json.dumps(calendar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Built calendar with {len(events)} confirmed events")
