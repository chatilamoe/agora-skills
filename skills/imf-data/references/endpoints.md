# IMF SDMX 2.1 API: endpoints, keys, formats, parsing

Base URL `https://api.imf.org/external/sdmx/2.1`. No key, no sign-up. Everything below was checked on 2026-10-06.

The old API, `https://dataservices.imf.org/REST/SDMX_JSON.svc`, is gone: on 2026-10-06 its host did not resolve (`curl: (6) Could not resolve host: dataservices.imf.org`).

## Endpoints

| Call | What it returns | Size and time seen |
|---|---|---|
| `GET /dataflow/all/all/all` | every dataflow, every version (407 entries, 223 dataflows) | 851 KB, 2 s |
| `GET /dataflow` (= `/dataflow/all/all/latest`) | the latest version of each, but only 222: `IMF.STA,GFS_SOO` is missing | 446 KB, 2 s |
| `GET /dataflow/IMF.STA` | one agency's dataflows | 393 KB |
| `GET /dataflow/all/{id}/latest` | finds a dataflow's agency from its bare id | 3 KB |
| `GET /dataflow/{agency}/{id}/latest?references=datastructure` | the dataflow and its data structure (dimensions, attributes, groups) | 54 KB for WEO, 1 s |
| `GET /dataflow/{agency}/{id}/latest?references=descendants` | the same plus concept schemes and codelists; `references=all` adds category schemes | 2.9 to 6.8 MB, 2 to 6 s |
| `GET /datastructure/{agency}/{dsd}/{version}?references=children` | a structure and its concept schemes, but no codelists | 134 KB for DSD_WEO |
| `GET /codelist/{agency}/{id}/latest` | one codelist | 128 KB for `IMF.RES/CL_WEO_INDICATOR`, 145 codes |
| `GET /availableconstraint/{agency},{id}/{key}` | the codes with data under a partial key, per dimension; `series_count`, `time_period_start`, `time_period_end` (the day after the last period: `2032-01-01` for WEO, whose last year is 2031) | 3 to 44 KB, 1 s |
| `GET /contentconstraint/all/all/latest` | stored constraints; only three ISORA ones, so use `availableconstraint` | 22 KB |
| `GET /data/{agency},{id}[,{version}]/{key}` | the data | WEO, one country and indicator: 5 KB; WEO `all` for one year: 6 MB, 18 s |

`/data` parameters that work: `startPeriod`, `endPeriod` (`2015`, `2025-01`, `2025-M01`, `2025-Q1`), `lastNObservations=N`. A dataflow reference may carry a version (`IMF.RES,WEO,9.0.0`) or `latest`; without one the latest is used. The agency may be left out (`data/WEO/...` worked), but always give it.

## Keys

- **Order:** the dimensions in the order of the data structure's `DimensionList` (the `position` attribute). For WEO: `COUNTRY.INDICATOR.FREQUENCY`. `imf_dimensions.py` prints it.
- **Several codes:** `NPL+IND+BGD`.
- **All codes in one position:** leave it empty (`NPL..A`; `.NGDP_RPCH.A` for every country).
- **Short keys:** missing trailing positions act as wildcards (`NPL` and `NPL..A` return the same 33 WEO series). `imf_fetch.py` pads them so the logged URL is explicit.
- **Everything:** `all`.
- **Case and order matter:** `npl.ngdp_rpch.a` and `NGDP_RPCH.NPL.A` return HTTP 200 with no series.
- **Too many positions:** HTTP 400, `key NPL.NGDP_RPCH.A.X has more than expected 3 dimension(s)`.

## Formats

The default for `/data` is SDMX-ML 2.1 StructureSpecificData (`application/xml`). Choose another with the `Accept` header; the `format=` parameter is ignored.

| `Accept` | Result |
|---|---|
| none, `*/*`, `application/vnd.sdmx.structurespecificdata+xml;version=2.1` | StructureSpecificData XML |
| `application/json` | SDMX-JSON: `dataSets` with series keyed `0:0:0` and observations keyed by time index, plus `structure` with the names of every code |
| `text/csv` or `application/vnd.sdmx.data+csv;version=1.0.0` | SDMX-CSV: one row per observation, every attribute as a column (68 columns for WEO) |
| `application/vnd.sdmx.data+json;version=1.0.0` | ignored: XML comes back |
| `application/vnd.sdmx.data+json;version=2.0.0`, `application/vnd.sdmx.genericdata+xml;version=2.1` | HTTP 500 |

