# The standard-library extractor (`scripts/_pdf_stdlib.py`)

Route 3 of `pdf_text.py`. It is used when neither `pdftotext` nor `pypdf` is available, or with `--engine stdlib`.

## What it does

1. Scans the file for `N G obj ... endobj`, skipping stream bodies. It unpacks compressed object streams (`/Type /ObjStm`) and reads the trailer (classic or cross-reference stream) for `/Root`, `/Info` and `/Encrypt`.
2. Walks the page tree from the catalog to list pages in order. Without a usable tree it falls back to object order, and `pages.json` says so.
3. Decodes content streams: FlateDecode (`zlib`, with PNG predictors), LZWDecode, ASCII85Decode, ASCIIHexDecode, RunLengthDecode. Image filters are never needed for text.
4. Interprets the text operators `Tj`, `TJ`, `'` and `"`, and the positioning operators `Td`, `TD`, `Tm`, `T*`, `cm`, `q`/`Q`. It follows Form XObjects (`Do`) up to six levels deep and skips inline images.
5. Maps bytes to Unicode with the font's `/ToUnicode` CMap (`bfchar`, `bfrange`, code space ranges). Without one it uses `/Encoding` with `/Differences` (glyph names through an Adobe Glyph List subset, `uniXXXX`, and accented-letter names). It falls back to WinAnsi for TrueType and StandardEncoding otherwise.
6. Uses glyph widths (`/Widths`, CID `/W` and `/DW`, Helvetica widths when a font has none) to place each string. A space goes in when the gap exceeds 0.15 em or the baseline shifts (superscripts). A line break goes in when the baseline moves by more than half the font size, a blank line on a larger jump.

## Results on three World Bank PDFs (6 October 2026)

Compared word by word with `pdftotext` (reading order) as the reference. "Found" means 40 sentences sampled at random from the reference text, searched with `cite_find.py` in each route's output: the tier that matched, and whether the page was right.

| PDF | Pages | Time | Recall | Precision | stdlib: found on right page | pypdf: found on right page | pdftotext auto: found on right page |
|---|---|---|---|---|---|---|---|
| WPS9560, Mobile Internet Adoption in West Africa (2021) | 33 | 0.7 s | 99.8% | 99.6% | 38 exact/normalized + 2 fuzzy | 26 + 9 fuzzy (5 page errors) | 40 exact/normalized |
| WPS5664, Mobile Banking and Financial Inclusion (2011) | 34 | 0.2 s | 99.8% | 99.4% | 38 + 2 fuzzy | 30 + 10 fuzzy | 39 + 1 fuzzy |
| Brief, Financial Inclusion, Women, and Building Back Better (2021, two columns) | 6 | 0.1 s | 99.9% | 99.8% | 38 + 2 fuzzy | 38 + 2 fuzzy | 40 |

(The pypdf and stdlib "found" counts for WPS9560 come from the run before the repeated-sentence fix in `cite_find.py`. After the fix, stdlib on WPS9560 gave 38 exact or normalized and 2 fuzzy, all on the right page.)

In the same test, `pdftotext -layout` without the two-column switch (`--layout on`) found only 10 of the brief's 40 sentences exactly or normalized; 25 were not found. That is why `--layout auto` uses reading order on two-column pages.

Where the stdlib text differs from pdftotext:
- Superscript markers are kept apart ("Castelán a", "Kenya 3"); pdftotext glues them ("Kenya3").
- Hyphenated compounds at line ends are kept ("M-\nPesa"); pdftotext joins them ("MPesa"). `cite_find.py` normalises both.
- Math italic symbols (Cambria Math) come out garbled in both.
- The "Public Disclosure Authorized" watermark on the cover is repeated more often.

## Limits

- No OCR: scanned pages have no text operators and come out empty.
- No decryption: encrypted PDFs are refused, even those with only "no copying" flags. pdftotext and pypdf open them.
- Fonts without a ToUnicode map and without a standard encoding (some Type3 bitmap fonts, CJK CID fonts) give wrong or missing characters. `pages.json` (`stdlib_report`) lists fonts without ToUnicode and counts unmapped glyphs.
- Spaces and line breaks are inferred from positions: words can run together or split, especially with unusual spacing or rotated text.
- Reading order is the content-stream order. It was column by column in these tests, but generators can draw text in any order. It works on simple single-column PDFs; two-column layouts may interleave. Prefer pdftotext or pypdf when present.
