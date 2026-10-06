#!/usr/bin/env python3
"""Smoke test for the un-statistics skill: one minimal live call per endpoint.

Prints one line per endpoint, OK or FAIL, and exits 1 if any call fails.
Each call goes through the same fetch and parsing code the scripts use, so a FAIL means
either the service is down or its format changed. Nothing is written to ./research.

Usage: python3 tests/smoke.py [--only NAME,NAME]
"""
import argparse
import csv
import io
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import _common as C  # noqa: E402
import _sdmx as X  # noqa: E402


def sdmx_check(provider, flow, key):
    def check():
        base, _ = X.resolve_base(provider)
        body, _ = C.fetch(X.data_url(base, flow, key, last=1), accept=X.ACCEPT_JSON)
        rows, _ = X.parse_data(body)
        assert rows, "no observations"
        r = rows[-1]
        return "%d obs; %s %s = %s" % (len(rows), key, r.get("TIME_PERIOD"), r.get("OBS_VALUE"))
    return check


def sdg_data():
    d = C.fetch_json(C.build_url("https://unstats.un.org/SDGAPI/v1/sdg/Series/Data",
                                 [("seriesCode", "SI_POV_DAY1"), ("areaCode", "524"), ("pageSize", 5)]))
    assert d.get("data"), "no data"
    return "%s rows; SI_POV_DAY1 Nepal" % d.get("totalElements")


def sdg_list():
    d = C.fetch_json("https://unstats.un.org/SDGAPI/v1/sdg/Indicator/List")
    assert len(d) > 200, "only %d indicators" % len(d)
    return "%d indicators" % len(d)


def uis_version():
    d = C.fetch_json("https://api.uis.unesco.org/api/public/versions/default")
    assert d.get("version"), "no version"
    return "default version %s" % d["version"]


def uis_data():
    d = C.fetch_json("https://api.uis.unesco.org/api/public/data/indicators?indicator=CR.1&geoUnit=NPL")
    recs = d.get("records") or []
    assert recs, "no records"
    return "%d records; CR.1 NPL %s = %.1f" % (len(recs), recs[-1]["year"], recs[-1]["value"])


def who_indicator():
    d = C.fetch_json(C.build_url("https://ghoapi.azureedge.net/api/Indicator",
                                 {"$filter": "IndicatorCode eq 'WHOSIS_000001'"}))
    assert d.get("value"), "indicator not found"
    return d["value"][0]["IndicatorName"]


def who_data():
    d = C.fetch_json(C.build_url("https://ghoapi.azureedge.net/api/WHOSIS_000001",
                                 {"$filter": "SpatialDim eq 'NPL' and Dim1 eq 'SEX_BTSX' and TimeDim ge 2020"}))
    vals = d.get("value") or []
    assert vals, "no values"
    last = max(vals, key=lambda v: v["TimeDim"])
    return "%d values; NPL %s = %s" % (len(vals), last["TimeDim"], last["NumericValue"])


def unhcr():
    d = C.fetch_json("https://api.unhcr.org/population/v1/population/?year=2024&coo=AFG&cf_type=ISO&limit=5")
    items = d.get("items") or []
    assert items and items[0].get("coo_iso") == "AFG", "no AFG row"
    return "refugees from AFG 2024 = %s" % items[0].get("refugees")


def eurostat_data():
    d = C.fetch_json("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_a"
                     "?geo=DE&age=Y15-74&unit=PC_ACT&sex=T&lastTimePeriod=1")
    assert d.get("value"), "no values"
    t = list(d["dimension"]["time"]["category"]["index"])[0]
    return "une_rt_a DE %s = %s" % (t, list(d["value"].values())[0] if isinstance(d["value"], dict) else d["value"][0])


def eurostat_structure():
    body, _ = C.fetch("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/une_rt_a/latest"
                      "?references=descendants&detail=referencepartial", accept=X.ACCEPT_STRUCTURE)
    st = X.parse_structure(body, "une_rt_a")
    assert st["dimensions"], "no dimensions"
    return "une_rt_a key %s" % X.key_template(st["dimensions"])


