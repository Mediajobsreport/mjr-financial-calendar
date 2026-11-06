#!/usr/bin/env python3
"""Wait until the raster company graphics are available on GitHub Pages."""
import time
import urllib.error
import urllib.request

URL = "https://mediajobsreport.github.io/mjr-financial-calendar/generated-assets/company-graphics/GTN.png"

for attempt in range(48):
    try:
        request = urllib.request.Request(URL, headers={"User-Agent": "MJR Financial Calendar"})
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read(16)
            if response.status == 200 and response.headers.get_content_type() == "image/png" and payload.startswith(b"\x89PNG"):
                print("Company PNG graphics are live.")
                raise SystemExit(0)
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(10)

raise SystemExit("Company graphics did not become available; no drafts were created.")
