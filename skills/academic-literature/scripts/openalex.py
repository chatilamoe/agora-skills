#!/usr/bin/env python3
"""Search OpenAlex works with filters (year, type, institution, series), a grey-literature mode,
and DOI look-ups. Prints a table (or JSON) and appends one line per work to research/sources.jsonl.

OpenAlex is keyless, but it now meters keyless use: about US$0.10 a day per IP address.
A search costs $0.001 (about 100 searches a day), a filter-only list $0.0001, a single DOI
look-up and the institution autocomplete are free. The script prints what is left.
"""
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://api.openalex.org"
PACE = c.Pacer(1.0)
SELECT = ("id,doi,display_name,publication_year,publication_date,type,cited_by_count,open_access,"
          "primary_location,best_oa_location,locations,authorships,abstract_inverted_index")

# OpenAlex institution IDs, checked 2026-10-06 with /autocomplete/institutions.
INSTITUTIONS = {
    "worldbank": ["I1334329717", "I55633929"],  # World Bank; World Bank Group
    "imf": ["I1310145890"],
    "nber": ["I1321305853"],
    "cepr": ["I4210140326"],
    "un": ["I1286959531"],
    "undp": ["I107145371"],
    "unicef": ["I112289208"],
    "fao": ["I1320745970"],
    "ilo": ["I1285985921"],
    "who": ["I4210105654"],
    "unu-wider": ["I32309878"],
    "unctad": ["I4405271075"],
    "oecd": ["I1288051870"],
    "idb": ["I184564680"],
    "adb": ["I4210129130"],
    "afdb": ["I1330402449"],
    "ebrd": ["I35841627"],
    "bis": ["I52989892"],
    "wto": ["I1285402005"],
    "ifpri": ["I150314799"],
    "jpal": ["I4210113636"],
    "ipa": ["I1313272365"],
    "3ie": ["I4210121424"],
}
GREY = ["worldbank", "imf", "un", "undp", "unicef", "fao", "ilo", "who", "unu-wider", "unctad",
        "oecd", "idb", "adb", "afdb", "ebrd", "bis", "wto", "ifpri"]

# Series presets: (OpenAlex filter, what it selects, client-side landing-URL check or None).
SERIES = {
    "wb-prwp": ("doi_starts_with:10.1596/1813-9450", "World Bank Policy Research Working Papers", None),
    "worldbank": ("doi_starts_with:10.1596", "World Bank publications with a 10.1596 DOI", None),
    "imf-wp": ("primary_location.source.id:S4210171147", "IMF Working Papers", None),
    "imf": ("doi_starts_with:10.5089", "IMF publications with a 10.5089 DOI", None),
    "nber-wp": ("doi_starts_with:10.3386/w", "NBER Working Papers", None),
    "3ie": ("doi_starts_with:10.23846", "3ie impact evaluations, systematic reviews, working papers", None),
    "cepr-dp": ("locations.source.id:S4306401271,authorships.institutions.lineage:I4210140326",
                "CEPR Discussion Papers (RePEc copies with a cepr.org link)", "cepr.org"),
    "repec": ("locations.source.id:S4306401271", "works OpenAlex holds from RePEc", None),
    "ssrn": ("locations.source.id:S4210172589", "SSRN papers", None),
    "wber": ("primary_location.source.id:S2735890421", "The World Bank Economic Review", None),
    "wbro": ("primary_location.source.id:S117685085", "The World Bank Research Observer", None),
    "jde": ("primary_location.source.id:S101209419", "Journal of Development Economics", None),
    "jdeff": ("primary_location.source.id:S136516072", "Journal of Development Effectiveness", None),
}
SORTS = {"relevance": "relevance_score:desc", "cites": "cited_by_count:desc", "date": "publication_date:desc"}

EPILOG = """examples:
  python3 openalex.py "mobile money financial inclusion" --from-year 2018 --limit 5 --abstracts
  python3 openalex.py "cash transfers" --series wb-prwp --from-year 2022 --limit 5
  python3 openalex.py "debt restructuring" --grey --from-year 2020 --limit 5
  python3 openalex.py --doi 10.1596/1813-9450-9000 --doi 10.1111/joes.12372

series presets: """ + ", ".join(sorted(SERIES)) + """
institution presets: """ + ", ".join(sorted(INSTITUTIONS)) + """ (or an OpenAlex ID such as I1334329717,
  or any name, resolved with the free autocomplete endpoint)
types: article, report, preprint, book, book-chapter, review, dissertation, dataset, other
"""


def rebuild_abstract(inverted):
    """OpenAlex stores abstracts as {word: [positions]}; put the words back in order."""
    if not inverted:
        return None
    slots = [(pos, word) for word, positions in inverted.items() for pos in positions]
    return " ".join(word for _, word in sorted(slots))


