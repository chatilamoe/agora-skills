"""Shared helpers for the imf-data scripts. Imported by them; not run on its own.

Python 3.9+, standard library only.

Every request:
  - goes to the IMF SDMX 2.1 API at https://api.imf.org/external/sdmx/2.1 (no key);
  - sends the agora-skills User-Agent and accepts gzip (the data endpoint compresses);
  - times out after 30 s;
  - on HTTP 429, HTTP 5xx, a connection error or an unreadable body, is tried again
    after 2, 5 and 10 s (first try plus three retries), then fails with a plain message.

Files go under the --out folder (default ./research):
  data/<file>.csv       tidy data written by imf_fetch.py
  data_log.jsonl        one line per data file written
  catalog/<file>.csv    look-up tables written by imf_dataflows.py and imf_dimensions.py
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
import xml.etree.ElementTree as ET
import zlib

BASE = "https://api.imf.org/external/sdmx/2.1"
USER_AGENT = "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
TIMEOUT = 30
BACKOFF = (2, 5, 10)
PAGE_SLEEP = 0.5

# SDMX-ML 2.1 namespaces. Ref, Series, Group and Obs elements carry no namespace in IMF responses.
MES = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"
STR = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
COM = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Names and descriptions come in several languages (the first is often Arabic); never crash on output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass


class FetchError(RuntimeError):
    """A request that still failed after the retries, or failed in a way a retry cannot fix."""


def build_url(base, params=None):
    """base + query string. Values that are None or "" are dropped."""
    items = [(k, str(v)) for k, v in (params or {}).items() if v is not None and str(v) != ""]
    if not items:
        return base
    qs = urllib.parse.urlencode(items, quote_via=urllib.parse.quote, safe=",:")
    return base + ("&" if "?" in base else "?") + qs


def _error_text(err):
    """Short reason from an HTTP error body. The IMF API answers errors with JSON {"message": ...}."""
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


def get_bytes(url, accept=None):
    """GET url with the retry policy. Returns the body as bytes, or None for HTTP 204 (no such object)."""
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    if accept:
        headers["Accept"] = accept
    last = "unknown error"
    for attempt in range(len(BACKOFF) + 1):
        if attempt:
            delay = BACKOFF[attempt - 1]
            print(f"  ({last}; retrying in {delay} s)", file=sys.stderr)
            time.sleep(delay)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                if resp.status == 204:
                    return None
                body = resp.read()
                if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                    body = zlib.decompress(body, 16 + zlib.MAX_WBITS)
                return body
        except urllib.error.HTTPError as e:
            if e.code == 429 or 500 <= e.code <= 599:
                last = f"HTTP {e.code} {_error_text(e)}".strip()
                continue
            raise FetchError(f"HTTP {e.code} for {url}: {_error_text(e) or e.reason}")
        except zlib.error as e:
            last = f"unreadable compressed body ({e})"
            continue
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            last = f"{type(e).__name__}: {getattr(e, 'reason', None) or e}"
            continue
    raise FetchError(f"gave up after {len(BACKOFF) + 1} tries ({last}): {url}")


def get_xml(url):
    """GET url and parse SDMX-ML. Returns the root element, or None for HTTP 204.

    A body that is not XML (a cut-off download) counts as a failed try and is retried."""
    last = None
    for attempt in range(2):
        body = get_bytes(url)
        if body is None:
            return None
        try:
            return ET.fromstring(body)
        except ET.ParseError as e:
            last = e
            time.sleep(BACKOFF[0])
    raise FetchError(f"the response was not readable XML ({last}): {url}")


def local(tag):
    """'{namespace}Series' -> 'Series'."""
    return tag.rsplit("}", 1)[-1]


def en_text(el, child="Name"):
    """English text of a multilingual com:Name or com:Description child; falls back to the first one."""
    if el is None:
        return ""
    found = el.findall(COM + child)
    for f in found:
        if f.get(XML_LANG) == "en":
            return " ".join((f.text or "").split())
    return " ".join((found[0].text or "").split()) if found else ""


# Old dataflow names that no longer exist in the 2025 API, and where their series went.
LEGACY = {
    "IFS": "IFS is no longer one dataflow. Its series moved to topic dataflows: IMF.STA,CPI (prices), "
           "IMF.STA,ER (exchange rates), IMF.STA,IL (reserves), IMF.STA,MFS_MA / MFS_IR / MFS_CBS / MFS_DC "
           "(money, interest rates, central bank), IMF.STA,ANEA / QNEA (national accounts), IMF.STA,BOP. "
           "Series that were in IFS carry the attribute IFS_FLAG=true.",
    "DOT": "Direction of Trade Statistics is now IMF.STA,IMTS (International Trade in Goods by partner country).",
    "DOTS": "Direction of Trade Statistics is now IMF.STA,IMTS (International Trade in Goods by partner country).",
    "GFS": "GFS is split by statement: IMF.STA,GFS_SOO (operations: revenue, expense, balances), GFS_BS, "
           "GFS_COFOG, GFS_SSUC, GFS_SOEF, GFS_SFCP; quarterly data in IMF.STA,QGFS.",
    "FSI": "Financial Soundness Indicators are IMF.STA,FSIC (core and additional), FSIBSIS and FSICDM.",
    "CDIS": "CDIS is now IMF.STA,DIP (Direct Investment Positions by Counterpart Economy).",
    "CPIS": "CPIS is now IMF.STA,PIP (Portfolio Investment Positions by Counterpart Economy).",
}


def legacy_hint(fid):
    return LEGACY.get(str(fid).upper(), "")


def parse_flow(text):
    """'IMF.RES,WEO' or 'IMF.RES,WEO,9.0.0' or 'IMF.RES/WEO' -> (agency, id, version or None).

    A bare id such as 'WEO' returns (None, 'WEO', None); resolve_flow() finds the agency."""
    parts = [p.strip() for p in re.split(r"[,/]", text.strip()) if p.strip()]
    if len(parts) == 1:
        return None, parts[0], None
    if len(parts) in (2, 3):
        return parts[0], parts[1], (parts[2] if len(parts) == 3 else None)
    die(f"cannot read dataflow '{text}': use AGENCY,ID such as IMF.RES,WEO (see imf_dataflows.py)")


def resolve_flow(text):
    """Return (agency, id, version) with the agency filled in for a bare id."""
    agency, fid, version = parse_flow(text)
    if agency:
        return agency, fid, version
    root = get_xml(f"{BASE}/dataflow/all/{urllib.parse.quote(fid)}/latest")
    flows = [] if root is None else list(root.iter(STR + "Dataflow"))
    if not flows:
        die(f"no IMF dataflow with id '{fid}'. {legacy_hint(fid) or 'List them with imf_dataflows.py.'}")
    if len(flows) > 1:
        options = ", ".join(f"{d.get('agencyID')},{d.get('id')}" for d in flows)
        die(f"'{fid}' exists under several agencies ({options}); give AGENCY,ID")
    return flows[0].get("agencyID"), flows[0].get("id"), version


def version_key(v):
    """'9.0.0' -> (9, 0, 0) for sorting; non-numbers sort first."""
    out = []
    for part in str(v or "").split("."):
        out.append(int(part) if part.isdigit() else -1)
    return tuple(out)


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
    """File-name-safe version of a dataflow id or key; long names keep a short checksum."""
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
