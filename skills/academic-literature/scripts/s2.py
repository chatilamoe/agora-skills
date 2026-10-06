#!/usr/bin/env python3
"""Search Semantic Scholar, look up a paper (DOI, arXiv id or S2 id), or list its citations or
references. Prints a table (or JSON) and appends one line per paper to research/sources.jsonl.

Keyless use shares one pool with every other keyless user and is limited to about one request
a second. The relevance search (/paper/search) is often throttled (HTTP 429) at busy times; after
three retries this script falls back to /paper/search/bulk, which is ordered by citation count,
not relevance, and says so. Use --no-fallback to fail instead.
"""
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://api.semanticscholar.org/graph/v1"
PACE = c.Pacer(1.1)
FIELDS = ("title,year,authors,externalIds,openAccessPdf,citationCount,abstract,venue,publicationTypes,"
          "publicationDate,url,journal")
LIST_FIELDS = "title,year,authors,externalIds,openAccessPdf,citationCount,venue,publicationDate,url"
TYPES = {"JournalArticle": "article", "Review": "review", "Conference": "conference-paper", "Book": "book",
         "BookSection": "book-chapter", "Dataset": "dataset", "Editorial": "editorial", "Study": "article",
         "CaseReport": "article", "ClinicalTrial": "article", "MetaAnalysis": "review", "News": "other",
         "LettersAndComments": "other"}

EPILOG = """examples:
  python3 s2.py "mobile money financial inclusion" --year 2018-2025 --limit 5
  python3 s2.py --paper 10.1111/joes.12372
  python3 s2.py --citations 10.1111/joes.12372 --limit 5
  python3 s2.py --references 10.1111/joes.12372 --limit 5

paper ids: a DOI (10.x/...), DOI:..., ARXIV:2412.03879, CorpusId:..., or a 40-character S2 paperId
"""


def paper_id(value):
    value = value.strip()
    if value.lower().startswith("https://doi.org/") or value.startswith("10."):
        return "DOI:" + c.norm_doi(value)
    return value


def to_item(p, rank=None):
    ext = p.get("externalIds") or {}
    doi = c.norm_doi(ext.get("DOI"))
    oa = p.get("openAccessPdf") or {}
    oa_url = oa.get("url") or None
    venue = c.series_from_doi(doi) or c.clean_text(p.get("venue") or (p.get("journal") or {}).get("name")) or None
    types = p.get("publicationTypes") or []
    return {
        "api": "semantic-scholar", "id": "s2:" + str(p.get("paperId")), "doi": doi,
        "title": c.clean_text(p.get("title")), "authors": [a.get("name") for a in p.get("authors") or [] if a.get("name")],
        "year": p.get("year"), "date": p.get("publicationDate"), "type": TYPES.get(types[0]) if types else None,
        "venue": venue, "cited_by": p.get("citationCount"), "is_oa": bool(oa_url), "oa_status": oa.get("status"),
        "pdf_url": oa_url if c.looks_like_pdf(oa_url) else None, "oa_url": oa_url,
        "url": c.doi_url(doi) or p.get("url"), "landing_url": p.get("url"), "abstract": p.get("abstract"),
        "arxiv": ext.get("ArXiv"), "rank": rank,
    }


def to_record(item, query, note=""):
    notes = "venue: %s; cited_by: %s; oa: %s" % (item.get("venue") or "-", item.get("cited_by"),
                                                 item.get("oa_status") or "-")
    if item.get("oa_url") and not item.get("pdf_url"):
        notes += "; oa_url: %s" % item["oa_url"]
    if note:
        notes += "; " + note
    return c.make_record(id=item["id"], source="semantic-scholar", type=item.get("type"), title=item["title"],
                         authors=item["authors"], year=item["year"], date=item["date"], url=item["url"],
                         pdf_url=item["pdf_url"], doi=item["doi"], query=query, notes=notes)


def _get(path, params):
    PACE.wait()
    return c.get_json(API + path, params)


def bulk(query, limit=10, year=None, fields_of_study=None, oa_only=False):
    """/paper/search/bulk: boolean query, up to 1000 papers per call, sorted by citation count."""
    params = {"query": query, "fields": LIST_FIELDS, "sort": "citationCount:desc"}
    if year:
        params["year"] = year
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if oa_only:
        params["openAccessPdf"] = ""
    data = _get("/paper/search/bulk", params)
    items = [to_item(p, rank) for rank, p in enumerate((data.get("data") or [])[:limit], 1)]
    return items, {"api": "semantic-scholar", "endpoint": "/paper/search/bulk", "count": data.get("total"),
                   "order": "citation count (not relevance)"}


