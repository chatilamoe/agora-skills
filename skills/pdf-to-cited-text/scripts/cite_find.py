#!/usr/bin/env python3
"""Find a quote or key phrase in the per-page text made by pdf_text.py; print the page number(s),
the surrounding sentence, and a ready citation (Short title, Year, p. N, URL) when sources.jsonl has
the record.

Matching, in order; the first tier that finds something wins:
  1. exact     the quote appears character for character on a page;
  2. normalized  case, whitespace, line breaks, hyphenation, dashes, quote marks, accents and
                 punctuation ignored (also across a page break, and "..." splits a quote into parts);
  3. fuzzy     share of the quote's words found in the best window of the page >= --threshold.
A fuzzy hit means the wording differs: read the page and quote the text as printed before citing.
"""
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

DASHES = set("-­‐‑‒–—―−﹘﹣－")
ELLIPSIS = re.compile(r"\s*(?:\.\s*\.\s*\.|…)\s*")
ABBREV = {"e.g", "i.e", "al", "etc", "fig", "figs", "no", "nos", "dr", "mr", "mrs", "ms", "vs", "cf", "vol", "pp",
          "p", "eds", "ed", "inc", "ltd", "co", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
          "oct", "nov", "dec", "u.s", "u.k", "st", "approx", "est", "op", "cit", "ibid", "sec", "ch", "eq"}
SENT_END = re.compile(r"[.!?][\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9])|\n[ \t]*\n")

EPILOG = """examples:
  python3 cite_find.py brief-161098 "Financial inclusion occurs when adults have access to appropriate"
  python3 cite_find.py wps9560 "WAEMU countries" --max 3
  python3 cite_find.py --all "Guatemala" --max 2

The first argument is a text folder (research/text/<id>) or just its id. --all searches every folder.
Exit code 0 when something matched (any tier), 1 when nothing did.
The page is the PDF page index (1 = first page of the file), not the number printed on the page.
"""


# ---------------------------------------------------------------- normalisation

def normalize(text):
    """Return (normalised string, map from each normalised character to its index in text)."""
    chars, idx = [], []
    glue = False
    for i, ch in enumerate(text):
        if ch in DASHES:  # drop dashes and the spaces around them: eco-\nnomic = economic, low-income = lowincome
            if chars and chars[-1] == " ":
                chars.pop()
                idx.pop()
            glue = True
            continue
        if ch.isalnum():
            if ch.isascii():
                chars.append(ch.lower())
                idx.append(i)
            else:
                for part in unicodedata.normalize("NFKD", ch).lower():
                    if part.isalnum():
                        chars.append(part)
                        idx.append(i)
            glue = False
            continue
        if glue:
            continue
        if chars and chars[-1] != " ":
            chars.append(" ")
            idx.append(i)
    if chars and chars[-1] == " ":
        chars.pop()
        idx.pop()
    return "".join(chars), idx


# ---------------------------------------------------------------- loading

def load(folder):
    folder = Path(folder)
    index = json.loads((folder / "pages.json").read_text(encoding="utf-8"))
    pages = []
    for p in index.get("pages") or []:
        path = folder / p["file"]
        pages.append((p["page"], path.read_text(encoding="utf-8") if path.exists() else ""))
    return index, pages


class Doc:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.index, self.pages = load(folder)
        self._norm = {}

    def norm(self, k):
        if k not in self._norm:
            self._norm[k] = normalize(self.pages[k][1])
        return self._norm[k]


# ---------------------------------------------------------------- sentences

def _is_abbrev(text, dot):
    m = re.search(r"([A-Za-z.]+)$", text[max(0, dot - 12):dot])
    word = (m.group(1).lower().strip(".") if m else "")
    return word in ABBREV or (len(word) == 1 and word.isalpha())


