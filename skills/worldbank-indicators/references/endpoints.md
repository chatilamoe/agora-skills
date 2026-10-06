# Endpoints, parameters and real replies

World Bank Indicators API v2. Base URL: `https://api.worldbank.org/v2`. All replies below are real, from 2026-10-06, with long strings cut with `...`.

## Reply shape

Every list endpoint returns `[meta, rows]`. `meta` has `page`, `pages`, `per_page` and `total`. Data replies add `sourceid` and `lastupdated`. These values are numbers in some replies and strings in others (`"per_page": "50"`, `"total": "71"`).

Errors come back with **HTTP 200**:

```
GET https://api.worldbank.org/v2/country/NPL/indicator/NOT.A.CODE?format=json
[{"message": [{"id": "120", "key": "Invalid value", "value": "The provided parameter value is not valid"}]}]
```

A wrong country code (`XXX`) returns the same message.

## Indicators

| Endpoint | Notes |
|---|---|
| `/indicator?format=json&per_page=1000&page=N` | 29,544 indicators in 30 pages, about 1 MB a page. Each code is filed under one source; 54 codes appear twice |
| `/indicator/{code}?format=json` | one indicator |
| `/sources/{id}/indicators?format=json&per_page=1000` | a source's complete list. Source 28 (Global Findex) has 3,313 here, but only 2,947 are filed under 28 in the global list; 366 sit under Gender Statistics (14) |
| `/topic/{id}/indicator?format=json` | indicators of a topic (topic 7, Financial Sector: 203) |

```
GET https://api.worldbank.org/v2/indicator/FX.OWN.TOTL.ZS?format=json
[{"page": 1, "pages": 1, "per_page": "50", "total": 1},
 [{"id": "FX.OWN.TOTL.ZS",
   "name": "Account ownership at a financial institution or with a mobile-money-service provider (% of population ages 15+)",
   "unit": "", "source": {"id": "2", "value": "World Development Indicators"},
   "sourceNote": "Account denotes the percentage of respondents who report having an account (by themselves or together with someone else)...",
   "sourceOrganization": "Global Findex Database, World Bank (WB), uri: https://www.worldbank.org/en/publication/globalfindex",
   "topics": [{"id": "7", "value": "Financial Sector "}]}]]
```

```
GET https://api.worldbank.org/v2/sources/28/indicators?format=json&per_page=1
[{"page": 1, "pages": 3313, "per_page": "1", "total": 3313},
 [{"id": "account.t.d", "name": "Account (% age 15+)", "unit": "", "source": {"id": "28", "value": "Global Findex database"},
   "sourceNote": "The percentage of respondents who report having an account (by themselves or together with someone else) at a bank or si...",
   "sourceOrganization": "Global Findex Database", "topics": [{}]}]]
```

Topic names carry trailing spaces (`"Financial Sector "`). Findex codes follow a pattern:

- `account.t.d` covers all adults;
- `.1` is women and `.2` is men;
- `.3` is young (15-24) and `.4` is older (25+);
- `.10` is urban;
- `.11` is out of the labour force and `.12` is in it.

## Sources and topics

```
GET https://api.worldbank.org/v2/sources?format=json&per_page=100
meta {"page": "1", "pages": "1", "per_page": "100", "total": "71"}; the entry for 28:
[{"id": "28", "lastupdated": "2025-10-06", "name": "Global Findex database", "code": "FDX", "description": "", "url": "",
  "dataavailability": "Y", "metadataavailability": "Y", "concepts": "3"}]
```

Sources used most often:

| id | code | name | last updated |
|---|---|---|---|
| 2 | WDI | World Development Indicators | 2026-07-13 |
| 3 | WGI | Worldwide Governance Indicators | 2026-09-25 |
| 6 | IDS | International Debt Statistics | 2025-12-03 |
| 12 | EDS | Education Statistics | 2024-06-25 |
| 14 | GDS | Gender Statistics | 2026-07-22 |
| 15 | GEM | Global Economic Monitor (monthly, quarterly) | 2026-09-08 |
| 16 | HNP | Health Nutrition and Population Statistics | 2026-07-01 |
| 22 | QDS | Quarterly External Debt Statistics SDDS | 2026-08-07 |
| 28 | FDX | Global Findex database | 2025-10-06 |
| 32 | GFD | Global Financial Development | 2022-09-23 |
| 57 | WDA | WDI Database Archives | 2025-10-29 |
| 89 | ID4 | Identification for Development (ID4D) Data | 2026-07-23 |

`/sources` and `/source` both work, as do `/topic` and `/topics`. There are 21 topics. Ids 1 to 21 are:

