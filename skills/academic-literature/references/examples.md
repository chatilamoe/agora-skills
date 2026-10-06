# Examples (real outputs, 6 October 2026)

Run from a working folder; the scripts sit in `skills/academic-literature/scripts/`. Long tables are cut (`...`).

## lit_search.py: one query, three APIs

```
$ python3 lit_search.py "mobile money financial inclusion" --from-year 2018 --limit 5
  api.semanticscholar.org: HTTP 429; retrying in 2 s
  api.semanticscholar.org: HTTP 429; retrying in 5 s
  api.semanticscholar.org: HTTP 429; retrying in 10 s
  semantic scholar: relevance search is throttled for keyless users right now; falling back to /paper/search/bulk (ordered by citations)
openalex: 92826 matches, 5 returned (keyless budget left today: $0.096)
crossref: 713054 matches, 5 returned
semantic-scholar: 1151 matches, 5 returned (relevance search throttled; used bulk search ordered by citations)
13 unique works after de-duplication

#   year  cites  in   title                                                         authors               venue                     pdf  doi or url
1   2020  273    OS   MOBILE MONEY, FINANCIAL INCLUSION AND DEVELOPMENT: A REVI...  Ahmad et al.          Journal of Economic S...  pdf  10.1111/joes.12372
2   2021  0      C    Financial inclusion as transformations in financial pract...                        Financial Inclusion       -    10.1017/9781788211192.007
3   2021  56     O    Mobile Money, Financial Inclusion, and Unmet Opportunitie...  Hamdan et al.         The Journal of Develo...  pdf  10.1080/00220388.2021.1988078
4   2019  280    S    Mobile phones for financial inclusion: What explains the ...  Lashitew et al.       Research Policy           oa   10.1016/j.respol.2018.12.010
...
logged 13 records to research/sources.jsonl
```

The work found by two sources (O and S) ranks first. Crossref's top hit (row 2) is weak: Crossref ranks for bibliographic matching, not topic relevance.

## openalex.py: a series, grey literature, DOI look-ups

```
$ python3 openalex.py "cash transfers" --series wb-prwp --from-year 2022 --limit 5
filter: from_publication_date:2022-01-01,doi_starts_with:10.1596/1813-9450
OpenAlex: 73 matches; showing 5
#   year  type          cites  title                                                         authors               venue                       oa   doi or url
1   2025  report        3      Cash Is Queen: Local Economy Effects of Cash Transfers to...  Papineni et al.       World Bank Policy Resea...  pdf  10.1596/1813-9450-11112
2   2023  review        21     Is the Magic Happening? A Systematic Literature Review of...  Gassmann et al.       World Bank Policy Resea...  oa   10.1596/1813-9450-10529
3   2023  report        1      The Macroeconomic Effects of Cash Transfers: Evidence fro...  Mendes et al.         World Bank Policy Resea...  oa   10.1596/1813-9450-10652
...
OpenAlex keyless budget: this call $0.001; $0.098 of $0.1 left today (resets 00:00 UTC)
logged 5 records to research/sources.jsonl
```

```
$ python3 openalex.py "debt restructuring" --grey --from-year 2020 --limit 5
filter: from_publication_date:2020-01-01,type:report,authorships.institutions.lineage:I1334329717|I55633929|I1310145890|...
OpenAlex: 129 matches; showing 5
1   2023  report        0      Debt Reduction in Latin America and the Caribbean             Powell and Panizza                                pdf  10.18235/0005339
2   2021  report        6      The Aftermath of Debt Surges                                  Reinhart et al.       World Bank Policy Resea...  oa   10.1596/1813-9450-9771
4   2020  report        29     Debt and Financial Crises                                     Koh et al.            World Bank Policy Resea...  pdf  10.1596/1813-9450-9116
...
```

```
$ python3 openalex.py --doi 10.1596/1813-9450-9000 --doi 10.1111/joes.12372
1   2019  report        6      Impacts of PROSPERA on Enrollment, School Trajectories, a...  Behrman et al.        World Bank, Washington,...  oa   10.1596/1813-9450-9000
2   2020  article       273    MOBILE MONEY, FINANCIAL INCLUSION AND DEVELOPMENT: A REVI...  Ahmad et al.          Journal of Economic Sur...  pdf  10.1111/joes.12372
```

(Run before the series name was added to `venue`. Now PRWP 9000 shows "World Bank Policy Research Working Paper 9000".)

The line written to `research/sources.jsonl` for the second work:

```json
{"id": "openalex:W3031373263", "source": "openalex", "type": "article", "title": "MOBILE MONEY, FINANCIAL INCLUSION AND DEVELOPMENT: A REVIEW WITH REFERENCE TO AFRICAN EXPERIENCE", "authors": ["Ahmad Hassan Ahmad", "Christopher Green", "Fei Jiang"], "year": 2020, "date": "2020-05-28", "url": "https://doi.org/10.1111/joes.12372", "pdf_url": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/joes.12372", "doi": "10.1111/joes.12372", "query": "doi:10.1111/joes.12372", "accessed": "2026-10-06", "pages": null, "notes": "venue: Journal of Economic Surveys; cited_by: 273; oa: hybrid"}
```

