#!/usr/bin/env python3
"""Fetch World Bank indicator values (API v2) into a tidy CSV: country, iso3, indicator, year, value.

Examples:
  python3 wdi_fetch.py FX.OWN.TOTL.ZS --country NPL --date 2011:2024
  python3 wdi_fetch.py NY.GDP.PCAP.CD --country "NPL;IND;BGD" --mrv 3
  python3 wdi_fetch.py "FX.OWN.TOTL.FE.ZS;FX.OWN.TOTL.MA.ZS" --country "NPL;SAS;WLD" --mrnev 1
  python3 wdi_fetch.py FX.OWN.TOTL.ZS --country all --mrnev 1 --economies-only
  python3 wdi_fetch.py account.t.d.1 --source 28 --country NPL --date 2011:2024

--country takes ISO3 (NPL) or ISO2 (NP) codes, aggregate codes (SAS, LMC, WLD; see
wdi_countries.py --aggregates) or 'all'; separate several with ';'.
--date takes YYYY or YYYY:YYYY. --mrv N gives the N most recent years that have data for the request
as a whole (one country can still be empty in those years); --mrnev N gives each country its own N
most recent non-empty values, so the years can differ by country.
Empty values are dropped from the CSV unless --keep-empty. For monthly and quarterly series the
'year' column holds the period as the API gives it (2025M03, 2024Q1).

Writes, under --out (default ./research):
  data/wdi_<indicator>_<countries>_<period>[_src<id>].csv   one per indicator
  data_log.jsonl                                  one line per CSV (appended)
"""
import argparse
import pathlib
import re
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402
from wdi_countries import api_rows, load_countries  # noqa: E402
from wdi_find import load_sources  # noqa: E402

API = "https://api.worldbank.org/v2"
PER_PAGE = 1000
CSV_COLUMNS = ["country", "iso3", "indicator", "year", "value"]


def dataset_name(source_id, out_dir):
    if str(source_id) == "2":
        return "WDI"
    try:
        s = load_sources(out_dir).get(str(source_id))
    except c.FetchError:
        s = None
    return s["name"] if s else f"World Bank source {source_id}"


def indicator_source(code):
    """Source id of an indicator, from /indicator/{code}; '2' (WDI) if it cannot be found."""
    try:
        _, rows = api_rows(c.get_json(f"{API}/indicator/{code}?format=json"))
        return str(((rows or [{}])[0].get("source") or {}).get("id") or "2")
    except c.FetchError:
        return "2"


def entity_label(codes):
    if codes == ["all"]:
        return "all"
    return "-".join(codes) if len(codes) <= 6 else "-".join(codes[:3]) + f"-and-{len(codes) - 3}-more"


def fetch(indicator, codes, a):
    """All pages for one indicator. Returns (rows, meta, url_without_paging)."""
    params = {"format": "json", "per_page": PER_PAGE}
    if a.date:
        params["date"] = a.date
    if a.mrv:
        params["mrv"] = a.mrv
    if a.mrnev:
        params["mrnev"] = a.mrnev
    if a.source:
        params["source"] = a.source
    if a.frequency:
        params["frequency"] = a.frequency
    path = f"{API}/country/{';'.join(codes)}/indicator/{indicator}"
    base_url = c.build_url(path, params)
    rows, meta, page = [], {}, 1
    while True:
        meta, batch = api_rows(c.get_json(c.build_url(path, dict(params, page=page))))
        rows.extend(batch)
        if page >= int(meta.get("pages") or 1):
            break
        page += 1
        time.sleep(c.PAGE_SLEEP)
    return rows, meta, base_url


def tidy(raw_rows, keep_empty, iso_lookup, economies):
    out = []
    for r in raw_rows:
        if r.get("value") is None and not keep_empty:
            continue
        country = (r.get("country") or {})
        iso3 = r.get("countryiso3code") or iso_lookup().get(country.get("id", ""), country.get("id", ""))
        if economies is not None and iso3 not in economies():
            continue
        out.append({"country": country.get("value", ""), "iso3": iso3,
                    "indicator": (r.get("indicator") or {}).get("id", ""), "year": r.get("date", ""),
                    "value": r.get("value")})
    out.sort(key=lambda x: (x["iso3"], str(x["year"])))
    return out


