"""Pure standard-library PDF text extraction: route 3 of pdf_text.py. Imported; not run on its own.

How it works
  1. Finds every "N G obj ... endobj" in the file, plus the objects packed in compressed object streams.
  2. Walks the page tree (/Root -> /Pages -> /Kids) to list the pages in order.
  3. Decodes each page's content streams: FlateDecode with zlib, also LZW, ASCII85, ASCIIHex, RunLength.
  4. Reads the text operators Tj, TJ, ' and " and maps bytes to Unicode with the font's /ToUnicode
     CMap, else its /Encoding and /Differences, else WinAnsi. Glyph widths and the text and graphics
     matrices (Td, TD, Tm, T*, cm) decide where spaces and line breaks go. Text in Form XObjects (Do)
     is followed.

Limits
  - No OCR: a scanned page has no text operators and comes out empty.
  - No decryption: encrypted PDFs (including "no copying" permission flags) are refused.
  - Fonts without a ToUnicode map and without a standard encoding (some Type3 and CJK fonts)
    give wrong or missing characters; they are counted in the report.
  - Spaces and line breaks are inferred from positions: words can run together or split.
  - Reading order is the content-stream order: usually column by column, but not always.
"""
import base64
import math
import re
import unicodedata
import zlib

__all__ = ["extract", "PDFError"]


class PDFError(Exception):
    pass


class Ref:
    __slots__ = ("num", "gen")

    def __init__(self, num, gen):
        self.num, self.gen = num, gen


class Stream:
    __slots__ = ("dict", "raw")

    def __init__(self, d, raw):
        self.dict, self.raw = d, raw


# ---------------------------------------------------------------- tokenizer

_DELIMS = rb"\x00\t\n\x0c\r ()<>\[\]{}/%"
_TOKEN = re.compile(
    rb"[\x00\t\n\x0c\r ]+|%[^\r\n]*"
    rb"|(?P<name>/[^" + _DELIMS + rb"]*)"
    rb"|(?P<num>[+-]?(?:\d+\.?\d*|\.\d+))(?![^" + _DELIMS + rb"])"
    rb"|(?P<dopen><<)|(?P<dclose>>>)"
    rb"|(?P<hex><[0-9A-Fa-f\x00\t\n\x0c\r ]*>)"
    rb"|(?P<lpar>\()"
    rb"|(?P<aopen>\[)|(?P<aclose>\])"
    rb"|(?P<brace>[{}])"
    rb"|(?P<kw>[^" + _DELIMS + rb"]+)"
)
_LIT_SPECIAL = re.compile(rb"[()\\]")
_ESC = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12, ord("("): 40, ord(")"): 41, ord("\\"): 92}
_INLINE_END = re.compile(rb"[\x00\t\n\x0c\r ]EI(?=[\x00\t\n\x0c\r ]|$)")
_NAME_ESC = re.compile(rb"#([0-9A-Fa-f]{2})")


def _literal(data, i):
    """data[i] is '('; return (bytes, index after the closing ')')."""
    out = bytearray()
    depth = 1
    i += 1
    n = len(data)
    while True:
        m = _LIT_SPECIAL.search(data, i)
        if not m:
            out += data[i:]
            return bytes(out), n
        j = m.start()
        out += data[i:j]
        ch = data[j]
        if ch == 0x5C:  # backslash
            j += 1
            if j >= n:
                return bytes(out), n
            e = data[j]
            if e in _ESC:
                out.append(_ESC[e])
                i = j + 1
            elif 0x30 <= e <= 0x37:
                k, v = j, 0
                while k < n and k < j + 3 and 0x30 <= data[k] <= 0x37:
                    v = v * 8 + data[k] - 0x30
                    k += 1
                out.append(v & 0xFF)
                i = k
            elif e == 0x0D:
                i = j + 1
                if i < n and data[i] == 0x0A:
                    i += 1
            elif e == 0x0A:
                i = j + 1
            else:
                out.append(e)
                i = j + 1
            continue
        if ch == 0x28:
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return bytes(out), j + 1
        out.append(ch)
        i = j + 1


def _hexstr(tok):
    h = re.sub(rb"[^0-9A-Fa-f]", b"", tok)
    if len(h) % 2:
        h += b"0"
    return bytes.fromhex(h.decode("ascii"))


def tokens(data, pos=0, end=None):
    """Yield (kind, value, position after token). Kinds: name num str kw aopen aclose dopen dclose."""
    end = len(data) if end is None else end
    match = _TOKEN.match
    while pos < end:
        m = match(data, pos)
        if m is None:
            pos += 1
            continue
        kind = m.lastgroup
        if kind is None:
            pos = m.end()
            continue
        if kind == "lpar":
            value, pos = _literal(data, m.start())
            yield "str", value, pos
            continue
        tok = m.group(kind)
        pos = m.end()
        if kind == "num":
            yield "num", (float(tok) if b"." in tok else int(tok)), pos
        elif kind == "name":
            yield "name", "/" + _NAME_ESC.sub(lambda x: bytes([int(x.group(1), 16)]), tok[1:]).decode("latin-1"), pos
        elif kind == "hex":
            yield "str", _hexstr(tok), pos
        elif kind == "brace":
            continue
        elif kind == "kw" and tok == b"ID":  # inline image data: skip to EI
            e = _INLINE_END.search(data, pos)
            pos = e.end() if e else end
            yield "kw", b"EI", pos
        else:
            yield kind, (tok if kind == "kw" else None), pos


