# Vitality Shoe Finder

Every in-stock shoe on the [SportsShoes Vitality page](https://www.sportsshoes.com/products/vitality), filterable by UK size, and ranked by star rating adjusted for review count (Bayesian average: each shoe's rating is blended with 20 reviews at the catalogue mean).

Live page: https://shetlandj.github.io/vitality-shoe-finder/

## Refresh

```sh
rm -rf data/raw          # product pages are cached here; clear for fresh stock/prices
python3 scrape.py        # listing + ~5.6k product pages, ~25 min
python3 build.py         # data/shoes.csv + data/shoes.db (shoes, stock, reviews)
python3 make_page.py     # docs/index.html
```

The page data comes from each product page's Next.js payload: Bazaarvoice rating stats, per-size `isInStock`, and the `vitality-code-eligible` promotion tag.
