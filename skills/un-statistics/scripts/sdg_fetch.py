#!/usr/bin/env python3
"""Fetch SDG indicator data from the UN SDG Global Database API (unstats.un.org/SDGAPI, keyless).

The SDG database is organised as goal > target > indicator (e.g. 1.1.1) > series (e.g. SI_POV_DAY1).
Data come by series (or by indicator: all its series) for one or more areas.

  --search WORDS                 find indicators and series by words or codes
  --series CODE --area NPL       data for a series (several: --series A,B; --area NPL,IND)
  --indicator 1.1.1 --area NPL   data for every series of an indicator
  --areas [--search WORDS]       area codes (M49) and names, including regions such as 1 (World)

Areas: ISO3 (NPL), ISO2 (NP), M49 (524) or exact names are accepted; the API itself uses M49
numbers without leading zeros, so they are converted. Regions use M49 too (World = 1,
Southern Asia = 34; see --areas). --start/--end are sent as one timePeriod per year, because
the API's timePeriodStart/timePeriodEnd parameters do not behave as a range, and re-checked here.
The API slows down at times, more so with big pages: on read timeouts use --page-size 100.

Rows include every disaggregation (sex, age, location, ...); --totals keeps only the totals
on each dimension where totals exist. Writes <out>/data/sdg_<series>_<areas>.csv and appends
one record to <out>/data_log.jsonl.
"""
import argparse
import datetime
import time

import _common as C

API = "https://unstats.un.org/SDGAPI/v1/sdg"
DATASET = "UN SDG Global Database"
PAGE_SIZE = 500   # rows per page; the server slows down with bigger pages (see --page-size)

EXAMPLES = """examples:
  python3 sdg_fetch.py --search poverty line
  python3 sdg_fetch.py --series SI_POV_DAY1 --area NPL --totals
  python3 sdg_fetch.py --series SE_TOT_CPLR --area NPL,IND --start 2015 --totals
  python3 sdg_fetch.py --indicator 3.2.1 --area NPL --start 2020
  python3 sdg_fetch.py --areas --search asia
"""


def cmd_search(words, args):
    url = API + "/Indicator/List"
    data = C.fetch_json(url)
    rows = []
    for ind in data:
        for s in ind.get("series") or []:
            text = " ".join([ind.get("code", ""), ind.get("description", ""), s.get("code", ""),
                             s.get("description", "")])
            if C.matches(text, words):
                rows.append({"indicator": ind.get("code"), "series": s.get("code"),
                             "series_description": s.get("description"), "release": s.get("release"),
                             "tier": ind.get("tier")})
    if args.json:
        C.print_json({"url": url, "query": words, "count": len(rows), "series": rows})
        return
    print("SDG series matching %r: %d" % (words, len(rows)))
    C.print_table(rows, ["indicator", "series", "series_description", "release"], limit=args.limit, width=90,
                  more="use more words, --limit N or --json")
    if rows:
        print("\nNext: --series %s --area NPL --totals" % rows[0]["series"])


def cmd_areas(words, args):
    url = API + "/GeoArea/List"
    data = C.fetch_json(url)
    rows = [{"m49": a.get("geoAreaCode"), "iso3": C.iso3_from_m49(a.get("geoAreaCode")),
             "name": a.get("geoAreaName")} for a in data]
    if words:
        rows = [r for r in rows if C.matches("%s %s %s" % (r["m49"], r["iso3"], r["name"]), words)]
    if args.json:
        C.print_json({"url": url, "count": len(rows), "areas": rows})
        return
    print("SDG areas%s: %d (regions have no ISO3)" % ((" matching %r" % words) if words else "", len(rows)))
    C.print_table(rows, ["m49", "iso3", "name"], limit=args.limit, width=70, more="use --search or --json")


def total_codes(dimensions):
    """{dimension: {codes meaning 'total'}} from the response's dimension metadata (SDMX code _T)."""
    out = {}
    for dim in dimensions or []:
        codes = {c.get("code") for c in dim.get("codes") or [] if c.get("sdmx") == "_T"}
        if codes:
            out[dim.get("id")] = codes
    return out


