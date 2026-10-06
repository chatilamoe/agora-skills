#!/usr/bin/env python3
"""Download World Bank PDFs to research/pdfs/<id>.pdf, with a size cap and a polite pause between files.

TARGET is a PDF URL, or the id of a document already logged in research/sources.jsonl by
wds_search.py, wds_get.py or okr_search.py (wds:31476985, okr:10986/43438); its pdf_url is used.

Examples:
  python3 fetch_pdf.py wds:31476985
  python3 fetch_pdf.py okr:10986/42650 wds:18419181 --delay 2
  python3 fetch_pdf.py https://documents.worldbank.org/curated/en/680321468163464611/pdf/WPS6630.pdf --id wds:18419181

No parsing here: turn the PDF into page-numbered text with the pdf-to-cited-text skill.

Writes, under --out (default ./research):
  pdfs/<id>.pdf           the file (wds_31476985.pdf, okr_10986_43438.pdf)
  pdfs/manifest.jsonl     one line per download: id, file, url, final_url, bytes, content_type, accessed
"""
import argparse
import json
import pathlib
import re
import sys
import time

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _common as c  # noqa: E402


class TooBig(Exception):
    pass


def logged_sources(out):
    """id -> record and pdf_url -> id, from sources.jsonl (later lines win)."""
    by_id, by_url = {}, {}
    path = pathlib.Path(out) / "sources.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("id"):
                by_id[rec["id"]] = rec
                if rec.get("pdf_url"):
                    by_url[rec["pdf_url"]] = rec["id"]
    return by_id, by_url


def id_from_url(url):
    m = re.search(r"documents1?\.worldbank\.org/curated/[a-z]{2}/(\d{9,20})/", url)
    if m:
        return f"wbdoc_{m.group(1)}"
    m = re.search(r"/core/bitstreams/([0-9a-f-]{36})/content", url)
    if m:
        return f"okr_bitstream_{m.group(1)}"
    stem = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    stem = re.sub(r"\.pdf$", "", stem, flags=re.I)
    return c.safe_name(stem)[:80] or "document"


def download(url, dest, max_bytes):
    """Stream url to dest; returns (bytes, final_url, content_type). Retries per the shared policy."""
    part = dest.with_name(dest.name + ".part")

    def action():
        with c.open_url(url, accept="application/pdf,*/*;q=0.8") as resp:
            ctype = resp.headers.get("Content-Type", "")
            length = resp.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > max_bytes:
                raise TooBig(int(length))
            n, head = 0, b""
            with part.open("wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    if len(head) < 1024:
                        head += chunk[: 1024 - len(head)]
                    n += len(chunk)
                    if n > max_bytes:
                        raise TooBig(n)
                    fh.write(chunk)
            return n, resp.geturl(), ctype, head

    try:
        n, final_url, ctype, head = c.with_retries(action, url)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    if b"%PDF" not in head:
        part.unlink(missing_ok=True)
        snippet = c.clean(head[:80].decode("latin-1"))
        raise c.FetchError(f"not a PDF (server sent '{ctype}', starting '{snippet}'): {url}")
    part.replace(dest)
    return n, final_url, ctype


def is_pdf(path):
    with path.open("rb") as fh:
        return b"%PDF" in fh.read(1024)


def resolve(target, explicit_id, by_id, by_url):
    """Return (id, url) or raise ValueError with a plain explanation."""
    if re.match(r"^https?://", target, re.I):
        return explicit_id or by_url.get(target) or by_url.get(c.https(target)) or id_from_url(target), target
    rec = by_id.get(target)
    if not rec:
        raise ValueError(f"{target} is not in sources.jsonl; run wds_search.py, wds_get.py or okr_search.py "
                         "first, or pass the PDF URL")
    if not rec.get("pdf_url"):
        hint = " (projects have no PDF; list their documents with wds_search.py --project ID)" \
            if target.startswith("project:") else ""
        raise ValueError(f"no pdf_url logged for {target}{hint}")
    return explicit_id or target, rec["pdf_url"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="PDF URL(s) or logged id(s) such as wds:31476985")
    ap.add_argument("--id", help="id to name the file by (only with a single URL), e.g. wds:18419181")
    ap.add_argument("--max-mb", type=float, default=80, help="refuse files larger than this (default 80 MB)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds to wait between downloads (default 1)")
    ap.add_argument("--force", action="store_true", help="download again even if the file is already there")
    ap.add_argument("--out", default="research", help="output folder (default ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout")
    a = ap.parse_intermixed_args()
    if a.id and len(a.targets) > 1:
        ap.error("--id works with a single target")

    out = pathlib.Path(a.out)
    pdf_dir = out / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    by_id, by_url = logged_sources(out)
    max_bytes = int(a.max_mb * 1_000_000)
    results, fetched = [], 0
    for target in a.targets:
        res = {"target": target, "status": "failed"}
        try:
            doc_id, url = resolve(target, a.id, by_id, by_url)
            dest = pdf_dir / f"{c.safe_name(doc_id)}.pdf"
            res.update(id=doc_id, url=url, file=str(dest))
            if dest.exists() and not a.force and is_pdf(dest):
                res.update(status="already there", bytes=dest.stat().st_size)
            else:
                if fetched:
                    time.sleep(a.delay)
                fetched += 1
                n, final_url, ctype = download(url, dest, max_bytes)
                res.update(status="saved", bytes=n, final_url=final_url, content_type=ctype)
                c.append_jsonl(pdf_dir / "manifest.jsonl", [{
                    "id": doc_id, "file": str(dest), "url": url, "final_url": final_url, "bytes": n,
                    "content_type": ctype, "accessed": c.today()}])
        except TooBig as e:
            res["error"] = f"larger than --max-mb {a.max_mb:g} ({e.args[0] / 1e6:.1f} MB or more); not saved"
        except (ValueError, c.FetchError) as e:
            res["error"] = str(e)
        results.append(res)

    if a.json:
        c.print_json(results)
    else:
        for r in results:
            if r["status"] == "failed":
                print(f"FAILED  {r['target']}: {r['error']}")
            else:
                print(f"{r['status']:<13} {r['file']}  ({r['bytes']:,} bytes)  <- {r['url']}")
    failed = [r for r in results if r["status"] == "failed"]
    if failed:
        print(f"{len(failed)} of {len(results)} failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
