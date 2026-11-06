# MJR Media Financial Calendar

A small, responsive calendar for confirmed earnings releases, investor calls and financial reports from media companies. It is designed to be hosted as a static page and embedded in a Media Jobs Report page.

## Current setup

- `data/companies.json` holds company names, sectors, tickers and investor-relations links.
- `data/events.json` holds confirmed events and their company-source links.
- `scripts/build.py` validates event records and produces `calendar.json` for the page.
- GitHub Actions rebuilds the data on a six-hour schedule, deploys the static calendar to GitHub Pages, and creates eligible MJR News Article drafts using the repository secret `BD_API_KEY`.
- The page provides search and stock-category filters; its collapsed, searchable company directory covers all 39 tickers from MJR stock reports with company, investor-relations and quote links. Event cards link to announcements, webcasts and financial reports.
- `scripts/generate_company_graphics.py` creates a 1200×640 editorial SVG graphic for every tracked company in `generated-assets/company-graphics/`. Graphics use the company name, ticker, sector motif and an editorial accent color.
- `scripts/publish.py` drafts verified upcoming earnings announcements within 14 days, selects the matching company graphic, deduplicates by official source URL in `data/published-events.json`, and limits drafts to two per day. These are concise calendar notices.
- `scripts/publish_results.py` drafts results stories and major developments only from records in `data/verified-releases.json`. Each record must be marked `verified`, contain an editorial headline and substantive summary, and link directly to the actual company press release or material announcement. The resulting posts remain unpublished for editorial approval and use the company's graphic.
- SEC filings may be used as monitoring leads, but a filing or exhibit link alone never creates a story. Routine notices such as share repurchases are excluded unless they are part of a separately verified material development.

## Add a results release or major development

Add a record to `data/verified-releases.json` only after checking the issuer's release. Use this shape:

```json
{
  "id": "fox-2026-q1-results",
  "status": "verified",
  "story_type": "earnings_results",
  "company": "Fox Corporation",
  "ticker": "FOXA",
  "release_date": "2026-11-02",
  "release_url": "https://issuer.example/news/actual-results-release",
  "headline": "A specific, news-focused headline",
  "summary": "An original AP-style lead that explains the main result and why it matters.",
  "highlights": [
    "A verified financial or operating result from the release.",
    "A second meaningful result or business development."
  ]
}
```

Use `story_type: "major_development"` for material acquisitions, bankruptcies, restructurings, major layoffs, or other consequential company announcements. Link directly to the issuer's release, not an SEC filing or routine form. Add only facts supported by that release. A record is drafted once; to correct a draft, edit the MJR post and update the release record before its first workflow run.

## Add or update an upcoming event

Add an event to `data/events.json` only after checking an official company announcement. Include `company`, `title`, `date` (`YYYY-MM-DD`), `source_url`, `status: confirmed`, and `verified_at`. Use `time` and `timezone` only when the source states them. Optional fields include `webcast_url`, `report_url`, `replay_url`, `event_type`, and `fiscal_period`.

Do not estimate dates from prior quarters or third-party calendars. Company reports and conference calls can have separate times. Keep the original source link and verify ticker and investor-relations information before adding a company.

## Deployment

GitHub Pages publishes the repository root through `.github/workflows/pages.yml`. In repository settings, set Pages' build and deployment source to **GitHub Actions**. The public page URL is `https://mediajobsreport.github.io/mjr-financial-calendar/` once the first deployment finishes.

To embed it in Brilliant Directories, add an iframe to the body of an MJR custom web page:

```html
<iframe src="https://mediajobsreport.github.io/mjr-financial-calendar/" title="MJR Media Financial Calendar" loading="lazy" style="width:100%;height:1100px;border:0" referrerpolicy="strict-origin-when-cross-origin"></iframe>
```

The calendar and generated notices are editorial reference material, not investment advice. Event records are entered in `data/events.json` only after verification against official company sources. Results articles are drafted from verified issuer releases and major company announcements; SEC filing notices alone are not published as stories.
