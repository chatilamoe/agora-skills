#!/usr/bin/env python3
"""Show how to build a data key for an IMF dataflow: its dimensions in key order and,
for each, the codes (with English names) that actually have data.

Two calls:
  1. /dataflow/{agency}/{id}/latest?references=descendants   structure: dimensions, concepts, codelists
  2. /availableconstraint/{agency},{id}/{key}                which codes have data (and how many series)

A key is the dimension codes in this order joined by '.', for example NPL.NGDP_RPCH.A for
WEO (COUNTRY.INDICATOR.FREQUENCY). Use + for several codes (NPL+IND) and leave a position
empty for all codes (NPL..A). Pass the key to imf_fetch.py.

Writes: <out>/catalog/imf_codes_<AGENCY>_<ID>.csv (every code of every dimension, with a has_data flag).
"""
import argparse
import datetime
import pathlib
import sys
import time
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (BASE, COM, PAGE_SLEEP, STR, FetchError, die, en_text, get_xml, legacy_hint, print_json,  # noqa: E402
                     resolve_flow, run, safe_name, say, script_path, write_csv)

EPILOG = """examples:
  python3 imf_dimensions.py IMF.RES,WEO
  python3 imf_dimensions.py IMF.RES,WEO --dim INDICATOR --search "current account"
  python3 imf_dimensions.py IMF.RES,WEO --key NPL..A --dim INDICATOR     # WEO indicators Nepal has
  python3 imf_dimensions.py IMF.STA,CPI --key NPL....                     # CPI codes with data for Nepal
  python3 imf_dimensions.py IMF.STA,BOP --dim COUNTRY --search nepal
"""

COLUMNS = ["flow", "position", "dimension", "codelist", "code", "name", "has_data"]


def load_structure(agency, fid, version):
    """Dataflow name and version, and the ordered dimensions with their codes."""
    url = f"{BASE}/dataflow/{agency}/{urllib.parse.quote(fid)}/{version or 'latest'}?references=descendants"
    root = get_xml(url)
    if root is None:
        die(f"no dataflow {agency},{fid} at the IMF API. {legacy_hint(fid) or 'List them with imf_dataflows.py.'}")
    flow = None
    for d in root.iter(STR + "Dataflow"):
        if d.get("agencyID") == agency and d.get("id") == fid:
            flow = d
    if flow is None:
        die(f"the structure response did not contain {agency},{fid}")
    ref = flow.find(STR + "Structure/Ref")
    dsds = list(root.iter(STR + "DataStructure"))
    dsd = next((s for s in dsds if ref is not None and s.get("id") == ref.get("id")
                and s.get("agencyID") == ref.get("agencyID")), dsds[0] if dsds else None)
    if dsd is None:
        die(f"no data structure found for {agency},{fid}")

    codelists = {}
    for cl in root.iter(STR + "Codelist"):
        codelists[(cl.get("agencyID"), cl.get("id"), cl.get("version"))] = cl
    concepts = {}
    for scheme in root.iter(STR + "ConceptScheme"):
        for c in scheme.findall(STR + "Concept"):
            concepts[(scheme.get("agencyID"), scheme.get("id"), scheme.get("version"), c.get("id"))] = c

    def find_codelist(enum):
        if enum is None:
            return None
        key = (enum.get("agencyID"), enum.get("id"), enum.get("version"))
        if key in codelists:
            return codelists[key]
        same = [v for k, v in codelists.items() if k[:2] == key[:2]]
        return same[0] if same else None

    dims = []
    dim_list = dsd.find(f"{STR}DataStructureComponents/{STR}DimensionList")
    for i, d in enumerate(dim_list.findall(STR + "Dimension") if dim_list is not None else []):
        cref = d.find(STR + "ConceptIdentity/Ref")
        concept = None
        if cref is not None:
            concept = concepts.get((cref.get("agencyID"), cref.get("maintainableParentID"),
                                    cref.get("maintainableParentVersion"), cref.get("id")))
            if concept is None:  # same concept, other scheme version
                concept = next((v for k, v in concepts.items()
                                if k[1] == cref.get("maintainableParentID") and k[3] == cref.get("id")), None)
        enum = d.find(f"{STR}LocalRepresentation/{STR}Enumeration/Ref")
        if enum is None and concept is not None:
            enum = concept.find(f"{STR}CoreRepresentation/{STR}Enumeration/Ref")
        cl = find_codelist(enum)
        codes = [(c.get("id"), en_text(c, "Name")) for c in cl.findall(STR + "Code")] if cl is not None else []
        pos = d.get("position")
        dims.append({
            "position": int(pos) + 1 if pos is not None and pos.isdigit() else i + 1,
            "id": d.get("id"),
            "name": en_text(concept, "Name") if concept is not None else "",
            "codelist": f"{cl.get('agencyID')}:{cl.get('id')}({cl.get('version')})" if cl is not None else "",
            "codes": codes,
        })
    dims.sort(key=lambda x: x["position"])
    info = {"flow": f"{agency},{fid}", "name": en_text(flow, "Name"), "version": flow.get("version"),
            "structure_url": url}
    return info, dims


