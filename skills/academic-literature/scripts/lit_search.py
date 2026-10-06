#!/usr/bin/env python3
"""One query across OpenAlex, Crossref and Semantic Scholar. Results are de-duplicated by DOI, then by
normalised title (same title, years at most one apart), and ranked by reciprocal-rank fusion (a work
near the top of several lists ranks above a work near the top of one), scaled by the share of query
words found in the title or abstract. Prints a ranked table (or JSON) and appends one line per merged
work to research/sources.jsonl.

All three APIs are keyless. A source that fails (rate limit, outage) is reported and skipped; the
others still return results.
"""
import concurrent.futures
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402
import crossref  # noqa: E402
import openalex  # noqa: E402
import s2  # noqa: E402

API_NAMES = {"openalex": "openalex", "crossref": "crossref", "s2": "semantic-scholar"}
LETTERS = {"openalex": "O", "crossref": "C", "s2": "S"}
# Generic type -> each API's own type names; None means the API cannot filter on it (source skipped).
TYPE_MAP = {
    "article": {"openalex": ["article"], "crossref": ["journal-article"], "s2": ["JournalArticle"]},
    "report": {"openalex": ["report"], "crossref": ["report"], "s2": None},
    "preprint": {"openalex": ["preprint"], "crossref": ["posted-content"], "s2": None},
    "book": {"openalex": ["book"], "crossref": ["book"], "s2": ["Book"]},
    "review": {"openalex": ["review"], "crossref": None, "s2": ["Review"]},
}
RRF_K = 60
STOP = {"the", "and", "for", "with", "from", "into", "on", "of", "in", "a", "an", "to", "by", "at", "or", "is",
        "are", "what", "how", "does", "do", "its", "their", "effect", "effects", "impact", "impacts", "evidence"}

EPILOG = """examples:
  python3 lit_search.py "mobile money financial inclusion" --from-year 2018 --limit 5

--sources picks from openalex, crossref, s2 (default: all three).
--limit is per source, so three sources at --limit 10 give up to 30 rows before de-duplication.
Columns: in = found by O(penAlex), C(rossref), S(emantic Scholar); pdf = an open-access PDF link is known.
"""


def run_source(name, query, limit, from_year, to_year, gtype, oa_only):
    """Return (items, meta) for one API, applying the shared filters where the API supports them."""
    types = TYPE_MAP[gtype][name] if gtype else None
    if name == "openalex":
        return openalex.search(query, limit, None, from_year, to_year, types, oa_only=oa_only)
    if name == "crossref":
        return crossref.search(query, limit, None, from_year, to_year, types)
    year = None
    if from_year or to_year:
        year = "%s-%s" % (from_year or "", to_year or "")
    return s2.search(query, limit, year, None, oa_only, types)


def coverage(query, group):
    """Share of the query's content words found in the title or abstract (prefix match, so
    'transfer' finds 'transfers')."""
    terms = {t for t in c.norm_title(query).split() if len(t) > 2 and t not in STOP}
    if not terms:
        return 1.0
    words = c.norm_title("%s %s" % (group.get("title") or "", group.get("abstract") or "")).split()
    hits = 0
    for term in terms:
        stem = term[:-1] if term.endswith("s") and len(term) > 4 else term
        if any(w.startswith(stem) for w in words):
            hits += 1
    return hits / len(terms)


def merge(results, order, query=""):
    """Group the same work found by several APIs; keep the best of each field."""
    groups, by_doi, by_title = [], {}, {}
    for name in order:
        for item in results.get(name, []):
            group = by_doi.get(item["doi"]) if item.get("doi") else None
            title_key = c.norm_title(item.get("title"))
            if group is None and len(title_key) >= 12:
                for cand in by_title.get(title_key, []):
                    if not item.get("year") or not cand.get("year") or abs(item["year"] - cand["year"]) <= 1:
                        group = cand
                        break
            if group is None:
                group = {"doi": None, "other_dois": [], "title": None, "authors": [], "year": None, "date": None,
                         "type": None, "venue": None, "cited_by": None, "pdf_url": None, "is_oa": False,
                         "url": None, "abstract": None, "found_in": {}, "ids": []}
                groups.append(group)
            if item.get("doi"):
                if not group["doi"]:
                    group["doi"] = item["doi"]
                elif item["doi"] != group["doi"] and item["doi"] not in group["other_dois"]:
                    group["other_dois"].append(item["doi"])
                by_doi.setdefault(item["doi"], group)
            for key in ("title", "year", "date", "type", "venue", "pdf_url", "abstract"):
                if not group[key] and item.get(key):
                    group[key] = item[key]
            if len(item.get("authors") or []) > len(group["authors"]):
                group["authors"] = item["authors"]
            if item.get("cited_by") is not None:
                group["cited_by"] = max(group["cited_by"] or 0, item["cited_by"])
            group["is_oa"] = group["is_oa"] or bool(item.get("is_oa"))
            group["found_in"].setdefault(name, item.get("rank") or 99)
            group["ids"].append(item["id"])
            if title_key and group not in by_title.setdefault(title_key, []):
                by_title[title_key].append(group)
    for group in groups:
        group["url"] = c.doi_url(group["doi"]) or next(
            (it.get("url") for name in order for it in results.get(name, []) if it["id"] in group["ids"]), None)
        fused = sum(1.0 / (RRF_K + rank) for rank in group["found_in"].values())
        group["coverage"] = round(coverage(query, group), 2)
        group["score"] = round(fused * (0.5 + 0.5 * group["coverage"]), 5)
    groups.sort(key=lambda g: (-g["score"], -(g["cited_by"] or 0)))
    for rank, group in enumerate(groups, 1):
        group["rank"] = rank
    return groups


