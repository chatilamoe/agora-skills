"""Shared helpers for the academic-literature scripts. Imported by them; not run on its own.

- http_get / get_json: the project User-Agent, a 30 s timeout, and up to three retries
  (waiting 2, 5, 10 s) on HTTP 429, 5xx and connection errors. If a server asks for a
  longer wait (Retry-After), it stops and says so instead of hammering the API.
- make_record / append_sources: the one-line-per-item record in research/sources.jsonl.
- norm_doi / norm_title / clean_text: normalisation used for de-duplication.
- print_table: the short readable table every script prints without --json.

Python 3.9+, standard library only.
"""
import argparse
import datetime
import email.utils
import gzip
import html
import http.client
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
MAILTO = "decaihub@worldbank.org"
TIMEOUT = 30
BACKOFF = (2, 5, 10)
MAX_SERVER_WAIT = 60  # seconds; a longer Retry-After ends the retries with a message
RECORD_KEYS = ("id", "source", "type", "title", "authors", "year", "date", "url", "pdf_url",
               "doi", "query", "accessed", "pages", "notes")


class FetchError(Exception):
    """A request failed after the retries, or failed in a way that retrying cannot fix."""


def _wait_hint(headers):
    """Seconds the server asks us to wait: Retry-After, or CORE's X-RateLimit-Retry-After."""
    if headers is None:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    value = (headers.get("Retry-After") or "").strip()
    if value:
        if value.isdigit():
            return float(value)
        try:
            return max(0.0, (email.utils.parsedate_to_datetime(value) - now).total_seconds())
        except (TypeError, ValueError):
            pass
    value = (headers.get("X-RateLimit-Retry-After") or "").strip()
    if value:
        try:
            when = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
            return max(0.0, (when - now).total_seconds())
        except ValueError:
            pass
    return None


def _snippet(err):
    try:
        body = err.read()[:300].decode("utf-8", "replace")
    except Exception:  # the error body is optional
        body = ""
    return re.sub(r"\s+", " ", body).strip()[:200]


def http_get(url, params=None, headers=None, timeout=TIMEOUT, retries=BACKOFF, max_bytes=None):
    """GET url (with params) and return (body bytes, response headers, final URL).

    max_bytes reads only the first bytes of the body (used to check that a link is a PDF).
    Raises FetchError with a plain message when the request cannot succeed.
    """
    if params:
        query = urllib.parse.urlencode([(k, v) for k, v in params.items() if v is not None], doseq=True)
        url = url + ("&" if "?" in url else "?") + query
    host = urllib.parse.urlsplit(url).netloc
    req_headers = {"User-Agent": USER_AGENT}
    if max_bytes is None:
        req_headers["Accept-Encoding"] = "gzip"
    req_headers.update(headers or {})
    problem = "no attempt made"
    for attempt in range(len(retries) + 1):
        wait = retries[attempt] if attempt < len(retries) else None
        try:
            request = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                body = resp.read() if max_bytes is None else resp.read(max_bytes)
                if max_bytes is None and (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                    body = gzip.decompress(body)
                return body, resp.headers, resp.geturl()
        except urllib.error.HTTPError as err:
            if err.code == 429 or 500 <= err.code < 600:
                hint = _wait_hint(err.headers)
                if hint is not None and hint > MAX_SERVER_WAIT:
                    raise FetchError("%s answered HTTP %d and asks to wait %d s before the next request; "
                                     "try again later" % (host, err.code, hint))
                problem = "HTTP %d" % err.code
                if wait is not None and hint is not None:
                    wait = max(wait, int(hint) + 1)
            else:
                raise FetchError("%s answered HTTP %d for %s %s" % (host, err.code, url, _snippet(err)))
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError,
                socket.timeout, TimeoutError) as err:
            problem = "connection error (%s)" % (getattr(err, "reason", None) or err)
        if wait is None:
            break
        print("  %s: %s; retrying in %d s" % (host, problem, wait), file=sys.stderr)
        time.sleep(wait)
    raise FetchError("%s: %s after %d attempts (%s)" % (host, problem, len(retries) + 1, url))


def get_json(url, params=None, headers=None, with_headers=False, **kwargs):
    """GET and parse JSON. Returns the data, or (data, headers) when with_headers is True."""
    hdrs = {"Accept": "application/json"}
    hdrs.update(headers or {})
    body, resp_headers, final_url = http_get(url, params, hdrs, **kwargs)
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        raise FetchError("%s did not return JSON: %r" % (urllib.parse.urlsplit(final_url).netloc, body[:120]))
    return (data, resp_headers) if with_headers else data


class Pacer:
    """Keeps at least `interval` seconds between calls to the same API within one run."""

    def __init__(self, interval):
        self.interval = interval
        self.last = 0.0

    def wait(self):
        gap = time.monotonic() - self.last
        if self.last and gap < self.interval:
            time.sleep(self.interval - gap)
        self.last = time.monotonic()


# ---------------------------------------------------------------- records and files

def today():
    return datetime.date.today().isoformat()


