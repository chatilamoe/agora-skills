"""Shared helpers for the un-statistics scripts. Python 3.9+, standard library only.

Not a script: the *_fetch.py files next to it import it. Keep it in the same folder.

What lives here:
- fetch(): HTTP GET with the agora-skills User-Agent, a 30 s timeout, gzip, and
  retries with backoff (2, 5, 10 s) on HTTP 429, HTTP 5xx and network errors.
- write_csv(), log_data(): files under --out (default ./research) and the
  research/data_log.jsonl record every data script appends.
- Country codes: ISO3 / ISO2 / M49 lookups from references/country_codes.csv.
- Small output helpers: a readable table, or JSON with --json.
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

USER_AGENT = ("agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; "
              "mailto:decaihub@worldbank.org)")
SOURCE = "un-statistics"          # the "source" field of every data_log.jsonl record
TIMEOUT = 30                      # seconds per request
BACKOFF = (2, 5, 10)              # seconds to wait before each retry
PAGE_SLEEP = 0.5                  # seconds between paged calls
SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
COUNTRY_FILE = SKILL_DIR / "references" / "country_codes.csv"


class FetchError(Exception):
    """An HTTP or network failure, with a plain-language message."""

    def __init__(self, message, status=None, body="", url=""):
        super().__init__(message)
        self.status = status
        self.body = body
        self.url = url


# --------------------------------------------------------------------------- HTTP

def build_url(base, params=None):
    """Append query parameters. params is a dict or a list of (key, value) pairs.
    None and "" values are skipped; list values become repeated keys (?a=1&a=2)."""
    if not params:
        return base
    items = params.items() if isinstance(params, dict) else params
    pairs = []
    for key, value in items:
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple)):
            pairs.extend((key, str(v)) for v in value if v is not None and v != "")
        else:
            pairs.append((key, str(value)))
    if not pairs:
        return base
    query = urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote, safe="~,")
    return base + ("&" if "?" in base else "?") + query


def _decompress(body, encoding):
    if body[:2] == b"\x1f\x8b" or (encoding or "").lower() == "gzip":
        try:
            return zlib.decompress(body, 16 + zlib.MAX_WBITS)
        except zlib.error:
            return body
    if (encoding or "").lower() == "deflate":
        try:
            return zlib.decompress(body)
        except zlib.error:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def _host(url):
    return urllib.parse.urlsplit(url).netloc or url


def snippet(text, n=300):
    """First n characters of a response body, on one line."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()[:n]


def fetch(url, accept=None, headers=None, timeout=TIMEOUT):
    """GET url and return (body_bytes, headers).

    Retries up to three times, waiting 2, 5 and 10 s (longer if the server sends
    Retry-After), on HTTP 429, HTTP 5xx and network errors. Other HTTP errors
    (400, 401, 403, 404, 406, ...) raise FetchError at once: they do not go away.
    """
    hdrs = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    if accept:
        hdrs["Accept"] = accept
    if headers:
        hdrs.update(headers)
    last = None
    for attempt in range(len(BACKOFF) + 1):
        wait = BACKOFF[attempt] if attempt < len(BACKOFF) else 0
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = _decompress(resp.read(), resp.headers.get("Content-Encoding"))
                return body, resp.headers
        except urllib.error.HTTPError as err:
            raw = b""
            try:
                raw = err.read() or b""
            except Exception:  # noqa: BLE001 - the body is only used for the message
                pass
            enc = err.headers.get("Content-Encoding") if err.headers else None
            text = _decompress(raw, enc).decode("utf-8", "replace")
            msg = "HTTP %s from %s: %s" % (err.code, _host(url), snippet(text) or err.reason)
            if err.code == 429 or err.code >= 500:
                last = FetchError(msg, err.code, text, url)
                retry_after = (err.headers.get("Retry-After") or "") if err.headers else ""
                if retry_after.isdigit():
                    wait = max(wait, min(int(retry_after), 60))
            else:
                raise FetchError(msg, err.code, text, url)
        except (urllib.error.URLError, http.client.HTTPException, OSError) as err:
            reason = getattr(err, "reason", None) or err
            last = FetchError("network error contacting %s: %s" % (_host(url), reason), None, "", url)
        if attempt < len(BACKOFF):
            time.sleep(wait)
    raise last


def fetch_json(url, accept="application/json", headers=None):
    body, _ = fetch(url, accept=accept, headers=headers)
    try:
        return json.loads(body.decode("utf-8-sig"))  # utf-8-sig: the SDG API sends a BOM
    except ValueError:
        raise FetchError("%s did not return JSON: %s" % (_host(url), snippet(body.decode("utf-8", "replace"))),
                         None, body.decode("utf-8", "replace"), url)


def fetch_text(url, accept=None, headers=None):
    body, _ = fetch(url, accept=accept, headers=headers)
    return body.decode("utf-8-sig", "replace")


# --------------------------------------------------------------------------- files and log

def today():
    return datetime.date.today().isoformat()


