"""Shared helpers for the scripts in this folder. Python 3.9+, standard library only.

Every request:
  - sends the agora-skills User-Agent;
  - times out after 30 s;
  - on HTTP 429, HTTP 5xx, a connection error or a garbled body, is tried again
    after 2, 5 and 10 s (first try plus three retries), then fails with a plain message.

Logs are append-only JSON Lines files under the --out folder (default ./research):
  sources.jsonl   one line per document, report or project returned
  data_log.jsonl  one line per data file written
"""
import csv
import datetime
import http.client
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
MAILTO = "decaihub@worldbank.org"
TIMEOUT = 30
BACKOFF = (2, 5, 10)
PAGE_SLEEP = 0.5

# Titles and abstracts contain non-ASCII text; never crash on a terminal that cannot show it.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass


class FetchError(RuntimeError):
    """A request that still failed after the retries, or failed in a way a retry cannot fix."""


def build_url(base, params=None):
    """base + query string. Values that are None or "" are dropped; spaces become %20."""
    if not params:
        return base
    items = [(k, str(v)) for k, v in params.items() if v is not None and str(v) != ""]
    if not items:
        return base
    qs = urllib.parse.urlencode(items, quote_via=urllib.parse.quote, safe=",:")
    return base + ("&" if "?" in base else "?") + qs


def _retry_after(err):
    try:
        value = int(err.headers.get("Retry-After", "0"))
    except (TypeError, ValueError, AttributeError):
        return 0
    return max(0, min(value, 60))


def with_retries(action, url):
    """Run action() under the retry policy. action does the request and any reading/parsing."""
    last = "unknown error"
    wait_extra = 0
    for attempt in range(len(BACKOFF) + 1):
        if attempt:
            delay = max(BACKOFF[attempt - 1], wait_extra)
            print(f"  ({last}; retrying in {delay} s)", file=sys.stderr)
            time.sleep(delay)
            wait_extra = 0
        try:
            return action()
        except urllib.error.HTTPError as e:
            if e.code == 429 or 500 <= e.code <= 599:
                last = f"HTTP {e.code}"
                wait_extra = _retry_after(e)
                continue
            body = ""
            try:
                body = " ".join(e.read(300).decode("utf-8", "replace").split())
            except Exception:
                pass
            raise FetchError(f"HTTP {e.code} {e.reason} for {url}" + (f" - {body}" if body else "")) from None
        except ValueError as e:  # garbled or truncated JSON
            last = f"unreadable response ({e})"
            continue
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            reason = getattr(e, "reason", None) or e
            last = f"{type(e).__name__}: {reason}"
            continue
    raise FetchError(f"gave up after {len(BACKOFF) + 1} tries ({last}): {url}")


def open_url(url, accept="application/json", headers=None, timeout=TIMEOUT):
    """Open url and return the response object (the caller reads and closes it). No retries here."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": accept}
    if headers:
        hdrs.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=timeout)


def get_bytes(url, accept="*/*", headers=None):
    """GET url with retries; returns the body as bytes."""
    def action():
        with open_url(url, accept=accept, headers=headers) as resp:
            return resp.read()
    return with_retries(action, url)


def get_json(url, headers=None):
    """GET url with retries; returns parsed JSON."""
    def action():
        with open_url(url, accept="application/json", headers=headers) as resp:
            return json.loads(resp.read().decode("utf-8"))
    return with_retries(action, url)


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def say(msg, json_mode=False):
    """Status lines: stdout normally, stderr when stdout carries JSON."""
    print(msg, file=sys.stderr if json_mode else sys.stdout)


def today():
    return datetime.date.today().isoformat()


def plural(n, word):
    """plural(1, 'row') -> '1 row'; plural(1060, 'row') -> '1,060 rows'."""
    return f"{n:,} {word}" + ("" if n == 1 else "s")


def clean(text):
    """Collapse runs of whitespace (abstracts arrive with newlines and indentation)."""
    if text is None:
        return ""
    return " ".join(str(text).split())


def slug(text, maxlen=70):
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return (s[:maxlen].rstrip("_")) or "all"


def safe_name(text):
    """File-name-safe version of an id such as wds:31476985 or okr:10986/42650."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text)).strip("_") or "file"


def iso_date(value):
    """'2019-10-14T04:00:00Z' -> '2019-10-14'; '2006-12' stays; junk such as '1-01-01' -> None."""
    if not value:
        return None
    m = re.match(r"^(\d{4})(-\d{2})?(-\d{2})?", str(value).strip())
    if not m:
        return None
    year = int(m.group(1))
    if year < 1800 or year > 2100:
        return None
    return "".join(g for g in m.groups() if g)


def year_of(date_str):
    d = iso_date(date_str)
    return int(d[:4]) if d else None


def date_bound(value, end=False):
    """Turn YYYY, YYYY-MM or YYYY-MM-DD into a full date; end=True gives the last day of the period."""
    if value is None:
        return None
    v = str(value).strip()
    try:
        if re.fullmatch(r"\d{4}", v):
            return f"{v}-12-31" if end else f"{v}-01-01"
        if re.fullmatch(r"\d{4}-\d{2}", v):
            y, m = int(v[:4]), int(v[5:7])
            if not end:
                return f"{v}-01"
            nxt = datetime.date(y + (m == 12), m % 12 + 1, 1)
            return (nxt - datetime.timedelta(days=1)).isoformat()
        return datetime.date.fromisoformat(v).isoformat()
    except ValueError:
        pass
    die(f"bad date '{value}': use YYYY, YYYY-MM or YYYY-MM-DD")


def https(url):
    """Upgrade http:// links on World Bank document hosts to https:// (both work; https is what to cite)."""
    if not url:
        return url
    return re.sub(r"^http://((documents1?|openknowledge|www)\.worldbank\.org)/", r"https://\1/", url)


def append_jsonl(path, records):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def source_record(id, source, type, title, authors=None, year=None, date=None, url=None,
                  pdf_url=None, doi=None, query="", pages=None, notes=""):
    """One line of research/sources.jsonl, in the field order CONVENTIONS.md shows."""
    return {
        "id": id, "source": source, "type": type, "title": title, "authors": authors or [],
        "year": year, "date": date, "url": url, "pdf_url": pdf_url, "doi": doi, "query": query,
        "accessed": today(), "pages": pages, "notes": notes,
    }


def log_sources(out_dir, records):
    return append_jsonl(pathlib.Path(out_dir) / "sources.jsonl", records)


def log_data(out_dir, record):
    return append_jsonl(pathlib.Path(out_dir) / "data_log.jsonl", [record])


def write_csv(path, rows, columns):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("; ".join(map(str, v)) if isinstance(v, (list, tuple)) else v) for k, v in r.items()})
    return path


def print_table(rows, cols, out=None):
    """cols: (header, key, width); width None = no truncation (capped at 110)."""
    out = out or sys.stdout

    def cell(v, w):
        if isinstance(v, (list, tuple)):
            v = "; ".join(map(str, v))
        s = clean("" if v is None else v)
        w = w or 110
        return s if len(s) <= w else s[: w - 1] + "~"

    print("  ".join(h.ljust(w or 0) for h, _, w in cols).rstrip(), file=out)
    for r in rows:
        print("  ".join(cell(r.get(k), w).ljust(w or 0) for _, k, w in cols).rstrip(), file=out)


def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