Structure calls (`/dataflow`, `/datastructure`, `/codelist`) answer only XML; asking for JSON gives HTTP 406. `/availableconstraint` answers XML but labels it `application/json`. `/data` compresses with gzip when asked (`Accept-Encoding: gzip`: 154 KB became 22 KB); structure calls do not.

The documented calls, run as a script:

```
$ cat curl_doc.sh
UA="agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"
B=https://api.imf.org/external/sdmx/2.1
curl -s -A "$UA" -H "Accept: text/csv" "$B/data/IMF.RES,WEO/NPL.NGDP_RPCH.A?startPeriod=2024&endPeriod=2025" | cut -d, -f1-6
curl -s -A "$UA" -H "Accept: application/json" "$B/data/IMF.RES,WEO/NPL.NGDP_RPCH.A?startPeriod=2024&endPeriod=2025" | head -c 160; echo
curl -s -A "$UA" -w "\n[HTTP %{http_code}]\n" "$B/data/IMF.RES,NOPE/NPL.NGDP_RPCH.A" | cut -c1-110
curl -s -A "$UA" -w "\n[HTTP %{http_code}]\n" "$B/data/IMF.RES,WEO/NPL.NGDP_RPCH.A.X" | cut -c1-110
curl -s -A "$UA" -o /dev/null -w "HTTP %{http_code}, %{size_download} bytes\n" "$B/dataflow/IMF.STA/IFS"
curl -s -A "$UA" "$B/availableconstraint/IMF.RES,WEO/NPL..A" | grep -A1 '<com:Annotation id=' | grep -o '<com:Annotation[^>]*>\|<com:AnnotationTitle>[^<]*'
```

```
$ bash curl_doc.sh
DATAFLOW,COUNTRY,INDICATOR,FREQUENCY,TIME_PERIOD,OBS_VALUE
IMF.RES:WEO(9.0.0),NPL,NGDP_RPCH,A,2024,3.665374
IMF.RES:WEO(9.0.0),NPL,NGDP_RPCH,A,2025,4.603769
{"header":{"id":"DS1791311508122","prepared":"2026-10-06T18:31:48Z","test":false,"sender":{"id":"IMF","name":"unknown"}},"dataSets":[{"action":"Replace","attrib
{"status":404,"code":40400,"message":"No such dataflow found: Dataflow=IMF.RES:NOPE(latest)","devMessage":null
[HTTP 404]
{"status":400,"code":40000,"message":"key NPL.NGDP_RPCH.A.X has more than expected 3 dimension(s)","devMessage
[HTTP 400]
HTTP 204, 0 bytes
<com:Annotation id="series_count">
<com:AnnotationTitle>33
<com:Annotation id="time_period_start">
<com:AnnotationTitle>1980-01-01
<com:Annotation id="time_period_end">
<com:AnnotationTitle>2032-01-01
```

## Parsing StructureSpecificData with xml.etree

The shape of a `/data` reply:

```xml
<message:StructureSpecificData ...>
  <message:Header> ... </message:Header>
  <message:DataSet ... UPDATE_DATE="2026-04-15T13:00:00Z" PUBLICATION_DATE="2026-04-14T13:00:00Z"
                   SUGGESTED_CITATION="International Monetary Fund. World Economic Outlook (WEO), ...">
    <Group INDICATOR="NGDP_RPCH" SERIES_NAME="Gross domestic product (GDP), Constant prices, Percent change" UNIT="PT" .../>
    <Group INDICATOR="NGDP_RPCH" COUNTRY="NPL" LATEST_ACTUAL_ANNUAL_DATA="FY2024/25" METHODOLOGY_NOTES="..." .../>
    <Series COUNTRY="NPL" INDICATOR="NGDP_RPCH" FREQUENCY="A" SCALE="0" DECIMALS_DISPLAYED="3" ...>
      <Obs TIME_PERIOD="2024" OBS_VALUE="3.665374"/>
      <Obs TIME_PERIOD="2025" OBS_VALUE="4.603769"/>
    </Series>
  </message:DataSet>
</message:StructureSpecificData>
```

- `DataSet` is in the message namespace; `Group`, `Series` and `Obs` have no namespace. Match on the local name.
- Dimension values and series attributes are both plain attributes of `Series`. Tell them apart with the structure's dimension list (`imf_fetch.py` reads it from `?references=datastructure`).
- `Group` elements carry attributes shared by several series. A group applies to a series when the group's dimension attributes (here `INDICATOR`, or `COUNTRY` and `INDICATOR`) equal the series'.
- An `Obs` may have no `OBS_VALUE` at all: a placeholder (GFS, GDD). Skip it.