def safe_name(text, limit=120):
    """A file-system-safe name: letters, digits, dot, dash, underscore."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-.") or "data"
    if len(name) > limit:
        name = name[:limit - 9] + "-" + format(zlib.crc32(text.encode("utf-8")), "08x")
    return name


def write_csv(rows, columns, out_dir, stem):
    """Write rows (list of dicts) to <out_dir>/data/<stem>.csv; return the path as a string."""
    path = pathlib.Path(out_dir) / "data" / (safe_name(stem) + ".csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in columns})
    return str(path)


def log_data(out_dir, dataset, indicator, entity, period, url, rows, file):
    """Append one record to <out_dir>/data_log.jsonl (the format in CONVENTIONS.md)."""
    record = {"source": SOURCE, "dataset": dataset, "indicator": indicator, "entity": entity,
              "period": period, "url": url, "accessed": today(), "rows": rows, "file": file}
    path = pathlib.Path(out_dir) / "data_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def period_of(values, fallback=""):
    """'first:last' of the time values actually returned (ISO-style periods sort as text)."""
    vals = sorted({str(v) for v in values if v not in (None, "")})
    if not vals:
        return fallback
    return vals[0] if len(vals) == 1 else "%s:%s" % (vals[0], vals[-1])


def period_tag(start=None, end=None, last=None):
    """Short file-name tag for the requested period: 2015-2024, from2015, to2020, last5."""
    if start and end:
        return "%s-%s" % (start, end)
    if start:
        return "from%s" % start
    if end:
        return "to%s" % end
    if last:
        return "last%s" % last
    return ""


def joined(values):
    """Distinct values in first-seen order, comma-joined (for the log's entity field)."""
    seen = []
    for v in values:
        if v not in (None, "") and v not in seen:
            seen.append(v)
    return ",".join(str(v) for v in seen)


# --------------------------------------------------------------------------- arguments

def add_common_args(parser):
    parser.add_argument("--out", default="research",
                        help="folder for data files and data_log.jsonl (default: ./research)")
    parser.add_argument("--json", action="store_true", help="print JSON to stdout instead of a table")


def split_values(values):
    """Flatten repeated and comma-separated arguments: ['NPL,IND', 'BGD'] -> ['NPL', 'IND', 'BGD']."""
    out = []
    for v in values or []:
        out.extend(p.strip() for p in str(v).split(",") if p.strip())
    return out


def matches(text, words):
    """True when every word of `words` appears in `text`, ignoring case."""
    t = (text or "").casefold()
    return all(w in t for w in str(words or "").casefold().split())


def year_or_none(text, name):
    if text in (None, ""):
        return None
    try:
        return int(str(text)[:4])
    except ValueError:
        die("%s must be a year such as 2015, not %r" % (name, text))


# --------------------------------------------------------------------------- countries

_COUNTRIES = None


def countries():
    """Rows of references/country_codes.csv: iso3, iso2, m49, name, region, ..."""
    global _COUNTRIES
    if _COUNTRIES is None:
        with open(COUNTRY_FILE, newline="", encoding="utf-8") as fh:
            _COUNTRIES = list(csv.DictReader(fh))
    return _COUNTRIES


def lookup_country(token):
    """Find a country by ISO3, ISO2, M49 (with or without leading zeros) or exact name."""
    t = str(token).strip()
    if not t:
        return None
    up = t.upper()
    for row in countries():
        if up == row["iso3"] or up == row["iso2"]:
            return row
    if t.isdigit():
        for row in countries():
            if int(t) == int(row["m49"]):
                return row
    low = t.casefold()
    for row in countries():
        if low == row["name"].casefold():
            return row
    return None


def to_iso3(token):
    row = lookup_country(token)
    return row["iso3"] if row else str(token).strip()


def to_iso2(token):
    row = lookup_country(token)
    return row["iso2"] if row else str(token).strip()


def to_m49(token):
    """M49 without leading zeros (the SDG API style: Afghanistan is 4, not 004)."""
    row = lookup_country(token)
    if row:
        return str(int(row["m49"]))
    t = str(token).strip()
    return str(int(t)) if t.isdigit() else t


def iso3_from_m49(code):
    t = str(code).strip()
    if t.isdigit():
        for row in countries():
            if int(t) == int(row["m49"]):
                return row["iso3"]
    return ""


# --------------------------------------------------------------------------- output

def die(message, code=1):
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(code)


def print_table(rows, columns, limit=20, width=38, more="all rows are in the CSV file"):
    """Print up to `limit` rows as an aligned plain-text table."""
    if not rows:
        print("(no rows)")
        return
    shown = rows[:limit]

    def cell(value):
        text = "" if value is None else str(value)
        text = re.sub(r"\s+", " ", text)
        return text if len(text) <= width else text[:width - 1] + "~"

    widths = {c: max(len(c), *(len(cell(r.get(c))) for r in shown)) for c in columns}
    print("  ".join(c.ljust(widths[c]) for c in columns))
    print("  ".join("-" * widths[c] for c in columns))
    for r in shown:
        print("  ".join(cell(r.get(c)).ljust(widths[c]) for c in columns))
    if len(rows) > limit:
        print("... %d more rows (%s)" % (len(rows) - limit, more))


def print_json(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")


def report(args, rows, columns, table_columns, log, extra=None):
    """Standard ending for a data script: JSON with --json, otherwise a table and a summary."""
    if args.json:
        payload = {"log": log, "columns": columns, "data": rows}
        if extra:
            payload.update(extra)
        print_json(payload)
        return
    print_table(rows, table_columns)
    print()
    print("Logged to %s" % (pathlib.Path(args.out) / "data_log.jsonl"))
    if not log.get("file"):
        print("No rows matched; nothing written and nothing to cite. Say what was searched and not found.")
        return
    print("Wrote %d rows to %s" % (log["rows"], log["file"]))
    print("Cite as: (%s, %s, %s, %s, retrieved %s, %s)" % (
        log["dataset"], log["indicator"], log["entity"] or "-", log["period"] or "-",
        log["accessed"], log["url"]))


def run(main):
    """Call main(); turn FetchError and Ctrl-C into a plain message and exit code 1."""
    try:
        main()
    except FetchError as err:
        die(str(err))
    except KeyboardInterrupt:
        die("interrupted")
