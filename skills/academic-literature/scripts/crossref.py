#!/usr/bin/env python3
"""Search Crossref works (DOI metadata from publishers), filter by year, type and DOI prefix,
or look up DOIs. Prints a table (or JSON) and appends one line per work to research/sources.jsonl.

Crossref is keyless. Sending mailto puts you in the "polite" pool (3 requests a second today).
"""
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://api.crossref.org"
PACE = c.Pacer(1.0)
SELECT = ("DOI,title,subtitle,author,issued,type,container-title,publisher,is-referenced-by-count,"
          "URL,link,abstract")
SORTS = {"relevance": "relevance", "cites": "is-referenced-by-count", "date": "published"}
# Series checked on the client side, because Crossref has no DOI-pattern or series filter.
# (DOI prefix, extra server-side filter or None, client-side check, label)
SERIES = {
    "wb-prwp": ("10.1596", None, lambda m: m.get("DOI", "").lower().startswith("10.1596/1813-9450-"),
                "World Bank Policy Research Working Papers (deposited as type 'book')"),
    "imf-wp": ("10.5089", "type:journal-article", lambda m: "IMF Working Papers" in (m.get("container-title") or []),
               "IMF Working Papers (type 'journal-article', container 'IMF Working Papers')"),
    "nber-wp": ("10.3386", None, lambda m: re.match(r"10\.3386/w\d", m.get("DOI", "").lower()) is not None,
                "NBER Working Papers (type 'report')"),
}

EPILOG = """examples:
  python3 crossref.py "mobile money financial inclusion" --from-year 2020 --limit 5
  python3 crossref.py "social protection" --publisher worldbank --from-year 2023 --limit 5
  python3 crossref.py "fiscal multipliers" --series imf-wp --limit 5
  python3 crossref.py --doi 10.1596/1813-9450-11008

publisher presets (DOI prefixes): """ + ", ".join("%s=%s" % kv for kv in sorted(c.PREFIXES.items())) + """
series presets: """ + ", ".join(sorted(SERIES)) + """
types: journal-article, report, book, book-chapter, posted-content (preprints), dissertation,
  proceedings-article, monograph, dataset, other
"""


def date_parts(message):
    parts = ((message.get("issued") or {}).get("date-parts") or [[None]])[0]
    parts = [p for p in parts if p]
    if not parts:
        return None, None
    text = "%04d" % parts[0] + "".join("-%02d" % p for p in parts[1:3])
    return parts[0], text


def to_item(m, rank=None):
    doi = c.norm_doi(m.get("DOI"))
    title = c.clean_text(" ".join(m.get("title") or []))
    subtitle = c.clean_text(" ".join(m.get("subtitle") or []))
    if subtitle and subtitle.lower() not in title.lower():
        title = "%s: %s" % (title, subtitle)
    authors = []
    for a in m.get("author") or []:
        name = (" ".join(x for x in (a.get("given"), a.get("family")) if x)).strip() or a.get("name")
        if name:
            authors.append(c.clean_text(name))
    year, date = date_parts(m)
    institution = ((m.get("institution") or [{}])[0] or {}).get("name")
    venue = (c.series_from_doi(doi) or c.clean_text((m.get("container-title") or [None])[0])
             or institution or c.clean_text(m.get("publisher")) or None)
    links = [l.get("URL") for l in m.get("link") or [] if l.get("URL")]
    return {
        "api": "crossref", "id": "crossref:" + (doi or ""), "doi": doi, "title": title, "authors": authors,
        "year": year, "date": date, "type": m.get("type"), "venue": venue, "publisher": m.get("publisher"),
        "cited_by": m.get("is-referenced-by-count"), "is_oa": None, "pdf_url": None, "url": c.doi_url(doi),
        "landing_url": m.get("URL"), "abstract": c.clean_text(m.get("abstract")) or None,
        "publisher_links": links[:3], "rank": rank,
    }


def to_record(item, query):
    notes = "venue: %s; cited_by: %s; publisher: %s" % (item.get("venue") or "-", item.get("cited_by"),
                                                       item.get("publisher") or "-")
    return c.make_record(id=item["id"], source="crossref", type=item.get("type"), title=item["title"],
                         authors=item["authors"], year=item["year"], date=item["date"], url=item["url"],
                         pdf_url=None, doi=item["doi"], query=query, notes=notes)


