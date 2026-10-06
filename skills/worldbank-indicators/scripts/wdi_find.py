#!/usr/bin/env python3
"""Find World Bank indicator codes by keyword (API v2 /indicator: about 29,500 indicators, 70 sources).

Examples:
  python3 wdi_find.py account ownership
  python3 wdi_find.py "gdp per capita" --source 2
  python3 wdi_find.py account women --source 28 --name-only --limit 10
  python3 wdi_find.py --list-sources
  python3 wdi_find.py --list-topics

The first run pages through the whole list once (30 calls of 1,000 rows, under a minute) and caches
it in <out>/cache/wb_indicators.json (about 15 MB); later runs search the cache, which is rebuilt after
30 days or with --refresh. With --source, the source's own complete list is searched instead (one or a
few calls, cached as cache/wb_indicators_source_<id>.json): the whole list files each code under one
source only, so filtering it by source would miss codes. Every word must appear, at the start of a word and in any case, in the
name or in the source note; quote a phrase to keep its words together ("per capita"). Matches in the
name come first, then World Development Indicators (source 2), then shorter names.

Writes, under --out (default ./research):
  cache/wb_indicators.json                  the full indicator list
  cache/wb_indicators_source_<id>.json      one source's list (with --source)
  cache/wb_sources.json                     source ids, codes and names
"""
import argparse
import datetime
import json
import pathlib
import re
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402
from wdi_countries import api_rows  # noqa: E402

API = "https://api.worldbank.org/v2"
PER_PAGE = 1000


def build_cache(path, url, what):
    meta, rows = api_rows(c.get_json(f"{url}&page=1"))
    pages = int(meta.get("pages") or 1)
    print(f"downloading {what}: {meta.get('total')} indicators in {pages} page(s)", file=sys.stderr)
    for page in range(2, pages + 1):
        time.sleep(c.PAGE_SLEEP)
        print(f"  page {page}/{pages}", file=sys.stderr)
        rows.extend(api_rows(c.get_json(f"{url}&page={page}"))[1])
    slim = [{"id": r.get("id", ""), "name": c.clean(r.get("name")), "unit": r.get("unit") or "",
             "source": {"id": str((r.get("source") or {}).get("id", "")),
                        "value": c.clean((r.get("source") or {}).get("value"))},
             "sourceNote": c.clean(r.get("sourceNote")), "sourceOrganization": c.clean(r.get("sourceOrganization")),
             "topics": [c.clean(t.get("value")) for t in (r.get("topics") or []) if isinstance(t, dict) and t.get("value")]}
            for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched": c.today(), "url": url, "total": meta.get("total"), "indicators": slim},
                               ensure_ascii=False), encoding="utf-8")
    print(f"cached {len(slim)} indicators in {path}", file=sys.stderr)
    return slim


def load_indicators(out_dir, refresh=False, max_age_days=30, source=None):
    """The whole list (/indicator), or with source= one source's own complete list (/sources/{id}/indicators).

    The whole list files each code under one source only: 366 Findex codes such as borrow.any.t.d sit
    under Gender Statistics (14) there, so a source filter must use the source's own list.
    """
    if source:
        path = pathlib.Path(out_dir) / "cache" / f"wb_indicators_source_{c.safe_name(source)}.json"
        url, what = f"{API}/sources/{source}/indicators?format=json&per_page={PER_PAGE}", f"source {source}"
    else:
        path = pathlib.Path(out_dir) / "cache" / "wb_indicators.json"
        url, what = f"{API}/indicator?format=json&per_page={PER_PAGE}", "the full indicator list"
    if path.exists() and not refresh:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if (datetime.date.today() - datetime.date.fromisoformat(cached["fetched"])).days <= max_age_days:
                return cached["indicators"]
        except (ValueError, KeyError):
            pass
    inds = build_cache(path, url, what)
    if source:
        for ind in inds:  # report the source that was asked for
            ind["source"]["id"] = str(source)
    return inds


