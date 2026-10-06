"""Shared helpers for the pdf-to-cited-text scripts. Imported by them; not run on its own.

HTTP download with the project User-Agent, 30 s timeout and retries (2, 5, 10 s); the sources.jsonl
record and look-ups in it; locating text folders made by pdf_text.py; small output helpers.
Python 3.9+, standard library only.
"""
import argparse
import datetime
import http.client
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
TIMEOUT = 30
BACKOFF = (2, 5, 10)
RECORD_KEYS = ("id", "source", "type", "title", "authors", "year", "date", "url", "pdf_url",
               "doi", "query", "accessed", "pages", "notes")
PAGE_NOTE = ("Page numbers are PDF page indexes (1 = the first page of the file), "
             "not the numbers printed on the pages.")


class FetchError(Exception):
    """A download failed after the retries, or cannot succeed."""


def today():
    return datetime.date.today().isoformat()


def http_get(url, headers=None, timeout=TIMEOUT, retries=BACKOFF):
    """GET url; return (body bytes, response headers, final URL). Retries 429, 5xx, connection errors."""
    host = urllib.parse.urlsplit(url).netloc
    req_headers = {"User-Agent": USER_AGENT}
    req_headers.update(headers or {})
    problem = "no attempt made"
    for attempt in range(len(retries) + 1):
        wait = retries[attempt] if attempt < len(retries) else None
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=req_headers), timeout=timeout) as resp:
                return resp.read(), resp.headers, resp.geturl()
        except urllib.error.HTTPError as err:
            if err.code == 429 or 500 <= err.code < 600:
                problem = "HTTP %d" % err.code
            else:
                raise FetchError("%s answered HTTP %d for %s" % (host, err.code, url))
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError,
                socket.timeout, TimeoutError) as err:
            problem = "connection error (%s)" % (getattr(err, "reason", None) or err)
        if wait is None:
            break
        print("  %s: %s; retrying in %d s" % (host, problem, wait), file=sys.stderr)
        time.sleep(wait)
    raise FetchError("%s: %s after %d attempts (%s)" % (host, problem, len(retries) + 1, url))


def slug(text, limit=60):
    """'Mobile-Internet-Adoption-in-West-Africa.pdf' -> 'mobile-internet-adoption-in-west-africa'."""
    text = re.sub(r"\.pdf$", "", str(text or ""), flags=re.I)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (text[:limit].rstrip("-")) or "document"


def make_record(**fields):
    rec = dict.fromkeys(RECORD_KEYS)
    for key, value in fields.items():
        if key not in rec:
            raise KeyError("not a sources.jsonl field: %s" % key)
        rec[key] = value
    rec["authors"] = rec["authors"] or []
    rec["notes"] = rec["notes"] or ""
    rec["accessed"] = rec["accessed"] or today()
    return rec


def append_sources(out_dir, records):
    if not records:
        return None
    path = Path(out_dir) / "sources.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def load_sources(out_dir):
    """All records in <out_dir>/sources.jsonl; later lines win when an id repeats."""
    path = Path(out_dir) / "sources.jsonl"
    records = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("id"):
                records[rec["id"]] = rec
    return records


def find_source(out_dir, source_id=None, url=None):
    """The sources.jsonl record with this id, or whose pdf_url or url equals url."""
    records = load_sources(out_dir)
    if source_id and source_id in records:
        return records[source_id]
    if url:
        want = _canon(url)
        for rec in reversed(list(records.values())):
            if want in (_canon(rec.get("pdf_url")), _canon(rec.get("url"))):
                return rec
    return None


def _canon(url):
    if not url:
        return None
    parts = urllib.parse.urlsplit(url.strip())
    return (parts.netloc.lower().replace("documents1.", "documents.") + parts.path).rstrip("/")


def text_dir(out_dir, ref):
    """A text folder from a path, or from an id under <out_dir>/text/."""
    path = Path(ref)
    if (path / "pages.json").exists():
        return path
    candidate = Path(out_dir) / "text" / ref
    if (candidate / "pages.json").exists():
        return candidate
    known = sorted(p.parent.name for p in (Path(out_dir) / "text").glob("*/pages.json"))
    raise FileNotFoundError("no text folder %r (looked in %s and %s). Known ids: %s"
                            % (ref, path, candidate, ", ".join(known) or "none; run pdf_text.py first"))


def all_text_dirs(out_dir):
    return sorted(p.parent for p in (Path(out_dir) / "text").glob("*/pages.json"))


def short_title(title, words=10):
    """Up to the first colon, at most `words` words."""
    title = re.sub(r"\s+", " ", title or "").strip()
    head = re.split(r"\s*[:–—]\s+|\s+-\s+", title, maxsplit=1)[0] or title
    parts = head.split()
    return " ".join(parts[:words]) + ("..." if len(parts) > words else "")


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def parser(description, epilog):
    ap = argparse.ArgumentParser(description=description, epilog=epilog,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="research", metavar="DIR",
                    help="research folder holding text/, pdfs/ and sources.jsonl (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of readable text")
    return ap
