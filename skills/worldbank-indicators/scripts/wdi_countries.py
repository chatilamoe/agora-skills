#!/usr/bin/env python3
"""List World Bank economies and aggregates with region, income level and lending type (API v2 /country).

Examples:
  python3 wdi_countries.py nepal
  python3 wdi_countries.py --region SAS
  python3 wdi_countries.py --income LIC --json
  python3 wdi_countries.py --aggregates          # codes for regions and income groups: SAS, LMC, WLD ...

Codes: iso3 (NPL) is what wdi_fetch.py takes; iso2 (NP) is what projects_search.py takes.
Income groups are re-set every 1 July from the previous year's GNI per capita; the list shows today's.

One call downloads the whole list (296 rows); it is cached for 30 days in <out>/cache/wb_countries.json.

Writes, under --out (default ./research):
  data/wb_countries[_filters].csv     the rows shown
  data_log.jsonl                      one line for that file (appended)
  cache/wb_countries.json             the full list
"""
import argparse
import datetime
import json
import pathlib
import sys

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://api.worldbank.org/v2"
LIST_URL = API + "/country?format=json&per_page=400"
CSV_COLUMNS = ["iso3", "iso2", "name", "region", "region_id", "income", "income_id", "lending", "lending_id",
               "capital", "aggregate"]


def api_rows(data):
    """World Bank v2 replies [meta, rows]; errors come back with HTTP 200 as [{"message": [...]}]."""
    if isinstance(data, list) and data and isinstance(data[0], dict) and "message" in data[0]:
        msgs = data[0]["message"]
        text = "; ".join(f"{m.get('key', '')}: {m.get('value', '')}" for m in msgs if isinstance(m, dict))
        raise c.FetchError(f"API error: {text or msgs}")
    if not isinstance(data, list) or len(data) < 2:
        return {}, []
    return data[0] or {}, data[1] or []


def flat(r):
    region = (r.get("region") or {}).get("value", "").strip()
    return {
        "iso3": r.get("id", ""),
        "iso2": r.get("iso2Code", ""),
        "name": c.clean(r.get("name")),
        "region": region,
        "region_id": (r.get("region") or {}).get("id", ""),
        "income": (r.get("incomeLevel") or {}).get("value", "").strip(),
        "income_id": (r.get("incomeLevel") or {}).get("id", ""),
        "lending": (r.get("lendingType") or {}).get("value", "").strip(),
        "lending_id": (r.get("lendingType") or {}).get("id", ""),
        "capital": r.get("capitalCity", ""),
        "aggregate": region == "Aggregates",
    }


def load_countries(out_dir, refresh=False, max_age_days=30):
    """Full country list (flattened), from the cache when it is fresh enough."""
    path = pathlib.Path(out_dir) / "cache" / "wb_countries.json"
    if path.exists() and not refresh:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            age = (datetime.date.today() - datetime.date.fromisoformat(cached["fetched"])).days
            if age <= max_age_days:
                return cached["countries"]
        except (ValueError, KeyError):
            pass
    meta, rows = api_rows(c.get_json(LIST_URL))
    countries = [flat(r) for r in rows]
    if not countries:
        raise c.FetchError("the country list came back empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched": c.today(), "url": LIST_URL, "total": meta.get("total"),
                                "countries": countries}, ensure_ascii=False), encoding="utf-8")
    return countries


def matches(value_id, value_name, wanted):
    w = wanted.strip().lower()
    return w == value_id.lower() or w in value_name.lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="part of a name or a code (nepal, NPL, NP)")
    ap.add_argument("--region", help="region id or part of its name: SAS, EAS, ECS, LCN, MEA, NAC, SSF, 'south asia'")
    ap.add_argument("--income", help="LIC, LMC, UMC, HIC or part of the name")
    ap.add_argument("--lending", help="IDX (IDA), IBD (IBRD), IDB (Blend), LNX (not classified)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--aggregates", action="store_true", help="list only aggregates (regions, income groups, World)")
    g.add_argument("--all", action="store_true", help="list economies and aggregates")
    ap.add_argument("--refresh", action="store_true", help="download the list again even if the cache is fresh")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_intermixed_args()

    try:
        countries = load_countries(a.out, refresh=a.refresh)
    except c.FetchError as e:
        c.die(str(e))

    rows = countries
    if a.aggregates:
        rows = [r for r in rows if r["aggregate"]]
    elif not a.all:
        rows = [r for r in rows if not r["aggregate"]]
    if a.region:
        rows = [r for r in rows if matches(r["region_id"], r["region"], a.region)]
    if a.income:
        rows = [r for r in rows if matches(r["income_id"], r["income"], a.income)]
    if a.lending:
        rows = [r for r in rows if matches(r["lending_id"], r["lending"], a.lending)]
    if a.names:
        terms = [n.lower() for n in a.names]
        rows = [r for r in rows if any(t in r["name"].lower() or t == r["iso3"].lower() or t == r["iso2"].lower()
                                       for t in terms)]

    filters = [f"{k}={v}" for k, v in (("region", a.region), ("income", a.income), ("lending", a.lending)) if v]
    filters += [f"name={n}" for n in a.names]
    if a.aggregates:
        filters.append("aggregates")
    elif a.all:
        filters.append("all")
    out = pathlib.Path(a.out)
    csv_path = out / "data" / ("wb_countries" + (f"_{c.slug('_'.join(filters))}" if filters else "") + ".csv")
    if rows:
        c.write_csv(csv_path, rows, CSV_COLUMNS)
        c.log_data(out, {"source": "worldbank-indicators", "dataset": "World Bank country classification",
                         "indicator": "region, income level, lending type", "entity": "; ".join(filters) or "all economies",
                         "period": f"as of {c.today()}", "url": LIST_URL, "accessed": c.today(),
                         "rows": len(rows), "file": str(csv_path)})

    if a.json:
        c.print_json(rows)
    else:
        kind = "aggregates" if a.aggregates else ("economies and aggregates" if a.all else "economies")
        if len(rows) == 1:
            kind = {"aggregates": "aggregate", "economies": "economy"}.get(kind, "entry")
        print(f"{len(rows)} {kind}" + (f" ({', '.join(filters)})" if filters else ""))
        if rows:
            c.print_table(rows, [("iso3", "iso3", 4), ("iso2", "iso2", 4), ("name", "name", 34),
                                 ("region", "region", 30), ("income", "income", 19), ("lending", "lending", 14)])
    if rows:
        c.say(f"wrote {csv_path} ({c.plural(len(rows), 'row')}); appended 1 line to {out / 'data_log.jsonl'}", a.json)
    else:
        c.say("nothing matched; try a shorter name or --all", a.json)


if __name__ == "__main__":
    main()
