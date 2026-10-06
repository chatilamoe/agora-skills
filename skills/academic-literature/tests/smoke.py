#!/usr/bin/env python3
"""Smoke test for academic-literature: one minimal live call per endpoint, through the scripts' own
functions. Prints OK or FAIL per line; exits 1 if any FAIL. Writes nothing to disk.

Run: python3 skills/academic-literature/tests/smoke.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _common as c  # noqa: E402
import arxiv_search  # noqa: E402
import core_search  # noqa: E402
import crossref  # noqa: E402
import nber_search  # noqa: E402
import oa_pdf  # noqa: E402
import openalex  # noqa: E402
import s2  # noqa: E402


# Each check returns a list of items (dicts with a title); an empty list counts as a failure.
CHECKS = [
    ("openalex /works?search", lambda: openalex.search("mobile money", limit=1)[0]),
    ("openalex /works/doi:{doi}", lambda: [openalex.get_work("10.1111/joes.12372")]),
    ("crossref /works?query", lambda: crossref.search("mobile money", limit=1)[0]),
    ("crossref /works/{doi}", lambda: [crossref.get_work("10.1596/1813-9450-11008")]),
    ("semantic scholar /paper/search", lambda: s2.search("mobile money", limit=1, fallback=False)[0]),
    ("semantic scholar /paper/search/bulk", lambda: s2.bulk('"mobile money" +M-Pesa +Kenya', limit=1, year="2011")[0]),
    ("semantic scholar /paper/{doi}", lambda: [s2.get_paper("10.1111/joes.12372")]),
    ("semantic scholar /paper/{id}/citations", lambda: s2.neighbours("10.1111/joes.12372", "citations", 1)),
    ("arxiv /api/query", lambda: arxiv_search.search("remittances", limit=1, cats=["econ.GN"])[0]),
    ("core /v3/search/works/", lambda: core_search.search("mobile money", limit=1)[0]),
    ("nber working_page_listing search", lambda: nber_search.search("mobile money", limit=1)[0]),
    ("unpaywall /v2/{doi}", lambda: [oa_pdf.from_unpaywall("10.1596/1813-9450-9000")[0]]),
]


def main():
    failed = 0
    for name, call in CHECKS:
        started = time.time()
        try:
            items = [it for it in call() if it and it.get("title")]
            if not items:
                raise c.FetchError("answered, but returned no results")
            title = (items[0].get("title") or "")[:50]
            print("OK   %s (%.1f s): %s" % (name, time.time() - started, title))
        except Exception as err:  # report every failure the same way
            failed += 1
            print("FAIL %s (%.1f s): %s" % (name, time.time() - started, str(err)[:200]))
    print("%d of %d endpoints OK" % (len(CHECKS) - failed, len(CHECKS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
