#!/usr/bin/env python3
"""List the IMF's SDMX dataflows (datasets) and filter them by keyword.

A dataflow is what you pass to imf_dimensions.py and imf_fetch.py, written AGENCY,ID
(for example IMF.RES,WEO for the World Economic Outlook). The list comes from
https://api.imf.org/external/sdmx/2.1/dataflow/all/all/all (all versions; the script keeps
the newest version of each). Dated snapshots such as WEO_2025_OCT_VINTAGE are hidden
unless you ask for --vintages.

Writes: <out>/catalog/imf_dataflows.csv (every dataflow, newest version, vintages included).
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (BASE, STR, en_text, get_xml, print_json, print_table, run, say,  # noqa: E402
                     version_key, write_csv, die)

EPILOG = """examples:
  python3 imf_dataflows.py                      # every current dataflow
  python3 imf_dataflows.py price                # keyword in id, name or description
  python3 imf_dataflows.py "balance of payments"
  python3 imf_dataflows.py --agency IMF.RES     # one IMF department
  python3 imf_dataflows.py weo --vintages       # include dated snapshots (vintages)
  python3 imf_dataflows.py fiscal --json
"""

COLUMNS = ["flow", "agency", "id", "version", "name", "is_vintage", "structure", "description"]


def is_vintage(flow_id):
    return flow_id.upper().endswith("_VINTAGE")


def fetch_dataflows():
    """Every dataflow, newest version of each, as dicts."""
    root = get_xml(f"{BASE}/dataflow/all/all/all")
    if root is None:
        die("the IMF API returned no dataflows")
    newest = {}
    for d in root.iter(STR + "Dataflow"):
        key = (d.get("agencyID"), d.get("id"))
        if key in newest and version_key(newest[key].get("version")) >= version_key(d.get("version")):
            continue
        newest[key] = d
    rows = []
    for (agency, fid), d in newest.items():
        ref = d.find(STR + "Structure/Ref")
        dsd = f"{ref.get('agencyID')}:{ref.get('id')}({ref.get('version')})" if ref is not None else ""
        rows.append({
            "flow": f"{agency},{fid}", "agency": agency, "id": fid, "version": d.get("version"),
            "name": en_text(d, "Name"), "is_vintage": is_vintage(fid), "structure": dsd,
            "description": en_text(d, "Description"),
        })
    rows.sort(key=lambda r: (r["agency"], r["id"]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keywords", nargs="*", help="words that must all appear in the id, name or description")
    ap.add_argument("--agency", help="only this agency, e.g. IMF.RES (research), IMF.STA (statistics), IMF.FAD (fiscal)")
    ap.add_argument("--vintages", action="store_true", help="also show dated snapshots (ids ending in _VINTAGE)")
    ap.add_argument("--out", default="research", metavar="DIR", help="folder for files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_args()

    rows = fetch_dataflows()
    catalog = write_csv(pathlib.Path(a.out) / "catalog" / "imf_dataflows.csv", rows, COLUMNS)

    words = [w.lower() for w in a.keywords]
    shown, hidden_vintages = [], 0
    for r in rows:
        if a.agency and r["agency"].lower() != a.agency.lower():
            continue
        text = f"{r['flow']} {r['name']} {r['description']}".lower()
        if not all(w in text for w in words):
            continue
        if r["is_vintage"] and not a.vintages:
            hidden_vintages += 1
            continue
        shown.append(r)

    if a.json:
        print_json([{k: r[k] for k in COLUMNS} for r in shown])
    else:
        print_table(shown, [("FLOW", "flow", 34), ("VERSION", "version", 8), ("NAME", "name", 90)])
    note = f"{len(shown)} of {len(rows)} dataflows"
    if hidden_vintages:
        note += f"; {hidden_vintages} dated vintage snapshot(s) hidden (add --vintages)"
    say(f"\n{note}. Full list: {catalog.as_posix()}", a.json)
    if not shown:
        say("Nothing matched. Try one broader word; names are in English (e.g. 'price', 'trade', 'debt').", a.json)
        return 1
    return 0


if __name__ == "__main__":
    run(main)
