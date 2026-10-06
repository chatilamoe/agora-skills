#!/usr/bin/env python3
"""Full-text search on DBnomics: find the datasets whose series match your words, then the
matching series inside each, with the series ID to pass to dbn_series.py.

DBnomics search works in two steps, and so does this script:
  1. /search?q=WORDS                         datasets, ranked by how many of their series match
  2. /series/{provider}/{dataset}?q=WORDS    the matching series inside each top dataset

Words match whole words in series names and codes: 'gdp' does not match 'Gross domestic
product' or 'NGDP_RPCH'. Try the words the provider uses ('gross domestic product',
'consumer prices', 'unemployment rate') and a country name.

Datasets published as dated releases (IMF/WEO:2008-04 ... IMF/WEO:2025-04) are collapsed to
the newest release, and the upper/lower-case duplicates some providers have (Eurostat) to
the most recently indexed one; --all-releases shows them all.

Writes: <out>/catalog/dbn_search_<words>.csv (every series listed).
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (BASE, PAGE_SLEEP, build_url, get_json, print_json, quote_path, run, safe_name,  # noqa: E402
                     say, script_path, write_csv)

EPILOG = """examples:
  python3 dbn_search.py nepal inflation
  python3 dbn_search.py euro area hicp --provider ECB
  python3 dbn_search.py account ownership nepal --series 10
  python3 dbn_search.py quarterly real gdp growth --provider OECD --datasets 3
  python3 dbn_search.py nepal gross domestic product --all-releases --datasets 3 --json
"""

COLUMNS = ["query", "rank", "provider", "dataset", "dataset_name", "dataset_indexed_at", "nb_matching_series",
           "nb_series", "series_id", "series_code", "series_name", "frequency"]


def search_datasets(q, providers, want):
    """Dataset hits in DBnomics order; pages further (100 per page, up to 500) when a provider filter thins them."""
    hits, offset, num_found, url = [], 0, None, None
    while True:
        page_url = build_url(f"{BASE}/search", {"q": q, "limit": 100, "offset": offset or None})
        url = url or page_url
        res = get_json(page_url).get("results", {})
        num_found = res.get("num_found", 0)
        docs = res.get("docs", [])
        for d in docs:
            if not providers or d.get("provider_code", "").upper() in providers:
                hits.append(d)
        offset += len(docs)
        if not providers or len(hits) >= want * 3 or not docs or offset >= min(num_found, 500):
            break
        time.sleep(PAGE_SLEEP)
    return hits, num_found, url


def collapse(hits):
    """Keep one dataset per release family (WEO:2025-04 over WEO:2010-10) and per case-duplicate."""
    best, order = {}, []
    for d in hits:
        code = d.get("code", "")
        release = ":" in code
        fam = (d.get("provider_code"), (code.split(":")[0] if release else code).upper())
        if fam not in best:
            best[fam] = d
            order.append(fam)
            continue
        cur = best[fam]
        if release and code > cur.get("code", ""):
            best[fam] = d
        elif not release and d.get("indexed_at", "") > cur.get("indexed_at", ""):
            best[fam] = d
    kept = [best[f] for f in order]
    return kept, len(hits) - len(kept)


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="+", help="search words, e.g. nepal inflation")
    ap.add_argument("--provider", help="only these providers, comma-separated, e.g. IMF,WB,OECD,ECB")
    ap.add_argument("--datasets", type=int, default=5, help="datasets to open (default 5)")
    ap.add_argument("--series", type=int, default=5, help="series to list per dataset (default 5, max 1000)")
    ap.add_argument("--all-releases", action="store_true", help="keep every dated release and duplicate")
    ap.add_argument("--out", default="research", metavar="DIR", help="folder for files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_args()

    q = " ".join(a.words).strip()
    providers = {p.strip().upper() for p in (a.provider or "").split(",") if p.strip()}
    hits, num_found, search_url = search_datasets(q, providers, a.datasets)
    hidden = 0
    if not a.all_releases:
        hits, hidden = collapse(hits)
    top = hits[: max(a.datasets, 0)]

    results, csv_rows = [], []
    for rank, d in enumerate(top, 1):
        time.sleep(PAGE_SLEEP)
        p, ds = d.get("provider_code", ""), d.get("code", "")
        url = build_url(f"{BASE}/series/{quote_path(p)}/{quote_path(ds)}",
                        {"q": q, "limit": min(max(a.series, 1), 1000), "metadata": 0})
        sres = get_json(url).get("series", {})
        series = []
        for s in sres.get("docs", []):
            sid = f"{p}/{ds}/{s.get('series_code', '')}"
            item = {"id": sid, "code": s.get("series_code", ""), "name": s.get("series_name", ""),
                    "frequency": s.get("@frequency", "")}
            series.append(item)
            csv_rows.append({"query": q, "rank": rank, "provider": p, "dataset": ds,
                             "dataset_name": d.get("name", ""), "dataset_indexed_at": (d.get("indexed_at") or "")[:10],
                             "nb_matching_series": d.get("nb_matching_series"), "nb_series": d.get("nb_series"),
                             "series_id": sid, "series_code": item["code"], "series_name": item["name"],
                             "frequency": item["frequency"]})
        results.append({"rank": rank, "provider": p, "dataset": ds, "name": d.get("name", ""),
                        "nb_matching_series": d.get("nb_matching_series"), "nb_series": d.get("nb_series"),
                        "indexed_at": (d.get("indexed_at") or "")[:10], "series_found": sres.get("num_found", 0),
                        "series": series})

    catalog = None
    if csv_rows:
        catalog = write_csv(pathlib.Path(a.out) / "catalog" / f"dbn_search_{safe_name(q.lower(), 60)}.csv",
                            csv_rows, COLUMNS)

    if a.json:
        print_json({"query": q, "search_url": search_url, "datasets_found": num_found,
                    "older_releases_hidden": hidden, "datasets": results,
                    "catalog_file": catalog.as_posix() if catalog else None})
    else:
        scope = f" in {','.join(sorted(providers))}" if providers else ""
        line = f'DBnomics search "{q}"{scope}: {num_found} datasets matched; showing {len(top)}'
        if hidden:
            line += f" ({hidden} older releases or duplicates hidden; --all-releases shows them)"
        print(line)
        for r in results:
            name = r["name"] if len(r["name"]) <= 90 else r["name"][:89] + "~"
            print(f"\n{r['provider']}/{r['dataset']}  {name}  "
                  f"[{r['nb_matching_series']} of {r['nb_series']} series match; indexed {r['indexed_at']}]")
            for s in r["series"]:
                print(f"  {s['id']:<58} {s['name'][:110]}")
            if not r["series"]:
                print("  (no series name inside this dataset matches all the words; "
                      f"try: python3 {script_path('dbn_dataset.py')} {r['provider']}/{r['dataset']} --q \"<fewer words>\")")
            elif r["series_found"] > len(r["series"]):
                print(f"  ... {r['series_found']} match in this dataset: python3 {script_path('dbn_dataset.py')} "
                      f"{r['provider']}/{r['dataset']} --q \"{q}\"")
    if catalog:
        say(f"\nSeries IDs: {catalog.as_posix()}. Next: python3 {script_path('dbn_series.py')} <series id> --start YYYY", a.json)
    if not top:
        say("Nothing found. Use fewer or different words (whole words; 'gross domestic product' rather than 'gdp').",
            a.json)
        return 1
    return 0


if __name__ == "__main__":
    run(main)
