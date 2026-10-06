"""Shared helpers for the dbnomics-macro scripts. Imported by them; not run on its own.

Python 3.9+, standard library only.

Every request:
  - goes to the DBnomics Web API v22 at https://api.db.nomics.world/v22 (JSON, no key);
  - sends the agora-skills User-Agent;
  - times out after 30 s;
  - on HTTP 429, HTTP 5xx, a connection error or an unreadable body, is tried again
    after 2, 5 and 10 s (first try plus three retries), then fails with a plain message.
Paged calls sleep 0.5 s between pages.

Files go under the --out folder (default ./research):
  data/<file>.csv       tidy data written by dbn_series.py
  data_log.jsonl        one line per data file written
  catalog/<file>.csv    look-up tables written by dbn_search.py and dbn_dataset.py
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
import zlib

BASE = "https://api.db.nomics.world/v22"
WEB = "https://db.nomics.world"
USER_AGENT = "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
TIMEOUT = 30
BACKOFF = (2, 5, 10)
PAGE_SLEEP = 0.5

# Series names use en dashes and accented country names; never crash on a terminal that cannot show them.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass


class FetchError(RuntimeError):
    """A request that still failed after the retries, or failed in a way a retry cannot fix."""


def quote_path(text, safe="+:@.-_~"):
    """Percent-encode one path segment (dataset codes contain ':' and '@'; masks contain '+')."""
    return urllib.parse.quote(str(text), safe=safe)


def build_url(base, params=None):
    """base + query string. Values that are None or "" are dropped; True/False become 1/0."""
    items = []
    for k, v in (params or {}).items():
        if v is None or v == "":
            continue
        if v is True or v is False:
            v = int(v)
        items.append((k, str(v)))
    if not items:
        return base
    qs = urllib.parse.urlencode(items, quote_via=urllib.parse.quote, safe=",:@/")
    return base + ("&" if "?" in base else "?") + qs


def _error_text(err):
    """DBnomics answers errors with JSON {"message": ...}."""
    try:
        raw = err.read()
        if (err.headers.get("Content-Encoding") or "").lower() == "gzip":
            raw = zlib.decompress(raw, 16 + zlib.MAX_WBITS)
        text = raw.decode("utf-8", "replace")
    except Exception:
        return ""
    try:
        msg = json.loads(text).get("message")
        if msg:
            return str(msg)
    except (ValueError, AttributeError):
        pass
    return " ".join(text.split())[:200]


def get_json(url):
    """GET url with the retry policy and parse the JSON body."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Encoding": "gzip"}
    last = "unknown error"
    for attempt in range(len(BACKOFF) + 1):
        if attempt:
            delay = BACKOFF[attempt - 1]
            print(f"  ({last}; retrying in {delay} s)", file=sys.stderr)
            time.sleep(delay)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=TIMEOUT) as resp:
                body = resp.read()
                if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                    body = zlib.decompress(body, 16 + zlib.MAX_WBITS)
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or 500 <= e.code <= 599:
                last = f"HTTP {e.code} {_error_text(e)}".strip()
                continue
            raise FetchError(f"HTTP {e.code}: {_error_text(e) or e.reason} ({url})")
        except (ValueError, zlib.error) as e:  # cut-off or garbled body
            last = f"unreadable response ({e})"
            continue
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            last = f"{type(e).__name__}: {getattr(e, 'reason', None) or e}"
            continue
    raise FetchError(f"gave up after {len(BACKOFF) + 1} tries ({last}): {url}")


def split_dataset(text):
    """'IMF/WEO:2025-04' -> ('IMF', 'WEO:2025-04')."""
    parts = text.strip().strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        die(f"'{text}' is not PROVIDER/DATASET, e.g. IMF/WEO:2025-04 (find codes with dbn_search.py)")
    return parts[0], parts[1]


def split_series_id(text):
    """'IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change' -> ('IMF', 'WEO:2025-04', 'NPL.NGDP_RPCH.pcent_change')."""
    parts = text.strip().split("/", 2)
    if len(parts) != 3 or not all(parts):
        die(f"'{text}' is not PROVIDER/DATASET/SERIES, e.g. IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change")
    return parts[0], parts[1], parts[2]


