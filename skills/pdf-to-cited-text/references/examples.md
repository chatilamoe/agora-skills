# Examples (real outputs, 6 October 2026)

```
$ python3 fetch_pdf.py https://documents1.worldbank.org/curated/en/545241624880584363/pdf/Financial-Inclusion-Women-and-Building-Back-Better.pdf --id brief-161098
saved research/pdfs/brief-161098.pdf (0.2 MB, sha256 50d1468c3b67...)
next: python3 pdf_text.py research/pdfs/brief-161098.pdf

$ python3 pdf_text.py research/pdfs/brief-161098.pdf --title "Financial Inclusion, Women, and Building Back Better" --year 2021
engine: pdftotext [pdftotext version 26.04.0, -layout; reading order on 4 two-column page(s)]
pages: 6 written to research/text/brief-161098/ (page-001.txt ... page-006.txt)
characters: 27691 in total; empty pages: none
source: pdf:brief161098 (Financial Inclusion, Women, and Building Back Better, 2021)

$ python3 pdf_text.py research/pdfs/wps9560.pdf --engine stdlib --id wps9560-stdlib
engine: stdlib [standard library (zlib + Tj/TJ operators)]
pages: 33 written to research/text/wps9560-stdlib/ (page-001.txt ... page-033.txt)
characters: 126480 in total; empty pages: none
source: pdf:wps9560 (Mobile Internet Adoption in West Africa, 2021)
```

`cite_find.py`: a quote over a line break (normalized tier), a key phrase on many pages, and a claim that is not in the text.

```
$ python3 cite_find.py wps9560 "the probability of using the internet is higher among individuals who are younger, more well educated, and wealthier"
wps9560 (pdf:wps9560, 33 pages, engine pdftotext): NORMALIZED
  p. 7  normalized
    "A study in rural Mexico shows that the probability of using the internet is higher among individuals who are younger, more well educated, and wealthier and who have knowledge of digital technologies, live in the northern (richer) part of the country, and have social networks (Martínez-Domínguez and Mora-Rivera 2020)."
    cite: (Mobile Internet Adoption in West Africa, 2021, p. 7, https://documents1.worldbank.org/curated/en/878041614611542135/pdf/Mobile-Internet-Adoption-in-West-Africa.pdf#page=7)

$ python3 cite_find.py wps9560 "WAEMU countries" --max 3
wps9560 (pdf:wps9560, 33 pages, engine pdftotext): EXACT
  found 22 times on 10 pages: p. 5 (4), p. 6 (2), p. 7 (1), p. 12 (2), p. 13 (5), p. 16 (2), p. 17 (1), p. 18 (2), p. 19 (1), p. 20 (2)
  p. 5  exact
    "Thus, the average price of data-only mobile broadband stood at US$8.50 in WAEMU countries (in nominal US dollars), compared with US$5.50 in East Africa (ITU 2020)."
  ...

$ python3 cite_find.py wps9560 "the probability of using internet is higher for people who are younger, better educated and wealthier"
wps9560 (pdf:wps9560, 33 pages, engine pdftotext): FUZZY
  p. 7  fuzzy (score 0.81: wording differs; quote the page as printed)

$ python3 cite_find.py wps9560 "mobile money increased household consumption by 30 percent"
wps9560 (pdf:wps9560, 33 pages, engine pdftotext): NONE
NOT FOUND: 'mobile money increased household consumption by 30 percent' in wps9560 (33 pages). Do not make this claim from these texts.
```

`verify_claims.py` on four claims: claim 2 cites the wrong page, and claim 4 is not in the text (exit code 1).

```
$ python3 verify_claims.py research/claims.jsonl
1. FOUND      cited p. 7     found p. 7           Studies of internet use in rural Mexico find younger, better educated and wealthier people
2. OTHER PAGE cited p. 6     found p. 5           Five of the eight WAEMU countries are in the bottom decile of internet penetration.
3. FOUND      cited p. 3     found p. 3           Guatemala paid relief through codes sent by text message.
4. NOT FOUND  cited p. 12    found -              Mobile money raised household consumption by 30 percent.
2 of 4 claims FOUND on the cited page
```

(cite: lines cut.) The claims file, one JSON object per line:

```json
{"claim": "Guatemala paid relief through codes sent by text message.", "quote": "Eligible participants then receive text messages with payment codes", "source_id": "pdf:brief161098", "page": 3, "type": "finding"}
```
