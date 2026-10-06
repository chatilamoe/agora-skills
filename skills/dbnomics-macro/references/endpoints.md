# DBnomics Web API v22: endpoints, parameters, replies, freshness

Base URL `https://api.db.nomics.world/v22`. No key. Documentation: `/v22/apidocs`; OpenAPI spec: `/v22/apispec_1.json`. Checked on 2026-10-06 (API version 22.1.17).

## Endpoints and parameters

| Endpoint | Parameters (default, maximum) | Returns |
|---|---|---|
| `GET /providers` | `limit` (1000), `offset` | `providers.docs[]`: `code`, `name`, `region`, `website`, `terms_of_use`, `indexed_at`; plus `nb_datasets`, `nb_series` |
| `GET /providers/{provider}` | | `provider` and `category_tree` (nested `children`; leaves have `code` and `name`) |
| `GET /datasets/{provider}` | `limit` (50, max 500), `offset` | every dataset with its full labels: heavy |
| `GET /datasets/{provider}/{dataset}` | | `datasets.docs[0]`: `code`, `name`, `nb_series`, `indexed_at`, `updated_at` (some providers), `dimensions_codes_order`, `dimensions_labels`, `dimensions_values_labels`, `source_href`, `doc_href` |
| `GET /search` | `q`, `limit` (10, max 100), `offset` | `results.docs[]` of datasets: `provider_code`, `code`, `name`, `nb_matching_series`, `nb_series`, `indexed_at`; `results.num_found` |
| `GET /series/{provider}/{dataset}` | `dimensions` (JSON object), `q`, `facets`, `observations`, `metadata`, `format`, `align_periods`, `limit` (1000, max 1000), `offset` | `series.docs[]`, `series.num_found`; with `facets=1`, `series_dimensions_facets` = `{dimension: [{code, count}]}` |
| `GET /series/{provider}/{dataset}/{series code or mask}` | as above, except `dimensions` | the series that match the code or mask |
| `GET /series` | `series_ids` (comma-separated `P/D/S`), `observations`, `metadata`, `format`, `align_periods`, `limit`, `offset` | `series.docs[]` from any datasets; `errors[]` for IDs that failed |
| `GET /last-updates` | `providers.limit`, `datasets.limit` and their offsets | the most recently indexed providers and datasets |

- **`observations=1`** adds three arrays to each series: `period` (`2024`, `2024-Q1`, `2024-01`, `2024-01-31`), `period_start_day` (ISO date) and `value` (numbers, or the string `"NA"`).
- **`metadata=0`** drops the `provider` and `dataset` objects from series replies. Two series (WEO and WDI) with metadata: 137 KB; without: 5 KB.
- **`dimensions`** is URL-encoded JSON, values as lists: `{"weo-country":["NPL","IND"],"weo-subject":["NGDP_RPCH"]}`. Dimension names and codes are case-sensitive.
- **`q`** inside a dataset matches whole words in series names and the dataset's text.
- **Masks** in the path: codes joined by `+`, an empty position for all codes, a trailing empty position may be dropped (`A.FR.` = `A.FR`); a value that contains `+` goes in double quotes. Masks do not work in `series_ids`.
- **`format=csv`** returns CSV (a ZIP of one CSV per frequency when frequencies are mixed). The scripts use JSON.
- **No period filter.** Filter on `period_start_day` after the call.

A series as returned by `/series/IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change?observations=1&metadata=0` (arrays shortened):

```json
{"@frequency": "annual", "dataset_code": "WEO:2025-04", "dataset_name": "World Economic Outlook by countries",
 "dimensions": {"unit": "pcent_change", "weo-country": "NPL", "weo-subject": "NGDP_RPCH"},
 "indexed_at": "2025-05-15T11:13:27.379Z", "provider_code": "IMF", "series_code": "NPL.NGDP_RPCH.pcent_change",
 "series_name": "Nepal – Gross domestic product, constant prices (NGDP_RPCH) – Percent change",
 "period": ["1980", "...", "2030"], "period_start_day": ["1980-01-01", "...", "2030-01-01"], "value": [-2.32, "...", 4.999]}
```

## The calls, run as a script

