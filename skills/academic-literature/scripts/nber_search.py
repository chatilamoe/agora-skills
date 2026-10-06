#!/usr/bin/env python3
"""Search NBER working papers through the JSON listing behind nber.org's own search page.
Prints a table (or JSON) and appends one line per paper to research/sources.jsonl.

Keyless. This is an internal endpoint of nber.org, not a documented API: it may change without
notice. If it breaks, use openalex.py --series nber-wp or crossref.py --series nber-wp instead
(NBER working papers have DOIs 10.3386/wNNNNN). Abstracts here are cut at about 300 characters.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://www.nber.org/api/v1/working_page_listing/contentType/working_paper/_/_/search"
PACE = c.Pacer(0.5)
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                      "august", "september", "october", "november", "december"], 1)}

EPILOG = """examples:
  python3 nber_search.py "mobile money" --limit 5
  python3 nber_search.py "mobile money" --limit 5 --page 2

What comes back per paper: title, authors (as HTML links, stripped here), displaydate ("January 2011"),
a shortened abstract and url (/papers/w16721). The script adds the DOI (10.3386/w16721) and the
PDF link (https://www.nber.org/system/files/working_papers/w16721/w16721.pdf).
"""


def iso_month(display):
    m = re.match(r"\s*([A-Za-z]+)\s+(\d{4})", display or "")
    if m and m.group(1).lower() in MONTHS:
        return "%s-%02d" % (m.group(2), MONTHS[m.group(1).lower()])
    return str(c.year_of(display)) if c.year_of(display) else None


def to_item(r, rank=None):
    path = r.get("url") or ""
    number = path.rstrip("/").rsplit("/", 1)[-1]
    is_wp = re.match(r"w\d+$", number) is not None
    return {
        "api": "nber", "id": "nber:" + number, "doi": "10.3386/" + number if is_wp else None,
        "title": c.clean_text(r.get("title")), "authors": [c.clean_text(a) for a in r.get("authors") or []],
        "year": c.year_of(r.get("displaydate")), "date": iso_month(r.get("displaydate")), "type": "report",
        "venue": "NBER Working Paper %s" % number[1:] if is_wp else "NBER", "cited_by": None, "is_oa": True,
        "pdf_url": ("https://www.nber.org/system/files/working_papers/%s/%s.pdf" % (number, number)) if is_wp else None,
        "url": "https://www.nber.org" + path if path.startswith("/") else path,
        "abstract": c.clean_text(r.get("abstract")) or None, "rank": rank,
    }


def to_record(item, query):
    return c.make_record(id=item["id"], source="nber", type="report", title=item["title"], authors=item["authors"],
                         year=item["year"], date=item["date"], url=item["url"], pdf_url=item["pdf_url"],
                         doi=item["doi"], query=query, notes="%s; abstract shortened by NBER" % item["venue"])


def search(query, limit=10, page=1):
    """The endpoint honours perPage only from 20 to 100 (smaller values give 50), so fetch 20 or 100
    per call and slice to the page the caller asked for."""
    offset = (page - 1) * limit
    per = 20 if offset + limit <= 20 else 100
    server_page = offset // per + 1
    skip = offset % per
    rows, total = [], None
    while len(rows) < skip + limit:
        PACE.wait()
        data = c.get_json(API, {"page": server_page, "perPage": per, "q": query})
        total = data.get("totalResults")
        batch = data.get("results") or []
        rows.extend(batch)
        if len(batch) < per:
            break
        server_page += 1
    rows = rows[skip:skip + limit]
    items = [to_item(r, offset + i) for i, r in enumerate(rows, 1)]
    return items, {"api": "nber", "count": total, "page": page}


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", help="search words")
    ap.add_argument("--limit", type=int, default=10, help="results per page (default 10)")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--abstracts", action="store_true", help="print the (shortened) abstracts")
    a = ap.parse_args(argv)
    items, meta = search(a.query, a.limit, a.page)
    path = c.append_sources(a.out, [to_record(it, a.query) for it in items])
    if a.json:
        out = dict(meta)
        out["results"] = [dict(it, citation=c.academic_citation(it)) for it in items]
        c.print_json(out)
        return 0
    print("NBER: %s matches (the site's own search; loose matching); page %d, showing %d"
          % (meta["count"], a.page, len(items)))
    print()
    for it in items:
        it["_who"] = c.author_label(it["authors"])
    if items:
        c.print_table(items, [("#", "rank", 2), ("date", "date", 7), ("title", "title", 64), ("authors", "_who", 24),
                              ("doi", "doi", 16), ("pdf", "pdf_url", None)])
    else:
        print("no results")
    if a.abstracts:
        print()
        for it in items:
            print("[%s] %s" % (it["rank"], it.get("abstract") or "(no abstract)"))
    if path:
        print("logged %d records to %s" % (len(items), path))
    return 0


if __name__ == "__main__":
    c.run(main)
