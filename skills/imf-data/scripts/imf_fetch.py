#!/usr/bin/env python3
"""Download IMF data for one dataflow and key into a tidy CSV, and log it.

Two calls:
  1. /dataflow/{agency}/{id}/latest?references=datastructure   the dimension order, to read series keys
  2. /data/{agency},{id}/{key}?startPeriod=..&endPeriod=..      SDMX-ML StructureSpecificData

The key is the dimension codes in key order joined by '.', e.g. NPL.NGDP_RPCH.A for WEO
(COUNTRY.INDICATOR.FREQUENCY). Use + for several codes (NPL+IND+BGD) and an empty position
for all codes (NPL..A). Missing trailing positions are filled with wildcards. Codes are
case-sensitive. See imf_dimensions.py for the order and the codes.

The CSV has one row per observation:
  dataflow, series_key, country, indicator, period, value,
  frequency, unit, derivation, series_name, latest_actual
'indicator' is the series key without the country and frequency parts (for WEO just the
indicator code; for CPI e.g. CPI._T.YOY_PCH_PA_PT). Values are in full units (42914268000,
not 42.9): the IMF's SCALE attribute only says how it displays them. 'latest_actual' (WEO)
is the last year of actual data; later years are IMF staff estimates or projections.
'derivation' is the observation's DERIVATION_TYPE where given (O official, SE staff
estimate, SP staff projection, ...).

Writes: <out>/data/imf_<ID>_<key>[_<start>-<end>].csv and one line in <out>/data_log.jsonl.
"""
import argparse
import pathlib
import sys
import time
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (BASE, PAGE_SLEEP, STR, build_url, die, en_text, get_xml, joined, legacy_hint, local,  # noqa: E402
                     log_data, print_json, print_table, resolve_flow, run, safe_name, say, script_path, today,
                     write_csv)

EPILOG = """examples:
  python3 imf_fetch.py IMF.RES,WEO NPL.NGDP_RPCH.A --start 2015 --end 2026
  python3 imf_fetch.py IMF.RES,WEO NPL+IND+BGD+PAK+LKA.NGDP_RPCH+PCPIPCH.A --start 2023 --end 2026
  python3 imf_fetch.py IMF.RES,WEO NPL.BCA_NGDPD.A --last 5
  python3 imf_fetch.py IMF.STA,CPI NPL.CPI._T.YOY_PCH_PA_PT.M --start 2025-01
  python3 imf_fetch.py IMF.STA,ER NPL.XDC_USD.PA_RT.A --start 2020 --json
"""

COLUMNS = ["dataflow", "series_key", "country", "indicator", "period", "value",
           "frequency", "unit", "derivation", "series_name", "latest_actual"]
COUNTRY_DIMS = ("COUNTRY", "REF_AREA", "JURISDICTION")
FREQ_DIMS = ("FREQUENCY", "FREQ")
MISSING = ("", "NaN", "nan", "NA", "NULL")


def load_dimensions(agency, fid, version):
    """(dataflow name, version, [dimension ids in key order])."""
    url = f"{BASE}/dataflow/{agency}/{urllib.parse.quote(fid)}/{version or 'latest'}?references=datastructure"
    root = get_xml(url)
    if root is None:
        die(f"no dataflow {agency},{fid} at the IMF API. {legacy_hint(fid) or 'List them with imf_dataflows.py.'}")
    flow = next((d for d in root.iter(STR + "Dataflow") if d.get("id") == fid), None)
    dsd = next(root.iter(STR + "DataStructure"), None)
    if flow is None or dsd is None:
        die(f"the structure of {agency},{fid} could not be read from {url}")
    dim_list = dsd.find(f"{STR}DataStructureComponents/{STR}DimensionList")
    dims = []
    for i, d in enumerate(dim_list.findall(STR + "Dimension") if dim_list is not None else []):
        pos = d.get("position")
        dims.append((int(pos) if pos is not None and pos.isdigit() else i, d.get("id")))
    dims.sort()
    return en_text(flow, "Name"), flow.get("version"), [d for _, d in dims]