def make_record(**fields):
    """One sources.jsonl line, with exactly the keys in CONVENTIONS.md."""
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
    """Append records to <out_dir>/sources.jsonl; return the path (or None if nothing to write)."""
    if not records:
        return None
    path = Path(out_dir) / "sources.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------- text helpers

_TAG = re.compile(r"<[^<>]{1,200}>")


def clean_text(value):
    """Strip markup (JATS, HTML), unescape entities, collapse whitespace."""
    if not value:
        return ""
    value = html.unescape(_TAG.sub(" ", str(value)))
    return re.sub(r"\s+", " ", value).strip()


def norm_doi(value):
    """'https://doi.org/10.1596/X' or 'doi:10.1596/X' -> '10.1596/x' (DOIs are case-insensitive)."""
    if not value:
        return None
    value = str(value).strip()
    value = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.lower() or None


def doi_url(doi):
    return "https://doi.org/" + doi if doi else None


# DOI prefixes of the main development-economics publishers (checked with api.crossref.org/prefixes).
PREFIXES = {
    "worldbank": "10.1596", "imf": "10.5089", "nber": "10.3386", "3ie": "10.23846", "oecd": "10.1787",
    "idb": "10.18235", "adb": "10.22617", "unu-wider": "10.35188", "ifpri": "10.2499", "ilo": "10.54394",
    "un": "10.18356", "ssrn": "10.2139",
}


def series_from_doi(doi):
    """Name the working-paper series when the DOI pattern gives it away, else None."""
    doi = norm_doi(doi) or ""
    match = re.match(r"10\.1596/1813-9450-(\d+)$", doi)
    if match:
        return "World Bank Policy Research Working Paper %s" % match.group(1)
    match = re.match(r"10\.3386/w(\d+)$", doi)
    if match:
        return "NBER Working Paper %s" % match.group(1)
    return None


def norm_title(title):
    """Lower-case ASCII letters and digits only, single spaces: used to match the same work across APIs."""
    text = unicodedata.normalize("NFKD", title or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def looks_like_pdf(url):
    if not url:
        return False
    path = urllib.parse.urlsplit(url).path.lower()
    return path.endswith(".pdf") or "/pdf" in path


def year_of(value):
    match = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", str(value or ""))
    return int(match.group(1)) if match else None


_PARTICLES = {"de", "da", "del", "della", "der", "den", "di", "du", "dos", "das", "van", "von", "le", "la",
              "al", "el", "bin", "ter", "ten", "zu"}


def surname(name):
    """'Suresh de Mel' -> 'de Mel'; 'Natile, Serena' -> 'Natile'."""
    name = (name or "").strip()
    if "," in name:
        return name.split(",")[0].strip()
    parts = name.split()
    if not parts:
        return ""
    i = len(parts) - 1
    while i > 0 and parts[i - 1].lower() in _PARTICLES:
        i -= 1
    return " ".join(parts[i:])


def author_label(authors):
    """'Suri', 'Jack and Suri', 'Jack et al.'"""
    names = [a for a in (authors or []) if a]
    if not names:
        return ""
    if len(names) == 1:
        return surname(names[0])
    if len(names) == 2:
        return "%s and %s" % (surname(names[0]), surname(names[1]))
    return "%s et al." % surname(names[0])


def academic_citation(item):
    """(Author(s), Year, Title, journal or series, DOI or URL), as in CONVENTIONS.md."""
    link = doi_url(item.get("doi")) or item.get("url") or ""
    parts = [author_label(item.get("authors")) or "Anon.", str(item.get("year") or "n.d."),
             item.get("title") or "Untitled"]
    if item.get("venue"):
        parts.append(item["venue"])
    parts.append(link)
    return "(" + ", ".join(parts) + ")"


# ---------------------------------------------------------------- output

def print_table(rows, columns, file=None):
    """rows: list of dicts; columns: list of (header, key, width); width None = no truncation."""
    out = file or sys.stdout
    widths = [w for _, _, w in columns]
    head = []
    for (title, _, width) in columns:
        head.append(title if width is None else title.ljust(width)[:width])
    print("  ".join(head).rstrip(), file=out)
    print("  ".join("-" * (w or 10) for w in widths), file=out)
    for row in rows:
        cells = []
        for (_, key, width) in columns:
            value = row.get(key)
            value = "" if value is None else re.sub(r"\s+", " ", str(value))
            if width is not None:
                value = value if len(value) <= width else value[: max(1, width - 3)] + "..."
                value = value.ljust(width)
            cells.append(value)
        print("  ".join(cells).rstrip(), file=out)


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def parser(description, epilog):
    """argparse parser with the shared --out and --json options."""
    ap = argparse.ArgumentParser(description=description, epilog=epilog,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="research", metavar="DIR",
                    help="folder for sources.jsonl and other files (default: ./research)")
    ap.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")
    return ap


def run(main):
    """Run main(); turn FetchError into a plain message and exit code 1."""
    try:
        code = main()
    except FetchError as err:
        print("error: %s" % err, file=sys.stderr)
        code = 1
    except KeyboardInterrupt:
        code = 130
    sys.exit(code or 0)
