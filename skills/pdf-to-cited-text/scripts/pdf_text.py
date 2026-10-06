#!/usr/bin/env python3
"""Turn a PDF into one text file per page, so that every claim can be cited to a page.

Three routes, tried in this order; the first that works is used (--engine forces one):
  1. pdftotext -layout (poppler), when the binary is installed.
  2. pypdf, when the Python package happens to be installed (it is not required).
  3. The standard-library extractor in _pdf_stdlib.py (zlib + the PDF text operators); always there.

Writes <out>/text/<id>/page-001.txt, page-002.txt, ... and <out>/text/<id>/pages.json, which says
which route ran, the page count, characters per page, empty pages and the linked sources.jsonl id.
Page numbers are PDF page indexes (1 = first page of the file), not the numbers printed on the pages.
"""
import hashlib
import importlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402
import _pdf_stdlib  # noqa: E402
import fetch_pdf  # noqa: E402

ENGINES = ("pdftotext", "pypdf", "stdlib")
EMPTY_CHARS = 20

EPILOG = """examples:
  python3 pdf_text.py research/pdfs/brief-161098.pdf --title "Financial Inclusion, Women, and Building Back Better" --year 2021
  python3 pdf_text.py --url https://documents1.worldbank.org/curated/en/878041614611542135/pdf/Mobile-Internet-Adoption-in-West-Africa.pdf --id wps9560 --title "Mobile Internet Adoption in West Africa" --year 2021
  python3 pdf_text.py research/pdfs/wps9560.pdf --engine stdlib --id wps9560-stdlib

--engine auto (default) | pdftotext | pypdf | stdlib
--layout auto (default) | on | off: how pdftotext lays out text. -layout keeps tables readable but
  puts two prose columns side by side, which breaks sentences; auto uses reading order on those pages.
Link the text to its sources.jsonl record with --source-id, or let the script find the record whose
pdf_url or url equals the download URL; with --title and --year it creates a record if none exists.
"""


_GUTTER = re.compile(r"\S {3,}\S")


def _prose(text):
    return len(text) >= 20 and sum(ch.isalpha() for ch in text) > 0.6 * len(text)


def two_columns(page):
    """True when -layout text shows two prose columns: lines with prose on both sides of a gap near
    the middle, or (when the columns' baselines differ) right-column lines indented past a third of
    the width, make up at least 30% of the long lines."""
    lines = [l.rstrip() for l in page.splitlines() if len(l.strip()) >= 20]
    if len(lines) < 8:
        return False
    width = max(len(l) for l in lines)
    evidence = 0
    for line in lines:
        indent = len(line) - len(line.lstrip())
        if indent > 0.35 * width and _prose(line.strip()):
            evidence += 1
            continue
        for m in _GUTTER.finditer(line):
            left, right = line[:m.start() + 1].strip(), line[m.end() - 1:].strip()
            if 0.25 * width < m.start() < 0.75 * width and _prose(left) and _prose(right):
                evidence += 1
                break
    return evidence >= 0.3 * len(lines)


def _pdftotext(exe, path, layout):
    args = [exe] + (["-layout"] if layout else []) + ["-enc", "UTF-8", str(path), "-"]
    proc = subprocess.run(args, capture_output=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError("exit %d: %s" % (proc.returncode, proc.stderr.decode("utf-8", "replace").strip()[:200]))
    pages = proc.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]  # pdftotext ends every page, including the last, with a form feed
    return pages


