#!/usr/bin/env python3
"""Search World Bank projects and operations (search.worldbank.org/api/v3/projects).

Examples:
  python3 projects_search.py --country NP --status Active
  python3 projects_search.py "financial inclusion" --country NP --rows 5
  python3 projects_search.py --country "NP;BD" --from 2015 --to 2016 --sort oldest
  python3 projects_search.py --sector "Banking Institutions" --region "South Asia"
  python3 projects_search.py --id P508961

Country codes are ISO 2-letter codes (NP, not NPL; the script upper-cases them); see wdi_countries.py in the
worldbank-indicators skill for the list. Only lending operations are here: advisory (ASA) product ids
that appear in Documents & Reports, such as P161744, are not.

For a project's documents (appraisal document, ISRs, completion report):
  python3 wds_search.py --project P508961 --sort newest

Writes, under --out (default ./research):
  sources.jsonl              one line per project (appended)
  projects_<query>.csv       the result table (overwritten when the same search is run again)
"""
import argparse
import pathlib
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402

API = "https://search.worldbank.org/api/v3/projects"
PROJECT_PAGE = "https://projects.worldbank.org/en/projects-operations/project-detail/{}"
FIELDS = ("id,project_name,countryshortname,countrycode,regionname,status,boardapprovaldate,closingdate,"
          "totalamt,curr_total_commitment,curr_ida_commitment,curr_ibrd_commitment,idacommamt,grantamt,"
          "lendprojectcost,major_sectors,themev2_level1_exact,projectfinancialtype,pdo,project_abstract,"
          "borrower,impagency,fiscalyear,last_stage_reached_name,teamleadname")
SORTS = {"newest": "desc", "oldest": "asc"}
CSV_COLUMNS = ["id", "name", "country", "region", "status", "approval_date", "closing_date", "fiscal_year",
               "commitment_usd", "current_commitment_usd", "ida_usd", "ibrd_usd", "grant_usd",
               "project_cost_usd", "financing", "major_sectors", "sectors", "themes", "pdo", "borrower",
               "implementing_agency", "url"]


