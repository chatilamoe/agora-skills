# Fields, filters and real responses

Everything below was checked against the live APIs on 2026-10-06. "Works" means the filter changed the result count the way it should. JSON excerpts are real replies, trimmed: long strings cut with `...` and lists shortened.

## 1. Documents & Reports (WDS) v3

`GET https://search.worldbank.org/api/v3/wds?format=json&...`

### Parameters

| Parameter | Example | Status |
|---|---|---|
| `qterm` | `findex nepal`, `findex OR nepal`, `"financial inclusion"` | works. Words are ANDed (`findex nepal` 1 hit, `findex OR nepal` 6,898); a quoted phrase is a phrase (`financial inclusion` 58,352, quoted 11,936) |
| `rows`, `os` | `rows=20&os=40` | works. `os` is the offset, and the reply's `page` = os/rows + 1. `rows=1000` is accepted; scripts use at most 100. `rows=abc` gives HTTP 400 |
| `fl` | `fl=id,display_title,docdt,authr` | works, but is not strict: `id`, `abstracts` and `entityids` always come back. **Authors: request `authr`**. `fl=authors` returns no authors |
| `count_exact` | `Nepal`, `Nepal^India` | works. Country name, case-sensitive (`nepal` gives 0). `^` = OR |
| `docty_exact` | `Policy Research Working Paper`, `Brief^Publication` | works |
| `majdocty_exact` | `Publications & Research`, `Project Documents` | works |
| `lang_exact` | `English`, `French` | works |
| `admreg_exact` | `South Asia` | works (Bank region) |
| `projectid` | `P508961` | works: the documents of one project |
| `id` | `31476985` | works: one document |
| `guid` | `570891571303596376` | works: the number in documents.worldbank.org URLs |
| `repnb` | `WPS6630`, `173780` | works: report number; one report can be several documents |
| `strdate` + `enddate` | `strdate=2021-01-01&enddate=2026-12-31` | works. **`strdate` alone returns only that calendar year** (2021: 3 hits vs 22 with an end date) |
| `srt` + `order` | `srt=docdt&order=desc` | works. `order=asc` puts junk year-1 dates first |
| `fct` | `rows=0&fct=docty_exact,count_exact` | works: value counts per field, under `documents.facets` |
| `docid`, `title` | | ignored: `docid` gives 0, `title` returns everything |

### Response shape

`{"rows", "os", "page", "total", "documents": {"D<id>": {...}, ..., "facets": {...}}}`. The documents come in ranking order, keyed `D` + id. The `facets` key sits beside them inside `documents`.

```
GET https://search.worldbank.org/api/v3/wds?format=json&qterm=post%20office&docty_exact=Policy%20Research%20Working%20Paper&rows=1&fl=id,display_title,docdt,docty,majdocty,count,lang,authr,repnb,volnb,guid,keywd,abstracts,pdfurl,txturl,url,colti,projectid
```
```json
{"rows": 1, "os": 0, "page": 1, "total": 44,
 "documents": {
  "D18419181": {
   "id": "18419181",
   "authors": {"0": {"author": "Anson, Jose"}, "1": {"author": "Berthaud, Alexandre"},
               "2": {"author": "Klapper, Leora"}, "3": {"author": "Singer, Dorothe"}},
   "count": "World", "docty": "Policy Research Working Paper", "lang": "English",
   "entityids": {"entityid": "000158349_20131021084620"},
   "repnb": "WPS6630", "docdt": "2013-10-01T04:00:00Z",
   "keywd": {"0": {"keywd": "Finance & Private Sector Development"}, "1": {"keywd": "summary statistic"}, "2": {"keywd": "account ownership"}},
   "volnb": "1", "majdocty": "Publications & Research",
   "abstracts": {"cdata!": "Given their widespread presence in rural and poor areas, post offices can play a leading role in advancing fin..."},
   "colti": "Policy Research working paper ; no. WPS 6630",
   "display_title": "Financial inclusion and the role of the post office",
   "pdfurl": "http://documents.worldbank.org/curated/en/680321468163464611/pdf/WPS6630.pdf",
   "txturl": "http://documents.worldbank.org/curated/en/680321468163464611/text/WPS6630.txt",
   "projectid": "P123365", "guid": "680321468163464611",
   "url": "http://documents.worldbank.org/curated/en/680321468163464611"},
  "facets": {}}}
```

Facets (`rows=0&fct=lang_exact`, query `financial inclusion`):

```json
{"total": 58352, "documents": {"facets": {"lang_exact": {
  "0": {"count": 54512, "name": "English", "label": "English"},
  "1": {"count": 1239, "name": "French", "label": "French"},
  "2": {"count": 889, "name": "Spanish", "label": "Spanish"}}}}}
```

### Fields