def labels(mapping):
    """dimensions_values_labels comes as {code: label} or as [[code, label], ...]; return a dict."""
    if isinstance(mapping, dict):
        return {str(k): v for k, v in mapping.items()}
    out = {}
    for item in mapping or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out[str(item[0])] = item[1]
    return out


# Dimension names that hold the country or area, most specific first.
ENTITY_DIMS = ("ref_area", "country", "weo-country", "geo", "location", "reporter", "economy",
               "jurisdiction", "area", "region")


def entity_of(dimensions):
    """Country or area code of a series from its dimensions dict, or ''."""
    lowered = {str(k).lower(): v for k, v in (dimensions or {}).items()}
    for name in ENTITY_DIMS:
        if name in lowered:
            return str(lowered[name])
    for k, v in lowered.items():
        if "country" in k or "area" in k or "geo" in k:
            return str(v)
    return ""


def period_bound(value, end=False):
    """YYYY, YYYY-MM, YYYY-Qn or YYYY-MM-DD -> first (or last) day as YYYY-MM-DD, for filtering."""
    if not value:
        return None
    v = str(value).strip()
    m = re.fullmatch(r"(\d{4})", v)
    if m:
        return f"{v}-12-31" if end else f"{v}-01-01"
    m = re.fullmatch(r"(\d{4})-?[Qq]([1-4])", v)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        return f"{y}-{q * 3:02d}-31" if end else f"{y}-{q * 3 - 2:02d}-01"
    m = re.fullmatch(r"(\d{4})-(\d{2})", v)
    if m:
        return f"{v}-31" if end else f"{v}-01"
    m = re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)
    if m:
        return v
    die(f"cannot read period '{value}': use YYYY, YYYY-MM, YYYY-Qn or YYYY-MM-DD")


def script_path(name):
    """How to call a sibling script, written the way this one was called (e.g. skills/x/scripts/name.py)."""
    parent = pathlib.Path(sys.argv[0]).parent
    return name if str(parent) in ("", ".") else (parent / name).as_posix()


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def say(msg, json_mode=False):
    """Status lines: stdout normally, stderr when stdout carries JSON."""
    print(msg, file=sys.stderr if json_mode else sys.stdout)


def today():
    return datetime.date.today().isoformat()


def safe_name(text, maxlen=90):
    """File-name-safe version of a code; long names keep a short checksum."""
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text)).strip("-") or "all"
    if len(s) > maxlen:
        s = s[: maxlen - 9] + "-" + format(zlib.crc32(s.encode()) & 0xFFFFFFFF, "08x")
    return s


def joined(values, limit=25):
    """Distinct values in first-seen order, joined with ';'. Long lists become a count."""
    seen = []
    for v in values:
        if v not in seen:
            seen.append(v)
    if len(seen) > limit:
        return f"{len(seen)} values (see file)"
    return ";".join(str(v) for v in seen)


def write_csv(path, rows, columns):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def append_jsonl(path, records):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def log_data(out_dir, record):
    """Append one record to <out>/data_log.jsonl."""
    return append_jsonl(pathlib.Path(out_dir) / "data_log.jsonl", [record])


def print_table(rows, cols, out=None):
    """cols: list of (header, key, width); width None = no truncation (capped at 110)."""
    out = out or sys.stdout

    def cell(v, w):
        s = " ".join(str("" if v is None else v).split())
        w = w or 110
        return s if len(s) <= w else s[: w - 1] + "~"

    print("  ".join(h.ljust(w or 0) for h, _, w in cols).rstrip(), file=out)
    for r in rows:
        print("  ".join(cell(r.get(k), w).ljust(w or 0) for _, k, w in cols).rstrip(), file=out)


def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def run(main):
    """Run main(); turn FetchError into a plain message and exit code 1."""
    try:
        code = main()
    except FetchError as e:
        print(f"error: {e}", file=sys.stderr)
        code = 1
    except KeyboardInterrupt:
        code = 130
    sys.exit(code or 0)
