# Real runs

These were recorded on 2026-10-06 from the repository root with Python 3.9.6. The same commands, run with Python 3.14.3, printed the same output. Every command on this page exited 0 except the one marked as an error case. Each one took 0 to 3 s, and the smoke test took 7 s. `[...]` marks output cut for length.

## Quick start

```
$ python3 skills/worldbank-documents/scripts/wds_search.py "financial inclusion" --country Nepal --rows 5
791 documents match "financial inclusion | country=Nepal"; showing 5, sorted by relevance
id         date        type                      country         title
32801148   2021-02-02  Implementation Completi~  Nepal           Nepal - NP: Financial sector stability DPC2
32960939   2021-03-31  Project Paper             Nepal           Disclosable Restructuring Paper - Integrated Public Financial Management Reform~
32847339   2021-02-19  Project Paper             Nepal           Disclosable Restructuring Paper - Integrated Public Financial Management Reform~
33318032   2021-07-09  Auditing Document         Nepal           Nepal - SOUTH ASIA - P164783 - Integrated Public Financial Management Reform Pr~
17816418   2013-06-06  Program Document          Nepal           Nepal - Financial Sector Stability Credit Program
wrote research/wds_financial_inclusion_country_nepal.csv (5 rows); appended 5 lines to research/sources.jsonl
next: wds_get.py ID for all fields; fetch_pdf.py wds:ID for the PDF
```

```
$ python3 skills/worldbank-documents/scripts/okr_search.py --doi 10.1596/1813-9450-11021
1 OKR item matches "doi=10.1596/1813-9450-11021"; showing 1, sorted by relevance
handle       date        type          pdf       title
10986/42650  2025-01-09  Working Pap~  0.7 MB    Financial Inclusion and Economic Development: A Review of the Data and Evidence
wrote research/okr_doi_10_1596_1813_9450_11021.csv (1 row); appended 1 line to research/sources.jsonl
next: fetch_pdf.py okr:HANDLE downloads the pdf_url logged for that item
```

```
$ python3 skills/worldbank-documents/scripts/fetch_pdf.py okr:10986/42650
saved         research/pdfs/okr_10986_42650.pdf  (666,098 bytes)  <- https://openknowledge.worldbank.org/server/api/core/bitstreams/e18fa373-7822-4fb8-beee-37dda8aa4202/content
```

The lines these three commands added to `research/sources.jsonl` (first and sixth lines shown) and to `research/pdfs/manifest.jsonl`:

```json
{"id": "wds:32801148", "source": "worldbank-documents", "type": "implementation completion report review", "title": "Nepal - NP: Financial sector stability DPC2", "authors": ["IEG Review Team"], "year": 2021, "date": "2021-02-02", "url": "https://documents.worldbank.org/curated/en/561371612292643120", "pdf_url": "https://documents.worldbank.org/curated/en/561371612292643120/pdf/Nepal-NP-Financial-sector-stability-DPC2.pdf", "doi": null, "query": "financial inclusion | country=Nepal", "accessed": "2026-10-06", "pages": null, "notes": "Implementation Completion Report Review; Nepal; English; report no. ICRR0022192"}
{"id": "okr:10986/42650", "source": "worldbank-documents", "type": "working paper", "title": "Financial Inclusion and Economic Development: A Review of the Data and Evidence", "authors": ["Ansar, Saniya", "Klapper, Leora", "Singer, Dorothe"], "year": 2025, "date": "2025-01-09", "url": "https://hdl.handle.net/10986/42650", "pdf_url": "https://openknowledge.worldbank.org/server/api/core/bitstreams/e18fa373-7822-4fb8-beee-37dda8aa4202/content", "doi": "10.1596/1813-9450-11021", "query": "doi=10.1596/1813-9450-11021", "accessed": "2026-10-06", "pages": null, "notes": "Policy Research Working Paper; Publications & Research; series: Policy Research Working Paper; 11021; same document as wds:34443889 in Documents & Reports"}
```
```json
{"id": "okr:10986/42650", "file": "research/pdfs/okr_10986_42650.pdf", "url": "https://openknowledge.worldbank.org/server/api/core/bitstreams/e18fa373-7822-4fb8-beee-37dda8aa4202/content", "final_url": "https://openknowledge.worldbank.org/server/api/core/bitstreams/e18fa373-7822-4fb8-beee-37dda8aa4202/content", "bytes": 666098, "content_type": "application/pdf;charset=UTF-8", "accessed": "2026-10-06"}
```

