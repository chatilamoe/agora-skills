#!/usr/bin/env python3
"""Smoke test for dbnomics-macro: one minimal live call per endpoint the scripts use.

Prints one line per endpoint, OK or FAIL; exits 1 if any line fails.
Usage: python3 skills/dbnomics-macro/tests/smoke.py
"""
import json
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # importing the scripts must not leave files behind
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from _common import BASE, build_url, get_json  # noqa: E402

SERIES = "IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change"
failures = 0


def check(name, fn):
    global failures
    t0 = time.time()
    try:
        detail = fn()
        print(f"OK   {name}: {detail} ({time.time() - t0:.1f} s)")
    except Exception as e:  # any failure is a FAIL line, never a crash
        failures += 1
        print(f"FAIL {name}: {type(e).__name__}: {e}")
    time.sleep(0.5)


def providers():
    docs = get_json(f"{BASE}/providers")["providers"]["docs"]
    codes = {d["code"] for d in docs}
    missing = {"IMF", "WB", "OECD", "ECB"} - codes
    assert not missing, f"providers missing: {missing}"
    return f"{len(codes)} providers incl. IMF, WB, OECD, ECB"


def provider_tree():
    tree = get_json(f"{BASE}/providers/IMF")["category_tree"]
    found = set()

    def walk(nodes):
        for n in nodes:
            if n.get("children"):
                walk(n["children"])
            elif n.get("code"):
                found.add(n["code"])
    walk(tree)
    assert "WEO:2025-04" in found, "IMF/WEO:2025-04 not in the IMF category tree"
    return f"IMF has {len(found)} datasets"


def search():
    res = get_json(build_url(f"{BASE}/search", {"q": "nepal inflation", "limit": 5}))["results"]
    assert res["num_found"] > 0 and res["docs"], "no dataset found"
    return f"{res['num_found']} datasets for 'nepal inflation'"


def dataset():
    doc = get_json(f"{BASE}/datasets/IMF/WEO:2025-04")["datasets"]["docs"][0]
    assert doc["dimensions_codes_order"] == ["weo-country", "weo-subject", "unit"], doc["dimensions_codes_order"]
    return f"IMF/WEO:2025-04 has {doc['nb_series']} series, indexed {doc['indexed_at'][:10]}"


def series_list():
    url = build_url(f"{BASE}/series/IMF/WEO:2025-04", {"dimensions": json.dumps({"weo-country": ["NPL"]}),
                                                         "facets": 1, "limit": 5, "metadata": 0})
    res = get_json(url)
    assert res["series"]["num_found"] > 0 and res.get("series_dimensions_facets"), "no series or no facets"
    return f"{res['series']['num_found']} WEO series for NPL, facets returned"


def series_one():
    doc = get_json(f"{BASE}/series/{SERIES}?observations=1&metadata=0")["series"]["docs"][0]
    assert len(doc["period"]) == len(doc["value"]) > 0, "no observations"
    return f"{SERIES} {doc['period'][-1]} = {doc['value'][-1]}"


def series_batch():
    ids = f"{SERIES},WB/WDI/A-NY.GDP.MKTP.KD.ZG-NPL"
    res = get_json(build_url(f"{BASE}/series", {"series_ids": ids, "observations": 1, "metadata": 0}))
    assert res["series"]["num_found"] == 2, f"expected 2 series, got {res['series']['num_found']}"
    return "2 series from IMF and WB in one call"


check("providers       /providers", providers)
check("provider tree   /providers/IMF", provider_tree)
check("search          /search?q=", search)
check("dataset         /datasets/IMF/WEO:2025-04", dataset)
check("series list     /series/IMF/WEO:2025-04?dimensions=&facets=1", series_list)
check("series by code  /series/IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change", series_one)
check("series batch    /series?series_ids=", series_batch)
sys.exit(1 if failures else 0)
