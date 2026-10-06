#!/usr/bin/env python3
"""Smoke test for pdf-to-cited-text: download one small public World Bank PDF (6 pages, about 200 KB),
extract it with the best available route and with the standard-library route, and find one known
sentence in each. Prints OK or FAIL per line; exits 1 if any FAIL. Works in a temporary folder.

Run: python3 skills/pdf-to-cited-text/tests/smoke.py
"""
import contextlib
import io
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cite_find  # noqa: E402
import fetch_pdf  # noqa: E402
import pdf_text  # noqa: E402

URL = ("https://documents1.worldbank.org/curated/en/545241624880584363/pdf/"
       "Financial-Inclusion-Women-and-Building-Back-Better.pdf")
PHRASE = "Financial inclusion occurs when adults have access to appropriate, affordable, and well-regulated financial services"
PAGE = 1


def main():
    failed = 0
    with tempfile.TemporaryDirectory() as out:
        started = time.time()
        try:
            meta = fetch_pdf.download(URL, out, "brief")
            print("OK   download documents1.worldbank.org (%.1f s): %d bytes" % (time.time() - started, meta["bytes"]))
        except Exception as err:
            print("FAIL download documents1.worldbank.org: %s" % str(err)[:200])
            print("0 of 1 checks OK (later checks need the PDF)")
            return 1
        for engine in ("auto", "stdlib"):
            label = "extract --engine %s" % engine
            started = time.time()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = pdf_text.main([meta["file"], "--out", out, "--id", "brief-" + engine, "--engine", engine])
                index = cite_find.Doc(Path(out) / "text" / ("brief-" + engine)).index
                if code != 0 or index["page_count"] != 6:
                    raise RuntimeError("exit %s, %s pages" % (code, index.get("page_count")))
                print("OK   %s (%.1f s): route %s, %d pages" % (label, time.time() - started, index["engine"],
                                                                index["page_count"]))
                res = cite_find.search(Path(out) / "text" / ("brief-" + engine), PHRASE, out)
                if res["match"] not in ("exact", "normalized") or PAGE not in res["hits"][0]["pages"]:
                    raise RuntimeError("match %s on pages %s" % (res["match"], [h["page"] for h in res["hits"]]))
                print("OK   cite_find on %s text: %s match on p. %d" % (index["engine"], res["match"], PAGE))
            except Exception as err:
                failed += 1
                print("FAIL %s: %s" % (label, str(err)[:200]))
    print("%s" % ("all checks OK" if not failed else "%d check(s) failed" % failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
