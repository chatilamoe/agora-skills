#!/usr/bin/env python3
"""Describe a DBnomics dataset (its dimensions, the codes that have series, how fresh it is)
and list the series that match a filter; or list the datasets of one provider.

  dbn_dataset.py PROVIDER                 datasets of a provider     /providers/{provider} (category tree)
  dbn_dataset.py PROVIDER/DATASET         dimensions and codes       /datasets/{provider}/{dataset}
                                          codes with series, counts  /series/{provider}/{dataset}?facets=1&limit=0
  ... with --dim / --q / --list           matching series            /series/{provider}/{dataset}?dimensions=...&q=...

Dimension names and codes are case-sensitive and must be those of the dataset: an unknown
dimension makes DBnomics return zero series without an error, so this script checks them.

Writes: <out>/catalog/dbn_datasets_<PROVIDER>.csv, or <out>/catalog/dbn_codes_<PROVIDER>_<DATASET>.csv
and, when series are listed, <out>/catalog/dbn_list_<PROVIDER>_<DATASET>.csv.
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (BASE, PAGE_SLEEP, build_url, die, get_json, labels, print_json, print_table,  # noqa: E402
                     quote_path, run, safe_name, say, script_path, write_csv)

EPILOG = """examples:
  python3 dbn_dataset.py IMF                                   # datasets of a provider
  python3 dbn_dataset.py IMF --q "economic outlook"
  python3 dbn_dataset.py IMF/WEO:2025-04                       # dimensions and codes
  python3 dbn_dataset.py IMF/WEO:2025-04 --dim weo-country=NPL --dim weo-subject=NGDP_RPCH,PCPIPCH
  python3 dbn_dataset.py WB/WDI --dim country=NPL --q "account ownership"
  python3 dbn_dataset.py ECB/HICP --dim REF_AREA=U2 --dim ICP_ITEM=000000 --dim FREQ=M
