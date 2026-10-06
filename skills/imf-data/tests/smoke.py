#!/usr/bin/env python3
"""Smoke test for imf-data: one minimal live call per endpoint the scripts use.

Prints one line per endpoint, OK or FAIL; exits 1 if any line fails.
Usage: python3 skills/imf-data/tests/smoke.py
"""
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # importing the scripts must not leave files behind
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from _common import BASE, COM, STR, get_xml  # noqa: E402
from imf_fetch import parse_data  # noqa: E402

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


def dataflows():
    root = get_xml(f"{BASE}/dataflow/all/all/all")
    ids = {(d.get("agencyID"), d.get("id")) for d in root.iter(STR + "Dataflow")}
    assert ("IMF.RES", "WEO") in ids, "IMF.RES,WEO missing from the dataflow list"
    return f"{len(ids)} dataflows, IMF.RES,WEO present"


def structure():
    root = get_xml(f"{BASE}/dataflow/IMF.RES/WEO/latest?references=datastructure")
    dims = [d.get("id") for d in root.iter(STR + "Dimension") if d.get("position") is not None]
    assert dims[:3] == ["COUNTRY", "INDICATOR", "FREQUENCY"], f"unexpected WEO key order {dims}"
    return "WEO key order COUNTRY.INDICATOR.FREQUENCY"


def codelists():
    root = get_xml(f"{BASE}/dataflow/IMF.RES/WEO/latest?references=descendants")
    codes = [c.get("id") for cl in root.iter(STR + "Codelist") if cl.get("id") == "CL_WEO_INDICATOR"
             for c in cl.findall(STR + "Code")]
    assert "NGDP_RPCH" in codes, "NGDP_RPCH not in CL_WEO_INDICATOR"
    return f"CL_WEO_INDICATOR has {len(codes)} codes"


def availability():
    root = get_xml(f"{BASE}/availableconstraint/IMF.RES,WEO/NPL..A")
    values = {kv.get("id"): [v.text for v in kv.findall(COM + "Value")] for kv in root.iter(COM + "KeyValue")}
    assert "NGDP_RPCH" in values.get("INDICATOR", []), "NGDP_RPCH not available for NPL"
    return f"{len(values.get('INDICATOR', []))} WEO indicators with data for NPL"


def data():
    root = get_xml(f"{BASE}/data/IMF.RES,WEO/NPL.NGDP_RPCH.A?startPeriod=2024&endPeriod=2024")
    _, series = parse_data(root, ["COUNTRY", "INDICATOR", "FREQUENCY"])
    assert len(series) == 1 and series[0][2], "no series or no observation returned"
    obs = series[0][2][0]
    float(obs["OBS_VALUE"])
    return f"WEO NPL.NGDP_RPCH.A {obs['TIME_PERIOD']} = {obs['OBS_VALUE']}"


check("dataflow list   /dataflow/all/all/all", dataflows)
check("structure       /dataflow/IMF.RES/WEO?references=datastructure", structure)
check("codelists       /dataflow/IMF.RES/WEO?references=descendants", codelists)
check("availability    /availableconstraint/IMF.RES,WEO/NPL..A", availability)
check("data            /data/IMF.RES,WEO/NPL.NGDP_RPCH.A", data)
sys.exit(1 if failures else 0)
