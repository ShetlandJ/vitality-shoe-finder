"""Build docs/index.html (shoe finder) from data/raw/*.json. Groups colourways into models."""
import json, re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
recs = [json.loads(f.read_text()) for f in sorted((ROOT / "data" / "raw").glob("*.json"))]

rated = [r for r in recs if r["review_count"]]
C = sum(r["rating"] * r["review_count"] for r in rated) / sum(r["review_count"] for r in rated)
M = 20

def clean_name(n, brand):
    n = re.sub(r"\s+", " ", n or "").strip()
    if brand and n.lower().startswith(brand.lower() + " "):
        n = n[len(brand) + 1:]
    return n

models = defaultdict(list)
for r in recs:
    if not any(s["in_stock"] for s in r["sizes"]):
        continue
    a = r["attributes"] or {}
    key = (r["brand"], clean_name(r["name"], r["brand"]).lower())
    models[key].append(r)

out = []
for (brand, _), rs in models.items():
    name = clean_name(rs[0]["name"], brand)
    # Ratings may be per colourway or shared; take the colourway with the most reviews as the model's figure
    best = max(rs, key=lambda r: r["review_count"] or 0)
    n, avg = best["review_count"] or 0, best["rating"]
    a = best["attributes"] or {}
    g = a.get("gender", [])
    out.append({
        "b": brand, "n": name,
        "g": "u" if len(g) > 1 or "unisex" in g else ("w" if "womens" in g else "m"),
        "r": round(avg, 2) if n else None, "c": n,
        "a": round((avg * n + C * M) / (n + M), 3) if n else None,
        "t": a.get("attributeTerrain", []), "sp": a.get("sport", []), "st": a.get("attributeStability", []),
        "cu": a.get("attributeCushioning", []), "ty": a.get("attributeType", []),
        "w": a.get("shoeWidth", []), "f": a.get("features", []),
        "d": (best["short_description"] or "")[:400],
        "k": [{
            "s": r["sku"], "col": r["colour"], "p": (r["prices"] or {}).get("price"), "rrp": (r["prices"] or {}).get("retailPrice"),
            "v": "vitality-code-eligible" in (r["promotions"] or []) and not r["excluded_from_promotions"],
            "u": r["url"], "z": [s["uk"] for s in r["sizes"] if s["in_stock"]],
        } for r in sorted(rs, key=lambda r: (r["prices"] or {}).get("price") or 0)],
    })

tpl = (ROOT / "page_template.html").read_text()
html = (tpl.replace("/*DATA*/[]", json.dumps(out, separators=(",", ":")))
           .replace("{{UPDATED}}", date.today().strftime("%-d %B %Y"))
           .replace("{{MEAN}}", f"{C:.2f}").replace("{{M}}", str(M)))
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "index.html").write_text(html)
print(f"{len(out)} models, {sum(len(m['k']) for m in out)} colourways, mean {C:.2f}, {len(html)//1024} KB")