"""


def list_provider(provider, words, out, json_mode):
    data = get_json(f"{BASE}/providers/{quote_path(provider)}")
    prov = data.get("provider") or {}
    rows = []

    def walk(nodes, path):
        for n in nodes or []:
            if n.get("children"):
                walk(n["children"], path + [n.get("name") or n.get("code") or ""])
            elif n.get("code"):
                rows.append({"provider": provider, "dataset": n["code"], "name": n.get("name", ""),
                             "category": " / ".join(p for p in path if p)})
    walk(data.get("category_tree"), [])
    seen, unique = set(), []
    for r in rows:  # a dataset can sit in several categories
        if r["dataset"] not in seen:
            seen.add(r["dataset"])
            unique.append(r)
    shown = [r for r in unique if all(w in f"{r['dataset']} {r['name']} {r['category']}".lower() for w in words)]
    catalog = write_csv(pathlib.Path(out) / "catalog" / f"dbn_datasets_{safe_name(provider)}.csv", unique,
                        ["provider", "dataset", "name", "category"])
    if json_mode:
        print_json({"provider": prov, "datasets": shown, "catalog_file": catalog.as_posix()})
    else:
        print(f"{prov.get('code', provider)}  {prov.get('name', '')}  (provider last indexed "
              f"{(prov.get('indexed_at') or '?')[:10]}; terms: {prov.get('terms_of_use') or 'not given'})")
        print_table(shown, [("DATASET", "dataset", 46), ("NAME", "name", 100)])
    say(f"\n{len(shown)} of {len(unique)} datasets. Full list: {catalog.as_posix()}. "
        f"Next: python3 {script_path('dbn_dataset.py')} {provider}/<DATASET>", json_mode)
    return 0 if shown else 1


def parse_dims(pairs, order, json_mode):
    """--dim KEY=V1,V2 -> {KEY: [V1, V2]}, checked against the dataset's dimension names."""
    dims = {}
    for pair in pairs or []:
        if "=" not in pair:
            die(f"--dim needs KEY=VALUE[,VALUE], got '{pair}'")
        key, values = pair.split("=", 1)
        key = key.strip()
        if order and key not in order:
            match = [d for d in order if d.lower() == key.lower()]
            if not match:
                die(f"this dataset has no dimension '{key}'; it has: {', '.join(order)}")
            say(f"note: dimension '{key}' is spelled '{match[0]}' in this dataset", json_mode)
            key = match[0]
        dims.setdefault(key, []).extend(v.strip() for v in values.split(",") if v.strip())
    return dims


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="PROVIDER (list its datasets) or PROVIDER/DATASET (describe it)")
    ap.add_argument("--dim", action="append", metavar="KEY=V1,V2",
                    help="dimension filter; repeat for several dimensions (names as shown, case-sensitive)")
    ap.add_argument("--q", help="full-text filter: whole words in series names (or in dataset names for a provider)")
    ap.add_argument("--list", action="store_true", help="list matching series even without a filter")
    ap.add_argument("--limit", type=int, default=50, help="series to list (default 50)")
    ap.add_argument("--max-codes", type=int, default=10, help="codes shown per dimension (default 10)")
    ap.add_argument("--out", default="research", metavar="DIR", help="folder for files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_args()

    target = a.target.strip().strip("/")
    if "/" not in target:
        words = [w.lower() for w in (a.q or "").split()]
        return list_provider(target, words, a.out, a.json)
    provider, dataset = target.split("/", 1)

    meta_res = get_json(f"{BASE}/datasets/{quote_path(provider)}/{quote_path(dataset)}")
    docs = (meta_res.get("datasets") or {}).get("docs") or []
    if not docs:
        die(f"no dataset {provider}/{dataset}; list them with: python3 {script_path('dbn_dataset.py')} {provider}")
    meta = docs[0]
    order = meta.get("dimensions_codes_order") or []
    dim_labels = meta.get("dimensions_labels") or {}
    value_labels = {k: labels(v) for k, v in (meta.get("dimensions_values_labels") or {}).items()}
    dims = parse_dims(a.dim, order, a.json)
    for key, values in dims.items():
        unknown = [v for v in values if value_labels.get(key) and v not in value_labels[key]]
        if unknown:
            say(f"warning: {key} has no code {', '.join(unknown)} in this dataset (codes are case-sensitive)", a.json)

    filt = {"dimensions": json.dumps(dims, separators=(",", ":")) if dims else None, "q": a.q}
    base = f"{BASE}/series/{quote_path(provider)}/{quote_path(dataset)}"
    time.sleep(PAGE_SLEEP)
    facets_res = get_json(build_url(base, dict(filt, facets=1, limit=0, metadata=0)))
    num_found = (facets_res.get("series") or {}).get("num_found", 0)
    facets = facets_res.get("series_dimensions_facets") or {}

    code_rows, dim_out = [], []
    for dim in order or list(facets):
        counts = facets.get(dim) or []
        codes = sorted(({"code": str(c.get("code")), "count": c.get("count", 0),
                         "label": value_labels.get(dim, {}).get(str(c.get("code")), "")} for c in counts),
                       key=lambda c: (-c["count"], c["code"]))
        for c in codes:
            code_rows.append({"dimension": dim, "dimension_label": dim_labels.get(dim, ""), **c})
        dim_out.append({"id": dim, "label": dim_labels.get(dim, ""), "codes": codes,
                        "codes_in_codelist": len(value_labels.get(dim, {}))})
    tag = safe_name(f"{provider}_{dataset}")
    codes_file = write_csv(pathlib.Path(a.out) / "catalog" / f"dbn_codes_{tag}.csv", code_rows,
                           ["dimension", "dimension_label", "code", "label", "count"])

    series, list_file = [], None
    if a.list or dims or a.q:
        offset = 0
        while offset < min(a.limit, num_found):
            time.sleep(PAGE_SLEEP)
            page = get_json(build_url(base, dict(filt, limit=min(1000, a.limit - offset), offset=offset or None,
                                                 metadata=0)))
            batch = (page.get("series") or {}).get("docs") or []
            for s in batch:
                series.append({"series_id": f"{provider}/{dataset}/{s.get('series_code', '')}",
                               "series_code": s.get("series_code", ""), "series_name": s.get("series_name", ""),
                               "frequency": s.get("@frequency", "")})
            if not batch:
                break
            offset += len(batch)
        list_file = write_csv(pathlib.Path(a.out) / "catalog" / f"dbn_list_{tag}.csv", series,
                              ["series_id", "series_code", "series_name", "frequency"])

    info = {"dataset": f"{provider}/{dataset}", "name": meta.get("name", ""), "nb_series": meta.get("nb_series"),
            "indexed_at": (meta.get("indexed_at") or "")[:10], "updated_at": (meta.get("updated_at") or "")[:10],
            "source_href": meta.get("source_href"), "doc_href": meta.get("doc_href"),
            "dimensions_order": order, "filter": {"dimensions": dims, "q": a.q}, "series_matching": num_found}
    if a.json:
        print_json(dict(info, dimensions=dim_out, series=series, codes_file=codes_file.as_posix(),
                        list_file=list_file.as_posix() if list_file else None))
        return 0 if num_found else 1

    updated = f"; provider updated {info['updated_at']}" if info["updated_at"] else ""
    print(f"{info['dataset']}  {info['name']}")
    print(f"{info['nb_series']} series; DBnomics indexed {info['indexed_at'] or '?'}{updated}"
          + (f"; source {info['source_href']}" if info["source_href"] else ""))
    print(f"Dimensions, in series-code order: {', '.join(order) if order else '(not given)'}")
    if dims or a.q:
        shown = "; ".join([f"{k}={'+'.join(v)}" for k, v in dims.items()] + ([f'q="{a.q}"'] if a.q else []))
        print(f"Filter: {shown} -> {num_found} series")
        print("(code counts below apply the filters on the other dimensions)")
    for i, d in enumerate(dim_out, 1):
        print(f"\n[{i}] {d['id']}  {d['label']}  ({len(d['codes'])} codes with series"
              + (f" of {d['codes_in_codelist']} in the codelist)" if d["codes_in_codelist"] else ")"))
        for c in d["codes"][: a.max_codes]:
            print(f"    {c['code']:<22} {c['label'][:80]:<80} {c['count']:>7}")
        if len(d["codes"]) > a.max_codes:
            print(f"    ... {len(d['codes']) - a.max_codes} more in {codes_file.as_posix()}")
    if series:
        print(f"\nSeries ({num_found} match; showing {len(series)}):")
        for s in series:
            print(f"  {s['series_id']:<60} {s['series_name'][:100]}")
        print(f"\nSeries list: {list_file.as_posix()}")
        print(f"Next: python3 {script_path('dbn_series.py')} {series[0]['series_id']} --start YYYY")
    elif dims or a.q:
        print("\nNo series match this filter. Check codes above (case-sensitive) or use fewer words.")
    else:
        print(f"\nNext: add --dim {order[0] if order else 'DIM'}=CODE (or --q WORDS) to list series")
    return 0 if num_found else 1


if __name__ == "__main__":
    run(main)