def _to_dict(items):
    d = {}
    for i in range(0, len(items) - 1, 2):
        if isinstance(items[i], str):
            d[items[i]] = items[i + 1]
    return d


def parse_object(data, pos, end=None, single=False):
    """Parse a PDF object at pos. Returns (value, position after it, terminating keyword or None)."""
    stack = [[]]
    last = pos
    for kind, val, p in tokens(data, pos, end):
        last = p
        top = stack[-1]
        if kind in ("aopen", "dopen"):
            stack.append([kind])
            continue
        if kind in ("aclose", "dclose"):
            if len(stack) == 1:
                continue
            items = stack.pop()[1:]
            stack[-1].append(items if kind == "aclose" else _to_dict(items))
        elif kind == "kw":
            if val == b"R" and len(top) >= 2 and type(top[-1]) is int and type(top[-2]) is int:
                gen = top.pop()
                top.append(Ref(top.pop(), gen))
            elif val in (b"true", b"false"):
                top.append(val == b"true")
            elif val == b"null":
                top.append(None)
            elif val in (b"endobj", b"stream", b"obj", b"endstream", b"xref", b"trailer", b"startxref"):
                while len(stack) > 1:  # unclosed containers: close them
                    items = stack.pop()
                    stack[-1].append(items[1:] if items[0] == "aopen" else _to_dict(items[1:]))
                return (stack[0][0] if stack[0] else None), p, val
        else:
            top.append(val)
        if single and len(stack) == 1 and stack[0]:
            return stack[0][0], p, None
    return (stack[0][0] if stack[0] else None), last, None


# ---------------------------------------------------------------- filters

def _inflate(data):
    try:
        return zlib.decompress(data)
    except zlib.error:
        pass
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        d = zlib.decompressobj(wbits)
        try:
            return d.decompress(data)
        except zlib.error:
            continue
    d, out = zlib.decompressobj(), bytearray()  # salvage what decodes before the damage
    for i in range(0, len(data), 512):
        try:
            out += d.decompress(data[i:i + 512])
        except zlib.error:
            break
    return bytes(out)


def _lzw(data, early=1):
    out, table = bytearray(), [bytes([i]) for i in range(256)] + [b"", b""]
    bits, buf, nbits, prev = 9, 0, 0, None
    for byte in data:
        buf = (buf << 8) | byte
        nbits += 8
        while nbits >= bits:
            nbits -= bits
            code = (buf >> nbits) & ((1 << bits) - 1)
            if code == 256:
                table, bits, prev = table[:258], 9, None
                continue
            if code == 257:
                return bytes(out)
            if prev is None:
                entry = table[code] if code < len(table) else b""
            elif code < len(table):
                entry = table[code]
                table.append(prev + entry[:1])
            elif code == len(table):
                entry = prev + prev[:1]
                table.append(entry)
            else:
                return bytes(out)
            out += entry
            prev = entry
            if len(table) + early >= (1 << bits) and bits < 12:
                bits += 1
    return bytes(out)


def _a85(data):
    data = re.sub(rb"\s", b"", data)
    if data.startswith(b"<~"):
        data = data[2:]
    stop = data.find(b"~>")
    return base64.a85decode(data[:stop] if stop >= 0 else data)


def _ahx(data):
    data = re.sub(rb"\s", b"", data)
    stop = data.find(b">")
    return _hexstr(data[:stop] if stop >= 0 else data)


def _rl(data):
    out, i = bytearray(), 0
    while i < len(data):
        n = data[i]
        i += 1
        if n == 128:
            break
        if n < 128:
            out += data[i:i + n + 1]
            i += n + 1
        else:
            out += data[i:i + 1] * (257 - n)
            i += 1
    return bytes(out)