def load_sources(out_dir, max_age_days=30):
    """Source id -> {code, name}, cached in <out>/cache/wb_sources.json (one small call)."""
    path = pathlib.Path(out_dir) / "cache" / "wb_sources.json"
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if (datetime.date.today() - datetime.date.fromisoformat(cached["fetched"])).days <= max_age_days:
                return cached["sources"]
        except (ValueError, KeyError):
            pass
    _, rows = api_rows(c.get_json(f"{API}/sources?format=json&per_page=200"))
    sources = {str(s.get("id")): {"code": s.get("code", ""), "name": c.clean(s.get("name"))} for s in rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched": c.today(), "sources": sources}, ensure_ascii=False), encoding="utf-8")
    return sources


def word_start(term):
    return re.compile(r"(?<![a-z0-9])" + re.escape(term.lower()))


def search(inds, terms, a):
    pats = [word_start(t) for t in terms]
    hits = []
    for ind in inds:
        src = ind["source"]["id"]
        if a.topic and not any(a.topic.lower() in t.lower() for t in ind.get("topics") or []):
            continue
        name = ind["name"].lower()
        in_name = all(p.search(name) for p in pats)
        if not in_name:
            if a.name_only:
                continue
            text = name + " " + ind.get("sourceNote", "").lower()
            if not all(p.search(text) for p in pats):
                continue
        hits.append(((0 if in_name else 1, 0 if src == "2" else 1, len(name), ind["id"]), ind))
    hits.sort(key=lambda h: h[0])
    return [dict(h[1], match="name" if h[0][0] == 0 else "note") for h in hits]


def list_sources(a):
    _, rows = api_rows(c.get_json(f"{API}/sources?format=json&per_page=200"))
    rows = [{"id": s.get("id"), "code": s.get("code"), "name": c.clean(s.get("name")),
             "lastupdated": s.get("lastupdated")} for s in rows]
    if a.json:
        c.print_json(rows)
        return
    print(f"{len(rows)} sources; pass the id to wdi_find.py --source or wdi_fetch.py --source")
    c.print_table(rows, [("id", "id", 3), ("code", "code", 4), ("updated", "lastupdated", 10), ("name", "name", 80)])


def list_topics(a):
    _, rows = api_rows(c.get_json(f"{API}/topic?format=json&per_page=100"))
    rows = [{"id": t.get("id"), "name": c.clean(t.get("value"))} for t in rows]
    if a.json:
        c.print_json(rows)
        return
    print(f"{len(rows)} topics; filter with wdi_find.py --topic NAME")
    c.print_table(rows, [("id", "id", 3), ("name", "name", 60)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keywords", nargs="*", help="words or quoted phrases that must all appear")
    ap.add_argument("--source", help="only these source ids, ';' for several (2 = WDI, 28 = Global Findex)")
    ap.add_argument("--topic", help="only indicators tagged with this topic (part of the name, e.g. 'financial')")
    ap.add_argument("--name-only", action="store_true", help="match the name only, not the source note")
    ap.add_argument("--limit", type=int, default=25, help="rows to show (default 25)")
    ap.add_argument("--refresh", action="store_true", help="download the indicator list again")
    ap.add_argument("--list-sources", action="store_true", help="list the data sources (one call) and stop")
    ap.add_argument("--list-topics", action="store_true", help="list the topics (one call) and stop")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    a = ap.parse_intermixed_args()
    a.source = [s.strip() for s in a.source.split(";")] if a.source else None

    try:
        if a.list_sources:
            return list_sources(a)
        if a.list_topics:
            return list_topics(a)
        if not a.keywords and not a.refresh:
            ap.error("give keywords, --refresh, --list-sources or --list-topics")
        if a.source:
            inds = []
            for i, sid in enumerate(a.source):
                if i:
                    time.sleep(c.PAGE_SLEEP)
                inds.extend(load_indicators(a.out, refresh=a.refresh, source=sid))
        else:
            inds = load_indicators(a.out, refresh=a.refresh)
    except c.FetchError as e:
        c.die(str(e))
    if not a.keywords:
        return

    hits = search(inds, a.keywords, a)
    shown = hits[: max(1, a.limit)]
    if a.json:
        c.print_json({"query": a.keywords, "matches": len(hits), "results": shown})
        return
    label = " ".join(f'"{k}"' if " " in k else k for k in a.keywords)
    print(f"{len(hits)} of {len(inds)} indicators match {label}" + (f"; showing {len(shown)}" if hits else ""))
    if shown:
        try:
            codes = {k: v["code"] for k, v in load_sources(a.out).items()}
        except c.FetchError:
            codes = {}
        for h in shown:
            sid = h["source"]["id"]
            h["src"] = f"{sid} {codes.get(sid) or h['source']['value']}"
        c.print_table(shown, [("code", "id", 24), ("source", "src", 8), ("in", "match", 4), ("name", "name", 100)])
        if any(h["match"] == "note" for h in shown):
            print("in = where the words were found: name, or only the source note (often a weaker match)")
        print("next: wdi_fetch.py CODE --country NPL --mrnev 1   (add --source ID to read the code from that source)")


if __name__ == "__main__":
    main()