## wds_search.py

```
$ python3 skills/worldbank-documents/scripts/wds_search.py "global findex" --doctype "Policy Research Working Paper" --from 2020 --sort newest --rows 5
5 documents match "global findex | doctype=Policy Research Working Paper | from=2020-01-01 | to=2026-10-06"; showing 5, sorted by newest
id         date        type                      country         title
40088404   2026-02-24  Policy Research Working~  World           Formalizing Savings
34016763   2023-03-07  Policy Research Working~  World           The Importance of Financial Education for the Effective Use of Formal Financial~
33986030   2023-01-24  Policy Research Working~  World           Gendered Laws and Women’s Financial Inclusion
32994173   2021-04-13  Policy Research Working~  World           Social Transfer Multipliers in Developed and Emerging Countries : The Role of H~
31935784   2020-04-07  Policy Research Working~  Sri Lanka       Financial Inclusion and Inclusive Growth : What Does It Mean for Sri Lanka?
wrote research/wds_global_findex_doctype_policy_research_working_paper_from_2020_01_01_to.csv (5 rows); appended 5 lines to research/sources.jsonl
next: wds_get.py ID for all fields; fetch_pdf.py wds:ID for the PDF
```

Working papers carry their DOI. This is the line logged for the first hit:

```json
{"id": "wds:40088404", "source": "worldbank-documents", "type": "policy research working paper", "title": "Formalizing Savings", "authors": ["Melecky, Martin", "Singer, Dorothe"], "year": 2026, "date": "2026-02-24", "url": "https://documents.worldbank.org/curated/en/099634102242631882", "pdf_url": "https://documents.worldbank.org/curated/en/099634102242631882/pdf/IDU-a737d708-a5eb-4399-8040-6a0705c3dafb.pdf", "doi": "10.1596/1813-9450-11322", "query": "global findex | doctype=Policy Research Working Paper | from=2020-01-01 | to=2026-10-06", "accessed": "2026-10-06", "pages": null, "notes": "Policy Research Working Paper; World; English; report no. WPS11322"}
```

```
$ python3 skills/worldbank-documents/scripts/wds_search.py --project P508961 --sort newest --rows 5
15 documents match "project=P508961"; showing 5, sorted by newest
id         date        type                      country         title
40110002   2026-06-17  Letter                    Nepal           Official Documents- Corrigendum correcting Schedule 2, Section I.C.1 to the Fin~
40107040   2026-06-04  Project Agreement         Nepal           Official Documents- Project Agreement with Deposit and Credit Guarantee Fund fo~
40103924   2026-05-19  Implementation Status a~  Nepal           Disclosable Version of the ISR - Sustainable and Inclusive Finance - P508961 - ~
40099092   2026-04-28  Project Agreement         Nepal           Official Documents- Project Agreement for Credit 7958-NP.pdf
40098870   2026-04-22  Financing Agreement       Nepal           Official Documents- Financing Agreement for Credit 7958-NP.pdf
wrote research/wds_project_p508961.csv (5 rows); appended 5 lines to research/sources.jsonl
next: wds_get.py ID for all fields; fetch_pdf.py wds:ID for the PDF
```

```
$ python3 skills/worldbank-documents/scripts/wds_search.py "financial inclusion" --facets count_exact,docty_exact,lang_exact,majdocty_exact,admreg_exact
58352 documents match; top facet values (pass a value back as a filter):

count_exact:
     4699  World
     2819  India
     1523  Brazil
[...]
      970  Viet Nam
[...]
      791  Nepal
[...]
      614  Congo, Democratic Republic of
[...]
      599  Egypt, Arab Republic of

docty_exact:
     8378  Procurement Plan
     4634  Implementation Status and Results Report
     4493  Auditing Document
[...]
      510  Publication
      509  Project Agreement

lang_exact:
    54512  English
     1239  French
      889  Spanish
[...]

majdocty_exact:
    44099  Project Documents
     9849  Publications & Research
     1667  Economic & Sector Work
     1364  Board Documents
      708  Publications
      609  Country Focus
       53
        1  Analytic & Advisory Work

admreg_exact:
     9710  Western and Central Africa
     9255  Eastern and Southern Africa
     8398  Latin America and Caribbean
     6696  East Asia and Pacific
     6659  Europe and Central Asia
     5978  Middle East, North Africa, Afghanistan, and Pakistan
     5711  South Asia
     4814  Other
     1046  Africa
```

