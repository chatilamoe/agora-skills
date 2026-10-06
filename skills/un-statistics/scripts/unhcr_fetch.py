#!/usr/bin/env python3
"""Fetch forcibly displaced and stateless population figures from the UNHCR Refugee Statistics API (keyless).

https://api.unhcr.org/population/v1 . Figures are by year, country of origin (coo) and country
of asylum (coa). Leaving coo or coa out sums over it; --coo-all / --coa-all splits by every
country instead.

Endpoints (--table):
  population           refugees, asylum_seekers, returned_refugees, idps, returned_idps,
                       stateless, ooc (others of concern), oip (other people in need of
                       international protection), hst (host community)   [default]
  demographics         the same people by sex and age band (f_0_4 ... m_60, total)
  asylum-applications  applications lodged (procedure type, application type, decision level)
  asylum-decisions     recognized, complementary protection (dec_other), rejected, closed
  solutions            returned refugees, resettlement, naturalisation, returned IDPs
  idmc                 internally displaced people from conflict, from IDMC
  unrwa                Palestine refugees under UNRWA's mandate
  nowcasting           UNHCR's latest monthly estimate of global refugee and asylum-seeker totals

Countries are ISO3 (NPL), ISO2 or M49; the script always asks the API to use ISO3 (cf_type=ISO):
UNHCR's own codes differ (Germany GFR, Nepal NEP, Egypt ARE) and an ISO3 code sent without that
switch silently matches nothing. Years: --year 2024, or --start/--end; years outside the request
are dropped here too, because the API ignores a year range that has no data and returns everything.

Writes <out>/data/unhcr_<table>_<coo>_<coa>.csv and appends one record to <out>/data_log.jsonl.
"""
import argparse
import time

import _common as C

API = "https://api.unhcr.org/population/v1"
TABLES = ["population", "demographics", "asylum-applications", "asylum-decisions", "solutions",
          "idmc", "unrwa", "nowcasting"]
LIMIT = 1000
NOTES = {
    "population": "Stocks at the end of each year.",
    "demographics": "Stocks at the end of each year, by sex and age band.",
    "asylum-applications": "Flows: applications lodged during each year.",
    "asylum-decisions": "Flows: decisions taken during each year.",
    "solutions": "Flows: returns, resettlement and naturalisation during each year.",
    "idmc": "Stocks at the end of each year (IDMC estimates of conflict IDPs).",
    "unrwa": "Palestine refugees registered with UNRWA at the end of each year.",
    "nowcasting": "UNHCR's latest monthly nowcast; check the month column.",
}

EXAMPLES = """examples:
  python3 unhcr_fetch.py --coo AFG --year 2024
  python3 unhcr_fetch.py --coo SYR --start 2020 --end 2025
  python3 unhcr_fetch.py --coa NPL --coo-all --year 2025
  python3 unhcr_fetch.py --table asylum-decisions --coa DEU --year 2024
  python3 unhcr_fetch.py --table idmc --coo SDN --start 2022
"""


def clean(value):
    """UNHCR sends '-' for 'not applicable' and some zeros as strings."""
    if value == "-":
        return ""
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default="population", choices=TABLES, help="which endpoint (default population)")
    ap.add_argument("--coo", action="append", help="country/countries of origin, e.g. AFG or AFG,SYR")
    ap.add_argument("--coa", action="append", help="country/countries of asylum, e.g. DEU")
    ap.add_argument("--coo-all", action="store_true", help="one row per country of origin")
    ap.add_argument("--coa-all", action="store_true", help="one row per country of asylum")
    ap.add_argument("--year", action="append", help="year(s), e.g. 2024 or 2023,2024")
    ap.add_argument("--start", help="first year")
    ap.add_argument("--end", help="last year")
    C.add_common_args(ap)
    args = ap.parse_args()

    coo = [C.to_iso3(c) for c in C.split_values(args.coo)]
    coa = [C.to_iso3(c) for c in C.split_values(args.coa)]
    years = [C.year_or_none(y, "--year") for y in C.split_values(args.year)]
    start, end = C.year_or_none(args.start, "--start"), C.year_or_none(args.end, "--end")
    params = [("limit", LIMIT), ("cf_type", "ISO"), ("coo", ",".join(coo)), ("coa", ",".join(coa)),
              ("coo_all", "true" if args.coo_all else None), ("coa_all", "true" if args.coa_all else None),
              ("yearFrom", start), ("yearTo", end)]
    params += [("year[]", y) for y in years]
    base_url = C.build_url("%s/%s/" % (API, args.table), params)

    items, page, pages = [], 1, 1
    while page <= pages:
        data = C.fetch_json(C.build_url(base_url, [("page", page)]) if page > 1 else base_url)
        items.extend(data.get("items") or [])
        pages = data.get("maxPages") or 0
        page += 1
        if page <= pages:
            time.sleep(C.PAGE_SLEEP)

    rows, dropped = [], 0
    for it in items:
        y = it.get("year")
        y = int(y) if isinstance(y, (int, str)) and str(y).isdigit() else y
        if isinstance(y, int) and ((years and y not in years) or (start and y < start) or (end and y > end)):
            dropped += 1
            continue
        rows.append({k: clean(v) for k, v in it.items()})
    lead = ["year", "coo_iso", "coo_name", "coa_iso", "coa_name"]
    tail = ["coo", "coa", "coo_id", "coa_id"]
    columns = [c for c in lead if any(c in r for r in rows)]
    for r in rows:
        for k in r:
            if k not in columns and k not in tail and k != "0":
                columns.append(k)
    columns += [c for c in tail if any(c in r for r in rows)]
    rows.sort(key=lambda r: (r.get("year") or 0, str(r.get("coo_name")), str(r.get("coa_name"))))

    measures = [c for c in columns if c not in lead + tail]
    view = [c for c in ["year", "coo_iso", "coa_iso"] if c in columns]
    view += [m for m in measures if any(r.get(m) not in ("", 0, None) for r in rows)][:8]
    tag = C.period_tag(start, end) or ("-".join(str(y) for y in years) if years else "")
    stem = "unhcr_%s_coo-%s_coa-%s%s" % (args.table, "all" if args.coo_all else ("-".join(coo) or "total"),
                                         "all" if args.coa_all else ("-".join(coa) or "total"),
                                         ("_" + tag) if tag else "")
    path = C.write_csv(rows, columns, args.out, stem) if rows else None
    entity = "coo=%s; coa=%s" % ("all" if args.coo_all else (",".join(coo) or "total"),
                                 "all" if args.coa_all else (",".join(coa) or "total"))
    requested = ",".join(str(y) for y in years) or ("%s:%s" % (start or "", end or "") if (start or end) else "")
    log = C.log_data(args.out, "UNHCR Refugee Population Statistics (%s)" % args.table, args.table, entity,
                     C.period_of((r.get("year") for r in rows), requested), base_url, len(rows), path)
    C.report(args, rows, columns, view, log)
    if not args.json:
        if dropped:
            print("Dropped %d rows outside the requested years (the API ignored the year filter)." % dropped)
        print(NOTES[args.table] + " An empty cell means not applicable.")


if __name__ == "__main__":
    C.run(main)
