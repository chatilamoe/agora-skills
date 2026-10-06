#!/usr/bin/env python3
"""Search the World Bank Open Knowledge Repository (OKR, DSpace 7 REST API) and get each item's PDF link.

Examples:
  python3 okr_search.py "global findex" --size 5
  python3 okr_search.py "financial inclusion" --country Nepal --sort newest
  python3 okr_search.py "mobile money" --doctype "Policy Research Working Paper" --from 2020 --to 2025
  python3 okr_search.py --doi 10.1596/1813-9450-11021
  python3 okr_search.py --handle 10986/43438
  python3 okr_search.py "financial inclusion" --facets doctype,country

OKR holds the Bank's formal publications (books, flagship reports, Policy Research Working Papers,
journal articles) with DOIs under the prefix 10.1596. Project documents are not here; use wds_search.py.

Writes, under --out (default ./research):
  sources.jsonl        one line per item (appended)
  okr_<query>.csv      the result table (overwritten when the same search is run again)
"""
import argparse
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402

BASE = "https://openknowledge.worldbank.org/server/api"
SEARCH = BASE + "/discover/search/objects"
SORTS = {"relevance": None, "newest": "dc.date.issued,DESC", "oldest": "dc.date.issued,ASC",
         "title": "dc.title,ASC"}
CSV_COLUMNS = ["handle", "title", "date", "authors", "doi", "type", "doctype", "series", "countries", "url",
               "pdf_url", "pdf_name", "pdf_bytes", "other_pdfs", "wds_id", "report_no", "rights", "abstract"]


def mv(md, key):
    return [x.get("value") for x in md.get(key, []) if isinstance(x, dict) and x.get("value")]


def first(md, *keys):
    for k in keys:
        vals = mv(md, k)
        if vals:
            return vals[0]
    return None


def pdf_bitstreams(io):
    """PDF files in the item's ORIGINAL bundle (needs embed=bundles/bitstreams), best guess first."""
    bundles = (((io.get("_embedded") or {}).get("bundles") or {}).get("_embedded") or {}).get("bundles") or []
    pdfs = []
    for b in bundles:
        if b.get("name") != "ORIGINAL":
            continue
        bits = (((b.get("_embedded") or {}).get("bitstreams") or {}).get("_embedded") or {}).get("bitstreams") or []
        for bs in bits:
            name = bs.get("name") or ""
            if not name.lower().endswith(".pdf"):
                continue
            md = bs.get("metadata") or {}
            href = ((bs.get("_links") or {}).get("content") or {}).get("href") \
                or f"{BASE}/core/bitstreams/{bs.get('uuid')}/content"
            pdfs.append({"name": name, "description": first(md, "dc.description") or "",
                         "language": first(md, "bitstream.language") or "", "bytes": bs.get("sizeBytes"),
                         "sequence": bs.get("sequenceId"), "url": href})

    def rank(p):
        text = (p["description"] + " " + p["name"]).lower()
        r = 0 if "full report" in text else (2 if ("summary" in text or "overview" in text) else 1)
        seq = p["sequence"] if isinstance(p["sequence"], int) else 10 ** 9
        return (r, seq)

    return sorted(pdfs, key=rank)