## wds_get.py

```
$ python3 skills/worldbank-documents/scripts/wds_get.py 31476985
wds:31476985
  title         Financial Inclusion in the Maldives Findex 2018 Survey
  date          2019-10-14
  doctype       Report
  major_doctype Publications & Research
  country       Maldives
  region        South Asia
  language      English
  report_no     142670
  volume        1
  project_id    P155693
  guid          570891571303596376
  url           https://documents.worldbank.org/curated/en/570891571303596376
  pdf_url       https://documents.worldbank.org/curated/en/570891571303596376/pdf/Financial-Inclusion-in-the-Maldives-Findex-2018-Survey.pdf
  txt_url       https://documents.worldbank.org/curated/en/570891571303596376/text/Financial-Inclusion-in-the-Maldives-Findex-2018-Survey.txt
  abstract      In this note authors explore the many ways that adults in the Maldives are using digital payment services [...]
  other fields:
    owner               EFI-SAR-FCI-Finance-1 (ESAF1)
    projn               MV-Maldives #C001 Enabling a Non-Bank Mobile Money Solution -- P155693
    subsc               FY17 - Other Non-bank Financial Institutions
    trustfund           TF0A1308 - Maldives #C001 Enabling a Non-Bank Mobile Money Solution
    theme               FY17 - Payment & markets infrastructure,FY17 - Financial Infrastructure and Access
    prdln               Advisory Services & Analytics
    [...]
    disclosure_date     2019-10-17T09:09:50Z
    disclstat           Disclosed
    available_in        English

saved 1 metadata file under research/meta; appended 1 line to research/sources.jsonl
```

One report number, five documents (the titles come from `docna`):

```
$ python3 skills/worldbank-documents/scripts/wds_get.py --report 173780
wds:33863209
  title         The Global Findex Database 2021 : Financial Inclusion, Digital Payments, and Resilience in the Age of COVID-19
  [...]
  doi           10.1596/978-1-4648-1897-4
  authors       Demirguc-Kunt, Asli; Klapper, Leora; Singer, Dorothe; Ansar, Saniya
  [...]
wds:33863235
  title         The Global Findex Database 2021 : Financial Inclusion, Digital Payments, and Resilience in the Age of COVID-19 - Chapter 3 : Financial Well-Being
wds:33863284
  title         The Global Findex Database 2021 : Financial Inclusion, Digital Payments, and Resilience in the Age of COVID-19 - Executive Summary
wds:33863219
  title         The Global Findex Database 2021 : Financial Inclusion, Digital Payments, and Resilience in the Age of COVID-19 - Chapter 1 : Financial Access
wds:33863225
  title         The Global Findex Database 2021 : Financial Inclusion, Digital Payments, and Resilience in the Age of COVID-19 - Chapter 2 : Use of Financial Services
[...]
saved 5 metadata files under research/meta; appended 5 lines to research/sources.jsonl
```

## okr_search.py

```
$ python3 skills/worldbank-documents/scripts/okr_search.py "global findex" --size 5
37 OKR items match "global findex"; showing 5, sorted by relevance
handle       date        type          pdf       title
10986/43438  2025-07-16  Publication   14.3 MB   The Global Findex Database 2025: Connectivity and Financial Inclusion in the Di~
10986/37578  2022-06-29  Publication   15.3 MB   The Global Findex Database 2021: Financial Inclusion, Digital Payments, and Res~
10986/29510  2018-04-19  Book          13.6 MB   Global Findex Database 2017: Measuring Financial Inclusion and the Fintech Revo~
10986/21865  2015-04     Working Pap~  7.5 MB    The Global Findex Database 2014: Measuring Financial Inclusion around the World
10986/6042   2012-04     Policy Rese~  4.9 MB    Measuring Financial Inclusion : The Global Findex Database
wrote research/okr_global_findex.csv (5 rows); appended 5 lines to research/sources.jsonl
next: fetch_pdf.py okr:HANDLE downloads the pdf_url logged for that item
```