| Field | Meaning | Notes |
|---|---|---|
| `id` | document id | cite as `wds:<id>` |
| `display_title` | title | missing in some non-English search hits; then use `docna` or `repnme` |
| `docna` | `{"0": {"docna": title}}` | carries " - Chapter 3 : ..." when a report is split into files |
| `repnme` | `{"repnme": title}` | report name |
| `docdt` | document date, `2013-10-01T04:00:00Z` | some junk: year 1, or future dates on agreements |
| `docty` / `majdocty` | document type / major type | e.g. `Policy Research Working Paper` / `Publications & Research` |
| `count` | country name | `World` for global work |
| `admreg` | Bank region | `Other` for global work |
| `lang`, `available_in` | language(s) | |
| `authors` | `{"0": {"author": "Surname, Given"}}` | request with `fl=authr` |
| `repnb`, `volnb`, `totvolnb` | report number, volume, number of volumes | |
| `colti` | series, e.g. `Policy Research working paper ; no. WPS 6630` | |
| `keywd` | `{"0": {"keywd": ...}}` | some values have a leading space |
| `abstracts` | `{"cdata!": text}` | |
| `projectid`, `projn` | project id and name | ASA products too |
| `guid` | number in the document URL | |
| `dois`, `isbn` | DOI and ISBN(s), as strings: `10.1596/978-1-4648-1897-4`, `978-1-4648-1897-4; 978-1-4648-1898-1` | publications only; chapters share the book's DOI |
| `url`, `pdfurl`, `txturl` | document page, PDF, plain text | given as `http://`; both schemes work, and the scripts store `https://` |
| also | `owner`, `trustfund`, `theme`, `majtheme`, `subtopic`, `teratopic`, `sectr`, `prdln`, `disclosure_date`, `disclstat`, `seccl`, `versiontyp`, `geo_regions` | returned when `fl` is omitted (`wds_get.py`) |

Document types with the most hits for `financial inclusion`:

- Procurement Plan 8,378;
- Implementation Status and Results Report 4,634;
- Auditing Document 4,493;
- Project Information Document 2,860;
- Working Paper 2,772;
- Project Appraisal Document 2,067;
- Implementation Completion and Results Report 1,943;
- Report 1,907;
- Brief 1,482;
- Publication 510;
- Policy Research Working Paper 431.

### PDF hosting

`http://documents.worldbank.org/curated/en/<guid>/pdf/<name>.pdf` follows this redirect chain:

1. 302 to `https://documents.worldbank.org/...`;
2. 302 to `http://documents1.worldbank.org/...`;
3. 301 to `https://documents1.worldbank.org/...`;
4. 200, `application/pdf`.

A `HEAD` request on the same URL ends in **404**, so use `GET`. `Range` headers are ignored: the whole file comes back with 200. The OKR content endpoint does honour `Range` and answers 206.

## 2. Open Knowledge Repository, DSpace 7 REST

Base: `https://openknowledge.worldbank.org/server/api`. Send `Accept: application/json`.

| Endpoint | Use |
|---|---|
| `/discover/search/objects?query=...&page=0&size=10` | search; add `embed=bundles/bitstreams` to get each item's files in the same reply |
| `/discover/facets/{name}?query=...&size=30` | value counts: `doctype`, `country`, `author`, `dateIssued`, `topic`, `subject`, `region`, `entityType`, `supportedlanguage` |
| `/discover/search` | the list of filters and sort options |
| `/core/items/{uuid}/bundles?embed=bitstreams` | an item's files (bundles ORIGINAL, LICENSE, THUMBNAIL) |
| `/core/bundles/{uuid}/primaryBitstream` | the bundle's primary file, often empty |
| `/core/bitstreams/{uuid}/content` | the file itself (`Content-Disposition: attachment`; Range works) |
| `/pid/find?id=10986/42650` | handle to item: 302 to `/core/items/{uuid}` |

### Search parameters

| Parameter | Example | Status |
|---|---|---|
| `query` | `global findex` | works. Field queries work too: `dc.identifier.doi:"10.1596/1813-9450-11021" OR okr.identifier.doi:"..."`, `handle:"10986/43438"` |
| `f.entityType` | `Publication,equals` | works. Without it, Person (1,319), Series (11) and Journal (4) records mix in |
| `f.country` | `Nepal,equals` | works (`financial inclusion`: 1,970 to 19) |
| `f.doctype` | `Policy Research Working Paper,equals` | works (64) |
| `f.dateIssued` | `[2023 TO 2025],equals` | works (310) |
| `f.author` | `Klapper,contains` | works (23). `Klapper, Leora,equals` gives 0 |
| `sort` | `dc.date.issued,DESC` | works. Also `score`, `dc.title`, `dc.date.accessioned` |
| `page`, `size` | `page=0&size=10` | 0-based pages. Reply: `page.totalElements`, `page.totalPages` |
| `embed` | `bundles/bitstreams` | about 23 KB extra per item, about 50 KB per item in all (10 items: 258 KB without, 493 KB with) |