def load_availability(agency, fid, key):
    """Codes with data per dimension, plus series count and time range, or None if unavailable."""
    url = f"{BASE}/availableconstraint/{agency},{urllib.parse.quote(fid)}/{key}"
    root = get_xml(url)  # the server labels this XML as application/json; it is SDMX-ML
    if root is None:
        return None
    avail = {}
    for kv in root.iter(COM + "KeyValue"):
        avail[kv.get("id")] = [v.text for v in kv.findall(COM + "Value") if v.text]
    notes = {}
    for a in root.iter(COM + "Annotation"):
        title = a.find(COM + "AnnotationTitle")
        if title is not None and title.text:
            notes[a.get("id")] = title.text
    end = notes.get("time_period_end")  # the first day after the last period with data
    try:
        last_day = (datetime.date.fromisoformat(end[:10]) - datetime.timedelta(days=1)).isoformat()
    except (TypeError, ValueError):
        last_day = end
    return {"codes": avail, "series_count": notes.get("series_count"),
            "time_start": (notes.get("time_period_start") or "")[:10] or None, "time_end": last_day, "url": url}


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataflow", help="AGENCY,ID such as IMF.RES,WEO (a bare id such as WEO also works)")
    ap.add_argument("--key", default="all",
                    help="only count codes with data under this partial key, e.g. NPL..A (default: all)")
    ap.add_argument("--dim", help="show only this dimension (all its codes), e.g. INDICATOR")
    ap.add_argument("--search", help="only codes whose code or English name contains all these words")
    ap.add_argument("--all-codes", action="store_true", help="also show codes that have no data")
    ap.add_argument("--max", type=int, default=None,
                    help="codes shown per dimension (default 12; unlimited with --dim or --search)")
    ap.add_argument("--out", default="research", metavar="DIR", help="folder for files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_args()

    agency, fid, version = resolve_flow(a.dataflow)
    info, dims = load_structure(agency, fid, version)
    if not dims:
        die(f"{info['flow']} has no dimensions in its structure")
    key = a.key.strip() or "all"
    time.sleep(PAGE_SLEEP)
    try:
        avail = load_availability(agency, fid, key)
    except FetchError as e:
        say(f"warning: could not get data availability ({e}); showing full codelists", a.json)
        avail = None

    if a.dim and a.dim.upper() not in [d["id"].upper() for d in dims]:
        die(f"{info['flow']} has no dimension '{a.dim}'; it has {', '.join(d['id'] for d in dims)}")
    words = [w.lower() for w in (a.search or "").split()]
    limit = a.max if a.max is not None else (None if (a.dim or a.search) else 12)

    csv_rows, out_dims = [], []
    for d in dims:
        with_data = set(avail["codes"].get(d["id"], [])) if avail else None
        names = dict(d["codes"])
        codes = list(d["codes"])
        # codes that have data but are missing from the codelist still count
        for c in sorted(with_data or []):
            if c not in names:
                codes.append((c, ""))
        rows = []
        for code, name in codes:
            has = (code in with_data) if with_data is not None else None
            csv_rows.append({"flow": info["flow"], "position": d["position"], "dimension": d["id"],
                             "codelist": d["codelist"], "code": code, "name": name,
                             "has_data": "" if has is None else has})
            if has is False and not a.all_codes:
                continue
            if words and not all(w in f"{code} {name}".lower() for w in words):
                continue
            rows.append({"code": code, "name": name, "has_data": has})
        out_dims.append(dict(d, shown=rows, n_total=len(d["codes"]),
                             n_data=len(with_data) if with_data is not None else None))

    suffix = "" if key == "all" else "_" + safe_name(key)
    catalog = write_csv(pathlib.Path(a.out) / "catalog" / f"imf_codes_{safe_name(agency)}_{safe_name(fid)}{suffix}.csv",
                        csv_rows, COLUMNS)
    selected = [d for d in out_dims if not a.dim or d["id"].upper() == a.dim.upper()]

    if a.json:
        print_json({
            "flow": info["flow"], "name": info["name"], "version": info["version"], "key": key,
            "key_order": [d["id"] for d in dims],
            "series_with_data": avail["series_count"] if avail else None,
            "time_start": avail["time_start"] if avail else None,
            "time_end": avail["time_end"] if avail else None,
            "dimensions": [{"position": d["position"], "id": d["id"], "name": d["name"], "codelist": d["codelist"],
                            "codes_total": d["n_total"], "codes_with_data": d["n_data"], "codes": d["shown"]}
                           for d in selected],
            "catalog_file": catalog.as_posix(),
        })
        return 0

    print(f"{info['flow']}  {info['name']}  (version {info['version']})")
    print(f"Key order: {'.'.join(d['id'] for d in dims)}")
    if avail:
        scope = "" if key == "all" else f" under key {key}"
        print(f"With data{scope}: {avail['series_count'] or '?'} series, "
              f"{avail['time_start'] or '?'} to {avail['time_end'] or '?'}"
              + ("" if a.all_codes else " (only codes with data are listed; --all-codes for the full lists)"))
    for d in selected:
        count = f"{d['n_data']} of {d['n_total']} codes have data" if d["n_data"] is not None else f"{d['n_total']} codes"
        print(f"\n[{d['position']}] {d['id']}  {d['name']}  ({d['codelist'] or 'no codelist'}; {count})")
        shown = d["shown"] if limit is None else d["shown"][:limit]
        for r in shown:
            mark = "" if r["has_data"] is not False else "   (no data)"
            print(f"    {r['code']:<24} {r['name'][:100]}{mark}")
        if not d["shown"]:
            print("    (no code matches)")
        elif len(shown) < len(d["shown"]):
            print(f"    ... {len(d['shown']) - len(shown)} more: add --dim {d['id']} to list all")
    print(f"\nAll codes: {catalog.as_posix()}")
    print(f"Next: python3 {script_path('imf_fetch.py')} {info['flow']} <key in the order above> --start YYYY")
    return 0


if __name__ == "__main__":
    run(main)