def run_pdftotext(path, layout="auto"):
    """layout: 'on' = -layout everywhere; 'off' = reading order everywhere; 'auto' = -layout, except
    pages where two prose columns sit side by side, which get pdftotext's reading-order text."""
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("not installed")
    version = (subprocess.run([exe, "-v"], capture_output=True, text=True).stderr.splitlines() or ["pdftotext"])[0]
    if layout == "off":
        pages = _pdftotext(exe, path, False)
        return pages, "%s, reading order" % version.strip(), {"modes": ["reading order"] * len(pages)}
    pages = _pdftotext(exe, path, True)
    modes = ["layout"] * len(pages)
    if layout == "auto":
        flagged = [i for i, page in enumerate(pages) if two_columns(page)]
        if flagged:
            reading = _pdftotext(exe, path, False)
            if len(reading) == len(pages):
                for i in flagged:
                    pages[i] = reading[i]
                    modes[i] = "reading order (two columns)"
    detail = "%s, -layout" % version.strip()
    switched = sum(1 for m in modes if m != "layout")
    if switched:
        detail += "; reading order on %d two-column page(s)" % switched
    return pages, detail, {"modes": modes}


def run_pypdf(path):
    try:
        pypdf = importlib.import_module("pypdf")
    except ImportError:
        raise RuntimeError("not installed")
    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt("")
    pages, errors = [], []
    for i, page in enumerate(reader.pages, 1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as err:  # keep going; report the page
            pages.append("")
            errors.append("page %d: %s" % (i, err))
    return pages, "pypdf %s" % getattr(pypdf, "__version__", "?"), {"errors": errors}


def run_stdlib(data):
    pages, report = _pdf_stdlib.extract(data)
    return pages, "standard library (zlib + Tj/TJ operators)", report


def extract(path, data, engine="auto", layout="auto"):
    """Return (pages, engine name, detail, report, attempts)."""
    order = ENGINES if engine == "auto" else (engine,)
    attempts = []
    for name in order:
        try:
            if name == "pdftotext":
                pages, detail, report = run_pdftotext(path, layout)
            elif name == "pypdf":
                pages, detail, report = run_pypdf(path)
            else:
                pages, detail, report = run_stdlib(data)
        except Exception as err:  # try the next route
            attempts.append({"engine": name, "ok": False, "why": str(err)[:200]})
            continue
        if not pages:
            attempts.append({"engine": name, "ok": False, "why": "no pages returned"})
            continue
        attempts.append({"engine": name, "ok": True})
        return pages, name, detail, report, attempts
    raise RuntimeError("no route could read this PDF: " + "; ".join("%s: %s" % (a["engine"], a["why"]) for a in attempts))


def link_source(out_dir, source_id, url, title, year, file_id, page_count):
    """Find (or, with title and year, create) the sources.jsonl record for this PDF."""
    rec = c.find_source(out_dir, source_id, url)
    if rec:
        return rec, False
    if title:
        rec = c.make_record(id=source_id or "pdf:" + file_id, source="pdf-to-cited-text", type="document",
                            title=title, year=year, date=str(year) if year else None, url=url, pdf_url=url,
                            query=None, pages=page_count, notes="record created by pdf_text.py")
        c.append_sources(out_dir, [rec])
        return rec, True
    return None, False


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("pdf", nargs="?", help="path to a PDF (or use --url)")
    ap.add_argument("--url", help="download the PDF first (saved to <out>/pdfs/<id>.pdf); with a local PDF path, "
                                  "only record this URL as where the PDF came from")
    ap.add_argument("--id", help="folder name under <out>/text/ (default: from the file name or --source-id)")
    ap.add_argument("--source-id", help="sources.jsonl id of this document, e.g. wds:34285961")
    ap.add_argument("--engine", choices=("auto",) + ENGINES, default="auto")
    ap.add_argument("--layout", choices=("auto", "on", "off"), default="auto",
                    help="pdftotext: auto = -layout except two-column pages (default); on = -layout "
                         "everywhere; off = reading order everywhere")
    ap.add_argument("--title", help="title for a new sources.jsonl record (when none exists)")
    ap.add_argument("--year", type=int, help="year for a new sources.jsonl record")
    a = ap.parse_args(argv)
    if not a.pdf and not a.url:
        ap.error("give a PDF path or --url")

    sidecar = {}
    try:
        if a.url and not a.pdf:
            sidecar = fetch_pdf.download(a.url, a.out, a.id, a.source_id)
            path = Path(sidecar["file"])
        else:
            path = Path(a.pdf)
            side = Path(str(path) + ".json")
            if side.exists():
                sidecar = json.loads(side.read_text(encoding="utf-8"))
    except c.FetchError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1
    if not path.exists():
        print("error: no such file: %s" % path, file=sys.stderr)
        return 1
    data = path.read_bytes()
    if data.lstrip()[:4] != b"%PDF" and data.find(b"%PDF", 0, 1024) < 0:
        print("error: %s is not a PDF" % path, file=sys.stderr)
        return 1
    source_id = a.source_id or sidecar.get("source_id")
    file_id = a.id or sidecar.get("id") or (c.slug(source_id) if source_id else c.slug(path.name))
    pdf_url = a.url or sidecar.get("url")

    try:
        pages, engine, detail, report, attempts = extract(path, data, a.engine, a.layout)
    except RuntimeError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1

    folder = Path(a.out) / "text" / file_id
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("page-*.txt"):
        old.unlink()
    width = max(3, len(str(len(pages))))
    index_pages, empty = [], []
    for n, text in enumerate(pages, 1):
        name = "page-%0*d.txt" % (width, n)
        (folder / name).write_text(text, encoding="utf-8")
        chars = len(text.strip())
        if chars < EMPTY_CHARS:
            empty.append(n)
        entry = {"page": n, "file": name, "chars": chars, "words": len(text.split())}
        if report.get("modes") and report["modes"][n - 1] != "layout":
            entry["mode"] = report["modes"][n - 1]
        index_pages.append(entry)

    rec, created = link_source(a.out, source_id, pdf_url, a.title, a.year, file_id, len(pages))
    notes = []
    if empty:
        notes.append("%d of %d pages have no text layer (scanned images, blank or figure-only pages). "
                     "No OCR here: nothing on those pages can be cited from this text." % (len(empty), len(pages)))
    for err in report.get("errors") or []:
        notes.append("extraction error on " + err)
    if report.get("unmapped_glyphs"):
        notes.append("%d glyphs had no Unicode mapping and were dropped (fonts: %s)"
                     % (report["unmapped_glyphs"], ", ".join(report.get("fonts_without_tounicode") or [])))
    if not rec:
        notes.append("no sources.jsonl record linked: cite_find.py will give the page but not the title, year and "
                     "URL; re-run with --source-id, or with --title and --year")
    index = {
        "id": file_id, "source_id": rec["id"] if rec else source_id, "title": rec.get("title") if rec else None,
        "pdf": str(path.resolve()), "pdf_url": pdf_url, "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data), "engine": engine, "engine_detail": detail, "attempts": attempts,
        "page_count": len(pages), "empty_pages": empty, "likely_scanned": len(empty) > len(pages) / 2,
        "extracted": c.today(), "page_numbering": c.PAGE_NOTE, "notes": notes, "pages": index_pages,
    }
    if engine == "stdlib":
        index["stdlib_report"] = {k: v for k, v in report.items() if k != "errors"}
    (folder / "pages.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.json:
        c.print_json(index)
        return 0
    tried = ", ".join("%s (%s)" % (t["engine"], "used" if t["ok"] else t["why"]) for t in attempts)
    print("engine: %s [%s]" % (engine, detail))
    if len(attempts) > 1:
        print("tried: %s" % tried)
    print("pages: %d written to %s/ (%s ... %s)" % (len(pages), folder, index_pages[0]["file"], index_pages[-1]["file"]))
    print("characters: %d in total; empty pages: %s" % (sum(p["chars"] for p in index_pages),
                                                        ", ".join(map(str, empty)) if empty else "none"))
    if rec:
        print("source: %s (%s, %s)%s" % (rec["id"], c.short_title(rec.get("title")), rec.get("year") or "n.d.",
                                         " [new record added to sources.jsonl]" if created else ""))
    for note in notes:
        print("note: " + note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