### Item metadata

Values are lists of `{"value": ...}`.

| Field | Meaning |
|---|---|
| `dc.title`, `dc.title.subtitle` | title and subtitle (`okr.crossref.title` has both joined) |
| `dc.contributor.author` | authors, "Surname, Given" |
| `dc.date.issued` | issue date: `2025-01-09`, `2015-04` or `2012` |
| `dc.description.abstract` | abstract (with newlines and indentation) |
| `dc.identifier.doi` / `okr.identifier.doi` | DOI: books `10.1596/978-...`, PRWPs `10.1596/1813-9450-NNNNN` |
| `dc.identifier.uri` | handle link `https://hdl.handle.net/10986/...` (persistent) |
| `dc.type` | `Working Paper`, `Book`, `Report`, `Journal Article`... (sometimes empty) |
| `okr.doctype` | `Policy Research Working Paper`, `Publications & Research::Publication`... |
| `dc.relation.ispartofseries` | `Policy Research Working Paper; 11021` |
| `okr.region.country`, `okr.region.geographical` | countries, regions |
| `okr.identifier.report` | report number, e.g. `WPS11021` |
| `okr.identifier.externaldocumentum` | the WDS id of the same document |
| `okr.pdfurl`, `okr.docurl`, `okr.guid` | the Documents & Reports copy |
| `dc.rights` | licence, usually `CC BY 3.0 IGO` |

### Real reply

DOI lookup with files (`embed=bundles/bitstreams`), trimmed:

```
GET https://openknowledge.worldbank.org/server/api/discover/search/objects?query=dc.identifier.doi:%2210.1596%2F1813-9450-11021%22&size=1&f.entityType=Publication,equals&embed=bundles%2Fbitstreams
```
```json
{"_embedded": {"searchResult": {
  "page": {"number": 0, "size": 1, "totalPages": 1, "totalElements": 1},
  "_embedded": {"objects": [{"_embedded": {"indexableObject": {
    "uuid": "37271e00-4b20-4b90-b81f-5f5cd4280f4e", "handle": "10986/42650",
    "name": "Financial Inclusion and Economic Development", "entityType": "Publication",
    "metadata": {
      "dc.contributor.author": [{"value": "Ansar, Saniya"}, {"value": "Klapper, Leora"}, {"value": "Singer, Dorothe"}],
      "dc.date.issued": [{"value": "2025-01-09"}],
      "dc.identifier.doi": [{"value": "10.1596/1813-9450-11021"}],
      "dc.identifier.uri": [{"value": "https://hdl.handle.net/10986/42650"}],
      "dc.relation.ispartofseries": [{"value": "Policy Research Working Paper; 11021"}],
      "dc.title": [{"value": "Financial Inclusion and Economic Development"}],
      "dc.title.subtitle": [{"value": "A Review of the Data and Evidence"}],
      "dc.type": [{"value": "Working Paper"}],
      "okr.doctype": [{"value": "Policy Research Working Paper"}, {"value": "Publications & Research"}],
      "okr.identifier.externaldocumentum": [{"value": "34443889"}],
      "okr.identifier.report": [{"value": "WPS11021"}],
      "okr.pdfurl": [{"value": "http://documents.worldbank.org/curated/en/099329001082519086/pdf/IDU15bb9262016afe14e8c1b33b1cb2cc7b93495.pdf"}]},
    "_embedded": {"bundles": {"_embedded": {"bundles": [
      {"name": "ORIGINAL", "_embedded": {"bitstreams": {"_embedded": {"bitstreams": [
        {"name": "IDU15bb9262016afe14e8c1b33b1cb2cc7b93495.pdf", "uuid": "e18fa373-7822-4fb8-beee-37dda8aa4202",
         "sizeBytes": 666098, "sequenceId": 1,
         "_links": {"content": {"href": "https://openknowledge.worldbank.org/server/api/core/bitstreams/e18fa373-7822-4fb8-beee-37dda8aa4202/content"}}},
        {"name": "IDU15bb9262016afe14e8c1b33b1cb2cc7b93495.txt", "sizeBytes": 86816, "sequenceId": 2}]}}}},
      {"name": "LICENSE"}, {"name": "THUMBNAIL"}]}}}}}}]}}}}
```

The ORIGINAL bundle of *The Global Findex Database 2025* (`okr:10986/43438`) holds five PDFs:

| sequence | name | description |
|---|---|---|
| 9 | `9781464822049.pdf` | Full Report, 14.3 MB |
| 10 | `9781464822049_VisualSummary.pdf` | Visual Executive Summary |
| 11 | `33838_English.pdf` | Executive Summary |
| 12 | `33840_Spanish ES.pdf` | Spanish Executive Summary |
| 13 | `33839_rev.pdf` | French Executive Summary |