def normalize(io):
    md = io.get("metadata") or {}
    title = first(md, "dc.title") or io.get("name") or ""
    sub = first(md, "dc.title.subtitle")
    if sub and sub.lower() not in title.lower():
        title = f"{title}: {sub}"
    date = c.iso_date(first(md, "dc.date.issued"))
    handle = io.get("handle") or ""
    pdfs = pdf_bitstreams(io)
    wds_pdf = c.https(first(md, "okr.pdfurl"))
    wds_id = first(md, "okr.identifier.externaldocumentum")
    best = pdfs[0] if pdfs else None
    return {
        "uuid": io.get("uuid"),
        "handle": handle,
        "title": c.clean(title),
        "date": date,
        "year": int(date[:4]) if date else None,
        "authors": mv(md, "dc.contributor.author"),
        "doi": first(md, "dc.identifier.doi", "okr.identifier.doi"),
        "type": first(md, "dc.type") or (mv(md, "okr.doctype") or [""])[0].split("::")[-1],
        "doctype": "; ".join(mv(md, "okr.doctype")),
        "series": "; ".join(mv(md, "dc.relation.ispartofseries")),
        "countries": mv(md, "okr.region.country"),
        "language": first(md, "dc.language", "dc.language.iso") or "",
        "rights": first(md, "dc.rights") or "",
        "report_no": first(md, "okr.identifier.report") or "",
        "wds_id": f"wds:{wds_id}" if wds_id else "",
        "url": first(md, "dc.identifier.uri") or (f"https://hdl.handle.net/{handle}" if handle else ""),
        "landing_page": f"https://openknowledge.worldbank.org/entities/publication/{io.get('uuid')}",
        "pdf_url": best["url"] if best else wds_pdf,
        "pdf_name": best["name"] if best else "",
        "pdf_bytes": best["bytes"] if best else None,
        "other_pdfs": len(pdfs) - 1 if pdfs else 0,
        "pdfs": pdfs,
        "wds_pdf_url": wds_pdf,
        "abstract": c.clean(first(md, "dc.description.abstract")),
    }


def to_source(it, label):
    notes = [it["doctype"] or it["type"]]
    if it["series"]:
        notes.append(f"series: {it['series']}")
    if it["countries"]:
        notes.append("countries: " + ", ".join(it["countries"][:5]))
    if it["wds_id"]:
        notes.append(f"same document as {it['wds_id']} in Documents & Reports")
    if it["pdfs"] and len(it["pdfs"]) > 1:
        notes.append(f"{len(it['pdfs'])} PDFs in the item; pdf_url is {it['pdf_name']}")
    return c.source_record(
        id=f"okr:{it['handle']}", source="worldbank-documents", type=(it["type"] or "publication").lower(),
        title=it["title"], authors=it["authors"], year=it["year"], date=it["date"], url=it["url"],
        pdf_url=it["pdf_url"], doi=it["doi"], query=label, notes="; ".join(n for n in notes if n))


def search_params(a):
    p = {}
    if a.doi:
        d = a.doi.strip().replace("https://doi.org/", "")
        p["query"] = f'dc.identifier.doi:"{d}" OR okr.identifier.doi:"{d}"'
    elif a.handle:
        h = a.handle.strip().replace("https://hdl.handle.net/", "")
        p["query"] = f'handle:"{h}"'
    elif a.query:
        p["query"] = a.query
    p["f.entityType"] = "Publication,equals"  # leave out Person, Series and Journal records
    if a.country:
        p["f.country"] = f"{a.country},equals"
    if a.doctype:
        p["f.doctype"] = f"{a.doctype},equals"
    if a.author:
        p["f.author"] = f"{a.author},contains"  # 'Surname, Given,equals' does not match; contains does
    if a.date_from or a.date_to:
        p["f.dateIssued"] = f"[{a.date_from or 1900} TO {a.date_to or c.today()[:4]}],equals"
    return p


def query_label(a, p):
    if a.doi or a.handle:
        parts = [f"doi={a.doi}" if a.doi else f"handle={a.handle}"]
    else:
        parts = [p["query"]] if p.get("query") else []
    for flag, val in (("country", a.country), ("doctype", a.doctype), ("author", a.author),
                      ("from", a.date_from), ("to", a.date_to)):
        if val:
            parts.append(f"{flag}={val}")
    return " | ".join(parts) or "all"


