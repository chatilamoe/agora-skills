#!/usr/bin/env python3
"""Find the best open-access PDF link for one or more DOIs: OpenAlex first (a free look-up per DOI),
then Unpaywall, then known URL patterns (NBER, arXiv). --check confirms that the link returns a PDF.
Prints a table (or JSON) and appends one line per DOI to research/sources.jsonl.

Both APIs are keyless. Unpaywall needs a real email address in ?email=, which this script sends
(decaihub@worldbank.org). Unpaywall asks for no more than 100,000 calls a day.
"""
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

OPENALEX = "https://api.openalex.org/works/"
UNPAYWALL = "https://api.unpaywall.org/v2/"
PACE_OA = c.Pacer(1.0)
PACE_UP = c.Pacer(0.5)
VERSION_RANK = {"publishedVersion": 0, "acceptedVersion": 1, "submittedVersion": 2}
SELECT = "id,doi,display_name,publication_year,publication_date,type,authorships,open_access,best_oa_location,locations"

EPILOG = """examples:
  python3 oa_pdf.py 10.1111/joes.12372
  python3 oa_pdf.py 10.3386/w16721 10.1596/1813-9450-9000 10.1093/wbro/lky001 --check
  python3 oa_pdf.py 10.1111/joes.12372 --check --all

Order of preference: the OpenAlex best open-access location, other OpenAlex locations (published,
then accepted, then submitted version), Unpaywall's best location and others, then URL patterns
(NBER 10.3386/wN, arXiv 10.48550/arXiv.N). With --check, the first link that returns %PDF wins.
"""


def _not_found(err):
    return "HTTP 404" in str(err)


def from_openalex(doi):
    PACE_OA.wait()
    try:
        w = c.get_json(OPENALEX + "doi:" + urllib.parse.quote(doi, safe="/"), {"mailto": c.MAILTO, "select": SELECT})
    except c.FetchError as err:
        if _not_found(err):
            return {}, [], []
        raise
    best = w.get("best_oa_location") or {}
    locations = w.get("locations") or []
    cands = []
    ordered = [best] + sorted(locations, key=lambda l: VERSION_RANK.get(l.get("version"), 3))
    for loc in ordered:
        if loc.get("pdf_url"):
            cands.append({"pdf_url": loc["pdf_url"], "via": "openalex", "version": loc.get("version"),
                          "license": loc.get("license"), "host": (loc.get("source") or {}).get("display_name")})
    landing = [l.get("landing_page_url") for l in locations if l.get("landing_page_url")]
    meta = {"title": c.clean_text(w.get("display_name")), "year": w.get("publication_year"),
            "date": w.get("publication_date"), "type": w.get("type"),
            "authors": [(a.get("author") or {}).get("display_name") for a in w.get("authorships") or []
                        if (a.get("author") or {}).get("display_name")],
            "oa_status": (w.get("open_access") or {}).get("oa_status")}
    return meta, cands, landing


def from_unpaywall(doi):
    PACE_UP.wait()
    try:
        d = c.get_json(UNPAYWALL + urllib.parse.quote(doi, safe="/"), {"email": c.MAILTO})
    except c.FetchError as err:
        if _not_found(err):
            return {}, [], []
        raise
    best = d.get("best_oa_location") or {}
    cands, landing = [], []
    for loc in [best] + (d.get("oa_locations") or []):
        host = loc.get("repository_institution") or loc.get("host_type")
        if loc.get("url_for_pdf"):
            cands.append({"pdf_url": loc["url_for_pdf"], "via": "unpaywall", "version": loc.get("version"),
                          "license": loc.get("license"), "host": host})
        if loc.get("url_for_landing_page"):
            landing.append(loc["url_for_landing_page"])
    meta = {"title": c.clean_text(d.get("title")), "year": d.get("year"), "date": d.get("published_date"),
            "type": d.get("genre"), "oa_status": d.get("oa_status"),
            "authors": [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in d.get("z_authors") or []]}
    return meta, cands, landing


def from_pattern(doi):
    m = re.match(r"10\.3386/(w\d+)$", doi)
    if m:
        w = m.group(1)
        return [{"pdf_url": "https://www.nber.org/system/files/working_papers/%s/%s.pdf" % (w, w),
                 "via": "pattern:nber", "version": "publishedVersion", "license": None, "host": "nber.org"}]
    m = re.match(r"10\.48550/arxiv\.(.+)$", doi)
    if m:
        return [{"pdf_url": "https://arxiv.org/pdf/" + m.group(1), "via": "pattern:arxiv",
                 "version": "submittedVersion", "license": None, "host": "arxiv.org"}]
    return []


def check_pdf(url):
    """Read the first bytes of url; (True, detail) if it is a PDF."""
    try:
        body, headers, final = c.http_get(url, headers={"Range": "bytes=0-1023", "Accept": "application/pdf,*/*"},
                                         retries=(2,), max_bytes=1024)
    except c.FetchError as err:
        return False, str(err).split(" for ")[0][:80]
    ctype = (headers.get("Content-Type") or "").split(";")[0]
    if body.lstrip()[:4] == b"%PDF":
        return True, "PDF (%s)" % (ctype or "no content type")
    return False, "not a PDF: %s" % (ctype or "unknown type")