```
$ python3 skills/worldbank-documents/scripts/okr_search.py mobile money --doctype "Policy Research Working Paper" --from 2020 --to 2025 --size 3
7 OKR items match "mobile money | doctype=Policy Research Working Paper | from=2020 | to=2025"; showing 3, sorted by relevance
handle       date        type          pdf       title
10986/43814  2025-10-07  Working Pap~  0.6 MB    The Impact of a Mobile Money Levy on Household Welfare: Evidence from Tanzania
10986/42650  2025-01-09  Working Pap~  0.7 MB    Financial Inclusion and Economic Development: A Review of the Data and Evidence
10986/43153  2025-05-02  Working Pap~  2.2 MB    Mitigating the Impact of Household Expropriation on Female Entrepreneurship: Ex~
wrote research/okr_mobile_money_doctype_policy_research_working_paper_from_2020_to_2025.csv (3 rows); appended 3 lines to research/sources.jsonl
next: fetch_pdf.py okr:HANDLE downloads the pdf_url logged for that item
```

The five files of *The Global Findex Database 2025*. This is the `pdfs` list from `okr_search.py --handle 10986/43438 --json`, one line per file: name, description, language, bytes, sequence:

```
pdf: 9781464822049.pdf Full Report en 14309364 9
pdf: 9781464822049_VisualSummary.pdf Visual Executive Summary en 2871960 10
pdf: 33838_English.pdf Executive Summary en 5624729 11
pdf: 33840_Spanish ES.pdf Spanish Executive Summary es 5521709 12
pdf: 33839_rev.pdf French Executive Summary fr 3577613 13
```

## projects_search.py

```
$ python3 skills/worldbank-documents/scripts/projects_search.py --country NP --status active --rows 5
25 projects match "country=NP | status=Active"; showing 5, sorted by approval date (newest)
id       approved    status    US$ m     country       name
P512377  2026-03-13  Active    85.0      Nepal         Greater Lumbini Area Development Project
P506527  2026-03-05  Active    52.0      Nepal         Nepal Clean Air and Prosperity Project
P511767  2026-02-09  Active    50.0      Nepal         Nepal Digital Transformation
P508961  2026-01-29  Active    95.0      Nepal         Sustainable and Inclusive Finance
P505226  2025-08-06  Active    10.0      Nepal         Public Financial Management for Development Effectiveness Project
wrote research/projects_country_np_status_active.csv (5 rows); appended 5 lines to research/sources.jsonl
next: wds_search.py --project ID lists a project's documents
```

P505226 is trust-funded: it has no `totalamt`, so the US$10.0m comes from `curr_total_commitment`.

```
$ python3 skills/worldbank-documents/scripts/projects_search.py "financial inclusion" --country NP --rows 5
25 projects match "financial inclusion | country=NP"; showing 5, sorted by approval date (newest)
id       approved    status    US$ m     country       name
P511767  2026-02-09  Active    50.0      Nepal         Nepal Digital Transformation
P508961  2026-01-29  Active    95.0      Nepal         Sustainable and Inclusive Finance
P178531  2024-05-06  Closed    80.0      Nepal         Nepal Finance for Growth DPC (3 of 3)
P176881  2022-03-24  Closed    150.0     Nepal         Nepal Second Finance for Growth Development Policy Financing
P173982  2021-06-16  Closed    150.0     Nepal         Nepal Programmatic Fiscal Policy for Growth, Recovery and Resilience ~
wrote research/projects_financial_inclusion_country_np.csv (5 rows); appended 5 lines to research/sources.jsonl
next: wds_search.py --project ID lists a project's documents
```

The first two rows of the CSV (cut at the right):

