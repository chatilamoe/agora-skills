#!/usr/bin/env python3
"""Smoke test for worldbank-documents: one minimal live call per endpoint the scripts use.

Prints OK or FAIL per line and exits 1 if anything failed. Writes nothing to disk.
Run from anywhere:  python3 skills/worldbank-documents/tests/smoke.py
"""
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import _common as c  # noqa: E402

WDS = "https://search.worldbank.org/api/v3/wds"
PROJECTS = "https://search.worldbank.org/api/v3/projects"
OKR = "https://openknowledge.worldbank.org/server/api"
# Fixed, stable records: Findex note on the Maldives (WDS) and The Global Findex Database 2025 (OKR).
WDS_ID = "31476985"
WDS_PDF = "https://documents.worldbank.org/curated/en/570891571303596376/pdf/Financial-Inclusion-in-the-Maldives-Findex-2018-Survey.pdf"
OKR_ITEM = "8b9002b6-d8dd-426c-aa7c-6d7d16902cd7"
OKR_BITSTREAM = "795d71b1-9df7-4c04-a11d-75d1d8bbcf2f"


def first_kb(url):
    """Read only the first 1 KB of a file (documents.worldbank.org ignores Range headers)."""
    def action():
        with c.open_url(url, accept="application/pdf", headers={"Range": "bytes=0-1023"}) as resp:
            return resp.read(1024)
    return c.with_retries(action, url)


def wds_search():
    d = c.get_json(c.build_url(WDS, {"format": "json", "qterm": "findex", "rows": 1, "fl": "id,display_title"}))
    docs = [k for k in (d.get("documents") or {}) if k.startswith("D")]
    assert docs, "no documents in the response"
    return f"{d.get('total')} documents for 'findex'"


def wds_by_id():
    d = c.get_json(c.build_url(WDS, {"format": "json", "id": WDS_ID, "fl": "id,display_title,pdfurl"}))
    doc = (d.get("documents") or {}).get(f"D{WDS_ID}")
    assert doc and doc.get("pdfurl"), f"D{WDS_ID} missing or has no pdfurl"
    return doc.get("display_title", "")[:60]


def wds_pdf():
    head = first_kb(WDS_PDF)
    assert head[:5] == b"%PDF-", f"not a PDF: {head[:40]!r}"
    return "first 1 KB is a PDF"


def okr_search():
    d = c.get_json(c.build_url(OKR + "/discover/search/objects",
                               {"query": "global findex", "size": 1, "f.entityType": "Publication,equals"}))
    page = d["_embedded"]["searchResult"]["page"]
    assert int(page["totalElements"]) > 0, "no items"
    return f"{page['totalElements']} items for 'global findex'"


def okr_bundles():
    d = c.get_json(f"{OKR}/core/items/{OKR_ITEM}/bundles?embed=bitstreams")
    names = []
    for b in d["_embedded"]["bundles"]:
        if b.get("name") == "ORIGINAL":
            names += [x["name"] for x in b["_embedded"]["bitstreams"]["_embedded"]["bitstreams"]]
    assert any(n.lower().endswith(".pdf") for n in names), "no PDF in the ORIGINAL bundle"
    return f"{len(names)} files in ORIGINAL"


def okr_content():
    head = first_kb(f"{OKR}/core/bitstreams/{OKR_BITSTREAM}/content")
    assert head[:5] == b"%PDF-", f"not a PDF: {head[:40]!r}"
    return "first 1 KB is a PDF"


def projects():
    d = c.get_json(c.build_url(PROJECTS, {"format": "json", "countrycode_exact": "NP", "rows": 1,
                                          "fl": "id,project_name"}))
    ps = [v for v in (d.get("projects") or {}).values() if isinstance(v, dict) and v.get("id")]
    assert ps, "no projects"
    return f"{d.get('total')} projects in Nepal"


CHECKS = [
    ("wds search      search.worldbank.org/api/v3/wds?qterm=", wds_search),
    ("wds by id       search.worldbank.org/api/v3/wds?id=", wds_by_id),
    ("wds pdf         documents.worldbank.org/curated/.../pdf/", wds_pdf),
    ("okr search      openknowledge.worldbank.org/server/api/discover/search/objects", okr_search),
    ("okr files       .../server/api/core/items/{uuid}/bundles?embed=bitstreams", okr_bundles),
    ("okr pdf         .../server/api/core/bitstreams/{uuid}/content", okr_content),
    ("projects        search.worldbank.org/api/v3/projects", projects),
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
