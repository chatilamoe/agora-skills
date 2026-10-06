#!/usr/bin/env python3
"""Fetch Eurostat data (EU statistics API, JSON-stat, keyless) into a tidy CSV.

  --search WORDS                         find datasets in Eurostat's table of contents
  --dataset une_rt_a --dims              the dataset's dimensions and the codes in use
  --dataset une_rt_a --filter geo=DE,EL --filter sex=T ... [--start/--end/--last]   the data

Every dimension you do not filter comes back in full, so filter all of them except time
(--dims lists them). --geo is a shortcut for the geo filter that also accepts ISO3 codes and
converts them: Eurostat uses ISO2 except EL (Greece) and UK (United Kingdom), plus aggregates
such as EU27_2020, EA20, EA21. An unknown code (GR) is not an error: it silently returns nothing.

Periods: --start/--end (2019, 2019-Q1, 2019-01) or --last N. Status flags come back in the
'status' column (b break in series, e estimated, p provisional, u low reliability, ...).
The dataset DOI (10.2908/...) is printed and logged for citation.

Writes <out>/data/eurostat_<dataset>_<filters>.csv and appends one record to <out>/data_log.jsonl.
"""
import argparse
import csv
import io
import json
import re

import _common as C
import _sdmx as X

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
SDMX = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
TOC = "https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en"
GEO_FIX = {"GR": "EL", "GB": "UK"}

EXAMPLES = """examples:
  python3 eurostat_fetch.py --search unemployment sex age annual
  python3 eurostat_fetch.py --dataset une_rt_a --dims
  python3 eurostat_fetch.py --dataset une_rt_a --geo DEU,GRC --filter age=Y15-74 --filter unit=PC_ACT --filter sex=T --start 2019
  python3 eurostat_fetch.py --dataset prc_hicp_minr --geo EA,DE,FR --filter unit=RCH_A --filter coicop18=TOTAL --last 3
"""


def to_geo(token):
    t = token.strip()
    if t.upper() in ("EL", "UK") or re.match(r"^(EU|EA|EFTA|EEA)", t.upper()):
        return t.upper()
    row = C.lookup_country(t)
    if not row:
        return t
    return GEO_FIX.get(row["iso2"], row["iso2"])


def cmd_search(words, args):
    text = C.fetch_text(TOC)
    rows, seen = [], set()
    for rec in csv.DictReader(io.StringIO(text), delimiter="\t"):
        kind = (rec.get("type") or "").strip()
        code = (rec.get("code") or "").strip()
        title = (rec.get("title") or "").strip()
        if kind not in ("dataset", "table") or code in seen:
            continue
        if C.matches(title + " " + code, words):
            seen.add(code)
            rows.append({"code": code, "title": title, "type": kind,
                         "data": "%s to %s" % ((rec.get("data start") or "").strip(), (rec.get("data end") or "").strip()),
                         "updated": (rec.get("last update of data") or "").strip()})
    if args.json:
        C.print_json({"url": TOC, "query": words, "count": len(rows), "datasets": rows})
        return
    print("Eurostat datasets matching %r: %d" % (words, len(rows)))
    C.print_table(rows, ["code", "title", "data", "updated"], limit=args.limit, width=90,
                  more="use more words, --limit N or --json")
    if rows:
        print("\nNext: --dataset %s --dims" % rows[0]["code"])


def cmd_dims(dataset, args):
    url = "%s/dataflow/ESTAT/%s/latest?references=descendants&detail=referencepartial" % (SDMX, dataset)
    body, _ = C.fetch(url, accept=X.ACCEPT_STRUCTURE)
    st = X.parse_structure(body, dataset)
    rows = [{"dimension": d["id"], "codes": len(d["codes"]),
             "examples": ", ".join("%s=%s" % kv for kv in list(d["codes"].items())[:8])}
            for d in st["dimensions"] if not d["time"]]
    if args.json:
        C.print_json({"dataset": dataset, "name": st["name"], "url": url,
                      "dimensions": [{"dimension": d["id"], "codes": d["codes"]} for d in st["dimensions"] if not d["time"]]})
        return
    print("Eurostat %s: %s" % (dataset, st["name"]))
    print("Filter each of these (codes in use; --json lists every code):\n")
    C.print_table(rows, ["dimension", "codes", "examples"], limit=100, width=120)