def hint(doi):
    if doi.startswith("10.1596/"):
        return ("World Bank: the PDF sits on documents.worldbank.org or openknowledge.worldbank.org; "
                "use the worldbank-documents skill, or open the landing page")
    if doi.startswith("10.5089/"):
        return "IMF: the IMF eLibrary landing page links a free PDF for working papers"
    return "no open-access copy known to OpenAlex or Unpaywall; use the landing page"


def resolve(doi, check=False, list_all=False):
    doi = c.norm_doi(doi)
    meta, cands, landing = from_openalex(doi)
    sources_used = ["openalex"]
    if list_all or not cands:
        up_meta, up_cands, up_landing = from_unpaywall(doi)
        sources_used.append("unpaywall")
        cands += up_cands
        landing += up_landing
        meta = meta or up_meta
    cands += from_pattern(doi)
    seen, unique = set(), []
    for cand in cands:
        if cand["pdf_url"] not in seen:
            seen.add(cand["pdf_url"])
            unique.append(cand)
    chosen = unique[0] if unique else None
    if check and unique:
        chosen = None
        for cand in unique:
            ok, detail = check_pdf(cand["pdf_url"])
            cand["check"] = detail
            if ok:
                chosen = cand
                break
        if chosen is None and not list_all and "unpaywall" not in sources_used:
            _m, more, more_landing = from_unpaywall(doi)
            sources_used.append("unpaywall")
            landing += more_landing
            for cand in more:
                if cand["pdf_url"] in seen:
                    continue
                ok, detail = check_pdf(cand["pdf_url"])
                cand["check"] = detail
                unique.append(cand)
                if ok:
                    chosen = cand
                    break
    landing = list(dict.fromkeys(u for u in landing if u))
    return {"doi": doi, "title": meta.get("title"), "year": meta.get("year"), "date": meta.get("date"),
            "type": meta.get("type"), "authors": meta.get("authors") or [], "oa_status": meta.get("oa_status"),
            "pdf_url": chosen["pdf_url"] if chosen else None, "via": chosen["via"] if chosen else None,
            "version": chosen.get("version") if chosen else None, "license": chosen.get("license") if chosen else None,
            "host": chosen.get("host") if chosen else None, "check": chosen.get("check") if chosen else None,
            "candidates": unique, "landing_pages": landing[:5], "looked_up": sources_used,
            "hint": None if chosen else blocked_hint(unique) or hint(doi)}


def blocked_hint(candidates):
    if not candidates:
        return None
    return ("%d open-access link(s) found, but none returned a PDF to a script (publisher sites often "
            "block scripted downloads); open the link in a browser, or try the repository copies below"
            % len(candidates))


def to_record(r):
    notes = "via: %s; version: %s; license: %s; host: %s" % (r["via"] or "-", r["version"] or "-",
                                                            r["license"] or "-", r["host"] or "-")
    if r.get("check"):
        notes += "; check: %s" % r["check"]
    if not r["pdf_url"]:
        notes = "no open-access PDF found (%s); %s" % (", ".join(r["looked_up"]), r["hint"])
    source = (r["via"] or r["looked_up"][-1]).split(":")[0]
    return c.make_record(id="doi:" + r["doi"], source=source if source != "pattern" else "oa-pdf-pattern",
                         type=r["type"], title=r["title"], authors=r["authors"], year=r["year"], date=r["date"],
                         url=c.doi_url(r["doi"]), pdf_url=r["pdf_url"], doi=r["doi"], query="oa_pdf " + r["doi"],
                         notes=notes)


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("doi", nargs="+", help="one or more DOIs (10.x/..., doi:..., or https://doi.org/...)")
    ap.add_argument("--check", action="store_true", help="fetch the first 1 KB of each link to confirm it is a PDF")
    ap.add_argument("--all", action="store_true", help="always ask Unpaywall too and list every candidate link")
    a = ap.parse_args(argv)
    results = [resolve(d, a.check, a.all) for d in a.doi]
    path = c.append_sources(a.out, [to_record(r) for r in results])
    if a.json:
        c.print_json({"results": results})
        return 0
    rows = []
    for r in results:
        rows.append({"doi": r["doi"], "via": r["via"] or "-", "version": r["version"] or "-",
                     "check": r.get("check") or ("-" if not a.check else "no PDF passed"),
                     "pdf": r["pdf_url"] or "none found"})
    c.print_table(rows, [("doi", "doi", 26), ("via", "via", 13), ("version", "version", 16),
                         ("check", "check", 22), ("pdf_url", "pdf", None)])
    for r in results:
        if not r["pdf_url"]:
            print("\n%s: %s" % (r["doi"], r["hint"]))
            for url in r["landing_pages"]:
                print("  landing page: %s" % url)
        if a.all and r["candidates"]:
            print("\n%s: %d candidate links" % (r["doi"], len(r["candidates"])))
            for cand in r["candidates"]:
                print("  [%s, %s] %s%s" % (cand["via"], cand.get("version") or "-", cand["pdf_url"],
                                           "  -> " + cand["check"] if cand.get("check") else ""))
    if path:
        print("\nlogged %d records to %s" % (len(results), path))
    return 0


if __name__ == "__main__":
    c.run(main)
