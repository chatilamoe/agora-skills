#!/usr/bin/env python3
"""Fetch health data from the WHO Global Health Observatory (GHO) OData API (keyless).

About 3,000 indicators: life expectancy, mortality, disease burden, immunisation, nutrition,
health systems, risk factors. Data are filtered on the server with OData $filter.

  --search WORDS                         find indicators by words or code
  --indicator WHOSIS_000001 --country NPL     data (several countries: --country NPL,IND)
  --countries [--search WORDS]           country codes (ISO3) and WHO regions

Countries: ISO3 (NPL), ISO2 or M49 are accepted. WHO regions (SEAR, AFR, AMR, EMR, EUR, WPR)
and GLOBAL pass through as given. Many indicators are split by sex (Dim1 = SEX_BTSX both sexes,
SEX_MLE, SEX_FMLE) or by age or other dimensions; --dim1 keeps one value. --filter adds any
OData condition, e.g. "Dim2 eq 'AGEGROUP_YEARS15-49'".

Writes <out>/data/who_<indicator>_<countries>.csv and appends one record to <out>/data_log.jsonl.
"""
import argparse

import _common as C

API = "https://ghoapi.azureedge.net/api"

EXAMPLES = """examples:
  python3 who_fetch.py --search life expectancy
  python3 who_fetch.py --indicator WHOSIS_000001 --country NPL --start 2015 --dim1 SEX_BTSX
  python3 who_fetch.py --indicator MDG_0000000001 --country NPL,IND,BGD --start 2020
  python3 who_fetch.py --indicator WHS4_100 --country SEAR --start 2020
  python3 who_fetch.py --countries --search nepal
"""


def cmd_search(words, args):
    url = API + "/Indicator"
    data = C.fetch_json(url).get("value") or []
    rows = [{"indicator": d.get("IndicatorCode"), "name": d.get("IndicatorName")} for d in data
            if C.matches("%s %s" % (d.get("IndicatorCode"), d.get("IndicatorName")), words)]
    rows.sort(key=lambda r: len(r["name"] or ""))
    if args.json:
        C.print_json({"url": url, "query": words, "count": len(rows), "indicators": rows})
        return
    print("WHO GHO indicators matching %r: %d" % (words, len(rows)))
    C.print_table(rows, ["indicator", "name"], limit=args.limit, width=110, more="use more words, --limit N or --json")
    if rows:
        print("\nNext: --indicator %s --country NPL" % rows[0]["indicator"])


def cmd_countries(words, args):
    rows = []
    for dim in ("COUNTRY", "REGION"):
        url = "%s/DIMENSION/%s/DimensionValues" % (API, dim)
        for d in C.fetch_json(url).get("value") or []:
            rows.append({"code": d.get("Code"), "name": d.get("Title"), "type": dim,
                         "parent": d.get("ParentTitle") or ""})
    if words:
        rows = [r for r in rows if C.matches("%s %s" % (r["code"], r["name"]), words)]
    if args.json:
        C.print_json({"count": len(rows), "areas": rows})
        return
    C.print_table(rows, ["code", "name", "type", "parent"], limit=args.limit, width=60, more="use --search or --json")