```
id,name,country,region,status,approval_date,closing_date,fiscal_year,commitment_usd,current_commitment_usd,ida_usd,ibrd_usd,grant_usd,project_cost_usd,financing,major_sectors,sectors,themes,pdo,borrower,implementing_agency,url
P512377,Greater Lumbini Area Development Project,Nepal,South Asia,Active,2026-03-13,2031-04-30,2026,85000000,85000000,85000000,0,0,85000000,IDA,"Public Administration; Industry, Trade and Services","Sub-National Government (19%); [...]
```

## fetch_pdf.py

```
$ python3 skills/worldbank-documents/scripts/fetch_pdf.py wds:31476985
saved         research/pdfs/wds_31476985.pdf  (231,929 bytes)  <- https://documents.worldbank.org/curated/en/570891571303596376/pdf/Financial-Inclusion-in-the-Maldives-Findex-2018-Survey.pdf
```

Run again, the file is not fetched twice:

```
$ python3 skills/worldbank-documents/scripts/fetch_pdf.py wds:31476985
already there research/pdfs/wds_31476985.pdf  (231,929 bytes)  <- https://documents.worldbank.org/curated/en/570891571303596376/pdf/Financial-Inclusion-in-the-Maldives-Findex-2018-Survey.pdf
```

Error case (exit 1):

```
$ python3 skills/worldbank-documents/scripts/fetch_pdf.py okr:10986/43438 --max-mb 2 project:P508961 wds:00000001
3 of 3 failed
FAILED  okr:10986/43438: larger than --max-mb 2 (2.0 MB or more); not saved
FAILED  project:P508961: no pdf_url logged for project:P508961 (projects have no PDF; list their documents with wds_search.py --project ID)
FAILED  wds:00000001: wds:00000001 is not in sources.jsonl; run wds_search.py, wds_get.py or okr_search.py first, or pass the PDF URL
```

## A page-level citation, end to end

1. `wds_get.py 31476985` and `fetch_pdf.py wds:31476985` (above) saved `research/pdfs/wds_31476985.pdf`. The file has no printed page numbers.
2. PDF page 3 (page index, 1 = the cover) reads: "In the Maldives 80 percent of adults have an account".
3. Cross-check against the data: `wdi_fetch.py FX.OWN.TOTL.ZS --country MDV --date 2017` (worldbank-indicators) returns 79.55 for 2017, which rounds to the 80 percent on the page.
4. Citation:

> In 2017, 80 percent of adults in the Maldives had an account (Financial Inclusion in the Maldives Findex 2018 Survey, 2019, p. 3, https://documents.worldbank.org/curated/en/570891571303596376).

## Smoke test

```
$ python3 skills/worldbank-documents/tests/smoke.py
OK    wds search      search.worldbank.org/api/v3/wds?qterm=  (89 documents for 'findex')
OK    wds by id       search.worldbank.org/api/v3/wds?id=  (Financial Inclusion in the Maldives Findex 2018 Survey)
OK    wds pdf         documents.worldbank.org/curated/.../pdf/  (first 1 KB is a PDF)
OK    okr search      openknowledge.worldbank.org/server/api/discover/search/objects  (37 items for 'global findex')
OK    okr files       .../server/api/core/items/{uuid}/bundles?embed=bitstreams  (5 files in ORIGINAL)
OK    okr pdf         .../server/api/core/bitstreams/{uuid}/content  (first 1 KB is a PDF)
OK    projects        search.worldbank.org/api/v3/projects  (281 projects in Nepal)
```

## What a network failure looks like

This was simulated against a local port where nothing is listening, with the waits shortened for the test. The real waits are 2, 5 and 10 s.

```
  (URLError: [Errno 61] Connection refused; retrying in 0.1 s)
  (URLError: [Errno 61] Connection refused; retrying in 0.1 s)
  (URLError: [Errno 61] Connection refused; retrying in 0.1 s)
error: gave up after 4 tries (URLError: [Errno 61] Connection refused): http://127.0.0.1:9/api/v3/wds?qterm=findex&[...]
```

Exit code 1; nothing written. During the recorded runs one live call timed out after 30 s and succeeded on the retry: `(TimeoutError: The read operation timed out; retrying in 2 s)`.
