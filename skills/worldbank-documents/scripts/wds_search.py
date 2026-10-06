#!/usr/bin/env python3
"""Search World Bank Documents & Reports (search.worldbank.org/api/v3/wds) and log what comes back.

Examples:
  python3 wds_search.py "financial inclusion" --country Nepal --rows 5
  python3 wds_search.py "global findex" --doctype "Policy Research Working Paper" --from 2020 --sort newest
  python3 wds_search.py --project P508961 --sort newest
  python3 wds_search.py "financial inclusion" --facets docty_exact,count_exact

Words in the query are ANDed; put a phrase in double quotes inside the query ('"mobile money"');
OR works ("findex OR nepal"). Filters are exact and case-sensitive ("Nepal", not "nepal").
Several values for one filter: separate with ';' (--country "Nepal;India").

Writes, under --out (default ./research):
  sources.jsonl          one line per document (appended)
  wds_<query>.csv        the result table (overwritten when the same search is run again)
"""
import argparse
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://search.worldbank.org/api/v3/wds"
# 'authr' is the name to request; the response key is 'authors'. Asking for 'authors' returns nothing.
FIELDS = ("id,display_title,docna,repnme,docdt,docty,majdocty,count,admreg,lang,authr,repnb,volnb,"
          "totvolnb,guid,keywd,abstracts,pdfurl,txturl,url,colti,projectid,dois")
SORTS = {"relevance": None, "newest": "desc", "oldest": "asc"}
CSV_COLUMNS = ["id", "title", "date", "doctype", "major_doctype", "country", "language", "report_no",
               "volume", "series", "project_id", "doi", "authors", "url", "pdf_url", "txt_url", "abstract"]


def _values(obj, key):
    """WDS packs lists as {"0": {key: v}, "1": {key: v}}; sometimes a plain dict or list."""
    if not obj:
        return []
    items = obj.values() if isinstance(obj, dict) else obj
    out = []
    for it in items:
        v = it.get(key) if isinstance(it, dict) else it
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    if not out and isinstance(obj, dict) and isinstance(obj.get(key), str):
        out.append(obj[key].strip())
    return out


def _text(v):
    """Plain string for fields that are usually strings but may arrive as lists."""
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x).strip() for x in v if x)
    return str(v).strip() if v else ""


def normalize(d):
    """One WDS document -> flat dict with stable names."""
    docna = c.clean((_values(d.get("docna"), "docna") or [""])[0])
    title = c.clean(d.get("display_title")) or docna or c.clean((_values(d.get("repnme"), "repnme") or [""])[0])
    if docna and docna != title and docna.startswith(title):
        title = docna  # chapters and summaries share display_title; docna adds " - Chapter 3 : ..."
    abstract = d.get("abstracts")
    if isinstance(abstract, dict):
        abstract = abstract.get("cdata!", "")
    date = c.iso_date(d.get("docdt"))
    return {
        "id": str(d.get("id", "")),
        "title": c.clean(title),
        "date": date,
        "year": int(date[:4]) if date else None,
        "doctype": _text(d.get("docty")),
        "major_doctype": _text(d.get("majdocty")),
        "country": _text(d.get("count")),
        "region": _text(d.get("admreg")),
        "language": _text(d.get("lang")),
        "report_no": _text(d.get("repnb")),
        "volume": _text(d.get("volnb")),
        "series": c.clean(_text(d.get("colti"))),
        "project_id": _text(d.get("projectid")),
        "doi": (_text(d.get("dois")).split(";")[0].strip() or None),
        "authors": _values(d.get("authors"), "author"),
        "keywords": _values(d.get("keywd"), "keywd"),
        "guid": d.get("guid") or "",
        "url": c.https(d.get("url")),
        "pdf_url": c.https(d.get("pdfurl")),
        "txt_url": c.https(d.get("txturl")),
        "abstract": c.clean(abstract),
    }


def to_source(doc, query_label):
    notes = "; ".join(x for x in [doc["doctype"], doc["country"], doc["language"],
                                  f"report no. {doc['report_no']}" if doc["report_no"] else ""] if x)
    return c.source_record(
        id=f"wds:{doc['id']}", source="worldbank-documents", type=(doc["doctype"] or "document").lower(),
        title=doc["title"], authors=doc["authors"], year=doc["year"], date=doc["date"], url=doc["url"],
        pdf_url=doc["pdf_url"], doi=doc["doi"], query=query_label, notes=notes)


def documents(data):
    """Documents in server order. Skip the 'facets' key that sits inside 'documents'."""
    docs = data.get("documents") or {}
    return [v for k, v in docs.items() if k.startswith("D") and isinstance(v, dict)]


def filter_params(a):
    p = {}
    if a.query:
        p["qterm"] = a.query
    join = lambda s: "^".join(x.strip() for x in s.split(";") if x.strip())  # noqa: E731
    if a.country:
        p["count_exact"] = join(a.country)
    if a.doctype:
        p["docty_exact"] = join(a.doctype)
    if a.major_doctype:
        p["majdocty_exact"] = join(a.major_doctype)
    if a.lang:
        p["lang_exact"] = join(a.lang)
    if a.region:
        p["admreg_exact"] = join(a.region)
    if a.project:
        p["projectid"] = a.project.strip().upper()
    if a.date_from or a.date_to:
        # Always send both ends: strdate on its own only returns that one calendar year.
        p["strdate"] = c.date_bound(a.date_from or "1900")
        p["enddate"] = c.date_bound(a.date_to, end=True) if a.date_to else c.today()
    return p


