#!/usr/bin/env python3
"""Search arXiv preprints (Atom API), optionally within economics, finance and applied-statistics
categories. Prints a table (or JSON) and appends one line per preprint to research/sources.jsonl.

arXiv is keyless. Its terms ask for no more than one request every three seconds; this script
waits three seconds between calls. Preprints are not peer reviewed: say so when you cite one.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://export.arxiv.org/api/query"
PACE = c.Pacer(3.0)
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom",
      "os": "http://a9.com/-/spec/opensearch/1.1/"}
GROUPS = {
    "econ": ["econ.EM", "econ.GN", "econ.TH"],
    "q-fin": ["q-fin.CP", "q-fin.EC", "q-fin.GN", "q-fin.MF", "q-fin.PM", "q-fin.PR", "q-fin.RM",
              "q-fin.ST", "q-fin.TR"],
}
DEV_ECON = ["econ.EM", "econ.GN", "econ.TH", "q-fin.EC", "q-fin.GN", "stat.AP"]
SORTS = {"relevance": "relevance", "submitted": "submittedDate", "updated": "lastUpdatedDate"}

EPILOG = """examples:
  python3 arxiv_search.py "mobile money" --econ --limit 5
  python3 arxiv_search.py "remittances" --cat econ.GN --from-year 2024 --sort submitted --limit 5
  python3 arxiv_search.py 'ti:"difference-in-differences" AND cat:econ.EM' --limit 5

--econ = econ.EM, econ.GN, econ.TH, q-fin.EC, q-fin.GN, stat.AP
--cat takes a category (econ.GN, stat.AP, cs.CY ...) or a group: econ, q-fin (repeatable)
Queries that already use arXiv field syntax (ti:, abs:, au:, cat:, all:) are passed through as written.
"""


def build_query(query, cats=None, phrase=False, from_year=None, to_year=None):
    if re.search(r"\b(ti|au|abs|co|jr|cat|rn|id|all|submittedDate):", query):
        q = query
    elif phrase:
        q = 'all:"%s"' % query.replace('"', "")
    else:
        words = re.findall(r"[\w.\-']+", query)
        q = " AND ".join("all:%s" % w for w in words) or 'all:"%s"' % query
    expanded = []
    for cat in cats or []:
        for item in GROUPS.get(cat, [cat]):
            if item not in expanded:
                expanded.append(item)
    if expanded:
        q = "(%s) AND (%s)" % (q, " OR ".join("cat:" + x for x in expanded))
    if from_year or to_year:
        q = "(%s) AND submittedDate:[%d01010000 TO %d12312359]" % (q, from_year or 1991, to_year or 2100)
    return q


def parse_feed(body):
    root = ET.fromstring(body)
    total = root.findtext("os:totalResults", default="0", namespaces=NS)
    items = []
    for entry in root.findall("a:entry", NS):
        raw_id = entry.findtext("a:id", default="", namespaces=NS)
        if "/api/errors" in raw_id:
            raise c.FetchError("arXiv rejected the query: %s" % c.clean_text(entry.findtext("a:summary", namespaces=NS)))
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1]
        base = re.sub(r"v\d+$", "", arxiv_id)
        pdf = None
        for link in entry.findall("a:link", NS):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf = link.get("href")
        primary = entry.find("arxiv:primary_category", NS)
        journal_doi = c.norm_doi(entry.findtext("arxiv:doi", namespaces=NS))
        published = entry.findtext("a:published", default="", namespaces=NS)[:10] or None
        items.append({
            "api": "arxiv", "id": "arxiv:" + base, "arxiv_id": arxiv_id,
            "doi": journal_doi or "10.48550/arxiv." + base.lower(),
            "journal_doi": journal_doi, "journal_ref": c.clean_text(entry.findtext("arxiv:journal_ref", namespaces=NS)) or None,
            "title": c.clean_text(entry.findtext("a:title", namespaces=NS)),
            "authors": [c.clean_text(a.findtext("a:name", namespaces=NS)) for a in entry.findall("a:author", NS)],
            "year": c.year_of(published), "date": published,
            "updated": entry.findtext("a:updated", default="", namespaces=NS)[:10] or None,
            "type": "preprint", "venue": "arXiv " + (primary.get("term") if primary is not None else ""),
            "categories": [cat.get("term") for cat in entry.findall("a:category", NS)],
            "cited_by": None, "is_oa": True, "pdf_url": pdf or "https://arxiv.org/pdf/" + arxiv_id,
            "url": "https://arxiv.org/abs/" + base, "abstract": c.clean_text(entry.findtext("a:summary", namespaces=NS)),
            "comment": c.clean_text(entry.findtext("arxiv:comment", namespaces=NS)) or None,
        })
    return int(total or 0), items


def search(query, limit=10, cats=None, sort="relevance", phrase=False, from_year=None, to_year=None, start=0):
    q = build_query(query, cats, phrase, from_year, to_year)
    params = {"search_query": q, "start": start, "max_results": max(1, min(2000, limit)),
              "sortBy": SORTS[sort], "sortOrder": "descending"}
    PACE.wait()
    body, _headers, _url = c.http_get(API, params, {"Accept": "application/atom+xml"})
    total, items = parse_feed(body)
    for rank, it in enumerate(items, start + 1):
        it["rank"] = rank
    return items, {"api": "arxiv", "count": total, "search_query": q, "sort": SORTS[sort]}


def to_record(item, query):
    notes = "%s; categories: %s; not peer reviewed" % (item["venue"], ", ".join(item.get("categories") or []))
    if item.get("journal_ref"):
        notes += "; published as: %s" % item["journal_ref"]
    return c.make_record(id=item["id"], source="arxiv", type="preprint", title=item["title"], authors=item["authors"],
                         year=item["year"], date=item["date"], url=item["url"], pdf_url=item["pdf_url"],
                         doi=item["doi"], query=query, notes=notes)


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", help="search words, or arXiv query syntax")
    ap.add_argument("--cat", action="append", default=[], help="category or group (repeatable)")
    ap.add_argument("--econ", action="store_true", help="restrict to " + ", ".join(DEV_ECON))
    ap.add_argument("--phrase", action="store_true", help="search the words as one exact phrase")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--sort", choices=sorted(SORTS), default="relevance")
    ap.add_argument("--limit", type=int, default=10, help="results to return (default 10, max 2000)")
    ap.add_argument("--abstracts", action="store_true", help="print abstracts under the table")
    a = ap.parse_args(argv)
    cats = list(a.cat) + (DEV_ECON if a.econ else [])
    items, meta = search(a.query, a.limit, cats, a.sort, a.phrase, a.from_year, a.to_year)
    path = c.append_sources(a.out, [to_record(it, a.query) for it in items])
    if a.json:
        out = dict(meta)
        out["results"] = [dict(it, citation=c.academic_citation(it)) for it in items]
        c.print_json(out)
        return 0
    print("arXiv: %s matches for %s; showing %d" % (meta["count"], meta["search_query"], len(items)))
    print()
    for it in items:
        it["_who"] = c.author_label(it["authors"])
    if items:
        c.print_table(items, [("#", "rank", 2), ("date", "date", 10), ("title", "title", 64), ("authors", "_who", 22),
                              ("category", "venue", 22), ("url", "url", None)])
    else:
        print("no results")
    if a.abstracts:
        print()
        for it in items:
            print("[%s] %s" % (it["rank"], it["abstract"][:600]))
    if path:
        print("logged %d records to %s" % (len(items), path))
    return 0


if __name__ == "__main__":
    c.run(main)