## crossref.py: prefixes and series

```
$ python3 crossref.py "fiscal multipliers" --series imf-wp --limit 5
filter: type:journal-article,prefix:10.5089
Crossref: 1453 matches; showing 5
1   2025  journal-article  0      Fiscal Multipliers in Mongolia                                Poghosyan             IMF Working Papers            10.5089/9798229008846.001
2   2015  journal-article  3      Fiscal Multipliers in Ukraine                                 Mitra and Poghosyan   IMF Working Papers            10.5089/9781484305898.001
...
note: series imf-wp checked on the first 25 rows only
```

```
$ python3 crossref.py "cash transfers" --series wb-prwp --from-year 2018 --limit 5
filter: from-pub-date:2018,prefix:10.1596
Crossref: 127 matches; showing 5
1   2020  book             3      The Targeting Benefit Of Conditional Cash Transfers           Bergstrom and Dodds   World Bank Policy Researc...  10.1596/1813-9450-9101
3   2020  book             25     Do Cash Transfers Foster Resilience? Evidence from Rural ...  Stoeffler and Pre...  World Bank Policy Researc...  10.1596/1813-9450-9473
...
```

## s2.py: search, references

```
$ python3 s2.py --references 10.1111/joes.12372 --limit 5
Semantic Scholar /paper/{id}/references: 5 matches; showing 5
1   2018  219    Mobile Money and the Economy: A Review of the Evidence        Aron                  The World Bank Research...  -    10.1093/wbro/lky001
5   2018  2194   The Global Findex Database 2017: Measuring Financial Incl...  Demirguc-Kunt et al.                              oa   10.1596/978-1-4648-1259-0
...
$ python3 s2.py --references 10.1596/1813-9450-11008 --limit 5
no results: Semantic Scholar has no reference list for this paper (common for working papers)
```

## arxiv_search.py, core_search.py, nber_search.py

```
$ python3 arxiv_search.py "remittances" --cat econ.GN --from-year 2024 --sort submitted --limit 5
arXiv: 7 matches for ((all:remittances) AND (cat:econ.GN)) AND submittedDate:[202401010000 TO 210012312359]; showing 5
1   2026-08-22  Debt relief and remittances can offset foreign aid cuts for m...  Vismara et al.          arXiv econ.GN     https://arxiv.org/abs/2608.21843
...

$ python3 core_search.py "cash transfers" --from-year 2020 --limit 5
CORE: 3717 matches for (cash transfers) AND yearPublished>=2020; showing 5 (duplicates from several repositories removed)
1   2025  Launching Group Cash Transfers in Nepal                           Shrestha                Oxfam                       -    https://doi.org/10.21201/2025.000072
3   2024  Cash transfers and health: Evidence from Tanzania                 Kosec et al.            Oxford University Press     -    https://doi.org/10.1093/heapol/czz172
...

$ python3 nber_search.py "mobile money" --limit 5
NBER: 4698 matches (the site's own search; loose matching); page 1, showing 5
1   2011-01  Mobile Money: The Economics of M-PESA                             Jack and Suri             10.3386/w16721    https://www.nber.org/system/files/working_papers/w16721/w16721.pdf
2   2023-09  Mobile Money, Interoperability, and Financial Inclusion           Brunnermeier et al.       10.3386/w31696    https://www.nber.org/system/files/working_papers/w31696/w31696.pdf
...
```

CORE row 3 shows year 2024 for a paper whose DOI is from 2019: CORE's year can be the deposit year.

## oa_pdf.py: open-access PDFs

```
$ python3 oa_pdf.py 10.3386/w16721 10.1596/1813-9450-9000 10.1093/wbro/lky001 --check
doi                         via            version           check                   pdf_url
10.3386/w16721              openalex       publishedVersion  PDF (application/pdf)   https://doi.org/10.3386/w16721
10.1596/1813-9450-9000      -              -                 no PDF passed           none found
10.1093/wbro/lky001         -              -                 no PDF passed           none found

10.1596/1813-9450-9000: World Bank: the PDF sits on documents.worldbank.org or openknowledge.worldbank.org; use the worldbank-documents skill, or open the landing page
  landing page: https://doi.org/10.1596/1813-9450-9000
  landing page: https://hdl.handle.net/10986/32374
...
$ python3 oa_pdf.py 10.1111/joes.12372 --check --all
10.1111/joes.12372: 1 candidate links
  [openalex, publishedVersion] https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/joes.12372  -> not a PDF: text/html
```

The second run was made before the blocked-link hint was added; the script now also prints "1 open-access link(s) found, but none returned a PDF to a script...".