def to_item(work, rank=None):
    doi = c.norm_doi(work.get("doi"))
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    best = work.get("best_oa_location") or {}
    access = work.get("open_access") or {}
    locations = work.get("locations") or []
    pdf = best.get("pdf_url") or primary.get("pdf_url")
    if not pdf:
        pdf = next((loc.get("pdf_url") for loc in locations if loc.get("pdf_url")), None)
    if not pdf and c.looks_like_pdf(access.get("oa_url")):
        pdf = access.get("oa_url")
    authors, institutions = [], []
    for authorship in work.get("authorships") or []:
        name = (authorship.get("author") or {}).get("display_name") or authorship.get("raw_author_name")
        if name:
            authors.append(name)
        for inst in authorship.get("institutions") or []:
            if inst.get("display_name") and inst["display_name"] not in institutions:
                institutions.append(inst["display_name"])
    landing = primary.get("landing_page_url") or work.get("id")
    return {
        "api": "openalex",
        "id": "openalex:" + str(work.get("id", "")).rsplit("/", 1)[-1],
        "doi": doi,
        "title": c.clean_text(work.get("display_name") or work.get("title")),
        "authors": authors,
        "year": work.get("publication_year"),
        "date": work.get("publication_date"),
        "type": work.get("type"),
        "venue": c.series_from_doi(doi) or c.clean_text(source.get("display_name")) or None,
        "cited_by": work.get("cited_by_count"),
        "is_oa": access.get("is_oa"),
        "oa_status": access.get("oa_status"),
        "pdf_url": pdf,
        "oa_url": access.get("oa_url"),
        "url": c.doi_url(doi) or landing,
        "landing_url": landing,
        "institutions": institutions[:12],
        "abstract": rebuild_abstract(work.get("abstract_inverted_index")),
        "rank": rank,
        "_landing_urls": [loc.get("landing_page_url") or "" for loc in locations],
    }


def to_record(item, query):
    notes = "venue: %s; cited_by: %s; oa: %s" % (item.get("venue") or "-", item.get("cited_by"),
                                                 item.get("oa_status") or "-")
    return c.make_record(id=item["id"], source="openalex", type=item.get("type"), title=item["title"],
                         authors=item["authors"], year=item["year"], date=item["date"], url=item["url"],
                         pdf_url=item["pdf_url"], doi=item["doi"], query=query, notes=notes)


def budget(headers):
    """Cost of the call and the keyless budget left today, from OpenAlex's rate-limit headers."""
    if headers is None:
        return {}
    keys = {"cost_usd": "X-RateLimit-Cost-USD", "remaining_usd": "X-RateLimit-Remaining-USD",
            "limit_usd": "X-RateLimit-Limit-USD", "reset_seconds": "X-RateLimit-Reset"}
    out = {}
    for name, header in keys.items():
        value = headers.get(header)
        if value not in (None, ""):
            try:
                out[name] = float(value)
            except ValueError:
                out[name] = value
    return out


def resolve_institution(name):
    """Preset name, OpenAlex ID, or free-text name (resolved with the free autocomplete endpoint)."""
    key = name.strip().lower()
    if key in INSTITUTIONS:
        return INSTITUTIONS[key]
    if key.upper().startswith("I") and key[1:].isdigit():
        return [key.upper()]
    PACE.wait()
    data = c.get_json(API + "/autocomplete/institutions", {"q": name, "mailto": c.MAILTO})
    results = data.get("results") or []
    if not results:
        raise c.FetchError("no OpenAlex institution matches %r" % name)
    top = results[0]
    print("  institution %r -> %s (%s)" % (name, top["id"].rsplit("/", 1)[-1], top.get("display_name")),
          file=sys.stderr)
    return [top["id"].rsplit("/", 1)[-1]]


def build_filters(from_year=None, to_year=None, types=None, institutions=None, series=None,
                  grey=False, oa_only=False, min_cites=None, extra=None):
    filters, notes = [], []
    if from_year:
        filters.append("from_publication_date:%d-01-01" % from_year)
    if to_year:
        filters.append("to_publication_date:%d-12-31" % to_year)
    if grey and not types:
        types = ["report"]
    if types:
        filters.append("type:" + "|".join(types))
    ids = []
    for name in (GREY if grey else []) + list(institutions or []):
        for inst in resolve_institution(name):
            if inst not in ids:
                ids.append(inst)
    if ids:
        filters.append("authorships.institutions.lineage:" + "|".join(ids))
    url_check = None
    if series:
        if series not in SERIES:
            raise c.FetchError("unknown series %r; choose from %s" % (series, ", ".join(sorted(SERIES))))
        flt, label, url_check = SERIES[series]
        filters.append(flt)
        notes.append("series: " + label)
    if oa_only:
        filters.append("open_access.is_oa:true")
    if min_cites:
        filters.append("cited_by_count:>%d" % (int(min_cites) - 1))
    filters.extend(extra or [])
    return ",".join(filters), url_check, notes


