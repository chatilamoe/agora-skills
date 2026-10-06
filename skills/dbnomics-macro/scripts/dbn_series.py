#!/usr/bin/env python3
"""Download DBnomics series into one tidy CSV (provider, dataset, series_code, series_name,
frequency, period, value) and log the file in research/data_log.jsonl.

Give either
  - one or more exact series IDs, PROVIDER/DATASET/SERIES (up to 50), fetched in one call to
    /series?series_ids=...&observations=1, or
  - one series code mask, fetched from /series/PROVIDER/DATASET/MASK?observations=1:
    '+' joins codes (NPL+IND+BGD) and an empty position means all codes (NPL..).
Find IDs with dbn_search.py or dbn_dataset.py.

DBnomics has no period filter, so --start/--end are applied here, on each observation's
first day. Missing values ("NA") are left out.

Writes: <out>/data/dbn_<...>.csv and one line in <out>/data_log.jsonl.
"""
import argparse
import pathlib
import sys
import time
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (BASE, PAGE_SLEEP, build_url, die, entity_of, get_json, joined, log_data,  # noqa: E402
                     period_bound, print_json, print_table, quote_path, run, safe_name, say,
                     split_series_id, today, write_csv)

EPILOG = """examples:
  python3 dbn_series.py IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change --start 2015
  python3 dbn_series.py "IMF/WEO:2025-04/NPL+IND+BGD.NGDP_RPCH.pcent_change" --start 2020 --end 2025
  python3 dbn_series.py WB/WDI/A-NY.GDP.MKTP.KD.ZG-NPL IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change --start 2019
  python3 dbn_series.py ECB/EXR/D.USD.EUR.SP00.A --start 2026-09-01
  python3 dbn_series.py OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD/Q.Y.USA.S1.S1.B1GQ._Z._Z._Z.PC.L.G1.T0102 --start 2025-Q1 --json
"""

COLUMNS = ["provider", "dataset", "series_code", "series_name", "frequency", "period", "value"]
MAX_IDS = 50


def is_mask(code):
    return "+" in code or ".." in code or code.startswith(".") or code.endswith(".") or '"' in code


def fetch_all(url):
    """Series docs from a /series call, following offset paging (1000 per page)."""
    docs, errors, offset = [], [], 0
    while True:
        page = get_json(url if not offset else build_url(url, {"offset": offset}))
        errors += page.get("errors") or []
        s = page.get("series") or {}
        batch = s.get("docs", [])
        docs += batch
        offset += len(batch)
        if not batch or offset >= s.get("num_found", 0):
            return docs, errors
        time.sleep(PAGE_SLEEP)