def fetch_all(endpoint, params, page_size=PAGE_SIZE):
    """Page through Series/Data or Indicator/Data; return (records, dimension metadata, first url)."""
    records, dims, first_url, page = [], [], None, 1
    while True:
        url = C.build_url(API + endpoint, params + [("pageSize", page_size), ("page", page)])
        first_url = first_url or url
        data = C.fetch_json(url)
        records.extend(data.get("data") or [])
        dims = dims or data.get("dimensions") or []
        total_pages = data.get("totalPages") or 0
        if page >= total_pages:
            break
        page += 1
        time.sleep(C.PAGE_SLEEP)
    return records, dims, first_url


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", nargs="*", metavar="WORD", help="find series by words or codes (with --areas: filter areas)")
    ap.add_argument("--areas", action="store_true", help="list area codes (M49) and names")
    ap.add_argument("--series", action="append", help="series code(s), e.g. SI_POV_DAY1")
    ap.add_argument("--indicator", action="append", help="indicator code(s), e.g. 1.1.1 (all its series)")
    ap.add_argument("--area", action="append", help="area(s): NPL, NP, 524, Nepal; regions by M49 (1 = World)")
    ap.add_argument("--start", help="first year")
    ap.add_argument("--end", help="last year")
    ap.add_argument("--totals", action="store_true", help="keep only totals (both sexes, all ages, all areas, ...)")
    ap.add_argument("--page-size", type=int, default=PAGE_SIZE,
                    help="rows per request (default %d); use 100 when the API times out" % PAGE_SIZE)
    ap.add_argument("--limit", type=int, default=50, help="rows shown for --search and --areas (default 50)")
    C.add_common_args(ap)
    args = ap.parse_args()

    words = " ".join(args.search) if args.search else ""
    if args.areas:
        cmd_areas(words, args)
        return
    if args.search is not None and not (args.series or args.indicator):
        if not words:
            ap.error("give words after --search")
        cmd_search(words, args)
        return
    series = C.split_values(args.series)
    indicators = C.split_values(args.indicator)
    if not (series or indicators):
        ap.error("give --series or --indicator (find them with --search WORDS)")
    if series and indicators:
        ap.error("give --series or --indicator, not both")
    areas_in = C.split_values(args.area)
    if not areas_in:
        ap.error("give --area (e.g. NPL); fetching every area of a series can take minutes")
    start, end = C.year_or_none(args.start, "--start"), C.year_or_none(args.end, "--end")
    m49 = [C.to_m49(a) for a in areas_in]

    if series:
        endpoint, params, label = "/Series/Data", [("seriesCode", series), ("areaCode", m49)], ",".join(series)
    else:
        endpoint, params, label = "/Indicator/Data", [("indicator", indicators), ("areaCode", m49)], ",".join(indicators)
    if start is not None or end is not None:
        # timePeriodStart/timePeriodEnd are not a range in this API; one timePeriod per year is,
        # and it makes the server return (and slow down on) fewer rows. Years are re-checked below.
        last_year = end if end is not None else datetime.date.today().year
        params.append(("timePeriod", list(range(start if start is not None else 1950, last_year + 1))))
    records, dims, url = fetch_all(endpoint, params, max(1, args.page_size))

    dim_names = []
    for r in records:
        for k in (r.get("dimensions") or {}):
            if k not in dim_names:
                dim_names.append(k)
    rows = []
    for r in records:
        year = r.get("timePeriodStart")
        year = int(year) if isinstance(year, (int, float)) else year
        if start is not None and isinstance(year, int) and year < start:
            continue
        if end is not None and isinstance(year, int) and year > end:
            continue
        attrs = r.get("attributes") or {}
        row = {"series": r.get("series"), "series_description": r.get("seriesDescription"),
               "indicator": ",".join(r.get("indicator") or []), "area_code": r.get("geoAreaCode"),
               "iso3": C.iso3_from_m49(r.get("geoAreaCode")), "area_name": r.get("geoAreaName"),
               "year": year, "value": r.get("value"), "units": attrs.get("Units"), "nature": attrs.get("Nature"),
               "lower_bound": r.get("lowerBound"), "upper_bound": r.get("upperBound"),
               "base_period": r.get("basePeriod"), "time_detail": r.get("time_detail"),
               "source": r.get("source"), "footnotes": " | ".join(r.get("footnotes") or [])}
        for k in dim_names:
            row[k] = (r.get("dimensions") or {}).get(k, "")
        rows.append(row)

    dropped = 0
    if args.totals and rows:
        totals = total_codes(dims)
        # filter only on dimensions where at least one row is a total (education level, for
        # example, defines the series and never has a total row)
        active = {d: codes for d, codes in totals.items() if any(r.get(d) in codes for r in rows)}
        kept = [r for r in rows if all(r.get(d) in codes for d, codes in active.items() if d in r)]
        dropped, rows = len(rows) - len(kept), kept
    rows.sort(key=lambda r: (str(r["series"]), str(r["area_name"]), str(r["year"])) +
              tuple(str(r.get(k, "")) for k in dim_names))

    columns = ["series", "series_description", "indicator", "area_code", "iso3", "area_name", "year",
               "value", "units", "nature"] + dim_names + ["lower_bound", "upper_bound", "base_period",
                                                          "time_detail", "source", "footnotes"]
    entity = ",".join(C.to_iso3(a) if C.lookup_country(a) else C.to_m49(a) for a in areas_in)
    stem = "sdg_%s_%s" % (label, "-".join(C.to_iso3(a) if C.lookup_country(a) else C.to_m49(a) for a in areas_in))
    if start or end:
        stem += "_" + C.period_tag(start, end)
    if args.totals:
        stem += "_totals"
    path = C.write_csv(rows, columns, args.out, stem) if rows else None
    requested = "%s:%s" % (start or "", end or "") if (start or end) else ""
    log = C.log_data(args.out, DATASET, label, entity, C.period_of((r["year"] for r in rows), requested),
                     url, len(rows), path)
    disagg = [k for k in dim_names if k != "Reporting Type" and len({r.get(k) for r in rows}) > 1]
    view = ["series", "area_name", "year", "value", "units"] + disagg
    C.report(args, rows, columns, view, log)
    if not args.json:
        if dropped:
            print("--totals dropped %d disaggregated rows." % dropped)
        elif disagg and not args.totals:
            print("Rows differ by %s; add --totals to keep only totals." % ", ".join(disagg))
        if rows and len({r["source"] for r in rows}) == 1 and rows[0]["source"]:
            print("Original source named by the SDG database: %s" % rows[0]["source"])


if __name__ == "__main__":
    C.run(main)