def sentence_around(text, start, end, limit=480):
    """The sentence(s) containing text[start:end], whitespace-collapsed, at most `limit` characters."""
    left = 0
    for m in SENT_END.finditer(text, max(0, start - 2000), start):
        if text[m.start()] == "\n" or not _is_abbrev(text, m.start()):
            left = m.end()
    right = len(text)
    for m in SENT_END.finditer(text, end):
        if text[m.start()] == "\n":
            right = m.start()
            break
        if not _is_abbrev(text, m.start()):
            right = m.start() + 1
            break
    piece = re.sub(r"(\w)[-­]\s*\n\s*([a-z])", r"\1\2", text[left:right])
    piece = re.sub(r"\s+", " ", piece).strip()
    if len(piece) > limit:
        quote = re.sub(r"\s+", " ", text[start:end]).strip()
        at = max(0, piece.find(quote[:40]))
        lo = max(0, at - (limit - len(quote)) // 2)
        piece = ("..." if lo else "") + piece[lo:lo + limit] + ("..." if lo + limit < len(piece) else "")
    return piece


# ---------------------------------------------------------------- matching

def _hit(doc, k, start, end, match, score=1.0, pages=None):
    pageno, text = doc.pages[k]
    return {"page": pageno, "pages": pages or [pageno], "match": match, "score": round(score, 3),
            "sentence": sentence_around(text, start, end),
            "matched_text": re.sub(r"\s+", " ", text[start:end]).strip()[:300]}


def _spread(found, max_hits):
    """found: [(k, nth occurrence on that page, start, end)] -> first occurrence on each page first,
    then later ones; at most max_hits; returned in page order."""
    found.sort(key=lambda f: (f[1], f[0]))
    return sorted(found[:max_hits], key=lambda f: (f[0], f[2]))


def _exact(doc, quote, max_hits):
    found = []
    for k, (_pageno, text) in enumerate(doc.pages):
        pos, nth = text.find(quote), 0
        while pos >= 0:
            found.append((k, nth, pos, pos + len(quote)))
            pos, nth = text.find(quote, pos + 1), nth + 1
    return [_hit(doc, k, s, e, "exact") for k, _n, s, e in _spread(found, max_hits)]


def _normalized_spans(doc, nq, max_hits=10):
    """[(page k, norm start, norm end)]: on-page occurrences (first on each page first), then
    occurrences across a page break as (k, -1, offset)."""
    found = []
    for k in range(len(doc.pages)):
        norm, _ = doc.norm(k)
        pos, nth = norm.find(nq), 0
        while pos >= 0:
            found.append((k, nth, pos, pos + len(nq)))
            pos, nth = norm.find(nq, pos + 1), nth + 1
    spans = [(k, s, e) for k, _n, s, e in _spread(found, max_hits)]
    for k in range(len(doc.pages) - 1):  # quotes that run over a page break
        a, _ = doc.norm(k)
        b, _ = doc.norm(k + 1)
        tail, head = a[-(len(nq) + 5):], b[:len(nq) + 5]
        joined = tail + " " + head
        pos = joined.find(nq)
        if pos >= 0 and pos < len(tail) < pos + len(nq):
            spans.append((k, -1, len(a) - len(tail) + pos))
    return spans


def _normalized(doc, quote, max_hits):
    parts = [p for p in ELLIPSIS.split(quote) if p.strip()]
    if len(parts) > 1:
        return _segments(doc, parts, max_hits)
    nq, _ = normalize(quote)
    if len(nq) < 3:
        return []
    hits = []
    for k, start, end in _normalized_spans(doc, nq, max_hits):
        if len(hits) >= max_hits:
            break
        if start == -1:  # across the break between page k and k+1
            norm_a, map_a = doc.norm(k)
            o_start = map_a[end] if end < len(map_a) else len(doc.pages[k][1])
            h = _hit(doc, k, o_start, len(doc.pages[k][1]), "normalized",
                     pages=[doc.pages[k][0], doc.pages[k + 1][0]])
            h["sentence"] = (h["sentence"] + " [continues on the next page] " +
                             sentence_around(doc.pages[k + 1][1], 0, 1))[:600]
            hits.append(h)
            continue
        norm, mp = doc.norm(k)
        hits.append(_hit(doc, k, mp[start], mp[end - 1] + 1, "normalized"))
    return hits


def _segments(doc, parts, max_hits):
    """A quote with '...': every part must appear, in order, on the same page."""
    norm_parts = [normalize(p)[0] for p in parts]
    norm_parts = [p for p in norm_parts if len(p) >= 3]
    hits = []
    for k in range(len(doc.pages)):
        norm, mp = doc.norm(k)
        pos, first, last = 0, None, None
        for p in norm_parts:
            found = norm.find(p, pos)
            if found < 0:
                break
            first = found if first is None else first
            last = found + len(p)
            pos = last
        else:
            if first is not None:
                hits.append(_hit(doc, k, mp[first], mp[last - 1] + 1, "normalized"))
                hits[-1]["note"] = "quote has an ellipsis: all %d parts found in order" % len(norm_parts)
        if len(hits) >= max_hits:
            break
    return hits


def _fuzzy(doc, quote, threshold, max_hits):
    words = normalize(" ".join(ELLIPSIS.split(quote)))[0].split()
    n = len(words)
    if n < 4:
        return []
    want = collections.Counter(words)
    results = []
    for k in range(len(doc.pages)):
        norm, mp = doc.norm(k)
        toks = [(m.group(), m.start(), m.end()) for m in re.finditer(r"\S+", norm)]
        if not toks:
            continue
        best = (0, 0, 0)
        for size in sorted({n, n + max(1, n // 5)}):
            size = min(size, len(toks))
            have, overlap = collections.Counter(), 0
            for i, (t, _, _) in enumerate(toks):
                if have[t] < want.get(t, 0):
                    overlap += 1
                have[t] += 1
                if i >= size:
                    old = toks[i - size][0]
                    if have[old] <= want.get(old, 0):
                        overlap -= 1
                    have[old] -= 1
                if i >= size - 1 and overlap > best[0]:
                    best = (overlap, i - size + 1, i)
        score = best[0] / n
        if score >= threshold:
            first, last = toks[best[1]], toks[best[2]]
            results.append((score, k, mp[first[1]], mp[last[2] - 1] + 1))
    results.sort(key=lambda r: (-r[0], r[1]))
    return [_hit(doc, k, s, e, "fuzzy", score) for score, k, s, e in results[:max_hits]]


def find_quote(doc, quote, threshold=0.8, max_hits=10):
    """Search one Doc. Returns (match tier or 'none', hits)."""
    quote = quote.strip()
    hits = _exact(doc, quote, max_hits)
    if hits:  # the same words may also sit on other pages with different line breaks
        seen = {h["page"] for h in hits}
        more = [h for h in _normalized(doc, quote, max_hits) if h["page"] not in seen]
        return "exact", sorted(hits + more, key=lambda h: h["page"])[:max_hits]
    hits = _normalized(doc, quote, max_hits)
    if hits:
        return "normalized", hits
    hits = _fuzzy(doc, quote, threshold, max_hits)
    return ("fuzzy", hits) if hits else ("none", [])


# ---------------------------------------------------------------- citations

def source_for(doc, out_dir):
    idx = doc.index
    return c.find_source(out_dir, idx.get("source_id"), idx.get("pdf_url"))


def citation(doc, record, pages):
    pages = sorted(set(pages))
    where = "p. %d" % pages[0] if len(pages) == 1 else "pp. %d-%d" % (pages[0], pages[-1])
    pdf_url = (record or {}).get("pdf_url") or doc.index.get("pdf_url")
    url = pdf_url or (record or {}).get("url")
    if url and url == pdf_url:
        url = "%s#page=%d" % (url, pages[0])
    if record:
        year = record.get("year") or (str(record.get("date") or "")[:4] or "n.d.")
        return "(%s, %s, %s, %s)" % (c.short_title(record.get("title")) or "Untitled", year, where,
                                     url or "no URL recorded")
    return "(TITLE?, YEAR?, %s, %s) [no sources.jsonl record for this text]" % (where, url or doc.index.get("pdf"))


def search(folder, quote, out_dir="research", threshold=0.8, max_hits=10):
    doc = Doc(folder)
    tier, hits = find_quote(doc, quote, threshold, max_hits)
    record = source_for(doc, out_dir)
    for h in hits:
        h["citation"] = citation(doc, record, h["pages"])
    return {"text": str(doc.folder), "id": doc.index.get("id"), "source_id": record.get("id") if record else None,
            "engine": doc.index.get("engine"), "pages_searched": len(doc.pages), "match": tier,
            "occurrences": occurrences(doc, quote, tier), "hits": hits}


def occurrences(doc, quote, tier):
    """{page: count} for exact or normalized matches (all pages, not limited by --max)."""
    if tier == "exact":
        counts = {p: t.count(quote) for p, t in doc.pages}
    elif tier == "normalized" and not ELLIPSIS.search(quote):
        nq = normalize(quote)[0]
        counts = {doc.pages[k][0]: doc.norm(k)[0].count(nq) for k in range(len(doc.pages))}
    else:
        return {}
    return {str(p): n for p, n in counts.items() if n}


def main(argv=None):
    ap = c.parser(__doc__.split("\n\n")[0], EPILOG)
    ap.add_argument("text", nargs="?", help="text folder or id (omit with --all)")
    ap.add_argument("quote", help="quote or key phrase to find")
    ap.add_argument("--all", action="store_true", help="search every folder under <out>/text/")
    ap.add_argument("--threshold", type=float, default=0.8, help="fuzzy tier: share of words that must match (0.8)")
    ap.add_argument("--max", type=int, default=10, help="most hits to show per document (10)")
    a = ap.parse_args(argv)
    if a.all:
        if a.text:
            a.quote = a.text + " " + a.quote if a.quote else a.text
        folders = c.all_text_dirs(a.out)
        if not folders:
            print("error: no text folders under %s/text; run pdf_text.py first" % a.out, file=sys.stderr)
            return 1
    else:
        if not a.text:
            ap.error("give a text folder or id, or use --all")
        try:
            folders = [c.text_dir(a.out, a.text)]
        except FileNotFoundError as err:
            print("error: %s" % err, file=sys.stderr)
            return 1
    results = [search(f, a.quote, a.out, a.threshold, a.max) for f in folders]
    found = [r for r in results if r["hits"]]
    if a.json:
        c.print_json({"quote": a.quote, "results": results})
        return 0 if found else 1
    for r in results:
        if a.all and not r["hits"]:
            continue
        print("%s (%s, %d pages, engine %s): %s" % (r["id"], r["source_id"] or "no source record",
                                                    r["pages_searched"], r["engine"], r["match"].upper()))
        occ = r.get("occurrences") or {}
        if len(occ) > 1 or sum(occ.values()) > len(r["hits"]):
            print("  found %d times on %d pages: %s" % (sum(occ.values()), len(occ),
                                                      ", ".join("p. %s (%d)" % kv for kv in occ.items())))
        for h in r["hits"]:
            label = "p. %s" % h["page"] if len(h["pages"]) == 1 else "pp. %s-%s" % (h["pages"][0], h["pages"][-1])
            extra = " (score %.2f: wording differs; quote the page as printed)" % h["score"] if h["match"] == "fuzzy" else ""
            print("  %s  %s%s" % (label, h["match"], extra))
            print("    \"%s\"" % h["sentence"])
            print("    cite: %s" % h["citation"])
            if h.get("note"):
                print("    note: %s" % h["note"])
    if not found:
        searched = ", ".join("%s (%d pages)" % (r["id"], r["pages_searched"]) for r in results)
        print("NOT FOUND: %r in %s. Do not make this claim from these texts." % (a.quote, searched))
        return 1
    print("pages are PDF page indexes (1 = first page of the file), not printed page numbers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
