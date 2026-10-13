"""Build data/shoes.csv + data/shoes.db from scraped raw product JSON. Keeps only SKUs with at least one size in stock."""
import csv, json, sqlite3
from pathlib import Path

OUT = Path(__file__).parent / "data"
recs = [json.loads(f.read_text()) for f in sorted((OUT / "raw").glob("*.json"))]

# Bayesian average: pull low-count ratings toward the catalogue mean (prior weight M reviews)
rated = [r for r in recs if r["review_count"]]
C = sum(r["rating"] * r["review_count"] for r in rated) / sum(r["review_count"] for r in rated)
M = 20

rows = []
for r in recs:
    in_stock = [s["uk"] for s in r["sizes"] if s["in_stock"]]
    if not in_stock:
        continue
    a = r["attributes"] or {}
    n, avg = r["review_count"] or 0, r["rating"]
    p = r["prices"] or {}
    rows.append({
        "sku": r["sku"], "parent_sku": r["parent_sku"], "brand": r["brand"], "name": r["name"], "colour": r["colour"],
        "price": p.get("price"), "rrp": p.get("retailPrice"), "pct_off": p.get("salePercentage"),
        "rating": round(avg, 2) if avg else None, "review_count": n,
        "bayes_rating": round((avg * n + C * M) / (n + M), 3) if n else None,
        "gender": ",".join(a.get("gender", [])),
        "sizes_in_stock": "|" + "|".join(in_stock) + "|",  # pipe-delimited so LIKE '%|11|%' matches exactly
        "sport": ",".join(a.get("sport", [])), "terrain": ",".join(a.get("attributeTerrain", [])),
        "type": ",".join(a.get("attributeType", []) if isinstance(a.get("attributeType"), list) else []),
        "cushioning": ",".join(a.get("attributeCushioning", [])), "stability": ",".join(a.get("attributeStability", [])),
        "width": ",".join(a.get("shoeWidth", [])), "features": ",".join(a.get("features", [])),
        "vitality_code_eligible": "vitality-code-eligible" in (r["promotions"] or []),
        "excluded_from_promotions": r["excluded_from_promotions"], "outlet": r["is_outlet"],
        "season": f'{(r["season"] or {}).get("seasonType", "")} {(r["season"] or {}).get("year", "")}'.strip(),
        "fit_size": r["fit_size"], "url": r["url"],
    })

rows.sort(key=lambda x: (x["bayes_rating"] or 0), reverse=True)
with open(OUT / "shoes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

db = sqlite3.connect(OUT / "shoes.db")
db.execute("DROP TABLE IF EXISTS shoes")
db.execute(f"CREATE TABLE shoes ({', '.join(rows[0])})")
db.executemany(f"INSERT INTO shoes VALUES ({', '.join('?' * len(rows[0]))})", [list(r.values()) for r in rows])
db.execute("DROP TABLE IF EXISTS stock")
db.execute("CREATE TABLE stock (sku, uk, eu, us, in_stock)")
keep = {r["sku"] for r in rows}
db.executemany("INSERT INTO stock VALUES (?,?,?,?,?)",
               [(r["sku"], s["uk"], s["eu"], s["us"], s["in_stock"]) for r in recs if r["sku"] in keep for s in r["sizes"]])
db.execute("DROP TABLE IF EXISTS reviews")
db.execute("CREATE TABLE reviews (sku, rating, title, text, date)")
db.executemany("INSERT INTO reviews VALUES (?,?,?,?,?)",
               [(r["sku"], v["rating"], v["title"], v["text"], v["date"]) for r in recs if r["sku"] in keep for v in r["reviews"]])
db.commit()
print(f"{len(rows)} in-stock SKUs (of {len(recs)} scraped); catalogue mean rating {C:.2f}")