`okr_search.py` picks the Full Report. The bundle's `primaryBitstream` is set on this item but empty on most others.

### DOI and handle

DOIs resolve to the item page: `https://doi.org/10.1596/1813-9450-11021` lands on `https://openknowledge.worldbank.org/entities/publication/37271e00-...`, and so does `https://hdl.handle.net/10986/42650`. The patterns are:

- `10.1596/978-<ISBN>` for books and flagships;
- `10.1596/1813-9450-<number>` for Policy Research Working Papers (ISSN 1813-9450).

## 3. Projects & Operations v3

`GET https://search.worldbank.org/api/v3/projects?format=json&...`

| Parameter | Example | Status |
|---|---|---|
| `countrycode_exact` | `NP`, `NP^BD` | works. ISO2, capitals only (`np` gives 0) |
| `countryshortname_exact` | `Nepal` | works |
| `status_exact` | `Active`, `Closed`, `Pipeline`, `Dropped` | works (Nepal: 25 / 196 / 2 / 58) |
| `regionname_exact` | `South Asia` | works |
| `sector_exact` (= `mjsector_exact`) | `Banking Institutions` | works. Sector names, not major sectors (`Financial Sector` gives 0) |
| `themev2_level1_exact` | `Finance` | works |
| `qterm` | `financial inclusion` | works |
| `strdate`, `enddate` | `2015-01-01`, `2016-12-31` | works on board approval date. Here `strdate` alone means "from" |
| `srt=boardapprovaldate&order=desc` | | works (the default order). `asc` lists projects with no date first |
| `id` | `P508961` | works |
| `fct` | `status_exact` | works. Facets for sector fields come back empty |
| `fl` | `fl=*` for everything | works. There is no `url`, `sector1` or `lendinginstr` field any more |
| `major_sector_name`, `major_sector_name_exact` | | ignored |

`rows` is a number, but `os`, `page` and `total` come back as strings. Projects are keyed by id. The project page is `https://projects.worldbank.org/en/projects-operations/project-detail/<id>`.

```
GET https://search.worldbank.org/api/v3/projects?format=json&id=P508961&fl=id,project_name,countryshortname,countrycode,regionname,status,boardapprovaldate,closingdate,totalamt,curr_total_commitment,grantamt,major_sectors,themev2_level1_exact,pdo
```
```json
{"rows": 10, "os": "0", "page": "1", "total": "1",
 "projects": {"P508961": {
   "id": "P508961",
   "themev2_level1_exact": ["Data Ecosystem", "Data Ecosystem", "Data Ecosystem", "Digital Transformation", "..."],
   "proj_id": "P508961", "countryshortname": "Nepal",
   "boardapprovaldate": "2026-01-29T00:00:00Z", "grantamt": "0", "totalamt": "95000000",
   "regionname": "South Asia", "closingdate": "2030-06-30",
   "project_abstract": "The proposed SIF operation aims to strengthen:  (i) the Deposit and Credit Guarantee Fund (DCGF) by enhancing ...",
   "major_sectors": [{"major_sector": {"major_sector_code": "FFX", "major_sector_name": "Financial Sector", "sectors": [
      {"sector_name": "Banking Institutions", "sector_code": "FFA", "sector_percent": "53.0"},
      {"sector_name": "Capital Markets", "sector_code": "FFK", "sector_percent": "45.0"},
      {"sector_name": "Public Administration - Financial Sector", "sector_code": "FFP", "sector_percent": "2.0"}]}}],
   "countrycode": ["NP"], "status": "Active",
   "pdo": "Improve access to finance for MSMEs through credit risk mitigation and improved credit infrastructure",
   "project_name": "Sustainable and Inclusive Finance", "curr_total_commitment": "95000000"}},
 "facets": {}}
```

| Field | Meaning |
|---|---|
| `boardapprovaldate`, `closingdate` | approval (future for pipeline) and closing dates |
| `totalamt` | Bank commitment, US$ (missing for many trust-funded grants) |
| `curr_total_commitment`, `curr_ida_commitment`, `curr_ibrd_commitment` | current commitments, US$ |
| `grantamt`, `idacommamt`, `lendprojectcost` | grant amount, IDA amount, total project cost |
| `major_sectors` | major sector with sectors and percentages |
| `themev2_level1_exact` | top-level themes, repeated once per sub-theme |
| `pdo`, `project_abstract` | development objective, abstract |
| `projectfinancialtype`, `financers` | IDA, IBRD, Grants, Trust Funds; financiers with amounts |
| `borrower`, `impagency`, `teamleadname` | borrower, implementing agency, team lead |
| also | `milestones`, `isr_ratings`, `geo_locations`, `loan_transactions`, `theme_list`, `last_stage_reached_name`, `fiscalyear` | with `fl=*` |