def frequency_of(doc):
    if doc.get("@frequency"):
        return doc["@frequency"]
    dims = {str(k).lower(): v for k, v in (doc.get("dimensions") or {}).items()}
    return str(dims.get("freq") or dims.get("frequency") or "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("series", nargs="+", help="PROVIDER/DATASET/SERIES IDs, or one PROVIDER/DATASET/MASK")
    ap.add_argument("--start", help="first period kept: YYYY, YYYY-MM, YYYY-Qn or YYYY-MM-DD")
    ap.add_argument("--end", help="last period kept, same formats")
    ap.add_argument("--file", help="CSV file name to write in <out>/data/ (default: built from the IDs)")
    ap.add_argument("--out", default="research", metavar="DIR", help="folder for files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_args()

    ids = [split_series_id(s) for s in a.series]
    start, end = period_bound(a.start), period_bound(a.end, end=True)
    if len(ids) == 1:
        p, d, code = ids[0]
        url = build_url(f"{BASE}/series/{quote_path(p)}/{quote_path(d)}/{quote_path(code)}",
                        {"observations": 1, "metadata": 0, "limit": 1000})
    else:
        if any(is_mask(c) for _, _, c in ids):
            die("give one mask on its own, or several exact series IDs (a mask uses '+' or empty positions)")
        if len(ids) > MAX_IDS:
            die(f"at most {MAX_IDS} series IDs per run; split the list")
        url = build_url(f"{BASE}/series", {"series_ids": ",".join("/".join(i) for i in ids),
                                           "observations": 1, "metadata": 0, "limit": 1000})
    docs, errors = fetch_all(url)
    for e in errors:
        where = "/".join(str(e.get(k) or "") for k in ("provider_code", "dataset_code", "series_code")).rstrip("/")
        say(f"warning: {where}: {e.get('message', 'not loaded')}" + (f" ({e['cause']})" if e.get("cause") else ""),
            True)

    rows, series_info, skipped = [], [], 0
    for doc in docs:
        p, d, code = doc.get("provider_code", ""), doc.get("dataset_code", ""), doc.get("series_code", "")
        name, freq = doc.get("series_name", ""), frequency_of(doc)
        periods, days, values = doc.get("period") or [], doc.get("period_start_day") or [], doc.get("value") or []
        kept = []
        for i, (per, val) in enumerate(zip(periods, values)):
            day = days[i] if i < len(days) else str(per)
            if (start and day < start) or (end and day > end):
                continue
            if val is None or val == "NA":
                skipped += 1
                continue
            kept.append(per)
            rows.append({"provider": p, "dataset": d, "series_code": code, "series_name": name,
                         "frequency": freq, "period": per, "value": val})
        series_info.append({"id": f"{p}/{d}/{code}", "provider": p, "dataset": d, "series_code": code,
                            "dataset_name": doc.get("dataset_name", ""),
                            "series_name": name, "frequency": freq, "entity": entity_of(doc.get("dimensions")),
                            "indexed_at": (doc.get("indexed_at") or "")[:10], "observations": len(kept),
                            "first": kept[0] if kept else None, "last": kept[-1] if kept else None,
                            "last_available": next((per for per, val in zip(reversed(periods), reversed(values))
                                                    if val is not None and val != "NA"), None)})

    if not docs:
        die("no series found. Check the IDs with dbn_dataset.py or dbn_search.py (codes are case-sensitive).")
    if not rows:
        die(f"{len(docs)} series found but no values from {a.start or 'the first period'} to {a.end or 'the latest'}; "
            f"latest available: " + ", ".join(f"{s['id']} {s['last_available']}" for s in series_info[:5]))

    if a.file:
        fname = a.file if a.file.endswith(".csv") else a.file + ".csv"
    else:
        span = f"_{a.start or ''}-{a.end or ''}" if (a.start or a.end) else ""
        if len(ids) == 1:
            base = f"dbn_{safe_name(ids[0][0])}_{safe_name(ids[0][1])}_{safe_name(ids[0][2])}"
        else:
            tag = format(zlib.crc32(",".join(a.series).encode()) & 0xFFFFFFFF, "08x")
            base = f"dbn_{len(ids)}series_{tag}"
        fname = f"{base}{safe_name(span) if span else ''}.csv"
    path = write_csv(pathlib.Path(a.out) / "data" / fname, rows, COLUMNS)

    periods = [r["period"] for r in rows]
    datasets = joined(f"{s['provider']}/{s['dataset']}" for s in series_info if s["observations"])
    indexed = joined(f"{s['provider']}/{s['dataset']} indexed {s['indexed_at']}" for s in series_info
                     if s["observations"])
    record = {
        "source": "dbnomics-macro", "dataset": datasets,
        "indicator": joined(s["series_code"] for s in series_info if s["observations"]),
        "entity": joined(s["entity"] for s in series_info if s["observations"] and s["entity"]),
        "period": f"{min(periods)}:{max(periods)}", "url": url, "accessed": today(), "rows": len(rows),
        "file": path.as_posix(),
        "notes": f"via DBnomics (a copy of the provider's data, refreshed on DBnomics' schedule); {indexed}",
    }
    log = log_data(a.out, record)

    if a.json:
        out_rows = [dict(r, value=float(r["value"]) if isinstance(r["value"], (int, float)) else r["value"])
                    for r in rows]
        print_json({"url": url, "file": path.as_posix(), "series": series_info, "rows": out_rows})
    else:
        print_table(rows[:30], [("SERIES", "series_code", 44), ("PERIOD", "period", 11), ("VALUE", "value", 18)])
        if len(rows) > 30:
            print(f"... {len(rows) - 30} more rows in the file")
        print()
        for s in series_info:
            print(f"{s['id']}: {s['observations']} values {s['first'] or ''} to {s['last'] or ''} "
                  f"(latest available {s['last_available']}; DBnomics indexed {s['indexed_at']})")
            print(f"   {s['series_name']}")
    say(f"\n{len(rows)} rows from {sum(1 for s in series_info if s['observations'])} series -> {path.as_posix()} "
        f"(logged in {log.as_posix()})", a.json)
    if skipped:
        say(f"{skipped} missing values (NA) left out", a.json)
    for s in [s for s in series_info if s["observations"]][:5]:
        span = s["first"] if s["first"] == s["last"] else f"{s['first']}:{s['last']}"
        dataset = f"{s['provider']} {s['dataset_name']} via DBnomics [{s['provider']}/{s['dataset']}]"
        say(f"Cite as: ({dataset}, {s['series_code']}, {s['entity'] or '<entity>'}, "
            f"{span}, retrieved {today()}, "
            f"{BASE}/series/{quote_path(s['provider'])}/{quote_path(s['dataset'])}/{quote_path(s['series_code'])}"
            f"?observations=1)", a.json)
    return 0


if __name__ == "__main__":
    run(main)
