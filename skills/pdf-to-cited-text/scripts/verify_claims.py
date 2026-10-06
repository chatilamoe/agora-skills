#!/usr/bin/env python3
"""Check claims against the per-page text made by pdf_text.py: is each claim's quote really on the
page it cites? Uses cite_find.py's matching. Prints FOUND / OTHER PAGE / CHECK / NOT FOUND per claim.

Input: a JSON list, or JSON Lines (research/claims.jsonl), of claims such as
  {"claim": "...", "quote": "words copied from the PDF", "source_id": "pdf:wps9560", "page": 7}
The text folder is found from "text" (a folder or id), else from "source_id" (matched against each
pages.json), else from --text. Exit code 0 when every claim is FOUND, 1 otherwise.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402
import cite_find  # noqa: E402

EPILOG = """example:
  python3 verify_claims.py research/claims.jsonl

statuses: FOUND (exact or normalized match on the cited page, or anywhere if no page is given);
OTHER PAGE (found, but not on the cited page); CHECK (only a fuzzy match: the wording differs);
NOT FOUND; NO TEXT (no text folder for this source: run pdf_text.py first).
A claim that is not FOUND should be fixed or dropped, not softened.
"""


def read_claims(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def folder_for(claim, out_dir, default):
    if claim.get("text"):
        return c.text_dir(out_dir, claim["text"])
    sid = claim.get("source_id") or claim.get("source id") or claim.get("source")
    if sid:
        for folder in c.all_text_dirs(out_dir):
            if json.loads((folder / "pages.json").read_text(encoding="utf-8")).get("source_id") == sid:
                return folder
    if default:
        return c.text_dir(out_dir, default)
    raise FileNotFoundError("no text folder for source %r" % sid)


def check(claim, out_dir, default, threshold):
    quote = claim.get("quote") or ""
    page = claim.get("page")
    row = {"claim": claim.get("claim") or quote, "quote": quote, "page": page, "status": "NOT FOUND",
           "found_pages": [], "match": "none", "citation": None}
    try:
        folder = folder_for(claim, out_dir, default)
    except FileNotFoundError as err:
        row.update(status="NO TEXT", note=str(err))
        return row
    if not quote.strip():
        row.update(status="NOT FOUND", note="no quote given")
        return row
    res = cite_find.search(folder, quote, out_dir, threshold, 10)
    pages = sorted({p for h in res["hits"] for p in h["pages"]})
    row.update(text=res["id"], match=res["match"], found_pages=pages)
    if res["match"] in ("exact", "normalized"):
        on_page = page is None or int(page) in pages
        row["status"] = "FOUND" if on_page else "OTHER PAGE"
        best = next((h for h in res["hits"] if page is None or int(page) in h["pages"]), res["hits"][0])
        row["citation"] = best["citation"]
    elif res["match"] == "fuzzy":
        row["status"] = "CHECK"
        row["citation"] = res["hits"][0]["citation"]
        row["note"] = "fuzzy match (score %.2f): the wording differs from the page" % res["hits"][0]["score"]
    return row


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("claims", help="JSON list or JSON Lines file of claims")
    ap.add_argument("--text", help="text folder or id to use when a claim names none")
    ap.add_argument("--threshold", type=float, default=0.8, help="fuzzy tier threshold (0.8)")
    a = ap.parse_args(argv)
    try:
        claims = read_claims(a.claims)
    except (OSError, ValueError) as err:
        print("error: cannot read %s: %s" % (a.claims, err), file=sys.stderr)
        return 1
    rows = [check(cl, a.out, a.text, a.threshold) for cl in claims]
    if a.json:
        c.print_json(rows)
    else:
        for i, r in enumerate(rows, 1):
            where = ", ".join("p. %d" % p for p in r["found_pages"]) or "-"
            cited = "p. %s" % r["page"] if r["page"] is not None else "no page"
            print("%d. %-10s cited %-8s found %-14s %s" % (i, r["status"], cited, where, r["claim"][:90]))
            if r.get("citation"):
                print("   cite: %s" % r["citation"])
            if r.get("note"):
                print("   note: %s" % r["note"])
        ok = sum(r["status"] == "FOUND" for r in rows)
        print("%d of %d claims FOUND on the cited page" % (ok, len(rows)))
    return 0 if all(r["status"] == "FOUND" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