A minimal reader, standard library only:

```python
import urllib.request
import xml.etree.ElementTree as ET

url = ("https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/NPL+IND.NGDP_RPCH.A"
       "?startPeriod=2024&endPeriod=2025")
req = urllib.request.Request(url, headers={"User-Agent": "agora-skills/0.1 (+https://github.com/chatilamoe/agora-skills; mailto:decaihub@worldbank.org)"})
root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())


def local(tag):
    return tag.rsplit("}", 1)[-1]   # DataSet is namespaced; Group, Series and Obs are not


for dataset in (e for e in root.iter() if local(e.tag) == "DataSet"):
    print("IMF update date:", dataset.get("UPDATE_DATE"))
    groups = [g.attrib for g in dataset if local(g.tag) == "Group"]   # shared attributes
    for series in (s for s in dataset if local(s.tag) == "Series"):
        name = next((g["SERIES_NAME"] for g in groups
                     if g.get("INDICATOR") == series.get("INDICATOR") and "SERIES_NAME" in g), "")
        for obs in (o for o in series if local(o.tag) == "Obs"):
            if obs.get("OBS_VALUE") is None:   # placeholder observation: no value
                continue
            print(series.get("COUNTRY"), series.get("INDICATOR"), obs.get("TIME_PERIOD"),
                  obs.get("OBS_VALUE"), "|", name)
```

```
$ python3 parse_snippet.py
IMF update date: 2026-04-15T13:00:00Z
IND NGDP_RPCH 2024 7.099269 | Gross domestic product (GDP), Constant prices, Percent change
IND NGDP_RPCH 2025 7.618457 | Gross domestic product (GDP), Constant prices, Percent change
NPL NGDP_RPCH 2024 3.665374 | Gross domestic product (GDP), Constant prices, Percent change
NPL NGDP_RPCH 2025 4.603769 | Gross domestic product (GDP), Constant prices, Percent change
```

## Attributes worth reading

| Attribute | Where | Meaning |
|---|---|---|
| `UPDATE_DATE`, `PUBLICATION_DATE` | DataSet | when the IMF last updated the dataflow; for WEO, which release you have |
| `SUGGESTED_CITATION` | DataSet | the IMF's own citation text and its data.imf.org page |
| `SERIES_NAME`, `UNIT` | Group (WEO, IMTS) | the indicator's name and unit (`PT` percent, `USD`, `XDC` domestic currency) |
| `LATEST_ACTUAL_ANNUAL_DATA` | Group (WEO) | the last period of actual data, in the country's terms (`FY2024/25`, `2024`) |
| `METHODOLOGY_NOTES`, `METHODOLOGY`, `BASE_YEAR`, `HISTORICAL_DATA_SOURCE` | Group (WEO) | how the country's series is built; Nepal: "FY(t-1/t) = CY(t)" |
| `SCALE` | Series | how the IMF displays the value (`9` billions); the value itself is in units |
| `DECIMALS_DISPLAYED` | Series | how many decimals the IMF shows (`3` for WEO) |
| `IFS_FLAG` | Series | `true` for series that belonged to International Financial Statistics |
| `DERIVATION_TYPE` | Obs (CPI, ER, BOP, IMTS, GFS, FSIC, FM, GDD...) | `O` reported official data, `R` raw data, `M` mixed, `OU` official converted to US dollars, `SE` staff estimate, `SP` staff projection, `SC` staff calculation, `FA` adjusted with Fund records, `TPD` third-party data |

## Errors and empty answers

| Situation | Reply |
|---|---|
| unknown dataflow in `/data` | HTTP 404, JSON `{"status":404,"code":40400,"message":"No such dataflow found: ..."}` |
| unknown dataflow in a structure call | HTTP 204, empty body |
| key with too many positions | HTTP 400, JSON `message` |
| unknown code, wrong order, lower case | HTTP 200, a `DataSet` with no `Series` |
| `endPeriod` before `startPeriod` | HTTP 200, a `Series` with no `Obs` |
| JSON asked from a structure call | HTTP 406 |
| SDMX-JSON 2.0 or generic data asked | HTTP 500 |

The scripts retry 429 and 5xx (after 2, 5 and 10 s) and stop on the others with the server's `message`.