def _predict(data, parms):
    if not isinstance(parms, dict):
        return data
    pred = int(parms.get("/Predictor", 1) or 1)
    if pred < 10:
        return data  # TIFF predictor 2 never appears on text content streams
    colors = int(parms.get("/Colors", 1) or 1)
    bpc = int(parms.get("/BitsPerComponent", 8) or 8)
    cols = int(parms.get("/Columns", 1) or 1)
    bpp = max(1, colors * bpc // 8)
    rowlen = (colors * bpc * cols + 7) // 8
    out, prev, i = bytearray(), bytearray(rowlen), 0
    while i < len(data):
        ft = data[i]
        row = bytearray(data[i + 1:i + 1 + rowlen])
        row += bytes(rowlen - len(row))
        i += rowlen + 1
        if ft == 1:
            for j in range(bpp, rowlen):
                row[j] = (row[j] + row[j - bpp]) & 255
        elif ft == 2:
            for j in range(rowlen):
                row[j] = (row[j] + prev[j]) & 255
        elif ft == 3:
            for j in range(rowlen):
                left = row[j - bpp] if j >= bpp else 0
                row[j] = (row[j] + ((left + prev[j]) >> 1)) & 255
        elif ft == 4:
            for j in range(rowlen):
                a = row[j - bpp] if j >= bpp else 0
                b = prev[j]
                c = prev[j - bpp] if j >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[j] = (row[j] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        out += row
        prev = row
    return bytes(out)


# ---------------------------------------------------------------- encodings

def _single_byte_table(codec):
    table = []
    for b in range(256):
        try:
            table.append(bytes([b]).decode(codec))
        except UnicodeDecodeError:
            table.append("")
    return table


WINANSI = _single_byte_table("cp1252")
WINANSI[0xA0], WINANSI[0xAD] = " ", "-"
MACROMAN = _single_byte_table("mac_roman")

AGL = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$", "percent": "%",
    "ampersand": "&", "quotesingle": "'", "quoteright": "’", "quoteleft": "‘", "parenleft": "(",
    "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-", "period": ".", "slash": "/",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "colon": ":", "semicolon": ";", "less": "<", "equal": "=", "greater": ">",
    "question": "?", "at": "@", "bracketleft": "[", "backslash": "\\", "bracketright": "]",
    "asciicircum": "^", "underscore": "_", "grave": "`", "braceleft": "{", "bar": "|", "braceright": "}",
    "asciitilde": "~", "exclamdown": "¡", "cent": "¢", "sterling": "£", "fraction": "⁄",
    "yen": "¥", "florin": "ƒ", "section": "§", "currency": "¤", "quotedblleft": "“",
    "guillemotleft": "«", "guilsinglleft": "‹", "guilsinglright": "›", "fi": "fi", "fl": "fl",
    "ff": "ff", "ffi": "ffi", "ffl": "ffl", "endash": "–", "emdash": "—", "dagger": "†",
    "daggerdbl": "‡", "periodcentered": "·", "paragraph": "¶", "bullet": "•",
    "quotesinglbase": "‚", "quotedblbase": "„", "quotedblright": "”", "guillemotright": "»",
    "ellipsis": "…", "perthousand": "‰", "questiondown": "¿", "acute": "´",
    "circumflex": "ˆ", "tilde": "˜", "macron": "¯", "breve": "˘", "dotaccent": "˙",
    "dieresis": "¨", "ring": "˚", "cedilla": "¸", "hungarumlaut": "˝", "ogonek": "˛",
    "caron": "ˇ", "AE": "Æ", "ae": "æ", "ordfeminine": "ª", "ordmasculine": "º",
    "Lslash": "Ł", "lslash": "ł", "Oslash": "Ø", "oslash": "ø", "OE": "Œ",
    "oe": "œ", "dotlessi": "ı", "germandbls": "ß", "minus": "−", "degree": "°",
    "copyright": "©", "registered": "®", "trademark": "™", "multiply": "×",
    "divide": "÷", "plusminus": "±", "mu": "µ", "onehalf": "½", "onequarter": "¼",
    "threequarters": "¾", "onesuperior": "¹", "twosuperior": "²", "threesuperior": "³",
    "logicalnot": "¬", "brokenbar": "¦", "nbspace": " ", "nonbreakingspace": " ", "sfthyphen": "-",
    "softhyphen": "-", "Euro": "€", "euro": "€", "Eth": "Ð", "eth": "ð", "Thorn": "Þ",
    "thorn": "þ", "lessequal": "≤", "greaterequal": "≥", "notequal": "≠",
    "approxequal": "≈", "infinity": "∞", "summation": "∑", "product": "∏",
    "radical": "√", "partialdiff": "∂", "integral": "∫", "Delta": "Δ", "Omega": "Ω",
    "pi": "π", "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "sigma": "σ", "lozenge": "◊", "arrowright": "→", "arrowleft": "←",
    "checkmark": "✓", "dotlessj": "ȷ", "quotereversed": "‛", "figuredash": "‒",
}
_ACCENTS = {"acute": "ACUTE", "grave": "GRAVE", "circumflex": "CIRCUMFLEX", "dieresis": "DIAERESIS",
            "tilde": "TILDE", "ring": "RING ABOVE", "cedilla": "CEDILLA", "caron": "CARON", "macron": "MACRON",
            "breve": "BREVE", "ogonek": "OGONEK", "dotaccent": "DOT ABOVE", "hungarumlaut": "DOUBLE ACUTE",
            "commaaccent": "COMMA BELOW"}
_ACCENTED = re.compile(r"([A-Za-z])(" + "|".join(_ACCENTS) + r")$")


def glyph_to_unicode(name):
    n = name.lstrip("/")
    if n in AGL:
        return AGL[n]
    if len(n) == 1 and n.isascii() and n.isalpha():
        return n
    m = re.match(r"uni((?:[0-9A-Fa-f]{4})+)$", n)
    if m:
        h = m.group(1)
        return "".join(chr(int(h[i:i + 4], 16)) for i in range(0, len(h), 4))
    m = re.match(r"u([0-9A-Fa-f]{4,6})$", n)
    if m:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return None
    if "." in n and not n.startswith("."):
        return glyph_to_unicode(n.split(".")[0])
    if "_" in n:
        parts = [glyph_to_unicode(p) for p in n.split("_")]
        return "".join(parts) if all(parts) else None
    m = _ACCENTED.match(n)
    if m:
        letter, accent = m.groups()
        try:
            return unicodedata.lookup("LATIN %s LETTER %s WITH %s" % (
                "CAPITAL" if letter.isupper() else "SMALL", letter.upper(), _ACCENTS[accent]))
        except KeyError:
            return None
    return None


_STD_HIGH = {
    0xA1: "exclamdown", 0xA2: "cent", 0xA3: "sterling", 0xA4: "fraction", 0xA5: "yen", 0xA6: "florin",
    0xA7: "section", 0xA8: "currency", 0xA9: "quotesingle", 0xAA: "quotedblleft", 0xAB: "guillemotleft",
    0xAC: "guilsinglleft", 0xAD: "guilsinglright", 0xAE: "fi", 0xAF: "fl", 0xB1: "endash", 0xB2: "dagger",
    0xB3: "daggerdbl", 0xB4: "periodcentered", 0xB6: "paragraph", 0xB7: "bullet", 0xB8: "quotesinglbase",
    0xB9: "quotedblbase", 0xBA: "quotedblright", 0xBB: "guillemotright", 0xBC: "ellipsis", 0xBD: "perthousand",
    0xBF: "questiondown", 0xC1: "grave", 0xC2: "acute", 0xC3: "circumflex", 0xC4: "tilde", 0xC5: "macron",
    0xC6: "breve", 0xC7: "dotaccent", 0xC8: "dieresis", 0xCA: "ring", 0xCB: "cedilla", 0xCD: "hungarumlaut",
    0xCE: "ogonek", 0xCF: "caron", 0xD0: "emdash", 0xE1: "AE", 0xE3: "ordfeminine", 0xE8: "Lslash",
    0xE9: "Oslash", 0xEA: "OE", 0xEB: "ordmasculine", 0xF1: "ae", 0xF5: "dotlessi", 0xF8: "lslash",
    0xF9: "oslash", 0xFA: "oe", 0xFB: "germandbls",
}
STANDARD = [chr(b) if 0x20 <= b <= 0x7E else "" for b in range(256)]
STANDARD[0x27], STANDARD[0x60] = "’", "‘"
for _code, _name in _STD_HIGH.items():
    STANDARD[_code] = AGL.get(_name, "")
BASE_ENCODINGS = {"/WinAnsiEncoding": WINANSI, "/MacRomanEncoding": MACROMAN, "/StandardEncoding": STANDARD}

# Helvetica advance widths (1/1000 em) for codes 32-126: used when a font gives no /Widths.
_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556,
         556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778,
         722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278,
         278, 278, 469, 556, 222, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
         556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
HELV_WIDTHS = {32 + i: w for i, w in enumerate(_HELV)}


# ---------------------------------------------------------------- CMaps and fonts

def _hexclean(h):
    return re.sub(rb"[^0-9A-Fa-f]", b"", h)


def _utf16(h):
    raw = bytes.fromhex(h.decode("ascii")) if h else b""
    if len(raw) % 2:
        return raw.decode("latin-1")
    return raw.decode("utf-16-be", "replace")


def parse_cmap(data):
    """ToUnicode CMap -> ({(nbytes, code): text}, [(nbytes, lo, hi)])."""
    mapping, spaces = {}, []
    pair = re.compile(rb"<([0-9A-Fa-f\s]*)>\s*<([0-9A-Fa-f\s]*)>")
    for block in re.finditer(rb"begincodespacerange(.*?)endcodespacerange", data, re.S):
        for lo, hi in pair.findall(block.group(1)):
            lo, hi = _hexclean(lo), _hexclean(hi)
            if lo:
                spaces.append((len(lo) // 2, int(lo, 16), int(hi or lo, 16)))
    for block in re.finditer(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in pair.findall(block.group(1)):
            src = _hexclean(src)
            if src:
                mapping[(len(src) // 2, int(src, 16))] = _utf16(_hexclean(dst))
    entry = re.compile(rb"<([0-9A-Fa-f\s]*)>\s*<([0-9A-Fa-f\s]*)>\s*(\[[^\]]*\]|<[0-9A-Fa-f\s]*>)")
    for block in re.finditer(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for m in entry.finditer(block.group(1)):
            lo_h, hi_h = _hexclean(m.group(1)), _hexclean(m.group(2))
            if not lo_h:
                continue
            nb, lo, hi = len(lo_h) // 2, int(lo_h, 16), int(hi_h or lo_h, 16)
            if hi < lo or hi - lo > 65535:
                continue
            dst = m.group(3)
            if dst.startswith(b"["):
                for k, h in enumerate(re.findall(rb"<([0-9A-Fa-f\s]*)>", dst)):
                    if lo + k > hi:
                        break
                    mapping[(nb, lo + k)] = _utf16(_hexclean(h))
            else:
                h = _hexclean(dst[1:-1])
                if not h:
                    continue
                base, width = int(h, 16), len(h)
                for k in range(hi - lo + 1):
                    mapping[(nb, lo + k)] = _utf16(("%0*X" % (width, base + k)).encode("ascii"))
    return mapping, spaces


def _num(x, default=0.0):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else default


class Font:
    def __init__(self, doc, fdict):
        r = doc.resolve
        self.subtype = r(fdict.get("/Subtype"))
        self.name = str(r(fdict.get("/BaseFont")) or "?")
        self.cid = self.subtype == "/Type0"
        self.unicode, self.spaces = {}, []
        self.has_tounicode = False
        self.ucs2 = False
        self.unmapped = 0
        self.wscale = 0.001
        tu = r(fdict.get("/ToUnicode"))
        if isinstance(tu, Stream):
            try:
                self.unicode, self.spaces = parse_cmap(doc.decode(tu))
                self.has_tounicode = bool(self.unicode)
            except Exception:  # a broken CMap: fall back to the encoding
                self.unicode, self.spaces = {}, []
        if self.cid:
            enc = r(fdict.get("/Encoding"))
            self.ucs2 = isinstance(enc, str) and ("UCS2" in enc or "UTF16" in enc)
            kids = r(fdict.get("/DescendantFonts")) or [None]
            desc = r(kids[0]) if isinstance(kids, list) and kids else None
            desc = desc if isinstance(desc, dict) else {}
            self.default_width = _num(r(desc.get("/DW")), 1000.0)
            self.widths = self._cid_widths(doc, r(desc.get("/W")))
            self.encoding = None
            if not self.spaces:
                self.spaces = [(2, 0, 0xFFFF)]
        else:
            first = int(_num(r(fdict.get("/FirstChar")), 0))
            widths = r(fdict.get("/Widths")) or []
            self.widths = {}
            if isinstance(widths, list):
                for i, w in enumerate(widths):
                    self.widths[first + i] = _num(r(w))
            desc = r(fdict.get("/FontDescriptor"))
            missing = _num(r(desc.get("/MissingWidth")), 0.0) if isinstance(desc, dict) else 0.0
            self.default_width = missing or 0.0
            if self.subtype == "/Type3":
                matrix = r(fdict.get("/FontMatrix"))
                if isinstance(matrix, list) and matrix:
                    self.wscale = _num(r(matrix[0]), 0.001)
            self.encoding = self._simple_encoding(doc, fdict)
            self.spaces = [s for s in self.spaces if s[0] == 1] or [(1, 0, 0xFF)]
        self.spaces.sort()
        self.multibyte = any(nb > 1 for nb, _, _ in self.spaces)

    @staticmethod
    def _cid_widths(doc, w):
        out = {}
        if not isinstance(w, list):
            return out
        i = 0
        while i < len(w):
            first = doc.resolve(w[i])
            nxt = doc.resolve(w[i + 1]) if i + 1 < len(w) else None
            if isinstance(nxt, list):
                for k, width in enumerate(nxt):
                    out[int(_num(first)) + k] = _num(doc.resolve(width))
                i += 2
            elif i + 2 < len(w):
                last, width = doc.resolve(w[i + 1]), _num(doc.resolve(w[i + 2]))
                for code in range(int(_num(first)), min(int(_num(last)), int(_num(first)) + 65536) + 1):
                    out[code] = width
                i += 3
            else:
                break
        return out

    def _simple_encoding(self, doc, fdict):
        enc = doc.resolve(fdict.get("/Encoding"))
        base_name, diffs = None, None
        if isinstance(enc, str):
            base_name = enc
        elif isinstance(enc, dict):
            base_name = doc.resolve(enc.get("/BaseEncoding"))
            diffs = doc.resolve(enc.get("/Differences"))
        if base_name in BASE_ENCODINGS:
            table = list(BASE_ENCODINGS[base_name])
        elif self.subtype == "/TrueType":
            table = list(WINANSI)
        else:
            table = list(STANDARD)
        if isinstance(diffs, list):
            code = 0
            for item in diffs:
                item = doc.resolve(item)
                if isinstance(item, (int, float)) and not isinstance(item, bool):
                    code = int(item)
                elif isinstance(item, str) and 0 <= code < 256:
                    uni = glyph_to_unicode(item)
                    table[code] = uni if uni is not None else ""
                    code += 1
        return table

    def _code_len(self, s, i):
        for nb, lo, hi in self.spaces:
            if i + nb <= len(s) and lo <= int.from_bytes(s[i:i + nb], "big") <= hi:
                return nb
        return self.spaces[-1][0] if self.cid else 1

    def decode(self, s):
        """bytes -> list of (text, advance width per unit font size, is single-byte space)."""
        out = []
        if not self.multibyte:
            for b in s:
                text = self.unicode.get((1, b))
                if text is None:
                    text = self.encoding[b] if self.encoding else chr(b)
                    if self.cid:
                        text = ""
                w = self.widths.get(b) or self.default_width or HELV_WIDTHS.get(b, 556)
                out.append((text, w * self.wscale, b == 32))
            return out
        i, n = 0, len(s)
        while i < n:
            nb = self._code_len(s, i)
            chunk = s[i:i + nb]
            code = int.from_bytes(chunk, "big")
            text = self.unicode.get((nb, code))
            if text is None:
                if self.ucs2:
                    text = chunk.decode("utf-16-be", "replace")
                elif nb == 1 and self.encoding:
                    text = self.encoding[code]
                else:
                    text = ""
                    self.unmapped += 1
            w = self.widths.get(code, self.default_width if self.cid else 556)
            out.append((text, w * 0.001, nb == 1 and code == 32))
            i += nb
        return out


# ---------------------------------------------------------------- document

_OBJ = re.compile(rb"(?<![0-9])(\d{1,10})[\x00\t\n\x0c\r ]+(\d{1,5})[\x00\t\n\x0c\r ]+obj(?![A-Za-z])")
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)


def _matrix(values):
    vals = [_num(v) for v in values]
    return tuple(vals) if len(vals) == 6 else IDENTITY


class Document:
    def __init__(self, data):
        start = data.find(b"%PDF")
        if start < 0 or start > 1024:
            raise PDFError("not a PDF (no %PDF header)")
        self.data = data
        self.objects = {}
        self._scan()
        self.trailer = self._trailer()
        if "/Encrypt" in self.trailer:
            raise PDFError("encrypted PDF: the standard-library route cannot decrypt it; "
                           "use pdftotext (poppler) or pypdf")
        self._unpack_object_streams()
        self.fonts = {}
        self.page_order = "page tree"

    def _scan(self):
        data, pos = self.data, 0
        while True:
            m = _OBJ.search(data, pos)
            if not m:
                break
            num = int(m.group(1))
            try:
                value, p, term = parse_object(data, m.end())
            except Exception:
                pos = m.end()
                continue
            if term == b"stream":
                start = p
                if data[start:start + 2] == b"\r\n":
                    start += 2
                elif data[start:start + 1] in (b"\n", b"\r"):
                    start += 1
                d = value if isinstance(value, dict) else {}
                length = d.get("/Length")
                stop = None
                if isinstance(length, int) and length >= 0:
                    tail = data[start + length:start + length + 32].lstrip(b"\r\n \t\x00\x0c")
                    if tail.startswith(b"endstream"):
                        stop = start + length
                if stop is None:
                    idx = data.find(b"endstream", start)
                    stop = idx if idx >= 0 else len(data)
                self.objects[num] = Stream(d, data[start:stop])
                pos = stop
            else:
                self.objects[num] = value
                pos = max(p, m.end())

    def _trailer(self):
        trailer = {}
        for m in re.finditer(rb"trailer[\x00\t\n\x0c\r ]*<<", self.data):
            try:
                value, _, _ = parse_object(self.data, m.end() - 2, single=True)
            except Exception:
                continue
            if isinstance(value, dict):
                trailer.update(value)
        for obj in self.objects.values():
            if isinstance(obj, Stream) and obj.dict.get("/Type") == "/XRef":
                for key in ("/Root", "/Info", "/Encrypt"):
                    if key in obj.dict:
                        trailer[key] = obj.dict[key]
        return trailer

    def _unpack_object_streams(self):
        for obj in list(self.objects.values()):
            if not (isinstance(obj, Stream) and obj.dict.get("/Type") == "/ObjStm"):
                continue
            try:
                data = self.decode(obj)
                n = int(_num(self.resolve(obj.dict.get("/N"))))
                first = int(_num(self.resolve(obj.dict.get("/First"))))
            except Exception:
                continue
            nums = [int(x) for x in re.findall(rb"\d+", data[:first])][:2 * n]
            pairs = list(zip(nums[0::2], nums[1::2]))
            for k, (onum, off) in enumerate(pairs):
                begin = first + off
                end = first + pairs[k + 1][1] if k + 1 < len(pairs) else len(data)
                if onum in self.objects:
                    continue
                try:
                    value, _, _ = parse_object(data, begin, end)
                except Exception:
                    continue
                self.objects[onum] = value

    def resolve(self, x):
        for _ in range(32):
            if not isinstance(x, Ref):
                return x
            x = self.objects.get(x.num)
        return None

    def decode(self, stream):
        data = stream.raw
        filters = self.resolve(stream.dict.get("/Filter"))
        parms = self.resolve(stream.dict.get("/DecodeParms"))
        if filters is None:
            return data
        if not isinstance(filters, list):
            filters = [filters]
        if not isinstance(parms, list):
            parms = [parms] * len(filters)
        for i, f in enumerate(filters):
            f = self.resolve(f)
            p = self.resolve(parms[i]) if i < len(parms) else None
            if f in ("/FlateDecode", "/Fl"):
                data = _predict(_inflate(data), p)
            elif f in ("/LZWDecode", "/LZW"):
                early = int(_num(p.get("/EarlyChange"), 1)) if isinstance(p, dict) else 1
                data = _predict(_lzw(data, early), p)
            elif f in ("/ASCII85Decode", "/A85"):
                data = _a85(data)
            elif f in ("/ASCIIHexDecode", "/AHx"):
                data = _ahx(data)
            elif f in ("/RunLengthDecode", "/RL"):
                data = _rl(data)
            elif f == "/Crypt":
                continue
            else:
                raise PDFError("unsupported filter %s" % f)
        return data

    def info_title(self):
        info = self.resolve(self.trailer.get("/Info"))
        title = self.resolve(info.get("/Title")) if isinstance(info, dict) else None
        if not isinstance(title, bytes) or not title.strip():
            return None
        if title[:2] == b"\xfe\xff":
            return title[2:].decode("utf-16-be", "replace").strip() or None
        return title.decode("latin-1").strip() or None

    def pages(self):
        out = []
        root = self.resolve(self.trailer.get("/Root"))
        if not isinstance(root, dict):
            root = next((o for o in self.objects.values() if isinstance(o, dict) and o.get("/Type") == "/Catalog"), None)
        if isinstance(root, dict):
            self._walk(root.get("/Pages"), None, out, set(), 0)
        if not out:
            self.page_order = "object order (no usable page tree)"
            for num in sorted(self.objects):
                o = self.objects[num]
                if isinstance(o, dict) and o.get("/Type") == "/Page":
                    out.append((o, self.resolve(o.get("/Resources"))))
        return out

    def _walk(self, node_ref, inherited, out, seen, depth):
        if depth > 64:
            return
        key = ("ref", node_ref.num) if isinstance(node_ref, Ref) else ("id", id(node_ref))
        if key in seen:
            return
        seen.add(key)
        node = self.resolve(node_ref)
        if not isinstance(node, dict):
            return
        res = node.get("/Resources", inherited)
        kids = self.resolve(node.get("/Kids"))
        if node.get("/Type") == "/Pages" or (isinstance(kids, list) and node.get("/Type") != "/Page"):
            for kid in kids or []:
                self._walk(kid, res, out, seen, depth + 1)
        else:
            out.append((node, self.resolve(res)))

    def font(self, ref):
        key = ref.num if isinstance(ref, Ref) else id(ref)
        if key not in self.fonts:
            fdict = self.resolve(ref)
            self.fonts[key] = Font(self, fdict) if isinstance(fdict, dict) else None
        return self.fonts[key]

    def page_text(self, page, resources):
        contents = self.resolve(page.get("/Contents"))
        parts = contents if isinstance(contents, list) else [contents]
        data = b"\n".join(self.decode(s) for s in (self.resolve(p) for p in parts) if isinstance(s, Stream))
        sink = _Sink()
        self._run(data, resources if isinstance(resources, dict) else {}, IDENTITY, sink, 0)
        return sink.text()

    def _run(self, data, resources, ctm, sink, depth):
        r = self.resolve
        fonts = r(resources.get("/Font")) or {}
        xobjects = r(resources.get("/XObject")) or {}
        gs = {"ctm": ctm, "font": None, "size": 0.0, "tc": 0.0, "tw": 0.0, "th": 1.0, "tl": 0.0, "rise": 0.0}
        saved, tm, tlm = [], IDENTITY, IDENTITY
        ops, arrays, dict_depth = [], [], 0
        for kind, val, _pos in tokens(data):
            if dict_depth:
                if kind == "dopen":
                    dict_depth += 1
                elif kind == "dclose":
                    dict_depth -= 1
                continue
            if kind == "dopen":
                dict_depth = 1
                continue
            if kind == "aopen":
                arrays.append([])
                continue
            if kind == "aclose":
                if arrays:
                    done = arrays.pop()
                    (arrays[-1] if arrays else ops).append(done)
                continue
            if kind != "kw":
                (arrays[-1] if arrays else ops).append(val)
                continue
            arrays = []
            op = val
            try:
                if op == b"Tj" or op == b"TJ":
                    if ops:
                        tm = self._show(gs, tm, ops[-1], sink)
                elif op == b"Td" or op == b"TD":
                    tx, ty = _num(ops[-2]), _num(ops[-1])
                    if op == b"TD":
                        gs["tl"] = -ty
                    tlm = _mul((1.0, 0.0, 0.0, 1.0, tx, ty), tlm)
                    tm = tlm
                elif op == b"Tm":
                    tlm = tm = _matrix(ops[-6:])
                elif op == b"T*":
                    tlm = _mul((1.0, 0.0, 0.0, 1.0, 0.0, -gs["tl"]), tlm)
                    tm = tlm
                elif op == b"'" or op == b'"':
                    if op == b'"' and len(ops) >= 3:
                        gs["tw"], gs["tc"] = _num(ops[-3]), _num(ops[-2])
                    tlm = _mul((1.0, 0.0, 0.0, 1.0, 0.0, -gs["tl"]), tlm)
                    tm = tlm
                    if ops:
                        tm = self._show(gs, tm, ops[-1], sink)
                elif op == b"Tf":
                    gs["font"] = self.font(fonts.get(ops[-2])) if isinstance(fonts, dict) and ops[-2] in fonts else None
                    gs["size"] = _num(ops[-1])
                elif op == b"BT":
                    tm = tlm = IDENTITY
                elif op == b"cm":
                    gs["ctm"] = _mul(_matrix(ops[-6:]), gs["ctm"])
                elif op == b"q":
                    saved.append(dict(gs))
                elif op == b"Q":
                    if saved:
                        gs = saved.pop()
                elif op == b"Tc":
                    gs["tc"] = _num(ops[-1])
                elif op == b"Tw":
                    gs["tw"] = _num(ops[-1])
                elif op == b"Tz":
                    gs["th"] = _num(ops[-1], 100.0) / 100.0
                elif op == b"TL":
                    gs["tl"] = _num(ops[-1])
                elif op == b"Ts":
                    gs["rise"] = _num(ops[-1])
                elif op == b"Do" and depth < 6 and ops and isinstance(xobjects, dict):
                    xo = r(xobjects.get(ops[-1]))
                    if isinstance(xo, Stream) and xo.dict.get("/Subtype") == "/Form":
                        matrix = _matrix(r(xo.dict.get("/Matrix")) or IDENTITY)
                        res = r(xo.dict.get("/Resources"))
                        self._run(self.decode(xo), res if isinstance(res, dict) else resources,
                                  _mul(matrix, gs["ctm"]), sink, depth + 1)
            except (IndexError, KeyError, TypeError, ValueError, PDFError):
                pass  # a malformed operator: skip it
            ops = []

    def _show(self, gs, tm, operand, sink):
        font, size = gs["font"], gs["size"]
        if font is None:
            return tm
        items = operand if isinstance(operand, list) else [operand]
        th, ctm, rise = gs["th"], gs["ctm"], gs["rise"]
        for item in items:
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                adv = -item / 1000.0 * size * th
                tm = (tm[0], tm[1], tm[2], tm[3], tm[4] + adv * tm[0], tm[5] + adv * tm[1])
                continue
            if not isinstance(item, bytes):
                continue
            trm = _mul(tm, ctm)
            x0 = rise * trm[2] + trm[4]
            y0 = rise * trm[3] + trm[5]
            scale = math.sqrt(abs(trm[0] * trm[3] - trm[1] * trm[2])) or 1.0
            pieces, adv = [], 0.0
            for text, w, is_space in font.decode(item):
                adv += (w * size + gs["tc"] + (gs["tw"] if is_space else 0.0)) * th
                pieces.append(text)
            tm = (tm[0], tm[1], tm[2], tm[3], tm[4] + adv * tm[0], tm[5] + adv * tm[1])
            end = _mul(tm, ctm)
            sink.add("".join(pieces), x0, y0, rise * end[2] + end[4], abs(size) * scale)
        return tm


class _Sink:
    """Collects shown strings; inserts spaces and line breaks from their positions."""

    def __init__(self):
        self.parts = []
        self.last = None

    def add(self, text, x0, y0, x1, size):
        if not text:
            return
        size = size or 1.0
        if self.last is not None:
            lx, ly, lsize = self.last
            ref = max(size, lsize)
            dy = y0 - ly
            if abs(dy) > 0.5 * ref:
                self.parts.append("\n\n" if abs(dy) > 2.2 * ref else "\n")
            else:
                dx = x0 - lx
                prev = self.parts[-1] if self.parts else ""
                shifted = abs(dy) > 0.2 * ref  # superscript or subscript: keep it apart from the word
                if (dx > 0.15 * ref or shifted) and not prev.endswith((" ", "\n")) and not text.startswith(" "):
                    self.parts.append(" ")
                elif dx < -3.0 * ref:
                    self.parts.append("\n")
        self.parts.append(text)
        self.last = (x1, y0, size)

    def text(self):
        out = "".join(self.parts)
        out = re.sub(r"[ \t ]+\n", "\n", out)
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        return out.strip()


def extract(data):
    """PDF bytes -> (list of page texts, report dict)."""
    doc = Document(data)
    pages = doc.pages()
    texts, errors = [], []
    for i, (page, resources) in enumerate(pages, 1):
        try:
            texts.append(doc.page_text(page, resources))
        except Exception as err:  # one bad page must not stop the others
            texts.append("")
            errors.append("page %d: %s" % (i, err))
    fonts = [f for f in doc.fonts.values() if f is not None]
    report = {
        "page_order": doc.page_order,
        "title": doc.info_title(),
        "fonts": len(fonts),
        "fonts_without_tounicode": sorted({f.name for f in fonts if not f.has_tounicode}),
        "unmapped_glyphs": sum(f.unmapped for f in fonts),
        "errors": errors,
    }
    return texts, report
