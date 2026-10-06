# Fields: what each API returns and what the scripts keep

Checked against live responses on 6 October 2026. "Kept" fields go into the `--json` output; the `research/sources.jsonl` record always has the CONVENTIONS.md keys (`id, source, type, title, authors, year, date, url, pdf_url, doi, query, accessed, pages, notes`).

## OpenAlex `/works`

Request: `search=`, `filter=` (comma = AND, `|` = OR inside one filter), `sort=`, `per-page=` (max 200), `select=`, `mailto=`.
`meta` has `count`, `cost_usd` and the query in OQL. The headers carry the budget: `X-RateLimit-Cost-USD`, `X-RateLimit-Remaining-USD`, `X-RateLimit-Limit-USD` (0.1) and `X-RateLimit-Reset` (seconds).

| Field | Kept as | Note |
|---|---|---|
| `id` | `id` = `openalex:W…` | |
| `doi` | `doi` (bare, lower case) | comes as `https://doi.org/...` |
| `display_name` / `title` | `title` | may contain HTML tags: stripped |
| `publication_year`, `publication_date` | `year`, `date` | |
| `type` | `type` | `article`, `report`, `preprint`, `book`, `book-chapter`, `review`, `dissertation`, `dataset`, `other` |
| `authorships[].author.display_name` | `authors` | `authorships[].institutions[].display_name` -> `institutions` (JSON only) |
| `primary_location.source.display_name` | `venue` | replaced by the series name when the DOI shows it (PRWP, NBER) |
| `cited_by_count` | `cited_by` (in `notes`) | |
| `open_access.{is_oa, oa_status, oa_url}` | `is_oa`, `oa_status`, `oa_url` | `oa_url` may be a landing page |
| `best_oa_location.pdf_url`, `locations[].pdf_url` | `pdf_url` | first non-empty |
| `abstract_inverted_index` | `abstract` | rebuilt: `{word: [positions]}` -> text |
| `content_urls` | not used | cached PDFs; `content.openalex.org` answers 401 without a key |

Not kept (large): `concepts`, `topics`, `referenced_works`, `related_works`, `counts_by_year`, `mesh`. The scripts send `select=` to skip them.

Useful filters: `doi_starts_with:`, `primary_location.source.id:`, `locations.source.id:`, `authorships.institutions.lineage:`, `type:`, `from_publication_date:`, `to_publication_date:`, `open_access.is_oa:true`, `cited_by_count:>N`, `language:en`, `title_and_abstract.search:` (billed like a search).

## Crossref `/works`

Request: `query=`, `filter=` (`from-pub-date`, `until-pub-date`, `type`, `prefix`, `has-abstract`...), `sort=` (`relevance`, `is-referenced-by-count`, `published`), `order=`, `rows=` (max 1000), `select=`, `mailto=`. `/works/{doi}` for one record.

| Field | Kept as | Note |
|---|---|---|
| `DOI` | `doi`, `id` = `crossref:<doi>` | |
| `title[]`, `subtitle[]` | `title` | joined as `Title: Subtitle` |
| `author[]` (`given`, `family` or `name`) | `authors` | organisations come as `name` ("World Bank") |
| `issued.date-parts` | `year`, `date` | |
| `type` | `type` | `journal-article`, `report`, `book`, `book-chapter`, `posted-content`, `component`, ... |
| `container-title[]`, `publisher` | `venue`, `publisher` | World Bank items have no container; publisher reads "Washington, DC: World Bank" |
| `is-referenced-by-count` | `cited_by` | Crossref's own count, lower than OpenAlex's |
| `abstract` | `abstract` | JATS XML, stripped; often absent |
| `link[]` | `publisher_links` (JSON only) | text-mining links, often paywalled: never used as `pdf_url` |

`select=institution` is not allowed (HTTP 400); `institution` still comes back on `/works/{doi}` and on full records.

## Semantic Scholar Graph API

`/paper/search?query=&limit=&fields=&year=&fieldsOfStudy=&publicationTypes=&openAccessPdf`, `/paper/search/bulk` (same filters plus `sort=citationCount:desc`; ignores `limit`, returns up to 1,000), `/paper/{id}`, `/paper/{id}/citations`, `/paper/{id}/references`.

| Field | Kept as | Note |
|---|---|---|
| `paperId` | `id` = `s2:<paperId>` | |
| `externalIds.DOI`, `.ArXiv` | `doi`, `arxiv` | |
| `title`, `year`, `publicationDate` | `title`, `year`, `date` | titles can be wrong: PRWP 7255 (Global Findex 2014) is titled "Decentralized Environmental Regulations..." in S2 |
| `authors[].name` | `authors` | initials only for some ("L. Klapper") |
| `venue`, `journal.name` | `venue` | |
| `citationCount` | `cited_by` | |
| `openAccessPdf.{url, status, license}` | `pdf_url` if the URL looks like a PDF, else `oa_url` | `url` may be a handle or DOI landing page, or empty with a publisher `disclaimer` |
| `abstract` | `abstract` | sometimes elided by the publisher |
| `publicationTypes[0]` | `type` | mapped: JournalArticle -> article, Review -> review, Book -> book, ... |

## arXiv `/api/query` (Atom XML)

`search_query=` (`all:`, `ti:`, `abs:`, `au:`, `cat:`, `submittedDate:[YYYYMMDDHHMM TO ...]`, AND/OR), `start`, `max_results` (max 2000), `sortBy` (`relevance`, `submittedDate`, `lastUpdatedDate`), `sortOrder`.

Kept per `<entry>`: `id` (-> `arxiv:<id>` without version), `title`, `summary` (abstract), `published`, `updated`, `author/name`, `link[@title="pdf"]` -> `pdf_url`, `arxiv:primary_category` and `category/@term`, `arxiv:doi` (journal DOI, when present), `arxiv:journal_ref`, `arxiv:comment`. `opensearch:totalResults` gives the count.

## CORE `/v3/search/works/`

`q=` (fields: `title:`, `authors:`, `doi:`, `yearPublished>=`), `limit`, `offset`, `exclude=fullText`. The response has `totalHits` and `results[]`.

Kept: `id` (-> `core:<id>`), `doi`, `title`, `authors[].name` ("Surname, Given"), `yearPublished`, `publishedDate`, `documentType`, `publisher`, `journals[].title`, `citationCount`, `downloadUrl` (-> `pdf_url`, CORE's cached copy; often empty), `links[type=display]` (the CORE page), `abstract`, `dataProviders[].name` (the repositories). Dropped: `fullText`, `references`, `identifiers`, `oaiIds`.

## NBER listing

`page`, `perPage` (20-100), `q`. The response has `totalResults`, `results[]` and `facets` (large: ignored).
Kept per result: `title`, `authors` (HTML anchors, tags stripped), `displaydate` ("January 2011" -> `date` 2011-01), `abstract` (cut at about 300 characters), `url` (`/papers/w16721`). Added: DOI `10.3386/w16721`, PDF `https://www.nber.org/system/files/working_papers/w16721/w16721.pdf` (checked: `application/pdf`).

## Unpaywall `/v2/{doi}?email=`

Kept: `title`, `year`, `published_date`, `genre`, `oa_status`, `z_authors[].{given,family}`, `best_oa_location` and `oa_locations[]` -> `url_for_pdf` (candidate PDF), `url_for_landing_page`, `version` (`publishedVersion`, `acceptedVersion`, `submittedVersion`), `license`, `host_type`, `repository_institution`.