def search(query=None, limit=10, sort=None, from_year=None, to_year=None, types=None, prefixes=None,
           series=None, extra=None):
    """Return (items, meta) for a Crossref /works query."""
    filters = []
    if from_year:
        filters.append("from-pub-date:%d" % from_year)
    if to_year:
        filters.append("until-pub-date:%d-12-31" % to_year)
    for t in types or []:
        filters.append("type:" + t)
    check = None
    prefixes = list(prefixes or [])
    if series:
        prefix, server_filter, check, _label = SERIES[series]
        if prefix not in prefixes:
            prefixes.append(prefix)
        if server_filter and server_filter not in filters:
            filters.append(server_filter)
    for p in prefixes:
        filters.append("prefix:" + c.PREFIXES.get(p, p))
    filters.extend(extra or [])
    if not query and not filters:
        raise c.FetchError("give a query, a filter, or --doi")
    sort_key = sort or ("relevance" if query else "date")
    rows = max(1, min(1000, limit * 5 if check else limit))
    params = {"rows": rows, "select": SELECT, "mailto": c.MAILTO, "sort": SORTS[sort_key], "order": "desc"}
    if query:
        params["query"] = query
    if filters:
        params["filter"] = ",".join(filters)
    PACE.wait()
    data = c.get_json(API + "/works", params)
    message = data.get("message") or {}
    raw = message.get("items") or []
    if check:
        raw = [m for m in raw if check(m)]
    items = [to_item(m, rank) for rank, m in enumerate(raw[:limit], 1)]
    meta = {"api": "crossref", "count": message.get("total-results"), "filter": params.get("filter"),
            "sort": params["sort"], "request": API + "/works?" + urllib.parse.urlencode(params)}
    if check:
        meta["notes"] = ["series %s checked on the first %d rows only" % (series, rows)]
    return items, meta


def get_work(doi):
    PACE.wait()
    data = c.get_json(API + "/works/" + urllib.parse.quote(c.norm_doi(doi), safe="/"), {"mailto": c.MAILTO})
    return to_item(data.get("message") or {}, 1)


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", nargs="?", help="search words (Crossref 'query': titles, authors, venues)")
    ap.add_argument("--doi", action="append", default=[], help="look up a DOI (repeatable)")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--type", help="comma-separated Crossref types, e.g. journal-article,report")
    ap.add_argument("--publisher", action="append", default=[], metavar="NAME_OR_PREFIX",
                    help="preset (worldbank, imf, nber, ...) or a DOI prefix like 10.1596 (repeatable)")
    ap.add_argument("--series", choices=sorted(SERIES), help="keep one working-paper series")
    ap.add_argument("--filter", action="append", default=[], help="raw Crossref filter, e.g. has-abstract:true")
    ap.add_argument("--sort", choices=sorted(SORTS), help="default: relevance with a query, else date")
    ap.add_argument("--limit", type=int, default=10, help="results to return (default 10)")
    ap.add_argument("--abstracts", action="store_true", help="print abstracts under the table")
    a = ap.parse_args(argv)

    if a.doi:
        items = [get_work(d) for d in a.doi]
        for rank, it in enumerate(items, 1):
            it["rank"] = rank
        meta = {"api": "crossref", "count": len(items)}
        records = [to_record(it, "doi:" + d) for it, d in zip(items, a.doi)]
    else:
        types = [t.strip() for t in a.type.split(",")] if a.type else None
        items, meta = search(a.query, a.limit, a.sort, a.from_year, a.to_year, types, a.publisher,
                             a.series, a.filter)
        records = [to_record(it, a.query or meta["filter"]) for it in items]
    path = c.append_sources(a.out, records)
    if a.json:
        out = dict(meta)
        out["results"] = [dict(it, citation=c.academic_citation(it)) for it in items]
        c.print_json(out)
        return 0
    if meta.get("filter"):
        print("filter: %s" % meta["filter"])
    print("Crossref: %s matches; showing %d" % (meta.get("count"), len(items)))
    print()
    for it in items:
        it["_who"] = c.author_label(it["authors"])
    if items:
        c.print_table(items, [("#", "rank", 2), ("year", "year", 4), ("type", "type", 15), ("cites", "cited_by", 5),
                              ("title", "title", 60), ("authors", "_who", 20), ("venue", "venue", 28),
                              ("doi", "doi", None)])
    else:
        print("no results")
    if a.abstracts:
        print()
        for it in items:
            print("[%s] %s" % (it["rank"], (it.get("abstract") or "(no abstract deposited)")[:600]))
    for note in meta.get("notes") or []:
        print("note: " + note)
    if path:
        print("logged %d records to %s" % (len(items), path))
    return 0


if __name__ == "__main__":
    c.run(main)