def query_label(a, p):
    parts = [a.query] if a.query else []
    names = {"count_exact": "country", "docty_exact": "doctype", "majdocty_exact": "major_doctype",
             "lang_exact": "lang", "admreg_exact": "region", "projectid": "project",
             "strdate": "from", "enddate": "to"}
    parts += [f"{names[k]}={p[k]}" for k in names if k in p]
    return " | ".join(parts)


def show_facets(a, p):
    fields = [f.strip() for f in a.facets.split(",") if f.strip()]
    url = c.build_url(API, dict(p, format="json", rows=0, fct=",".join(fields)))
    data = c.get_json(url)
    facets = (data.get("documents") or {}).get("facets") or {}
    out = {}
    for f in fields:
        vals = facets.get(f) or {}
        items = vals.values() if isinstance(vals, dict) else vals
        out[f] = [{"value": v.get("name"), "count": v.get("count")} for v in items if isinstance(v, dict)]
    if a.json:
        c.print_json({"api": "wds", "url": url, "total": data.get("total"), "facets": out})
        return
    print(f"{data.get('total')} documents match; top facet values (pass a value back as a filter):")
    for f, vals in out.items():
        print(f"\n{f}:" + ("" if vals else " (no values; check the field name)"))
        for v in vals[:30]:
            print(f"  {str(v['count']).rjust(7)}  {v['value']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="search words (optional if a filter is given)")
    ap.add_argument("--country", help="country name, exact and case-sensitive (e.g. Nepal); ';' for several")
    ap.add_argument("--doctype", help='document type, e.g. "Policy Research Working Paper", "Report", "Publication"')
    ap.add_argument("--major-doctype", help='e.g. "Publications & Research", "Project Documents"')
    ap.add_argument("--lang", help="language, e.g. English, French, Spanish")
    ap.add_argument("--region", help='Bank region, e.g. "South Asia", "Eastern and Southern Africa"')
    ap.add_argument("--project", help="project id, e.g. P508961: documents of one project")
    ap.add_argument("--from", dest="date_from", help="earliest document date: YYYY, YYYY-MM or YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", help="latest document date (default today when --from is given)")
    ap.add_argument("--sort", choices=sorted(SORTS), default="relevance", help="default relevance")
    ap.add_argument("--rows", type=int, default=20, help="results per page, 1-100 (default 20)")
    ap.add_argument("--pages", type=int, default=1, help="pages to fetch (default 1)")
    ap.add_argument("--facets", help="list values and counts for these fields instead of documents, "
                                     "e.g. docty_exact,count_exact,lang_exact,majdocty_exact,admreg_exact")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_intermixed_args()
    a.query = " ".join(a.query).strip()

    p = filter_params(a)
    if not p:
        ap.error("give search words or at least one filter")
    if a.facets:
        try:
            show_facets(a, p)
        except c.FetchError as e:
            c.die(str(e))
        return

    rows = max(1, min(a.rows, 100))
    params = dict(p, format="json", fl=FIELDS, rows=rows)
    if SORTS[a.sort]:
        params.update(srt="docdt", order=SORTS[a.sort])

    results, total, first_url = [], 0, None
    try:
        for page in range(max(1, a.pages)):
            url = c.build_url(API, dict(params, os=page * rows))
            first_url = first_url or url
            if page:
                time.sleep(c.PAGE_SLEEP)
            data = c.get_json(url)
            total = int(data.get("total") or 0)
            batch = [normalize(d) for d in documents(data)]
            results.extend(batch)
            if not batch or (page + 1) * rows >= total:
                break
    except c.FetchError as e:
        c.die(str(e))

    label = query_label(a, p)
    out = pathlib.Path(a.out)
    csv_path = None
    if results:
        c.log_sources(out, [to_source(d, label) for d in results])
        csv_path = c.write_csv(out / f"wds_{c.slug(label)}.csv", results, CSV_COLUMNS)

    if a.json:
        c.print_json({"api": "wds", "query": label, "url": first_url, "total": total,
                      "returned": len(results), "results": results})
    else:
        print(f'{c.plural(total, "document")} match{"es" if total == 1 else ""} "{label}"; '
              f'showing {len(results)}, sorted by {a.sort}')
        if results:
            c.print_table(results, [("id", "id", 9), ("date", "date", 10), ("type", "doctype", 24),
                                    ("country", "country", 14), ("title", "title", 80)])
    if results:
        c.say(f"wrote {csv_path} ({c.plural(len(results), 'row')}); appended {c.plural(len(results), 'line')} "
              f"to {out / 'sources.jsonl'}", a.json)
        c.say("next: wds_get.py ID for all fields; fetch_pdf.py wds:ID for the PDF", a.json)
    else:
        c.say("no documents found; nothing written. Try fewer words, OR, or --facets to see filter values.",
              a.json)


if __name__ == "__main__":
    main()