def amount(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def unique(seq):
    seen, out = set(), []
    for x in seq or []:
        x = c.clean(x)
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def normalize(p):
    majors, sectors = [], []
    for ms in p.get("major_sectors") or []:
        m = (ms or {}).get("major_sector") or {}
        if m.get("major_sector_name"):
            majors.append(m["major_sector_name"])
        for s in m.get("sectors") or []:
            if s.get("sector_name"):
                pct = s.get("sector_percent")
                sectors.append(f"{s['sector_name']} ({float(pct):g}%)" if pct else s["sector_name"])
    pid = p.get("id") or ""
    approval = c.iso_date(p.get("boardapprovaldate"))
    return {
        "id": pid,
        "name": c.clean(p.get("project_name")),
        "country": p.get("countryshortname") or "",
        "country_code": "; ".join(p.get("countrycode") or []) if isinstance(p.get("countrycode"), list)
        else (p.get("countrycode") or ""),
        "region": p.get("regionname") or "",
        "status": p.get("status") or "",
        "stage": p.get("last_stage_reached_name") or "",
        "approval_date": approval,
        "closing_date": c.iso_date(p.get("closingdate")),
        "fiscal_year": p.get("fiscalyear") or "",
        "commitment_usd": amount(p.get("totalamt")),
        "current_commitment_usd": amount(p.get("curr_total_commitment")),
        "ida_usd": amount(p.get("curr_ida_commitment") or p.get("idacommamt")),
        "ibrd_usd": amount(p.get("curr_ibrd_commitment")),
        "grant_usd": amount(p.get("grantamt")),
        "project_cost_usd": amount(p.get("lendprojectcost")),
        "financing": unique(p.get("projectfinancialtype")),
        "major_sectors": unique(majors),
        "sectors": unique(sectors),
        "themes": unique(p.get("themev2_level1_exact")),
        "pdo": c.clean(p.get("pdo")),
        "abstract": c.clean(p.get("project_abstract")),
        "borrower": c.clean(p.get("borrower")),
        "implementing_agency": c.clean(p.get("impagency")),
        "team_lead": "; ".join(unique(p.get("teamleadname"))) if isinstance(p.get("teamleadname"), list)
        else c.clean(p.get("teamleadname")),
        "url": PROJECT_PAGE.format(pid),
        "documents": f"wds_search.py --project {pid}",
    }


def headline_usd(pr):
    """totalamt is missing for many trust-funded grants; fall back to the current commitment, then the grant."""
    return pr["commitment_usd"] or pr["current_commitment_usd"] or pr["grant_usd"] or None


def to_source(pr, label):
    usd = headline_usd(pr)
    money = f"US${usd / 1e6:,.1f}m" if usd else "amount not given"
    notes = (f"{pr['country']}; {pr['status']}; approved {pr['approval_date'] or 'n/a'}; {money}; "
             f"documents: {pr['documents']}")
    return c.source_record(
        id=f"project:{pr['id']}", source="worldbank-documents", type="project", title=pr["name"],
        authors=["World Bank"], year=int(pr["approval_date"][:4]) if pr["approval_date"] else None,
        date=pr["approval_date"], url=pr["url"], pdf_url=None, doi=None, query=label, notes=notes)


def filter_params(a):
    p = {}
    join = lambda s: "^".join(x.strip() for x in s.split(";") if x.strip())  # noqa: E731
    if a.id:
        p["id"] = a.id.strip().upper()
    if a.query:
        p["qterm"] = a.query
    if a.country:
        p["countrycode_exact"] = join(a.country.upper())  # the API only matches capitals
    if a.country_name:
        p["countryshortname_exact"] = join(a.country_name)
    if a.status:
        p["status_exact"] = join(a.status.title())  # Active, Closed, Pipeline, Dropped
    if a.region:
        p["regionname_exact"] = join(a.region)
    if a.sector:
        p["sector_exact"] = join(a.sector)
    if a.theme:
        p["themev2_level1_exact"] = join(a.theme)
    if a.date_from or a.date_to:
        p["strdate"] = c.date_bound(a.date_from or "1900")
        p["enddate"] = c.date_bound(a.date_to or str(int(c.today()[:4]) + 2), end=True)
    return p


def query_label(a, p):
    names = {"id": "id", "countrycode_exact": "country", "countryshortname_exact": "country_name",
             "status_exact": "status", "regionname_exact": "region", "sector_exact": "sector",
             "themev2_level1_exact": "theme", "strdate": "approved_from", "enddate": "approved_to"}
    parts = [a.query] if a.query else []
    parts += [f"{names[k]}={p[k]}" for k in names if k in p]
    return " | ".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="search words (optional)")
    ap.add_argument("--id", help="one project id, e.g. P508961")
    ap.add_argument("--country", help="ISO 2-letter code(s), ';' for several: NP or 'NP;BD'")
    ap.add_argument("--country-name", help="country short name as the API spells it, e.g. 'Viet Nam'")
    ap.add_argument("--status", help="Active, Closed, Pipeline or Dropped")
    ap.add_argument("--region", help='e.g. "South Asia", "Eastern and Southern Africa"')
    ap.add_argument("--sector", help='sector name, e.g. "Banking Institutions"')
    ap.add_argument("--theme", help='top-level theme, e.g. "Finance", "Gender"')
    ap.add_argument("--from", dest="date_from", help="board approval from: YYYY, YYYY-MM or YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", help="board approval to")
    ap.add_argument("--sort", choices=sorted(SORTS), default="newest", help="by board approval date (default newest)")
    ap.add_argument("--rows", type=int, default=20, help="results per page, 1-100 (default 20)")
    ap.add_argument("--pages", type=int, default=1, help="pages to fetch (default 1)")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_intermixed_args()
    a.query = " ".join(a.query).strip()

    p = filter_params(a)
    if not p:
        ap.error("give search words, --id or at least one filter")
    rows = max(1, min(a.rows, 100))
    params = dict(p, format="json", fl=FIELDS, rows=rows, srt="boardapprovaldate", order=SORTS[a.sort])

    results, total, first_url = [], 0, None
    try:
        for page in range(max(1, a.pages)):
            url = c.build_url(API, dict(params, os=page * rows))
            first_url = first_url or url
            if page:
                time.sleep(c.PAGE_SLEEP)
            data = c.get_json(url)
            total = int(data.get("total") or 0)  # sent as a string by this API
            batch = [normalize(v) for v in (data.get("projects") or {}).values()
                     if isinstance(v, dict) and v.get("id")]
            results.extend(batch)
            if not batch or (page + 1) * rows >= total:
                break
    except c.FetchError as e:
        c.die(str(e))

    label = query_label(a, p)
    out = pathlib.Path(a.out)
    csv_path = None
    if results:
        c.log_sources(out, [to_source(r, label) for r in results])
        csv_path = c.write_csv(out / f"projects_{c.slug(label)}.csv", results, CSV_COLUMNS)

    if a.json:
        c.print_json({"api": "projects", "query": label, "url": first_url, "total": total,
                      "returned": len(results), "results": results})
    else:
        print(f'{c.plural(total, "project")} match{"es" if total == 1 else ""} "{label}"; '
              f'showing {len(results)}, sorted by approval date ({a.sort})')
        for r in results:
            r["usd_m"] = f"{headline_usd(r) / 1e6:,.1f}" if headline_usd(r) else ""
        if results:
            c.print_table(results, [("id", "id", 7), ("approved", "approval_date", 10), ("status", "status", 8),
                                    ("US$ m", "usd_m", 8), ("country", "country", 12), ("name", "name", 70)])
    if results:
        c.say(f"wrote {csv_path} ({c.plural(len(results), 'row')}); appended {c.plural(len(results), 'line')} "
              f"to {out / 'sources.jsonl'}", a.json)
        c.say("next: wds_search.py --project ID lists a project's documents", a.json)
    else:
        c.say("no projects found; nothing written. Country codes are ISO 2-letter (NP, not NPL).", a.json)


if __name__ == "__main__":
    main()