def parse_jsonstat(d):
    ids, sizes = d["id"], d["size"]
    cats = []
    for dim in ids:
        cat = d["dimension"][dim]["category"]
        index = cat.get("index")
        if isinstance(index, list):
            pos_to_code = dict(enumerate(index))
        elif isinstance(index, dict):
            pos_to_code = {v: k for k, v in index.items()}
        else:
            pos_to_code = {0: next(iter(cat.get("label", {"": ""})))}
        cats.append((pos_to_code, cat.get("label") or {}))
    strides = [1] * len(sizes)
    for k in range(len(sizes) - 2, -1, -1):
        strides[k] = strides[k + 1] * sizes[k + 1]
    values = d.get("value")
    status = d.get("status") or {}
    items = values.items() if isinstance(values, dict) else enumerate(values or [])
    time_dim = "time" if "time" in ids else ids[-1]
    rows = []
    for flat, val in items:
        flat = int(flat)
        st = status.get(str(flat), "") if isinstance(status, dict) else (status[flat] if flat < len(status) else "")
        if val is None and not st:
            continue
        row = {}
        for k, dim in enumerate(ids):
            pos = (flat // strides[k]) % sizes[k]
            code = cats[k][0].get(pos, "")
            if dim == time_dim:
                row["time"] = code
            else:
                row[dim] = code
                row[dim + "_label"] = cats[k][1].get(code, "")
        row["value"] = "" if val is None else val
        row["status"] = st or ""
        rows.append(row)
    dims = [x for x in ids if x != time_dim]
    columns = []
    for dim in dims:
        columns += [dim, dim + "_label"]
    columns += ["time", "value", "status"]
    rows.sort(key=lambda r: tuple(str(r.get(x, "")) for x in dims) + (str(r.get("time")),))
    return rows, columns, dims


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLES,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", nargs="+", metavar="WORD", help="find datasets by words or code")
    ap.add_argument("--dataset", help="dataset code, e.g. une_rt_a")
    ap.add_argument("--dims", action="store_true", help="show the dataset's dimensions and codes in use")
    ap.add_argument("--filter", action="append", metavar="DIM=CODES", help="e.g. sex=T or geo=DE,FR (repeat)")
    ap.add_argument("--geo", help="countries/aggregates; ISO3 or ISO2 converted to Eurostat codes")
    ap.add_argument("--start", help="first period: 2019, 2019-Q1, 2019-01")
    ap.add_argument("--end", help="last period")
    ap.add_argument("--last", type=int, help="last N periods")
    ap.add_argument("--limit", type=int, default=50, help="rows shown for --search (default 50)")
    C.add_common_args(ap)
    args = ap.parse_args()

    if args.search:
        cmd_search(" ".join(args.search), args)
        return
    if not args.dataset:
        ap.error("give --dataset (find one with --search WORDS)")
    if args.dims:
        cmd_dims(args.dataset, args)
        return
    filters = []
    for f in args.filter or []:
        if "=" not in f:
            ap.error("--filter takes DIM=CODES, e.g. sex=T or geo=DE,FR")
        dim, codes = f.split("=", 1)
        filters.append((dim.strip(), C.split_values([codes])))
    if args.geo:
        filters.append(("geo", [to_geo(g) for g in C.split_values([args.geo])]))
    if not filters:
        ap.error("give --filter and/or --geo (run --dims first); an unfiltered dataset can be very large")
    params = [(dim, codes) for dim, codes in filters]
    params += [("sinceTimePeriod", args.start), ("untilTimePeriod", args.end), ("lastTimePeriod", args.last),
               ("lang", "en")]
    url = C.build_url("%s/%s" % (API, args.dataset), params)
    try:
        d = C.fetch_json(url)
    except C.FetchError as err:
        try:
            labels = [e.get("label") for e in json.loads(err.body).get("error", [])]
        except (ValueError, AttributeError, TypeError):
            labels = []
        if labels:
            raise C.FetchError("Eurostat: %s" % "; ".join(l for l in labels if l), err.status, err.body, url)
        raise
    rows, columns, dims = parse_jsonstat(d)
    doi = ""
    m = re.search(r"10\.2908/[A-Za-z0-9_.-]+", json.dumps(d.get("extension") or {}))
    if m:
        doi = m.group(0)
    geos = [c for dim, codes in filters if dim == "geo" for c in codes]
    stem = "eurostat_%s_%s" % (args.dataset, "_".join("%s-%s" % (dim, "-".join(codes)) for dim, codes in filters))
    tag = C.period_tag(args.start, args.end, args.last)
    if tag:
        stem += "_" + tag
    path = C.write_csv(rows, columns, args.out, stem) if rows else None
    dataset = "Eurostat %s%s" % (args.dataset, (", doi:%s" % doi) if doi else "")
    indicator = ";".join("%s=%s" % (dim, ",".join(codes)) for dim, codes in filters if dim != "geo") or args.dataset
    requested = "%s:%s" % (args.start or "", args.end or "") if (args.start or args.end) else ""
    log = C.log_data(args.out, dataset, indicator, ",".join(geos), C.period_of((r["time"] for r in rows), requested),
                     url, len(rows), path)
    if not args.json:
        print("%s: %s (updated %s)%s\n" % (args.dataset, d.get("label", ""), d.get("updated", ""),
                                           ("; DOI https://doi.org/" + doi) if doi else ""))
        empty = [dim for dim, size in zip(d.get("id", []), d.get("size", [])) if size == 0]
        if empty:
            print("No codes matched for dimension(s): %s. Check the codes with --dims (Greece is EL, not GR).\n"
                  % ", ".join(empty))
    varying = [x for x in dims if len({r.get(x) for r in rows}) > 1] or dims[-1:]
    view = []
    for x in varying:
        view += [x, x + "_label"]
    view += ["time", "value", "status"]
    C.report(args, rows, columns, view, log, extra={"doi": doi, "label": d.get("label"), "updated": d.get("updated")})


if __name__ == "__main__":
    try:
        C.run(main)
    except X.SDMXError as err:
        C.die(str(err))
