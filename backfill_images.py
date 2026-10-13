"""One-off: add `image` to raw records scraped before scrape.py stored it.
Uses the cdn.sportsshoes.com URL where it exists, otherwise re-fetches the product page for the BigCommerce URL."""
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scrape

RAW = Path(__file__).parent / "data" / "raw"


def fill(f):
    r = json.loads(f.read_text())
    if r.get("image"):
        return "had"
    s = r["sku"]
    cdn = f"https://cdn.sportsshoes.com/product/{s[0]}/{s}/{s}_400_1.jpg"
    code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-I", "-w", "%{http_code}", "-A", scrape.UA, cdn],
                          capture_output=True, text=True).stdout
    if code == "200":
        r["image"] = cdn
    else:
        pp = scrape.next_data(scrape.get(f"{scrape.BASE}/product/{s.lower()}/x"))
        r["image"] = scrape.thumb(pp["product"].get("images"))
    f.write_text(json.dumps(r))
    return "cdn" if code == "200" else "bc"


def safe(f):
    try:
        return fill(f)
    except Exception:
        return "err"


if __name__ == "__main__":
    from collections import Counter
    with ThreadPoolExecutor(8) as ex:
        print(Counter(ex.map(safe, sorted(RAW.glob("*.json")))))
