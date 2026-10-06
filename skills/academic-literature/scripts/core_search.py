#!/usr/bin/env python3
"""Search CORE (core.ac.uk), the aggregator of open-access repositories: theses, working papers
and author manuscripts that journals and publishers do not index. Prints a table (or JSON) and
appends one line per work to research/sources.jsonl.

No key needed at low volume: keyless calls are limited to about 10 per window (the
X-RateLimit-* headers), and after a 429 CORE may ask you to wait about ten minutes. A free key
raises the limits but is not required, and this skill does not use one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

# Trailing slash matters: without it CORE answers 301 and the redirect costs one of your requests.
API = "https://api.core.ac.uk/v3/search/works/"
PACE = c.Pacer(1.0)

EPILOG = """examples:
  python3 core_search.py "cash transfers" --from-year 2020 --limit 5

CORE query syntax: field:value with AND / OR, e.g. title:"..." authors:"..." yearPublished>=2020 doi:"10..."
"""


def to_item(r, rank=None):
    doi = c.norm_doi(r.get("doi"))
    display = next((l.get("url") for l in r.get("links") or [] if l.get("type") == "display"), None)
    journals = r.get("journals") or []
    venue = c.clean_text((journals[0] or {}).get("title")) if journals else None
    providers = [p.get("name") for p in r.get("dataProviders") or [] if p.get("name")]
    published = (r.get("publishedDate") or "")[:10] or None
    return {
        "api": "core", "id": "core:%s" % r.get("id"), "doi": doi, "title": c.clean_text(r.get("title")),
        "authors": [c.clean_text(a.get("name")) for a in r.get("authors") or [] if a.get("name")],
        "year": r.get("yearPublished"), "date": published, "type": r.get("documentType") or None,
        "venue": venue or c.clean_text(r.get("publisher")) or None, "cited_by": r.get("citationCount"),
        "is_oa": True, "pdf_url": r.get("downloadUrl") or None, "url": c.doi_url(doi) or display,
        "landing_url": display, "abstract": c.clean_text(r.get("abstract")) or None,
        "providers": providers[:5], "rank": rank,
    }


def to_record(item, query):
    notes = "venue: %s; repositories: %s" % (item.get("venue") or "-", "; ".join(item.get("providers") or []) or "-")
    if item.get("landing_url"):
        notes += "; core: %s" % item["landing_url"]
    return c.make_record(id=item["id"], source="core", type=item.get("type"), title=item["title"],
                         authors=item["authors"], year=item["year"], date=item["date"], url=item["url"],
                         pdf_url=item["pdf_url"], doi=item["doi"], query=query, notes=notes)


def search(query, limit=10, from_year=None, to_year=None):
    q = query
    if from_year:
        q = "(%s) AND yearPublished>=%d" % (q, from_year)
    if to_year:
        q = "(%s) AND yearPublished<=%d" % (q, to_year)
    params = {"q": q, "limit": max(1, min(100, limit * 2)), "offset": 0, "exclude": "fullText"}
    PACE.wait()
    data = c.get_json(API, params)
    items, seen = [], set()
    for r in data.get("results") or []:
        it = to_item(r)
        key = it["doi"] or "%s|%s" % (c.norm_title(it["title"]), it["year"])
        if key in seen:  # CORE often returns the same paper from two repositories
            continue
        seen.add(key)
        items.append(it)
    items = items[:limit]
    for rank, it in enumerate(items, 1):
        it["rank"] = rank
    return items, {"api": "core", "count": data.get("totalHits"), "q": q}


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", help="search words or CORE query syntax")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--limit", type=int, default=10, help="results to return (default 10)")
    ap.add_argument("--abstracts", action="store_true", help="print abstracts under the table")
    a = ap.parse_args(argv)
    items, meta = search(a.query, a.limit, a.from_year, a.to_year)
    path = c.append_sources(a.out, [to_record(it, a.query) for it in items])
    if a.json:
        out = dict(meta)
        out["results"] = [dict(it, citation=c.academic_citation(it)) for it in items]
        c.print_json(out)
        return 0
    print("CORE: %s matches for %s; showing %d (duplicates from several repositories removed)"
          % (meta["count"], meta["q"], len(items)))
    print()
    for it in items:
        it["_who"] = c.author_label(it["authors"])
        it["_pdf"] = "pdf" if it.get("pdf_url") else "-"
    if items:
        c.print_table(items, [("#", "rank", 2), ("year", "year", 4), ("title", "title", 64), ("authors", "_who", 22),
                              ("venue or publisher", "venue", 26), ("pdf", "_pdf", 3), ("url", "url", None)])
    else:
        print("no results")
    if a.abstracts:
        print()
        for it in items:
            print("[%s] %s" % (it["rank"], (it.get("abstract") or "(no abstract)")[:600]))
    if path:
        print("logged %d records to %s" % (len(items), path))
    return 0


if __name__ == "__main__":
    c.run(main)