```
$ cat dbn_curl.sh
UA="agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
A=https://api.db.nomics.world/v22
curl -s -A "$UA" "$A/providers" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['providers']['docs']), 'providers,', d['nb_datasets'], 'datasets,', d['nb_series'], 'series')"
curl -s -A "$UA" "$A/search?q=nepal%20gdp%20weo&limit=2" | python3 -c "import json,sys; r=json.load(sys.stdin)['results']; print(r['num_found'], [(d['provider_code'], d['code'], d['nb_matching_series']) for d in r['docs']])"
curl -s -A "$UA" "$A/series/IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change?observations=1&metadata=0" | python3 -c "import json,sys; s=json.load(sys.stdin)['series']['docs'][0]; print(s['series_code'], s['@frequency'], s['period'][-2:], s['value'][-2:], s['indexed_at'])"
curl -s -A "$UA" "$A/series/IMF/WEO:2025-04?dimensions=%7B%22weo-country%22%3A%5B%22NPL%22%5D%7D&facets=1&limit=0&metadata=0" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['series']['num_found'], {k: len(v) for k, v in d['series_dimensions_facets'].items()})"
curl -s -A "$UA" "$A/series?series_ids=IMF/WEO:2025-04/NPL.NGDP_RPCH.pcent_change,WB/WDI/A-NY.GDP.MKTP.KD.ZG-NPL&metadata=0" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['series']['num_found'], [s['series_code'] for s in d['series']['docs']])"
curl -s -A "$UA" "$A/last-updates?datasets.limit=2&providers.limit=2" | python3 -c "import json,sys; d=json.load(sys.stdin); print([(p['code'], p['indexed_at'][:10]) for p in d['providers']['docs']])"
curl -s -A "$UA" -w "\n%{http_code}\n" "$A/series/IMF/WEO:2025-04/NPL.NOPE.x" | python3 -c "import json,sys; t=sys.stdin.read().split('\\n'); print('HTTP', t[-2], json.loads(t[0])['message'])"
curl -s -A "$UA" "$A/series/IMF/WEO:2025-04?dimensions=%7B%22nope%22%3A%5B%22NPL%22%5D%7D&limit=2&metadata=0" | python3 -c "import json,sys; print(json.load(sys.stdin)['series']['num_found'], 'series')"
curl -s -A "$UA" -w "\n%{http_code}\n" "$A/series?q=nepal" | python3 -c "import json,sys; t=sys.stdin.read().split('\\n'); print('HTTP', t[-2], json.loads(t[0])['message'])"
curl -s -A "$UA" -w "\n%{http_code}\n" "$A/series/IMF/WEO:2025-04?limit=1001" | python3 -c "import json,sys; t=sys.stdin.read().split('\\n'); print('HTTP', t[-2], json.loads(t[0])['message'])"
```

```
$ bash dbn_curl.sh
94 providers, 47264 datasets, 1725489754 series
34 [('IMF', 'WEO:2010-10', 13), ('IMF', 'WEO:2011-04', 13)]
NPL.NGDP_RPCH.pcent_change annual ['2029', '2030'] [5.0, 4.999] 2025-05-15T11:13:27.379Z
44 {'unit': 12, 'weo-country': 196, 'weo-subject': 44}
2 ['NPL.NGDP_RPCH.pcent_change', 'A-NY.GDP.MKTP.KD.ZG-NPL']
[('DESTATIS', '2026-10-06'), ('CSO', '2026-10-06')]
HTTP 404 Series 'IMF/WEO:2025-04/NPL.NOPE.x' not found
0 series
HTTP 400 Invalid value {'q': 'nepal'} (dict): additional properties: ['q']
HTTP 400 Invalid value 1001 (int): must not be larger than 1000 (at limit)
```

## Errors

| Situation | Reply |
|---|---|
| unknown provider, dataset or series | HTTP 404, `{"message": "Series 'IMF/WEO:2025-04/NPL.NOPE.x' not found"}` (or `Dataset '...'`, `Provider '...'`) |
| unknown parameter (`q` on `/series`) | HTTP 400, `Invalid value {'q': 'nepal'} (dict): additional properties: ['q']` |
| `limit` over the maximum | HTTP 400, `must not be larger than 1000 (at limit)` |
| unknown dimension name in `dimensions` | HTTP 200, `num_found` 0: no error |
| an ID in `series_ids` that does not exist, or a mask there | HTTP 200; the series is missing and `errors[]` says `Could not load series` or `Could not load dataset` |

The scripts retry 429 and 5xx (after 2, 5 and 10 s), stop on the others with the server's `message`, and check the two silent cases.

## How fresh each provider is

`indexed_at` per provider on 2026-10-06:

```
$ cat fresh.sh
curl -s "https://api.db.nomics.world/v22/providers" | python3 -c "import json,sys; d=json.load(sys.stdin)['providers']['docs']; print('\n'.join(p['code'].ljust(9) + p['indexed_at'][:10] for p in d if p['code'] in ('IMF','WB','OECD','ECB','BIS','Eurostat','ILO','UNDATA','UNCTAD','FAO','WHO','WTO','AMECO','FED','BEA','BLS','INSEE','ONS')))"
```

```
$ bash fresh.sh
AMECO    2026-10-06
BEA      2026-10-06
BIS      2025-07-10
BLS      2026-03-25
ECB      2026-10-04
Eurostat 2026-01-22
FAO      2024-06-03
FED      2026-10-06
ILO      2024-02-20
IMF      2025-09-04
INSEE    2026-10-06
OECD     2026-06-16
ONS      2026-10-06
UNCTAD   2023-07-01
UNDATA   2026-10-04
WB       2024-09-19
WHO      2026-10-06
WTO      2026-10-06
```

A provider's date is its latest indexing; a dataset can be older. Dates seen on datasets the same day:

| Dataset | `indexed_at` | Newest data in the copy |
|---|---|---|
| `IMF/WEO:2025-04` | 2025-05-15 | the April 2025 WEO (the IMF serves April 2026) |
| `IMF/IFS` | 2025-08-26 | frozen copy of the old IMF API |
| `IMF/DOT`, `IMF/GFSR` | 2025-08-31 | frozen copy of the old IMF API |
| `WB/WDI` | 2024-06-29 | Nepal GDP growth to 2023; account ownership to 2021 |
| `OECD/DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD` | 2026-06-16 | 2026-Q1 |
| `ECB/HICP`, `ECB/EXR` | 2026-10-04 | 2026-09; 2026-10-02 |
| `ECB/ICP` | 2026-10-04 | stops at 2025-12: superseded by `ECB/HICP` |

Totals on 2026-10-06: 94 providers, 47,264 datasets, 1,725,489,754 series. Datasets per provider from `/datasets/{provider}`: IMF 106, World Bank 14, ECB 116, OECD 1,403.
