"""Scrape sportsshoes.com Vitality PLP: all men's + women's shoes, then enrich with ratings + per-size stock."""
import json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://www.sportsshoes.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
OUT = Path(__file__).parent / "data"
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)
GENDERS = ["mens", "womens"]


def get(url, tries=3):
    for i in range(tries):
        try:
            r = subprocess.run(["curl", "-sSfL", "--max-time", "40", "-A", UA, "-H", "Accept-Language: en-GB", url],
                               capture_output=True, check=True)
            return r.stdout.decode("utf-8", "replace")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))["props"]["pageProps"]


def listing():
    found = {}
    for gender in GENDERS:
        page = 1
        while True:
            url = (f"{BASE}/products/vitality?page={page}&display=200&f_attribute_gender={gender}"
                   f"&f_attribute_product_type=shoes")
            pd = next_data(get(url))["productsData"]
            prods = pd["products"]
            for p in prods:
                e = found.setdefault(p["sku"], {**{k: p[k] for k in ("sku", "title", "brand", "url", "price", "rrp", "attributes", "promotions")}, "listed_in": []})
                e["listed_in"].append(gender)
            print(f"{gender} page {page}: {len(prods)} (total {pd['totalNumberOfResults']})", file=sys.stderr)
            if not prods or page * 200 >= pd["totalNumberOfResults"]:
                break
            page += 1
            time.sleep(0.5)
    return found


def product(sku):
    f = RAW / f"{sku}.json"
    if f.exists():
        return json.loads(f.read_text())
    pp = next_data(get(f"{BASE}/product/{sku.lower()}/x"))
    p = pp["product"]
    bv = pp.get("bazaarvoiceReviews") or {}
    stats = bv.get("stats") or {}
    sizes = []
    for g in p.get("groupedVariants") or []:
        for v in g.get("values", []):
            sizes.append({"uk": v.get("gbSize") or v.get("label"), "eu": v.get("euSize"), "us": v.get("usSize"),
                          "in_stock": v.get("isInStock"), "preorder": v.get("preorderDate") or None})
    reviews = [{"rating": r.get("Rating"), "title": r.get("Title"), "text": r.get("ReviewText"),
                "date": r.get("SubmissionTime"), "secondary": {k: (s or {}).get("Value") for k, s in (r.get("SecondaryRatings") or {}).items()},
                "fit": (r.get("ContextDataValues") or {}).get("Fit", {}).get("Value") if isinstance(r.get("ContextDataValues"), dict) else None}
               for r in bv.get("reviews") or []]
    rec = {
        "sku": sku, "name": p.get("name"), "brand": p.get("brand"), "url": BASE + (p.get("url") or ""),
        "prices": p.get("prices"), "attributes": p.get("attributes"), "promotions": p.get("promotions"),
        "excluded_from_promotions": p.get("excludedFromPromotions"), "is_outlet": p.get("isOutlet"),
        "season": p.get("season"), "colour": p.get("manufacturerColor"), "fit_size": p.get("fitSize"),
        "short_description": p.get("shortDescription"),
        "features": [re.sub(r"<[^>]+>", "", x).strip() for x in p.get("features") or []],
        "description_text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p.get("description") or "")).strip(),
        "parent_sku": p.get("parentSku"),
        "rating": stats.get("AverageOverallRating"), "review_count": stats.get("TotalReviewCount"),
        "sizes": sizes, "reviews": reviews,
    }
    f.write_text(json.dumps(rec))
    return rec


def main():
    lst = listing()
    (OUT / "listing.json").write_text(json.dumps(lst, indent=1))
    skus = list(lst)
    print(f"{len(skus)} unique SKUs", file=sys.stderr)
    done = 0
    errors = {}

    def work(sku):
        try:
            product(sku)
        except Exception as e:
            errors[sku] = repr(e)
        time.sleep(0.3)

    with ThreadPoolExecutor(8) as ex:
        for _ in ex.map(work, skus):
            done += 1
            if done % 100 == 0:
                print(f"{done}/{len(skus)} ({len(errors)} errors)", file=sys.stderr)
    (OUT / "errors.json").write_text(json.dumps(errors, indent=1))
    print(f"done, {len(errors)} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