def normalise_key(key, dim_ids):
    key = key.strip()
    if key.lower() in ("", "all", "*"):
        return "all"
    parts = key.split(".")
    if len(parts) > len(dim_ids):
        die(f"the key has {len(parts)} positions but this dataflow has {len(dim_ids)}: {'.'.join(dim_ids)}")
    if any(ch.islower() for ch in key):
        print("note: IMF codes are upper case and the API is case-sensitive; a lower-case key returns nothing",
              file=sys.stderr)
    if len(parts) < len(dim_ids):
        parts += [""] * (len(dim_ids) - len(parts))
        print(f"note: key padded to {'.'.join(parts)} (an empty position means all codes)", file=sys.stderr)
    return ".".join(parts)


def parse_data(root, dim_ids):
    """Read StructureSpecificData: DataSet attributes, Group attributes, Series and Obs.

    Returns (dataset attributes, [(dimension values, series attributes, [obs attribute dicts])])."""
    dataset = next((e for e in root.iter() if local(e.tag) == "DataSet"), None)
    if dataset is None:
        return {}, []
    ds_attrs = {k: v for k, v in dataset.attrib.items() if not k.startswith("{")}
    groups = []
    for g in dataset:
        if local(g.tag) == "Group":  # attributes shared by several series, keyed by some dimensions
            attrs = {k: v for k, v in g.attrib.items() if not k.startswith("{")}
            groups.append(({k: v for k, v in attrs.items() if k in dim_ids},
                           {k: v for k, v in attrs.items() if k not in dim_ids}))
    series = []
    for s in dataset:
        if local(s.tag) != "Series":
            continue
        attrs = {k: v for k, v in s.attrib.items() if not k.startswith("{")}
        dims = {d: attrs.get(d, "") for d in dim_ids}
        merged = {}
        for keys, values in groups:
            if keys and all(dims.get(k) == v for k, v in keys.items()):
                merged.update(values)
        merged.update({k: v for k, v in attrs.items() if k not in dim_ids})
        obs = [dict(o.attrib) for o in s if local(o.tag) == "Obs"]
        series.append((dims, merged, obs))
    return ds_attrs, series


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataflow", help="AGENCY,ID such as IMF.RES,WEO (AGENCY,ID,VERSION pins a structure version)")
    ap.add_argument("key", help="series key in dimension order, e.g. NPL.NGDP_RPCH.A; 'all' for everything")
    ap.add_argument("--start", help="first period: 2015, 2025-01 (or 2025-M01), 2025-Q1")
    ap.add_argument("--end", help="last period, same formats")
    ap.add_argument("--last", type=int, help="only the last N observations of each series (lastNObservations)")
    ap.add_argument("--file", help="CSV file name to write in <out>/data/ (default: built from dataflow and key)")
    ap.add_argument("--out", default="research", metavar="DIR", help="folder for files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_args()

    agency, fid, version = resolve_flow(a.dataflow)
    name, flow_version, dim_ids = load_dimensions(agency, fid, version)
    if not dim_ids:
        die(f"{agency},{fid} has no dimensions in its structure")
    key = normalise_key(a.key, dim_ids)

    flow_ref = f"{agency},{fid}" + (f",{version}" if version else "")
    path_key = urllib.parse.quote(key, safe="+.")
    url = build_url(f"{BASE}/data/{flow_ref}/{path_key}",
                    {"startPeriod": a.start, "endPeriod": a.end, "lastNObservations": a.last})
    time.sleep(PAGE_SLEEP)
    root = get_xml(url)
    ds_attrs, series = parse_data(root, dim_ids) if root is not None else ({}, [])

    country_dim = next((d for d in COUNTRY_DIMS if d in dim_ids), None)
    freq_dim = next((d for d in FREQ_DIMS if d in dim_ids), None)
    rows, skipped = [], 0
    for dims, attrs, obs in series:
        series_key = ".".join(dims[d] for d in dim_ids)
        indicator = ".".join(dims[d] for d in dim_ids if d not in (country_dim, freq_dim))
        for o in obs:
            value = o.get("OBS_VALUE")
            if value is None or value.strip() in MISSING:
                skipped += 1
                continue
            rows.append({
                "dataflow": f"{agency},{fid}", "series_key": series_key,
                "country": dims.get(country_dim, "") if country_dim else "",
                "indicator": indicator, "period": o.get("TIME_PERIOD", ""), "value": value.strip(),
                "frequency": dims.get(freq_dim, "") if freq_dim else "",
                "unit": dims.get("UNIT") or attrs.get("UNIT", ""),
                "derivation": o.get("DERIVATION_TYPE") or o.get("OBS_STATUS") or "",
                "series_name": attrs.get("SERIES_NAME", ""),
                "latest_actual": attrs.get("LATEST_ACTUAL_ANNUAL_DATA", ""),
            })

    if not rows and skipped:
        die(f"{len(series)} series matched, but the {skipped} observation(s) in this window have no value "
            f"(placeholders some dataflows keep for recent years; --last counts them). "
            f"Try an earlier --start instead of --last.")
    if not rows:
        period = f" for {a.start or 'the first period'} to {a.end or 'the latest'}" if (a.start or a.end) else ""
        die(f"no data for key {key} in {agency},{fid}{period}. The key order is {'.'.join(dim_ids)} and codes "
            f"are case-sensitive; check them with: python3 {script_path('imf_dimensions.py')} {agency},{fid} --key {key}")

    if a.file:
        fname = a.file if a.file.endswith(".csv") else a.file + ".csv"
    else:
        span = f"_{a.start or ''}-{a.end or ''}" if (a.start or a.end) else (f"_last{a.last}" if a.last else "")
        fname = f"imf_{safe_name(fid)}_{safe_name(key)}{safe_name(span) if span else ''}.csv"
    path = write_csv(pathlib.Path(a.out) / "data" / fname, rows, COLUMNS)

    periods = sorted(r["period"] for r in rows)
    n_series = len({r["series_key"] for r in rows})
    countries = {r["country"] for r in rows}
    indicators = {r["indicator"] for r in rows}
    updated = (ds_attrs.get("UPDATE_DATE") or "")[:10]
    pairs = []
    for r in rows:
        item = (r["country"], r["indicator"], r["latest_actual"])
        if r["latest_actual"] and item not in pairs:
            pairs.append(item)
    if len(pairs) <= 6:
        latest = "; ".join(f"{c} {i} {lat}" for c, i, lat in pairs)
    else:
        latest = f"per series in column latest_actual ({len(pairs)} series)"
    notes = [f"{name} (dataflow version {flow_version})"]
    if updated:
        notes.append(f"IMF update date {updated}")
    notes.append(f"{n_series} series; values in full units")
    if latest:
        notes.append(f"latest actual data {latest}; later periods are IMF staff estimates or projections")
    record = {
        "source": "imf-data", "dataset": f"{agency},{fid}",
        "indicator": joined([r["indicator"] for r in rows]), "entity": joined([r["country"] for r in rows]),
        "period": f"{periods[0]}:{periods[-1]}", "url": url, "accessed": today(), "rows": len(rows),
        "file": path.as_posix(), "notes": "; ".join(notes),
    }
    log = log_data(a.out, record)

    if a.json:
        out_rows = []
        for r in rows:
            r = dict(r)
            try:
                r["value"] = float(r["value"])
            except ValueError:
                pass
            out_rows.append(r)
        print_json({"dataflow": f"{agency},{fid}", "name": name, "version": flow_version, "update_date": updated,
                    "url": url, "file": path.as_posix(), "series": n_series, "rows": out_rows})
    else:
        print(f"{agency},{fid}  {name}  (version {flow_version}; IMF update date {updated or 'not given'})")
        print_table(rows[:30], [("COUNTRY", "country", 8), ("INDICATOR", "indicator", 30), ("PERIOD", "period", 9),
                                ("VALUE", "value", 20), ("UNIT", "unit", 6), ("DERIV", "derivation", 5)])
        if len(rows) > 30:
            print(f"... {len(rows) - 30} more rows in the file")
    empty = len(series) - n_series
    say(f"\n{len(rows)} rows, {n_series} series -> {path.as_posix()} (logged in {log.as_posix()})"
        + (f"; {empty} series had no observations in the period" if empty else ""), a.json)
    if skipped:
        say(f"{skipped} observations without a value were left out", a.json)
    if latest:
        say(f"Latest actual data: {latest}. Later periods are IMF staff estimates or projections.", a.json)
    entity = record["entity"] if len(countries) == 1 else "<entity>"
    indicator = record["indicator"] if len(indicators) == 1 else "<indicator>"
    dataset = f"IMF {name} [{agency}:{fid}" + (f", updated {updated}]" if updated else "]")
    span = periods[0] if periods[0] == periods[-1] else record["period"]
    say(f"Cite as: ({dataset}, {indicator}, {entity}, {span}, "
        f"retrieved {today()}, {url})", a.json)
    return 0


if __name__ == "__main__":
    run(main)
