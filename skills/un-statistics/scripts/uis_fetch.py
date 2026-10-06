#!/usr/bin/env python3
"""Fetch education (and science, culture) data from the UNESCO Institute for Statistics (UIS) Data API.

Keyless JSON API at https://api.uis.unesco.org/api/public. About 5,000 indicators, mostly
education: enrolment, completion, out-of-school, literacy, learning, teachers, spending.

  --search WORDS                      find indicators by words or codes
  --indicator CR.1 --geo NPL          data (several: --indicator CR.1,CR.2 --geo NPL,IND)
  --regions [--search WORDS]          regional geo units, e.g. "SDG: Southern Asia", "WB: South Asia"

Countries: ISO3 (NPL), ISO2 or M49 are accepted and sent as ISO3. Regions: pass the id exactly
as --regions prints it (quote it in the shell). Footnotes (the survey or census behind a value)
are included by default. The data version (UIS publishes numbered releases) is recorded in the
dataset name of the log record.

Writes <out>/data/uis_<indicators>_<geo>.csv and appends one record to <out>/data_log.jsonl.
"""
import argparse

import _common as C

API = "https://api.uis.unesco.org/api/public"

EXAMPLES = """examples:
  python3 uis_fetch.py --search completion rate primary
  python3 uis_fetch.py --indicator CR.1,CR.2 --geo NPL --start 2015
  python3 uis_fetch.py --indicator ROFST.1.CP --geo NPL,IND,BGD --start 2018
  python3 uis_fetch.py --regions --search SDG
  python3 uis_fetch.py --indicator CR.1 --geo "SDG: Central and Southern Asia" --start 2018
"""


def cmd_search(words, args):
    url = API + "/definitions/indicators"
    data = C.fetch_json(url)
    rows = []
    for ind in data:
        text = "%s %s" % (ind.get("indicatorCode", ""), ind.get("name", ""))
        if C.matches(text, words):
            tl = (ind.get("dataAvailability") or {}).get("timeLine") or {}
            rows.append({"indicator": ind.get("indicatorCode"), "name": ind.get("name"), "theme": ind.get("theme"),
                         "years": "%s-%s" % (tl.get("min", ""), tl.get("max", "")),
                         "records": (ind.get("dataAvailability") or {}).get("totalRecordCount"),
                         "updated": ind.get("lastDataUpdate")})
    # headline indicators first: CR.1 before CR.1.F before CR.1.RUR.F
    rows.sort(key=lambda r: ((r["indicator"] or "").count("."), len(r["name"] or ""), r["indicator"] or ""))
    if args.json:
        C.print_json({"url": url, "query": words, "count": len(rows), "indicators": rows})
        return
    print("UIS indicators matching %r: %d" % (words, len(rows)))
    C.print_table(rows, ["indicator", "name", "years", "records"], limit=args.limit, width=95,
                  more="use more words, --limit N or --json")
    if rows:
        print("\nNext: --indicator %s --geo NPL" % rows[0]["indicator"])


def cmd_regions(words, args):
    url = API + "/definitions/geounits"
    data = C.fetch_json(url)
    rows = [{"id": g.get("id"), "name": g.get("name"), "group": g.get("regionGroup", "")}
            for g in data if g.get("type") == "REGIONAL"]
    if words:
        rows = [r for r in rows if C.matches("%s %s" % (r["id"], r["name"]), words)]
    if args.json:
        C.print_json({"url": url, "count": len(rows), "regions": rows})
        return
    print("UIS regional geo units%s: %d" % ((" matching %r" % words) if words else "", len(rows)))
    C.print_table(rows, ["id", "group"], limit=args.limit, width=90, more="use --search or --json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", nargs="*", metavar="WORD", help="find indicators (with --regions: filter regions)")
    ap.add_argument("--regions", action="store_true", help="list regional geo unit ids")
    ap.add_argument("--indicator", action="append", help="indicator id(s), e.g. CR.1 or CR.1,CR.2")
    ap.add_argument("--geo", action="append", help="country codes (NPL) or region ids (\"SDG: Southern Asia\")")
    ap.add_argument("--start", help="first year")
    ap.add_argument("--end", help="last year")
    ap.add_argument("--no-footnotes", action="store_true", help="leave out footnotes")
    ap.add_argument("--limit", type=int, default=50, help="rows shown for --search and --regions (default 50)")
    C.add_common_args(ap)
    args = ap.parse_args()

    words = " ".join(args.search) if args.search else ""
    if args.regions:
        cmd_regions(words, args)
        return
    if args.search is not None and not args.indicator:
        if not words:
            ap.error("give words after --search")
        cmd_search(words, args)
        return
    indicators = C.split_values(args.indicator)
    if not indicators:
        ap.error("give --indicator (find one with --search WORDS)")
    geos_in = []
    for g in args.geo or []:
        # region ids contain ':' or spaces and are never split; country lists may use commas
        geos_in.extend([g.strip()] if (":" in g or " " in g.strip()) else C.split_values([g]))
    if not geos_in:
        ap.error("give --geo (e.g. NPL); without it the API returns every country and region")
    geos = [g if (":" in g or " " in g) else C.to_iso3(g) for g in geos_in]
    start, end = C.year_or_none(args.start, "--start"), C.year_or_none(args.end, "--end")

    version = (C.fetch_json(API + "/versions/default") or {}).get("version", "")
    params = [("indicator", indicators), ("geoUnit", geos), ("start", start), ("end", end),
              ("indicatorMetadata", "true"), ("footnotes", "false" if args.no_footnotes else "true"),
              ("version", version)]
    url = C.build_url(API + "/data/indicators", params)
    data = C.fetch_json(url)
    names = {m.get("indicatorCode"): m.get("name") for m in data.get("indicatorMetadata") or []}
    rows = []
    for r in data.get("records") or []:
        notes = r.get("footnotes") or []
        rows.append({"indicator": r.get("indicatorId"), "indicator_name": names.get(r.get("indicatorId"), ""),
                     "geo_unit": r.get("geoUnit"), "year": r.get("year"), "value": r.get("value"),
                     "magnitude": r.get("magnitude"), "qualifier": r.get("qualifier"),
                     "footnotes": " | ".join("%s: %s" % (n.get("subtype") or n.get("type"), n.get("value"))
                                             for n in notes if isinstance(n, dict))})
    rows.sort(key=lambda r: (r["indicator"] or "", r["geo_unit"] or "", r["year"] or 0))
    for hint in data.get("hints") or []:
        if not args.json:
            print("UIS hint: %s" % (hint if isinstance(hint, str) else hint.get("message", hint)))
    columns = ["indicator", "indicator_name", "geo_unit", "year", "value", "magnitude", "qualifier", "footnotes"]
    tag = C.period_tag(start, end)
    stem = "uis_%s_%s%s" % ("-".join(indicators), "-".join(geos), ("_" + tag) if tag else "")
    path = C.write_csv(rows, columns, args.out, stem) if rows else None
    requested = "%s:%s" % (start or "", end or "") if (start or end) else ""
    log = C.log_data(args.out, "UNESCO UIS Data API (version %s)" % version if version else "UNESCO UIS Data API",
                     ",".join(indicators), ",".join(geos), C.period_of((r["year"] for r in rows), requested),
                     url, len(rows), path)
    C.report(args, rows, columns, ["indicator", "geo_unit", "year", "value", "qualifier", "footnotes"], log)


if __name__ == "__main__":
    C.run(main)
