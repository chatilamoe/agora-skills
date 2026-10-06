#!/usr/bin/env python3
"""Get the full metadata of World Bank documents by id (Documents & Reports API v3).

Examples:
  python3 wds_get.py 31476985
  python3 wds_get.py wds:18419181 D33863209 --json
  python3 wds_get.py 570891571303596376          # an 18-digit guid, as in documents.worldbank.org URLs
  python3 wds_get.py --report WPS6630            # a report number

An id of 12 or more digits is treated as a guid; shorter ones as the WDS document id.

Writes, under --out (default ./research):
  sources.jsonl            one line per document found (appended)
  meta/wds_<id>.json       every field the API returned, unchanged
"""
import argparse
import json
import pathlib
import re
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402
from wds_search import API, documents, normalize, to_source  # noqa: E402

SHOWN = ["title", "date", "doctype", "major_doctype", "country", "region", "language", "report_no",
         "volume", "series", "project_id", "doi", "authors", "guid", "url", "pdf_url", "txt_url"]


def lookup_param(raw, as_report=False):
    """Return (param, value) for the API: id=, guid= or repnb=."""
    s = raw.strip()
    if as_report:
        return "repnb", s
    s = re.sub(r"^(?:wds:|D(?=\d+$))", "", s, flags=re.I)
    if not s.isdigit():
        return "repnb", s  # e.g. WPS6630, ICRR0022192
    return ("guid", s) if len(s) >= 12 else ("id", s)


def show(doc, raw):
    print(f"wds:{doc['id']}")
    for k in SHOWN:
        v = doc.get(k)
        if v:
            print(f"  {k:<14}{'; '.join(v) if isinstance(v, list) else v}")
    if doc["keywords"]:
        print(f"  {'keywords':<14}{'; '.join(doc['keywords'][:15])}" + (" ..." if len(doc["keywords"]) > 15 else ""))
    if doc["abstract"]:
        a = doc["abstract"]
        print(f"  {'abstract':<14}{a[:700]}" + (" ..." if len(a) > 700 else ""))
    used = {"id", "display_title", "docna", "repnme", "docdt", "docty", "majdocty", "count", "admreg", "lang",
            "authors", "repnb", "volnb", "colti", "projectid", "keywd", "guid", "url", "pdfurl", "txturl",
            "abstracts", "entityids", "dois"}
    other = {k: v for k, v in raw.items() if k not in used and v not in ("", None, [], {})}
    if other:
        print("  other fields:")
        for k, v in other.items():
            s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            print(f"    {k:<20}{c.clean(s)[:110]}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+", help="document id(s): 31476985, D31476985, wds:31476985, or a guid")
    ap.add_argument("--report", action="store_true", help="treat the ids as report numbers (e.g. WPS6630)")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout")
    a = ap.parse_intermixed_args()

    out = pathlib.Path(a.out)
    found, missing = [], []
    try:
        for i, raw_id in enumerate(a.ids):
            if i:
                time.sleep(c.PAGE_SLEEP)
            param, value = lookup_param(raw_id, a.report)
            url = c.build_url(API, {"format": "json", param: value, "rows": 10})
            docs = documents(c.get_json(url))
            if not docs:
                missing.append(raw_id)
                continue
            for raw in docs:
                doc = normalize(raw)
                doc["api_url"] = url
                found.append((doc, raw))
    except c.FetchError as e:
        c.die(str(e))

    for doc, raw in found:
        meta = out / "meta" / f"wds_{c.safe_name(doc['id'])}.json"
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        doc["meta_file"] = str(meta)
    if found:
        c.log_sources(out, [to_source(d, f"wds_get {d['id']}") for d, _ in found])

    if a.json:
        c.print_json([dict(d, raw=r) for d, r in found])
    else:
        for doc, raw in found:
            show(doc, raw)
    if found:
        c.say(f"saved {c.plural(len(found), 'metadata file')} under {out / 'meta'}; appended "
              f"{c.plural(len(found), 'line')} to {out / 'sources.jsonl'}", a.json)
    if missing:
        print(f"not found: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
