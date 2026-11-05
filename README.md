# MJR Media Financial Calendar

A small, responsive calendar for confirmed earnings releases, investor calls and financial reports from media companies. It is designed to be hosted as a static page and embedded in a Media Jobs Report page.

## Current setup

- `data/companies.json` holds company names, sectors, tickers and investor-relations links.
- `data/events.json` holds confirmed events and their company-source links.
- `scripts/build.py` validates event records and produces `calendar.json` for the page.
- GitHub Actions rebuilds the data on a schedule and deploys the static calendar to GitHub Pages.
- The page provides search and sector filters; event cards link to announcements, webcasts and financial reports.

## Add or update an event

Add an event to `data/events.json` only after checking an official company announcement. Include `company`, `title`, `date` (`YYYY-MM-DD`), `source_url`, `status: confirmed`, and `verified_at`. Use `time` and `timezone` only when the source states them. Optional fields include `webcast_url`, `report_url`, `replay_url`, `event_type`, and `fiscal_period`.

Do not estimate dates from prior quarters or third-party calendars. Company reports and conference calls can have separate times. Keep the original source link and verify ticker and investor-relations information before adding a company.

## Deployment

GitHub Pages publishes the repository root through `.github/workflows/pages.yml`. In repository settings, set Pages' build and deployment source to **GitHub Actions**. The public page URL is `https://mediajobsreport.github.io/mjr-financial-calendar/` once the first deployment finishes.

To embed it in Brilliant Directories, add an iframe to the body of an MJR custom web page:

```html
<iframe src="https://mediajobsreport.github.io/mjr-financial-calendar/" title="MJR Media Financial Calendar" loading="lazy" style="width:100%;height:1100px;border:0" referrerpolicy="strict-origin-when-cross-origin"></iframe>
```

The calendar is editorial reference material, not investment advice. The current build uses verified event records entered in `data/events.json`; scheduled builds validate and republish those records but do not discover new events automatically.