def sdmx_structure():
    base, _ = X.resolve_base("bis")
    body, _ = C.fetch(X.structure_url(base, "BIS,WS_CBPOL,1.0"), accept=X.ACCEPT_STRUCTURE)
    st = X.parse_structure(body, "WS_CBPOL")
    assert st["dimensions"], "no dimensions"
    return "BIS WS_CBPOL key %s" % X.key_template(st["dimensions"])


def owid_csv():
    text = C.fetch_text("https://ourworldindata.org/grapher/gdp-per-capita-worldbank.csv?csvType=full")
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Code") == "NPL"]
    assert rows, "no NPL rows"
    return "%d NPL rows; latest %s" % (len(rows), max(int(r["Year"]) for r in rows))


def owid_meta():
    d = C.fetch_json("https://ourworldindata.org/grapher/gdp-per-capita-worldbank.metadata.json")
    assert (d.get("chart") or {}).get("citation"), "no citation"
    return "citation: %s" % d["chart"]["citation"]


def owid_search():
    d = C.fetch_json("https://ourworldindata.org/api/search?q=poverty&type=charts&hitsPerPage=1")
    assert d.get("results"), "no results"
    return "%s hits" % d.get("nbHits")


def comtrade_reference():
    d = C.fetch_json("https://comtradeapi.un.org/files/v1/app/reference/Reporters.json")
    assert len(d.get("results") or []) > 200, "short reporter list"
    return "%d reporters" % len(d["results"])


def comtrade_preview():
    time.sleep(2)  # the preview allows about one call every two seconds
    d = C.fetch_json("https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=524&period=2022"
                     "&cmdCode=TOTAL&flowCode=X&partnerCode=0")
    assert d.get("data"), "no rows (%s)" % (d.get("error") or "empty")
    return "NPL exports 2022 = %.0f USD" % d["data"][0]["primaryValue"]


CHECKS = [
    ("sdg-data", sdg_data),
    ("sdg-indicator-list", sdg_list),
    ("undata-sdmx", sdmx_check("undata", "IAEG-SDGs,DF_SDG_GLH,1.26", "A..SI_POV_DAY1.524...........")),
    ("unicef-sdmx", sdmx_check("unicef", "UNICEF,GLOBAL_DATAFLOW,1.0", "NPL.CME_MRY0T4._T")),
    ("ilostat-sdmx", sdmx_check("ilo", "ILO,DF_UNE_2EAP_SEX_AGE_RT,1.0", "NPL.A..SEX_T.AGE_YTHADULT_YGE15")),
    ("oecd-sdmx", sdmx_check("oecd", "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0", "FRA.A.N.CPI.PA._T.N.GY")),
    ("bis-sdmx", sdmx_check("bis", "BIS,WS_CBPOL,1.0", "M.US")),
    ("ecb-sdmx", sdmx_check("ecb", "EXR", "D.USD.EUR.SP00.A")),
    ("sdmx-structure", sdmx_structure),
    ("uis-version", uis_version),
    ("uis-data", uis_data),
    ("who-indicator", who_indicator),
    ("who-data", who_data),
    ("unhcr-population", unhcr),
    ("eurostat-data", eurostat_data),
    ("eurostat-structure", eurostat_structure),
    ("owid-csv", owid_csv),
    ("owid-metadata", owid_meta),
    ("owid-search", owid_search),
    ("comtrade-reference", comtrade_reference),
    ("comtrade-preview", comtrade_preview),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated check names, e.g. sdg-data,who-data")
    args = ap.parse_args()
    wanted = set(args.only.split(",")) if args.only else None
    failed = 0
    for name, check in CHECKS:
        if wanted and name not in wanted:
            continue
        t0 = time.time()
        try:
            detail = check()
            print("OK   %-20s %s (%.1fs)" % (name, detail, time.time() - t0))
        except Exception as err:  # noqa: BLE001 - report every failure as one line
            failed += 1
            print("FAIL %-20s %s (%.1fs)" % (name, str(err).replace("\n", " ")[:200], time.time() - t0))
        sys.stdout.flush()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