def odata_quote(value):
    return "'%s'" % str(value).replace("'", "''")


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", nargs="*", metavar="WORD", help="find indicators (with --countries: filter)")
    ap.add_argument("--countries", action="store_true", help="list country and region codes")
    ap.add_argument("--indicator", help="indicator code, e.g. WHOSIS_000001 (life expectancy at birth)")
    ap.add_argument("--country", action="append", help="ISO3 codes, WHO regions (SEAR) or GLOBAL")
    ap.add_argument("--start", help="first year")
    ap.add_argument("--end", help="last year")
    ap.add_argument("--dim1", help="keep one Dim1 value, e.g. SEX_BTSX (both sexes)")
    ap.add_argument("--filter", help="extra OData condition, joined with 'and'")
    ap.add_argument("--limit", type=int, default=50, help="rows shown for --search and --countries (default 50)")
    C.add_common_args(ap)
    args = ap.parse_args()

    words = " ".join(args.search) if args.search else ""
    if args.countries:
        cmd_countries(words, args)
        return
    if args.search is not None and not args.indicator:
        if not words:
            ap.error("give words after --search")
        cmd_search(words, args)
        return
    if not args.indicator:
        ap.error("give --indicator (find one with --search WORDS)")
    places = [C.to_iso3(c) if C.lookup_country(c) else c.upper() for c in C.split_values(args.country)]
    start, end = C.year_or_none(args.start, "--start"), C.year_or_none(args.end, "--end")
    conds = []
    if places:
        conds.append("(" + " or ".join("SpatialDim eq %s" % odata_quote(p) for p in places) + ")")
    if start is not None:
        conds.append("TimeDim ge %d" % start)
    if end is not None:
        conds.append("TimeDim le %d" % end)
    if args.dim1:
        conds.append("Dim1 eq %s" % odata_quote(args.dim1))
    if args.filter:
        conds.append("(%s)" % args.filter)
    if not conds:
        ap.error("give --country or a period; an unfiltered indicator can be tens of megabytes")

    meta = C.fetch_json(C.build_url(API + "/Indicator", {"$filter": "IndicatorCode eq %s" % odata_quote(args.indicator)}))
    name = ((meta.get("value") or [{}])[0] or {}).get("IndicatorName", "")
    url = C.build_url("%s/%s" % (API, args.indicator), {"$filter": " and ".join(conds)})
    records, next_url = [], url
    while next_url:
        data = C.fetch_json(next_url)
        records.extend(data.get("value") or [])
        next_url = data.get("@odata.nextLink")
    rows = []
    for r in records:
        rows.append({"indicator": r.get("IndicatorCode"), "indicator_name": name,
                     "area_type": r.get("SpatialDimType"), "area": r.get("SpatialDim"),
                     "parent_location": r.get("ParentLocation"), "year": r.get("TimeDim"),
                     "dim1_type": r.get("Dim1Type"), "dim1": r.get("Dim1"),
                     "dim2_type": r.get("Dim2Type"), "dim2": r.get("Dim2"),
                     "dim3_type": r.get("Dim3Type"), "dim3": r.get("Dim3"),
                     "numeric_value": r.get("NumericValue"), "value_text": r.get("Value"),
                     "low": r.get("Low"), "high": r.get("High"), "comments": r.get("Comments"),
                     "updated": r.get("Date")})
    rows.sort(key=lambda r: (str(r["area"]), str(r["dim1"]), str(r["dim2"]), str(r["dim3"]), r["year"] or 0))
    columns = list(rows[0].keys()) if rows else ["indicator", "area", "year", "numeric_value"]
    view = ["area", "year", "dim1", "numeric_value", "value_text"]
    if rows and any(r["dim2"] for r in rows):
        view.insert(3, "dim2")
    tag = C.period_tag(start, end)
    stem = "who_%s_%s%s%s" % (args.indicator, "-".join(places) or "all", ("_" + tag) if tag else "",
                              ("_" + args.dim1) if args.dim1 else "")
    path = C.write_csv(rows, columns, args.out, stem) if rows else None
    requested = "%s:%s" % (start or "", end or "") if (start or end) else ""
    log = C.log_data(args.out, "WHO Global Health Observatory", args.indicator, ",".join(places),
                     C.period_of((r["year"] for r in rows), requested), url, len(rows), path)
    if not args.json and name:
        print("%s: %s\n" % (args.indicator, name))
    C.report(args, rows, columns, view, log)
    if not args.json and rows and len({r["dim1"] for r in rows}) > 1:
        print("Rows differ by %s; use --dim1 to keep one (e.g. SEX_BTSX)." % (rows[0]["dim1_type"] or "Dim1"))


if __name__ == "__main__":
    C.run(main)