def search(query, limit=10, year=None, fields_of_study=None, oa_only=False, pub_types=None, fallback=True):
    """Relevance search; falls back to bulk search when the shared keyless pool answers 429."""
    params = {"query": query, "limit": max(1, min(100, limit)), "fields": FIELDS}
    if year:
        params["year"] = year
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if pub_types:
        params["publicationTypes"] = ",".join(pub_types)
    if oa_only:
        params["openAccessPdf"] = ""
    try:
        data = _get("/paper/search", params)
    except c.FetchError as err:
        if not fallback or "429" not in str(err):
            raise
        print("  semantic scholar: relevance search is throttled for keyless users right now; "
              "falling back to /paper/search/bulk (ordered by citations)", file=sys.stderr)
        items, meta = bulk(query, limit, year, fields_of_study, oa_only)
        meta["fallback"] = True
        return items, meta
    items = [to_item(p, rank) for rank, p in enumerate(data.get("data") or [], 1)]
    return items, {"api": "semantic-scholar", "endpoint": "/paper/search", "count": data.get("total"),
                   "order": "relevance"}


def get_paper(value):
    return to_item(_get("/paper/" + urllib.parse.quote(paper_id(value), safe=":/"), {"fields": FIELDS}), 1)


def neighbours(value, kind="citations", limit=10):
    """Papers citing (kind='citations') or cited by (kind='references') the given paper."""
    key = "citingPaper" if kind == "citations" else "citedPaper"
    data = _get("/paper/%s/%s" % (urllib.parse.quote(paper_id(value), safe=":/"), kind),
                {"fields": LIST_FIELDS, "limit": max(1, min(1000, limit))})
    rows = [row.get(key) or {} for row in data.get("data") or []]
    return [to_item(p, rank) for rank, p in enumerate(rows, 1) if p.get("paperId")]


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", nargs="?", help="search words")
    ap.add_argument("--paper", action="append", default=[], help="look up a paper by DOI or id (repeatable)")
    ap.add_argument("--citations", metavar="ID", help="list papers that cite this paper")
    ap.add_argument("--references", metavar="ID", help="list papers this paper cites")
    ap.add_argument("--year", help="e.g. 2018-2025, 2020-, -2015 or 2024")
    ap.add_argument("--fields-of-study", help="e.g. Economics or Economics,Political Science")
    ap.add_argument("--type", help="S2 publication types, e.g. JournalArticle,Review")
    ap.add_argument("--oa", action="store_true", help="only papers with an open-access PDF")
    ap.add_argument("--bulk", action="store_true", help="use /paper/search/bulk (boolean query, citation order)")
    ap.add_argument("--no-fallback", action="store_true", help="fail on 429 instead of falling back to bulk")
    ap.add_argument("--limit", type=int, default=10, help="results to return (default 10)")
    ap.add_argument("--abstracts", action="store_true", help="print abstracts under the table")
    a = ap.parse_args(argv)

    meta = {"api": "semantic-scholar"}
    if a.paper:
        items = [get_paper(v) for v in a.paper]
        for rank, it in enumerate(items, 1):
            it["rank"] = rank
        records = [to_record(it, "paper:" + v) for it, v in zip(items, a.paper)]
    elif a.citations or a.references:
        kind = "citations" if a.citations else "references"
        target = a.citations or a.references
        items = neighbours(target, kind, a.limit)
        note = ("cites %s" if kind == "citations" else "cited by %s") % target
        records = [to_record(it, "%s:%s" % (kind, target), note) for it in items]
        meta.update({"endpoint": "/paper/{id}/" + kind, "count": len(items)})
    elif a.query:
        if a.bulk:
            items, meta = bulk(a.query, a.limit, a.year, a.fields_of_study, a.oa)
        else:
            types = [t.strip() for t in a.type.split(",")] if a.type else None
            items, meta = search(a.query, a.limit, a.year, a.fields_of_study, a.oa, types, not a.no_fallback)
        records = [to_record(it, a.query) for it in items]
    else:
        ap.error("give a query, --paper, --citations or --references")
    path = c.append_sources(a.out, records)
    if a.json:
        out = dict(meta)
        out["results"] = [dict(it, citation=c.academic_citation(it)) for it in items]
        c.print_json(out)
        return 0
    if meta.get("endpoint"):
        print("Semantic Scholar %s: %s matches; showing %d%s" % (
            meta["endpoint"], meta.get("count"), len(items),
            "; ordered by %s" % meta["order"] if meta.get("order") else ""))
        print()
    for it in items:
        it["_who"] = c.author_label(it["authors"])
        it["_pdf"] = "pdf" if it.get("pdf_url") else ("oa" if it.get("is_oa") else "-")
        it["_link"] = it["doi"] or it["url"]
    if items:
        c.print_table(items, [("#", "rank", 2), ("year", "year", 4), ("cites", "cited_by", 5), ("title", "title", 60),
                              ("authors", "_who", 20), ("venue", "venue", 26), ("oa", "_pdf", 3),
                              ("doi or url", "_link", None)])
    elif a.references or a.citations:
        print("no results: Semantic Scholar has no %s list for this paper (common for working papers)"
              % ("reference" if a.references else "citation"))
    else:
        print("no results")
    if a.abstracts:
        print()
        for it in items:
            print("[%s] %s" % (it["rank"], (it.get("abstract") or "(no abstract from S2)")[:600]))
    if path:
        print("logged %d records to %s" % (len(items), path))
    return 0


if __name__ == "__main__":
    c.run(main)