def search(query=None, limit=10, sort=None, from_year=None, to_year=None, types=None, institutions=None,
           series=None, grey=False, oa_only=False, min_cites=None, extra=None):
    """Return (items, meta). items are dicts from to_item(); meta has count, cost and budget."""
    flt, url_check, notes = build_filters(from_year, to_year, types, institutions, series, grey,
                                          oa_only, min_cites, extra)
    if not query and not flt:
        raise c.FetchError("give a query, a filter, or --doi")
    sort_key = sort or ("relevance" if query else "cites")
    if sort_key == "relevance" and not query:
        sort_key = "cites"
    per_page = max(1, min(200, limit * 3 if url_check else limit))
    params = {"per-page": per_page, "select": SELECT, "mailto": c.MAILTO, "sort": SORTS[sort_key]}
    if query:
        params["search"] = query
    if flt:
        params["filter"] = flt
    PACE.wait()
    data, headers = c.get_json(API + "/works", params, with_headers=True)
    items = [to_item(work) for work in data.get("results") or []]
    if url_check:
        items = [it for it in items if any(url_check in (u or "") for u in it["_landing_urls"])]
    items = items[:limit]
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    meta = {"api": "openalex", "count": (data.get("meta") or {}).get("count"), "filter": flt or None,
            "sort": params["sort"], "notes": notes, "budget": budget(headers),
            "request": API + "/works?" + urllib.parse.urlencode(params)}
    return items, meta


def get_work(doi_or_id):
    """One work by DOI (or OpenAlex W-id). Free under the keyless budget."""
    key = doi_or_id.strip()
    if key.upper().startswith("W") and key[1:].isdigit():
        path = key.upper()
    else:
        path = "doi:" + c.norm_doi(key)
    PACE.wait()
    work = c.get_json(API + "/works/" + urllib.parse.quote(path, safe=":/"),
                      {"mailto": c.MAILTO, "select": SELECT})
    return to_item(work, 1)


def print_items(items, show_abstracts=False):
    for it in items:
        it["_who"] = c.author_label(it["authors"])
        it["_pdf"] = "pdf" if it.get("pdf_url") else ("oa" if it.get("is_oa") else "-")
        it["_link"] = it["doi"] or it["url"]
    c.print_table(items, [("#", "rank", 2), ("year", "year", 4), ("type", "type", 12), ("cites", "cited_by", 5),
                          ("title", "title", 60), ("authors", "_who", 20), ("venue", "venue", 26),
                          ("oa", "_pdf", 3), ("doi or url", "_link", None)])
    if show_abstracts:
        print()
        for it in items:
            print("[%s] %s" % (it["rank"], (it.get("abstract") or "(no abstract in OpenAlex)")[:600]))


def public(item):
    return {k: v for k, v in item.items() if not k.startswith("_")}


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("query", nargs="?", help="search words (OpenAlex 'search': title, abstract and full text)")
    ap.add_argument("--doi", action="append", default=[], help="look up a DOI or OpenAlex W-id (repeatable; free)")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--type", help="comma-separated OpenAlex types, e.g. article,report")
    ap.add_argument("--institution", action="append", default=[], help="preset, OpenAlex ID or name (repeatable)")
    ap.add_argument("--series", choices=sorted(SERIES), help="working-paper series or journal preset")
    ap.add_argument("--grey", action="store_true",
                    help="grey literature: type report, authors at the World Bank, IMF, UN agencies, OECD, MDBs")
    ap.add_argument("--filter", action="append", default=[], help="raw OpenAlex filter, e.g. language:en")
    ap.add_argument("--oa", action="store_true", help="open-access works only")
    ap.add_argument("--min-cites", type=int)
    ap.add_argument("--sort", choices=sorted(SORTS), help="default: relevance with a query, else cites")
    ap.add_argument("--limit", type=int, default=10, help="results to return (1-200, default 10)")
    ap.add_argument("--abstracts", action="store_true", help="print abstracts under the table")
    a = ap.parse_args(argv)

    if a.doi:
        items = []
        for value in a.doi:
            items.append(get_work(value))
        for rank, it in enumerate(items, 1):
            it["rank"] = rank
        meta = {"api": "openalex", "count": len(items), "lookup": a.doi}
        records = [to_record(it, "doi:" + value) for it, value in zip(items, a.doi)]
    else:
        types = [t.strip() for t in a.type.split(",")] if a.type else None
        items, meta = search(a.query, a.limit, a.sort, a.from_year, a.to_year, types, a.institution,
                             a.series, a.grey, a.oa, a.min_cites, a.filter)
        records = [to_record(it, a.query or meta["filter"]) for it in items]
    path = c.append_sources(a.out, records)
    if a.json:
        out = dict(meta)
        out["results"] = [dict(public(it), citation=c.academic_citation(it)) for it in items]
        c.print_json(out)
        return 0
    if meta.get("filter"):
        print("filter: %s" % meta["filter"])
    print("OpenAlex: %s matches; showing %d" % (meta.get("count"), len(items)))
    print()
    if items:
        print_items(items, a.abstracts)
    else:
        print("no results")
    b = meta.get("budget") or {}
    if "remaining_usd" in b:
        print("\nOpenAlex keyless budget: this call $%s; $%s of $%s left today (resets 00:00 UTC)"
              % (b.get("cost_usd", "?"), b.get("remaining_usd"), b.get("limit_usd", "0.1")))
    if path:
        print("logged %d records to %s" % (len(items), path))
    return 0


if __name__ == "__main__":
    c.run(main)