def period_of(rows, a):
    years = sorted(str(r["year"]) for r in rows if r["value"] is not None)
    if years:
        return years[0] if years[0] == years[-1] else f"{years[0]}:{years[-1]}"
    return a.date or (f"mrv={a.mrv}" if a.mrv else f"mrnev={a.mrnev}" if a.mrnev else "all years")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("indicators", nargs="+", help="indicator code(s), e.g. FX.OWN.TOTL.ZS; ';' or spaces for several")
    ap.add_argument("--country", required=True, help="NPL, 'NPL;IND', SAS, LMC, WLD or all")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--date", help="YYYY or YYYY:YYYY; 2024Q1:2025Q2 or 2025M01:2025M06 for quarterly or monthly series")
    g.add_argument("--mrv", type=int, help="the N most recent years with data for the request")
    g.add_argument("--mrnev", type=int, help="the N most recent years with a value (per country)")
    ap.add_argument("--source", help="source id to read from, e.g. 28 (Global Findex); needed when a code is in "
                                     "several sources, so the dataset you cite is the one you meant")
    ap.add_argument("--frequency", choices=["M", "Q"], help="monthly or quarterly values where a source has them "
                                                         "(e.g. Global Economic Monitor, source 15); use with --mrv")
    ap.add_argument("--keep-empty", action="store_true", help="keep years with no value (value left blank)")
    ap.add_argument("--economies-only", action="store_true", help="drop aggregates (regions, income groups, World)")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_intermixed_args()

    period = r"\d{4}(?:[QM]\d{1,2})?"
    if a.date and not re.fullmatch(f"{period}(?::{period})?", a.date):
        ap.error("--date takes YYYY or YYYY:YYYY (quarterly 2024Q1:2025Q2, monthly 2025M01:2025M06)")
    indicators = [x.strip() for arg in a.indicators for x in arg.split(";") if x.strip()]
    codes = [x.strip().upper() for x in a.country.split(";") if x.strip()]
    codes = ["all" if x == "ALL" else x for x in codes]
    out = pathlib.Path(a.out)

    cache = {}

    def iso_lookup():  # iso2-style ids (XN, 8S) -> iso3-style ids (LMC, SAS), for rows that lack countryiso3code
        if "iso" not in cache:
            cache["iso"] = {r["iso2"]: r["iso3"] for r in load_countries(out)}
        return cache["iso"]

    def economy_codes():
        if "eco" not in cache:
            cache["eco"] = {r["iso3"] for r in load_countries(out) if not r["aggregate"]}
        return cache["eco"]

    results, failures = [], 0
    for i, ind in enumerate(indicators):
        if i:
            time.sleep(c.PAGE_SLEEP)
        try:
            raw, meta, url = fetch(ind, codes, a)
            rows = tidy(raw, a.keep_empty, iso_lookup, economy_codes if a.economies_only else None)
        except c.FetchError as e:
            failures += 1
            hint = " (check the code with wdi_find.py and the countries with wdi_countries.py)" \
                if "API error" in str(e) else ""
            print(f"error: {ind}: {e}{hint}", file=sys.stderr)
            continue
        source_id = meta.get("sourceid") or a.source or indicator_source(ind)  # mrnev replies omit sourceid
        name = c.clean((raw[0].get("indicator") or {}).get("value", "")) if raw else ""
        period = period_of(rows, a)
        decimal = raw[0].get("decimal") if raw else None
        res = {"indicator": ind, "name": name, "dataset": dataset_name(source_id, out), "source_id": str(source_id),
               "lastupdated": meta.get("lastupdated"), "decimal": decimal, "entity": ";".join(codes),
               "period": period, "url": url, "rows": rows, "file": None}
        if rows:
            req = a.date.replace(":", "-") if a.date else (f"mrv{a.mrv}" if a.mrv else f"mrnev{a.mrnev}" if a.mrnev else "all")
            src = f"_src{c.safe_name(a.source)}" if a.source else ""
            path = out / "data" / f"wdi_{c.safe_name(ind)}_{entity_label(codes)}_{req}{src}.csv"
            c.write_csv(path, rows, CSV_COLUMNS)
            res["file"] = str(path)
            c.log_data(out, {"source": "worldbank-indicators", "dataset": res["dataset"], "indicator": ind,
                             "entity": res["entity"], "period": period, "url": url, "accessed": c.today(),
                             "rows": len(rows), "file": str(path)})
        results.append(res)

    if a.json:
        c.print_json(results)
    else:
        for res in results:
            print(f"{res['indicator']}  {res['name']}")
            print(f"  {res['dataset']} (source {res['source_id']}, last updated {res['lastupdated']}); "
                  f"{c.plural(len(res['rows']), 'row')} with values for {res['entity']}, {res['period']}"
                  + (f"; the API suggests {res['decimal']} decimal{'' if res['decimal'] == 1 else 's'}"
                     if res["decimal"] is not None else ""))
            shown = res["rows"][:40]
            if shown:
                c.print_table([dict(r, value="" if r["value"] is None else f"{r['value']:,.2f}") for r in shown],
                              [("iso3", "iso3", 4), ("country", "country", 28), ("year", "year", 7),
                               ("value", "value", 14)])
                if len(res["rows"]) > len(shown):
                    print(f"  ... {len(res['rows']) - len(shown)} more rows in the CSV")
            print()
    for res in results:
        if res["file"]:
            c.say(f"wrote {res['file']} ({c.plural(len(res['rows']), 'row')}); appended 1 line to "
                  f"{out / 'data_log.jsonl'}", a.json)
        else:
            c.say(f"{res['indicator']}: no values for {res['entity']} in that period; nothing written", a.json)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