def to_record(group, query):
    found = ", ".join("%s #%d" % (API_NAMES[n], r) for n, r in group["found_in"].items())
    notes = "venue: %s; cited_by: %s; found in: %s" % (group.get("venue") or "-", group.get("cited_by"), found)
    if group["other_dois"]:
        notes += "; other DOIs: %s" % ", ".join(group["other_dois"])
    rec_id = "doi:" + group["doi"] if group["doi"] else group["ids"][0]
    return c.make_record(id=rec_id, source="+".join(API_NAMES[n] for n in group["found_in"]), type=group["type"],
                         title=group["title"], authors=group["authors"], year=group["year"], date=group["date"],
                         url=group["url"], pdf_url=group["pdf_url"], doi=group["doi"], query=query, notes=notes)


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", help="search words")
    ap.add_argument("--sources", default="openalex,crossref,s2", help="comma-separated: openalex, crossref, s2")
    ap.add_argument("--limit", type=int, default=10, help="results per source (default 10)")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--type", choices=sorted(TYPE_MAP), help="keep one kind of work in every source")
    ap.add_argument("--oa", action="store_true", help="open access only (OpenAlex, S2; Crossref cannot filter)")
    a = ap.parse_args(argv)
    order = [s.strip() for s in a.sources.split(",") if s.strip()]
    for name in order:
        if name not in API_NAMES:
            ap.error("unknown source %r; choose from openalex, crossref, s2" % name)

    status, results, jobs = {}, {}, {}
    for name in order:
        if a.type and TYPE_MAP[a.type][name] is None:
            status[name] = {"ok": False, "skipped": "cannot filter on type '%s'" % a.type}
            continue
        if a.oa and name == "crossref":
            status[name] = {"ok": False, "skipped": "no open-access filter in Crossref"}
            continue
        jobs[name] = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
        futures = {pool.submit(run_source, name, a.query, a.limit, a.from_year, a.to_year, a.type, a.oa): name
                   for name in jobs}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                items, meta = future.result()
            except c.FetchError as err:
                status[name] = {"ok": False, "error": str(err)}
                continue
            results[name] = items
            status[name] = {"ok": True, "count": meta.get("count"), "returned": len(items)}
            if meta.get("fallback"):
                status[name]["note"] = "relevance search throttled; used bulk search ordered by citations"
            if name == "openalex" and (meta.get("budget") or {}).get("remaining_usd") is not None:
                status[name]["budget_left_usd"] = meta["budget"]["remaining_usd"]
    groups = merge(results, [n for n in order if n in results], a.query)
    path = c.append_sources(a.out, [to_record(g, a.query) for g in groups])
    if a.json:
        c.print_json({"query": a.query, "sources": status,
                      "results": [dict(g, citation=c.academic_citation(g)) for g in groups]})
        return 0 if results else 1
    for name in order:
        st = status.get(name, {})
        if st.get("ok"):
            line = "%s: %s matches, %d returned" % (API_NAMES[name], st.get("count"), st["returned"])
            if st.get("note"):
                line += " (%s)" % st["note"]
            if st.get("budget_left_usd") is not None:
                line += " (keyless budget left today: $%s)" % st["budget_left_usd"]
        else:
            line = "%s: %s" % (API_NAMES[name], st.get("skipped") or "FAILED: %s" % st.get("error"))
        print(line)
    print("%d unique works after de-duplication\n" % len(groups))
    for g in groups:
        g["_in"] = "".join(LETTERS[n] for n in order if n in g["found_in"])
        g["_who"] = c.author_label(g["authors"])
        g["_pdf"] = "pdf" if g.get("pdf_url") else ("oa" if g.get("is_oa") else "-")
        g["_link"] = g["doi"] or g["url"]
    if groups:
        c.print_table(groups, [("#", "rank", 2), ("year", "year", 4), ("cites", "cited_by", 5), ("in", "_in", 3),
                               ("title", "title", 60), ("authors", "_who", 20), ("venue", "venue", 24),
                               ("pdf", "_pdf", 3), ("doi or url", "_link", None)])
    if path:
        print("logged %d records to %s" % (len(groups), path))
    return 0 if results else 1


if __name__ == "__main__":
    c.run(main)
