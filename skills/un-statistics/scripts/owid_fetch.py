#!/usr/bin/env python3
"""Fetch the data behind an Our World in Data (OWID) chart, with its metadata and citation.

OWID republishes data from the UN, World Bank, IMF, academic projects and others, often
harmonised into long series. Each chart has a slug: the last part of its URL,
https://ourworldindata.org/grapher/<slug>.

  --search WORDS                                  find charts (slug, title)
  --slug life-expectancy --country NPL,IND [--start 2000 --end 2023]

The script downloads <slug>.csv?csvType=full (every entity and year) and filters it here,
because csvType=filtered follows the chart's default view (for map charts: one year, all
countries) and ignores the country selection. It also saves <slug>.metadata.json, which
carries OWID's citation and the original sources: cite the original source as OWID asks.

Countries: ISO3 codes (OWID uses ISO3; aggregates have OWID_ codes such as OWID_WRL, or none)
or exact entity names ("World", "South Asia (WB)").

Writes <out>/data/owid_<slug>_<countries>.csv (+ .metadata.json) and appends one record to
<out>/data_log.jsonl.
"""
import argparse
import csv
import io
import json
import pathlib

import _common as C

SITE = "https://ourworldindata.org"

EXAMPLES = """examples:
  python3 owid_fetch.py --search extreme poverty
  python3 owid_fetch.py --slug gdp-per-capita-worldbank --country NPL,IND --start 2015
  python3 owid_fetch.py --slug life-expectancy --country NPL,World --start 2000 --end 2023
"""


def cmd_search(words, args):
    url = C.build_url(SITE + "/api/search", [("q", words), ("type", "charts"), ("hitsPerPage", args.limit)])
    data = C.fetch_json(url)
    rows = [{"slug": r.get("slug"), "title": r.get("title"), "variant": r.get("variantName") or "",
             "updated": (r.get("updatedAt") or "")[:10]}
            for r in data.get("results") or [] if r.get("type") == "chart"]
    if args.json:
        C.print_json({"url": url, "query": words, "hits": data.get("nbHits"), "charts": rows})
        return
    print("OWID charts matching %r: %s hits, first %d shown" % (words, data.get("nbHits"), len(rows)))
    C.print_table(rows, ["slug", "title", "variant", "updated"], limit=args.limit, width=70)
    if rows:
        print("\nNext: --slug %s --country NPL" % rows[0]["slug"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", nargs="+", metavar="WORD", help="find charts by words")
    ap.add_argument("--slug", help="chart slug, e.g. life-expectancy")
    ap.add_argument("--country", action="append", help="ISO3 codes or entity names (World)")
    ap.add_argument("--start", help="first year")
    ap.add_argument("--end", help="last year")
    ap.add_argument("--limit", type=int, default=20, help="charts shown for --search (default 20)")
    C.add_common_args(ap)
    args = ap.parse_args()

    if args.search:
        cmd_search(" ".join(args.search), args)
        return
    if not args.slug:
        ap.error("give --slug (find one with --search WORDS)")
    slug = args.slug.strip().rstrip("/").split("/")[-1].split("?")[0]
    wanted = C.split_values(args.country)
    start, end = C.year_or_none(args.start, "--start"), C.year_or_none(args.end, "--end")

    url = C.build_url("%s/grapher/%s.csv" % (SITE, slug), [("csvType", "full")])
    try:
        text = C.fetch_text(url)
    except C.FetchError as err:
        if err.status == 404:
            raise C.FetchError("OWID has no chart %r (HTTP 404); find the slug with --search" % slug, 404, err.body, url)
        raise
    meta_url = "%s/grapher/%s.metadata.json" % (SITE, slug)
    meta = C.fetch_json(meta_url)

    reader = csv.DictReader(io.StringIO(text))
    columns = list(reader.fieldnames or [])
    if len(columns) < 3:
        raise C.FetchError("unexpected CSV from OWID for %r: %s" % (slug, C.snippet(text, 200)), None, text, url)
    ent_col, code_col, year_col = columns[0], columns[1], columns[2]
    keys = {w.casefold() for w in wanted} | {C.to_iso3(w).casefold() for w in wanted if C.lookup_country(w)}
    rows, found = [], set()
    for r in reader:
        if keys and (r.get(code_col) or "").casefold() not in keys and (r.get(ent_col) or "").casefold() not in keys:
            continue
        try:
            year = int(r.get(year_col))
        except (TypeError, ValueError):
            year = None
        if year is not None and ((start is not None and year < start) or (end is not None and year > end)):
            continue
        rows.append(r)
        found.add(r.get(code_col) or r.get(ent_col))
    missing = [w for w in wanted if w.casefold() not in {f.casefold() for f in found if f}
               and C.to_iso3(w).casefold() not in {f.casefold() for f in found if f}
               and not any((r.get(ent_col) or "").casefold() == w.casefold() for r in rows)]

    chart = meta.get("chart") or {}
    value_cols = [c for c in columns[3:]]
    citation = chart.get("citation") or ""
    sources = []
    for name, col in (meta.get("columns") or {}).items():
        sources.append({"column": name, "citation": col.get("citationLong") or col.get("citationShort") or "",
                        "unit": col.get("unit") or "", "last_updated": col.get("lastUpdated") or "",
                        "next_update": col.get("nextUpdate") or ""})
    tag = C.period_tag(start, end)
    stem = "owid_%s_%s%s" % (slug, "-".join(wanted) or "all", ("_" + tag) if tag else "")
    path = C.write_csv(rows, columns, args.out, stem) if rows else None
    if path:
        meta_path = pathlib.Path(path).with_suffix(".metadata.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    entities = C.joined((r.get(code_col) or r.get(ent_col)) for r in rows)
    requested = "%s:%s" % (start or "", end or "") if (start or end) else ""
    log = C.log_data(args.out, "Our World in Data: %s (%s)" % (chart.get("title") or slug, citation or "see metadata"),
                     slug, entities or ",".join(wanted), C.period_of((r.get(year_col) for r in rows), requested),
                     url, len(rows), path)
    if not args.json:
        print("%s\n%s\n" % (chart.get("title") or slug, chart.get("subtitle") or ""))
    C.report(args, rows, columns, [ent_col, year_col] + value_cols[:3], log,
             extra={"citation": citation, "sources": sources, "metadata_url": meta_url})
    if not args.json:
        if missing:
            print("Not found in this chart: %s" % ", ".join(missing))
        for s in sources:
            if s["citation"]:
                print("Source (%s): %s [updated %s]" % (s["column"], s["citation"], s["last_updated"]))
        if path:
            print("Metadata saved next to the CSV (.metadata.json).")


if __name__ == "__main__":
    C.run(main)
