#!/usr/bin/env python3
"""Smoke test for worldbank-indicators: one minimal live call per endpoint the scripts use.

Prints OK or FAIL per line and exits 1 if anything failed. Writes nothing to disk.
Run from anywhere:  python3 skills/worldbank-indicators/tests/smoke.py
"""
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import _common as c  # noqa: E402
from wdi_countries import api_rows  # noqa: E402

API = "https://api.worldbank.org/v2"


def indicator_list():
    meta, rows = api_rows(c.get_json(f"{API}/indicator?format=json&per_page=1"))
    assert rows and int(meta["total"]) > 20000, f"total {meta.get('total')}"
    return f"{meta['total']} indicators"


def indicator_meta():
    _, rows = api_rows(c.get_json(f"{API}/indicator/FX.OWN.TOTL.ZS?format=json"))
    assert rows and "Account ownership" in rows[0]["name"], "unexpected name"
    return f"FX.OWN.TOTL.ZS = {rows[0]['name'][:50]}..."


def data_one_country():
    meta, rows = api_rows(c.get_json(f"{API}/country/NPL/indicator/FX.OWN.TOTL.ZS?format=json&mrnev=1"))
    assert rows and rows[0]["value"] is not None, "no value"
    return f"NPL {rows[0]['date']} = {rows[0]['value']:.1f}"


def data_source_param():
    meta, rows = api_rows(c.get_json(f"{API}/country/NPL;IND/indicator/account.t.d?format=json&mrnev=1&source=28"))
    assert len(rows) == 2 and all(r["value"] is not None for r in rows), f"{len(rows)} rows"
    return f"source {meta.get('sourceid') or 28}: " + ", ".join(f"{r['countryiso3code']} {r['date']}" for r in rows)


def countries():
    meta, rows = api_rows(c.get_json(f"{API}/country?format=json&per_page=1"))
    assert rows and int(meta["total"]) >= 200, f"total {meta.get('total')}"
    return f"{meta['total']} economies and aggregates"


def sources():
    meta, rows = api_rows(c.get_json(f"{API}/sources?format=json&per_page=1"))
    assert rows and int(meta["total"]) >= 50, f"total {meta.get('total')}"
    return f"{meta['total']} sources"


def source_indicators():
    meta, rows = api_rows(c.get_json(f"{API}/sources/28/indicators?format=json&per_page=1"))
    assert rows and int(meta["total"]) > 1000, f"total {meta.get('total')}"
    return f"{meta['total']} indicators in source 28 (Global Findex)"


def topics():
    meta, rows = api_rows(c.get_json(f"{API}/topic?format=json"))
    assert rows and int(meta["total"]) >= 15, f"total {meta.get('total')}"
    return f"{meta['total']} topics"


CHECKS = [
    ("indicator list   api.worldbank.org/v2/indicator", indicator_list),
    ("indicator meta   /v2/indicator/{code}", indicator_meta),
    ("data             /v2/country/{iso3}/indicator/{code}?mrnev=1", data_one_country),
    ("data, source     /v2/country/{a;b}/indicator/{code}?source=28", data_source_param),
    ("countries        /v2/country", countries),
    ("sources          /v2/sources", sources),
    ("source list      /v2/sources/{id}/indicators", source_indicators),
    ("topics           /v2/topic", topics),
]


def main():
    failed = 0
    for i, (name, fn) in enumerate(CHECKS):
        if i:
            time.sleep(c.PAGE_SLEEP)
        try:
            print(f"OK    {name}  ({fn()})")
        except Exception as e:  # report every failure, keep going
            failed += 1
            print(f"FAIL  {name}  ({type(e).__name__}: {e})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