1. Agriculture & Rural Development
2. Aid Effectiveness
3. Economy & Growth
4. Education
5. Energy & Mining
6. Environment
7. Financial Sector
8. Health
9. Infrastructure
10. Social Protection & Labor
11. Poverty
12. Private Sector
13. Public Sector
14. Science & Technology
15. Social Development
16. Urban Development
17. Gender
18. Millenium development goals (the API's spelling)
19. Climate Change
20. External Debt
21. Trade

## Countries

```
GET https://api.worldbank.org/v2/country/NPL?format=json
[{"page": 1, "pages": 1, "per_page": "50", "total": 1},
 [{"id": "NPL", "iso2Code": "NP", "name": "Nepal",
   "region": {"id": "SAS", "iso2code": "8S", "value": "South Asia"},
   "adminregion": {"id": "SAS", "iso2code": "8S", "value": "South Asia"},
   "incomeLevel": {"id": "LMC", "iso2code": "XN", "value": "Lower middle income"},
   "lendingType": {"id": "IDX", "iso2code": "XI", "value": "IDA"},
   "capitalCity": "Kathmandu", "longitude": "85.3157", "latitude": "27.6939"}]]
```

`/country?format=json&per_page=400` returns 296 rows: 217 economies and 79 aggregates (`region.value` = "Aggregates").

| Field | Ids and counts of economies |
|---|---|
| region | EAS 37, ECS 58, LCN 42, MEA 23, NAC 3, SAS 6, SSF 48 |
| income | HIC 86, UMC 59, LMC 47, LIC 25 |
| lending | IBD (IBRD) 67, IDB (Blend) 19, IDX (IDA) 59, LNX (not classified) 72 |

Server-side filters `?region=SAS` and `?incomeLevel=LMC` work. `?lendingType=IDX` returned 118 rows on 2026-10-06 against 59 IDA economies in the full list. `wdi_countries.py` therefore filters the full list locally.

Aggregate codes accepted by the data endpoint include:

- `WLD`;
- regions: `SAS`, `EAS`, `ECS`, `LCN`, `MEA`, `NAC`, `SSF`;
- income groups: `LIC`, `LMC`, `UMC`, `HIC`, `LMY`, `MIC`;
- lending groups: `IDA`, `IBD`, `IDB`, `IDX`;
- others: `EUU`, `FCV`, `LDC`, `OED` and more. Run `wdi_countries.py --aggregates` for the full list.

## Data

`/country/{codes}/indicator/{code}?format=json&per_page=1000&page=N`

| Parameter | Example | Notes |
|---|---|---|
| codes in the path | `NPL`, `NP`, `NPL;IND;BGD`, `SAS;WLD;LMC`, `all` | `;` separates codes. `all` = 217 economies + 79 aggregates |
| `date` | `2011:2024`, `2024`, `2024Q1:2025Q2`, `2025M01:2025M03` | quarterly form for QEDS (22), monthly form for GEM (15) |
| `mrv` | `mrv=3` | latest N years with data **for the request**; one country can be empty in them |
| `mrnev` | `mrnev=1` | latest N **non-empty** values **per country**. The reply's `sourceid` is null |
| `source` | `source=28` | which database to read a code from |
| `frequency` | `frequency=M` | monthly values (GEM) with `mrv`. `Q` and `Y` returned nothing for GEM CPI |
| `per_page`, `page` | `per_page=1000` | `all` x 4 years of GDP per capita = 1,060 rows = 2 pages |

```
GET https://api.worldbank.org/v2/country/NPL/indicator/FX.OWN.TOTL.ZS?format=json&date=2023:2024
[{"page": 1, "pages": 1, "per_page": 50, "total": 2, "sourceid": "2", "lastupdated": "2026-07-13"},
 [{"indicator": {"id": "FX.OWN.TOTL.ZS", "value": "Account ownership at a financial institution or with a mobile-money-service provider (% of population ages 15+)"},
   "country": {"id": "NP", "value": "Nepal"}, "countryiso3code": "NPL", "date": "2024", "value": 59.9911157064883,
   "unit": "", "obs_status": "", "decimal": 2},
  {"indicator": {"id": "FX.OWN.TOTL.ZS", "value": "..."}, "country": {"id": "NP", "value": "Nepal"}, "countryiso3code": "NPL",
   "date": "2023", "value": null, "unit": "", "obs_status": "", "decimal": 2}]]
```

Income groups come back with an empty `countryiso3code` and an iso2-style id:

```
GET https://api.worldbank.org/v2/country/LMC/indicator/NY.GDP.PCAP.CD?format=json&mrv=1
[{"page": 1, "pages": 1, "per_page": 50, "total": 1, "sourceid": "2", "lastupdated": "2026-07-13"},
 [{"indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
   "country": {"id": "XN", "value": "Lower middle income"}, "countryiso3code": "", "date": "2025",
   "value": 2481.42751777184, "unit": "", "obs_status": "", "decimal": 1}]]
```

The empty codes are XD (High income), XM (Low income), XN (Lower middle income), XT (Upper middle income) and XY (Not classified). Region aggregates have an ISO3 code (`SAS`). Global Economic Monitor rows have an empty `countryiso3code` but the 3-letter code in `country.id`. `wdi_fetch.py` maps all of these back to the codes in `/country` (`LMC`, `HIC`, ...).

### mrv and mrnev: real replies

| Request | Rows returned |
|---|---|
| `NPL;LKA;BTN` / `FX.OWN.TOTL.ZS` / `mrv=1` | BTN 2024 null, LKA 2024 81.69, NPL 2024 59.99 |
| same / `mrnev=1` | BTN 2024 null, LKA 2024 81.69, NPL 2024 59.99 (Bhutan has nothing recent enough) |
| `BTN` alone / `mrv=1` | BTN 2014 33.67 (the latest year with data for this request) |
| `NPL;LKA` / `SI.POV.GINI` / `mrv=2` | LKA 2022 null, LKA 2019 37.7, NPL 2022 30, NPL 2019 null |
| same / `mrnev=2` | LKA 2019 37.7, LKA 2016 39.3, NPL 2022 30, NPL 2010 32.8 |

### Same code, two sources

| Request | Dataset reported | Values (NPL) |
|---|---|---|
| `borrow.any.t.d`, no `source` | Gender Statistics (14), updated 2026-07-22 | 2021 53.98, 2024 70.40 |
| `borrow.any.t.d`, `source=28` | Global Findex database (28), updated 2025-10-06 | 2021 53.98, 2024 70.40 |
| `FX.OWN.TOTL.ZS` (WDI) and `account.t.d` (28) | WDI / Global Findex | both 59.9911157064883 in 2024 |

## Data360

`data360api.worldbank.org` is the Bank's newer data platform. Its endpoint paths could not be verified on 2026-10-06, so no script here calls it. Use the v2 API above.