def show_facets(a, p):
    out = {}
    for name in [f.strip() for f in a.facets.split(",") if f.strip()]:
        url = c.build_url(f"{BASE}/discover/facets/{name}", dict(p, size=30))
        data = c.get_json(url)
        vals = (data.get("_embedded") or {}).get("values") or []
        out[name] = [{"value": v.get("label"), "count": v.get("count")} for v in vals]
        time.sleep(c.PAGE_SLEEP)
    if a.json:
        c.print_json({"api": "okr", "facets": out})
        return
    for name, vals in out.items():
        print(f"{name}:" + ("" if vals else " (no values)"))
        for v in vals:
            print(f"  {str(v['count']).rjust(7)}  {v['value']}")
        print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="search words")
    ap.add_argument("--doi", help="look up one item by DOI (10.1596/...)")
    ap.add_argument("--handle", help="look up one item by handle (10986/...)")
    ap.add_argument("--country", help="country as OKR spells it, e.g. Nepal")
    ap.add_argument("--doctype", help='e.g. "Policy Research Working Paper", "Report", "Journal Article", "Brief"')
    ap.add_argument("--author", help="author surname (matches any author containing it)")
    ap.add_argument("--from", dest="date_from", type=int, help="first year issued")
    ap.add_argument("--to", dest="date_to", type=int, help="last year issued")
    ap.add_argument("--sort", choices=sorted(SORTS), default="relevance", help="default relevance")
    ap.add_argument("--size", type=int, default=10, help="results per page, 1-50 (default 10)")
    ap.add_argument("--pages", type=int, default=1, help="pages to fetch (default 1)")
    ap.add_argument("--no-pdf", action="store_true", help="skip the file lookup (smaller, faster responses)")
    ap.add_argument("--facets", help="list values and counts instead of items: doctype,country,author,"
                                     "dateIssued,topic,subject,region,supportedlanguage")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_intermixed_args()
    a.query = " ".join(a.query).strip()
    if not (a.query or a.doi or a.handle or a.country or a.doctype or a.author or a.date_from or a.date_to):
        ap.error("give search words, --doi, --handle or a filter")

    p = search_params(a)
    if a.facets:
        try:
            show_facets(a, p)
        except c.FetchError as e:
            c.die(str(e))
        return

    size = max(1, min(a.size, 50))
    params = dict(p, size=size)
    if SORTS[a.sort]:
        params["sort"] = SORTS[a.sort]
    if not a.no_pdf:
        params["embed"] = "bundles/bitstreams"  # one call returns each item's files too

    items, total, first_url = [], 0, None
    try:
        for page in range(max(1, a.pages)):
            url = c.build_url(SEARCH, dict(params, page=page))
            first_url = first_url or url
            if page:
                time.sleep(c.PAGE_SLEEP)
            data = c.get_json(url)
            sr = (data.get("_embedded") or {}).get("searchResult") or {}
            pg = sr.get("page") or {}
            total = int(pg.get("totalElements") or 0)
            objs = (sr.get("_embedded") or {}).get("objects") or []
            batch = [normalize((o.get("_embedded") or {}).get("indexableObject") or {}) for o in objs]
            items.extend(x for x in batch if x["handle"])
            if not objs or page + 1 >= int(pg.get("totalPages") or 0):
                break
    except c.FetchError as e:
        c.die(str(e))

    label = query_label(a, p)
    out = pathlib.Path(a.out)
    csv_path = None
    if items:
        c.log_sources(out, [to_source(it, label) for it in items])
        csv_path = c.write_csv(out / f"okr_{c.slug(label)}.csv", items, CSV_COLUMNS)

    if a.json:
        c.print_json({"api": "okr", "query": label, "url": first_url, "total": total,
                      "returned": len(items), "results": items})
    else:
        print(f'{c.plural(total, "OKR item")} match{"es" if total == 1 else ""} "{label}"; '
              f'showing {len(items)}, sorted by {a.sort}')
        if items:
            for it in items:
                it["pdf"] = (f"{it['pdf_bytes'] / 1e6:.1f} MB" if it["pdf_bytes"] else
                             ("via D&R" if it["pdf_url"] else "none"))
            c.print_table(items, [("handle", "handle", 11), ("date", "date", 10), ("type", "type", 12),
                                  ("pdf", "pdf", 8), ("title", "title", 80)])
    if items:
        c.say(f"wrote {csv_path} ({c.plural(len(items), 'row')}); appended {c.plural(len(items), 'line')} "
              f"to {out / 'sources.jsonl'}", a.json)
        c.say("next: fetch_pdf.py okr:HANDLE downloads the pdf_url logged for that item", a.json)
    else:
        c.say("no items found; nothing written. Try fewer words or --facets to see filter values.", a.json)


if __name__ == "__main__":
    main()
